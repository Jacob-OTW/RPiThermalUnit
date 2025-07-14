import pickle
import cv2
import numpy as np
import time
from gpiozero import Button, RotaryEncoder
from Mini2_USB import Mini2
import enum
from Mini2_USB.Mini2 import DigitalVideoFormat, DigitalFrameRate


class Menu:
    """
    Menu which contains further elements
    """
    def __init__(self, parent, *elements):
        self.parent = parent
        self.elements: list[Element] = list(elements)

class AdjustableValue:
    """
    Used to store a range value internally
    """
    def __init__(self, start_value, min_value, max_value, userdata=None):
        self.value = start_value
        self.min_val = min_value
        self.max_val = max_value

        self.userdata = userdata

    def increment(self, delta):
        self.value = min(self.max_val, max(self.min_val, self.value + delta))

class SelectorValue:
    """
    Used to store a selector, so an option out of a list of options, internally
    """
    def __init__(self, options: list | tuple, userdata=None):
        assert(len(options) > 0)

        self.options = options
        self.selector = 0
        self.value = self.options[self.selector]

        self.userdata = userdata

    def next(self):
        self.selector = (self.selector + 1) % len(self.options)
        self.value = self.options[self.selector]

class Element:
    def __init__(self, text):
        self.display_text = text
        self.disabled = False

    def __str__(self):
        if type(self.display_text) == str:
            return self.display_text
        else:
            return self.display_text()

class SubMenuButton(Element):
    def __init__(self, text, callback):
        super().__init__(text)
        self.callback = callback

class Selector(Element):
    def __init__(self, text, value: SelectorValue):
        super().__init__(text)
        self.value = value

    def __str__(self):
        return self.display_text(self.value.value)

    def next(self):
        self.value.next()

class ValueRange(Element):
    def __init__(self, text, value, step_value = 1.0):
        super().__init__(text)
        self.value = value
        self.step_value = step_value

    def __str__(self):
        return self.display_text(self.value.value)

    def up(self):
        self.value.increment(self.step_value)

    def down(self):
        self.value.increment(-self.step_value)

