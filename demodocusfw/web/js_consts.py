"""
Software License Agreement (Apache 2.0)

Copyright (c) 2020, The MITRE Corporation.
All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

This project was developed by The MITRE Corporation.
If this code is used in a deployment or embedded within another project,
it is requested that you send an email to opensource@mitre.org in order to
let us know where this software is being used.
"""

from selenium.webdriver.common.keys import Keys


class JsEvents:
    """Enum that holds onto the different JavaScript events."""
    FOCUS = 'focus'
    BLUR = 'blur'
    MOUSE_IN = 'mousein'
    MOUSE_OVER = 'mouseover'
    MOUSE_CLICK = 'click'
    MOUSE_DOWN = 'mousedown'
    MOUSE_UP = 'mouseup'
    MOUSE_OUT = 'mouseout'
    MOUSE_EVENTS = {MOUSE_IN, MOUSE_OVER, MOUSE_CLICK,
                    MOUSE_DOWN, MOUSE_UP, MOUSE_OUT}
    KEY_DOWN = 'keydown'
    KEY_UP = 'keyup'
    KEY_PRESS = 'keypress'
    KEY_EVENTS = {KEY_DOWN, KEY_UP, KEY_PRESS}


class KeyCodes:
    """Enum that holds onto the different possible keypresses."""
    # keyCode, alphanum, key, code, Selenium
    BACKSPACE       = 8, "", "Backspace", "Backspace"
    TAB             = 9, "", "Tab", "Tab", Keys.TAB
    ENTER           = 13, "", "Enter", "Enter", Keys.ENTER
    SHIFT_L         = 16, "", "Shift", "ShiftLeft"
    SHIFT_R         = 16, "", "Shift", "ShiftRight"
    CTRL_L          = 17, "", "Control", "ControlLeft"
    CTRL_R          = 17, "", "Control", "ControlRight"
    ALT_L           = 18, "", "Alt", "AltLeft"
    ALT_R           = 18, "", "Alt", "AltRight"
    ESCAPE          = 27, "", "Escape", "Escape", Keys.ESCAPE
    SPACE           = 32, " ", " ", "Space", Keys.SPACE
    PAGE_UP         = 33, "", "PageUp", "PageUp"
    PAGE_DOWN       = 34, "", "PageDown", "PageDown"
    END             = 35, "", "End", "End"
    HOME            = 36, "", "Home", "Home"
    LEFT_ARROW      = 37, "", "ArrowLeft", "ArrowLeft", Keys.LEFT
    UP_ARROW        = 38, "", "ArrowUp", "ArrowUp", Keys.UP
    RIGHT_ARROW     = 39, "", "ArrowRight", "ArrowRight", Keys.RIGHT
    DOWN_ARROW      = 40, "", "ArrowDown", "ArrowDown", Keys.DOWN
    INSERT          = 45, "", "Insert", "Insert"
    DELETE          = 46, "", "Delete", "Delete"
    KEY_0           = 48, "0", "0", "Digit0"
    KEY_1           = 49, "1", "1", "Digit1"
    KEY_2           = 50, "2", "2", "Digit2"
    KEY_3           = 51, "3", "3", "Digit3"
    KEY_4           = 52, "4", "4", "Digit4"
    KEY_5           = 53, "5", "5", "Digit5"
    KEY_6           = 54, "6", "6", "Digit6"
    KEY_7           = 55, "7", "7", "Digit7"
    KEY_8           = 56, "8", "8", "Digit8"
    KEY_9           = 57, "9", "9", "Digit9"
    KEY_A           = 65, "a", "a", "KeyA"
    KEY_B           = 66, "b", "b", "KeyB"
    KEY_C           = 67, "c", "c", "KeyC"
    KEY_D           = 68, "d", "d", "KeyD"
    KEY_E           = 69, "e", "e", "KeyE"
    KEY_F           = 70, "f", "f", "KeyF"
    KEY_G           = 71, "g", "g", "KeyG"
    KEY_H           = 72, "h", "h", "KeyH"
    KEY_I           = 73, "i", "i", "KeyI"
    KEY_J           = 74, "j", "j", "KeyJ"
    KEY_K           = 75, "k", "k", "KeyK"
    KEY_L           = 76, "l", "l", "KeyL"
    KEY_M           = 77, "m", "m", "KeyM"
    KEY_N           = 78, "n", "n", "KeyN"
    KEY_O           = 79, "o", "o", "KeyO"
    KEY_P           = 80, "p", "p", "KeyP"
    KEY_Q           = 81, "q", "q", "KeyQ"
    KEY_R           = 82, "r", "r", "KeyR"
    KEY_S           = 83, "s", "s", "KeyS"
    KEY_T           = 84, "t", "t", "KeyT"
    KEY_U           = 85, "u", "u", "KeyU"
    KEY_V           = 86, "v", "v", "KeyV"
    KEY_W           = 87, "w", "w", "KeyW"
    KEY_X           = 88, "x", "x", "KeyX"
    KEY_Y           = 89, "y", "y", "KeyY"
    KEY_Z           = 90, "z", "z", "KeyZ"
    NUMPAD_0        = 96,   "0",   "0", "Numpad0"
    NUMPAD_1        = 97,   "1",   "1", "Numpad1"
    NUMPAD_2        = 98,   "2",   "2", "Numpad2"
    NUMPAD_3        = 99,   "3",   "3", "Numpad3"
    NUMPAD_4        = 100,  "4",   "4", "Numpad4"
    NUMPAD_5        = 101,  "5",   "5", "Numpad5"
    NUMPAD_6        = 102,  "6",   "6", "Numpad6"
    NUMPAD_7        = 103,  "7",   "7", "Numpad7"
    NUMPAD_8        = 104,  "8",   "8", "Numpad8"
    NUMPAD_9        = 105,  "9",   "9", "Numpad9"
    MULTIPLY        = 106,  "*",   "*", "NumpadMultiply"
    ADD             = 107,  "+",   "+", "NumpadAdd"
    SUBTRACT        = 109,  "-",   "-", "NumpadSubtract"
    DECIMAL         = 110,  ".",   ".", "NumpadDecimal"
    DIVIDE          = 111,  "/",   "/", "NumpadDivide"
    F1              = 112, "", "F1", "F1"
    F2              = 113, "", "F2", "F2"
    F3              = 114, "", "F3", "F3"
    F4              = 115, "", "F4", "F4"
    F5              = 116, "", "F5", "F5"
    F6              = 117, "", "F6", "F6"
    F7              = 118, "", "F7", "F7"
    F8              = 119, "", "F8", "F8"
    F9              = 120, "", "F9", "F9"
    F10             = 121, "", "F10", "F10"
    F11             = 122, "", "F11", "F11"
    F12             = 123, "", "F12", "F12"
    NUM_LOCK        = 144, "", "NumLock"
    SCROLL_LOCK     = 145, "", "ScrollLock"
    SEMICOLON       = 186, ";", ";", "Semicolon"
    EQUALS          = 187, "=", "=", "Equal"
    COMMA           = 188, ",", ",", "Comma"
    DASH            = 189, "-", "-", "Minus"
    PERIOD          = 190, ".", ".", "Period"
    FORWARD_SLASH   = 191, "/", "/", "Slash"
    GRAVE_ACCENT    = 192, "`", "`", "Backquote"
    OPEN_BRACKET    = 219, "[", "[", "BracketLeft"
    BACK_SLASH      = 220, "\\", "\\", "Backslash"
    CLOSE_BRACKET   = 221, "]", "]", "BracketRight"
    SINGLE_QUOTE    = 222, "'", "'", "Quote"
