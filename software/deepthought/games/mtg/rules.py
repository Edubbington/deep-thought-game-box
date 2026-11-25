"""Magic arithmetic: starting life, the steps of a turn, when a player is
out and when to warn them. No screen code.

These are the game's well-known numbers restated as sums. What any card
does is the card's business, not the box's."""

START_LIFE = {"standard": 20, "commander": 40}
POISON_OUT = 10             # poison counters that knock a player out
COMMANDER_OUT = 21          # combat damage from one commander that knocks a player out

# The steps of a turn, in order: (key, name on the strip).
STEPS = [("untap", "Untap"), ("upkeep", "Upkeep"), ("draw", "Draw"), ("main1", "First main"),
         ("combat", "Start of combat"), ("attackers", "Declare attackers"), ("blockers", "Declare blockers"),
         ("damage", "Combat damage"), ("endcombat", "End of combat"), ("main2", "Second main"),
         ("end", "End step"), ("cleanup", "Cleanup")]
STEP_NAME = dict(STEPS)
STEP_KEYS = [k for k, _ in STEPS]
FIRST_STEP = STEP_KEYS[0]
WHOLE_TURN = "main1"        # where the step sits when the button passes whole turns

# One line on what to do in each step, in the box's own words.
HINTS = {
    "untap": "Turn everything of yours upright again.",
    "upkeep": "Anything that happens at the start of your turn happens now.",
    "draw": "Draw one card.",
    "main1": "Play one land. Cast whatever you can pay for.",
    "combat": "Last chance for anyone to act before attackers are chosen.",
    "attackers": "Tap the creatures that attack. Say who each one attacks.",
    "blockers": "The defender picks which upright creatures block which attackers.",
    "damage": "Creatures deal damage equal to their power. Unblocked ones hit the player.",
    "endcombat": "Combat is done. Anything that lasts until end of combat stops.",
    "main2": "Play a land if you have not yet. Cast whatever you can pay for.",
    "end": "Anything that happens at the end of your turn happens now.",
    "cleanup": "Discard down to seven cards. Damage on creatures wears off.",
}
NO_DRAW = "No draw. Whoever goes first in a two-player game skips it on turn one."

WHY = {"life": "no life left", "poison": "ten poison counters",
       "commander": "21 damage from one commander", "other": "out of the game"}


def format_key(choice):
    """'Commander 40 life' -> 'commander'; anything else is a 20-life game."""
    return "commander" if "commander" in str(choice or "").lower() else "standard"


def start_life(fmt):
    return START_LIFE[fmt]


def grid(players):
    """Commander damage: grid[victim][source], all nought."""
    return [[0] * players for _ in range(players)]


def worst(cmd_row):
    """The most damage any single commander has dealt this player."""
    return max(cmd_row) if cmd_row else 0


def lost(life, poison, cmd_row=(), commander=False):
    """Why this player is out, or None. Life is checked first."""
    if life <= 0:
        return "life"
    if poison >= POISON_OUT:
        return "poison"
    if commander and worst(list(cmd_row)) >= COMMANDER_OUT:
        return "commander"
    return None


def warnings(life, poison, cmd_row=(), commander=False):
    """Which totals are one step from a knockout: any of 'life', 'poison', 'commander'."""
    out = []
    if life == 1:
        out.append("life")
    if poison == POISON_OUT - 1:
        out.append("poison")
    if commander and worst(list(cmd_row)) == COMMANDER_OUT - 1:
        out.append("commander")
    return out


def to_go(value, limit):
    """How many more before the limit is reached."""
    return max(0, limit - value)


def next_step(key):
    """The step after this one, or None when the turn is over."""
    i = STEP_KEYS.index(key)
    return STEP_KEYS[i + 1] if i + 1 < len(STEP_KEYS) else None


def next_alive(out, seat):
    """The next seat round the table that is still in the game, or None."""
    n = len(out)
    for k in range(1, n + 1):
        i = (seat + k) % n
        if not out[i]:
            return i
    return None
