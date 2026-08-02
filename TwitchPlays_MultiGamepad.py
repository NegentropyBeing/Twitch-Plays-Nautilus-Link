"""
TwitchPlays_MultiGamepad.py

Creates one independent virtual controller PER TEAM (up to 8 teams, A-H),
so each team's chat commands only ever affect their own controller.

Why DualShock 4 instead of Xbox 360 controllers here: Windows' XInput API
(the one Xbox-style virtual controllers use) is capped at 4 simultaneous
controller slots -- that's a limitation of XInput itself, not of vgamepad
or ViGEmBus. To support up to 8 independent controllers, this module uses
vgamepad's DualShock 4 (DS4) virtual controller type instead, since DS4
pads are exposed through a generic HID interface that isn't limited to 4.

Whether your game/emulator can actually use all 8 depends on it supporting
that many players in the first place (e.g. a multitap-style peripheral for
a classic console, or a game/emulator core built for many local players).
This module only handles the controller side -- binding each one to a
player slot happens in the game/emulator's own controller settings, the
same way as with a single controller.
"""

import time
import threading
import vgamepad as vg

TEAM_LETTERS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']

# One independent DS4 controller and lock per possible team letter. Teams
# you don't end up using just sit idle -- no harm in creating all 8 upfront.
_gamepads = {letter: vg.VDS4Gamepad() for letter in TEAM_LETTERS}
_locks = {letter: threading.Lock() for letter in TEAM_LETTERS}

def HoldButton(team_letter, button):
    """Presses and holds a button on the given team's controller."""
    gp = _gamepads[team_letter]
    with _locks[team_letter]:
        gp.press_button(button=button)
        gp.update()

def ReleaseButton(team_letter, button):
    """Releases a previously held button on the given team's controller."""
    gp = _gamepads[team_letter]
    with _locks[team_letter]:
        gp.release_button(button=button)
        gp.update()

def HoldAndReleaseButton(team_letter, button, seconds):
    """Holds a button for `seconds`, then releases it."""
    HoldButton(team_letter, button)
    time.sleep(seconds)
    ReleaseButton(team_letter, button)

def SetDPad(team_letter, direction):
    """
    Sets the D-pad to a direction from vg.DS4_DPAD_DIRECTIONS (e.g.
    DS4_BUTTON_DPAD_NORTH). Use DS4_BUTTON_DPAD_NONE to center/release it.

    Unlike XInput, DS4's D-pad is a single "hat switch" value rather than
    separate up/down/left/right bits, so only one direction (or none) can
    be active at a time -- setting a new direction replaces the old one.
    """
    gp = _gamepads[team_letter]
    with _locks[team_letter]:
        gp.directional_pad(direction=direction)
        gp.update()

def TapDPad(team_letter, direction, seconds):
    """Holds a D-pad direction for `seconds`, then centers it."""
    SetDPad(team_letter, direction)
    time.sleep(seconds)
    SetDPad(team_letter, vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NONE)

def SetLeftStick(team_letter, x, y):
    """
    Sets the left analog stick position for the given team's controller.
    x and y each range 0-255 (DS4 uses unsigned values, unlike XInput's
    signed range) -- 128 is centered on each axis.
    """
    gp = _gamepads[team_letter]
    with _locks[team_letter]:
        gp.left_joystick(x_value=x, y_value=y)
        gp.update()

def SetRightStick(team_letter, x, y):
    """Same as SetLeftStick, but for the right analog stick."""
    gp = _gamepads[team_letter]
    with _locks[team_letter]:
        gp.right_joystick(x_value=x, y_value=y)
        gp.update()

def ResetTeam(team_letter):
    """Releases everything and centers all sticks/D-pad for one team's controller."""
    gp = _gamepads[team_letter]
    with _locks[team_letter]:
        gp.reset()
        gp.update()

def ResetAll():
    """Resets every team's controller. Call this before the script exits."""
    for letter in TEAM_LETTERS:
        ResetTeam(letter)
