"""The Pi backend with stand-in hardware, on this PC.

This is NOT a Raspberry Pi. It runs the real hw/pi.py and the real main loop,
in real time, with three things faked:
  the GPIO pins   gpiozero's own mock pins; this test pulls GPIO 17 low and high
  the SPI bus     a fake spidev that keeps every frame sent to the LED ring
  the OS calls    arecord and "sudo systemctl poweroff" are recorded, not run
The screen and the sound card are SDL's dummy drivers.

It proves the Pi code path hangs together. It cannot prove the wiring, the
LEDs' timing on real silicon, the amp, the display, the touch panel or speed.
"""
import os, sys, tempfile, threading, time, types
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
DATA = tempfile.mkdtemp()
os.environ["DT_DATA"] = DATA
os.environ["DT_CONTENT_DB"] = os.path.join(DATA, "content.db")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

fails = []
def check(name, cond, detail=""):
    line = ("PASS  " if cond else "FAIL  ") + name + ("" if cond else "   " + str(detail))
    print(line.encode("ascii", "replace").decode())
    if not cond: fails.append(name)

# ---------------------------------------------------------------- stand-ins
class FakeSpi:
    last = None
    def __init__(self):
        self.frames, self.opened = [], None
        FakeSpi.last = self
    def open(self, bus, dev): self.opened = (bus, dev)
    def xfer3(self, data): self.frames.append((time.monotonic(), bytes(data)))
sys.modules["spidev"] = types.SimpleNamespace(SpiDev=FakeSpi)

from gpiozero import Device
from gpiozero.pins.mock import MockFactory
Device.pin_factory = MockFactory()

import pygame
from deepthought import hw, theme as T
from deepthought.hw import pi
from deepthought.app import App
from deepthought.games import load_games
from deepthought.screens import common
from deepthought.screens.home import Home

commands = []
class FakeProc:
    def __init__(self, cmd, *a, **k): commands.append(list(cmd))
    def terminate(self): pass
    def wait(self, timeout=None): return 0
    def kill(self): pass
pi.subprocess.Popen = FakeProc
pi.subprocess.run = lambda cmd, **k: types.SimpleNamespace(stdout="card 1: Device [USB PnP Sound Device]")

def decode(data):
    """SPI bytes back to 16 (r, g, b), the way a WS2812 reads them: every
    three SPI bits are one data bit, 110 = 1 and 100 = 0, green first."""
    body = data[1:-40]
    bits = "".join("{:08b}".format(b) for b in body)
    out, ok = [], len(bits) == 16 * 24 * 3
    vals = []
    for i in range(0, len(bits), 3):
        tri = bits[i:i + 3]
        ok &= tri in ("110", "100")
        vals.append(1 if tri == "110" else 0)
    for i in range(0, len(vals), 24):
        g, r, b = (int("".join(map(str, vals[i + k:i + k + 8])), 2) for k in (0, 8, 16))
        out.append((r, g, b))
    return out, ok and data[0] == 0 and data[-40:] == bytes(40)

# ---------------------------------------------------------------- start as the box would
on_real_pi = os.path.exists("/proc/device-tree/model") and "Raspberry Pi" in open("/proc/device-tree/model").read()
check("a PC is not mistaken for a Pi, and a real Pi is recognised", pi.is_pi() is on_real_pi)
box = hw.make("pi", sound=True)
check("the Pi backend starts with no problems reported", box.problems == [], box.problems)
spi = FakeSpi.last
check("the ring opens SPI bus 0, device 0, at 2.4 MHz", spi.opened == (0, 0) and spi.max_speed_hz == 2_400_000)
check("the box sees its USB microphone", box.has_mic())
pin = Device.pin_factory.pin(17)
check("the button is on GPIO 17 with the pull-up on", pin.function == "input" and pin.pull == "up" and pin.state == 1)

# ---------------------------------------------------------------- a swallowed edge, and which card the mic is
t_lost = time.monotonic()                                 # (in real time: the pin check takes the time itself)
box.g.edge(True, t_lost)                                  # the box believes the button went down...
time.sleep(0.05)
got = box.gestures(time.monotonic())                      # ...but the pin itself says it is up
check("a release lost to contact bounce is put right from the pin itself", got == ["press"] and box.g.down is False, got)
check("so the button is never left held: no hold a second later", box.gestures(t_lost + 1.0) == [] and box.gestures(t_lost + 6.0) == [])
box.gestures(time.monotonic())

# one press must stay one press when the frame's own time is old (a slow touch tap came first)
class StandInButton:
    is_pressed = False
