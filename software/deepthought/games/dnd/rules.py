"""D&D arithmetic for the fight tracker. No screen code, no files.

Only names and sums live here: who goes when, the concentration save number,
the death save count. What a condition or a spell does is in the player's book."""

CONDITIONS = ["Blinded", "Charmed", "Deafened", "Exhaustion", "Frightened", "Grappled",
              "Incapacitated", "Invisible", "Paralyzed", "Petrified", "Poisoned", "Prone",
              "Restrained", "Stunned", "Unconscious"]
KINDS = ("character", "enemy", "ally")
KIND_NAME = {"character": "Character", "enemy": "Enemy", "ally": "Ally"}
ENEMY_NAMES = ["Enemy", "Goblin", "Bandit", "Wolf", "Skeleton", "Zombie", "Orc", "Cultist",
               "Guard", "Beast", "Spider"]
ALLY_NAMES = ["Ally", "Guard", "Guide", "Sidekick", "Hireling", "Companion", "Villager", "Animal"]
MAX_COMBATANTS = 24
MAX_GROUP = 8

# The DM's prep, seven steps, the same every session. Short enough for a button.
PREP = ["Recap read and fixed", "Book open at the page", "Fights loaded",
        "People skimmed", "Open quests checked", "Maps and handouts out",
        "One thing to cut chosen"]


def conc_dc(damage, edition="2024"):
    """The Constitution save to keep concentrating: 10, or half the damage
    rounded down, whichever is higher. The 2024 rules stop it at 30."""
    dc = max(10, int(damage) // 2)
    return min(30, dc) if str(edition).startswith("2024") else dc


def order(combatants):
    """Initiative order: highest first. A tie goes to whoever was marked as
    winning ties, then to whoever joined first. No initiative yet = last."""
    return sorted(combatants, key=lambda c: (c["init"] is None, -(c["init"] or 0), -c.get("tie", 0), c["id"]))


def next_turn(combatants, current_id):
    """Who acts after current_id. Returns (id, new_round). The dead are skipped.
    None when nobody can act."""
    full = order(combatants)
    live = [c for c in full if not c["dead"]]
    if not live:
        return None, False
    ids = [c["id"] for c in full]
    if current_id not in ids:
        return live[0]["id"], False
    i = ids.index(current_id)
    for step in range(1, len(full) + 1):
        j = i + step
        c = full[j % len(full)]
        if not c["dead"]:
            return c["id"], j >= len(full)
    return None, False


def next_up(combatants, acted):
    """Who acts next, given the ids of those who have had their turn this
    round: the highest in the order who is alive and has not. When everyone
    has, the first of the living, and a new round. Returns (id, new_round);
    (None, False) when nobody can act. Unlike next_turn this does not care
    where the last one to act now stands in the order, so correcting an
    initiative in the middle of a round costs nobody a turn."""
    live = [c for c in order(combatants) if not c["dead"]]
    if not live:
        return None, False
    left = [c for c in live if c["id"] not in acted]
    return (left[0]["id"], False) if left else (live[0]["id"], True)


def gone_by(combatants, current_id):
    """The ids of everyone at or before current_id in the order: the ones whose
    place in this round has already gone by."""
    ids = [c["id"] for c in order(combatants)]
    return ids[:ids.index(current_id) + 1] if current_id in ids else []


def death_save(passed_so_far, failed_so_far, passed, natural=None):
    """One death save. natural is 1 or 20 when the die showed it.
    Returns (passed, failed, result): result is None, 'stable', 'dead' or 'up'
    (a 20: back on 1 hit point)."""
    p, f = passed_so_far, failed_so_far
    if natural == 20:
        return 0, 0, "up"
    if natural == 1:
        f += 2
    elif passed:
        p += 1
    else:
        f += 1
    if f >= 3:
        return p, 3, "dead"
    if p >= 3:
        return 3, f, "stable"
    return p, f, None


def numbered(existing, base, count=1, always=True):
    """Names for new combatants: 'Goblin 1', 'Goblin 2'. A single typed name
    stays as typed unless it is already taken."""
    existing = set(existing)
    if count == 1 and not always and base not in existing:
        return [base]
    used = set()
    for name in existing:
        head, _, tail = name.rpartition(" ")
        if head == base and tail.isdigit():
            used.add(int(tail))
    if base in existing:
        used.add(1)
    out, n = [], (max(used) if used else 0)
    for _ in range(count):
        n += 1
        out.append("%s %d" % (base, n))
    return out


def joined(words):
    words = list(words)
    if len(words) < 2:
        return "".join(words)
    return ", ".join(words[:-1]) + " and " + words[-1]
