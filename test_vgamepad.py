"""
Interactive virtual controller queue tester.

Lets you type a button sequence for each of several virtual Xbox 360
controllers, choose a delay before anything runs, choose whether all
controllers act at the same time or one after another, then asks you to
queue up another round once it's done.

Example session:

    How many controllers do you want to queue this round? 3
    Controller 1 sequence: b, up (repeat, infinite)
    Controller 2 sequence: b, up (repeat, 3x)
    Controller 3 sequence: a, down (repeat, infinite)
    Delay before executing (seconds, 0 for none): 30
    Run controllers simultaneously or in sequence? (simultaneous/sequential): simultaneous

- Controller 1 and 3 will keep repeating their sequence forever, in the
  background, while the script goes on to ask you for the next round.
- Controller 2 will run its sequence exactly 3 times, and (in simultaneous
  mode) the script waits for it to finish before asking for the next round.
- Leave a controller's line with no repeat directive (just "a, b, up") to
  run it once, same as before.
- Leave the line completely blank for a controller that already has a
  running sequence to stop it. Queuing a brand-new sequence for a
  controller that's already repeating also replaces (stops, then starts)
  whatever it was doing before.

Delay: how long to wait, after the whole round is planned out, before
anything actually starts running. Useful for switching over to your
game/emulator window first.

Simultaneous vs sequential:
- Simultaneous: every controller starts at the same time.
- Sequential: controller 1 runs first, then controller 2, and so on.
  A controller with a fixed repeat count is waited on before moving to the
  next one; a controller set to repeat infinitely can't be waited on (it
  never finishes), so it just starts running in the background and the
  script immediately moves on to the next controller in line.

Every round is planned out completely first (all prompts answered, nothing
touched yet), and only once the whole round's plan -- including the delay
and the simultaneous/sequential choice -- is known does the script create,
start, or stop any actual virtual controller. This avoids leaving a
half-set-up controller sitting around while you're still answering prompts
for the rest of the round.

Recognized button names: up, down, left, right, a, b, x, y, start, select, l, r

While anything is running, open joy.cpl (Win+R -> joy.cpl) to watch each
virtual controller react. Press Ctrl+C at any prompt to quit -- everything
still running is stopped and every controller is reset (nothing left held
down) before the script exits.
"""

import re
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

# Matches an optional trailing "(repeat, infinite)" or "(repeat, 3x)" /
# "(repeat, 3)" directive.
REPEAT_PATTERN = re.compile(r'\(\s*repeat\s*,\s*(infinite|\d+)\s*x?\s*\)\s*$', re.IGNORECASE)

def parse_repeat(raw):
    """
    Splits off an optional repeat directive from the end of the raw input.
    Returns (sequence_text, repeat_count) where repeat_count is:
      - None, meaning "repeat forever" (infinite)
      - an int >= 1, meaning "run this many times"
      - 1 by default, if no directive was given at all
    """
    match = REPEAT_PATTERN.search(raw)
    if not match:
        return raw, 1
    sequence_text = raw[:match.start()].strip()
    token = match.group(1).lower()
    if token == 'infinite':
        return sequence_text, None
    return sequence_text, int(token)

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

def run_controller_queue(controller_index, gamepad, sequence, repeat_count, stop_event):
    """
    Plays one controller's sequence, repeated either `repeat_count` times
    or forever (if repeat_count is None), on its own thread. Checks
    stop_event between every single button press so it can be interrupted
    promptly rather than only between full repetitions.
    """
    rep = 0
    while not stop_event.is_set():
        rep += 1
        for name, button in sequence:
            if stop_event.is_set():
                break
            label = f"rep {rep}" if repeat_count is None else f"rep {rep}/{repeat_count}"
            print(f"[Controller {controller_index}] ({label}) {name}")
            gamepad.press_button(button=button)
            gamepad.update()
            time.sleep(PRESS_SECONDS)
            gamepad.release_button(button=button)
            gamepad.update()
            time.sleep(GAP_SECONDS)
        if repeat_count is not None and rep >= repeat_count:
            break
    print(f"[Controller {controller_index}] stopped after {rep} repetition(s).")

def ask_delay_seconds():
    while True:
        raw = input("Delay before executing (seconds, 0 for none): ").strip()
        if raw == "":
            return 0.0
        try:
            value = float(raw)
        except ValueError:
            print("Please enter a number (e.g. 0, 5, 30).\n")
            continue
        if value < 0:
            print("Enter 0 or a positive number.\n")
            continue
        return value

