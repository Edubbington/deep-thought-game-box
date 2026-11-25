"""Tests for dt_content.py. All fixture text is made up for the test."""
import json, os, shutil, sys, tempfile, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dt_content as dc

T = tempfile.mkdtemp(prefix="dt_test_")
C = os.path.join(T, "content")
fails = []
def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else "   " + str(detail)))
    if not cond: fails.append(name)

def make_pdf(path, pages):
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(path, pagesize=letter)
    for lines in pages:
        y = 740
        for line in lines:
            c.drawString(72, y, line); y -= 16
        c.showPage()
    c.save()

def make_epub(path, chapters, protected=False):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        items = "".join('<item id="c%d" href="c%d.xhtml" media-type="application/xhtml+xml"/>' % (i, i) for i in range(len(chapters)))
        spine = "".join('<itemref idref="c%d"/>' % i for i in range(len(chapters)))
        z.writestr("OEBPS/content.opf", "<package><manifest>%s</manifest><spine>%s</spine></package>" % (items, spine))
        for i, (title, body) in enumerate(chapters):
            z.writestr("OEBPS/c%d.xhtml" % i, "<html><body><h1>%s</h1><p>%s</p></body></html>" % (title, body))
        if protected: z.writestr("META-INF/encryption.xml", "<encryption/>")

for sub in ("free/wh40k", "free/dnd", "mine/dnd/campaigns", "mine/wh40k", "mine/killteam"):
    os.makedirs(os.path.join(C, sub))
make_pdf(os.path.join(C, "free/wh40k/Test Core Rules.pdf"), [
    ["TEST RULES PAGE ONE", "A zorblat unit may advance six inches."],
    [],                                                         # blank page
    ["TEST RULES PAGE THREE", "Quibbling fire: roll one extra die when the", "target is within half range."]])
open(os.path.join(C, "free/dnd/Test SRD.md"), "w").write(
    "# Test Rules\n\nIntro text.\n\n## Conditions\n\n### Wobbly\n\nA wobbly creature has its speed halved.\n\n### Glimmered\n\nA glimmered creature sheds dim light.\n\n## Spells\n\n### Frostnip\n\nThe target takes cold damage.\n")
make_pdf(os.path.join(C, "mine/dnd/My Players Book.pdf"), [["CHAPTER 1", "The fennelmancer class gains herb slots."]])
make_pdf(os.path.join(C, "mine/dnd/campaigns/Test Campaign.pdf"), [["CHAPTER 2", "The secret villain is the innkeeper Dorvald."]])
make_epub(os.path.join(C, "mine/wh40k/My Codex.epub"), [("Army Rule", "Grumblecrons return on a roll of five."), ("Detachment", "The Snorefleet detachment costs two points.")])
make_epub(os.path.join(C, "mine/killteam/Locked.epub"), [("X", "hidden")], protected=True)
make_pdf(os.path.join(C, "mine/killteam/Scanned.pdf"), [[], []])
open(os.path.join(C, "mine/killteam/photo.jpg"), "wb").write(b"\xff\xd8")
long_para = " ".join("word%d" % i for i in range(3000))
open(os.path.join(C, "free/dnd/long.txt"), "w").write("Short start.\n\n" + long_para)

db = os.path.join(T, "content.db")
con = dc.connect(db)
log = []
rep = dict(dc.sync(con, C, log=log.append))
check("pdf: two text pages indexed, blank page counted", rep.get("free/wh40k/Test Core Rules.pdf") == "2 sections; 1 pages had no readable text", rep.get("free/wh40k/Test Core Rules.pdf"))
check("markdown split into heading sections", rep.get("free/dnd/Test SRD.md") == "4 sections", rep.get("free/dnd/Test SRD.md"))
check("epub chapters indexed", rep.get("mine/wh40k/My Codex.epub") == "2 sections", rep.get("mine/wh40k/My Codex.epub"))
check("protected epub reported, not fatal", "copy-protected" in rep.get("mine/killteam/Locked.epub", ""), rep.get("mine/killteam/Locked.epub"))
check("scanned pdf flagged for OCR", "NO TEXT FOUND" in rep.get("mine/killteam/Scanned.pdf", ""), rep.get("mine/killteam/Scanned.pdf"))
check("unsupported file reported", "not supported" in rep.get("mine/killteam/photo.jpg", ""))
mx = con.execute("SELECT max(length(body)) FROM docs").fetchone()[0]
check("no chunk longer than limit", mx <= dc.MAX_CHUNK, mx)
tot = con.execute("SELECT sum(length(body)) FROM docs WHERE path='free/dnd/long.txt'").fetchone()[0]
check("long text not truncated", tot >= len(long_para) - 20, (tot, len(long_para)))

