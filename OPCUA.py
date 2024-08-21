from opcua import Client

def collect_data():
    global R01_Load, R04_Load, CycleState
    server_endpoint = "opc.tcp://192.168.0.2:4840"
    client = Client(server_endpoint)
    client.connect()
    node_inputs = client.get_node("ns=3;s=Inputs")
    node_outputs = client.get_node("ns=3;s=Outputs")
    CycleState = node_outputs.get_child("Q_Cell_CycleState").get_value()
    R01_Load = node_inputs.get_child("I_R01_Gripper_Load").get_value()
    R04_Load = node_inputs.get_child("I_R04_Gripper_Load").get_value()
    # print(R01_Load)
    # print(R04_Load)
    # print(CycleState)
    client.disconnect()
    return R04_Load,R01_Load,CycleState


collect_data()

