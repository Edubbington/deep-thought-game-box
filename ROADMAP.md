# Deep Thought: where things stand

Updated 21 November 2026, after a full review. The Software Spec is still the detailed
design; where this file is newer, this file wins.

## What she is for

A table-top game master: she teaches, guides, keeps track, talks and answers, and knows
each game we play well enough to be the most useful thing on the table. She has a voice
and a personality. Games get added over time, including board games off the shelf.

## Built, and tested on a Windows desktop

2,352 checks in thirteen test files, all passing on Python 3.11 on the PC (23 Nov 2026). The full set last passed on the Pi at 2,322; files changed since were rerun there.
She first ran on the real Pi on 22 November 2026; `software/PI_SETUP.md` ends with what that found.
`tests/test_pi_sim.py` runs the Pi backend and the real main loop on the PC with stand-in
pins, SPI bus and power-off command. It checks the code path, not the hardware.

| Piece | State |
|---|---|
| App shell, Home, Pick a game, Dice | Built |
| On-screen keyboard, Lookup over `content.db` | Built. Her own notes (120 sections) and every Magic card (35,892, with 80,928 rulings, from the real Scryfall download) are loaded on the PC. |
| Session engine: event log, undo, save after every event, resume, history | Built |
| Reminders per player and phase, first-player spinner, per-player clock | Built |
| Risk | Built |
| Any game (data-only scorekeeper) and games added from a web page | Built |
| 23 shelf games (Exploding Kittens, UNO, Stratego, Clank!, Chess and the rest) | Built as data-only games on 24 Nov 2026. 18 teach from memory, unchecked against a rulebook; 5 say plainly that their rules are not loaded. See CLAUDE.md. |
| Magic | Built |
| Kill Team | Built. Kill grades and starting command points need checking against the rulebook. |
| Kill Team secret Tac Ops | Built. Each player types theirs on their own phone; the table sees only "chosen" until it is revealed. |
| Warhammer 40,000 | Built. Scoring caps are placeholders: check against your mission deck. |
| Kill Team and 40k slow-play nudge | Built. One dry line and an amber ring, once per activation (90 s) or phase (4 min). Set under Menu. Off in Teach mode unless turned on. |
| 40k named secondaries | Built, on the box and from a player's phone. **The 23 names in `games/wh40k/secondaries.json` are from memory, with no caps. Check them against your deck.** |
| Teach as we play (Risk, Magic, shelf games) | Built. Steps come up as cards at the right moment and are read aloud. Kill Team and 40k already had their own Teach mode. |
| D&D: initiative tracker, character sheets, DM mode | Built |
| D&D DM tools: Improvise, Calendar, Treasure, roll tables, monsters from your books | Built. The dragon table is empty until you copy it in. Monster numbers are read off the page by pattern; never tried on a real book. |
| D&D characters: level 1 form, whole-sheet form, fillable PDF, photo of a paper sheet | Built. The web forms were run in a real browser. **The photo route has only met a stand-in for the cloud.** |
| Persona, question pipeline, rulings log | Built. Tested with a stand-in for the cloud. |
| Voice (Claude answers, speech out, speech in) | Claude answers and speech out run live (22 and 23 Nov 2026): 159 stock lines recorded, 93 test questions answered from the Pi. **Speech in (hold to talk) never run: the button does not work. Ethan has not yet heard her speak.** |
| Web pages: scoreboard, phones, characters, library upload, games, rulings, soundboard | Built, tested over a real local connection and in headless Edge |
| Table code on the web pages | Built. Everything but the scoreboard asks for the four-digit code shown under Settings, Phones. The QR code carries it. |
| One phone to a seat | Built. The first phone to open a seat keeps it for that game. Settings, Phones, Free the seats lets everyone sit down again. |
| Safe power-off, listening light, turn colour | Built (desktop stand-ins) |
| Pi hardware backend, service file, setup guide | Running on the Pi. Display, touch, ring, speaker, microphone and start at power-on seen working. **Button not working (switch circuit stuck closed). Wi-Fi slow with the screen lit.** No game played through on her yet. |

## The review of 21 November 2026

