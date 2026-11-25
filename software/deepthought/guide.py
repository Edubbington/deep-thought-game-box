"""Teach as we play: the How to play steps, given one at a time while a real
game is tracked, each at the moment it matters.

A step in a game's teach.json is {"title", "text"} plus, optionally, one of:

  "after":   wait for something before showing this step, in its place in the order
  "trigger": show this step once, the first time something happens, whenever that is

Both take an event name ("capture": the event a button on the play screen
makes), or "phase:<key>" (the game has just entered that phase), or a mark the
game itself raises (Game.marks: Magic raises "knockout" when a player goes out
by any route), or a list of those. A mark that is not a string is ignored. If the button is set to pass whole turns, so that phases never change,
a step waiting on a phase is given when the turn passes instead.

Steps with neither are shown straight after the step before them. So a file
with no "after" at all is simply read out at the start of the game.

The place reached is kept in the saved game, so a resumed game carries on and
an undone step is not taught twice. Kill Team and Warhammer 40,000 have their
own Teach mode and do not use this.
"""

OPTION = {"key": "guide", "label": "Teach", "choices": ["Off", "As we play"]}


def offered(game):
    """Should Set up offer Teach: As we play for this game?"""
    if any(o["key"] in ("mode", "guide") for o in game.options):
        return False                              # the game has a Teach mode of its own
    steps = game.teach()
    return bool(steps) and (any(s.get("after") or s.get("trigger") for s in steps) or not game.options)


def start(session):
    """Turn the guide on for this game. Returns the steps to show before play begins."""
    session.d["guide"] = {"i": 0, "taught": []}
    return due(session)


def _hit(cond, ev, before, now, waiting=False, marks=()):
    """before and now are (active player, phase) either side of the event."""
    if not cond or ev is None:
        return False
    if isinstance(cond, list):
        return any(_hit(c, ev, before, now, waiting, marks) for c in cond)
    if not isinstance(cond, str):
        return False                              # a slip in a hand-written file: never matches
    if cond.startswith("phase:"):
        if now[1] == cond[6:] and before[1] != now[1]:
            return True
        return waiting and before[1] == now[1] and before[0] != now[0]     # the turn passed, the phase never moves
    return cond == ev or cond in marks


def due(session, ev=None, before=None, marks=()):
    """The steps to show now. ev is the name of the event that has just been
    applied (None at the start of the game); before is (active player, phase)
    as they were before it; marks are the extra moments the game says this
    event was (Game.marks)."""
    g = session.d.get("guide")
    if not g:
        return []
    steps = session.game.teach()
    now = (session.game.active(session.state), session.game.phase(session.state))
    before = before or now
    marks = [m for m in (marks or ()) if isinstance(m, str)]
    main = [s for s in steps if not s.get("trigger")]
    out, i, first = [], g["i"], True
    while i < len(main):
        cond = main[i].get("after")
        if cond and not (first and _hit(cond, ev, before, now, True, marks)):
            break                                 # this one is still waiting
        out.append(main[i])
        i, first = i + 1, False
    g["i"] = i
    for s in steps:
        if s.get("trigger") and s["title"] not in g["taught"] and _hit(s["trigger"], ev, before, now, False, marks):
            g["taught"].append(s["title"])
            out.append(s)
    return out


def waiting_for(session):
    """The step the guide is waiting to give next, or None. For the tests and the menu."""
    g = session.d.get("guide")
    main = [s for s in session.game.teach() if not s.get("trigger")]
    return main[g["i"]] if g and g["i"] < len(main) else None
