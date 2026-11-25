"""Improvise: a name, a shop or a rumour when the players wander off the page.

Two tiers. Offline, from the small word lists below, which were written for
this box: plain, generic fantasy, taken from no book, setting or adventure.
Or, when the cloud is switched on, one line from the cloud model, which is
told to keep clear of published settings too. Either way the result is marked
as invented wherever it is shown or kept. No screen code here."""
import random

KINDS = [("name", "Name"), ("shop", "Shop"), ("rumour", "Rumour")]
KIND_WORD = dict(KINDS)
MAX_TITLE, MAX_TEXT = 34, 130

# ---- a person
NAME_START = ["Al", "Bren", "Cor", "Dal", "El", "Fen", "Gar", "Hes", "Il", "Jor", "Kel", "Lor", "Mar", "Nel",
              "Or", "Per", "Quin", "Ros", "Sel", "Tam", "Ul", "Ver", "Wyn", "Yor"]
NAME_END = ["a", "an", "da", "en", "eth", "ia", "ic", "in", "is", "la", "na", "ith", "on", "or", "ra", "wyn"]
FAMILY_START = ["Ash", "Black", "Bright", "Cold", "Deep", "Elder", "Fair", "Grey", "Hollow", "Iron", "Long",
                "Marsh", "Oak", "Quick", "Red", "Stone", "Thorn", "Under", "Wind", "Winter"]
FAMILY_END = ["barrow", "brook", "field", "ford", "hand", "holt", "kettle", "mantle", "mere", "moor", "row",
              "shaw", "staff", "water", "well", "wick", "wood"]
MANNER = ["A tired", "A cheerful", "A suspicious", "A soft-spoken", "A loud", "A careful", "A forgetful",
          "A proud", "A nervous", "A patient", "A sharp-eyed", "A weary"]
TRADE = ["ferry keeper", "miller", "candle maker", "shepherd", "carter", "midwife", "cooper", "rat catcher",
         "bell ringer", "gravedigger", "well digger", "tinker", "charcoal burner", "toll keeper", "scribe",
         "night watchman", "beekeeper", "fishmonger"]
HABIT = ["hums when nervous", "never finishes a sentence", "counts everything twice", "is owed money by half the town",
         "talks to a dog that is not there", "keeps glancing at the door", "collects odd buttons",
         "claims to have seen the sea once", "laughs at the wrong moments", "trusts nobody with a clean cloak",
         "is saving up to leave", "knows every shortcut and takes none of them"]

# ---- a shop
SHOP_FIRST = ["Crooked", "Copper", "Sleeping", "Patient", "Last", "Mended", "Quiet", "Borrowed", "Lucky",
              "Dusty", "Second", "Leaning", "Honest", "Thirsty"]
SHOP_SECOND = ["Lantern", "Kettle", "Anvil", "Ladle", "Boot", "Barrel", "Needle", "Wheel", "Goose", "Candle",
               "Ledger", "Hammer", "Spoon", "Thimble"]
SHOP_KIND = ["A general store", "A smithy", "A bakery", "A tailor's", "A herb seller's", "A tavern",
             "A candle shop", "A barrel yard", "A stable", "A pawn counter", "A bookbinder's", "A cobbler's"]
SHOP_QUIRK = ["Prices drop for anyone who brings news.", "Nothing on the top shelf is for sale.",
              "It closes whenever it rains.", "The cat decides who gets served.", "Everything is slightly damp.",
              "Credit is given once, and remembered for ever.", "The back room is always locked.",
              "Half the stock belongs to somebody's cousin.", "It smells of smoke, and nobody says why.",
              "The sign has been wrong for years."]

# ---- a rumour
WHO = ["A stranger in a grey cloak", "The miller's youngest", "Somebody from over the hills", "An old soldier",
       "A pedlar nobody knows", "One of the night watch", "A child with muddy boots", "The oldest woman in town"]
DID = ["was seen digging", "has been buying far too much lamp oil", "heard singing", "lost three goats",
       "found fresh tracks", "left in a hurry", "has been asking after the party", "paid in very old coins",
       "saw lights moving", "will not go back"]
