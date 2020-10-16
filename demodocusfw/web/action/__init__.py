from .form import FormFillAction
from .keyboard import KeyPress, Focus, Blur
from .mouse import MouseClick, MouseOut, MouseOver
from demodocusfw.web import KeyCodes

# Let's make some sets of actions.
mouse_actions = {MouseClick.get(), MouseOut.get(), MouseOver.get()}

keys = {KeyCodes.TAB, KeyCodes.SPACE, KeyCodes.ENTER, KeyCodes.ESCAPE,
        KeyCodes.UP_ARROW, KeyCodes.DOWN_ARROW,
        KeyCodes.LEFT_ARROW, KeyCodes.RIGHT_ARROW}
keyboard_actions = {
    Focus.get(),
    Blur.get(),
} | {KeyPress.get(key) for key in keys}
