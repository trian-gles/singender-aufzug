import time
from pythonosc.udp_client import SimpleUDPClient


client = SimpleUDPClient("127.0.0.1", 9000)

commands = [
    ["idle"],
    ["listening"],
    ["thinking"],
    ["speaking", "Hello! I am speaking now."],
]

for command in commands:
    print("Sending:", command)

    client.send_message("/scene", command)

    time.sleep(3)
