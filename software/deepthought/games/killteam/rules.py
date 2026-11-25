"""Kill Team sums. No pygame, no screens: only the arithmetic the box enforces.

The box stores the shape of the scoring (three ops, a cap on each, a bonus at
the end). What a Crit Op or Tac Op actually asks for is on the players' cards.
"""

CATS = [("crit", "Crit Op"), ("tac", "Tac Op"), ("kill", "Kill Op")]
CAT_NAME = dict(CATS)
CAP = 6                 # each of the three ops stops at 6 points
BONUS_MAX = 3           # the primary-op bonus stops at 3
START_CP = 2            # Knowledge Base, Part 2: both sides start with 2
FULL, TUTORIAL = 4, 2   # turning points in a full game and in a first game
GRADES = 5
MIN_OPS, MAX_OPS, DEFAULT_OPS = 1, 20, 6


MAX_TAC_NAME = 24       # letters in the name a player gives their Tac Op


def tac_clean(name):
    """A typed Tac Op name, tidied: single spaces, a capital on each word, not
    too long. The box holds no list of them: the player types what is on
    their own card."""
    name = name if isinstance(name, str) else ""          # letters that can be shown and saved, nothing else
    words = "".join(ch if ch.isprintable() else " " for ch in name).split()
    return " ".join(w[:1].upper() + w[1:] for w in words)[:MAX_TAC_NAME].strip()


def tac_open(turning_point, phase):
    """Can a recorded Tac Op still be changed? Only until the first Firefight
    phase begins. After that it stays as it is until it is revealed."""
    return turning_point == 0 or (turning_point == 1 and phase in ("setup", "strategy"))


def cp_gain(turning_point, initiative):
    """Command points each side gains in the Strategy phase: [side 0, side 1].
    Turning point 1: one each. Afterwards: one for whoever has the initiative,
    two for the other."""
    if turning_point <= 1:
        return [1, 1]
    return [1 if side == initiative else 2 for side in (0, 1)]


def grade_marks(start):
    """How many of a team's operatives must be gone for the enemy to reach
    kill grades 1 to 5.

    CHECK AGAINST YOUR RULEBOOK. The Knowledge Base says only that the grades
    are fractions of the starting number. This uses one fifth of the starting
    number per grade, rounded to the nearest whole operative (never less than
    one for grade 1, never more than the whole team). If your book's table
    differs, this one function is the place to change it."""
    start = max(1, int(start))
    out = []
    for g in range(1, GRADES + 1):
        need = (2 * start * g + 5) // 10          # start * g / 5, rounded to nearest
        need = max(need, 1, (out[-1] if out else 0))
        out.append(min(need, start))
    return out


def kill_grade(start, lost):
    """The kill grade the enemy has reached against a team that started with
    `start` operatives and has lost `lost`. 0 to 5."""
    return sum(1 for need in grade_marks(start) if lost >= need)


def primary_bonus(score):
    """End of the game: half the points scored on the chosen op, rounded up,
    and never more than 3."""
    return min(BONUS_MAX, (max(0, int(score)) + 1) // 2)


def total(vp, bonus=0):
    return sum(vp[c] for c, _ in CATS) + bonus


def crit_open(turning_point, phase):
    """Can Crit Op points exist yet? Nothing scores from it in turning point 1,
    so the first chance is the End phase of turning point 2."""
    return turning_point > 2 or (turning_point == 2 and phase == "end")


def next_active(active, left):
    """Who activates after `active` finishes one. left: ready operatives per
    side, already counted down. The other side if it has any; otherwise the
    same side keeps going; None when nobody has any left."""
    other = 1 - active
    if left[other] > 0:
        return other
    if left[active] > 0:
        return active
    return None


def first_active(initiative, left):
    """Who starts the Firefight phase: the initiative holder, if they have
    anyone to activate."""
    if left[initiative] > 0:
        return initiative
    if left[1 - initiative] > 0:
        return 1 - initiative
    return None


def counteract(active, left, alive):
    """The side that may counteract: it has nothing ready, it still has
    operatives on the table, and the other side is still activating."""
    if active is None:
        return None
    other = 1 - active
    if left[other] == 0 and alive[other] > 0 and left[active] > 0:
        return other
    return None


def result(vp, bonus):
    """Final totals and the winner's seat (None for a draw)."""
    totals = [total(vp[i], bonus[i]) for i in (0, 1)]
    winner = None if totals[0] == totals[1] else totals.index(max(totals))
    return totals, winner


# ---------------------------------------------------------------- the slow-play clock
# (label on the menu, seconds, the same in her words). The first is the default.
NUDGES = [("90 s", 90, "Ninety seconds"), ("3 min", 180, "Three minutes"), ("Off", 0, "")]


class Pace:
    """A silent clock on the activation in hand. due() is asked many times a
    second with the time, and says True once, and only once, for each
    activation that runs past the limit. The time is whatever the caller
    passes in, so nothing here looks at a real clock."""

    def __init__(self):
        self.key, self.since, self.fired = None, 0.0, set()

    def restart(self):
        """Start timing afresh at the next due() (the limit was changed)."""
        self.key = None

    def due(self, key, now, limit):
        """key names the activation (None: nothing to time). limit is in seconds; 0 is off."""
        if key != self.key:                  # a new activation, or an old one come back by undo
            self.key, self.since = key, now
        if key is None or not limit or key in self.fired or now - self.since < limit:
            return False
        self.fired.add(key)                  # said once; undo and redo will not say it again
        return True
