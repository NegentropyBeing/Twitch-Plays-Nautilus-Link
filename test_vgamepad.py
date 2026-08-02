"""
Interactive virtual controller queue tester.

Lets you type a button sequence for each of several virtual Xbox 360
controllers, runs all of them at the same time (each controller's own
sequence plays back-to-back, but different controllers run concurrently
with each other), then asks you to queue up another round.

Example session:

    How many controllers do you want to queue this round? 2
    Controller 1 sequence (comma-separated, e.g. a, b, up, up): a, b, up, up, down, down
    Controller 2 sequence (comma-separated, e.g. a, b, up, up): a, up, up, up, left, left, left, left

Recognized button names: up, down, left, right, a, b, x, y, start, select, l, r

While a round is running, open joy.cpl (Win+R -> joy.cpl) to watch each
virtual controller react. Press Ctrl+C at any prompt to quit -- all
controllers are reset (nothing left held down) before the script exits.
"""

import time
import threading
import vgamepad as vg

BUTTON_MAP = {
    "up":     vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
    "down":   vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
    "left":   vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
    "right":  vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
    "a":      vg.XUSB_BUTTON.XUSB_GAMEPAD_A,
    "b":      vg.XUSB_BUTTON.XUSB_GAMEPAD_B,
    "x":      vg.XUSB_BUTTON.XUSB_GAMEPAD_X,
    "y":      vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,
    "start":  vg.XUSB_BUTTON.XUSB_GAMEPAD_START,
    "select": vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,
    "l":      vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
    "r":      vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
}

PRESS_SECONDS = 0.15  # how long each button is held down
GAP_SECONDS = 0.05    # pause between one button releasing and the next pressing

def parse_sequence(raw, controller_index):
    """Turns 'a, b, up, up' into [(name, button_constant), ...], skipping
    and warning about anything not in BUTTON_MAP."""
    sequence = []
    for name in [n.strip().lower() for n in raw.split(',') if n.strip()]:
        if name in BUTTON_MAP:
            sequence.append((name, BUTTON_MAP[name]))
        else:
            print(f'  Controller {controller_index}: skipping unrecognized button "{name}".')
    return sequence

def run_controller_queue(controller_index, gamepad, sequence):
    """Plays one controller's full sequence, in order, on its own thread."""
    for name, button in sequence:
        print(f"[Controller {controller_index}] {name}")
        gamepad.press_button(button=button)
        gamepad.update()
        time.sleep(PRESS_SECONDS)
        gamepad.release_button(button=button)
        gamepad.update()
        time.sleep(GAP_SECONDS)
    print(f"[Controller {controller_index}] finished ({len(sequence)} inputs).")

def main():
    print(__doc__)
    gamepads = {}  # controller_index -> VX360Gamepad, reused across rounds

    try:
        while True:
            raw_count = input("How many controllers do you want to queue this round? ").strip()
            try:
                count = int(raw_count)
            except ValueError:
                print("Please enter a number.\n")
                continue
            if count < 1:
                print("Enter at least 1.\n")
                continue
            if count > 4:
                print(f"Note: XInput itself only exposes 4 controller slots to games that use\n"
                      f"the XInput API directly. joy.cpl will still show all {count} controllers,\n"
                      f"but some games may only recognize the first 4.\n")

            # Phase 1: gather every controller's sequence first. No virtual
            # controller is created yet -- this loop only asks questions and
            # parses text, so nothing shows up to Windows/games mid-round.
            queues = {}
            for i in range(1, count + 1):
                raw = input(f"Controller {i} sequence (comma-separated, e.g. a, b, up, up): ")
                queues[i] = parse_sequence(raw, i)

            # Phase 2: now that the whole round's plan is known, create any
            # controllers that don't already exist, all at once, and then
            # run everything.
            print("\nAll sequences collected. Creating/updating controllers and running now "
                  "(each one plays its own sequence in order, but all controllers run at "
                  "the same time)...\n")

            for i in queues:
                if i not in gamepads:
                    gamepads[i] = vg.VX360Gamepad()

            threads = [
                threading.Thread(target=run_controller_queue, args=(i, gamepads[i], seq))
                for i, seq in queues.items()
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            print("\nAll controllers finished this round.\n")

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        for gp in gamepads.values():
            gp.reset()
            gp.update()
        print("All controllers reset -- nothing left held down. Done.")

if __name__ == "__main__":
    main()
