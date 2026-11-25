"""The game engine: one session, an event log, undo, and saving after every event.

A game plugin is a subclass of Game. It owns the rules; the Session owns the
record. The state is a plain dict of numbers, strings and lists, so it can be
saved as JSON and a power cut mid-game loses nothing.
"""
import copy
import json
import os
import time

from . import paths

UNDO_DEPTH = 40


class Game:
    """Base class for a game plugin. Subclasses fill these in."""
    id = ""
    name = ""
    min_players, max_players = 2, 6
    options = []        # [{"key": "length", "label": "Length", "choices": ["Full", "Short"]}]
    folder = None       # set by the game list: where game.json and teach.json live
    info = None         # the game.json contents

    def new_state(self, players, options):
        raise NotImplementedError

    def apply(self, state, ev):
        """Change state for one event. Return a list of things to say.
        Raise ValueError to refuse an event; the state is then left alone."""
        raise NotImplementedError

    def press(self, state):
        """The event one press of the button makes."""
        return {"ev": "next"}

    def active(self, state):
        """Index of the player whose turn it is, or None."""
        return state.get("active")

    def phase(self, state):
        """A short key for the current phase, e.g. 'command'. Reminders hang off it."""
        return str(state.get("phase", ""))

    # Reminders are said when a player's turn reaches the phase. A game whose phases are
    # shared, with the players alternating inside them (Kill Team), sets this to False:
    # then every player's reminder is said once, when the phase begins.
    remind_each_turn = True
    # Phase keys that carry no reminders at all, not even "Every phase" ones: a
    # stretch of the game that is no player's (D&D: the enemies' turns).
    quiet_phases = ()

    def phases(self):
        """Every phase key a reminder could be tied to, with its display name."""
        return []

    def over(self, state):
        """None while playing; {"winner": name or None, "lines": [..]} when finished."""
        return None

    def leader(self, state):
        """Seat number of whoever is ahead, or None. Used when a game is stopped early."""
        return None

    def standings(self, state, players):
        """A line or two saying how things stood, for a game stopped early."""
        return ["Stopped early"]

    def strip(self, session):
        """(left text, title) for the top strip."""
        return self.name, ""

    def play_screen(self, app, session):
        raise NotImplementedError

    def teach(self):
        """Steps that teach the game, in the box's own words: [{"title", "text"}]."""
        path = os.path.join(self.folder or "", "teach.json")
        if not os.path.isfile(path):
            return []
        try:
            with open(path, encoding="utf-8") as f:
                steps = json.load(f)
        except (OSError, ValueError):
            return []                        # a hand-written file with a slip in it teaches nothing; it must not stop the box
        if not isinstance(steps, list):
            return []
        return [s for s in steps if isinstance(s, dict) and isinstance(s.get("title"), str)
                and isinstance(s.get("text"), str)]

    def marks(self, before, state, ev):
        """Extra moments the teaching steps may wait on (see guide.py), beyond the
        event's own name and a change of phase: e.g. ["knockout"] when this event
        put a player out by whatever route. before is the state as it was."""
        return []

    def phone(self, session, seat):
        """What one player's phone shows, and what they may do from it:
        {"lines": [str], "actions": [{"label": str, "ev": {...}}]}.
        Each action is an event for Session.do. Show nothing another player
        should not see. The default lets the active player press Next."""
        actions = [{"label": "Next", "ev": self.press(session.state)}] if self.active(session.state) == seat else []
        return {"lines": [], "actions": actions}

    def scoreboard(self, session):
        """What the shared web scoreboard shows. Never anything hidden."""
        return {"rows": [{"name": n, "value": ""} for n in session.players], "note": ""}