r = dc.search(con, "zorblat advance")
check("search finds PDF page with page ref", r and r[0][0] == "Test Core Rules" and r[0][1] == "p. 1", r)
r = dc.search(con, "quibbling fire extra die")
check("search finds page 3 (numbering survives blank page)", r and r[0][1] == "p. 3", r)
r = dc.search(con, "wobbly", game="dnd")
check("markdown heading trail in title", r and r[0][2] == "Test Rules > Conditions > Wobbly", r)
r = dc.search(con, "wobbly", game="wh40k")
check("game filter excludes other games", r == [], r)
r = dc.search(con, "fennelmancer")
check("own book marked as yours", r and r[0][4] == 1, r)
r = dc.search(con, "grumblecrons")
check("epub searchable", r and r[0][0] == "My Codex" and r[0][1] == "ch. 1", r)
check("campaign hidden from player search", dc.search(con, "Dorvald villain") == [])
r = dc.search(con, "Dorvald villain", dm=True)
check("campaign visible in DM mode", r and r[0][0] == "Test Campaign", r)
r = dc.search(con, "speeds halving")   # stemming + OR fallback
check("stemmed / partial query still finds it", r and "Wobbly" in r[0][2], r)
check("punctuation-only query is safe", dc.search(con, '"); DROP -- *') == [])

n_before = con.execute("SELECT count(*) FROM docs").fetchone()[0]
rep2 = dict(dc.sync(con, C, log=log.append))
unchanged = [k for k, v in rep2.items() if "sections" in v and "NO TEXT" not in v]
check("second sync re-indexes nothing unchanged", unchanged == [] and con.execute("SELECT count(*) FROM docs").fetchone()[0] == n_before, rep2)
open(os.path.join(C, "free/dnd/Test SRD.md"), "a").write("\n### Zapple\n\nA zapple bolt arcs to a second target.\n")
os.remove(os.path.join(C, "mine/wh40k/My Codex.epub"))
rep3 = dict(dc.sync(con, C, log=log.append))
check("changed file re-indexed", rep3.get("free/dnd/Test SRD.md") == "5 sections", rep3.get("free/dnd/Test SRD.md"))
check("deleted file removed from index", "removed" in rep3.get("mine/wh40k/My Codex.epub", "") and dc.search(con, "grumblecrons") == [])
check("new section searchable, no duplicates", len(dc.search(con, "wobbly")) == 1 and len(dc.search(con, "zapple")) == 1)
check("fts index consistent", con.execute("INSERT INTO docs_fts(docs_fts) VALUES('integrity-check')") is not None)

