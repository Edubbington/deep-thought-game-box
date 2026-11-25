#!/usr/bin/env python3
"""Deep Thought content loader.

Builds content.db, the box's searchable library. Four kinds of content go in:

  free/   official free downloads (core rules PDFs, faction packs, the D&D SRD)
  mine/   your own copies of books you own (PDF, EPUB, text, Markdown)
  Magic   every card and ruling, from Scryfall's bulk files
  Magic   the Comprehensive Rules text file from Wizards

Nothing in this file contains any rules text. It only reads files you give it.

Usage (run on a PC, then copy content.db to the Pi; it also runs on the Pi):

  python3 dt_content.py sync  CONTENT_DIR            # index free/ and mine/
  python3 dt_content.py fetch-mtg CONTENT_DIR        # download Scryfall bulk files
  python3 dt_content.py mtg-cards oracle-cards.json [--rulings rulings.json]
  python3 dt_content.py mtg-rules MagicCompRules.txt
  python3 dt_content.py search "restrained" [--game dnd]
  python3 dt_content.py card "llanowar"
  python3 dt_content.py stats

CONTENT_DIR layout (game folder names: wh40k, killteam, dnd, mtg, risk, or any new game):

  content/free/wh40k/Core Rules.pdf
  content/free/dnd/SRD_CC_v5.2.1.pdf
  content/mine/dnd/Players Handbook.pdf
  content/mine/dnd/campaigns/Curse of Strahd.pdf     <- DM-only (see below)

Anything under a folder named "campaigns" is marked DM-only, so the player
lookup never shows it and the box never reads it aloud outside DM mode.
"""
import argparse, hashlib, html, json, os, posixpath, re, sqlite3, sys, time, urllib.parse, zipfile

DB_DEFAULT = "content.db"
GAMES = ("wh40k", "killteam", "dnd", "mtg")
TEXT_EXT = (".txt", ".md", ".markdown")
MAX_CHUNK = 3500  # characters; keeps answers short enough to read on a 5" screen

SCHEMA = """
CREATE TABLE IF NOT EXISTS files(
  path TEXT PRIMARY KEY, sha1 TEXT, game TEXT, source TEXT, mine INTEGER,
  dm_only INTEGER, chunks INTEGER, empty_pages INTEGER, added REAL);
CREATE TABLE IF NOT EXISTS docs(
  id INTEGER PRIMARY KEY, path TEXT, game TEXT, source TEXT, kind TEXT,
  title TEXT, ref TEXT, page INTEGER, body TEXT, mine INTEGER, dm_only INTEGER);
CREATE INDEX IF NOT EXISTS docs_path ON docs(path);
CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(
  title, body, content='docs', content_rowid='id', tokenize='porter unicode61');
CREATE TABLE IF NOT EXISTS cards(
  oracle_id TEXT PRIMARY KEY, name TEXT, mana_cost TEXT, cmc REAL,
  type_line TEXT, oracle_text TEXT, power TEXT, toughness TEXT, loyalty TEXT,
  colors TEXT, color_identity TEXT, keywords TEXT, layout TEXT,
  legalities TEXT, set_name TEXT, rarity TEXT, faces TEXT);
CREATE VIRTUAL TABLE IF NOT EXISTS cards_fts USING fts5(
  name, type_line, oracle_text, oracle_id UNINDEXED, tokenize='unicode61');
CREATE TABLE IF NOT EXISTS rulings(
  oracle_id TEXT, published_at TEXT, source TEXT, comment TEXT);
CREATE INDEX IF NOT EXISTS rulings_oid ON rulings(oracle_id);
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
"""


def connect(db):
    con = sqlite3.connect(db)
    try:                                               # WAL: the box can go on reading while a book is loaded
        con.execute("PRAGMA journal_mode=WAL")
    except sqlite3.Error:
        pass                                           # a read-only folder: the old way still works
    con.executescript(SCHEMA)
    return con


def is_busy(error):
    """Is this the library file being held by another program, and nothing worse?"""
    words = str(error).lower()
    return "locked" in words or "busy" in words


def set_meta(con, key, value):
    con.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (key, str(value)))


