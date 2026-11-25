# Deep Thought: how the game night box was built

Deep Thought is a tabletop companion in a 3D-printed body. She sits on the table on game
night, keeps the turn order and the scores, teaches new players as they play, answers rules
questions out loud, and rolls dice. She has a 5 inch touch screen, one lit button, a ring of
LEDs under a clear dome, a speaker and a microphone, and she runs on a Raspberry Pi 2.

This guide covers the whole build: parts, printing, wiring, the Pi, the program, her voice,
and adding games. The second half is the list of everything that went wrong and how each
problem was found and fixed. That half is the useful one.

Built by Ethan. The body was designed and printed first; the program was written over five
days in November 2026. The program, the tests and these documents
were written with Claude Code (Anthropic's coding assistant), working from Ethan's design
and steered by him at every step. The hardware, soldering, printing and every decision by
ear or eye were his.

## What she does

- **One button.** Press = next. Hold = talk to her. Double press = undo. The same in every game.
- **Six full games** with their own screens and rules: Warhammer 40,000 Kill Team,
  Warhammer 40,000, Dungeons & Dragons (initiative, character sheets, a DM desk), Magic: The
  Gathering, Risk, and a scorekeeper for anything else.
- **Twenty-three shelf games** as simple entries: turn order, a score where one makes sense,
  and a "How to play" in her own words.
- **Teach as we play.** Each rule comes up as a card at the moment it matters, read aloud.
- **Spoken questions.** Hold the button and ask. Speech goes to a speech-to-text service,
  the question and the three best passages from her library go to a language model, and the
  answer is spoken in her voice.
- **Phone pages.** A scoreboard for a shared screen, and a page per seat for each player's
  phone, served from the box over the home Wi-Fi behind a four-digit table code.
- **A character.** A vast, ancient, benevolent machine who is quietly amused that this is
  what she is asked to do.

## Parts

Prices are what was paid in late 2026. The full list is `docs/PARTS_LIST.csv`.

| Part | Notes |
|---|---|
| Raspberry Pi 2 Model B | Already owned. Slow, 1 GB of RAM, no Wi-Fi of its own. A newer Pi would make everything easier. |
| 5 inch DSI capacitive touch display, 800x480 | Powered through its ribbon. No HDMI or USB lead needed. |
| NS4168 I2S amplifier and a 3 W speaker | Wires up exactly like the common MAX98357A. |
| 16-LED WS2812 ring | Driven from the SPI pin, so no extra library tricks. |
| 30 mm LED arcade button | One. Buy the five-pack; spares are useful. |
| USB microphone, USB Wi-Fi adapter | The Wi-Fi adapter was the worst buy of the project. See the problems list. |
| 5 V 3 A micro-USB supply with a switch | And a 30 cm panel-mount extension so the socket is on the outside of the case. See the problems list for this too. |
| Jumper wires, heat shrink, self-tapping screws, foam tape | |
| About 107 dollars of parts, not counting the Pi, the card and the filament | |

## Printing the body

Seven parts, printed on an Ender 3 V3 KE: the body in blue PETG and the core with its dome in
clear PETG so the LED ring glows through it.

| Part | Material |
|---|---|
| Head bell | Blue PETG |
| Chin plate | Blue PETG |
| Core with legs and dome | Clear PETG |
| Base plate | Blue PETG |
| Riser | Blue PETG |
| Display clamp tabs (three needed) | Any |
| Speaker ear blocks (two needed) | Any |

**The printable STL files are not in this repository.** The body was cut from a free
Deep Thought model made by someone else, and that model is theirs to share, not this
project's. Find a Deep Thought model you like, or design your own body: nothing in the
program depends on the shape. The scripts that did the cutting and measuring are here.

The parts were cut from a one-piece model using Blender driven by Python scripts
(`cad/scripts/`, helpers in `lib.py`). The scripts are kept because they are the record of
every measurement.

## Wiring

`guide_images/wiring4.jpg` is the diagram to follow. With the SD card slot at the top:

| Pin | Wire | Goes to |
|---|---|---|
| 2 (5 V) | red | A splice feeding the LED ring's 5 V and the button lamp's + |
| 4 (5 V) | red | Amplifier V |
| 9 (ground) | black | Amplifier G |
| 11 (GPIO 17) | green | Button switch |
| 12 (GPIO 18) | blue | Amplifier BCLK |
| 14 (ground) | black | LED ring ground |
| 19 (GPIO 10, SPI MOSI) | green | LED ring data in |
| 20 (ground) | green | Button switch, the other lead |
| 25 (ground) | grey | Button lamp - |
| 35 (GPIO 19) | green | Amplifier LRC |
| 40 (GPIO 21) | yellow | Amplifier DIN |

Pins 1 and 17 are 3.3 V. Leave them empty.

On the button, the two small tabs are the switch and the two large tabs are the lamp. The
lamp is wired straight to 5 V, so it is always lit and the program cannot switch it.

Two habits that would have saved a day:

- Tag every wire at both ends before plugging anything in. There are four green wires.
- Once it works, put a short piece of heat shrink over each loose jumper plug. It holds them
  on and can be cut off later.

`docs/text/Assembly Guide.txt` has the full step-by-step assembly, with its pictures in
`guide_images/`.

## Setting up the Pi

`software/PI_SETUP.md` is the step-by-step. In outline:

1. Write Raspberry Pi OS Lite to the card with a current Raspberry Pi Imager. Set the user,
   the Wi-Fi and SSH in the Imager, because the card will never come out again.
2. In `config.txt`: `dtparam=spi=on`, `dtparam=audio=off`, `dtoverlay=hifiberry-dac`.
3. Install pygame and the graphics libraries from apt (the list is in `PI_SETUP.md`).
4. Copy `software/` to the Pi and install `tools/deepthought.service` so she starts at power-on.
5. Set up an SSH key from your PC. Everything after assembly is done over SSH.

## The program

One Python process using pygame, full screen at 800x480. Python 3.13 on the Pi, 3.11 on the
PC. Almost no dependencies: the web pages use Python's own `http.server`, and calls to the
cloud services are plain HTTPS.

```
software/run.py                  start it (space bar is the button on a PC, Esc quits)
software/deepthought/app.py      the shell: screens, the button, the top strip
software/deepthought/engine.py   a game session: events, undo, save, resume
software/deepthought/games/      one folder per game
software/deepthought/hw/         the real Pi, and a desktop stand-in for development
software/deepthought/voice.py    speech in, speech out, the question pipeline, the spend cap
software/deepthought/voicefx.py  the sound of her voice: a faint ring, a gentle hall
software/deepthought/persona.py  her character and her stock lines
software/deepthought/web.py      scoreboard and phone pages
software/tests/                  every piece of logic has a check
software/tools/                  recording her lines, simulating tables, auditioning voices
```

Every test file is a plain script that ends by printing `N failed`:

```
cd software
.venv/Scripts/python tests/test_engine.py
```

There are about 2,970 checks. They pass on Windows and on the Pi itself.

The whole program runs on a PC with a window instead of a display and the space bar instead
of the button. Nearly all the work was done that way before any hardware existed.

### Adding a game

A game is a folder. Most board games need two small files and no code: `game.json` (players,
the parts of a turn, what to count, how it is won) and `teach.json` (how to play, in your own
words). `software/PLUGINS.md` explains both kinds of game.

### Her voice

`software/VOICE.md` has the setup. Keys for the two cloud services go in
`software/config.toml`, which is never committed. A monthly spending cap is built in and she
falls back to her own notes when it is reached. In practice a game night costs a few cents.

Her stock lines and every "How to play" page are recorded ahead of time
(`tools/build_audio.py`), so they play instantly and without a network.

### Rules text

Nothing in this repository is copied from a rulebook, a codex, an adventure or a card. She
teaches in her own words. The actual rulebooks are loaded by their owner, from their own
files, into a library that is never committed (`software/LIBRARY.md`).

## Everything that went wrong, and how it was fixed

In the order it happened.

### Printing and fitting

| Problem | Cause | Fix | Lesson |
|---|---|---|---|
| Printed parts did not fit, more than once. | Dimensions were taken from the working model, not from the file that was actually sent to the printer. | Measure the exported STL itself before printing or changing anything. | Measure, do not guess. A bad guess costs filament and a day. |
| A simulation said the speaker could not go into its slot. | The simulation was wrong. | Ethan put it in by hand. It fits. | When a simulation and the physical part disagree, the part wins. |
| The display is mounted upside down. | The backlight switch edge had to be at the bottom to fit the head. | Rotate the picture in software. | Decide orientation from the part, then tell the software. |

### The program, before any hardware

| Problem | Cause | Fix | Lesson |
|---|---|---|---|
| A double press on a menu or a map could undo one or two moves in the game underneath. | Every screen was passing the double press down. The tests missed it because they sent a double press alone, which the real button can never do. | A double press belongs to the screen that received the first press. Tests now always send press, then double. | Test what the hardware can really do, not what is convenient to send. |
| About ninety other faults. | First drafts. | Each piece was reviewed by a reviewer that had not written it, each fault was reproduced before it was fixed, and each fix got a check. Then the fixes were reviewed twice more. | A fix without a test that fails first is a hope. |
| One fault in any screen stopped the whole program. | No safety net. | A fault now puts the game state back, is written to `data/errors.log`, and she says so and carries on. | A box on a table with no keyboard must never just stop. |
| An answer given to the DM could be repeated to the players. | DM-only material was not kept apart. | Everything on a DM screen is shown on the box only: never spoken, never sent to a web page. | Hidden information needs its own path through every output. |

### First power-up

| Problem | Cause | Fix | Lesson |
|---|---|---|---|
| The Pi would not join the Wi-Fi. | An older Raspberry Pi Imager stored the password in a form a WPA2/WPA3 router rejects. | Use a current Imager, or set the real password with `nmcli`. | |
| A black screen, then "EGL not initialized". | The Lite system has no graphics libraries, and SDL was not drawing through the graphics chip. | Install `libegl1 libgles2 libgl1-mesa-dri`; `run.py` sets `SDL_VIDEODRIVER=kmsdrm` and the OpenGL ES renderer itself on the Pi. | |
| Touch did nothing. | A touch arrives as a finger event, not a mouse click. | The program accepts both. | |
| The screen went dark and stayed dark. | Writing 0 to the backlight. The panel then stays dark until the display output is switched off and on. Anything under about 48 of 255 is dark as well. | Never write 0. She is set to 75 at power-on. | Find the safe range of a control before automating it. |
| No sound from a test beep. | `speaker-test` takes over a second to start on a Pi 2, so a one second tone is silent. | Play a ready-made sound file with `aplay`. | |
| The microphone heard nothing. | Its gain was 0 of 16 out of the box. | `amixer -c 0 sset Mic 14 cap`, then `sudo alsactl store`. | |
| Wi-Fi about ten times slower with the screen lit. | Measured, not guessed: the display's backlight and the USB microphone sitting beside the adapter each cut its speed. Signal strength, channel, power saving, USB port and supply were all ruled out one at a time. | Pages still load in about a second, so it was left. Wi-Fi power saving is off. | Check where a radio will physically sit before choosing it. A nano adapter pressed against a display is a poor place for an aerial. |

### Her voice

| Problem | Cause | Fix | Lesson |
|---|---|---|---|
| Recorded lines would not play on the Pi. | The speech service's WAV files give their length as "unknown", and the Pi's sound library refuses that. | `voice.true_lengths` writes the real lengths into each file. | |
| The language model's package would not be installed on the Pi 2. | Too heavy for the board. | Plain HTTPS calls instead. No package at all. | The fewer dependencies, the fewer surprises on old hardware. |
| Far too quiet for a room. | A small speaker and a small amplifier. Measured with her own microphone: the output rises in step with the signal up to full scale, with no clipping, so there was nothing left to turn up. | Every line is brought to full scale and given a gentle high-pass and a soft limiter, which makes speech sound louder at the same peak. | Measure the chain before blaming one link. |
| The first voice was a deep male voice. Wrong. The next attempts were slow, stern and heavily processed. Also wrong: "too pissed off". | The brief was being guessed. | An audition tool (`tools/audition.py`) plays numbered candidates through her own speaker. Ethan wrote his own description of the voice, picked by ear, and that description is now sent with every line. Effects were cut back to a faint ring and a gentle hall. | Taste cannot be specified in advance. Build the tool that lets the person choose, and offer a few options at a time. |
| Heavy loudness processing made her sound angry. | Compression reads as shouting. | A light touch only. | |

### The button

This one is told in full because the diagnosis was wrong.

The button did nothing. Reading the pin from the Pi showed the switch circuit closed all the
time: with both plugs on, the pin read "pressed" whether or not the button was pushed. Tests
at the header, pulling one plug and then the other, confirmed that the two switch wires
were joined at the button end.

The conclusion drawn was that the switch was stuck closed, probably damaged by soldering heat.
Ethan soldered a spare button on. It worked. Then he looked again at the first button and
found it was fine: **the wiring had been wrong**, and re-doing the joints on the spare had
put it right by accident.

What the measurement actually showed was "these two wires are joined". It did not show which
part joined them. The step that was skipped was the cheap one: check the wiring against the
diagram before blaming a component.

Two things built during the outage were kept:

- The 60 pixel strip across the top of the screen acts as the button: tap, hold, two taps.
- A real button that is down when she starts is ignored until it has been seen up once, so a
  stuck button can never trap her in "hold".

One more trap from the same day: the Pi has no clock battery, and its clock jumps forward
(about 35 minutes that day) when network time arrives a minute after power-up. A log of
button presses read across that jump made working presses look as if they had never happened.

### Using her

| Problem | Cause | Fix | Lesson |
|---|---|---|---|
| "Once a game is started I can't figure out how to end it." | The way out existed, behind a button labelled "More" at the far end of the bottom row. | The button is now "Menu". "End game" offers End it (record the result) and Scrap it (throw a wrongly started game away). | If the person who commissioned it cannot find the exit, the exit is not there. |
| Her answers talked about her own notes being cut off, and she did not know whose turn it was. | The model was shown raw search results and none of the game state. | The turn and the scores go with every question, and she is told never to describe her notes. | Read real answers to real questions. `tools/scenarios.py` asks 93 of them for about three cents. |

### Power

| Problem | Cause | Fix | Lesson |
|---|---|---|---|
| Low-voltage warnings whenever she speaks, and the processor slowed to two-thirds speed. | The 30 cm panel-mount extension lead inside the case. The same test with the supply plugged straight into the Pi gave no warnings at all. | A 30 minute soak test of non-stop speech through the lead found no fault: every SD card write read back correctly and no network packet was lost. So she was assembled as she was. A 5.25 V supply, which starts a quarter of a volt high to make up for the lead, is the planned cure and plugs in from outside. | Change one thing and run the same test. And prefer the fix that does not need the case opened. |

## What is still not done

- No real game night has been played on her yet.
- Hold-to-talk listens, but whether she understands a question spoken across a table is not confirmed.
- Whether she is loud enough for a table is not confirmed.
- Eighteen of the shelf games teach from memory and have not been checked against their
  rulebooks. Five say plainly that they have not been taught.
- Her notes hold no Kill Team or 40k core rules, and her D&D answers may use older wording.
- The 5.25 V supply has not been tested.

## If you build one

- Use a newer Pi than a Pi 2. Built-in Wi-Fi alone removes two of the problems above.
- Make the power socket a short, thick lead, or use a 5.25 V supply from the start.
- Fix the SD card question early: once she is glued, the card is out of reach, so SSH with a
  key has to work before assembly.
- Build the desktop stand-in for the hardware first. It is what made five days possible.
- Keep a file of what is tested and what is not. "Passes on made-up test files, never run on
  the real thing" is a fine sentence. An untested claim presented as fact is not.