WHERE = ["by the old bridge", "behind the mill", "out past the last farm", "near the dry well",
         "on the north road", "at the edge of the wood", "under the hill", "down by the ford"]
DOUBT = ["Whether it is true is yours to decide.", "Half the town believes it.", "Nobody has checked.",
         "It gets better with each telling."]


def _cut(text, limit):
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[:limit - 1].rstrip(" ,.;:") + "…"


def person(rng=random):
    return "%s%s %s%s" % (rng.choice(NAME_START), rng.choice(NAME_END), rng.choice(FAMILY_START), rng.choice(FAMILY_END))


def invent(kind, rng=random):
    """One invented thing from the word lists: {"kind", "title", "text", "source": "offline"}."""
    if kind == "shop":
        title = "The %s %s" % (rng.choice(SHOP_FIRST), rng.choice(SHOP_SECOND))
        text = "%s, kept by %s. %s" % (rng.choice(SHOP_KIND), person(rng), rng.choice(SHOP_QUIRK))
    elif kind == "rumour":
        title = "A rumour"
        text = "%s %s %s. %s" % (rng.choice(WHO), rng.choice(DID), rng.choice(WHERE), rng.choice(DOUBT))
    else:
        kind, title = "name", person(rng)
        text = "%s %s who %s." % (rng.choice(MANNER), rng.choice(TRADE), rng.choice(HABIT))
    return {"kind": kind, "title": _cut(title, MAX_TITLE), "text": _cut(text, MAX_TEXT), "source": "offline"}


# ---- the cloud tier
SYSTEM = ("You invent small original details for a home tabletop fantasy game, for the person running it. "
          "Everything must be your own invention: use no name, place, character or wording from any published "
          "game setting, adventure, novel or film. Plain words, no exclamation marks, no markdown. "
          "Reply with exactly two lines and nothing else.")
ASK = {"name": "Invent one ordinary person the players might meet in a small frontier town. "
               "Line one: their full name only. Line two: one sentence, under twenty words, on their trade and one habit.",
       "shop": "Invent one shop or tavern in a small frontier town. Line one: its name only. "
               "Line two: one or two sentences, under twenty-five words in all, on what it sells, who keeps it and one oddity.",
       "rumour": "Invent one rumour going round a small frontier town. It may be false. Line one: the words A rumour. "
                 "Line two: the rumour itself in one sentence, under twenty-five words."}


def request(kind):
    return ASK.get(kind, ASK["name"])


def from_cloud(kind, reply):
    """Turn the model's reply into the same dict invent() gives, or None if
    there is nothing usable in it."""
    rows = [r.strip().strip("*#\"“” ").strip() for r in str(reply or "").split("\n")]
    rows = [r for r in rows if r]
    if not rows:
        return None
    kind = kind if kind in KIND_WORD else "name"
    if kind == "rumour":
        title, text = "A rumour", " ".join(r for r in rows if r.lower().rstrip(".:") != "a rumour")
    else:
        title, text = rows[0].rstrip(".:"), " ".join(rows[1:])
    if not text or not title:
        return None
    return {"kind": kind, "title": _cut(title, MAX_TITLE), "text": _cut(text, MAX_TEXT), "source": "cloud"}


def source_words(item):
    return "by the cloud model, just now" if item["source"] == "cloud" else "by me, from my own word lists"


# ---- keeping one
def keep(c, item):
    """Write an invented thing into the campaign file, marked as invented: a
    name joins the people, a shop or a rumour becomes a note on today's day.
    Returns where it went, in words."""
    if item["kind"] == "name":
        c["people"].append({"name": item["title"], "where": "", "role": "Invented. " + item["text"], "met": False,
                            "attitude": None, "your_note": "", "invented": True})
        return "Kept in People, marked Invented."
    day = c["calendar"]["day"]
    words = item["text"] if item["kind"] == "rumour" else "%s. %s" % (item["title"], item["text"])
    c["calendar"]["notes"].append({"day": day, "text": "Invented %s: %s" % (KIND_WORD[item["kind"]].lower(), words),
                                   "invented": True})
    return "Kept as a note on day %d, marked Invented." % day