# ---- Magic cards (objects shaped like Scryfall's; texts invented)
cards = [
 {"object": "card", "oracle_id": "a1", "name": "Testwood Elves", "mana_cost": "{G}", "cmc": 1.0, "type_line": "Creature — Elf Druid", "oracle_text": "{T}: Add {G}.", "power": "1", "toughness": "1", "colors": ["G"], "color_identity": ["G"], "keywords": [], "layout": "normal", "legalities": {"commander": "legal", "standard": "not_legal"}, "set_name": "Test Set", "rarity": "common"},
 {"object": "card", "oracle_id": "a2", "name": "Testwood Elves Champion", "mana_cost": "{2}{G}{G}", "cmc": 4.0, "type_line": "Creature — Elf", "oracle_text": "Trample", "power": "4", "toughness": "4", "colors": ["G"], "color_identity": ["G"], "keywords": ["Trample"], "layout": "normal", "legalities": {"commander": "legal"}, "set_name": "Test Set", "rarity": "rare"},
 {"object": "card", "oracle_id": "a3", "name": "Day Thing // Night Thing", "cmc": 3.0, "layout": "transform", "color_identity": ["R", "W"], "legalities": {"commander": "banned"}, "set_name": "Test Set", "rarity": "mythic",
  "card_faces": [{"name": "Day Thing", "mana_cost": "{1}{R}{W}", "type_line": "Creature — Human", "oracle_text": "When this enters, glorp a card.", "power": "2", "toughness": "3"}, {"name": "Night Thing", "mana_cost": "", "type_line": "Creature — Horror", "oracle_text": "Menace", "power": "5", "toughness": "5"}]},
 {"object": "card", "oracle_id": "a4", "name": "Braces {and} \"quotes\"", "mana_cost": "{X}{W/U}{B/P}{2/R}", "cmc": 3.0, "type_line": "Sorcery", "oracle_text": "Text with ] and [ and }, { inside.", "layout": "normal", "legalities": {}, "set_name": "Test Set", "rarity": "uncommon"},
 {"object": "card", "oracle_id": "t1", "name": "Elf Token", "layout": "token", "type_line": "Token Creature — Elf"},
]
p = os.path.join(T, "oracle-cards.json")
# one file with one card per line (how Scryfall ships it), one pretty-printed, one minified
open(p, "w").write("[\n" + ",\n".join(json.dumps(c) for c in cards) + "\n]\n")
rul = os.path.join(T, "rulings.json")
json.dump([{"object": "ruling", "oracle_id": "a1", "source": "wotc", "published_at": "2020-01-01", "comment": "Invented ruling one."}, {"object": "ruling", "oracle_id": "a3", "source": "wotc", "published_at": "2021-01-01", "comment": "Invented ruling two."}], open(rul, "w"))
n, r_ = dc.load_cards(con, p, rul, log=log.append)
check("cards loaded, token skipped", (n, r_) == (4, 2), (n, r_))
# Scryfall's newer shipping: one object to a line, gzipped
import gzip
pz, rz = os.path.join(T, "oracle-cards.jsonl.gz"), os.path.join(T, "rulings.jsonl.gz")
with gzip.open(pz, "wt", encoding="utf-8") as f:
    f.write("\n".join(json.dumps(c) for c in cards) + "\n")
with gzip.open(rz, "wt", encoding="utf-8") as f:
    f.write("\n".join(json.dumps(x) for x in json.load(open(rul))) + "\n")
check("cards and rulings shipped one to a line and gzipped load the same", dc.load_cards(con, pz, rz, log=log.append) == (4, 2))
check("and the cards read the same as from the old file", [dict(c) if isinstance(c, dict) else c for c in dc.iter_json_records(pz)] == cards)
pl = os.path.join(T, "plain.jsonl"); open(pl, "w", encoding="utf-8").write("\n".join(json.dumps(c) for c in cards))
pg = os.path.join(T, "array.json.gz")
with gzip.open(pg, "wt", encoding="utf-8") as f:
    json.dump(cards, f)
check("one to a line without gzip, and a gzipped array, are read too", list(dc.iter_json_records(pl)) == cards and list(dc.iter_json_records(pg)) == cards and list(dc.iter_json_records(p)) == cards)
check("a two-faced creature's power and toughness are paired face by face", dc.power_toughness("1 // 3", "1 // 2") == "1/1 // 3/2" and dc.power_toughness("2", "3") == "2/3" and dc.power_toughness("*", "1+*") == "*/1+*" and dc.power_toughness("2", "2 // 4") == "2/2 // 4")
B = dc.bulk_link
check("the download link is found under the new name and the old one",
      B({"type": "oracle_cards", "jsonl_download_uri": "https://x.test/oracle-cards-2026.jsonl.gz"}) == ("https://x.test/oracle-cards-2026.jsonl.gz", "oracle-cards.jsonl.gz")
      and B({"type": "rulings", "download_uri": "https://x.test/rulings-2025.json"}) == ("https://x.test/rulings-2025.json", "rulings.json")
      and B({"type": "rulings"})[0] == "")
