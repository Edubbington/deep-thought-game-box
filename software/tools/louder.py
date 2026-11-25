"""Bring every line already recorded up to full volume. Safe to run again: a line
already loud is left alone.   python3 tools/louder.py"""
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deepthought import paths, voice  # noqa: E402

changed = 0
files = sorted(glob.glob(paths.data("speech", "*.wav")))
for path in files:
    with open(path, "rb") as f:
        was = f.read()
    now = voice.full_volume(voice.true_lengths(was))
    if now != was:
        with open(path + ".part", "wb") as f:
            f.write(now)
        os.replace(path + ".part", path)
        changed += 1
print("%d of %d lines made louder" % (changed, len(files)))
