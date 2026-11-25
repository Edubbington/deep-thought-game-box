"""The dome ring's named behaviours, as plain arithmetic.

frame(behaviour, t, ...) returns 16 (r, g, b) values for time t in seconds.
The desktop stand-in draws them; the Pi backend will send them to the LEDs.
Brightness is capped at half (Spec section 9).
"""
import math

N = 16
CAP = 127
IDLE = (60, 120, 255)
AMBER = (255, 170, 0)
ROUND_COLOURS = {"blue": (40, 110, 255), "teal": (0, 200, 190), "green": (40, 220, 90),
                 "amber": AMBER, "red": (255, 40, 30)}
BEHAVIOURS = ("breathe", "round", "turn", "spin", "thinking", "listening", "flare", "warn", "off")


def _scale(colour, k):
    k = max(0.0, min(1.0, k)) * CAP / 255.0
    return tuple(int(c * k) for c in colour)


def frame(behaviour, t, colour=IDLE, side=0, level=0.0, t0=0.0):
    if behaviour == "breathe":
        k = 0.12 + 0.88 * (0.5 - 0.5 * math.cos(2 * math.pi * t / 4.0))
        return [_scale(IDLE, k)] * N
    if behaviour == "round":                 # active side's half pulses slowly
        pulse = 0.55 + 0.45 * (0.5 - 0.5 * math.cos(2 * math.pi * t / 2.0))
        half = N // 2
        return [_scale(colour, pulse if (i // half) == side else 0.3) for i in range(N)]
    if behaviour == "turn":                  # whole ring in the active player's colour
        k = 0.6 + 0.4 * (0.5 - 0.5 * math.cos(2 * math.pi * t / 3.0))
        return [_scale(colour, k)] * N
    if behaviour == "spin":                  # first-player spinner: slows, stops on `side`
        dur, turns = 3.0, 4
        p = min(1.0, max(0.0, (t - t0) / dur))
        pos = (turns * N + side) * (1 - (1 - p) ** 3)
        head = int(pos) % N
        return [_scale(colour, 1.0 if i == head else 0.04) for i in range(N)]
    if behaviour == "thinking":             # one dot chasing, with a short tail
        head = int(t / 1.2 * N) % N
        tail = {head: 1.0, (head - 1) % N: 0.35, (head - 2) % N: 0.1}
        return [_scale(IDLE, tail.get(i, 0.0)) for i in range(N)]
    if behaviour == "listening":             # ring fills with the mic level
        lit = int(round(max(0.0, min(1.0, level)) * N))
        return [_scale((255, 255, 255), 1.0 if i < lit else 0.06) for i in range(N)]
    if behaviour == "flare":                 # bright flash, gone after 1.5 s
        k = max(0.0, 1.0 - (t - t0) / 1.5)
        return [_scale(colour, k * k)] * N
    if behaviour == "warn":                  # amber double blink
        p = t % 1.6
        on = p < 0.15 or 0.3 <= p < 0.45
        return [_scale(AMBER, 1.0 if on else 0.0)] * N
    if behaviour == "off":
        return [(0, 0, 0)] * N
    raise ValueError("no ring behaviour called %r" % behaviour)


class RingState:
    """Remembers which behaviour is showing. A flare plays once, then the
    ring goes back to whatever it was doing. A spin starts when it is first
    drawn and then stays pointing. Both backends use this."""

    def __init__(self):
        self.now = ("breathe", {})
        self.before = None
        self.started = None

    def set(self, behaviour, **kw):
        frame(behaviour, 0.0, **kw)          # fail at once if the name is wrong
        if behaviour == "flare" and self.now[0] != "flare":
            self.before = self.now
        self.started = None                  # timed behaviours start on the next frame
        self.now = (behaviour, kw)

    def frame(self, t):
        behaviour, kw = self.now
        if behaviour in ("flare", "spin"):
            if self.started is None:
                self.started = t
            if behaviour == "flare" and t - self.started >= 1.5:
                self.now = self.before or ("breathe", {})
                return frame(self.now[0], t, **self.now[1])
            return frame(behaviour, t, t0=self.started, **kw)
        return frame(behaviour, t, **kw)
