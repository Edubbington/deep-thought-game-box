"""Turns raw button edges into gestures. Knows nothing about what they mean.

  press       down and up inside HOLD seconds. Sent at once, on release.
  double      a second press inside DOUBLE seconds of the first. The first
              press has ALREADY been sent, so whoever handles "double" must
              take that press back as well as doing the undo.
  hold_start  the button has been down for HOLD seconds
  hold_end    released after a hold
  long_hold   still down after LONG seconds (shutdown prompt on Home)

Time is passed in, so this can be tested with a made-up clock.
"""
HOLD, DOUBLE, DEBOUNCE, LONG = 0.6, 0.35, 0.03, 5.0


class Gestures:
    def __init__(self):
        self.down = False
        self.t_edge = -1e9
        self.t_down = 0.0
        self.t_up = -1e9
        self.held = self.long = self.armed = False
        self.out = []

    def edge(self, down, t):
        """Call when the button goes down (True) or up (False)."""
        self.tick(t)
        if down == self.down or t - self.t_edge < DEBOUNCE:
            return
        self.down, self.t_edge = down, t
        if down:
            self.t_down, self.held, self.long = t, False, False
        elif self.held:
            self.out.append("hold_end")
            self.armed = False
        else:
            if self.armed and self.t_down - self.t_up <= DOUBLE:
                self.out.append("double")
                self.armed = False
            else:
                self.out.append("press")
                self.armed = True
            self.t_up = t

    def tick(self, t):
        """Call every frame so holds are noticed while the button is down."""
        if self.down and not self.held and t - self.t_down >= HOLD:
            self.held = True
            self.out.append("hold_start")
        if self.down and self.held and not self.long and t - self.t_down >= LONG:
            self.long = True
            self.out.append("long_hold")

    def take(self):
        out, self.out = self.out, []
        return out