dc.load_cards(con, p, rul, log=log.append)
for style, text in (("pretty", json.dumps(cards, indent=2)), ("minified", json.dumps(cards, separators=(",", ":"))), ("empty", "[]")):
    q = os.path.join(T, style + ".json"); open(q, "w").write(text)
    got = list(dc.iter_json_array(q, chunk=7))            # tiny chunks to stress the stream reader
    check("stream reader: %s file, 7-byte chunks" % style, got == (cards if style != "empty" else []), len(got))
f = dc.find_cards(con, "testwood elves")
check("exact name first, then longer names", [x[1] for x in f] == ["Testwood Elves", "Testwood Elves Champion"], [x[1] for x in f])
check("partial typing finds card", [x[1] for x in dc.find_cards(con, "testw")][:1] == ["Testwood Elves"])
check("search by back face name", [x[1] for x in dc.find_cards(con, "night thing")] == ["Day Thing // Night Thing"], [x[1] for x in dc.find_cards(con, "night thing")])
check("search by rules text", [x[1] for x in dc.find_cards(con, "glorp")] == ["Day Thing // Night Thing"])
d = dc.find_cards(con, "Day Thing")[0]
check("two-faced card keeps both faces", d[2] == "{1}{R}{W}" and d[4] == "When this enters, glorp a card. // Menace" and d[5] == "2 // 5", d)
check("rulings attach to card", len(dc.card_rulings(con, "a1")) == 1 and len(dc.card_rulings(con, "a2")) == 0)
check("odd characters in query are safe", dc.find_cards(con, "%\"'*)(") == [])
for cost, want in (("{G}", "one green"), ("{2}{G}{G}", "two and two green"), ("{0}", "zero"), ("", "no cost"), ("{X}{W/U}{B/P}{2/R}", "one X and one white or blue and one black or life and one two or red"), ("{1}{R}{W}", "one and one red and one white"), ("{12}", "12")):
    check("mana_words(%r)" % cost, dc.mana_words(cost) == want, dc.mana_words(cost))
dc.load_cards(con, p, rul, log=log.append)
check("reloading cards does not duplicate", con.execute("SELECT count(*) FROM cards").fetchone()[0] == 4 and con.execute("SELECT count(*) FROM cards_fts").fetchone()[0] == 4 and con.execute("SELECT count(*) FROM rulings").fetchone()[0] == 2)

# ---- Magic rules (layout copied from the real file; wording invented)
rules = "﻿Test Comprehensive Rules\r\n\r\nThese rules are effective as of January 1, 2099.\r\n\r\nContents\r\n\r\n1. Game Concepts\r\n100. General\r\n101. Golden Rules\r\n2. Parts\r\n200. General\r\n\r\nGlossary\r\n\r\nCredits\r\n\r\n1. Game Concepts\r\n\r\n100. General\r\n\r\n100.1. These test rules apply to any snorkel game.\r\n\r\n100.1a A two-player snorkel game uses two snorkels.\r\nExample: Ann and Bob each bring one snorkel.\r\n\r\n101. Golden Rules\r\n\r\n101.1. When a card contradicts these rules, the card wins.\r\n\r\n2. Parts\r\n\r\n200. General\r\n\r\n200.1. The parts of a card are the flibber and the name.\r\n\r\nGlossary\r\n\r\nFlibber\r\nA made-up card part. See rule 200.1.\r\n\r\nSnorkel Game\r\nA made-up game.\r\n\r\nCredits\r\n\r\nNobody.\r\n"
rp = os.path.join(T, "rules.txt"); open(rp, "wb").write(rules.encode("utf-8"))
n, g = dc.load_mtg_rules(con, rp, log=log.append)
check("rules and glossary counted (contents list not double-counted)", (n, g) == (4, 2), (n, g))
r = dc.search(con, "two-player snorkel", game="mtg")
check("rule found with its number and section", r and r[0][1] == "100.1a" and r[0][2] == "100. General", r)
body = con.execute("SELECT body FROM docs WHERE ref='100.1a'").fetchone()[0]
check("example line kept with its rule", "Example: Ann and Bob" in body, body)
r = dc.search(con, "flibber")
check("glossary term found", any(x[1] == "Glossary" and x[2] == "Flibber" for x in r), r)
check("effective date recorded", con.execute("SELECT value FROM meta WHERE key='mtg_rules_version'").fetchone()[0] == "These rules are effective as of January 1, 2099.")
open(rp, "wb").write(rules.encode("cp1252", "ignore").replace(b"snorkel game.", b"snorkel game \x97 always."))
n2, g2 = dc.load_mtg_rules(con, rp, log=log.append)
check("Windows-encoded file loads, reload replaces", (n2, g2) == (4, 2) and con.execute("SELECT count(*) FROM docs WHERE game='mtg'").fetchone()[0] == 6)
dc.sync(con, C, log=log.append)
check("sync leaves Magic rules alone", con.execute("SELECT count(*) FROM docs WHERE game='mtg'").fetchone()[0] == 6)
con.close()

