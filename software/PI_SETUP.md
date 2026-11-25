# Putting Deep Thought on the Pi

This is the plan as written before the box was powered up. **She has since run on the real
Pi (22 November 2026), and several steps needed changes.** Those are listed in "What the first
real run found" at the end; where the two disagree, that section wins.

Do the Assembly Guide's power-up tests first. This guide starts after the box boots.

## A. The memory card

1. On the PC, install Raspberry Pi Imager.
2. Choose device **Raspberry Pi 2**.
3. Choose **Raspberry Pi OS (Legacy, 32-bit) Lite** if offered, otherwise **Raspberry Pi OS (32-bit)**.
4. Press **Edit settings**. Set hostname `deepthought`, a user name and password, your Wi-Fi, and turn on SSH.
5. Write the card, put it in the Pi, and power on.
   You should see text scroll on the display within a minute. It may be upside down; that is expected.
6. On the PC, run `ssh <user>@deepthought.local`.
   You should get a prompt on the Pi.

## B. Switch on the ring and the amplifier

7. On the Pi, run `sudo nano /boot/firmware/config.txt`.
8. Add these three lines at the end:
   ```
   dtparam=spi=on
   dtoverlay=hifiberry-dac
   dtparam=audio=off
   ```
9. Save, then run `sudo reboot`.
   You should lose the connection and be able to log in again after a minute.

## C. Install what the program needs

10. Run:
    ```
    sudo apt update
    sudo apt install -y python3-pygame python3-gpiozero python3-spidev python3-pypdf python3-qrcode alsa-utils
    ```
    You should see it finish with no line starting `E:`.
11. Run `python3 --version`.
    You should see `Python 3.11` or newer.

## D. Copy the program

12. On the PC, in `D:\Deep Thought\DeepThought`, run:
    ```
    scp -r software <user>@deepthought.local:deepthought
    ```
    You should see file names scroll past. (`.venv` is large and not needed on the Pi; delete it there afterwards with `rm -rf ~/deepthought/.venv`.)

## E. Test each part on its own

Run each from `~/deepthought` on the Pi.

13. `python3 -m deepthought.hw.pi ring`
    You should see `problems: none`, then the ring breathe blue and change pattern every three seconds.
    If the ring stays dark, the two green wires on pins 19 and 20 may be swapped (see `CLAUDE.md`).
14. `python3 -m deepthought.hw.pi button`
    Press, hold, and double-press. You should see `press`, `hold_start` / `hold_end`, and `press` then `double`.
15. `python3 -m deepthought.hw.pi sound`
    You should hear five short ticks.
16. `python3 -m deepthought.hw.pi mic`
    Speak for three seconds. You should see `mic found: True` and hear yourself played back.

## F. Run it

17. `python3 run.py`
    You should see the Home screen, the right way up, filling the display.
    If it is upside down, run `python3 run.py --no-flip` instead and tell me.
18. Tap **Dice**, then press the button.
    You should see six dice and hear a tick.
19. Hold the button for five seconds on Home.
    You should see "Shut down?". Tap **Shut down**. The ring goes dark; wait ten seconds before switching the power off.

## G. Start at power-on

20. Copy the service file: `sudo cp ~/deepthought/tools/deepthought.service /etc/systemd/system/`
21. Open it with `sudo nano /etc/systemd/system/deepthought.service` and change `USERNAME` to your user name in three places.
22. Run `sudo systemctl enable --now deepthought`.
    You should see the Home screen appear without typing anything.
    If she ever stops by herself, the reason is in `~/deepthought/data/errors.log` and in `journalctl -u deepthought -n 50`. Send me either.
23. Power off with the five-second hold, then power on again.
    You should see the Home screen within about a minute.

## Things I expect might need fixing

- Touch may arrive unflipped while the picture is flipped, or the other way round.
- `dtoverlay=hifiberry-dac` is the spec's choice for the NS4168 amp; `dtoverlay=max98357a` is the alternative if there is no sound.
- The microphone is found by asking `arecord -l` for a USB sound card. If step 16 says `mic found: False`, run `arecord -l` and send me what it prints.
- Drawing may be slow. The program redraws only when something changes, but it has never been timed on a Pi 2.
- The Claude answers need `pip install anthropic`, which may not install cleanly on a Pi 2. Without it she answers from the library.

## What the first real run found (22 November 2026)

She first ran on the real Pi 2 on 22 November 2026: Raspberry Pi OS trixie Lite, Python 3.13.5,
pygame 2.6.1 from apt. This is what was true that day.

**Works, seen or heard by Ethan:** the display, touch, the LED ring, the amplifier and
speaker, the microphone, her Home screen, starting by herself at power-on.
**All thirteen test files pass on the Pi itself** (2,322 checks).

