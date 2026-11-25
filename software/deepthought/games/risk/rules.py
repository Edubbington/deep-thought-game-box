"""Risk arithmetic: armies, card sets and battle dice. No screen code.

These are the classic world-conquest rules, restated as sums."""
import random

TERRITORIES = 42
CONTINENTS = [("Asia", 7, 12), ("North America", 5, 9), ("Europe", 5, 7),
              ("Africa", 3, 6), ("South America", 2, 4), ("Australia", 2, 4)]   # name, bonus, territories
BONUS = {name: bonus for name, bonus, _ in CONTINENTS}
SIZE = {name: size for name, _, size in CONTINENTS}
START_ARMIES = {2: 40, 3: 35, 4: 30, 5: 25, 6: 20}
SET_VALUES = [4, 6, 8, 10, 12, 15]


def start_territories(players):
    """How the 42 territories split when dealt out evenly. Two players each
    get 14 and a neutral army holds the other 14."""
    if players == 2:
        return [14, 14], 14
    base, extra = divmod(TERRITORIES, players)
    return [base + (1 if i < extra else 0) for i in range(players)], 0


def set_value(sets_traded):
    """Armies for the next set traded in, given how many were traded before."""
    if sets_traded < len(SET_VALUES):
        return SET_VALUES[sets_traded]
    return 15 + 5 * (sets_traded - len(SET_VALUES) + 1)


def reinforcements(territories, continents=(), card_armies=0):
    """Armies at the start of a turn. Returns (total, how it was worked out)."""
    base = max(3, territories // 3)
    parts = ["%d territories ÷ 3 = %d" % (territories, territories // 3)]
    if territories // 3 < 3:
        parts[0] += ", so the minimum of 3"
    total = base
    for name in continents:
        total += BONUS[name]
        parts.append("%s +%d" % (name, BONUS[name]))
    if card_armies:
        total += card_armies
        parts.append("cards +%d" % card_armies)
    return total, "; ".join(parts)


def battle(attack_dice, defend_dice, rng=random):
    """One roll. Returns (attacker's dice, defender's dice, attacker losses,
    defender losses). Highest against highest, next against next; ties go to
    the defender."""
    if not 1 <= attack_dice <= 3:
        raise ValueError("The attacker rolls one, two or three dice.")
    if not 1 <= defend_dice <= 2:
        raise ValueError("The defender rolls one or two dice.")
    a = sorted((rng.randint(1, 6) for _ in range(attack_dice)), reverse=True)
    d = sorted((rng.randint(1, 6) for _ in range(defend_dice)), reverse=True)
    a_loss = d_loss = 0
    for x, y in zip(a, d):
        if x > y:
            d_loss += 1
        else:
            a_loss += 1
    return a, d, a_loss, d_loss
