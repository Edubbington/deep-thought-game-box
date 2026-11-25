"""Desktop stand-ins for the box's hardware."""
import array
import math
import pygame
from .. import ring as ring_mod
from ..gestures import DEBOUNCE, Gestures


class DesktopHardware:
    name = "desktop"

    def __init__(self, sound=True):
        self.g = Gestures()
        self._ring = ring_mod.RingState()
        self._tick = None
        if sound:
            try:
                pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=512)
                n = 24000 * 40 // 1000
                wave = array.array("h", (int(6000 * math.sin(2 * math.pi * 880 * i / 24000) * (1 - i / n))
                                         for i in range(n)))
                self._tick = pygame.mixer.Sound(buffer=wave.tobytes())
            except pygame.error:
                self._tick = None            # no sound device: carry on silently

    def key_event(self, event, t):
        if event.key == pygame.K_SPACE:
            self._want = event.type == pygame.KEYDOWN
            self.g.edge(self._want, t)

    def touch_button(self, down, t):
        """A finger on the strip across the top of the screen stands in for the button."""
        self._want = bool(down)
        self.g.edge(self._want, t)

    def gestures(self, t):
        want = getattr(self, "_want", None)          # a tap that came and went inside one frame: its
        if want is not None and want != self.g.down and t - self.g.t_edge >= DEBOUNCE:   # release fell inside the
            self.g.edge(want, t)                     # debounce, so it is caught up here
        self.g.tick(t)
        return self.g.take()

    def ring(self, behaviour, **kw):
        self._ring.set(behaviour, **kw)

    def ring_frame(self, t):
        return self._ring.frame(t)

    def tick_sound(self):
        if self._tick:
            self._tick.play()

    def shutdown(self):
        pass                                 # on the desktop the window just closes

    def set_volume(self, percent):
        self.volume = max(0, min(100, int(percent)))
        if self._tick:
            self._tick.set_volume(self.volume / 100.0)

    # ---- sound files and the microphone
    def play(self, path):
        """Play a WAV file (her speech, or a soundboard clip)."""
        try:
            if not pygame.mixer.get_init():
                return
            sound = pygame.mixer.Sound(path)
            sound.set_volume(getattr(self, "volume", 70) / 100.0)
            pygame.mixer.Channel(1).play(sound)
        except (pygame.error, FileNotFoundError):
            pass

    def stop_sound(self):
        if pygame.mixer.get_init():
            pygame.mixer.Channel(1).stop()

    def has_mic(self):
        return False                         # on the desktop, questions are typed

    def record_start(self):
        pass

    def record_stop(self):
        return None
