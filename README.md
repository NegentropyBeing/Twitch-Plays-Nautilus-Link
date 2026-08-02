# TwitchPlays: control-credit & mayhem

Two Twitch-chat-controlled game bots, built on top of DougDoug's original
TwitchPlays template. Chat commands are sent to a **virtual game
controller** rather than emulating the real keyboard/mouse, so the computer
running the bot stays completely free for normal use while it's running --
nothing gets typed into whatever window happens to be focused.

There are two variants, for two different styles of chat-controlled play:

## `control-credit`
- **3 teams** (A, B, C).
- Team A can send commands at any time. Every 7 commands Team A sends, one
  "turn credit" is banked for the opposing side -- either Team B or Team C
  can spend it, whichever speaks up first.
- All teams share **one** virtual controller.
- Good for a structured, turn-respecting "chat vs chat" format.

## `mayhem`
- **Up to 8 teams** (A through H).
- No turn system at all -- anyone registered to a team can send a command
  the instant they type it.
- **Each team gets its own independent virtual controller.**
- Good for total, simultaneous, many-sided chaos (as long as your
  game/emulator actually supports that many players).

Both variants support:
- A **competitors list** -- only registered usernames can ever trigger a
  command, so general chat can talk freely without accidentally doing
  anything.
- **Live roster editing** -- admins (the broadcaster, by default) can add
  competitors and assign them to teams mid-stream via chat commands
  (`!addcompetitor`, `!addteam`), no restart required.

---

## Requirements

- **Windows** (the virtual controller approach relies on the ViGEmBus
  driver, which is Windows-only).
- **Python 3.9+**
- An emulator or game that accepts controller input (e.g. BizHawk,
  RetroArch).

## Installing dependencies

1. Install [Python 3.9+](https://www.python.org/downloads/) (check "Add
   Python to PATH" during setup).
2. Install the [ViGEmBus driver](https://github.com/ViGEm/ViGEmBus/releases)
   -- download the `.msi`, right-click it and **Run as administrator**.
   Reboot afterward if prompted.
3. Install the Python packages:
   ```
   python -m pip install vgamepad requests keyboard
   ```
4. Verify the setup works using `test_vgamepad.py` (see below), and confirm
   the controller(s) show up in Windows' game controller list (`joy.cpl`).

## Testing your setup with `test_vgamepad.py`

Before running either bot for real, use `test_vgamepad.py` to confirm
ViGEmBus/vgamepad are working and to get a feel for how virtual controllers
behave -- no Twitch connection needed.

```
python test_vgamepad.py
```

It's interactive: it asks how many virtual controllers to create, then asks
each one for a comma-separated button sequence to play. Example:

```
How many controllers do you want to queue this round? 2
Controller 1 sequence: a, b, up, up, down, down
Controller 2 sequence: a, up, up, up, left, left, left, left
```

- All controllers run their sequence **at the same time** (each one plays
  its own sequence in order; different controllers don't wait on each
  other).
- Once every controller's sequence finishes, it asks you for the next
  round, so you can queue up a new set of sequences without restarting the
  script.
- Recognized button names: `up`, `down`, `left`, `right`, `a`, `b`, `x`,
  `y`, `start`, `select`, `l`, `r` -- same set used in `COMMAND_MAP`.
- Press **Ctrl+C** at any prompt to stop everything and reset all
  controllers cleanly.
- Note: more than 4 controllers still show up fine in `joy.cpl`, but games
  using the XInput API directly will only ever recognize the first 4 --
  same limitation covered in the `mayhem` section above.

## Running

```
python control-credit.py
```
or
```
python mayhem.py
```

Each script will prompt you (in the terminal) for:
1. The full list of competitors.
2. Usernames for each team.
3. Any additional admins who can add players live.

Then it counts down 5 seconds (switch to your game/emulator during this
window) before connecting to chat.

Edit `TWITCH_CHANNEL` near the top of either script before running, and
adjust `COMMAND_MAP` to match whatever buttons make sense for your game.

## Command list

These are the default chat commands in `COMMAND_MAP`, identical in both
scripts (only the underlying controller type differs internally):

| Chat command | Button        |
|--------------|---------------|
| `up`         | D-pad Up      |
| `down`       | D-pad Down    |
| `left`       | D-pad Left    |
| `right`      | D-pad Right   |
| `a`          | A / Cross     |
| `b`          | B / Circle    |
| `x`          | X / Square    |
| `y`          | Y / Triangle  |
| `start`      | Start/Options |
| `select`     | Select/Share  |
| `l`          | Left shoulder |
| `r`          | Right shoulder|

Edit `COMMAND_MAP` in either script to add, remove, or rename commands.
Only registered competitors on a team can trigger these -- everyone else's
identical text is just ignored.

### Repeating a command (getting around Twitch's duplicate-message lock)

Twitch mutes a user's identical repeated message for about 30 seconds. To
work around this, both scripts strip trailing dots before matching a
command -- so if you need to send the same command again right away, just
add a period (or a few):

```
a
a.
a..
a...
```

All four are treated as the exact same `a` command. This applies to every
entry in `COMMAND_MAP` automatically, no extra configuration needed.

## Adding someone to a team (admin only, live via chat)

Both bots support the same two admin commands, typed directly into chat by
the broadcaster (or anyone else listed in `ADMIN_USERS`):

**Register someone as a competitor** (without putting them on a team yet):
```
!addcompetitor username
```
or several at once:
```
!addcompetitor username1; username2; username3
```

**Add someone straight onto a team** (also registers them as a competitor
automatically, if they weren't already):
```
!addteam <letter> username
```
or several at once:
```
!addteam <letter> username1; username2
```

- In **`control-credit`**, `<letter>` must be `A`, `B`, or `C`.
- In **`mayhem`**, `<letter>` can be any of `A` through `H`.

Example, adding two people to Team B in `mayhem`:
```
!addteam B goblin_king; peter_parker
```

**Grant admin rights to someone else** (only an existing admin can do this
-- a regular viewer typing this command has no effect):
```
!addadmin username
```
or several at once:
```
!addadmin username1; username2
```

Anything that isn't sent by an admin, or doesn't match one of these
formats, is just treated as a normal (ignored, if not a recognized game
command) chat message.

## Ending the bot

Press **Shift+Backspace** in the terminal running the script.

---

## Credits

This project is a fork/evolution of **DougDoug's TwitchPlays template**,
itself originally based on:

- **Wituz** -- original ["Twitch Plays" tutorial](http://www.wituz.com/make-your-own-twitch-plays-stream.html)
- **DougDoug** -- the TwitchPlays template this repo builds on
- **DDarknut** -- added YouTube chat support
- **Ottomated** -- helped with the YouTube side of things

The chat-connection code (`TwitchPlays_Connection.py`) and the optional
legacy keyboard-emulation module (`TwitchPlays_KeyCodes.py`) descend
directly from that original project. The team system, live roster editing,
and virtual-controller-based input (both the single-controller and
8-controller versions) are new additions built on top of it.

Licensed under the MIT License (see `LICENSE`) -- original copyright
DougDoug, 2024.
