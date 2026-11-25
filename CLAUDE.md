# Deep Thought game night box

A tabletop companion shaped like Deep Thought. It sits on the table on game night, teaches
new players, tracks turns and scores, answers rules questions out loud in a weary
super-computer voice, and looks things up. Games: Warhammer 40,000 Kill Team, Warhammer
40,000, Dungeons & Dragons, Magic: The Gathering.

Owner: Ethan. He builds his own tools in Python and is comfortable in a terminal. He has
not soldered or done electronics in years, so anything about hardware should be spelled out.

## How Ethan wants the work done

These came from real problems earlier in the project. Follow them.

1. **Measure, don't guess.** Before changing or sending any printed part, measure the STL
   that was actually printed, not the working model. Bad guesses cost filament and days.
2. **Say plainly what changed and what didn't.** Never say something was not changed when
   it was. If a new version differs from the last one anywhere, list where.
3. **Say what is tested and what is not.** "Passes on made-up test files, never run on the
   real thing" is a fine sentence. An untested claim presented as fact is not.
4. **Instructions for Ethan are picture-first and short.** One action per step. He said
   long steps are heavy and the pictures are what help.
5. **Keep the hardware facts in mind.** There is ONE button. The display is powered through
   its ribbon. The Pi is a Pi 2 (ARMv7, 1 GB RAM, no built-in Wi-Fi).
6. **No copyrighted rules text.** Nothing in this repo may contain text from paid rulebooks,
   codexes, D&D books or adventures. The box teaches in its own words. Source text comes
   only from files the owner loads himself: official free downloads and his own books.

## What exists right now

| Thing | State |
|---|---|
| Printed body (7 parts) | Designed and printed. Speaker mounted. Final assembly waiting on heat shrink. |
| Wiring | Soldered. Powered up 22 Nov 2026: display, touch, ring, amp, speaker and microphone work. The button did not work at first: its two green wires read as joined at the header (23 Nov 2026). The cause was a wiring mistake Ethan found and put right on 24 Nov 2026, not the switch; the first button is fine. A spare is fitted now and reads open at rest and closed when pressed, with clean presses and holds logged on GPIO 17. The strip across the top of the screen is the button too. |
| Assembly Guide | Written, current. `docs/text/Assembly Guide.txt`, pictures in `guide_images/`. |
| Knowledge Base | Written, 9 tabs. `docs/text/Knowledge Base - *.txt`. |
| Software Spec | Written, 16 sections. `docs/text/Software Spec.txt`. Read this before coding. |
| Screen mockups | 30 screens, 800x480. `mockups/project/*.dc.html`. Sized by calculation, never rendered. |
| `software/dt_content.py` | Built. 81 checks pass. The Magic download has run against the real Scryfall service; no real rulebook PDF yet. |
| `software/dt_characters.py` | Built. 84 checks pass. PDF import never run on a real sheet. |
| `software/campaigns/dragon-of-icespire-peak.json` | Built. Names and quest notes from memory, unchecked against the booklet. |
| The program that runs on the Pi | **Built, and running on the real Pi since 22 Nov 2026.** `software/deepthought/`: shell, engine, Lookup, six games (Kill Team, 40k, D&D, Magic, Risk, Any game), persona, voice, web pages (behind a four-digit table code, one phone to a seat), teach-as-we-play, D&D DM tools, Pi hardware backend. Reviewed in three rounds on 21 Nov 2026. All thirteen test files (2,967 checks on 24 Nov 2026) pass on Windows (Python 3.11); the full set last ran on the Pi at 2,322, and the files changed since were rerun there. She starts at power-on and shows Home; touch works. Claude answers run live from the Pi over plain HTTPS (no `anthropic` package there) and 159 stock lines are recorded in her voice. `tools/simulate.py` plays random tables through every game; `tools/scenarios.py` asks her 93 table questions for real and keeps the answers to read. **Not yet done on the Pi: a real game played by people, hold-to-talk. Her voice was chosen by ear on 23 Nov 2026 (`persona.SPEAKING`, shaped by `voicefx.py`; `tools/audition.py` plays candidates). Ethan found her too quiet for a table even at full scale; whether the present loudness is enough is not confirmed.** `ROADMAP.md` lists what is built, untested and missing; `software/PI_SETUP.md` ends with what the first real run found. |

Guides: `software/PLUGINS.md` (adding a game), `software/LIBRARY.md` (loading books),
`software/VOICE.md` (keys and her voice), `software/PI_SETUP.md` (first run on the Pi).
In this Git Bash, shell heredocs mangle backslashes and apostrophes: write files with the
file tools, not heredocs.
In tests, a double press is always sent as press then double: the button cannot send a double alone.
Faults at run time are written to `software/data/errors.log`.
The Pi is reached from the PC with `ssh -i ~/.ssh/deepthought_ed25519 deepthought@<the Pi's address>`
(passwordless sudo). The program lives in `~/deepthought` there and runs as `deepthought.service`.
Copy changed files with `tar -cf - <files> | ssh ... 'tar -xf - -C ~/deepthought'`, then
`sudo systemctl restart deepthought`. Never write 0 to the backlight (see `PI_SETUP.md`).
Ethan cannot remove the SD card or open the case once assembled: fix things over SSH.

