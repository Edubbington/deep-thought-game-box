"""Warhammer 40,000 arithmetic: turn order, command points, scoring caps,
unit strength and the wound roll. No screen code.

These are core mechanics restated as plain sums. Nothing here is a unit's
stats, a points value or a mission's wording: those stay on the players' own
datasheets and cards."""

PHASES = [("command", "Command"), ("movement", "Movement"), ("shooting", "Shooting"),
          ("charge", "Charge"), ("fight", "Fight")]
ORDER = [key for key, _ in PHASES]
END = "end"                      # after the last turn: final scores, then the result

LENGTHS = [("Full, 5 rounds", 5), ("Tutorial, 3 rounds", 3)]
# Shown on Set up for reference only. The box never checks an army against these.
GAME_SIZES = ["Combat Patrol", "Incursion 1,000", "Strike Force 2,000", "Onslaught 3,000"]

CP_PER_COMMAND = 1               # both players, in every Command phase
CP_WARN_ABOVE = 12               # more than this earns a remark, never a refusal

# ---------------------------------------------------------------- the scoring table
# EDIT THIS TABLE TO MATCH THE MISSION PACK ON THE TABLE.
#
# primary_from_round is from the Knowledge Base ("usually from the second
# battle round"). The Knowledge Base gives NO numbers for the caps, so the
# four values marked DEFAULT below are placeholders, not checked against the
# edition being played. Set a cap to None to switch it off.
SCORING = {
    "primary_from_round": 2,     # Knowledge Base: primary scores from battle round 2
    "primary_per_round": 15,     # DEFAULT, unverified: most primary one player scores in one battle round
    "primary_max": 50,           # DEFAULT, unverified: most primary one player scores in a game
    "secondary_max": 40,         # DEFAULT, unverified: most secondary one player scores in a game
    # One row per secondary a player works on at once (the Knowledge Base has
    # two drawn each Command phase). "max" caps that one row; None = no cap.
    # The names are plain labels: the card in the player's hand says what scores.
    "secondary_rows": [{"name": "Secondary 1", "max": None},      # DEFAULT, unverified: no cap per row
                       {"name": "Secondary 2", "max": None}],
}

MAX_UNITS = 12                   # per side; three pages of four on the screen
MAX_MODELS = 30                  # in one unit


def rounds_for(length):
    """Battle rounds for a Length choice. Anything that starts 'Tutorial' is 3."""
    return 3 if str(length or "").lower().startswith("tutorial") else 5


# ---------------------------------------------------------------- turn order
def step(phase, active, first, rnd, rounds):
    """What one press of Next leads to. Returns (phase, active, round).
    Five phases; then the other player's turn; then the next battle round.
    After the second player's Fight phase in the last round comes END."""
    if phase == END:
        raise ValueError("The last turn is over. Only the final scores remain.")
    i = ORDER.index(phase)
    if i + 1 < len(ORDER):
        return ORDER[i + 1], active, rnd
    if active == first:
        return ORDER[0], 1 - first, rnd
    if rnd >= rounds:
        return END, active, rnd
    return ORDER[0], first, rnd + 1


def cp_warning(cp):
    """True when a command point total is high enough to be worth a remark."""
    return cp > CP_WARN_ABOVE


# ---------------------------------------------------------------- scoring
def add_primary(by_round, rnd, delta, final=False, table=None):
    """Add (or take away) primary points. by_round has one slot per battle
    round and a last slot for end-of-game points. Returns the new list;
    raises ValueError if the table forbids it."""
    t = table or SCORING
    out = list(by_round)
    slot = len(out) - 1 if final else rnd - 1
    if delta > 0:
        if not final and rnd < t["primary_from_round"]:
            raise ValueError("Primary points start in battle round %d." % t["primary_from_round"])
        cap = t.get("primary_per_round")
        if not final and cap is not None and out[slot] + delta > cap:
            raise ValueError("Primary stops at %d in one battle round." % cap)
        cap = t.get("primary_max")
        if cap is not None and sum(out) + delta > cap:
            raise ValueError("Primary stops at %d for the game." % cap)
        out[slot] += delta
        return out
    need = -delta
    if need > sum(out):
        raise ValueError("There are no primary points to take away.")
    for k in [slot] + [k for k in range(len(out) - 1, -1, -1) if k != slot]:
        take = min(need, out[k])         # this round's points first, then the latest before it
        out[k] -= take
        need -= take
    return out


def add_secondary(rows, row, delta, table=None):
    """Add (or take away) points on one secondary row. Returns the new list."""
    t = table or SCORING
    out = list(rows)
    if not 0 <= row < len(out):
        raise ValueError("There is no such secondary row.")
    if out[row] + delta < 0:
        raise ValueError("That secondary has no points to take away.")
    if delta > 0:
        cap = t["secondary_rows"][row].get("max") if row < len(t["secondary_rows"]) else None
        if cap is not None and out[row] + delta > cap:
            raise ValueError("That secondary stops at %d." % cap)
        cap = t.get("secondary_max")
        if cap is not None and sum(out) + delta > cap:
            raise ValueError("Secondary points stop at %d for the game." % cap)
    out[row] += delta
    return out