class Session:
    def __init__(self, game, players, options=None, folder=None, clock=time.time):
        self.game, self.clock, self.folder = game, clock, folder
        self.d = {"format": 1, "game": game.id, "players": list(players), "options": dict(options or {}),
                  "started": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(clock())),
                  "state": None, "log": [], "undo": [], "reminders": [],
                  "seconds": [0.0] * len(players), "finished": None}
        self.d["state"] = game.new_state(list(players), self.d["options"])
        self.t0 = self.t_last = clock()
        self.cards = []                  # teaching steps waiting to be shown (see guide.py); not saved
        self.path = None
        if folder:
            stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(clock()))
            self.path = os.path.join(folder, "%s-%s.json" % (stamp, game.id))
        self.save()

    # ---- shorthand
    @property
    def state(self):
        return self.d["state"]

    @property
    def players(self):
        return self.d["players"]

    @property
    def log(self):
        return self.d["log"]

    @property
    def finished(self):
        return self.d["finished"]

    def active_name(self):
        i = self.game.active(self.state)
        return self.players[i] if i is not None and 0 <= i < len(self.players) else None

    def _charge_clock(self):
        now, i = self.clock(), self.game.active(self.state)
        if i is not None and 0 <= i < len(self.d["seconds"]) and not self.finished:
            self.d["seconds"][i] += max(0.0, now - self.t_last)
        self.t_last = now

    # ---- events
    def do(self, **ev):
        """Apply one event. Returns the list of things to say."""
        if self.finished:
            return ["The game is over."]
        self._charge_clock()
        before = copy.deepcopy(self.state)
        where = (self.game.active(self.state), self.game.phase(self.state))
        try:
            said = list(self.game.apply(self.state, ev) or [])
        except ValueError as e:
            self.state.clear()               # put it back in place, so nobody holds a stale state
            self.state.update(before)
            return [str(e)]
        except Exception:                    # a fault in a plugin must not leave half an event behind
            self.state.clear()
            self.state.update(before)
            raise
        self.d["undo"] = (self.d["undo"] + [before])[-UNDO_DEPTH:]
        self.log.append(dict(ev, t=round(self.clock() - self.t0, 1)))
        now = (self.game.active(self.state), self.game.phase(self.state))
        if now != where and now[1] not in self.game.quiet_phases and (self.game.remind_each_turn or now[1] != where[1]):
            said += self.due_reminders()
        if self.d.get("guide"):
            from . import guide
            if not self.cards:
                self.guide_was = copy.deepcopy(self.d["guide"])     # so an unread card can be given again
            self.cards += guide.due(self, ev.get("ev"), where, self.game.marks(before, self.state, ev))
        result = self._named(self.game.over(self.state))
        if result:
            self.d["finished"] = dict(result, ended=time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(self.clock())),
                                      minutes=round((self.clock() - self.t0) / 60))
        self.save()
        return said

    def _named(self, result):
        """A plugin may name the winner or give their seat number."""
        if result and "winner" not in result:
            i = result.pop("winner_index", None)
            result["winner"] = self.players[i] if i is not None else None
        return result

    def undo(self):
        """Step back one event. Returns False when there is nothing to undo."""
        if not self.d["undo"]:
            return False
        self._charge_clock()
        self.d["state"] = self.d["undo"].pop()
        if self.log:
            self.log.pop()
        self.d["finished"] = None
        self.save()
        return True

    def finish(self, winner=None, lines=None):
        """End the game by hand (the players stopped)."""
        self._charge_clock()
        result = self._named(self.game.over(self.state))
        if not result:
            lead = self.game.leader(self.state)
            result = {"winner": winner or (self.players[lead] if lead is not None else None),
                      "lines": lines or self.game.standings(self.state, self.players)}
        self.d["finished"] = dict(result, ended=time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(self.clock())),
                                  minutes=round((self.clock() - self.t0) / 60),
                                  by_hand=True)      # no event ended it: taking the ending back undoes nothing
        self.save()

    # ---- reminders: each player's own "don't forget" lines, said at the right phase
    def add_reminder(self, player, phase, text):
        text = " ".join(str(text).split())[:120]
        if text:
            self.d["reminders"].append({"player": player, "phase": phase, "text": text})
            self.save()

    def remove_reminder(self, index):
        if 0 <= index < len(self.d["reminders"]):
            del self.d["reminders"][index]
            self.save()

    def due_reminders(self):
        """Reminders for the phase now starting. When it is one player's turn, theirs
        and everyone's. When the phase belongs to nobody (or the game says its
        phases are shared), every player's, each with the name."""
        i, phase = self.game.active(self.state), self.game.phase(self.state)
        shared = i is None or not self.game.remind_each_turn
        out = []
        for r in self.d["reminders"]:
            p = r.get("player")
            if r.get("phase") in (phase, "*") and (p is None or p == i or shared):
                who = self.players[p] if isinstance(p, int) and 0 <= p < len(self.players) else None
                out.append("Reminder%s: %s" % (" for " + who if who else "", r.get("text", "")))
        return out

    # ---- files
    def save(self):
        if not self.path:
            return
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        text = paths.json_text(self.d, ensure_ascii=False)     # always writable, whatever a player typed
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
        try:
            os.replace(tmp, self.path)      # never leaves a half-written game
        except OSError:                     # seen once on Windows (a scanner holding the file): try again
            time.sleep(0.05)
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(text)
            os.replace(tmp, self.path)
        _last_line.clear()

    def discard(self):
        """Throw the game away: its file goes, and nothing more is saved."""
        path, self.path = self.path, None
        if path:
            for p in (path, path + ".tmp"):
                try:
                    os.remove(p)
                except OSError:
                    pass
        _last_line.clear()

    @classmethod
    def load(cls, path, games, clock=time.time):
        """games: {id: Game}. Returns None if the file is for a game not on the box."""
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        game = games.get(d.get("game"))
        if not game:
            return None
        s = cls.__new__(cls)
        s.game, s.clock, s.folder, s.path, s.d = game, clock, os.path.dirname(path), path, d
        s.t_last = clock()
        s.cards = []
        s.t0 = clock() - (d["log"][-1]["t"] if d["log"] else 0)
        return s