# ---------------------------------------------------------------- text helpers
def clean(text):
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("­", "")
    text = re.sub(r"-\n(?=[a-z])", "", text)          # re-join hyphenated line breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_long(text, limit=MAX_CHUNK):
    """Split on paragraph breaks so no chunk is longer than limit."""
    if len(text) <= limit:
        return [text] if text else []
    out, cur = [], ""
    for para in re.split(r"\n\s*\n", text):
        while len(para) > limit:                      # one giant paragraph
            cut = para.rfind(" ", 0, limit)
            cut = cut if cut > 0 else limit
            if cur:
                out.append(cur); cur = ""
            out.append(para[:cut]); para = para[cut:].lstrip()
        if len(cur) + len(para) + 2 > limit and cur:
            out.append(cur); cur = para
        else:
            cur = (cur + "\n\n" + para) if cur else para
    if cur:
        out.append(cur)
    return out


def read_text_file(path):
    raw = open(path, "rb").read()
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


# ---------------------------------------------------------------- file readers
def read_pdf(path):
    """Yield (title, ref, page, text). One row per page; empty pages counted."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ValueError("PDF support needs pypdf:  pip install pypdf")
    empty = 0
    with open(path, "rb") as f:                        # an open file, so pypdf reads from disk as it goes
        reader = PdfReader(f)                          # (given a name it loads the whole book into memory)
        for n, page in enumerate(reader.pages, 1):
            try:
                text = clean(page.extract_text() or "")
            except Exception:
                text = ""
            if len(text) < 20:
                empty += 1
                continue
            first = text.split("\n", 1)[0][:80]
            for part in split_long(text):
                yield first, "p. %d" % n, n, part
    yield None, None, None, empty                      # sentinel: empty-page count


def read_markdown(path):
    """Yield one row per heading section; title is the heading trail."""
    trail, buf = [], []
    def flush():
        body = clean("\n".join(buf))
        if body:
            title = " > ".join(t for _, t in trail) or os.path.basename(path)
            for part in split_long(body):
                yield title, title, None, part
    for line in read_text_file(path).split("\n"):
        m = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", line)
        if m:
            yield from flush()
            buf = []
            level = len(m.group(1))
            trail = [(l, t) for l, t in trail if l < level] + [(level, m.group(2))]
        else:
            buf.append(line)
    yield from flush()


def read_plain(path):
    name = os.path.splitext(os.path.basename(path))[0]
    for i, part in enumerate(split_long(clean(read_text_file(path))), 1):
        yield name, "part %d" % i, None, part


def read_epub(path):
    """EPUBs without copy protection only. Reads chapters in spine order."""
    z = zipfile.ZipFile(path)
    names = z.namelist()
    if any(n.lower().endswith("encryption.xml") for n in names):
        raise ValueError("this EPUB is copy-protected; the loader cannot read it")
    opf = next((n for n in names if n.lower().endswith(".opf")), None)
    order = []
    if opf:
        x = z.read(opf).decode("utf-8", "replace")
        items = dict(re.findall(r'<item\b[^>]*?\bid="([^"]+)"[^>]*?\bhref="([^"]+)"', x))
        items.update({i: h for h, i in re.findall(
            r'<item\b[^>]*?\bhref="([^"]+)"[^>]*?\bid="([^"]+)"', x)})
        base = os.path.dirname(opf)
        for idref in re.findall(r'<itemref\b[^>]*?\bidref="([^"]+)"', x):
            if idref in items:                         # links may be written "chapter%201.xhtml" or "../Text/one.xhtml"
                href = urllib.parse.unquote(html.unescape(items[idref]).split("#")[0])
                order.append(posixpath.normpath(posixpath.join(base, href)))
    if not order:
        order = sorted(n for n in names if n.lower().endswith((".xhtml", ".html", ".htm")))
    for ch, name in enumerate(order, 1):
        if name not in names:
            continue
        x = z.read(name).decode("utf-8", "replace")
        m = re.search(r"<h[1-3][^>]*>(.*?)</h[1-3]>", x, re.S | re.I)
        title = clean(html.unescape(re.sub(r"<[^>]+>", " ", m.group(1)))) if m else "Chapter %d" % ch
        x = re.sub(r"<(script|style)\b.*?</\1>", " ", x, flags=re.S | re.I)
        x = re.sub(r"</(p|div|h[1-6]|li|tr)>|<br\s*/?>", "\n\n", x, flags=re.I)
        text = clean(html.unescape(re.sub(r"<[^>]+>", " ", x)))
        for part in split_long(text):
            yield title, "ch. %d" % ch, None, part


READERS = {".pdf": read_pdf, ".epub": read_epub, ".md": read_markdown,
           ".markdown": read_markdown, ".txt": read_plain}


# ---------------------------------------------------------------- adding files
def sha1_of(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def remove_file(con, path):
    for (rid, title, body) in con.execute("SELECT id,title,body FROM docs WHERE path=?", (path,)).fetchall():
        con.execute("INSERT INTO docs_fts(docs_fts,rowid,title,body) VALUES('delete',?,?,?)", (rid, title, body))
    con.execute("DELETE FROM docs WHERE path=?", (path,))
    con.execute("DELETE FROM files WHERE path=?", (path,))


def add_file(con, path, game, source=None, mine=False, dm_only=False, key=None):
    """Index one file. Returns (chunks, empty_pages) or None if unchanged."""
    ext = os.path.splitext(path)[1].lower()
    if ext not in READERS:
        return None
    key = key or os.path.abspath(path)
    digest = sha1_of(path)
    row = con.execute("SELECT sha1 FROM files WHERE path=?", (key,)).fetchone()
    if row and row[0] == digest:
        return None
    remove_file(con, key)
    source = source or os.path.splitext(os.path.basename(path))[0]
    kind = "campaign" if dm_only else ("book" if mine else "official")
    chunks = empty = 0
    for title, ref, page, body in READERS[ext](path):
        if title is None:                               # PDF sentinel
            empty = body
            continue
        cur = con.execute(
            "INSERT INTO docs(path,game,source,kind,title,ref,page,body,mine,dm_only) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (key, game, source, kind, title, ref, page, body, int(mine), int(dm_only)))
        con.execute("INSERT INTO docs_fts(rowid,title,body) VALUES(?,?,?)", (cur.lastrowid, title, body))
        chunks += 1
    con.execute("INSERT OR REPLACE INTO files VALUES(?,?,?,?,?,?,?,?,?)",
                (key, digest, game, source, int(mine), int(dm_only), chunks, empty, time.time()))
    return chunks, empty


def sync(con, content_dir, log=print):
    """Index everything under content_dir/free and content_dir/mine.
    Removes index entries for files that have been deleted."""
    seen, report = set(), []
    for bucket, mine in (("free", False), ("mine", True)):
        top = os.path.join(content_dir, bucket)
        found = sorted(d for d in os.listdir(top) if os.path.isdir(os.path.join(top, d))) if os.path.isdir(top) else []
        for game in list(GAMES) + [d for d in found if d not in GAMES]:   # any folder is a game
            root = os.path.join(content_dir, bucket, game)
            if not os.path.isdir(root):
                continue
            for dirpath, _, names in os.walk(root):
                rel_dirs = os.path.relpath(dirpath, root).lower().split(os.sep)
                dm_only = "campaigns" in rel_dirs
                for name in sorted(names):
                    path = os.path.join(dirpath, name)
                    ext = os.path.splitext(name)[1].lower()
                    key = os.path.relpath(path, content_dir).replace(os.sep, "/")
                    if ext not in READERS:
                        if not name.startswith(".") and ext not in (".json", ".jsonl", ".gz", ".part"):
                            report.append((key, "skipped: file type not supported"))
                        continue
                    seen.add(key)
                    try:
                        res = add_file(con, path, game, mine=mine, dm_only=dm_only, key=key)
                    except sqlite3.OperationalError as e:
                        con.rollback()
                        if is_busy(e):                  # the library file is held by something else: nothing is
                            report.append((key, "BUSY: %s" % e))    # wrong with this file, and it stays to be read next time
                        else:                           # a full card, a damaged library: say what it was
                            report.append((key, "FAILED: %s" % e))
                        continue
                    except Exception as e:              # one bad file must not stop the rest
                        con.rollback()                  # and leaves nothing half-loaded behind
                        report.append((key, "FAILED: %s" % e))
                        continue
                    if res is None:
                        continue
                    chunks, empty = res
                    note = "%d sections" % chunks
                    if empty:
                        note += "; %d pages had no readable text" % empty
                    if chunks == 0:
                        note = "NO TEXT FOUND: this looks like a scan. Run it through OCR first."
                    report.append((key, note))
                    con.commit()
    for (key,) in con.execute("SELECT path FROM files").fetchall():
        if key not in seen and (key.startswith("free/") or key.startswith("mine/")):
            remove_file(con, key)
            report.append((key, "removed (file no longer in the folder)"))
    set_meta(con, "last_sync", time.strftime("%Y-%m-%d %H:%M"))
    con.commit()
    for key, note in report:
        log("%-60s %s" % (key, note))
    if not report:
        log("Nothing new.")
    return report


# ---------------------------------------------------------------- searching
def fts_query(q, mode="AND"):
    words = re.findall(r"[A-Za-z0-9']+", q)
    words = [w for w in words if len(w) > 1 or w.isdigit()]
    return (" %s " % mode).join('"%s"' % w.replace('"', "") for w in words)


def search(con, q, game=None, dm=False, limit=5):
    """Return [(source, ref, title, snippet, mine, doc_id)], best first.
    dm=False hides DM-only material (campaign books)."""
    for mode in ("AND", "OR"):
        fq = fts_query(q, mode)
        if not fq:
            return []
        sql = ("SELECT d.source,d.ref,d.title,snippet(docs_fts,1,'[',']',' ... ',40),d.mine,d.id "
               "FROM docs_fts JOIN docs d ON d.id=docs_fts.rowid WHERE docs_fts MATCH ?")
        args = [fq]
        if game:
            sql += " AND d.game=?"; args.append(game)
        if not dm:
            sql += " AND d.dm_only=0"
        sql += " ORDER BY bm25(docs_fts, 6.0, 1.0) LIMIT ?"; args.append(limit)
        rows = con.execute(sql, args).fetchall()
        if rows:
            return rows
    return []


# ---------------------------------------------------------------- Magic cards
def open_text(path):
    """Open a text file for reading, unpacking it on the way if it is gzipped."""
    with open(path, "rb") as f:
        packed = f.read(2) == b"\x1f\x8b"
    if packed:
        import gzip
        return gzip.open(path, "rt", encoding="utf-8")
    return open(path, "r", encoding="utf-8")


def iter_json_records(path):
    """The objects in a Scryfall bulk file, one at a time, whichever way it was
    shipped: one big JSON array (the old way), or one object to a line (the way
    since 2026), either of them gzipped or not."""
    with open_text(path) as f:
        first = f.read(1)
        while first and first.isspace():
            first = f.read(1)
    if first == "[":
        for obj in iter_json_array(path):
            yield obj
        return
    with open_text(path) as f:
        for line in f:
            line = line.strip().rstrip(",")
            if line:
                yield json.loads(line)


def iter_json_array(path, chunk=1 << 16):
    """Stream the objects of one big JSON array without loading it all.
    (The Scryfall file is far bigger than a Pi 2's memory once parsed.)"""
    dec = json.JSONDecoder()
    with open_text(path) as f:
        buf, started = "", False
        while True:
            block = f.read(chunk)
            buf += block
            while True:
                buf = buf.lstrip()
                if not started:
                    if not buf:
                        break
                    if buf[0] != "[":
                        raise ValueError("not a JSON array")
                    buf, started = buf[1:], True
                    continue
                if buf[:1] == ",":
                    buf = buf[1:]; continue
                if buf[:1] == "]":
                    return
                if not buf:
                    break
                try:
                    obj, end = dec.raw_decode(buf)
                except json.JSONDecodeError:
                    break                              # need more data
                yield obj
                buf = buf[end:]
            if not block:
                if buf.strip():
                    raise ValueError("file ends in the middle of a card")
                return


SKIP_LAYOUTS = {"token", "double_faced_token", "emblem", "art_series"}


def _face_text(card):
    faces = card.get("card_faces") or []
    def pick(field):
        if card.get(field) not in (None, ""):
            return card[field]
        vals = [f.get(field, "") for f in faces if f.get(field)]
        return " // ".join(vals)
    return pick


def load_cards(con, cards_path, rulings_path=None, log=print):
    con.execute("DELETE FROM cards"); con.execute("DELETE FROM cards_fts")
    n = skipped = 0
    for c in iter_json_records(cards_path):
        if c.get("object") != "card" or c.get("layout") in SKIP_LAYOUTS or not c.get("oracle_id"):
            skipped += 1
            continue
        pick = _face_text(c)
        faces = [{k: f.get(k) for k in ("name", "mana_cost", "type_line", "oracle_text",
                                         "power", "toughness", "loyalty")}
                 for f in (c.get("card_faces") or [])]
        row = (c["oracle_id"], c.get("name", ""), pick("mana_cost"), c.get("cmc"),
               pick("type_line"), pick("oracle_text"), pick("power"), pick("toughness"),
               pick("loyalty"), "".join(c.get("colors") or []),
               "".join(c.get("color_identity") or []), ", ".join(c.get("keywords") or []),
               c.get("layout"), json.dumps(c.get("legalities") or {}), c.get("set_name"),
               c.get("rarity"), json.dumps(faces) if faces else None)
        con.execute("INSERT OR REPLACE INTO cards VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", row)
        con.execute("INSERT INTO cards_fts(name,type_line,oracle_text,oracle_id) VALUES(?,?,?,?)",
                    (row[1], row[4], row[5], row[0]))
        n += 1
        if n % 5000 == 0:
            con.commit(); log("  %d cards..." % n)
    r = 0
    if rulings_path:
        con.execute("DELETE FROM rulings")
        for x in iter_json_records(rulings_path):
            con.execute("INSERT INTO rulings VALUES(?,?,?,?)",
                        (x.get("oracle_id"), x.get("published_at"), x.get("source"), x.get("comment")))
            r += 1
    set_meta(con, "mtg_cards_loaded", time.strftime("%Y-%m-%d"))
    set_meta(con, "mtg_cards_credit", "Card data from Scryfall")
    con.commit()
    log("Loaded %d cards, %d rulings (%d non-cards skipped)." % (n, r, skipped))
    return n, r


def power_toughness(p, t):
    """'2/3'. A card with two faces stores '1 // 3' and '1 // 2': that is 1/1 // 3/2."""
    ps, ts = str(p or "").split(" // "), str(t or "").split(" // ")
    if len(ps) == len(ts):
        return " // ".join("%s/%s" % pair for pair in zip(ps, ts))
    return "%s/%s" % (p, t)


def find_cards(con, text, limit=8):
    """Exact name first, then names starting with the text, then any match."""
    cols = "oracle_id,name,mana_cost,type_line,oracle_text,power,toughness,loyalty,legalities"
    out, have = [], set()
    def take(rows):
        for row in rows:
            if row[0] not in have and len(out) < limit:
                have.add(row[0]); out.append(row)
    t = text.strip()
    take(con.execute("SELECT %s FROM cards WHERE name=? COLLATE NOCASE" % cols, (t,)).fetchall())
    take(con.execute("SELECT %s FROM cards WHERE name LIKE ? ORDER BY length(name) LIMIT ?" % cols,
                     (t.replace("%", "") + "%", limit)).fetchall())
    words = re.findall(r"[A-Za-z0-9']+", t)
    if words and len(out) < limit:
        q = " AND ".join('"%s"*' % w for w in words)
        for scope in ("name : (%s)" % q, q):
            ids = [r[0] for r in con.execute(
                "SELECT oracle_id FROM cards_fts WHERE cards_fts MATCH ? ORDER BY rank LIMIT ?",
                (scope, limit)).fetchall()]
            for oid in ids:
                take(con.execute("SELECT %s FROM cards WHERE oracle_id=?" % cols, (oid,)).fetchall())
    return out


MANA_WORDS = {"W": "white", "U": "blue", "B": "black", "R": "red", "G": "green",
              "C": "colourless", "X": "X", "S": "snow"}
NUM_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"]


def mana_words(cost):
    """'{2}{G}{G}' -> 'two and two green'. For reading a cost aloud."""
    if not cost:
        return "no cost"
    parts = []
    for side in cost.split(" // "):
        syms = re.findall(r"\{([^}]+)\}", side)
        generic = sum(int(s) for s in syms if s.isdigit())
        counts, order = {}, []
        for s in syms:
            if s.isdigit():
                continue
            if "/" in s:
                name = " or ".join(MANA_WORDS.get(p, "two" if p == "2" else ("life" if p == "P" else p))
                                   for p in s.split("/"))
            else:
                name = MANA_WORDS.get(s, s)
            if name not in counts:
                order.append(name)
            counts[name] = counts.get(name, 0) + 1
        bits = []
        if generic or not order:
            bits.append(NUM_WORDS[generic] if generic < len(NUM_WORDS) else str(generic))
        for name in order:
            k = counts[name]
            bits.append("%s %s" % (NUM_WORDS[k] if k < len(NUM_WORDS) else k, name))
        parts.append(" and ".join(bits))
    return " // ".join(parts)


def card_rulings(con, oracle_id):
    return con.execute("SELECT published_at,comment FROM rulings WHERE oracle_id=? ORDER BY published_at",
                       (oracle_id,)).fetchall()


# ---------------------------------------------------------------- Magic rules
RULE_RE = re.compile(r"^(\d{3}\.\d+[a-z]?)\.?\s+(.+)$")
SECT_RE = re.compile(r"^(\d{3})\.\s+(.+)$")
CHAP_RE = re.compile(r"^(\d)\.\s+(.+)$")


def load_mtg_rules(con, path, log=print):
    """Index the Comprehensive Rules text file: one row per numbered rule,
    one row per glossary term."""
    key = "mtg-comprehensive-rules"
    remove_file(con, key)
    lines = read_text_file(path).replace("\r\n", "\n").replace("\r", "\n").split("\n")
    eff = next((l.strip() for l in lines[:20] if "effective as of" in l.lower()), "")
    # The file lists every section title twice: once in the contents, once in
    # the body. The body starts at the second "1. Game Concepts"-style line.
    chap_idx = [i for i, l in enumerate(lines) if CHAP_RE.match(l.strip()) and l.strip().startswith("1.")]
    start = chap_idx[1] if len(chap_idx) > 1 else (chap_idx[0] if chap_idx else 0)
    gloss_idx = [i for i, l in enumerate(lines) if l.strip() == "Glossary"]
    gloss = gloss_idx[-1] if gloss_idx and gloss_idx[-1] > start else len(lines)
    cred_idx = [i for i, l in enumerate(lines) if l.strip() == "Credits"]
    end = cred_idx[-1] if cred_idx and cred_idx[-1] > gloss else len(lines)
    source = "Magic Comprehensive Rules"
    n = g = 0
    def put(kind, title, ref, body):
        cur = con.execute(
            "INSERT INTO docs(path,game,source,kind,title,ref,page,body,mine,dm_only) VALUES(?,?,?,?,?,?,?,?,0,0)",
            (key, "mtg", source, kind, title, ref, None, body))
        con.execute("INSERT INTO docs_fts(rowid,title,body) VALUES(?,?,?)", (cur.lastrowid, title, body))
    section, ref, buf = "", None, []
    def flush():
        nonlocal n
        if ref and buf:
            put("rule", section, ref, clean("\n".join(buf))); n += 1
    for l in lines[start:gloss]:
        s = l.strip()
        m = RULE_RE.match(s)
        if m:
            flush(); ref, buf = m.group(1), [m.group(2)]
        elif SECT_RE.match(s):
            flush(); ref, buf = None, []
            section = "%s. %s" % SECT_RE.match(s).groups()
        elif CHAP_RE.match(s):
            flush(); ref, buf = None, []
        elif s and ref:
            buf.append(s)                              # examples and continuation lines
    flush()
    for block in re.split(r"\n\s*\n", "\n".join(lines[gloss + 1:end])):
        parts = [p.strip() for p in block.strip().split("\n") if p.strip()]
        if len(parts) >= 2:
            put("glossary", parts[0], "Glossary", clean("\n".join(parts[1:]))); g += 1
    con.execute("INSERT OR REPLACE INTO files VALUES(?,?,?,?,?,?,?,?,?)",
                (key, sha1_of(path), "mtg", source, 0, 0, n + g, 0, time.time()))
    set_meta(con, "mtg_rules_version", eff)
    con.commit()
    log("Loaded %d rules and %d glossary terms. %s" % (n, g, eff))
    return n, g


# ---------------------------------------------------------------- downloading
def fetch_mtg(content_dir, log=print):
    """Download Scryfall's daily bulk files (cards and rulings)."""
    import urllib.request
    out = os.path.join(content_dir, "free", "mtg")
    os.makedirs(out, exist_ok=True)
    head = {"User-Agent": "gamebox/1.0 (personal use)", "Accept": "application/json"}
    req = urllib.request.Request("https://api.scryfall.com/bulk-data", headers=head)
    listing = json.load(urllib.request.urlopen(req, timeout=60))
    got = {}
    for item in listing.get("data", []):
        if item.get("type") in ("oracle_cards", "rulings"):
            url, name = bulk_link(item)
            if not url:
                raise ValueError("Scryfall's list has no download link for %s. It has: %s"
                                 % (item["type"], ", ".join(sorted(item))))
            dest = os.path.join(out, name)
            size = item.get("size") or item.get("compressed_size") or 0
            log("Downloading %s (%.0f MB)..." % (item["type"], size / 1e6))
            r = urllib.request.urlopen(urllib.request.Request(url, headers=head), timeout=600)
            with open(dest + ".part", "wb") as f:
                for block in iter(lambda: r.read(1 << 20), b""):
                    f.write(block)
            os.replace(dest + ".part", dest)
            got[item["type"]] = dest
    return got


def bulk_link(item):
    """(address, file name to keep it under) for one entry of Scryfall's bulk-data
    list. In 2026 the list changed from `download_uri` (a JSON array) to
    `jsonl_download_uri` (gzipped, one object to a line); either is taken."""
    url = item.get("download_uri") or item.get("jsonl_download_uri") or ""
    tail = url.split("?")[0].lower()
    ext = next((e for e in (".jsonl.gz", ".json.gz", ".jsonl", ".json") if tail.endswith(e)), ".json")
    return url, str(item.get("type", "bulk")).replace("_", "-") + ext


# ---------------------------------------------------------------- command line
def main(argv=None):
    ap = argparse.ArgumentParser(description="Deep Thought content loader")
    ap.add_argument("--db", default=DB_DEFAULT)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sync"); s.add_argument("content_dir")
    s = sub.add_parser("fetch-mtg"); s.add_argument("content_dir")
    s = sub.add_parser("mtg-cards"); s.add_argument("cards"); s.add_argument("--rulings")
    s = sub.add_parser("mtg-rules"); s.add_argument("txt")
    s = sub.add_parser("search"); s.add_argument("query"); s.add_argument("--game")
    s.add_argument("--dm", action="store_true")
    s = sub.add_parser("card"); s.add_argument("name")
    sub.add_parser("stats")
    a = ap.parse_args(argv)
    con = connect(a.db)
    if a.cmd == "sync":
        sync(con, a.content_dir)
    elif a.cmd == "fetch-mtg":
        got = fetch_mtg(a.content_dir)
        if "oracle_cards" in got:
            load_cards(con, got["oracle_cards"], got.get("rulings"))
    elif a.cmd == "mtg-cards":
        load_cards(con, a.cards, a.rulings)
    elif a.cmd == "mtg-rules":
        load_mtg_rules(con, a.txt)
    elif a.cmd == "search":
        rows = search(con, a.query, a.game, a.dm)
        for source, ref, title, snip, mine, _ in rows:
            print("%s, %s%s\n   %s\n" % (source, ref, " (your book)" if mine else "", snip.replace("\n", " ")))
        if not rows:
            print("No match.")
    elif a.cmd == "card":
        for oid, name, cost, tl, text, p, t, loy, legal in find_cards(con, a.name):
            pt = " " + power_toughness(p, t) if p else (" loyalty %s" % loy if loy else "")
            print("%s  [%s]\n   %s%s\n   %s\n   rulings: %d\n" % (
                name, mana_words(cost), tl, pt, (text or "").replace("\n", "\n   "),
                len(card_rulings(con, oid))))
    elif a.cmd == "stats":
        for game, source, mine, dm, chunks, empty in con.execute(
                "SELECT game,source,mine,dm_only,chunks,empty_pages FROM files ORDER BY game,mine,source"):
            tag = "DM only" if dm else ("yours" if mine else "free")
            print("%-9s %-8s %-45s %5d sections%s" % (game, tag, source[:45], chunks,
                  "  (%d unreadable pages)" % empty if empty else ""))
        print("Magic cards: %d   rulings: %d" % (
            con.execute("SELECT count(*) FROM cards").fetchone()[0],
            con.execute("SELECT count(*) FROM rulings").fetchone()[0]))
        for k, v in con.execute("SELECT key,value FROM meta ORDER BY key"):
            print("%s: %s" % (k, v))
    con.close()


if __name__ == "__main__":
    main()
