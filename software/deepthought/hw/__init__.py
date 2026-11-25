"""The hardware layer. The rest of the program only talks to this.

  desktop   space bar = the button, ring drawn beside the screen, default sound
  pi        GPIO 17 button, WS2812 ring on GPIO 10, I2S amp, USB microphone

Every backend offers:
  gestures(t)            list of gesture names since the last call
  key_event(event, t)    desktop only: feed it pygame key events
  touch_button(down, t)  a finger on the top strip of the screen, standing in for the button
  ring(behaviour, **kw)  name the ring behaviour to show
  ring_frame(t)          the 16 colours for now
  tick_sound()           the soft tick on Next
  set_volume(percent)    0 to 100
  play(path)             play a WAV file; stop_sound() stops it
  has_mic()              is there a microphone
  record_start()         start recording a question
  record_stop()          stop; returns the WAV path, or None
  shutdown()             power off safely (does nothing on the desktop)
"""


def make(name="auto", sound=True):
    if name == "auto":
        from .pi import is_pi
        name = "pi" if is_pi() else "desktop"
    if name == "desktop":
        from .desktop import DesktopHardware
        return DesktopHardware(sound=sound)
    if name == "pi":
        from .pi import PiHardware
        return PiHardware(sound=sound)
    raise ValueError("no hardware backend called %r" % name)
