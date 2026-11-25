"""The box's view of content.db. Wraps dt_content so screens get plain dicts
and never crash when the library is missing or empty."""
import functools
import os
import re
import sqlite3
import sys
import threading

from . import paths

sys.path.insert(0, paths.SOFTWARE)
import dt_content  # noqa: E402  (the loader module, kept where its tests expect it)


def locked(fn):
    """The screen, the voice worker and the web pages all read the library,
    from different threads. One at a time."""
    @functools.wraps(fn)
    def inner(self, *a, **k):
        with self.lock:
            if self.con is None and fn.__name__ != "close":
                self._open()                 # closed (a book was just loaded, say) and asked again: open it again
            return fn(self, *a, **k)
    return inner


SMALL = {"the", "of", "to", "a", "an", "in", "is", "it", "do", "me", "my", "you", "i"}   # dropped from a question before it gets here


def _words(text):
    """A name or a question as plain words, small words dropped, to compare the two."""
    return [w for w in re.findall(r"[a-z0-9]+", text.lower().replace("'", "")) if w not in SMALL]


def window(body, query, size=1200):
    """The part of a section that is about the question. Found on the real Pi, 23 Nov 2026:
    a long section was cut after its first 1,200 letters, so the line that answered the
    question was often missing. Now the stretch with the most of the question's words is taken."""
    if len(body) <= size:
        return body
    low = body.lower()
    words = {w for w in _words(query) if len(w) > 2}
    hits = sorted(m.start() for w in words for m in re.finditer(re.escape(w), low))[:400]
    best, most, first = 0, sum(1 for h in hits if h < size), 0
    for h in hits:
        start = max(0, h - 200)
        n = sum(1 for x in hits if start <= x < start + size)
        if n > most:
            best, most, first = start, n, h
    if best:
        line = body.rfind("\n", max(0, best - 200), first + 1)  # begin at the start of the line it is on, or of a word
        best = line + 1 if line != -1 else body.find(" ", best) + 1
    return body[best:best + size].strip()


class Library:
    def __init__(self, db_path=None):
        self.path = db_path or paths.content_db()
        self.con = None
        self.lock = threading.RLock()
        self._open()

    def _open(self):
        """Open content.db if it is there. Called at the start, and again by any
        use after close(): whoever still holds this library (the voice worker, in
        the middle of a question) must get the real pages, not an empty answer."""
        if not os.path.isfile(self.path):
            return
        try:                                              # a short wait: the screen must never hang on the
            self.con = sqlite3.connect(self.path, timeout=0.2, check_same_thread=False)   # library while a book loads
        except sqlite3.Error:
            self.con = None
        for setup in ("PRAGMA journal_mode=WAL", dt_content.SCHEMA):
            try:                                          # WAL: reading goes on while a web upload is indexed
                self.con and self.con.executescript(setup)
            except sqlite3.Error:
                pass

    @locked
    def close(self):
        """Put everything into content.db itself and let go of it. While any
        connection is open the newest pages can sit in content.db-wal beside it,
        and a copy of content.db alone would miss them."""
        con, self.con = self.con, None
        if con:
            try:
                con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except sqlite3.Error:
                pass
            try:
                con.close()
            except sqlite3.Error:
                pass

    @locked
    def counts(self):
        """(sections, cards). Both 0 when there is no library yet."""
        if not self.con:
            return 0, 0
        try:
            return (self.con.execute("SELECT count(*) FROM docs").fetchone()[0],
                    self.con.execute("SELECT count(*) FROM cards").fetchone()[0])
        except sqlite3.Error:
            return 0, 0

    @locked
    def games(self):
        if not self.con:
            return []
        try:
            out = [r[0] for r in self.con.execute("SELECT DISTINCT game FROM docs ORDER BY game")]
        except sqlite3.Error:
            return []
        if self.counts()[1] and "mtg" not in out:
            out.append("mtg")
        return out

    @locked
    def search(self, query, game=None, dm=False, limit=12):
        """Cards first (Magic only), then book sections. Each result is a dict:
        kind 'card' or 'doc', title, sub (source and page), snippet, id."""
        out = []
        if not self.con or not query.strip():
            return out
        try:
            if game in (None, "mtg"):
                for row in dt_content.find_cards(self.con, query, 4 if game is None else limit):
                    out.append({"kind": "card", "id": row[0], "title": row[1], "sub": row[3] or "Card",
                                "snippet": (row[4] or "").replace("\n", " ")})
            for source, ref, title, snip, mine, doc_id in dt_content.search(self.con, query, game, dm, limit):
                out.append({"kind": "doc", "id": doc_id, "title": "%s, %s" % (source, ref) if ref else source,
                            "sub": title or "", "snippet": " ".join(snip.replace("[", "").replace("]", "").split())})
        except sqlite3.Error:
            return out
        return out[:limit]

    @locked
    def doc(self, doc_id):
        try:
            row = self.con and self.con.execute("SELECT source,ref,title,body,dm_only FROM docs WHERE id=?", (doc_id,)).fetchone()
        except sqlite3.Error:
            row = None
        if not row:
            return None
        return {"title": "%s, %s" % (row[0], row[1]) if row[1] else row[0], "heading": row[2] or "",
                "body": row[3], "dm_only": bool(row[4])}

    @locked
    def card(self, oracle_id):
        try:
            row = self.con and self.con.execute(
                "SELECT name,mana_cost,type_line,oracle_text,power,toughness,loyalty FROM cards WHERE oracle_id=?",
                (oracle_id,)).fetchone()
            rulings = dt_content.card_rulings(self.con, oracle_id) if row else []
        except sqlite3.Error:
            row = None
        if not row:
            return None
        name, cost, type_line, text, p, t, loyalty = row
        stats = dt_content.power_toughness(p, t) if p else ("Loyalty %s" % loyalty if loyalty else "")
        body = "\n\n".join(x for x in (type_line, "Cost: " + dt_content.mana_words(cost), text, stats) if x)
        if rulings:
            body += "\n\nRulings:\n\n" + "\n\n".join("%s: %s" % (d, c) for d, c in rulings)
        return {"title": name, "heading": "Card data from Scryfall", "body": body, "dm_only": False}

    @locked
    def excerpts(self, query, game=None, dm=False, limit=3):
        """Top sections as (source and page, text) for a spoken question."""
        out = []
        card = self.named_card(query) if game in (None, "mtg") else None
        if card:                                          # a Magic card asked for by name: its own text first
            out.append(("Card data from Scryfall, " + card["title"], card["body"][:1200]))
        for r in self.search(query, game, dm, limit + 4):
            if r["kind"] == "doc" and len(out) < limit:
                d = self.doc(r["id"])
                if d:
                    out.append((d["title"], window(d["body"], query)))
        return out

    @locked
    def named_card(self, query):
        """The Magic card whose whole name is in the question, or None. The longest name wins.
        One word alone counts only when it is the whole question: 'ward' in a sentence is a rule."""
        words = _words(query)
        if not self.con or not words:
            return None
        try:
            for n in range(min(6, len(words)), 0, -1):
                if n == 1 and len(words) > 1:
                    break
                for i in range(len(words) - n + 1):
                    want = words[i:i + n]
                    rows = self.con.execute(
                        "SELECT c.oracle_id, c.name FROM cards_fts f JOIN cards c ON c.oracle_id = f.oracle_id "
                        "WHERE cards_fts MATCH ? LIMIT 40", ("name : (%s)" % " AND ".join('"%s"' % w for w in want),)).fetchall()
                    for oid, name in rows:
                        if _words(name) == want:
                            return self.card(oid)
        except sqlite3.Error:
            return None
        return None
