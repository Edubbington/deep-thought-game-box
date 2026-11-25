"""The real hardware, as wired in CLAUDE.md.

  button   GPIO 17 to ground, internal pull-up        (gpiozero)
  ring     16 WS2812 LEDs, data on GPIO 10 = SPI MOSI (spidev)
  sound    I2S amp on GPIO 18/19/21, hifiberry-dac overlay (pygame mixer over ALSA)
  mic      USB microphone                             (arecord)

NOT TESTED. This file has never run on a Pi: the box was not powered up when
it was written. Each part is small so it can be tried on its own:
  python -m deepthought.hw.pi ring     # every behaviour for three seconds
  python -m deepthought.hw.pi button   # prints gestures as you press
  python -m deepthought.hw.pi sound    # plays the tick five times
  python -m deepthought.hw.pi mic      # records three seconds, plays it back
"""
import array
import collections
import math
import os
import re
import subprocess
import tempfile
import threading
import time

from .. import ring as ring_mod
from ..gestures import DEBOUNCE, Gestures

BUTTON_GPIO = 17
SPI_HZ = 2_400_000              # three SPI bits make one WS2812 bit
RING_FPS = 30


def ws2812_bytes(colours):
    """Turn [(r, g, b), ...] into the SPI bytes that make WS2812 data.
    Each data bit becomes three SPI bits: 1 -> 110, 0 -> 100. The LEDs take
    green first, then red, then blue. A run of zero bytes at the end is the
    reset gap that latches the colours."""
    bits = []
    for r, g, b in colours:
        for value in (g, r, b):
            for i in range(7, -1, -1):
                bits += (1, 1, 0) if (value >> i) & 1 else (1, 0, 0)
    out = bytearray()
    for i in range(0, len(bits), 8):
        byte = 0
        for bit in bits[i:i + 8]:
            byte = (byte << 1) | bit
        out.append(byte)
    return bytes([0]) + bytes(out) + bytes(40)


