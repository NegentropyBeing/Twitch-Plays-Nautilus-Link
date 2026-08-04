import concurrent.futures
import threading
import random
import time
import keyboard
import vgamepad as vg
import TwitchPlays_Connection
import TwitchPlays_VirtualGamepad as vgp

##################### GAME VARIABLES #####################

# Replace this with your Twitch username. Must be all lowercase.
TWITCH_CHANNEL = 'negentropybeing' 

# If streaming on Youtube, set this to False
STREAMING_ON_TWITCH = True

# If you're streaming on Youtube, replace this with your Youtube's Channel ID
# Find this by clicking your Youtube profile pic -> Settings -> Advanced Settings
YOUTUBE_CHANNEL_ID = "YOUTUBE_CHANNEL_ID_HERE" 

# If you're using an Unlisted stream to test on Youtube, replace "None" below with your stream's URL in quotes.
# Otherwise you can leave this as "None"
YOUTUBE_STREAM_URL = None

##################### TEAM VARIABLES #####################

def parse_semicolon_list(raw):
    """
    Parses a semicolon-separated list of names, stripping quotes/whitespace
    and lowercasing everything (Twitch usernames are case-insensitive).
    """
    names = []
    for part in raw.split(';'):
        name = part.strip().strip('"\'').strip().lower()
        if name:
            names.append(name)
    return names

# First, define the full pool of people who are allowed to compete at all.
# Only usernames in this list can be assigned to a team below -- this keeps
# a random viewer from typing "left" and ending up on a team by accident.
print("First, enter the full list of competitors allowed to play.")
raw_competitors = input('Enter all competitor usernames, separated by ";" (e.g. "name1"; "name2"): ')
COMPETITORS = parse_semicolon_list(raw_competitors)
print(f"Competitors ({len(COMPETITORS)}): {COMPETITORS}")

def prompt_for_team(team_label):
    """
    Asks for a semicolon-separated list of usernames for one team, e.g.:
        "bob_212"; "Druid_human"; "Lover_in_a_bubble"
    Only names that are already in COMPETITORS are accepted onto the team --
    anything else is rejected with a warning and left out.
    """
    raw = input(f'Enter usernames for {team_label}, separated by ";" (e.g. "name1"; "name2"): ')
    names = []
    for name in parse_semicolon_list(raw):
        if name not in COMPETITORS:
            print(f'  Skipping "{name}" -- not in the competitors list.')
            continue
        names.append(name)
    return names

print("Now assign competitors to teams. Only names from the competitors list above will be accepted.")
TEAM_A = prompt_for_team('Team A')
TEAM_B = prompt_for_team('Team B')

print(f"Team A ({len(TEAM_A)}): {TEAM_A}")
print(f"Team B ({len(TEAM_B)}): {TEAM_B}")

# Admins can add new competitors/team members WHILE the bot is running, by
# typing special commands in chat (see handle_message below) -- no need to
# stop and restart the script. The broadcaster (TWITCH_CHANNEL) is always
# an admin; you can optionally name others here too.
raw_admins = input('Enter any additional admin usernames (besides yourself) who can add players live, separated by ";", or leave blank: ')
ADMIN_USERS = set(parse_semicolon_list(raw_admins))
ADMIN_USERS.add(TWITCH_CHANNEL.lower())
print(f"Admins who can add players live: {sorted(ADMIN_USERS)}")

# Guards changes to COMPETITORS/TEAM_A/TEAM_B/USER_TEAM, since these
# can now be edited live from a chat-handling thread while the main loop
# and other message-handling threads are also reading them.
roster_lock = threading.Lock()

def add_competitor(name):
    """Registers a new competitor (idempotent -- safe to call if they're
    already registered)."""
    name = name.strip().lower()
    if not name:
        return None
    with roster_lock:
        if name not in COMPETITORS:
            COMPETITORS.append(name)
    return name

def add_to_team(name, team_letter):
    """
    Registers `name` as a competitor if not already, and assigns them to
    team_letter ('A' or 'B'). Returns (success, message).
    """
    name = name.strip().lower()
    team_letter = team_letter.strip().upper()
    if not name:
        return False, "No username given."
    if team_letter not in ('A', 'B'):
        return False, f'Invalid team "{team_letter}" (must be A or B).'
    team_list = {'A': TEAM_A, 'B': TEAM_B}[team_letter]
    with roster_lock:
        if name not in COMPETITORS:
            COMPETITORS.append(name)
        USER_TEAM[name] = team_letter
        if name not in team_list:
            team_list.append(name)
    return True, f'Added "{name}" to Team {team_letter}.'

def add_admin(name):
    """
    Grants admin privileges to `name`. Only ever called after the caller
    has already been confirmed to be an existing admin (see handle_message)
    -- this function itself doesn't check that, so it should never be
    exposed to a non-admin-gated code path.
    """
    name = name.strip().lower()
    if not name:
        return None
    with roster_lock:
        ADMIN_USERS.add(name)
    return name

