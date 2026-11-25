"""Settings kept between runs, in data/settings.json. Keys and API keys live in
config.toml instead (see voice.py). The only private things here are the DM
code and the table code for the web pages, and both are shown on the box.
The data folder is never in git."""
import json
import os
import threading
from . import paths

_lock = threading.RLock()                    # the screen and the web pages both read and write

DEFAULTS = {"volume": 70, "chatty": "normal", "dm_code": "0000", "cloud": True, "flip": False,
            "web_lock": True, "web_code": "", "web_key": ""}
CHATTY = ("chatty", "normal", "terse")


def load():
    out = dict(DEFAULTS)
    with _lock:
        try:
            with open(paths.data("settings.json"), encoding="utf-8") as f:
                out.update(json.load(f))
        except (OSError, ValueError, TypeError):
            pass
    return out


def get(key):
    return load().get(key, DEFAULTS.get(key))


def put(key, value):
    with _lock:                              # read, change and write as one step
        d = load()
        d[key] = value
        path = paths.data("settings.json")
        with open(path + ".tmp", "w", encoding="utf-8") as f:
            json.dump(d, f, indent=1)
        os.replace(path + ".tmp", path)      # a power cut never leaves half a file
    return value
