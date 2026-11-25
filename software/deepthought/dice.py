"""Dice: the rolling, the one-line summary and Deep Thought's remark.

No screen code here, so all of it can be tested with a seeded random.
"""
import random

SIDES = (6, 3, 20)
MAX_DICE = 36
WORDS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
         "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
         "eighteen", "nineteen", "twenty"]
FACE_PLURAL = {1: "ones", 6: "sixes"}
FACE_SINGLE = {1: "one", 6: "six"}


def number(n):
    return WORDS[n] if 0 <= n < len(WORDS) else str(n)


def roll(n, sides=6, rng=random):
    """Roll n dice. Highest first, as players sort them on the table."""
    if sides not in SIDES:
        raise ValueError("no D%s here" % sides)
    n = max(1, min(MAX_DICE, int(n)))
    return sorted((rng.randint(1, sides) for _ in range(n)), reverse=True)


def _count(k, face):
    if k == 1:
        return "One " + FACE_SINGLE[face]
    return "%s %s" % (number(k).capitalize(), FACE_PLURAL[face])


def summary(results, sides=6):
    """The headline under the dice."""
    n, total = len(results), sum(results)
    if sides == 20:
        if n == 1:
            return {20: "Natural twenty", 1: "Natural one"}.get(results[0], "Rolled %d" % results[0])
        return "Highest %d, lowest %d" % (max(results), min(results))
    if sides == 3:
        return "Total %d" % total
    sixes, ones = results.count(6), results.count(1)
    parts = []
    if sixes:
        parts.append(_count(sixes, 6))
    if ones:
        parts.append(_count(ones, 1).lower() if parts else _count(ones, 1))
    if not sixes and not ones:
        parts.append("No sixes, no ones")
    text = ", ".join(parts)
    if n <= 3:
        text += " · total %d" % total
    return text


def mood(results, sides=6):
    """Which kind of remark the roll deserves."""
    n, top = len(results), results.count(sides)
    low = results.count(1)
    if n >= 2 and top == n:
        return "all_high"
    if n >= 2 and low == n:
        return "all_low"
    if sides == 20 and n == 1 and top:
        return "all_high"
    if sides == 20 and n == 1 and low:
        return "all_low"
    if sides == 6 and n >= 3 and top * 2 >= n:
        return "good"
    if sides == 6 and n >= 4 and top == 0:
        return "poor"
    return "plain"


# Deep Thought's own words. Several for each mood so she does not repeat herself.
REMARKS = {
    "all_high": [
        "Every one of them. I shall be checking those dice later.",
        "A perfect roll. Statistically, you have now used up your luck for the year.",
        "I have calculated universes less likely than that. Not many.",
        "All of them. I would like a word with whoever made those dice.",
        "Perfection. Enjoy it. It will not come again tonight.",
        "Every die at its best. I find that faintly suspicious.",
        "A flawless roll. Somewhere, a statistician has fainted.",
        "The maximum. I have nothing to add, and that is rare.",
        "That is as good as it gets. I did the sum twice.",
        "Extraordinary. Please do not let it go to your head.",
    ],
    "all_low": [
        "All ones. I would say something comforting, but I was not built for it.",
        "Remarkable. It takes real commitment to roll that badly.",
        "The dice have considered your plan and rejected it in full.",
        "Nothing but ones. I did not know the dice held a grudge.",
        "The worst possible roll. There is a certain purity to it.",
        "All ones. The dice have spoken, and they were not kind.",
        "A complete failure. I say that as a neutral observer.",
        "As low as it can go. At least it cannot get worse.",
        "Ones across the board. I shall look away.",
        "That roll will be remembered. Not fondly.",
    ],
    "good": [
        "I worked out the odds of that. You would not have liked them.",
        "Better than you deserve. I say that with great affection, or something like it.",
        "The dice appear to be on your side. Do not get used to it.",
        "A fine roll. I allowed it.",
        "Well above average. Luck, obviously, but well above average.",
        "That will do nicely.",
        "Strong numbers. Someone across the table has stopped smiling.",
        "A good roll. Try not to look so surprised.",
        "The odds were against that. The odds are often wrong about you.",
        "Rather good. I am almost impressed.",
        "Fortune favours you, for the moment.",
        "A healthy roll. Spend it wisely.",
        "Better than expected, and I expect a great deal.",
        "That landed well. I take no credit.",
        "Good. The dice are in a generous mood.",
    ],
    "poor": [
        "Not a six among them. The universe is vast and largely indifferent.",
        "I have seen more threatening rolls from a tea trolley.",
        "No sixes. I computed this outcome some time ago and chose not to mention it.",
        "A weak roll. It happens, mostly to you.",
        "Below average. I am sure it was the table.",
        "That was not what you hoped for. I could tell.",
        "Poor. The dice owe you nothing, and they know it.",
        "A feeble showing. Roll again when the rules allow, and not before.",
        "Low numbers. I have recorded them without comment. Almost.",
        "Unlucky. Or possibly just accurate.",
        "The dice were not listening to you.",
        "A disappointing handful. I have seen worse, though not recently.",
        "That roll helps nobody at this end of the table.",
        "Not your best. I hope.",
        "Meagre. Courage. There are more dice where those came from.",
    ],
    "plain": [
        "An unremarkable roll. I have recorded it anyway.",
        "Numbers. I have seen so very many of them.",
        "There. Entirely average, which is more than can be said for most things.",
        "It took me seven and a half million years to answer one question. That took a moment.",
        "Rolled. Do carry on.",
        "A roll. It was fine.",
        "Middling. Neither of us will remember it.",
        "Noted.",
        "An ordinary roll for an ordinary moment.",
        "About what one would expect. I did expect it.",
        "Average. The universe tends that way.",
        "Dice have been rolled. Play continues.",
        "Unexciting, but legal.",
        "That is a roll. I have nothing sharper to say about it.",
        "Right in the middle. How safe.",
        "Recorded. Carry on.",
        "Perfectly adequate numbers.",
    ],
}


def remark(results, sides=6, recent=(), rng=random):
    """Pick a line for this roll, avoiding the last two she used."""
    lines = [l for l in REMARKS[mood(results, sides)] if l not in list(recent)[-2:]]
    return rng.choice(lines or REMARKS[mood(results, sides)])
