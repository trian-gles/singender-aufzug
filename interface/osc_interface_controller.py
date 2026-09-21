from pythonosc.udp_client import SimpleUDPClient


client = SimpleUDPClient("127.0.0.1", 9000)


def idle():
    client.send_message("/scene", "idle")


def listening():
    client.send_message("/scene", "listening")


def thinking():
    client.send_message("/scene", "thinking")


def speaking(text):
    client.send_message("/scene", ["speaking", text])