# ---------------------------------------------------------------- named secondaries
# Each player has one row for every secondary they have worked on this game:
# {"name", "pts", "cap", "slot"}. slot is 0 or 1 for the two being worked on
# now, None for one that has been put away (its points still count). A slot
# that has not been named yet holds a plain row called "Secondary 1" or
# "Secondary 2". cap is the most that one named secondary may hold, or None.
MAX_SEC_ROWS = 24                # named secondaries one player may collect in a game
MAX_SEC_NAME = 24                # letters in a name


def sec_default(slot, table=None):
    """What an unnamed row in this slot is called."""
    return (table or SCORING)["secondary_rows"][slot]["name"]


def new_secs(table=None, points=None):
    """The rows a player starts with: one unnamed row per slot. points gives
    them a score each, which is how a game saved before names existed loads."""
    n = len((table or SCORING)["secondary_rows"])
    points = list(points or []) + [0] * n
    return [{"name": sec_default(k, table), "pts": int(points[k]), "cap": None, "slot": k} for k in range(n)]


def sec_at(rows, slot):
    """The row being worked on in this slot, or None."""
    return next((r for r in rows if r["slot"] == slot), None)


def sec_named(row, table=None):
    """False for a row that still has its plain 'Secondary 1' name."""
    return row["slot"] is None or row["name"] != sec_default(row["slot"], table)


def sec_points(rows):
    return sum(r["pts"] for r in rows)


def sec_clean(name):
    """A typed name, tidied: single spaces, a capital on each word, not too long."""
    name = name if isinstance(name, str) else ""          # letters that can be shown and saved, nothing else
    words = "".join(ch if ch.isprintable() else " " for ch in name).split()
    return " ".join(w[:1].upper() + w[1:] for w in words)[:MAX_SEC_NAME].strip()


def _sec_copy(rows, slot, table):
    t = table or SCORING
    if not isinstance(slot, int) or not 0 <= slot < len(t["secondary_rows"]):
        raise ValueError("There is no such secondary row.")
    out = [dict(r) for r in rows]
    if sec_at(out, slot) is None:            # should not happen; mend it rather than fail
        out.append({"name": sec_default(slot, t), "pts": 0, "cap": None, "slot": slot})
    return out, sec_at(out, slot), t


def sec_score(rows, slot, delta, table=None):
    """Add (or take away) points on the secondary in one slot. Returns new rows."""
    out, row, t = _sec_copy(rows, slot, table)
    if row["pts"] + delta < 0:
        raise ValueError("%s has no points to take away." % row["name"])
    if delta > 0:
        cap = row["cap"] if row.get("cap") is not None else t["secondary_rows"][slot].get("max")
        if cap is not None and row["pts"] + delta > cap:
            raise ValueError("%s stops at %d." % (row["name"], cap))
        cap = t.get("secondary_max")
        if cap is not None and sec_points(out) + delta > cap:
            raise ValueError("Secondary points stop at %d for the game." % cap)
    row["pts"] += delta
    return out


def sec_name(rows, slot, name, cap=None, table=None):
    """Name the secondary in a slot. An unnamed row, or one with no points,
    takes the new name. One that has scored is put away with its points and a
    new row starts at nothing. A name that was put away earlier comes back
    with the points it had. Returns new rows."""
    out, row, t = _sec_copy(rows, slot, table)
    name = sec_clean(name)
    if not name:
        raise ValueError("A secondary needs a name.")
    if cap is not None and (not isinstance(cap, int) or isinstance(cap, bool) or cap < 1):
        raise ValueError("A cap is a whole number of points, or nothing.")
    low = name.lower()
    if low in [r["name"].lower() for r in t["secondary_rows"]]:
        raise ValueError("That is what I call one with no name.")
    same = next((r for r in out if r["name"].lower() == low), None)
    if same is row:
        raise ValueError("That row is already %s." % row["name"])
    if same is not None and same["slot"] is not None:
        raise ValueError("%s is already in the other row." % same["name"])
    if same is None and (not sec_named(row, t) or row["pts"] == 0):
        if cap is not None and row["pts"] > cap:             # points scored before it had a name
            raise ValueError("%s stops at %d. This row already has %d." % (name, cap, row["pts"]))
        row["name"], row["cap"] = name, cap                  # the points, if any, stay with the row
        return out
    if row["pts"] == 0:
        out.remove(row)
    else:
        if not sec_named(row, t):
            raise ValueError("Name the row that has points before bringing %s back." % same["name"])
        row["slot"] = None
    if same is not None:
        same["slot"] = slot
    else:
        if len(out) >= MAX_SEC_ROWS:
            raise ValueError("%d secondaries is all I will list for one player." % MAX_SEC_ROWS)
        out.append({"name": name, "pts": 0, "cap": cap, "slot": slot})
    return out


