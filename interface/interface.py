import threading
from random import randint
from asciimatics.screen import Screen
from asciimatics.scene import Scene
from asciimatics.effects import Effect, Cycle, Stars, Print
from asciimatics.renderers import FigletText, StaticRenderer
from asciimatics.exceptions import NextScene
from time import sleep
from pythonosc import dispatcher
from pythonosc import osc_server


current_scene = "idle"
speaking_text = ""

class QuestionMarks(Effect):

    def __init__(self, screen, count):
        super().__init__(screen)
        self.count = count
        self.positions = []

        for _ in range(count):
            self.positions.append([
                randint(0, screen.width - 1),
                randint(0, screen.height - 1)
            ])

    @property
    def stop_frame(self):
        return None

    def _update(self, frame_no):
        for position in self.positions:
            x, y = position

            # Erase old position
            self._screen.print_at(" ", x, y)

            # Move upward
            y -= 1

            # Wrap around
            if y < 0:
                y = self._screen.height - 1
                x = randint(0, self._screen.width - 1)

            position[0] = x
            position[1] = y

            # Draw question mark
            self._screen.print_at(
                "?",
                x,
                y,
                colour=Screen.COLOUR_GREEN
            )

    def reset(self):
        pass
# --------------------------------------------------
# OSC
# --------------------------------------------------

def osc_handler(address, *args):
    global current_scene
    global speaking_text

    # print("OSC:", address, args, flush=True)

    if address == "/scene" and args:
        scene = str(args[0])
        if scene == "idle":
            sleep(2)
        if scene in ["idle", "listening", "thinking", "speaking"]:
            current_scene = scene

            if scene == "speaking" and len(args) > 1:
                speaking_text = str(args[1])

            # print("CURRENT SCENE:", current_scene, flush=True)
            # print("SPEAKING TEXT:", speaking_text, flush=True)


def osc_server_thread():
    d = dispatcher.Dispatcher()
    d.map("/scene", osc_handler)

    server = osc_server.ThreadingOSCUDPServer(
        ("0.0.0.0", 9000),
        d
    )

    # print("OSC listening on 9000", flush=True)
    server.serve_forever()


# --------------------------------------------------
# Scene switcher
# --------------------------------------------------

class SceneSwitcher(Effect):

    def __init__(self, screen, scene_name):
        super().__init__(screen)
        self.scene_name = scene_name

    @property
    def stop_frame(self):
        return None

    def _update(self, frame_no):
        if current_scene != self.scene_name:
            raise NextScene(current_scene)

    def reset(self):
        pass


# --------------------------------------------------
# Dynamic bottom text
# --------------------------------------------------

class BottomText(Effect):

    def __init__(self, screen, scene_name):
        super().__init__(screen)
        self.scene_name = scene_name

    @property
    def stop_frame(self):
        return None

    def _update(self, frame_no):

        if self.scene_name == "idle":
            text = "Drück die Taste zu sprechen!"

        elif self.scene_name == "listening":
            text = "Hören..."

        elif self.scene_name == "thinking":
            text = "Denken..."

        elif self.scene_name == "speaking":
            text = speaking_text

        else:
            text = ""

        # Clear the bottom line
        self._screen.print_at(
            " " * self._screen.width,
            0,
            self._screen.height - 2
        )

        # Center the text
        x = max(
            0,
            (self._screen.width - len(text)) // 2
        )

        self._screen.print_at(
            text,
            x,
            self._screen.height - 2,
            colour=Screen.COLOUR_GREEN
        )

    def reset(self):
        pass


# --------------------------------------------------
# ELFI graphics
# --------------------------------------------------

ELFI_FRAMES = [
    """
          .**************************************.
         ***-----------------**-----------------***
         ***                 **                 ***
         ***                 **                 ***
       --***        ::::     **     ::::        ***--
     **==***        ****     **     ****        ***==**
    ***--***        ----     **     ----        ***--***
    ***--***                 **                 ***--***
    ***--***                 **                 ***--***
    ***--***                 **                 ***--***
    ***--***                 **                 ***--***
    ***--***                 **                 ***--***
    ***--***                 **                 ***--***
    ***--***                 **                 ***--***
    ***--***      ************************      ***--***
    ***--***      ************************      ***--***
     .******       **********************       ******.
       ..***        -******************-        ***..
         ***           ------**------           ***
         ***                 **                 ***
         ***-----------------**-----------------***
          .**************************************.
    """,

    """
          .**************************************.
         ***-----------------**-----------------***
         ***                 **                 ***
         ***                 **                 ***
       --***        ::::     **     ::::        ***--
     **==***        ****     **     ****        ***==**
    ***--***        ----     **     ----        ***--***
    ***--***                 **                 ***--***
    ***--***                 **                 ***--***
    ***--***                 **                 ***--***
    ***--***                 **                 ***--***
    ***--***                 **                 ***--***
    ***--***                 **                 ***--***
    ***--***                 **                 ***--***
    ***--***      ...........**...........      ***--***
    ***--***      ...........**...........      ***--***
     .******       ..........**..........       ******.
       ..***        .........**.........        ***..
         ***          .......**.......          ***
         ***                 **                 ***
         ***-----------------**-----------------***
          .**************************************.
    """
]


# --------------------------------------------------
# Scenes
# --------------------------------------------------

def make_scene(screen, name):

    if name == "speaking":
        elfi_frames = ELFI_FRAMES
    else:
        elfi_frames = [ELFI_FRAMES[0]]

    effects = [
        SceneSwitcher(screen, name),

        Cycle(
            screen,
            FigletText("ELFI", font="big"),
            0
        ),

        Print(
            screen,
            StaticRenderer(elfi_frames),
            y=10,
            colour=Screen.COLOUR_GREEN,
            speed=10
        )
    ]

    if name in ["speaking", "idle"]:
        effects.append(
            Stars(
                screen,
                (screen.width + screen.height) // 2
            )
        )

    elif name in ["listening", "thinking"]:
        effects.append(
            QuestionMarks(
                screen,
                (screen.width + screen.height) // 2
            )
        )

    effects.append(
        BottomText(screen, name)
    )

    return Scene(
        effects,
        -1,
        name=name
    )
# --------------------------------------------------
# Main
# --------------------------------------------------

def demo(screen):

    threading.Thread(
        target=osc_server_thread,
        daemon=True
    ).start()

    scenes = [
        make_scene(screen, "idle"),
        make_scene(screen, "listening"),
        make_scene(screen, "thinking"),
        make_scene(screen, "speaking")
    ]

    screen.play(
        scenes,
        stop_on_resize=True
    )


Screen.wrapper(demo)
