"""Answering a question: rulings log first, then the library, then the cloud.

Offline first. The cloud is asked only when it is switched on, a key is set
and this month's spend is under the cap; otherwise the best library section
is shown as it stands. Every answer is saved in the rulings log with its
source, so the same question gets the same answer next month.
"""
import json
import re
import threading
import time
from . import paths, persona

_lock = threading.RLock()                    # the voice worker, the screen and the web pages share the log

FILLER = {"what", "whats", "does", "do", "is", "are", "the", "a", "an", "mean", "means", "how", "can",
          "i", "you", "me", "tell", "about", "please", "of", "in", "to", "it", "work", "works", "when", "my"}
ALIASES = {"kt": "kill team", "tp": "turning point", "cp": "command points", "vp": "victory points",
           "invuln": "invulnerable save", "ac": "armour class", "hp": "hit points", "dm": "dungeon master",
           "apl": "action point limit"}


def normalise(question):
    """Lower case, no punctuation, known short forms spelt out, filler dropped.
    Two questions that normalise the same are the same question."""
    words = re.findall(r"[a-z0-9+']+", question.lower().replace("’", "'"))
    out = []
    for w in words:
        w = w.strip("'")
        if w in ALIASES:
            out += ALIASES[w].split()
        elif w and w not in FILLER:
            out.append(w)
    return " ".join(out)


# ---------------------------------------------------------------- rulings log
def rulings():
    with _lock:
        try:
            with open(paths.data("rulings.json"), encoding="utf-8") as f:
                log = json.load(f)
        except (OSError, ValueError):
            return []
    return [r for r in log if isinstance(r, dict)] if isinstance(log, list) else []


def save_ruling(game, question, answer, source, origin, dm=False):
    """dm marks a ruling that rests on DM-only pages (a campaign book), so
    it is never repeated to the players or listed on the Rulings web page."""
    with _lock:
        log = rulings()
        log.append({"date": time.strftime("%Y-%m-%d"), "game": game or "", "q": question, "norm": normalise(question),
                    "answer": answer, "source": source, "from": origin, "dm": bool(dm)})
        paths.write_json(paths.data("rulings.json"), log[-500:], ensure_ascii=False, indent=1)


def find_ruling(game, question, dm=False):
    """The ruling already given for this question. One given in DM mode is
    only found again in DM mode. Older rulings carry no mark and are for everyone."""
    norm = normalise(question)
    for r in reversed(rulings()):
        if norm and r.get("norm") == norm and r.get("game", "") == (game or "") and (dm or not r.get("dm")):
            return r
    return None


def forget_ruling(game, question):
    """Throw away a ruling that turned out wrong, so the next ask starts fresh."""
    norm = normalise(question)
    with _lock:
        keep = [r for r in rulings() if not (r.get("norm") == norm and r.get("game", "") == (game or ""))]
        paths.write_json(paths.data("rulings.json"), keep, ensure_ascii=False, indent=1)


# ---------------------------------------------------------------- the pipeline
def build_prompt(question, game_name, phase, excerpts, table=""):
    """table: what she can see of the game herself (the time, whose turn, the scores)."""
    parts = []
    if table:
        parts.append(table)
    if game_name:
        parts.append("Game on the table: %s%s." % (game_name, (", phase: %s" % phase) if phase else ""))
    if excerpts:
        parts.append("Your notes that came up for this question (the owner's own files and the box's own notes). "
                     "Some may be about something else entirely:")
        for i, (where, text) in enumerate(excerpts, 1):
            parts.append("[%d] %s\n%s" % (i, where, text))
    else:
        parts.append("Your notes have nothing on this question.")
    parts.append("The player asks: %s" % question)
    return "\n\n".join(parts)


def answer(question, library, game=None, game_name="", phase="", dm=False, llm=None, remember=True, table=""):
    """Returns {"text", "source", "from"}. `from` is one of:
    ruling (asked before), cloud, library (offline: the section itself), none.
    llm(system, user) -> text, or None when the cloud is not to be used. It may
    raise; any failure falls back to the library."""
    question = " ".join(question.split())
    if not normalise(question):
        return {"text": persona.line("nothing_found"), "source": "", "from": "none"}
    old = find_ruling(game, question, dm)
    if old:
        return {"text": old.get("answer", ""), "source": old.get("source", ""), "from": "ruling",
                "date": old.get("date", "an earlier night")}
    query = normalise(question)
    excerpts, scope = library.excerpts(query, game, dm=dm, limit=3), game
    if not excerpts:
        excerpts, scope = library.excerpts(query, None, dm=dm, limit=3), None
    # In DM mode with D&D on the table the question itself may give the plot away,
    # so the ruling is always the DM's alone. For any other game it is the DM's only
    # if a DM-only page was among the excerpts: that is so exactly when the players'
    # search would have found something else.
    secret = bool(dm) and (game == "dnd" or excerpts != library.excerpts(query, scope, dm=False, limit=3))
    source = "; ".join(where for where, _ in excerpts[:2])
    result, note = None, ""
    if llm:
        try:
            user = build_prompt(question, game_name, phase, excerpts, table)
            text = llm(persona.VOICE, user)
            if text and not persona.in_voice(text):       # one retry if she broke character
                text = llm(persona.VOICE, user + "\n\nAnswer again in plain sentences with no exclamation marks.")
            if text and persona.in_voice(text):
                result = {"text": " ".join(text.split()), "source": source or "from my own knowledge", "from": "cloud"}
        except Exception as e:                            # network, key, cap: never a crash
            note = str(e)
    if result is None and excerpts:
        where, text = excerpts[0]
        result = {"text": text[:900].strip(), "source": where, "from": "library"}
    if result is None:
        return {"text": persona.line("nothing_found"), "source": "", "from": "none", "note": note}
    if note:
        result["note"] = note
    if remember and result["from"] == "cloud":            # only real rulings are kept
        save_ruling(game, question, result["text"], result["source"], result["from"], dm=secret)
    return result