Run it: `software/.venv/Scripts/python software/run.py` (space bar = the button, Esc quits,
`--shots DIR` saves every screen as a PNG). Deep Thought is "she". Risk is a launch game,
and more board games will be added over time: a game is a folder under
`software/deepthought/games/`.

## Hardware

- Raspberry Pi 2 Model B V1.1
- Hosyond 5" DSI capacitive touch display, 800x480 IPS. Powered through the DSI ribbon.
  Its 2-pin header is for a fan only.
- NS4168 I2S amplifier (same wiring as MAX98357A) and a small speaker
- 16-LED WS2812 ring under the translucent dome
- One 30 mm LED arcade button
- USB microphone, USB nano Wi-Fi adapter (MT7601U)
- 5 V 3 A supply through a 30 cm panel-mount micro-USB extension
- A Chromebook beside the table shows the shared scoreboard web page

The display is mounted with the backlight-switch edge at the bottom, so the picture is
upside down by default. Fix with `display_lcd_rotate=2` in config.txt, or
`video=DSI-1:800x480@60,rotate=180` in cmdline.txt, or flip it in the program.

### GPIO header, as wired

| Pin | Signal | Wire | Goes to |
|---|---|---|---|
| 2 | 5 V | red | Splice: LED ring 5 V, button lamp +, short stub |
| 4 | 5 V | red | Amp V |
| 9 | Ground | black | Amp G |
| 11 | GPIO 17 | green | Button switch |
| 12 | GPIO 18 | blue | Amp BCLK |
| 14 | Ground | black | LED ring ground |
| 19 | GPIO 10 (SPI MOSI) | green | LED ring data in |
| 20 | Ground | green | Button switch, other lead |
| 25 | Ground | grey | Button lamp - |
| 35 | GPIO 19 | green | Amp LRC |
| 40 | GPIO 21 | yellow | Amp DIN |

Pins 1 and 17 are empty. The button lamp is wired straight to 5 V, so it is always on;
software cannot switch it. Not confirmed from photos: which of two green wires is on pin 19
and which on pin 20. The first LED and button tests settle it.

### One-button controls

Press = next. Hold = talk (ask a question). Double press = undo. Same in every game.
Every game's play screen has Menu at the right of the bottom row: End game (End it records the result, Scrap it throws the game away) and Home (resume later).
A finger on the 60 px strip across the top of the screen is the button too (tap, hold, two taps).
A real button that is down when she starts is ignored until it has been seen up once.

## Software design in one page

Full detail is in `docs/text/Software Spec.txt`. Sections 15 and 16 are the newest and win
where they disagree with earlier sections.

- One Python process using pygame, full screen at 800x480. The Pi runs Python 3.13 (Raspberry Pi OS trixie);
  the PC venv is 3.11. Keep dependencies small: the Pi 2 is slow and has 1 GB of RAM.
- A game engine with one plugin per game: `killteam`, `wh40k`, `dnd`, `mtg`. Each plugin
  supplies setup questions, turn structure, scoring, its own screens, what the button does,
  and its trackers.
- A knowledge database (SQLite FTS) built from the Knowledge Base: the box's own words.
- `content.db`, built by `dt_content.py`: source text from free official downloads, the
  owner's own books, every Magic card and ruling, and the Magic rulebook.
- Voice: pre-generated persona lines for common moments; cloud speech-to-text and a cloud
  model for spoken questions, with a cache. A spoken question sends the question plus the
  top three library excerpts. DM-only material is sent only in DM mode.
- A small Flask server for the Chromebook scoreboard. The same server will serve a
  `/characters` page so players can create or upload D&D characters from a phone.
- D&D has a DM mode behind a four-digit code, a campaign file per campaign, and character
  files handled by `dt_characters.py`.

Build order agreed so far (Spec 15.6): wire Lookup to `content.db`; then the `mtg` plugin;
then `wh40k`; then `dnd` (initiative tracker first, DM mode second). Kill Team was the
first plugin specified and its screens are the reference design.

### Screen rules

- 800x480, dark. Ground `#0B0F14`, panel `#151C26`, raised panel `#1D2633`, line `#2F3B4D`,
  text `#EAF0F6`, dim text `#A9B8CA`. Players: `#6CB6FF`, `#FFA64D`, `#8FE3A0`, `#F29BD4`.
- Space Grotesk for headings and numbers, Inter for everything else.
- No text under 22 px. No button under 64 px tall. A 60 px strip across the top.
- Never rely on colour alone to show state.
- Typing is done on a phone or the Chromebook, not on the 5" screen.

## The shelf games (added 24 Nov 2026)

