#!/usr/bin/env python3
"""Load Deep Thought's own notes into content.db, so Lookup can search them.

Her notes are the Knowledge Base tabs in docs/text and each game's teach.json.
They are written for this project, in her own words. Books you own are loaded
separately, with:  python dt_content.py sync content

  python tools/build_notes.py            # writes software/content.db
  python tools/build_notes.py --db x.db
"""
import argparse
import json
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SOFTWARE = os.path.dirname(HERE)
sys.path.insert(0, SOFTWARE)
import dt_content  # noqa: E402

DOCS = os.path.join(os.path.dirname(SOFTWARE), "docs", "text")
SOURCE = "Deep Thought's notes"

# Knowledge Base tab -> (game, DM only)
TABS = {"Knowledge Base - Kill teams in depth.txt": ("killteam", False),
        "Knowledge Base - 40k factions in depth.txt": ("wh40k", False),
        "Knowledge Base - Your Necron army.txt": ("wh40k", False),
        "Knowledge Base - D&D.txt": ("dnd", False),
        "Knowledge Base - Magic The Gathering.txt": ("mtg", False),
        "Knowledge Base - DM guide official campaigns.txt": ("dnd", True),
        "Knowledge Base - Campaign Dragon of Icespire Peak.txt": ("dnd", True)}
MAIN = "Knowledge Base - Main tab (persona, Kill Team, 40k).txt"
# Parts of the main tab -> games. Parts 1, 11 and 12 are about the box, not the games.
PARTS = {2: ["killteam"], 3: ["killteam"], 4: ["killteam"], 5: ["killteam"],
         6: ["wh40k"], 7: ["wh40k"], 8: ["wh40k"], 9: ["wh40k"], 10: ["killteam", "wh40k"]}


def tidy(text):
    """Drop the page footers and running headers the PDF export left behind."""
    out = []
    for line in text.replace("\r", "").replace("\f", "\n").split("\n"):
        s = line.strip()
        if re.match(r"^Page \d+ of \d+$", s) or s.startswith("Deep Thought — "):
            continue
        out.append(line.rstrip())
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def main_tab_parts(text):
    """Split the main tab at its 'Part N — title' lines. Returns [(n, title, body)]."""
    marks = [(m.start(), int(m.group(1)), m.group(2).strip())
             for m in re.finditer(r"^\s*Part (\d+) — (.+)$", text, re.M)]
    seen, out = set(), []
    for k, (pos, n, title) in enumerate(marks):
        if n in seen:                        # the contents list names each part once already
            continue
        end = next((p for p, m, _ in marks[k + 1:] if m != n), len(text))
        body = text[pos:end]
        if len(body) > 400:                  # a real part, not its line in the contents
            seen.add(n)
            out.append((n, title, body))
    return out


def build(db_path, log=print):
    con = dt_content.connect(db_path)
    for (key,) in con.execute("SELECT path FROM files WHERE path LIKE 'notes/%'").fetchall():
        dt_content.remove_file(con, key)
    tmp = tempfile.mkdtemp()
    total = 0

    def add(name, text, game, dm_only=False, source=SOURCE):
        nonlocal total
        path = os.path.join(tmp, re.sub(r"[^A-Za-z0-9]+", "-", name) + ".md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        res = dt_content.add_file(con, path, game, source=source, dm_only=dm_only, key="notes/%s/%s" % (game, name))
        n = res[0] if res else 0
        total += n
        log("%-9s %-52s %4d sections%s" % (game, name[:52], n, "  (DM only)" if dm_only else ""))

    for name, (game, dm) in TABS.items():
        path = os.path.join(DOCS, name)
        if os.path.isfile(path):
            title = name[len("Knowledge Base - "):-4]
            add(title, "# %s\n\n%s" % (title, tidy(dt_content.read_text_file(path))), game, dm)
    path = os.path.join(DOCS, MAIN)
    if os.path.isfile(path):
        for n, title, body in main_tab_parts(tidy(dt_content.read_text_file(path))):
            for game in PARTS.get(n, []):
                add("Part %d %s" % (n, title), "# %s\n\n%s" % (title, body), game)
    games = os.path.join(SOFTWARE, "deepthought", "games")
    for gid in sorted(os.listdir(games)):
        teach = os.path.join(games, gid, "teach.json")
        if os.path.isfile(teach):
            with open(teach, encoding="utf-8") as f:
                steps = json.load(f)
            text = "\n\n".join("# %s\n\n%s" % (s["title"], s["text"]) for s in steps)
            add("How to play", text, gid, source="Deep Thought's notes: how to play")
    dt_content.set_meta(con, "notes_built", __import__("time").strftime("%Y-%m-%d %H:%M"))
    con.commit()
    con.close()
    log("\n%d sections of her own notes are in %s" % (total, db_path))
    return total


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.path.join(SOFTWARE, "content.db"))
    build(ap.parse_args().db)
