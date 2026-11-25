"""The list of games the box knows.

Each game is a folder here with a game.json in it. Adding a game to the box
starts with adding a folder. Fields of game.json:

  id       folder name; also the game name used in content.db
  name     what the tile says
  blurb    one short line under the name
  order    where it sits in the list (low first)

A game becomes playable in one of two ways:

  * the folder has a plugin.py with a class Plugin(Game), for games that need
    their own rules and screens; or
  * game.json has "trackers" and/or "phases", and the generic board-game
    plugin runs it from that data alone (see games/generic.py).

A folder with neither is listed as "Not built yet".
"""
import importlib
import json
import os

REQUIRED = ("id", "name", "blurb", "order")
HERE = os.path.dirname(os.path.abspath(__file__))


def _plugin_for(folder, name, g):
    if os.path.isfile(os.path.join(folder, name, "plugin.py")) and os.path.abspath(folder) == HERE:
        return importlib.import_module("deepthought.games.%s.plugin" % name).Plugin()
    if "trackers" in g or "phases" in g:
        from .generic import GenericGame
        return GenericGame(g)
    return None


def load_games(folder=None, extra=None):
    """Return (games, problems). A broken game is reported, not fatal.
    extra: a second folder of data-only games (the ones added from the web page)."""
    games, problems, seen = [], [], set()
    for root in [folder or HERE] + ([extra] if extra and os.path.isdir(extra) else []):
        for name in sorted(os.listdir(root)):
            path = os.path.join(root, name, "game.json")
            if not os.path.isfile(path) or name in seen:
                continue
            try:
                with open(path, encoding="utf-8") as f:
                    g = json.load(f)
                missing = [k for k in REQUIRED if k not in g]
                if missing:
                    raise ValueError("missing " + ", ".join(missing))
                if g["id"] != name:
                    raise ValueError("id %r does not match folder %r" % (g["id"], name))
                if isinstance(g["order"], bool) or not isinstance(g["order"], (int, float)):
                    raise ValueError("order must be a number")
                g["name"], g["blurb"] = str(g["name"]), str(g["blurb"])     # a name written as a number is still a name
                plugin = _plugin_for(root, name, g)
            except Exception as e:
                problems.append("%s: %s" % (name, e))
                continue
            if plugin:
                plugin.id, plugin.name = g["id"], g["name"]
                plugin.folder, plugin.info = os.path.join(root, name), g
            g["plugin"] = plugin
            g["status"] = "ready" if plugin else "planned"
            seen.add(name)
            games.append(g)
    games.sort(key=lambda g: (g["order"], g["name"]))
    return games, problems
