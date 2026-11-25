#!/usr/bin/env python3
"""Start Deep Thought.

  python run.py                 run it. On a PC: a window (space bar = the button, Esc = quit,
                                F12 = screenshot). On the Pi: full screen, real hardware.
  python run.py --shots DIR     draw every screen to DIR as PNG files and exit
  python run.py --flip          draw upside down (the display is mounted that way in the box;
                                on the Pi this is the default, --no-flip turns it off)
  python run.py --no-web        do not serve the phone and scoreboard pages
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots")
    ap.add_argument("--flip", action="store_true")
    ap.add_argument("--no-flip", action="store_true")
    ap.add_argument("--no-web", action="store_true")
    ap.add_argument("--hw", default="auto", choices=["auto", "desktop", "pi"])
    a = ap.parse_args()
    if a.shots:
        os.environ["SDL_VIDEODRIVER"] = "dummy"
    from deepthought import hw, paths, persona, settings, voice, web
    from deepthought.app import App
    from deepthought.games import load_games
    from deepthought.screens.home import Home
    games, problems = load_games(extra=paths.data("games"))
    for p in problems:
        print("game not loaded:", p)
    hardware = hw.make("desktop" if a.shots else a.hw, sound=not a.shots)
    if hardware.name == "pi":
        # Found on the real Pi 2, 22 Nov 2026: with no desktop, the picture has to be drawn
        # through the graphics chip. Left to choose for itself, SDL sent a black screen.
        os.environ.setdefault("SDL_VIDEODRIVER", "kmsdrm")
        os.environ.setdefault("SDL_RENDER_DRIVER", "opengles2")
        os.environ.setdefault("SDL_FRAMEBUFFER_ACCELERATION", "opengles2")
    flip = (a.flip or hardware.name == "pi") and not a.no_flip
    app = App(hardware, games, headless=bool(a.shots), flip=flip)
    app.push(Home(app))
    if a.shots:
        from deepthought.shots import all_shots
        for path in all_shots(app, a.shots):
            print(path)
        return
    hardware.set_volume(settings.get("volume"))
    voice.attach(app)
    if not a.no_web:
        web.attach(app)
    for p in getattr(hardware, "problems", []):
        print("hardware:", p)
    app.say(persona.line("power_on"))
    try:
        app.run()
    finally:
        if app.web:
            app.web.stop()
        app.close_library()                  # after the pages have stopped: nothing new is left in content.db-wal


if __name__ == "__main__":
    main()
