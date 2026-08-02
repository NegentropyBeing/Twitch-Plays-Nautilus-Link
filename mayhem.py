import concurrent.futures
import threading
import random
import time
import keyboard
import vgamepad as vg
import TwitchPlays_Connection
import TwitchPlays_MultiGamepad as mgp

##################### GAME VARIABLES #####################

# Replace this with your Twitch username. Must be all lowercase.
TWITCH_CHANNEL = 'negentropybeing'

# If streaming on Youtube, set this to False
STREAMING_ON_TWITCH = True

# If you're streaming on Youtube, replace this with your Youtube's Channel ID
YOUTUBE_CHANNEL_ID = "YOUTUBE_CHANNEL_ID_HERE"

# If you're using an Unlisted stream to test on Youtube, put the URL here.
YOUTUBE_STREAM_URL = None

##################### TEAM VARIABLES #####################
#
# This version supports up to 8 teams (A-H), each with its own independent
# virtual controller. There is NO turn/credit system here -- any registered
# player on any team can send a command at any time. This is intentional:
# with up to 8 teams all talking at once, a turn-based queue would just add
# extra complexity on top of chat that's already going to be chaotic.

TEAM_LETTERS = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']

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
# Only usernames in this list can be assigned to a team below.
print("First, enter the full list of competitors allowed to play.")
raw_competitors = input('Enter all competitor usernames, separated by ";": ')
COMPETITORS = parse_semicolon_list(raw_competitors)
print(f"Competitors ({len(COMPETITORS)}): {COMPETITORS}")

# TEAMS holds each team's roster; USER_TEAM maps username -> team letter
# for fast lookup when a chat message comes in.
TEAMS = {letter: [] for letter in TEAM_LETTERS}
USER_TEAM = {}

print("Now assign competitors to teams (A-H). Leave a team blank if you're using fewer than 8.")
for letter in TEAM_LETTERS:
    raw = input(f'Enter usernames for Team {letter}, separated by ";" (or leave blank to skip this team): ')
    names = []
    for name in parse_semicolon_list(raw):
        if name not in COMPETITORS:
            print(f'  Skipping "{name}" -- not in the competitors list.')
            continue
        names.append(name)
        USER_TEAM[name] = letter
    TEAMS[letter] = names
    print(f"Team {letter} ({len(names)}): {names}")

# Admins can add new competitors/team members WHILE the bot is running, by
# typing special commands in chat (see handle_message below) -- no need to
# stop and restart the script. The broadcaster (TWITCH_CHANNEL) is always
# an admin; you can optionally name others here too.
raw_admins = input('Enter any additional admin usernames (besides yourself) who can add players live, separated by ";", or leave blank: ')
ADMIN_USERS = set(parse_semicolon_list(raw_admins))
ADMIN_USERS.add(TWITCH_CHANNEL.lower())
print(f"Admins who can add players live: {sorted(ADMIN_USERS)}")

# Guards changes to COMPETITORS/TEAMS/USER_TEAM, since these can be edited
# live from a chat-handling thread while other threads are also reading them.
roster_lock = threading.Lock()

def add_competitor(name):
    """Registers a new competitor (safe to call if already registered)."""
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
    team_letter (must be one of 'A' through 'H'). Returns (success, message).
    """
    name = name.strip().lower()
    team_letter = team_letter.strip().upper()
    if not name:
        return False, "No username given."
    if team_letter not in TEAM_LETTERS:
        return False, f'Invalid team "{team_letter}" (must be one of {", ".join(TEAM_LETTERS)}).'
    with roster_lock:
        if name not in COMPETITORS:
            COMPETITORS.append(name)
        USER_TEAM[name] = team_letter
        if name not in TEAMS[team_letter]:
            TEAMS[team_letter].append(name)
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

##################### COMMAND MAP #####################

# Maps a chat command (lowercase, exact match) to (kind, value, hold_seconds).
# kind is either "button" (a DS4_BUTTONS value) or "dpad" (a
# DS4_DPAD_DIRECTIONS value). Add/remove entries here to match your
# emulator's control scheme.
COMMAND_MAP = {
    "up":     ("dpad",   vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_NORTH, 0.2),
    "down":   ("dpad",   vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_SOUTH, 0.2),
    "left":   ("dpad",   vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_WEST,  0.2),
    "right":  ("dpad",   vg.DS4_DPAD_DIRECTIONS.DS4_BUTTON_DPAD_EAST,  0.2),
    "a":      ("button", vg.DS4_BUTTONS.DS4_BUTTON_CROSS,          0.15),
    "b":      ("button", vg.DS4_BUTTONS.DS4_BUTTON_CIRCLE,         0.15),
    "x":      ("button", vg.DS4_BUTTONS.DS4_BUTTON_SQUARE,         0.15),
    "y":      ("button", vg.DS4_BUTTONS.DS4_BUTTON_TRIANGLE,       0.15),
    "start":  ("button", vg.DS4_BUTTONS.DS4_BUTTON_OPTIONS,        0.15),
    "select": ("button", vg.DS4_BUTTONS.DS4_BUTTON_SHARE,          0.15),
    "l":      ("button", vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_LEFT,  0.15),
    "r":      ("button", vg.DS4_BUTTONS.DS4_BUTTON_SHOULDER_RIGHT, 0.15),
}

##################### MESSAGE QUEUE VARIABLES #####################

MESSAGE_RATE = 0.5
MAX_QUEUE_LENGTH = 20
MAX_WORKERS = 100

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

        # Admin-only live roster commands, checked before anything else.
        if username in ADMIN_USERS:
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

        # No turn system here -- just check whether this person is
        # registered to a team at all. If so, they can act immediately.
        team = USER_TEAM.get(username)
        if team is None:
            return  # not on any team roster -- ignored

        if msg not in COMMAND_MAP:
            return  # not a recognized command

        print(f"{username} (Team {team}): {msg}")

        kind, value, hold_time = COMMAND_MAP[msg]
        if kind == "button":
            mgp.HoldAndReleaseButton(team, value, hold_time)
        elif kind == "dpad":
            mgp.TapDPad(team, value, hold_time)

    except Exception as e:
        print("Encountered exception: " + str(e))


while True:

    active_tasks = [t for t in active_tasks if not t.done()]

    #Check for new messages
    try:
        new_messages = t.twitch_receive_messages();
    except Exception as e:
        # Defense-in-depth: ensures an unexpected error here can never
        # silently kill the whole bot. Twitch.reconnect() already retries
        # internally, but this is a second safety net regardless.
        print(f'Error fetching messages, will retry: {e}')
        new_messages = []
        time.sleep(1)

    if new_messages:
        message_queue += new_messages;
        message_queue = message_queue[-MAX_QUEUE_LENGTH:]

    messages_to_handle = []
    if not message_queue:
        last_time = time.time()
    else:
        r = 1 if MESSAGE_RATE == 0 else (time.time() - last_time) / MESSAGE_RATE
        n = int(r * len(message_queue))
        if n > 0:
            messages_to_handle = message_queue[0:n]
            del message_queue[0:n]
            last_time = time.time();

    # If user presses Shift+Backspace, automatically end the program
    if keyboard.is_pressed('shift+backspace'):
        mgp.ResetAll()
        exit()

    if not messages_to_handle:
        continue
    else:
        for message in messages_to_handle:
            if len(active_tasks) <= MAX_WORKERS:
                active_tasks.append(thread_pool.submit(handle_message, message))
            else:
                print(f'WARNING: active tasks ({len(active_tasks)}) exceeds number of workers ({MAX_WORKERS}). ({len(message_queue)} messages in the queue)')
