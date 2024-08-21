import asyncio
import os
from OPCUA import collect_data
import cv2
from pypylon import pylon as py
from ImageCap import PylonCameras
from PIL import Image
import ns_hymap_inference
import json

json_file_path = 'output_data.json'


# Define constants
SIZE = (1080, 720)
BASE_IMG_LOC = 'Dataset'

# Ensure the base image directory exists
os.makedirs(BASE_IMG_LOC, exist_ok=True)

#Save the Image from the Cameras
def save_image(image, file_path):
    rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(rgb_image)
    pil_image.save(file_path)


#Grab Image from Cameras, create the file path
async def capture_and_save_images(cap,iteration):
    count = 0
    batch = f'BATCH{count // 2 + 1}'
    os.makedirs(os.path.join(BASE_IMG_LOC, batch), exist_ok=True)

    # Capture images from both cameras
    for i in range(2):
        res = cap.cameras[i].RetrieveResult(5000, py.TimeoutHandling_ThrowException)
        if res.GrabSucceeded():
            # idx, device = cap.get_image_device(res)
            img = cap.converters[i].Convert(res)
            image = img.GetArray()
            image = cap.set_img_size(image, SIZE)
            image = cap.adjust_white_balance(image)
            # Save the raw image
            raw_path = os.path.join(BASE_IMG_LOC, batch, f'{iteration:06d}_camera{i}.png')
            save_image(image, raw_path)
    print("Image capture complete.")

#Append new output to JSON file for logging
def append_to_json_file(data, file_path):
    # Read existing data from the file if it exists
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            try:
                existing_data = json.load(file)
            except json.JSONDecodeError:
                existing_data = []
    else:
        existing_data = []
    # Append new data
    existing_data.append(data)
    # Write the updated data back to the file
    with open(file_path, 'w') as file:
        json.dump(existing_data, file, indent=4)

def get_image_path(iteration, camera_index):
    return os.path.join(BASE_IMG_LOC, 'BATCH1', f'{iteration:06d}_camera{camera_index}.png')

#Capture Image, get sensor data from OPC UA, merge and run through the different forecasting models
async def main():
    cap = PylonCameras(num_devices=2)
    cap.grab('LatestOnly')
    AnomalyLabel = 500
    count = 0
    while True:
        await capture_and_save_images(cap,count)
        image_path = get_image_path(count, 0)  # Accessing camera 0
        image = ns_hymap_inference.prepare_image(image_path)
        # Gets data from OPC UA Server
        raw_data = collect_data()
        # Updates Data and current anomaly label
        time_series_data = [[raw_data[1], raw_data[0], AnomalyLabel]]

        data = ns_hymap_inference.prepare_time_series(time_series_data)

        output = ns_hymap_inference.make_inference_wImage(image, data)
        outputTS = ns_hymap_inference.make_inference_woutImage(data)

        # Update Anomaly label based of the output we just got
        AnomalyLabel = output[0, 0, -1].item()
        count = count + 1
        output_data = {
            'time_series_data': time_series_data,
            'output_with_Image': output.tolist(),  # Convert tensor to list for JSON serialization
            'output_without_Image': outputTS.tolist(),  # Same for this tensor
            'Image Path': image_path
        }
        # Append the output data to the JSON file
        append_to_json_file(output_data, json_file_path)



    #MAPPING NOT WORKING
    # data[2] = output[2].fill_(0).replace({
    #     'Normal': 100, 'NoNose': 200, 'NoBody1': 300, 'NoBody2': 400,
    #     'NoNose,NoBody2': 500, 'NoBody2,NoBody1': 600, 'NoNose,NoBody2,NoBody1': 700
    # })
    # Ensure the camera is released
    cap.cameras.Close()

asyncio.run(main())