# ---- command line
import subprocess
out = subprocess.run([sys.executable, os.path.join(os.path.dirname(dc.__file__), "dt_content.py"), "--db", db, "card", "testwood"], capture_output=True, text=True)
check("CLI card lookup", "Testwood Elves  [one green]" in out.stdout and out.returncode == 0, out.stdout + out.stderr)
out = subprocess.run([sys.executable, os.path.join(os.path.dirname(dc.__file__), "dt_content.py"), "--db", db, "stats"], capture_output=True, text=True)
check("CLI stats", "Magic cards: 4" in out.stdout and "DM only" in out.stdout and out.returncode == 0, out.stdout + out.stderr)

# ---- faults found in review, each kept fixed
T2 = tempfile.mkdtemp(prefix="dt_test2_")
C2 = os.path.join(T2, "content"); os.makedirs(os.path.join(C2, "mine", "dnd"))
import sqlite3
old_db = os.path.join(T2, "old.db")
oc = sqlite3.connect(old_db); oc.executescript(dc.SCHEMA)
oc.execute("INSERT INTO docs(path,game,source,title,body,mine,dm_only) VALUES('k','dnd','Old Book','T','the plonkit',1,0)")
oc.execute("INSERT INTO docs_fts(rowid,title,body) VALUES(1,'T','the plonkit')"); oc.commit()
check("a library made the old way starts in the old journal mode", oc.execute("PRAGMA journal_mode").fetchone()[0] == "delete"); oc.close()
nc = dc.connect(old_db)
check("connect opens an old library, keeps what is in it, and switches it to write-ahead mode", nc.execute("PRAGMA journal_mode").fetchone()[0] == "wal" and dc.search(nc, "plonkit")[0][0] == "Old Book")
reader = sqlite3.connect(old_db, timeout=0.2)
for i in range(3000):
    cur = nc.execute("INSERT INTO docs(path,game,source,title,body,mine,dm_only) VALUES('big','dnd','Big','T',?,1,0)", ("lorem %d " % i * 300,))
    nc.execute("INSERT INTO docs_fts(rowid,title,body) VALUES(?,?,?)", (cur.lastrowid, "T", "lorem %d " % i * 300))
try: seen = reader.execute("SELECT count(*) FROM docs").fetchone()[0], len(dc.search(reader, "plonkit"))
except sqlite3.Error as e: seen = repr(e)
check("another reader is not locked out while a big book is half loaded", seen == (1, 1), seen)
nc.rollback(); nc.close(); reader.close()
# an EPUB whose chapter links are URL-encoded or climb out of the folder
p = os.path.join(C2, "mine", "dnd", "Linked.epub")
with zipfile.ZipFile(p, "w") as z:
    z.writestr("OEBPS/content.opf", '<package><manifest><item id="c1" href="Text/chapter%201.xhtml"/><item id="c2" href="../Other/two.xhtml#top"/></manifest><spine><itemref idref="c1"/><itemref idref="c2"/></spine></package>')
    z.writestr("OEBPS/Text/chapter 1.xhtml", "<html><body><h1>One</h1><p>The flumphit hovers over the table and waits its turn.</p></body></html>")
    z.writestr("Other/two.xhtml", "<html><body><h1>Two</h1><p>The second chapter has a quaggit in it somewhere.</p></body></html>")