Every piece was read by a reviewer that had not written it, each fault was proved by
running it before it was fixed, and every fix has a check. Then the fixes were reviewed
again, twice. About ninety faults were fixed. The ones that would have been noticed at
the table:

- A double press on a menu, a map or a card could undo one or two events in the game
  underneath. A double press now belongs to the screen that was pressed, in every game.
  The old tests had missed it because they sent a double with no press before it, which
  the real button cannot do.
- An answer given in DM mode could be repeated to the players and listed on the Rulings page.
- Making or uploading a character could silently replace another with the same name.
- Undoing a long rest left the character files rested.
- A hidden enemy's save number, and later its name, could be seen or heard by players.
- A fault in any screen stopped the whole program. She now writes it to
  `data/errors.log`, says so, and carries on.
- Home read every saved game from the card each time it was drawn.
- On the Pi: a button edge lost to contact bounce could leave the button "held"; the
  microphone was assumed to be sound card 1; the program waited for Wi-Fi before starting.
- A mistake in `config.toml` stopped her starting. She now starts and says what is wrong.

## Still to do

Needs you:

1. Write the memory card and follow `software/PI_SETUP.md`. Tell me the first step that goes wrong.
2. Put keys in `software/config.toml` (`software/VOICE.md`) and choose her voice.
3. Load your books (`software/LIBRARY.md`). The Magic cards are done.
4. Check the numbers marked "check" in `games/killteam/rules.py` and `games/wh40k/rules.py`,
   and the secondary names in `games/wh40k/secondaries.json`.
5. Copy the dragon location table from the Icespire Peak booklet into the campaign file.
   The Tables screen in DM mode shows the exact file and field.
6. Decide whether names alone are acceptable in the repo: the campaign file holds the
   adventure's place and character names, and `secondaries.json` holds card names. There
   is no rules text in either.

Not proven, and cannot be until the box runs:

- Anything on the real Pi: the display, touch, ring, button, sound, microphone, and speed.
- Voice, the photo of a character sheet, and read-aloud against the live services.
- The book loader and the monster-number reader on your real books.

Known limits and judgement calls:

- The table code and the seat cookies travel unencrypted on the home Wi-Fi. They stop
  accidents, guests and a curious opponent, not someone determined.
- Whoever opens a seat first holds it. If the wrong phone took one, free the seats on the box.
- In Magic with the button set to pass whole turns, Teach gives one step per turn passed
  rather than one per phase.
- D&D: damage taken at 0 hit points that temporary hit points soak up completely still
  counts as a failed death save. Tell me if your table rules it the other way.
- D&D: a level-up, and "Level the party", cannot be undone on the box.
- D&D: a game resumed the very next evening goes into the previous night's log entry
  (so that a night running past midnight stays one session).
- A double press that lands just after a phone has done something undoes nothing and
  says so, rather than guess which of the two to take back.

## Decisions made on 20 and 21 November 2026

- A small on-screen keyboard is allowed on the box, for short search terms and names.
- The button acts on a press at once. A double press takes that press back and undoes one more.
- A double press belongs to the screen that was pressed. If the press closed that screen,
  the double does nothing.
- The button lamp is always on, as wired. The ring carries "your move" and "listening".
- Development is on Python 3.11 in `software/.venv`, pygame 2.6.1.
- Deep Thought is "she".
- The web pages use Python's own `http.server`, not Flask: one fewer thing to install on the Pi.
- Claude answers use the `anthropic` package and `claude-haiku-5-5` by default (set in `config.toml`).
- Speech in and out use an OpenAI-style speech service, set in `config.toml`. The provider is your choice.
- Teach as we play is Off unless chosen at Set up.
- A DM table roll (where the dragon is) stays in the DM's log but is left out of the recap read to the table.
- Everything she says on a DM screen is shown on the box only: not spoken, and not sent to the web pages.
- A question asked in DM mode with D&D on the table is kept as a DM ruling. Players never see it.
- Tac Op names are typed by the player from their own card. None are stored in the repo.
- Books sent from a phone are limited to 100 MB. Bigger ones go in by the folder way in `LIBRARY.md`.
- The program starts without waiting for Wi-Fi, and works out its address when asked.