def ask_execution_mode():
    while True:
        raw = input("Run controllers simultaneously or in sequence? (simultaneous/sequential): ").strip().lower()
        if raw in ("simultaneous", "sim", "s"):
            return "simultaneous"
        if raw in ("sequential", "seq", "q"):
            return "sequential"
        print('Please answer "simultaneous" or "sequential".\n')

def main():
    print(__doc__)
    gamepads = {}            # controller_index -> VX360Gamepad, reused across rounds
    controller_threads = {}  # controller_index -> (thread, stop_event)

    def stop_controller(i):
        """Signals and waits for controller i's current action (if any) to stop."""
        if i in controller_threads:
            thread, stop_event = controller_threads[i]
            stop_event.set()
            thread.join()
            del controller_threads[i]

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

            # Phase 1: gather EVERYTHING for this round first -- what each
            # controller should do (or whether it should stop), the delay
            # before running, and simultaneous vs sequential. Nothing is
            # created, started, or stopped yet; this phase only asks
            # questions and parses text.
            plans = {}  # controller_index -> None (stop) or (sequence, repeat_count)
            for i in range(1, count + 1):
                raw = input(
                    f'Controller {i} sequence (e.g. "a, b, up, up" or '
                    f'"b, up (repeat, infinite)", blank to stop it): '
                )
                if not raw.strip():
                    plans[i] = None
                    continue
                sequence_text, repeat_count = parse_repeat(raw)
                sequence = parse_sequence(sequence_text, i)
                if not sequence:
                    print(f"  Controller {i} has no valid buttons -- skipping.")
                    plans[i] = None
                    continue
                plans[i] = (sequence, repeat_count)

            delay_seconds = ask_delay_seconds()
            mode = ask_execution_mode()

            # Phase 2: the whole round's plan -- including delay and mode --
            # is now known. Only from here on do we actually wait, stop,
            # create, or start any controller.
            if delay_seconds > 0:
                print(f"\nWaiting {delay_seconds:g} second(s) before executing "
                      f"(switch to your game/emulator window now if needed)...")
                time.sleep(delay_seconds)

            print(f"\nApplying this round's plan now, {mode} "
                  f"(controllers set to repeat run in the background; others "
                  f"are waited on before the next round)...\n")

            def start_controller(i, sequence, repeat_count):
                if i not in gamepads:
                    gamepads[i] = vg.VX360Gamepad()
                stop_event = threading.Event()
                thread = threading.Thread(
                    target=run_controller_queue,
                    args=(i, gamepads[i], sequence, repeat_count, stop_event),
                    daemon=True,
                )
                controller_threads[i] = (thread, stop_event)
                thread.start()
                return thread

            finite_threads_this_round = []

            if mode == "simultaneous":
                for i, plan in plans.items():
                    stop_controller(i)  # replace/stop whatever it was doing
                    if plan is None:
                        print(f"  Controller {i}: idle.")
                        continue
                    sequence, repeat_count = plan
                    thread = start_controller(i, sequence, repeat_count)
                    if repeat_count is None:
                        print(f"  Controller {i} is now repeating indefinitely in the background.")
                    else:
                        finite_threads_this_round.append(thread)
                for t in finite_threads_this_round:
                    t.join()

            else:  # sequential
                for i, plan in plans.items():
                    stop_controller(i)
                    if plan is None:
                        print(f"  Controller {i}: idle.")
                        continue
                    sequence, repeat_count = plan
                    thread = start_controller(i, sequence, repeat_count)
                    if repeat_count is None:
                        print(f"  Controller {i} is now repeating indefinitely in the background "
                              f"-- moving on to the next controller immediately.")
                    else:
                        print(f"  Controller {i} running -- waiting for it to finish before "
                              f"starting the next controller...")
                        thread.join()

            print("\nReady for the next round.\n")

    except KeyboardInterrupt:
        print("\nStopping everything...")
    finally:
        for i in list(controller_threads.keys()):
            stop_controller(i)
        for gp in gamepads.values():
            gp.reset()
            gp.update()
        print("All controllers reset -- nothing left held down. Done.")

if __name__ == "__main__":
    main()