db2 = os.path.join(T2, "c.db"); con2 = dc.connect(db2)
rep = dict(dc.sync(con2, C2, log=lambda *a: None))
check("epub chapter links written with %20 or ../ are followed", rep.get("mine/dnd/Linked.epub") == "2 sections" and dc.search(con2, "flumphit")[0][1] == "ch. 1" and dc.search(con2, "quaggit")[0][1] == "ch. 2", rep)
# a file that fails part way through
p = os.path.join(C2, "mine", "dnd", "Half.epub")
with zipfile.ZipFile(p, "w") as z:
    z.writestr("a.xhtml", "<html><body><h1>One</h1><p>The snarfblat hovers over the table and waits its turn.</p></body></html>")
    z.writestr("b.xhtml", "<html><body><h1>Two</h1><p>" + "padding " * 2000 + "</p></body></html>")
blob = bytearray(open(p, "rb").read()); at = blob.find(b"padding"); blob[at + 500:at + 510] = b"XXXXXXXXXX"
open(p, "wb").write(bytes(blob))
rep = dict(dc.sync(con2, C2, log=lambda *a: None))
check("a file that breaks part way is reported and leaves nothing half loaded", rep.get("mine/dnd/Half.epub", "").startswith("FAILED") and dc.search(con2, "snarfblat") == []
      and con2.execute("SELECT count(*) FROM docs WHERE path='mine/dnd/Half.epub'").fetchone()[0] == 0 and len(dc.search(con2, "flumphit")) == 1, rep)
os.remove(p); dc.sync(con2, C2, log=lambda *a: None)
check("and nothing of it can be found once the file is gone", dc.search(con2, "snarfblat") == [])
# PDFs are read from an open file, not loaded whole
import pypdf
real_reader, given = pypdf.PdfReader, []
def spy(source, *a, **k):
    given.append(source); return real_reader(source, *a, **k)
pypdf.PdfReader = spy
p = os.path.join(C2, "mine", "dnd", "Small.pdf"); make_pdf(p, [["The wibblefish swims upstream in the second phase of every round."]])
rep = dict(dc.sync(con2, C2, log=lambda *a: None))
pypdf.PdfReader = real_reader
check("a PDF is handed to the reader as an open file, and the file is closed afterwards", rep.get("mine/dnd/Small.pdf") == "1 sections" and len(given) == 1 and not isinstance(given[0], str) and given[0].closed, (rep, given))
real_pypdf = sys.modules["pypdf"]; sys.modules["pypdf"] = None
os.utime(p, None); open(p, "ab").write(b"\n")
rep = dict(dc.sync(con2, C2, log=lambda *a: None))
sys.modules["pypdf"] = real_pypdf
check("with pypdf missing a PDF is a reported failure, not the end of the program", "pypdf" in rep.get("mine/dnd/Small.pdf", "") and rep["mine/dnd/Small.pdf"].startswith("FAILED"), rep)
for q in ["can't re-roll", "''", "'", '"', '""', "*", "NEAR(a b)", "AND OR NOT", "", "   ", "%", "_", "col:x", "^x", "(", "x'; DROP TABLE docs;--", "caf\u00e9"]:
    try: dc.search(con2, q); dc.find_cards(con2, q); ok = True
    except Exception as e: ok = repr(e)
    check("search and card search survive %r" % q, ok is True, ok)
con2.close(); shutil.rmtree(T2)
shutil.rmtree(T)
print("\n%d failed" % len(fails)); sys.exit(1 if fails else 0)