Twenty-three data-only games were added from photos of Ethan's shelf: a `game.json` and a
`teach.json` each, no code. Eighteen teach in her own words, **written from memory and not
checked against any rulebook**: Bears vs Babies, Cards for All People, Checkers, Chess, Clank!,
Digimon Card Game, Dominoes, Doomlings, Dungeon Mayhem, Exploding Kittens, Here to Slay,
Munchkin Babies, Pit, Pixel Tactics, Poker, Stratego, UNO, Wooden Pong. Five have a single
card saying she has not been taught them and will not invent rules: Far Away, Guilty Gear
Board Game, Heroes of Barcadia, Monster Rejects, Tic Tac K.O. Their rule sheets need loading
through the Library page. The game picker shows four big tiles, then eight names a page.

## Decisions already made

- D&D table will probably use the **2024 rules** (Ethan said "probably"; confirm before relying on it). The campaign is Dragon of Icespire Peak (Essentials
  Kit), whose booklet is written for the 2014 rules. Monsters are used as printed.
- The free D&D rules document (SRD 5.2.1, CC BY 4.0) is the rules source. It needs a
  credit line in Settings, About.
- Magic card data comes from Scryfall's bulk files and the screen credits Scryfall.
- Ethan owns several D&D books and Warhammer codexes. They load from his own files into
  `content/mine/`. Anything in a `campaigns` folder is DM-only.
- Ethan's 40k army is Necrons: 20 Warriors, C'tan Shard of the Void Dragon, 5 Triarch
  Praetorians, 5 Lychguard, 1 Canoptek Doomstalker, 1 Royal Warden, 1 Overlord, 6 Scarab
  Swarm bases.

## Known gaps and unverified claims

- `dt_content.py`: two-column PDFs may read out of order; datasheet tables may lose their
  columns; `fetch-mtg` has never run against the live Scryfall service.
- `dt_characters.py`: PDF field names were written from memory. Skill and save
  proficiencies are not read from sheets.
- Knowledge Base: four 2026 kill teams are marked "not yet verified"; some 40k faction rule
  names come from before the 11th edition; D&D and Magic tabs were written from memory.
- Wi-Fi: the MT7601U adapter is slowed about tenfold by the display backlight and further by the
  USB microphone sitting beside it (measured 22 Nov 2026). Cause believed to be noise through the
  air; a USB extension lead to move the adapter is untested. Ethan does not want to buy parts on a guess.
- Button: works wired on the bench (24 Nov 2026). Not confirmed: that it still works once mounted in the case. The Pi's clock jumps forward about 35 minutes shortly after each power-up (network time), so log times from before and after the jump do not line up.
- Sound: the speaker follows the signal in step up to full scale but is quiet, and full-scale tones bring low-voltage dips (measured with her microphone, 23 Nov 2026).
- Power: measured 24 Nov 2026 with the Pi's under-voltage alarm. Through the 30 cm panel-mount micro-USB extension she dips under voltage twice while starting and for the whole time she speaks (not at idle, not with all four cores busy). With the same tests on the supply plugged straight into the Pi: no dips at all. The extension loses the voltage. A 30-minute soak through it (speech without a break, `~/soak.sh` on the Pi) kept her under voltage and slowed to 600 MHz the whole time, with no fault: 15 of 15 SD write-and-read checks matched, no ping lost, no card or USB errors. Not tried: a 5.25 V supply (Adafruit 1995), which would be changed from outside the case.
- Hardware: whether the 8 mm display thickness was measured to the corner posts or to the
  board; an LED ring collar is undesigned (needs the ring's outer diameter and thickness).

## If you touch the printed parts

- Tooling was headless Blender (`bpy`) with helpers in `cad/scripts/lib.py`. Use MANIFOLD
  booleans. `bpy.ops.wm.read_factory_settings(use_empty=True)` breaks the context in this
  setup; open a .blend instead.
- Exported STLs are not in model coordinates. STL = model minus the bounding-box centre in
  X and Y, and Z minus the lowest Z. The bell is also printed flipped: x' = x - cx,
  y' = -(y - cy), z' = 239 - z.
- Measured facts (model coordinates, mm): core top plate at z 96, wall strips up to z 100.
  Base plate top is a flat 2.3 mm sheet with a 30 mm wire hole and a 28 mm button hole and
  no recess for the LED ring. The core sits flat and is glued, only after the LED test.
  Display pocket is 8.0 mm deep with three rim pilot holes (none at lower right, where the
  speaker slot is). Speaker slot entrance pinches to about 16 mm.
- Speaker: body 28.5 x 30.5 x 15.5 mm, ears 42.5 mm tip to tip and 3 mm thick, holes 35 mm
  apart. It is held by two ear blocks screwed through two grille holes.
- A motion-planning check once said the speaker could not fit the slot. Ethan put it in by
  hand. When a simulation and the physical part disagree, the part wins.
- Printer: Ender 3 V3 KE. Body in blue PETG, core in clear PETG.