**Does not work yet:**

- **The button.** The switch circuit is closed all the time: GPIO 17 reads pressed with the
  green plug on pin 11 and not pressed with it off, whether or not the button is pushed. The
  lamp works. The cause at the button is not found. The plug on pin 11 is left off; with it
  on she believes the button is held and asks about shutting down.
- **Wi-Fi is slow with the screen lit.** Measured, not guessed: the display's backlight and
  the USB microphone's physical presence each cut the MT7601U adapter's speed. Backlight off
  and microphone out: about 1 MB/s. Backlight at 75 and microphone in: about 30 KB/s
  receiving, 200 KB/s sending. Pages still load in about a second. Not the cause: signal
  strength, channel, power saving, USB port, supply sag, the microphone's data. Untested:
  moving the adapter away on a USB extension lead.

**What had to change from the plan above, and is now set up on her:**

- Raspberry Pi Imager older than 2.0.12 stores the Wi-Fi password in a form that cannot join
  a WPA2/WPA3 router. Use a newer Imager, or set the real password with
  `sudo nmcli connection modify <name> 802-11-wireless-security.psk <password>`.
- Extra packages: `iw python3-reportlab libegl1 libgles2 libgl1-mesa-dri`. Without the last
  three she fails with "EGL not initialized".
- The picture was black until SDL was told to draw through the graphics chip. `run.py` now
  sets `SDL_VIDEODRIVER=kmsdrm`, `SDL_RENDER_DRIVER=opengles2` and
  `SDL_FRAMEBUFFER_ACCELERATION=opengles2` by itself on the Pi.
- A touch arrives as a finger event, not a mouse click. `app.py` now accepts both.
- `/etc/asound.conf` sends sound to the amplifier: `defaults.pcm.!card sndrpihifiberry` and
  `defaults.ctl.!card sndrpihifiberry`. `dtoverlay=hifiberry-dac` is right for the NS4168.
- The microphone's gain was 0 of 16. Set with `amixer -c 0 sset Mic 14 cap`, saved with
  `sudo alsactl store`.
- Backlight: `/sys/class/backlight/10-0045/brightness`, 0 to 255. Below about 48 the panel is
  dark. She is set to 75 at power-on by `/etc/tmpfiles.d/dt-backlight.conf`. **Never write 0:**
  the panel then stays dark until the display output is switched off and on.
- `/etc/NetworkManager/dispatcher.d/50-dt-wifi-plain` asks for plain (non-802.11n) Wi-Fi when
  the link comes up. It helped in some measurements and not others; delete the file to undo.
- Wi-Fi power saving is off (`/etc/NetworkManager/conf.d/99-dt-powersave.conf`).
- The user is `deepthought`, at `<the Pi's address>` (`deepthought.local` did not resolve from the
  PC). The PC logs in with the key `~/.ssh/deepthought_ed25519`; sudo needs no password. So
  she can be updated and restarted with the case closed.
- The service is installed and enabled as `deepthought.service`.
- A short test beep must be a ready-made sound file. `speaker-test` takes over a second to
  start on the Pi 2, so a one-second tone from it is silent.

**Not yet measured on her:** how fast screens draw in a real game, hold-to-talk,
loading a book, the phone pages from a real phone. She uses about 40% of one core idle on Home.

## The second day (23 November 2026)

- **Her answers work from the Pi.** The `anthropic` package is not installed there, so
  `voice.py` falls back to plain HTTPS. 93 test questions (`python3 tools/scenarios.py`,
  about 3 cents) all came back, median 2.4 seconds.
- **The speech service's WAV files would not play on the Pi.** Their length fields say
  "unknown"; the Pi's sound library refuses that. `voice.true_lengths` mends them.
- **Nobody has heard her speak yet.** The program logs any sound it fails to play
  (`journalctl -u deepthought | grep hardware`) and logs none. Measuring the speaker with her
  own microphone did not work: it could not pick out even the test tone.
- **Power.** One low-voltage dip is logged 22 seconds into each boot checked, on the wall
  supply through the panel-mount lead. None under full load with the backlight at full.
  `vcgencmd get_throttled` shows it (0x50000 = it has happened since boot).
- **Simulated tables.** `python3 tools/simulate.py` is safe to run while she is running.
  360,000 random moves on the PC found one fault (the Any game scorekeeper), since fixed.
- **What reading her answers found**, all since changed: Magic cards asked for by name were
  not looked up; long sections were cut before the line that mattered; she talked about her
  own notes being cut off; she did not know the turn or the score. Still true: her notes have
  no Kill Team or 40k core rules in them, and without notes she may give D&D's 2014 wording.