class PiHardware:
    name = "pi"

    _touch, _pin_ok = False, True

    def __init__(self, sound=True):
        self.g = Gestures()
        self.edges = collections.deque()           # (down, time) from the GPIO thread
        self._ring = ring_mod.RingState()
        self._lock = threading.Lock()
        self.volume = 70
        self._tick = None
        self._rec = None
        self._rec_path = None
        self._button = None
        self._touch = False                         # the strip across the top of the screen, held as the button
        self._pin_ok = True                         # False while the pin has been down since she started
        self._spi = None
        self.problems = []                          # shown in Settings, never a crash
        self._start_button()
        self._start_ring()
        if sound:
            self._start_sound()

    # ---- button
    def _start_button(self):
        try:
            from gpiozero import Button
            self._button = Button(BUTTON_GPIO, pull_up=True, bounce_time=None)
            self._button.when_pressed = lambda: self.edges.append((True, time.monotonic()))
            self._button.when_released = lambda: self.edges.append((False, time.monotonic()))
            # Found on the real Pi, 22 and 23 Nov 2026: the switch reads closed all the time.
            # A button that is down when she starts is not a finger: it is left out until it
            # has been seen up once, so it cannot hold her microphone open or ask to shut down.
            self._pin_ok = not self._button.is_pressed
            if not self._pin_ok:
                self.problems.append("button: held down since I started, so I am ignoring it. The top of the screen does its job.")
        except Exception as e:
            self.problems.append("button: %s" % e)

    def key_event(self, event, t):
        pass                                        # no keyboard on the box

    def touch_button(self, down, t):
        """A finger on the strip across the top of the screen stands in for the button."""
        self._touch = bool(down)
        self.g.edge(self._touch or self._pin_down(), time.monotonic())

    def _pin_down(self):
        """Is the real button down, as far as she believes it?"""
        b = self._button
        if b is None:
            return False
        try:
            pin = bool(b.is_pressed)
        except Exception:
            return self.g.down and not self._touch
        if not self._pin_ok:
            if pin:
                return False
            self._pin_ok = True
            self.problems = [p for p in self.problems if not p.startswith("button: held down")]
        return pin

    def gestures(self, t):
        while self.edges:
            down, when = self.edges.popleft()
            if self._pin_ok and not self._touch:
                self.g.edge(down, when)
        now = time.monotonic()                      # a bounce can swallow an edge: trust the pin itself,
        if now - self.g.t_edge >= DEBOUNCE:         # so the button can never be left "held". The time is taken
            actual = self._pin_down() or self._touch    # here, not from the frame: edges still on their way
            if actual != self.g.down:               # from the pin's thread carry later times than the frame's,
                self.g.edge(actual, now)            # and a bounce among them must fall inside the debounce
        self.g.tick(t)
        return self.g.take()

    # ---- ring
    def _start_ring(self):
        try:
            import spidev
            self._spi = spidev.SpiDev()
            self._spi.open(0, 0)
            self._spi.max_speed_hz = SPI_HZ
            self._spi.mode = 0
            threading.Thread(target=self._ring_loop, daemon=True).start()
        except Exception as e:
            self.problems.append("ring: %s" % e)

    def _ring_loop(self):
        last = None
        while self._spi:
            with self._lock:
                frame = self._ring.frame(time.monotonic())
            if frame != last:                       # only talk to the LEDs when something changed
                try:
                    self._spi.xfer3(list(ws2812_bytes(frame)))
                except Exception:
                    pass
                last = frame
            time.sleep(1.0 / RING_FPS)

    def ring(self, behaviour, **kw):
        with self._lock:
            self._ring.set(behaviour, **kw)

    def ring_frame(self, t):
        with self._lock:
            return self._ring.frame(t)

    # ---- sound
    def _start_sound(self):
        try:
            import pygame
            pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=1024)
            n = 24000 * 40 // 1000
            wave = array.array("h", (int(6000 * math.sin(2 * math.pi * 880 * i / 24000) * (1 - i / n))
                                     for i in range(n)))
            self._tick = pygame.mixer.Sound(buffer=wave.tobytes())
        except Exception as e:
            self.problems.append("sound: %s" % e)

    def tick_sound(self):
        if self._tick:
            self._tick.play()

    def set_volume(self, percent):
        self.volume = max(0, min(100, int(percent)))
        if self._tick:
            self._tick.set_volume(self.volume / 100.0)

    def play(self, path):
        try:
            import pygame
            if pygame.mixer.get_init():
                sound = pygame.mixer.Sound(path)
                sound.set_volume(self.volume / 100.0)
                pygame.mixer.Channel(1).play(sound)
            else:
                print("hardware: sound not played, the mixer is not running", flush=True)
        except Exception as e:                       # say so in the log: a silent failure cost an evening
            print("hardware: sound not played: %s" % e, flush=True)

    def stop_sound(self):
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.Channel(1).stop()
        except Exception:
            pass

    # ---- microphone
    def mic_card(self):
        """The sound card number of the microphone, or None. A USB one is preferred;
        which number it gets depends on what else is plugged in."""
        try:
            out = subprocess.run(["arecord", "-l"], capture_output=True, text=True, timeout=3).stdout
        except Exception:
            return None
        return pick_mic_card(out)

    def has_mic(self):
        return self.mic_card() is not None

    def record_start(self):
        self._rec_path = os.path.join(tempfile.gettempdir(), "dt-question.wav")
        card = self.mic_card()
        try:
            self._rec = subprocess.Popen(["arecord", "-q", "-D", "plughw:%d" % (1 if card is None else card),
                                          "-f", "S16_LE", "-r", "16000", "-c", "1", self._rec_path])
        except Exception as e:
            self._rec = None
            self.problems.append("mic: %s" % e)

    def record_stop(self):
        if not self._rec:
            return None
        self._rec.terminate()
        try:
            self._rec.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self._rec.kill()
        self._rec = None
        ok = os.path.isfile(self._rec_path) and os.path.getsize(self._rec_path) > 1000
        return self._rec_path if ok else None

    # ---- power
    def shutdown(self):
        """Ring off, then a clean power-off so the SD card is not corrupted."""
        self.ring("off")
        time.sleep(0.3)
        if self._spi:
            try:
                self._spi.xfer3(list(ws2812_bytes([(0, 0, 0)] * 16)))
            except Exception:
                pass
        subprocess.Popen(["sudo", "systemctl", "poweroff"])


def pick_mic_card(listing):
    """Read `arecord -l` and choose a card: the first USB one, else the first of any kind."""
    cards = re.findall(r"^card (\d+):(.*)$", listing or "", re.M)
    usb = [int(n) for n, rest in cards if "usb" in rest.lower()]
    return usb[0] if usb else (int(cards[0][0]) if cards else None)


def is_pi():
    try:
        with open("/proc/device-tree/model") as f:
            return "Raspberry Pi" in f.read()
    except OSError:
        return False


if __name__ == "__main__":
    import sys
    what = sys.argv[1] if len(sys.argv) > 1 else ""
    hw = PiHardware(sound=what in ("sound", "mic"))
    print("problems:", hw.problems or "none")
    if what == "ring":
        for name in ring_mod.BEHAVIOURS:
            print(name)
            hw.ring(name, level=0.5) if name == "listening" else hw.ring(name)
            time.sleep(3)
        hw.ring("off")
        time.sleep(0.2)
    elif what == "button":
        print("Press, hold and double-press the button. Ctrl-C to stop.")
        while True:
            for gesture in hw.gestures(time.monotonic()):
                print(gesture)
            time.sleep(0.02)
    elif what == "sound":
        for _ in range(5):
            hw.tick_sound()
            time.sleep(0.5)
    elif what == "mic":
        print("mic found:", hw.has_mic())
        hw.record_start()
        time.sleep(3)
        path = hw.record_stop()
        print("recorded:", path)
        if path:
            hw.play(path)
            time.sleep(3.5)
    else:
        print(__doc__)