slow = pi.PiHardware.__new__(pi.PiHardware)               # the real gestures(), with a pin this test can hold
slow.g, slow.edges, slow._button = pi.Gestures(), pi.collections.deque(), StandInButton()
got = []
StandInButton.is_pressed = True                           # the finger is down; the pin's thread has not said so yet
got += slow.gestures(time.monotonic() - 0.05)             # a frame that began 50 ms ago
now = time.monotonic()
slow.edges.extend([(True, now), (False, now + 0.0008), (True, now + 0.0016)])       # then its edges arrive, with a bounce
for _ in range(4):
    time.sleep(0.03); got += slow.gestures(time.monotonic())
StandInButton.is_pressed = False                          # the finger lifts
slow.edges.append((False, time.monotonic()))
for _ in range(15):
    time.sleep(0.03); got += slow.gestures(time.monotonic())
check("one press seen first by the pin check, in a frame whose time is old, is still one press and no double", got == ["press"], got)
# found on the real Pi, 22 and 23 Nov 2026: the switch reads closed all the time
def fresh(pressed):
    StandInButton.is_pressed = pressed
    h = pi.PiHardware.__new__(pi.PiHardware)
    h.g, h.edges, h._button, h.problems = pi.Gestures(), pi.collections.deque(), StandInButton(), []
    h._pin_ok = not pressed
    return h
def run(h, secs):
    out, end = [], time.monotonic() + secs
    while time.monotonic() < end:
        out += h.gestures(time.monotonic()); time.sleep(0.02)
    return out
stuck = fresh(True)
check("a button that is down from the start is not a finger: no hold, no talking, nothing", run(stuck, 0.9) == [] and stuck.g.down is False)
stuck.touch_button(True, 0); got = run(stuck, 0.1); stuck.touch_button(False, 0); got += run(stuck, 0.1)
check("with the button stuck, a tap on the top of the screen is still one press", got == ["press"], got)
stuck.touch_button(True, 0); got = run(stuck, 0.8); stuck.touch_button(False, 0); got += run(stuck, 0.1)
check("and a finger held there is a hold, ended when it lifts", got == ["hold_start", "hold_end"], got)
stuck.touch_button(True, 0); stuck.touch_button(False, 0); got = run(stuck, 0.15)
check("a tap that comes and goes inside one frame is not lost and not left held", got == ["press"] and stuck.g.down is False, got)
StandInButton.is_pressed = False; run(stuck, 0.6)
StandInButton.is_pressed = True; got = run(stuck, 0.1); StandInButton.is_pressed = False; got += run(stuck, 0.1)
check("once the real button has been seen up, it is believed again", got == ["press"] and stuck._pin_ok, got)
good = fresh(False)
good.touch_button(True, 0); got = run(good, 0.1)
good.edges.append((False, time.monotonic())); got += run(good, 0.1)          # a stray release from the pin while a finger is down
check("a finger on the screen is not let go by the real button's pin", got == [] and good.g.down is True, got)
good.touch_button(False, 0); run(good, 0.1)
StandInButton.is_pressed = False
L = pi.pick_mic_card
check("microphone: the USB card is chosen whatever its number",
      L("**** List ****\ncard 0: vc4hdmi [vc4-hdmi], device 0: MAI PCM\ncard 3: Device [USB PnP Sound Device], device 0: USB Audio [USB Audio]") == 3)
check("microphone: with no USB card, the first card; with none, no microphone",
      L("card 2: sndrpihifiberry [snd_rpi_hifiberry_dac], device 0: x") == 2 and L("") is None and L("arecord: no soundcards found") is None)
box.record_start()
check("recording asks for the card that was found (card 1 here)", "plughw:1" in commands[-1], commands[-1:])
box.record_stop()

games, _ = load_games()
app = App(box, games, headless=False, flip=True)          # full screen and flipped, as on the Pi
app.push(Home(app))
ticks = []
app.stack[0].tick = ticks.append                          # a screen that keeps time, under whatever is on top
# The stand-in display only offers 1024x768, so the window size proves nothing here.
# On the box the panel has one mode, 800x480. That is for the real power-up to show.
check("the picture she draws is 800x480", app.surface.get_size() == (800, 480))

seen, notes = [], {}
real_gesture = app.gesture
def spy(name):
    seen.append(name)
    real_gesture(name)
app.gesture = spy

def push(secs):
    pin.drive_low(); time.sleep(secs); pin.drive_high()

def on_loop(fn):
    done = threading.Event()
    def job():
        try: fn()
        finally: done.set()
    app.later(job)
    done.wait(3)

def start_risk():
    risk = next(g["plugin"] for g in games if g["id"] == "risk")
    s = common.Setup(app, risk); app.push(s)
    s.n, s.names = 2, ["Ann", "Bob"] + s.names[2:]
    s.refresh(); s.start()

