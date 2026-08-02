"""
TwitchPlays_VirtualGamepad.py

Wraps a single virtual Xbox 360 controller (via vgamepad + the ViGEmBus
driver) so chat commands can control a game/emulator without ever touching
the real keyboard or mouse. This is what keeps the rest of the computer free
to use normally while the bot is running.

You should not need to modify this file -- import it from
TwitchPlays_TEMPLATE.py and call the functions below.

Requires: `pip install vgamepad` and the ViGEmBus driver installed
(https://github.com/ViGEm/ViGEmBus/releases). Windows only.
"""

import time
import threading
import vgamepad as vg

# A single shared virtual controller. Every chat command that reaches this
# module presses/releases buttons on this same virtual device, which is what
# the emulator should be configured to read as "Player 1" (or whichever
# player you bind it to).
gamepad = vg.VX360Gamepad()

# All reads/writes to the gamepad's report go through this lock. Chat
# commands are processed concurrently (via the thread pool in the main
# script), but the underlying controller report is a single shared object --
# without this lock, two threads updating it at the same time can corrupt
# each other's button state.
_lock = threading.Lock()

def HoldButton(button):
    """Presses and holds a button down (does not release it)."""
    with _lock:
        gamepad.press_button(button=button)
        gamepad.update()

def ReleaseButton(button):
    """Releases a previously held button."""
    with _lock:
        gamepad.release_button(button=button)
        gamepad.update()

def HoldAndReleaseButton(button, seconds):
    """Holds a button down for `seconds`, then releases it. This is the
    equivalent of the old HoldAndReleaseKey() from keyboard emulation."""
    HoldButton(button)
    time.sleep(seconds)
    ReleaseButton(button)

def SetLeftStick(x, y):
    """
    Sets the left analog stick position. x and y each range from -32768
    (full left / full down) to 32767 (full right / full up). (0, 0) is
    centered.
    """
    with _lock:
        gamepad.left_joystick(x_value=x, y_value=y)
        gamepad.update()

def SetRightStick(x, y):
    """Same as SetLeftStick, but for the right analog stick."""
    with _lock:
        gamepad.right_joystick(x_value=x, y_value=y)
        gamepad.update()

def SetTrigger(side, value):
    """
    Sets a trigger's pressure. side is 'left' or 'right'. value ranges from
    0 (not pressed) to 255 (fully pressed).
    """
    with _lock:
        if side == 'left':
            gamepad.left_trigger(value=value)
        else:
            gamepad.right_trigger(value=value)
        gamepad.update()

def ResetGamepad():
    """
    Releases every button and centers all sticks/triggers. Call this before
    the script exits so the controller doesn't get "stuck" mid-press if the
    program is closed abruptly while a button is being held.
    """
    with _lock:
        gamepad.reset()
        gamepad.update()