def sec_away(rows, slot, table=None):
    """Put the named secondary in a slot away. Its points stay in the total;
    with no points it is simply forgotten. The slot goes back to an unnamed row."""
    out, row, t = _sec_copy(rows, slot, table)
    if not sec_named(row, t):
        raise ValueError("That row has no name to put away.")
    if row["pts"] == 0:
        out.remove(row)
    else:
        row["slot"] = None
    out.append({"name": sec_default(slot, t), "pts": 0, "cap": None, "slot": slot})
    return out


def sec_words(rows, table=None):
    """'Assassination 3, Cleanse 0; earlier: Sabotage 5': one player's
    secondaries in words. Unnamed rows with no points are left out."""
    now = ["%s %d" % (r["name"], r["pts"]) for k in range(len((table or SCORING)["secondary_rows"]))
           for r in [sec_at(rows, k)] if r and (sec_named(r, table) or r["pts"])]
    old = ["%s %d" % (r["name"], r["pts"]) for r in rows if r["slot"] is None]
    return "; ".join(x for x in (", ".join(now), "earlier: " + ", ".join(old) if old else "") if x)


def totals(by_round, rows):
    """(primary, secondary, total) for one player."""
    return sum(by_round), sum(rows), sum(by_round) + sum(rows)


def winner(score_a, score_b):
    """Seat of the player with more victory points, or None for a draw."""
    if score_a == score_b:
        return None
    return 0 if score_a > score_b else 1


# ---------------------------------------------------------------- units
def new_unit(name, size):
    size = max(1, min(MAX_MODELS, int(size)))
    return {"name": str(name), "start": size, "alive": size, "hurt": False, "shocked": False}


def below_half(start, alive, hurt=False):
    """Below half strength: fewer than half the models it started with.
    A unit that started as one model counts wounds instead, which the box
    cannot see, so its player marks it ('hurt'). A destroyed unit is not
    below half; it is gone."""
    if alive <= 0:
        return False
    if start == 1:
        return bool(hurt)
    return alive * 2 < start


def step_model(start, alive, hurt, delta):
    """Remove (delta -1) or restore (+1) one model. Returns (alive, hurt).
    A single-model unit goes whole -> below half its wounds -> destroyed."""
    if delta not in (-1, 1):
        raise ValueError("One model at a time.")
    if start == 1:
        level = (0 if alive <= 0 else 1 if hurt else 2) + delta
        if level < 0:
            raise ValueError("That unit is already destroyed.")
        if level > 2:
            raise ValueError("That unit is already at full strength.")
        return (0, False) if level == 0 else (1, level == 1)
    if alive + delta < 0:
        raise ValueError("That unit is already destroyed.")
    if alive + delta > start:
        raise ValueError("That unit is already at full strength.")
    return alive + delta, False


def needs_test(unit):
    """Does this unit take a battle-shock test in its player's Command phase?
    Yes if it is below half strength, or is still shocked from before."""
    if unit["alive"] <= 0:
        return False
    return bool(unit["shocked"]) or below_half(unit["start"], unit["alive"], unit["hurt"])


def units_alive(army):
    return sum(1 for u in army if u["alive"] > 0)


# ---------------------------------------------------------------- the wound roll
WOUND_ROWS = [("Strength is double the Toughness, or more", 2), ("Strength is higher", 3),
              ("Strength and Toughness are equal", 4), ("Strength is lower", 5),
              ("Strength is half the Toughness, or less", 6)]


def wound_roll(strength, toughness):
    """The number needed on one die to wound: 2, 3, 4, 5 or 6."""
    if strength < 1 or toughness < 1:
        raise ValueError("Strength and Toughness are at least 1.")
    if strength >= 2 * toughness:
        return 2
    if strength > toughness:
        return 3
    if strength == toughness:
        return 4
    if 2 * strength <= toughness:
        return 6
    return 5


# ---------------------------------------------------------------- the slow-play clock
# (label on the menu, seconds, the same in her words). The first is the default.
NUDGES = [("4 min", 240, "Four minutes"), ("8 min", 480, "Eight minutes"), ("Off", 0, "")]


class Pace:
    """A silent clock on the phase in hand. due() is asked many times a second
    with the time, and says True once, and only once, for each phase that runs
    past the limit. The time is whatever the caller passes in, so nothing here
    looks at a real clock."""

    def __init__(self):
        self.key, self.since, self.fired = None, 0.0, set()

    def restart(self):
        """Start timing afresh at the next due() (the limit was changed)."""
        self.key = None

    def due(self, key, now, limit):
        """key names the phase (None: nothing to time). limit is in seconds; 0 is off."""
        if key != self.key:                  # a new phase, or an old one come back by undo
            self.key, self.since = key, now
        if key is None or not limit or key in self.fired or now - self.since < limit:
            return False
        self.fired.add(key)                  # said once; undo and redo will not say it again
        return True