def tap_label(label):
    for w in app.screen.widgets:
        if getattr(w, "label", None) == label and w.action:
            x, y = w.rect.center                              # where it is drawn
            pos = (T.W - 1 - x, T.H - 1 - y)                  # where a finger lands on the flipped panel
            ww, wh = app.window.get_size()                    # the real panel sends fingers, not clicks
            fx, fy = (pos[0] + 0.5) / ww, (pos[1] + 0.5) / wh
            app.handle(pygame.event.Event(pygame.FINGERDOWN, x=fx, y=fy, touch_id=1, finger_id=0), 0)
            app.handle(pygame.event.Event(pygame.FINGERUP, x=fx, y=fy, touch_id=1, finger_id=0), 0)
            # where a system also sends the same touch as a click, that copy must not count twice
            app.handle(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos, touch=True), 0)
            app.handle(pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=pos, touch=True), 0)
            return True
    return False

def script():
    try:
        time.sleep(0.8)
        notes["idle_frames"] = len(spi.frames)
        on_loop(start_risk); time.sleep(0.4)
        notes["started"] = app.session is not None
        notes["turn_frame"] = decode(spi.frames[-1][1])
        for _ in range(3):
            push(0.08); time.sleep(0.6)
        notes["after_three"] = (len(app.session.log), list(seen))
        push(0.08); time.sleep(0.12); push(0.08); time.sleep(0.6)
        notes["after_double"] = (len(app.session.log), list(seen))
        n = len(seen)
        push(0.9); time.sleep(0.3)
        notes["hold"] = seen[n:]
        on_loop(app.go_home); time.sleep(0.3)
        n = len(seen)
        push(5.3); time.sleep(0.3)
        notes["long"] = seen[n:]
        notes["prompt"] = type(app.screen).__name__
        notes["shot"] = app.surface.copy()
        notes["window"] = app.window.copy()
        notes["before_off"] = len(spi.frames)
        on_loop(lambda: notes.__setitem__("tapped", tap_label("Shut down")))
        time.sleep(1.0)
    except Exception as e:
        notes["error"] = "%s: %s" % (type(e).__name__, e)
    finally:
        app.later(lambda: setattr(app, "running", False))

threading.Thread(target=script, daemon=True).start()
app.library.counts()                                          # she has her library open
t0 = time.monotonic()
app.run()                                                     # the real main loop
ran = time.monotonic() - t0
check("when the main loop stops she lets go of the library file", app._library is None)

check("a screen that keeps time is ticked every frame, even from under other screens", len(ticks) > 100 and ticks == sorted(ticks), len(ticks))
check("the script ran to the end", "error" not in notes, notes.get("error"))
check("the ring is being fed while idle on Home (breathing)", notes.get("idle_frames", 0) >= 5, notes.get("idle_frames"))
frames_ok = all(decode(d)[1] for _, d in spi.frames)
check("every frame sent is well-formed WS2812 data for 16 LEDs (%d frames)" % len(spi.frames), frames_ok)
gaps = [b[0] - a[0] for a, b in zip(spi.frames, spi.frames[1:])]
check("frames are never sent faster than the 30 a second it aims for", min(gaps) > 0.02, min(gaps))
check("a game starts", notes.get("started"))
colours, _ = notes.get("turn_frame", ([], False))
check("in a game the ring is lit for the player whose turn it is", any(c != (0, 0, 0) for c in colours), colours[:4])
n3, g3 = notes.get("after_three", (None, []))
check("three pushes of GPIO 17 arrive as three presses", g3 == ["press"] * 3, g3)
check("each press moved the game on by one event", n3 == 3, n3)
n4, g4 = notes.get("after_double", (None, []))
check("two quick pushes arrive as press then double", g4[3:] == ["press", "double"], g4)
check("the double took that press back and undid one more", n4 == 2, n4)
check("a 0.9 second push is a hold: start, then end on release", notes.get("hold") == ["hold_start", "hold_end"], notes.get("hold"))
check("a 5.3 second push on Home is a long hold", notes.get("long") == ["hold_start", "long_hold", "hold_end"], notes.get("long"))
check("the long hold asks before shutting down", notes.get("prompt") == "Choice", notes.get("prompt"))
if "shot" in notes:
    s, w = notes["shot"], notes["window"]
    same = all(s.get_at((x, y)) == w.get_at((799 - x, 479 - y)) for x in range(0, 800, 37) for y in range(0, 480, 29))
    check("the picture sent to the display is upside down, to suit the mounting", same)
check("a finger on the flipped panel lands on the Shut down button", notes.get("tapped") is True)
check("Shut down runs the safe power-off command once, though the touch came as a finger and again as a click", commands.count(["sudo", "systemctl", "poweroff"]) == 1, commands)
last, ok = decode(spi.frames[-1][1])
check("the last thing sent to the ring is all sixteen LEDs dark", ok and last == [(0, 0, 0)] * 16, last[:3])
check("and the main loop stops", app.running is False)
print("(ran in real time for %.1f seconds)" % ran)

print("\n%d failed" % len(fails)); sys.exit(1 if fails else 0)
