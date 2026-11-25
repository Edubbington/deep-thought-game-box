#!/usr/bin/env python3
"""Make her stock lines into sound files ahead of time, so the box plays them
with no network and no wait.

  python tools/build_audio.py           # every stock line and every teaching step title
  python tools/build_audio.py --list    # show what would be made and what it would cost
  python tools/build_audio.py --teach   # also every How to play page, so Teach as we play
                                        # can read aloud with no network (costs more)

Needs the [speech] key in config.toml. Lines already made are skipped, so it
is safe to run again after adding lines. Changing the voice makes a new set.

First run against the live speech service on 22 Nov 2026.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deepthought import dice, persona, voice  # noqa: E402
from deepthought.screens.common import CLOSING  # noqa: E402


def all_lines():
    lines = [l for ls in persona.LINES.values() for l in ls]
    lines += [l for ls in dice.REMARKS.values() for l in ls]
    lines += CLOSING
    return sorted(set(lines))


def teach_pages():
    """Every How to play page of every game, as the words she reads out for it."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame
    pygame.display.init()
    pygame.font.init()
    from deepthought import paths
    from deepthought.games import load_games
    from deepthought.screens.common import paginate
    out = []
    for g in load_games(extra=paths.data("games"))[0]:
        if g.get("plugin"):
            steps = [(s["title"], s["text"]) for s in g["plugin"].teach()]
            out += [" ".join(l for l in lines if l) for _, lines in paginate(steps)] if steps else []
    return [t for t in out if t]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--teach", action="store_true")
    a = ap.parse_args()
    cfg = voice.load_config()

    class Quiet:                                   # just enough of an app for cache_file()
        hw = None
    v = voice.Voice.__new__(voice.Voice)
    v.cfg = cfg
    lines = sorted(set(all_lines() + (teach_pages() if a.teach else [])))
    todo = [l for l in lines if not os.path.isfile(v.cache_file(l))]
    chars = sum(len(l) for l in todo)
    print("%d lines, %d still to make, about $%.2f" % (len(lines), len(todo),
                                                       chars / 1000.0 * voice.TTS_DOLLARS_PER_1000_CHARS))
    if a.list:
        for l in todo:
            print("  " + l[:100])
        return
    if not cfg["speech"]["api_key"]:
        sys.exit("No speech key. Copy config.example.toml to config.toml and fill in [speech] api_key.")
    mended = 0
    for l in lines:                                          # lines made before the lengths were put right
        path = v.cache_file(l)
        if os.path.isfile(path):
            with open(path, "rb") as f:
                was = f.read()
            now = voice.full_volume(voice.true_lengths(was))
            if now != was:
                with open(path + ".part", "wb") as f:
                    f.write(now)
                os.replace(path + ".part", path)
                mended += 1
    if mended:
        print("%d lines already made had their lengths or loudness put right" % mended)
    for i, l in enumerate(todo, 1):
        for attempt in range(8):                             # found on the first live run: a new account
            try:                                             # is only allowed a few lines a minute
                audio = voice.text_to_speech(cfg, l)
                break
            except RuntimeError as e:
                if "(429)" not in str(e) or attempt == 7:
                    raise
                print("     the service asked me to slow down; waiting 25 seconds")
                time.sleep(25)
        with open(v.cache_file(l) + ".part", "wb") as f:     # a run that is stopped never leaves half a
            f.write(audio)                                   # sound that would count as made
        os.replace(v.cache_file(l) + ".part", v.cache_file(l))
        print("%3d/%d  %s" % (i, len(todo), l[:70]))


if __name__ == "__main__":
    main()
