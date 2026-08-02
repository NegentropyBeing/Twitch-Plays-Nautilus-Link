"""
Phase 2 test script: verifies ViGEmBus + vgamepad are working correctly by
continuously replaying the Konami Code on a virtual Xbox 360 controller.

What this does:
1. Creates a virtual Xbox 360 controller (this is what should appear in
   Windows' game controller list / joy.cpl while this script runs).
2. Repeats the Konami Code sequence -- Up, Up, Down, Down, Left, Right,
   Left, Right, B, A -- back-to-back, forever, with no pause or gap
   between one full sequence ending and the next one starting.

How to use it:
- Run this script: python test_vgamepad.py
- While it's running, press Win+R, type joy.cpl, hit enter.
- You should see a new "Controller (XBOX 360 For Windows)" entry appear.
- Open its Properties -> "Test" tab (button/stick test view) and watch the
  D-pad and B/A buttons cycle through the sequence continuously.
- Press Ctrl+C in the terminal to stop. The controller is reset (all
  buttons released) before the script exits, so nothing is left "stuck"
  held down.

If nothing shows up in joy.cpl at all: ViGEmBus isn't installed/running
correctly -- reinstall the driver and check Device Manager for a
"Virtual Gamepad Emulation Bus" entry under System devices before trying
this script again.
"""

import time
import vgamepad as vg

# How long each input is held down before releasing it. Short enough to
# keep the sequence moving quickly, but long enough that a game/emulator
# reliably registers each press as a distinct input rather than missing it.
PRESS_SECONDS = 0.08

# The classic Konami Code, as a sequence of button constants. On an Xbox
# 360-style controller, D-pad directions are just regular individual
# buttons (unlike the DualShock 4's single hat-switch D-pad used in
# mayhem.py), so every entry here is pressed and released the same way.
KONAMI_CODE = [
    vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
    vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
    vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
    vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
    vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
    vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
    vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
    vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
    vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
    vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
]

def press_and_release(gamepad, button):
    """Presses `button`, holds it for PRESS_SECONDS, then releases it."""
    gamepad.press_button(button=button)
    gamepad.update()
    time.sleep(PRESS_SECONDS)
    gamepad.release_button(button=button)
    gamepad.update()

def main():
    print("Creating virtual Xbox 360 controller...")
    gamepad = vg.VX360Gamepad()
    print("Created. Open joy.cpl now to watch the Konami Code repeat.")
    print("Press Ctrl+C to stop.\n")
    time.sleep(2)

    sequence_count = 0
    try:
        while True:
            sequence_count += 1
            print(f"--- Sequence #{sequence_count} ---")
            for button in KONAMI_CODE:
                press_and_release(gamepad, button)
            # No pause here -- the next sequence starts immediately, so the
            # whole thing repeats without interruption for as long as the
            # script runs.
    except KeyboardInterrupt:
        print(f"\nStopped after {sequence_count} sequence(s).")
    finally:
        gamepad.reset()
        gamepad.update()
        print("Controller reset -- nothing left held down. Done.")

if __name__ == "__main__":
    main()