# Team A can always send commands, freely, at any time -- it never has to wait.
# Every MOVES_PER_BC_CREDIT commands that Team A sends, one "turn credit" is
# banked for Team B. It doesn't have to be spent immediately -- it just sits
# there banked until Team B uses it (or until MAX_BANKED_BC_CREDITS is hit,
# if you don't want them able to stockpile too many at once).
MOVES_PER_BC_CREDIT = 7
MAX_BANKED_BC_CREDITS = 1  # raise this if you want Team B able to stockpile multiple unused turns

# Lookup table built automatically from the rosters above: username -> team letter
USER_TEAM = {}
for _u in TEAM_A: USER_TEAM[_u] = 'A'
for _u in TEAM_B: USER_TEAM[_u] = 'B'

a_move_count = 0
bc_credits = 0
turn_lock = threading.Lock()

def try_take_turn(username):
    """
    Team A: always allowed. Every MOVES_PER_BC_CREDIT A-moves, banks one
    credit for Team B (capped at MAX_BANKED_BC_CREDITS).

    Team B: allowed only if a banked credit is available, in which case
    it's spent. If no credit is banked, the message is ignored.

    Anyone not on a team roster is ignored.
    This is thread-safe, so exactly one command gets through per available
    turn/credit even if several eligible messages arrive at the same time.
    """
    global a_move_count, bc_credits
    team = USER_TEAM.get(username)
    if team is None:
        return False
    with turn_lock:
        if team == 'A':
            a_move_count += 1
            if a_move_count % MOVES_PER_BC_CREDIT == 0:
                bc_credits = min(bc_credits + 1, MAX_BANKED_BC_CREDITS)
            return True
        elif team == 'B':
            if bc_credits > 0:
                bc_credits -= 1
                return True
            return False
        return False

##################### COMMAND MAP #####################

# Maps a chat command (lowercase, exact match) to a (button, hold_seconds)
# pair. HoldAndReleaseButton will press the button, wait hold_seconds, then
# release it -- this is a simple "tap" and covers most retro-game inputs.
# Add/remove entries here to match your emulator's control scheme.
COMMAND_MAP = {
    "up":     (vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,    0.2),
    "down":   (vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,  0.2),
    "left":   (vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,  0.2),
    "right":  (vg.XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT, 0.2),
    "a":      (vg.XUSB_BUTTON.XUSB_GAMEPAD_A,          0.15),
    "b":      (vg.XUSB_BUTTON.XUSB_GAMEPAD_B,          0.15),
    "x":      (vg.XUSB_BUTTON.XUSB_GAMEPAD_X,          0.15),
    "y":      (vg.XUSB_BUTTON.XUSB_GAMEPAD_Y,          0.15),
    "start":  (vg.XUSB_BUTTON.XUSB_GAMEPAD_START,      0.15),
    "select": (vg.XUSB_BUTTON.XUSB_GAMEPAD_BACK,       0.15),
    "l":      (vg.XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,  0.15),
    "r":      (vg.XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER, 0.15),
}

##################### MESSAGE QUEUE VARIABLES #####################

# MESSAGE_RATE controls how fast we process incoming Twitch Chat messages. It's the number of seconds it will take to handle all messages in the queue.
# This is used because Twitch delivers messages in "batches", rather than one at a time. So we process the messages over MESSAGE_RATE duration, rather than processing the entire batch at once.
# A smaller number means we go through the message queue faster, but we will run out of messages faster and activity might "stagnate" while waiting for a new batch. 
# A higher number means we go through the queue slower, and messages are more evenly spread out, but delay from the viewers' perspective is higher.
# You can set this to 0 to disable the queue and handle all messages immediately. However, then the wait before another "batch" of messages is more noticeable.
MESSAGE_RATE = 0.5
# MAX_QUEUE_LENGTH limits the number of commands that will be processed in a given "batch" of messages. 
# e.g. if you get a batch of 50 messages, you can choose to only process the first 10 of them and ignore the others.
# This is helpful for games where too many inputs at once can actually hinder the gameplay.
# Setting to ~50 is good for total chaos, ~5-10 is good for 2D platformers
MAX_QUEUE_LENGTH = 20
MAX_WORKERS = 100 # Maximum number of threads you can process at a time 

last_time = time.time()
message_queue = []
thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS)
active_tasks = []

##########################################################

# Count down before starting, so you have time to load up the game
countdown = 5
while countdown > 0:
    print(countdown)
    countdown -= 1
    time.sleep(1)

if STREAMING_ON_TWITCH:
    t = TwitchPlays_Connection.Twitch()
    t.twitch_connect(TWITCH_CHANNEL)
else:
    t = TwitchPlays_Connection.YouTube()
    t.youtube_connect(YOUTUBE_CHANNEL_ID, YOUTUBE_STREAM_URL)

