from gpiozero import Button
from signal import pause

# gpiozero automatically assumes a pull-up circuit by default.
# It expects the button to connect to GND when pressed.
button = Button(16)

def button_pressed():
    print("Button Pressed!")

def button_released():
    print("Waiting...")

# Assign actions to button events
button.when_pressed = button_pressed
button.when_released = button_released

print("Program is running. Press the button to test!")

# pause() keeps the script running in the background to listen for events
pause()