class Camera:
    class Event(enum.Enum):
        ValueChange = 0x00
    """
    State of the `camera`, so the whole digital fusion part
    """
    def __init__(self, screen_size: tuple[int, int]):
        self.mini2 = Mini2.Mini2()

        """
        Is stored in non-volatile storage
        """
        self.store_default = {
            "brightness": AdjustableValue(30, 0, 100, Mini2.AttrHook.Brightness),
            "contrast": AdjustableValue(100, 0, 100, Mini2.AttrHook.Contrast),
            "scene": SelectorValue(["LowHighlight", "Linear", "LowContrast", "General", "HighContrast", "Highlight", "Outline"], Mini2.AttrHook.Scene),
            "x_offset": AdjustableValue(0, -256, 256),
            "y_offset": AdjustableValue(0, -192, 192),
            "scale": AdjustableValue(1, 0.1, 8),
            "color": SelectorValue(["WHOT", "BHOT", "PSQ", ]),
        }

        self.store_file_path = "store.pickle" # Needs to be adjusted!

        try:
            with open(self.store_file_path, "rb") as file:
                load = pickle.load(file)
        except FileNotFoundError:
            load = self.store_default.copy()

        self.store = self.store_default.copy()
        for key in self.store:
            if key not in load:
                continue

            if type(self.store[key]) == AdjustableValue and self.store[key].min_val <= load[key].value <= self.store[key].max_val:
                self.store[key].value = load[key].value
            elif type(self.store[key]) == SelectorValue and load[key].value in self.store[key].options:
                self.store[key].value = load[key].value

            self.event_handler(self.Event.ValueChange, self.store[key])

        self.set_50_hz()
        self.mini2.set_flip(Mini2.FlipMode.X_Flip)

        self.fps = -1

        self.image_menu = Menu(None)
        self.align_menu = Menu(None)
        self.store_menu = Menu(None)

        self.root_menu = Menu(
            None,
            SubMenuButton("Image Settings", lambda: self.set_menu(self.image_menu)),
            SubMenuButton("Align Settings", lambda: self.set_menu(self.align_menu)),
            SubMenuButton("Store", lambda: self.set_menu(self.store_menu)),
            Selector(lambda color: f"Color {color}", self.store["color"]),
            SubMenuButton(lambda: f"FPS {self.fps:.1f}", lambda: self.set_50_hz()),
            SubMenuButton("Exit", lambda: self.set_menu(None)),
        )

        self.image_menu.parent = self.root_menu
        self.image_menu.elements = [
            ValueRange(lambda bright: f"Brightness {bright:.0f}", self.store["brightness"]),
            ValueRange(lambda threshold: f"Contrast {threshold:.0f}", self.store["contrast"]),
            Selector(lambda color: f"Scene {color}", self.store["scene"]),
            SubMenuButton("Back", lambda: self.set_menu(None)),
        ]

        self.align_menu.parent = self.root_menu
        self.align_menu.elements = [
            ValueRange(lambda x: f"X : {x:.0f}", self.store["x_offset"]),
            ValueRange(lambda y: f"Y : {y:.0f}", self.store["y_offset"]),
            ValueRange(lambda scale: f"Scale {scale:.2f}x", self.store["scale"], step_value=0.01),
            SubMenuButton("Back", lambda: self.set_menu(None)),
        ]

        self.store_menu.parent = self.root_menu
        self.store_menu.elements = [
            SubMenuButton("Save", lambda: self.save()),
            SubMenuButton("Restore", lambda: self.restore()),
            SubMenuButton("Back", lambda: self.set_menu(None)),
        ]

        self.selected_menu = None
        self.selected = 0
        self.selected_element = None

        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 1
        self.thickness = 0

        self.encoder = RotaryEncoder(15, 14)
        self.encoder.when_rotated_clockwise = self.down
        self.encoder.when_rotated_counter_clockwise = self.up


        self.button = Button(16, pull_up=True)
        self.button.when_pressed = self.confirm

        self.menu_base = np.zeros((250, 400, 3)).astype(np.uint8)

    def save(self):
        with open(self.store_file_path, "wb") as file:
            pickle.dump(self.store, file)

    def set_50_hz(self):
        time.sleep(1)

        self.mini2.set_detector_frame_rate(Mini2.DigitalFrameRate.Hz50)

        time.sleep(1)

        self.mini2.set_digital_video_format(1, DigitalVideoFormat.UsbProgressive, DigitalFrameRate.Hz50)

    def event_handler(self, event, target: SelectorValue | AdjustableValue):
        match event:
            case Camera.Event.ValueChange:
                if target.userdata == Mini2.AttrHook.Brightness:
                    self.mini2.set_brightness(target.value)
                elif target.userdata == Mini2.AttrHook.Contrast:
                    self.mini2.set_contrast(target.value)
                elif target.userdata == Mini2.AttrHook.Scene:
                    lut = {"LowHighlight": Mini2.SceneMode.LowHighlight,
                           "Linear": Mini2.SceneMode.LinearStretch,
                           "LowContrast": Mini2.SceneMode.LowContrast,
                           "General": Mini2.SceneMode.GeneralMode,
                           "HighContrast": Mini2.SceneMode.HighContrast,
                           "Highlight": Mini2.SceneMode.Highlight,
                           "Outline": Mini2.SceneMode.Outline
                    }
                    self.mini2.set_scene(lut[target.value])

    def restore(self):
        self.store = self.store_default.copy()
        for key in self.store:
            self.event_handler(self.Event.ValueChange, self.store[key])

    def set_menu(self, menu):
        if self.selected_menu is not None and menu is None:
            self.selected_menu = self.selected_menu.parent
            self.selected = 0
        else:
            self.selected_menu = menu
            self.selected = 0

    def set_element(self):
        self.selected_element = self.selected_menu.elements[self.selected]

    def up(self):
        if self.selected_menu is None:
            return
        elif self.selected_element is not None:
            self.selected_element.down()
            self.event_handler(self.Event.ValueChange, self.selected_element.value)
        else:
            self.selected = (self.selected - 1) % len(self.selected_menu.elements)

    def down(self):
        if self.selected_menu is None:
            return
        elif self.selected_element is not None:
            self.selected_element.up()
            self.event_handler(self.Event.ValueChange, self.selected_element.value)
        else:
            self.selected = (self.selected + 1) % len(self.selected_menu.elements)
            if self.selected_menu.elements[self.selected].disabled:
                self.down()

    def confirm(self):
        if self.selected_menu is None:
            self.set_menu(self.root_menu)
        elif self.selected_element is not None:
            self.selected_element = None
        else:
            hovered_element = self.selected_menu.elements[self.selected]
            if isinstance(hovered_element, SubMenuButton):
                hovered_element.callback()
            elif isinstance(hovered_element, ValueRange):
                self.selected_element = hovered_element
            elif isinstance(hovered_element, Selector):
                hovered_element.next()
                self.event_handler(self.Event.ValueChange, hovered_element.value)


    def menu_image(self):
        base = self.menu_base
        if self.selected_menu is None:
            return base

        base[:] = 255

        for i, element in enumerate(self.selected_menu.elements):
            element: Element
            if i == self.selected:
                text_w, text_h = cv2.getTextSize(str(element), self.font, 1, 0)[0]
                start_x = 20
                start_y = 40 * i + 20
                border = 5
                """cv2.rectangle(base, (start_x - border, start_y - border),
                              (start_x + text_w + border, start_y + text_h + border), (255, 0, 0) if element is self.selected_element else (0, 125, 0), cv2.FILLED,
                              cv2.LINE_8)"""
            cv2.putText(base, str(element) + ((" <-" if element is self.selected_element else " <--") if i == self.selected else ""), (20, 40 * (i + 1)), self.font,
                        self.font_scale, (0, 0, 0), 0, cv2.LINE_AA)

        return base