def handle_message(message):
    try:
        msg = message['message'].strip()
        msg_lower = msg.lower()
        username = message['username'].lower()

        # Admin-only live roster commands. These let the broadcaster (or
        # anyone else in ADMIN_USERS) add players without restarting the
        # script. They're checked before anything else and never count as
        # a game command / turn.
        if username in ADMIN_USERS:
            if msg_lower == 'konami \U00013048':
                global bc_credits
                with turn_lock:
                    if bc_credits > 0:
                        bc_credits -= 1
                for button in (
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
                ):
                    vgp.HoldAndReleaseButton(button, 0.08)
                return

            if msg_lower.startswith('!addcompetitor '):
                raw_names = msg[len('!addcompetitor '):]
                names = [add_competitor(n) for n in parse_semicolon_list(raw_names)]
                print(f'[ADMIN] {username} added competitors: {names}')
                return

            if msg_lower.startswith('!addadmin '):
                # Only reachable by someone already in ADMIN_USERS, so a
                # regular viewer can never grant themselves (or anyone
                # else) admin rights this way.
                raw_names = msg[len('!addadmin '):]
                names = [add_admin(n) for n in parse_semicolon_list(raw_names)]
                print(f'[ADMIN] {username} added admins: {names}')
                return

            if msg_lower.startswith('!addteam '):
                rest = msg[len('!addteam '):].strip()
                split = rest.split(None, 1)  # "A bob_212; goblin" -> ["A", "bob_212; goblin"]
                if len(split) == 2:
                    team_letter, raw_names = split
                    for name in parse_semicolon_list(raw_names):
                        ok, info = add_to_team(name, team_letter)
                        print(f'[ADMIN] {username}: {info}')
                else:
                    print(f'[ADMIN] {username} sent a malformed !addteam command: "{msg}"')
                return

        # Twitch mutes identical repeated messages for ~30 seconds, so
        # players commonly work around it by appending "." (or "..", "...")
        # to an otherwise-repeated command. Stripping trailing dots here
        # means "a", "a.", "a.." all match the same COMMAND_MAP entry.
        msg = msg_lower.rstrip('.')

        # Only act on this message if it's this user's team's turn.
        # Ignores anyone not on TEAM_A/TEAM_B, and ignores messages from
        # Team B while it's not their turn yet.
        if not try_take_turn(username):
            return

        print(f"{username} ({USER_TEAM[username]}): {msg}")

        # Simple tap-style commands: look the message up in COMMAND_MAP and
        # press the matching button on the virtual controller for a fixed
        # duration. This covers most retro-game inputs (movement, jump,
        # attack, menu buttons, etc.).
        if msg in COMMAND_MAP:
            button, hold_time = COMMAND_MAP[msg]
            vgp.HoldAndReleaseButton(button, hold_time)
            return

        # For commands that need to be held indefinitely rather than
        # tapped (e.g. "run" while moving, until told to "stop"), handle
        # them explicitly here instead of through COMMAND_MAP:
        #
        # if msg == "run":
        #     vgp.HoldButton(vg.XUSB_BUTTON.XUSB_GAMEPAD_B)
        # elif msg == "stop":
        #     vgp.ReleaseButton(vg.XUSB_BUTTON.XUSB_GAMEPAD_B)
        #
        # For analog stick movement (e.g. an emulator core that reads
        # analog input instead of the D-pad):
        #
        # if msg == "look up":
        #     vgp.SetRightStick(0, 32767)

        # Anything not recognized above is silently ignored.

    except Exception as e:
        print("Encountered exception: " + str(e))


while True:

    active_tasks = [t for t in active_tasks if not t.done()]

    #Check for new messages
    try:
        new_messages = t.twitch_receive_messages();
    except Exception as e:
        # Defense-in-depth: even though Twitch.reconnect() now retries
        # internally instead of raising, this makes sure that ANY
        # unexpected error here (network-related or otherwise) can never
        # silently kill the whole bot. Worst case, this one loop iteration
        # is skipped and it tries again next time around.
        print(f'Error fetching messages, will retry: {e}')
        new_messages = []
        time.sleep(1)

    if new_messages:
        message_queue += new_messages; # New messages are added to the back of the queue
        message_queue = message_queue[-MAX_QUEUE_LENGTH:] # Shorten the queue to only the most recent X messages

    messages_to_handle = []
    if not message_queue:
        # No messages in the queue
        last_time = time.time()
    else:
        # Determine how many messages we should handle now
        r = 1 if MESSAGE_RATE == 0 else (time.time() - last_time) / MESSAGE_RATE
        n = int(r * len(message_queue))
        if n > 0:
            # Pop the messages we want off the front of the queue
            messages_to_handle = message_queue[0:n]
            del message_queue[0:n]
            last_time = time.time();

    # If user presses Shift+Backspace, automatically end the program
    if keyboard.is_pressed('shift+backspace'):
        vgp.ResetGamepad()
        exit()

    if not messages_to_handle:
        continue
    else:
        for message in messages_to_handle:
            if len(active_tasks) <= MAX_WORKERS:
                active_tasks.append(thread_pool.submit(handle_message, message))
            else:
                print(f'WARNING: active tasks ({len(active_tasks)}) exceeds number of workers ({MAX_WORKERS}). ({len(message_queue)} messages in the queue)')
 