# Giving Deep Thought her voice

She has three cloud abilities. Each is optional. Without any of them she shows her lines
on screen, takes typed questions, and answers from the library on the box.

| Ability | Needs | Cost, roughly |
|---|---|---|
| Answers in her own words | A Claude API key | Well under a cent a question |
| Speaking aloud | A speech key | About 1.5 cents per 1,000 characters, once per line |
| Hearing a spoken question | A speech key and the USB microphone | About 0.6 cents a minute |
| Reading a photo of a paper character sheet | A Claude API key | A cent or less a photo on the default model |

A monthly cap (5 dollars unless you change it) switches the cloud off when reached.
Settings, Library, then the "Voice and cloud" page shows what is on and what has been spent.

**None of this has been run against the live services.** No keys were available when it
was written. Expect to tell me what happens the first time.

## Set it up

1. In `software/`, copy `config.example.toml` to `config.toml`.
2. Open `config.toml` in a text editor.
3. Paste your Claude API key between the quotes after `api_key` under `[claude]`.
4. Paste your speech key between the quotes after `api_key` under `[speech]`.
5. Save the file and start Deep Thought.
   You should hear her say a power-on line within a few seconds.
6. Hold the button (space bar on a PC), let go, and type a question.
   You should see "You asked: …", the ring chasing, then an answer card with a source.

## Choosing the voice

The spec says to audition three voices with the same five lines. To try one:

1. Set `tts_voice` in `config.toml`.
2. Run `python tools/build_audio.py --list`.
   You should see how many lines would be made and the cost (a few cents).
3. Run `python tools/build_audio.py`.
   You should see each line listed as it is made.
4. Start Deep Thought and roll some dice.
   You should hear the remarks in the new voice.

Every line is stored under the voice that made it, so changing voice makes a new set and
the old set is kept. Stored lines play with no network and no delay.

## The rulings log

Every answer she gives from the cloud is saved with its source. Ask the same question
again, on any night, and she gives the same answer and says when she first ruled.
The Rulings web page lists them all.

## What leaves the box

A photo of a character sheet, only when a player uploads one on the Characters page and
presses Read photo. Otherwise only a typed or spoken question, the game and phase, and up
to three short excerpts from the library. Campaign (DM only) pages are sent only while DM mode is unlocked. Lookup,
scoring and tracking send nothing.