def _mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def iter_sessions(folder):
    """Saved games, newest first, read one at a time: a caller that only wants
    the newest does not make a Pi read every game ever played.
    Unreadable files, and files that are not a saved game, are skipped."""
    if not os.path.isdir(folder):
        return
    names = [n for n in os.listdir(folder) if n.endswith(".json")]
    names.sort(key=lambda n: (_mtime(os.path.join(folder, n)), n), reverse=True)   # last played first
    for name in names:
        try:
            with open(os.path.join(folder, name), encoding="utf-8") as f:
                d = json.load(f)
        except (ValueError, OSError):
            continue
        if isinstance(d, dict) and isinstance(d.get("players"), list) and isinstance(d.get("log"), list) \
                and isinstance(d.get("game"), str):
            yield os.path.join(folder, name), d


def list_sessions(folder):
    """Every saved game, newest first: [(path, data)]."""
    return list(iter_sessions(folder))


_last_line = {}          # folder -> the line; emptied whenever any game is saved


def last_game_line(folder, names):
    """'Last game: Risk, Ethan won' for the Home screen."""
    if folder in _last_line:
        return _last_line[folder]
    line = None
    for _, d in iter_sessions(folder):
        fin = d.get("finished")
        if isinstance(fin, dict):
            who = "%s won" % fin["winner"] if fin.get("winner") else "no winner"
            line = "Last game: %s, %s" % (names.get(d["game"], d["game"]), who)
            break
    _last_line[folder] = line
    return line


def unfinished(folder):
    """The newest game that was started, has at least one event, and never ended."""
    for path, d in iter_sessions(folder):
        if not d.get("finished") and d.get("log"):
            return path, d
        break                                # only the newest counts
    return None


def duration_words(minutes):
    h, m = divmod(int(minutes), 60)
    if h and m:
        return "%d hour%s %d minutes" % (h, "" if h == 1 else "s", m)
    if h:
        return "%d hour%s" % (h, "" if h == 1 else "s")
    return "%d minute%s" % (m, "" if m == 1 else "s")
