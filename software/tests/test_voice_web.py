"""Tests for her persona, the question pipeline, the voice module with no keys,
the LED data bytes, and the web pages. No test here uses the internet."""
import json, os, shutil, sys, tempfile, threading, time, urllib.error, urllib.request
os.environ["SDL_VIDEODRIVER"] = "dummy"
DATA = tempfile.mkdtemp()
os.environ["DT_DATA"] = DATA
os.environ["DT_CONTENT_DB"] = os.path.join(DATA, "content.db")
os.environ["DT_CONTENT"] = os.path.join(DATA, "content")
os.environ.pop("ANTHROPIC_API_KEY", None)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dt_content, dt_characters
from deepthought import ask, engine, paths, persona, settings, voice, web, theme as T
from deepthought.games import load_games
from deepthought.hw.pi import ws2812_bytes
from deepthought.library import Library

from deepthought import dice as dice_mod
fails = []
def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + ("" if cond else "   " + str(detail)))
    if not cond: fails.append(name)

# ---------------------------------------------------------------- persona
every = [l for ls in persona.LINES.values() for l in ls]
check("stock lines: none repeated, none with an exclamation mark", len(set(every)) == len(every) and all(persona.in_voice(l) for l in every))
seen = [persona.line("power_on") for _ in range(30)]
check("a moment with several lines never repeats one back to back, and uses more than three of them", all(a != b for a, b in zip(seen, seen[1:])) and len(set(seen)) > 3)
check("voice check: exclamation marks and banned phrases are caught", not persona.in_voice("Great roll!") and not persona.in_voice("That is awesome.") and not persona.in_voice("") and persona.in_voice("A roll. I have seen better."))
import random
r = random.Random(1)
share = lambda mode: sum(persona.optional(mode, r) for _ in range(4000)) / 4000
check("chatty always speaks; normal about 60%; terse about 15%", share("chatty") == 1 and 0.55 < share("normal") < 0.65 and 0.11 < share("terse") < 0.19)
check("the voice prompt forbids inventing rules and reading out card numbers", "Never invent a rule" in persona.VOICE and "read their own card" in persona.VOICE)

# ---------------------------------------------------------------- the question pipeline
N = ask.normalise
check("normalise: filler and punctuation go, short forms are spelt out", N("What does Lethal 5+ mean?") == "lethal 5+" and N("how do CP work in KT") == "command points kill team", (N("What does Lethal 5+ mean?"), N("how do CP work in KT")))
check("normalise: the same question asked two ways is one question", N("What is cover?") == N("cover") == N("Tell me about cover please"))
src = os.environ["DT_CONTENT"]
os.makedirs(os.path.join(src, "free", "risk")); os.makedirs(os.path.join(src, "mine", "dnd", "campaigns"))
open(os.path.join(src, "free", "risk", "Made Up Rules.md"), "w", encoding="utf-8").write("# Armies\n\nThe grobnar gets three armies for each continent it holds.\n")
open(os.path.join(src, "mine", "dnd", "campaigns", "Secret.md"), "w", encoding="utf-8").write("# The twist\n\nThe villain zorblat is the innkeeper.\n")
con = dt_content.connect(os.environ["DT_CONTENT_DB"]); dt_content.sync(con, src, log=lambda *a: None); con.close()
lib = Library()
calls = []
def good(system, user):
    calls.append((system, user)); return "The grobnar receives three armies per continent. I trust that was worth asking."
a = ask.answer("How many armies does the grobnar get?", lib, "risk", "Risk", "Reinforce", llm=good)
check("cloud answer: text, source named, logged as a ruling", a["from"] == "cloud" and a["source"] == "Made Up Rules, Armies" and len(ask.rulings()) == 1, a)
check("the cloud was sent the persona, the game, the phase, the excerpt and the question",
      calls[0][0] == persona.VOICE and "Risk, phase: Reinforce" in calls[0][1] and "three armies for each continent" in calls[0][1] and "How many armies does the grobnar get?" in calls[0][1])
p = ask.build_prompt("Whose turn is it?", "Risk", "Attack", [], table="It is Ann's turn. Scoreboard: Ann 4, Bob 2.")
check("what she can see for herself goes first in the prompt, and an empty library is called her notes",
      p.startswith("It is Ann's turn. Scoreboard: Ann 4, Bob 2.") and "Your notes have nothing on this question." in p and p.endswith("The player asks: Whose turn is it?"), p)
check("her voice rules: four sentences, never describe the notes, send dice to the Dice screen",
      "Four sentences at most" in persona.VOICE and "Never describe the notes themselves" in persona.VOICE and "Dice screen" in persona.VOICE)
a2 = ask.answer("how many armies does the grobnar get", lib, "risk", llm=good)
check("the same question again gets the same ruling, with its date, and no second cloud call", a2["from"] == "ruling" and a2["text"] == a["text"] and a2["date"] == time.strftime("%Y-%m-%d") and len(calls) == 1)
check("a ruling for one game is not used for another", ask.find_ruling("dnd", "how many armies does the grobnar get") is None)
ask.forget_ruling("risk", "How many armies does the grobnar get?")
check("a wrong ruling can be forgotten", ask.rulings() == [])
a = ask.answer("grobnar armies", lib, "risk", llm=None)
check("offline: the library section itself is shown, and not logged as a ruling", a["from"] == "library" and "three armies for each continent" in a["text"] and ask.rulings() == [], a)
def broken(system, user): raise RuntimeError("The network is away.")
a = ask.answer("grobnar armies", lib, "risk", llm=broken)
check("cloud failure falls back to the library and says why", a["from"] == "library" and a["note"] == "The network is away.", a)
tries = []
def shouty(system, user):
    tries.append(user); return "Three armies!" if len(tries) == 1 else "Three armies. Calm yourself."
a = ask.answer("grobnar armies again", lib, "risk", llm=shouty)
check("a reply that breaks her voice is asked for once more", len(tries) == 2 and a["text"] == "Three armies. Calm yourself.", a)
always = lambda s, u: "Wow!"
a = ask.answer("grobnar continent", lib, "risk", llm=always)
check("if she breaks voice twice the library text is used instead", a["from"] == "library", a)
sent = []
ask.answer("who is zorblat", lib, "dnd", llm=lambda s, u: (sent.append(u), "I have nothing certain on that. The book decides.")[1], remember=False)
check("campaign pages are not sent to the cloud for a player's question", "innkeeper" not in sent[0] and "nothing on this question" in sent[0], sent[0][-200:])
ask.answer("who is zorblat", lib, "dnd", dm=True, llm=lambda s, u: (sent.append(u), "The innkeeper. Do keep it to yourself.")[1], remember=False)
check("in DM mode they are", "innkeeper" in sent[1])
a = ask.answer("flumph", lib, "risk", llm=None)
check("nothing found, offline: she says so in character", a["from"] == "none" and a["text"] in persona.LINES["nothing_found"])
a = ask.answer("  ?? ", lib)
check("an empty question is not sent anywhere", a["from"] == "none")

# ---------------------------------------------------------------- voice with no keys
import pygame
from deepthought import hw
from deepthought.app import App
from deepthought import app as app_mod
from deepthought.screens import common
from deepthought.screens.home import Home
games, _ = load_games(extra=paths.data("games"))
app = App(hw.make("desktop", sound=False), games, headless=True)
app.push(Home(app))
cfg = voice.load_config(os.path.join(DATA, "missing.toml"))
check("no config file: sensible defaults, no keys", cfg["claude"]["model"] == "claude-haiku-5-5" and cfg["claude"]["api_key"] == "" and cfg["limits"]["monthly_dollars"] == 5.0)
open(os.path.join(DATA, "c.toml"), "w").write('[claude]\napi_key = "k1"\nmodel = "claude-sonnet-5-5"\n[speech]\napi_key = "k2"\ntts_voice = "deep"\n[limits]\nmonthly_dollars = 2\n')
cfg2 = voice.load_config(os.path.join(DATA, "c.toml"))
check("config file values replace the defaults, the rest stay", cfg2["claude"] == {"api_key": "k1", "model": "claude-sonnet-5-5"} and cfg2["speech"]["tts_voice"] == "deep" and cfg2["speech"]["stt_model"] == "whisper-1" and cfg2["limits"]["monthly_dollars"] == 2)
v = voice.Voice(app, cfg); app.voice = v
check("no keys: she cannot answer from the cloud, speak or hear, and says so", not v.can_answer() and not v.can_speak() and not v.can_hear() and "answers off" in v.status())
app.say("A line."); check("no keys: a line is still shown on screen", app.toast == "A line.")
app.gesture("hold_start"); app.gesture("hold_end")
entry = app.screen
check("no microphone: holding the button opens a typed question", isinstance(entry, common.TextEntry) and entry.title == "Ask" and "No microphone" in app.toast)
for ch in "grobnar armies": entry.type(ch)
entry.done()
def pump(until, secs=5):
    end = time.time() + secs
    while time.time() < end and not until():
        for job in app.jobs(): job()
        time.sleep(0.01)
pump(lambda: isinstance(app.screen, common.Pages))
page = app.screen
check("the typed question is answered from the library on an answer card",
      isinstance(page, common.Pages) and page.left == "You asked" and page.title == "From the library, as written" and any("Source: Made Up Rules, Armies" in l for l in page.pages[-1][1]), getattr(page, "pages", None))
check("the ring went to thinking and came back", app.hw._ring.now[0] == "breathe")
v2 = voice.Voice(app, cfg2)
check("with keys set: answers and speech are on; hearing still needs a microphone", v2.can_answer() and v2.can_speak() and not v2.can_hear())
check("made speech is filed by voice and text, so a changed voice makes new files", v2.cache_file("Hello.") != v.cache_file("Hello.") and v2.cache_file("Hello.") == v2.cache_file("Hello.") and v2.cache_file("Hello.").endswith(".wav"))
voice.add_spend(1.25); voice.add_spend(0.80)
check("spend is added up by month", abs(voice.spent_this_month() - 2.05) < 1e-9)
check("over the monthly cap the cloud is off", not v2.under_cap() and not v2.can_answer() and v.under_cap())
settings.put("cloud", False); check("the cloud setting switches it off too", not v.cloud_on()); settings.put("cloud", True)

# ---------------------------------------------------------------- LED data
b = ws2812_bytes([(255, 0, 0)])
check("ring data: one red LED is green 0, red 255, blue 0, three SPI bits per data bit",
      b[0] == 0 and b[1:10] == bytes([0x92, 0x49, 0x24, 0xDB, 0x6D, 0xB6, 0x92, 0x49, 0x24]) and b[10:] == bytes(40), b[:12].hex())
check("ring data: 16 LEDs make 144 data bytes plus the gaps", len(ws2812_bytes([(1, 2, 3)] * 16)) == 1 + 144 + 40)

# ---------------------------------------------------------------- web pages
w = web.Web(app, port=0, lock=False)       # the pages themselves; the table code is tested further down
check("the web server starts on a free port", w.start() and w.url.startswith("http://"))
app.web = w
stop = False
def loop():
    while not stop:
        for job in app.jobs(): job()
        time.sleep(0.005)
threading.Thread(target=loop, daemon=True).start()
base = "http://127.0.0.1:%d" % w.port
# One phone to a seat: each seat's requests come from its own phone (its own cookies),
# which has opened My seat and chosen that seat, as a real phone must. dev= names
# another phone, which is then used as it is, with no seat chosen for it.
import http.cookiejar, re
phones = {}
def phone_of(name):
    if name not in phones:
        phones[name] = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    return phones[name]
def seat_in(path, body=None):
    m = re.search(r"[?&]seat=(\d+)", path)
    if m: return int(m.group(1))
    return body["seat"] if isinstance(body, dict) and isinstance(body.get("seat"), int) else None
def get(path, dev=None):
    seat = seat_in(path)
    if dev is None and seat is not None and not path.startswith("/play"):
        get("/play?seat=%d" % seat)                   # sit down first
    try:
        with phone_of(seat if dev is None else dev).open(base + path, timeout=5) as r: return r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return "HTTP %s %s %s" % (e.code, path, e.read().decode("utf-8")[:300])
def post(path, body=b"", dev=None):
    seat = seat_in(path, body)
    if dev is None and seat is not None:
        get("/play?seat=%d" % seat)
    if isinstance(body, (dict, list)): body = json.dumps(body).encode()
    try:
        with phone_of(seat if dev is None else dev).open(urllib.request.Request(base + path, data=body, method="POST"), timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode("utf-8"))
loaded = {p: get(p) for p in ("/", "/play", "/characters", "/library", "/games", "/rulings", "/sounds")}
check("every page loads", all("Deep Thought" in v and not v.startswith("HTTP") for v in loaded.values()), [v[:300] for v in loaded.values() if v.startswith("HTTP")])
check("an unknown address is a 404 page, not a crash", get("/nope").startswith("HTTP 404"))
st = json.loads(get("/state.json"))
check("no game: the scoreboard says so", st["playing"] is False)
app.go_home()
t_none = v.table_now()
check("with no game on, she is told the time and that nothing is in play", t_none.startswith("The time is ") and "No game is in play" in t_none, t_none)
app.start_game(app.plugins["risk"], ["Ethan", "Trevor", "Sam"], {"hints": "On"})
t_game = v.table_now()
check("with a game on, she is told whose turn it is and the scoreboard, from the page every player may see",
      "It is Ethan's turn." in t_game and "Scoreboard" in t_game and all(n in t_game for n in ("Ethan", "Trevor", "Sam")), t_game)
seen = {}
real_answer = ask.answer
ask.answer = lambda *a, **k: seen.update(k) or {"text": "x", "source": "", "from": "none"}
v._answer("Who is winning?")
ask.answer = real_answer
check("that goes with every question she is asked", seen.get("table") == v.table_now(), seen)
st = json.loads(get("/state.json"))
check("scoreboard: game, phase, whose turn and a row per player", st["playing"] and st["title"] == "Reinforce" and st["active"] == 0 and [r["name"] for r in st["rows"]] == ["Ethan", "Trevor", "Sam"] and st["rows"][0]["value"] == 14, st)
ph0, ph1 = json.loads(get("/phone.json?seat=0")), json.loads(get("/phone.json?seat=1"))
check("phones: the active player has Next, the others do not", ph0["actions"] == ["Next"] and ph0["yours"] and ph1["actions"] == [] and not ph1["yours"], (ph0, ph1))
r = post("/do?seat=0&i=0", b"Next")
check("Next from the phone moves the game on the box", r == {"ok": True} and app.session.state["phase"] == "attack" and app.screen.title == "Attack", r)
r = post("/do?seat=1&i=0", b"Next")
check("another player's phone cannot press Next", "error" in r and app.session.state["phase"] == "attack", r)
r = post("/do?seat=0&i=0", b"Something else")
check("a stale button (label no longer matches) is refused", "error" in r and app.session.state["phase"] == "attack", r)
post("/remind", {"seat": 1, "phase": "attack", "text": "use the  cannons"})
check("a reminder typed on a phone is saved for that seat and phase", app.session.d["reminders"] == [{"player": 1, "phase": "attack", "text": "use the cannons"}], app.session.d["reminders"])
check("and shows on that phone only", json.loads(get("/phone.json?seat=1"))["reminders"] == ["use the cannons"] and json.loads(get("/phone.json?seat=0"))["reminders"] == [])
r = post("/characters/new", {"name": "Brakka", "player": "Ethan", "cls": "Fighter", "edition": "2024", "str": 16, "dex": 12, "con": 14, "int": 10, "wis": 12, "cha": 8})
c = dt_characters.load(os.path.join(paths.data("characters"), "brakka.json"))
check("a character made on the phone is saved: fighter, 12 hit points, 2024 rules", "ok" in r and c["hp"]["max"] == 12 and c["edition"] == "2024" and any("origin feat" in t for t in r["todo"]), r)
check("a character with no name or a score of 40 is refused", "error" in post("/characters/new", {"name": " "}) and "error" in post("/characters/new", {"name": "X", "str": 40}))
check("the characters page lists it", "Brakka" in get("/characters"))
r = post("/characters/upload?name=notes.txt", b"hello")
check("only PDFs can be uploaded as sheets", "error" in r, r)
r = post("/library/upload?game=risk&dm=0&name=" + urllib.request.quote("House Rules.md"), "# Mulligans\n\nThe flarn rule: reroll one die per game.\n".encode())
pump(lambda: False, 0.3)
check("an uploaded book lands in content/mine/<game> and is searchable at once",
      "ok" in r and os.path.isfile(os.path.join(src, "mine", "risk", "House Rules.md")) and app.library.search("flarn", "risk")[0]["title"] == "House Rules, Mulligans", r)
r = post("/library/upload?game=dnd&dm=1&name=Adventure.txt", b"The glimmerfang sleeps under the mill.")
pump(lambda: False, 0.3)
check("a book marked DM only goes in campaigns and is hidden from players", os.path.isfile(os.path.join(src, "mine", "dnd", "campaigns", "Adventure.txt")) and app.library.search("glimmerfang") == [] and len(app.library.search("glimmerfang", dm=True)) == 1)
check("uploads: bad type, unknown game and path tricks are refused",
      "error" in post("/library/upload?game=risk&name=virus.exe", b"x") and "error" in post("/library/upload?game=nope&name=a.txt", b"x")
      and web.safe_name("../../etc/passwd.txt", web.BOOK_TYPES) == "passwd.txt" and web.safe_name("..\\..\\run.py", web.BOOK_TYPES) is None)
r = post("/games/new", {"name": "Ticket To Ride", "blurb": "Trains across the map", "lo": 2, "hi": 5, "at": "", "phases": "Draw, Claim", "tracker": "Points", "teach": "Collect cards, claim routes.", "low": False})
pump(lambda: "ticket-to-ride" in app.plugins)
g = app.plugins.get("ticket-to-ride")
check("a game added from the phone is on the box, playable, with its how-to-play", "ok" in r and g is not None and g.phase_names == ["Draw", "Claim"] and (g.min_players, g.max_players) == (2, 5) and g.teach()[0]["text"] == "Collect cards, claim routes.", r)
check("adding the same game twice is refused", "error" in post("/games/new", {"name": "ticket to ride"}))
ask.save_ruling("risk", "Can I attack twice?", "As often as you like. Restraint is optional.", "Made Up Rules, Armies", "cloud")
check("the rulings page shows question, answer and source", all(x in get("/rulings") for x in ("Can I attack twice?", "Restraint is optional.", "Made Up Rules, Armies")))
r = post("/sounds/upload?name=thunder.wav", b"RIFF" + bytes(2000))
check("soundboard: an uploaded clip is listed; a missing one is refused", "ok" in r and "thunder.wav" in get("/sounds") and "error" in post("/sounds/play?name=nothing.wav") and post("/sounds/play?name=thunder.wav") == {"ok": True}, r)

# ---------------------------------------------------------------- a whole sheet typed in, and a photo of one
chars = paths.data("characters")
sheet = {"name": "Old Tom", "player": "Sam", "edition": "2014", "species": "Dwarf", "background": "Soldier",
         "classlevel": "Fighter (Champion) 3 / Rogue 2", "str": 16, "dex": 14, "con": 14, "int": 10, "wis": 12, "cha": 8,
         "saves": ["str", "con"], "skills": ["athletics", "stealth", "made up"], "expertise": ["stealth", "arcana"],
         "hp_max": 40, "hp_current": 31, "hp_temp": 0, "ac": 17, "speed": 25, "gp": 42, "sp": 7,
         "equipment": "Longsword\n2 x Dagger\nTorch (5)\n50 feet of rope", "spells": "", "features": "Second Wind\nSneak Attack",
         "notes": "Owes the innkeeper."}
r = post("/characters/save", sheet)
tom = dt_characters.load(os.path.join(chars, "old-tom.json"))
check("a whole sheet typed on a phone is saved with nothing to check", r.get("ok") and r["todo"] == [] and r["slug"] == "old-tom", r)
check("typed sheet: two classes with levels, subclass and hit dice", [(k["name"], k["subclass"], k["level"], k["hit_die"]) for k in tom["classes"]] == [("Fighter", "Champion", 3, 10), ("Rogue", None, 2, 8)], tom["classes"])
check("typed sheet: scores, hit points, armour, speed and coins as typed", tom["abilities"]["str"] == 16 and tom["hp"] == {"max": 40, "current": 31, "temp": 0, "gains": []} and tom["ac"] == 17 and tom["speed"] == 25 and tom["coins"]["gp"] == 42 and tom["coins"]["sp"] == 7 and tom["edition"] == "2014")
check("typed sheet: only real skills are kept, and expertise only in a ticked skill", tom["skill_profs"] == ["athletics", "stealth"] and tom["expertise"] == ["stealth"] and tom["save_profs"] == ["str", "con"], (tom["skill_profs"], tom["expertise"]))
check("typed sheet: gear counts are read; fifty feet of rope is one rope", [(i["name"], i["qty"]) for i in tom["equipment"]] == [("Longsword", 1), ("Dagger", 2), ("Torch", 5), ("50 feet of rope", 1)], tom["equipment"])
check("typed sheet: features and notes kept, and the history says where it came from", tom["features"] == ["Second Wind", "Sneak Attack"] and tom["notes"] == "Owes the innkeeper." and "Typed in" in tom["history"][-1]["what"])
back = dt_characters.to_form(tom)
again, _ = dt_characters.from_form(back)
check("a saved sheet put back into the form and saved again is the same character", {k: v for k, v in again.items() if k not in ("history", "ac_note")} == {k: v for k, v in tom.items() if k not in ("history", "ac_note")})
form = get("/characters/edit?name=old-tom")
check("the edit page opens with the sheet filled in", "Edit Old Tom" in form and '"classlevel": "Fighter (Champion) 3 / Rogue 2"' in form and 'data-g=skills' in form, form[:200])
check("the blank form opens too, and a missing character is a 404", "Type in a sheet" in get("/characters/edit") and get("/characters/edit?name=nobody").startswith("HTTP 404"))
check("the list has an Edit link for each character", "/characters/edit?name=old-tom" in get("/characters"))
tom["equipment"][0]["equipped"] = True; tom["equipment"][1]["attuned"] = True; dt_characters.save(tom, chars)
edit = dict(back, hp_current=12, ac=18, equipment="Longsword\n2 x Dagger\nShield")
r = post("/characters/save?was=old-tom", edit)
tom2 = dt_characters.load(os.path.join(chars, "old-tom.json"))
check("editing keeps what is worn and attuned, and the history", r.get("ok") and tom2["hp"]["current"] == 12 and tom2["ac"] == 18 and tom2["equipment"][0]["equipped"] and tom2["equipment"][1]["attuned"]
      and [i["name"] for i in tom2["equipment"]] == ["Longsword", "Dagger", "Shield"] and len(tom2["history"]) == len(tom["history"]) + 1 and tom2["history"][-1]["what"] == "Edited on the phone", r)
r = post("/characters/save?was=old-tom", dict(edit, name="Tom the Elder"))
check("renaming moves the file, leaving no copy behind", r.get("slug") == "tom-the-elder" and os.path.isfile(os.path.join(chars, "tom-the-elder.json")) and not os.path.isfile(os.path.join(chars, "old-tom.json")), r)
r = post("/characters/save", dict(sheet, name="Brakka"))
check("a new sheet cannot write over another character with the same name", "already a character" in r.get("error", "") and dt_characters.load(os.path.join(chars, "brakka.json"))["classes"][0]["level"] == 1, r)
r = post("/characters/save?was=tom-the-elder", dict(edit, name="Brakka"))
check("nor can a rename", "already a character" in r.get("error", "") and os.path.isfile(os.path.join(chars, "tom-the-elder.json")), r)
check("a sheet with no name or no class is refused in plain words", "needs a name" in post("/characters/save", dict(sheet, name=""))["error"] and "Fighter 3" in post("/characters/save", dict(sheet, name="Zed", classlevel=""))["error"])
r = post("/characters/save", dict(sheet, name="Odd One", hp_max=400, ac="", str=45))
check("odd numbers are saved but listed to check", r.get("ok") and len(r["todo"]) >= 2 and any("Strength" in t for t in r["todo"]), r)
r = post("/characters/save?was=../../settings", sheet)
check("an address cannot reach a file outside the characters folder", "no longer on the box" in r.get("error", ""), r)
r = post("/characters/save", dict(sheet, name="Homebrew Hal", classlevel="Gunslinger 4", hit_die=10, hp_max=30))
check("a class I do not know is accepted with the hit die typed in", r.get("ok") and dt_characters.load(os.path.join(chars, "homebrew-hal.json"))["classes"][0]["hit_die"] == 10, r)

def photo(body, kind="image/jpeg"):
    try:
        with urllib.request.urlopen(urllib.request.Request(base + "/characters/photo", data=body, method="POST", headers={"Content-Type": kind}), timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode("utf-8"))
jpeg = b"\xff\xd8\xff" + bytes(3000)
r = photo(jpeg)
check("photo of a sheet with no key: refused, and told to type it in", "Type the sheet in" in r.get("error", ""), r)
open(os.path.join(DATA, "c3.toml"), "w").write('[claude]\napi_key = "k1"\n[limits]\nmonthly_dollars = 500\n')
app.voice = voice.Voice(app, voice.load_config(os.path.join(DATA, "c3.toml")))
sent = []
real_answer = voice.claude_answer
def fake_reader(cfg, system, user, timeout=20.0, **more):
    sent.append((system, user, timeout))
    return 'Here it is:\n{"name": "Mira Vale", "player": null, "species": "Elf", "classlevel": "Wizard (Evoker) 5", "str": 8, "dex": 14, "con": 13, "int": 18, "wis": 12, "cha": 10, "saves": ["INT", "wis"], "skills": ["Arcana", "History"], "hp_max": 27, "hp_current": null, "ac": 12, "speed": 30, "gp": 15, "equipment": ["Quarterstaff", "2 x Dagger", null], "spells": ["Fire Bolt", "Shield"], "features": ["Arcane Recovery"], "favourite colour": "green"}'
voice.claude_answer = fake_reader
r = photo(jpeg)
mira = dt_characters.load(os.path.join(chars, "mira-vale.json"))
check("photo of a sheet: saved as read, and the player is told to check every number", r.get("slug") == "mira-vale" and "check every number" in r["ok"] and r["todo"] == [], r)
check("photo: class, level, scores, hit points and armour came through", mira["classes"][0]["name"] == "Wizard" and mira["classes"][0]["subclass"] == "Evoker" and mira["classes"][0]["level"] == 5 and mira["abilities"]["int"] == 18 and mira["hp"]["max"] == 27 and mira["hp"]["current"] == 27 and mira["ac"] == 12, mira["classes"])
check("photo: ticks, gear, spells and features came through; unknown keys were dropped", mira["save_profs"] == ["int", "wis"] and mira["skill_profs"] == ["arcana", "history"] and [(i["name"], i["qty"]) for i in mira["equipment"]] == [("Quarterstaff", 1), ("Dagger", 2)] and mira["spells"] == ["Fire Bolt", "Shield"] and "favourite colour" not in mira, (mira["save_profs"], mira["equipment"]))
check("photo: the history says it was read from a photo", mira["history"][-1]["what"] == "Read from a photo of a paper sheet")
system, user, timeout = sent[0]
check("photo: the picture is sent as an image block with the list of boxes, and a longer wait is allowed", user[0]["type"] == "image" and user[0]["source"]["media_type"] == "image/jpeg" and len(user[0]["source"]["data"]) > 3000 and '"classlevel"' in user[1]["text"] and timeout == 60.0 and "Never guess" in system)
r = photo(jpeg)
check("the same photo twice does not write over the first character", "already a character" in r.get("error", ""), r)
voice.claude_answer = lambda *a, **k: "I am sorry, I cannot make that out."
n_before = len(os.listdir(chars))
r = photo(jpeg)
check("photo that cannot be read: says so, and saves nothing new", "could not read that photo" in r.get("error", "") and len(os.listdir(chars)) == n_before, r)
voice.claude_answer = lambda *a, **k: '{"name": "Blur", "classlevel": null}'
r = photo(jpeg)
check("photo with a name but no class: not enough, and says what is missing", "could not read enough" in r.get("error", "") and not os.path.isfile(os.path.join(chars, "blur.json")), r)
def down(*a, **k): raise RuntimeError("The network is away.")
voice.claude_answer = down
check("photo with the network away: says so", photo(jpeg).get("error") == "The network is away.")
check("photo: an empty upload and a file that is not a picture are refused", "empty" in photo(b"x").get("error", "") and "not a photo" in photo(jpeg, "application/pdf").get("error", ""))
voice.claude_answer = real_answer
app.voice = v

# ---------------------------------------------------------------- faults found in review, each kept fixed
import socket, sqlite3, types
from concurrent.futures import ThreadPoolExecutor
def raw(port, data):
    """Send bytes as they are, close our side, and return everything that comes back."""
    s = socket.create_connection(("127.0.0.1", port), timeout=10)
    try:
        s.sendall(data); s.shutdown(socket.SHUT_WR)
        out = b""
        while True:
            got = s.recv(65536)
            if not got: return out
            out += got
    except OSError:
        return out
    finally:
        s.close()
# a ruling given in DM mode stays with the DM
def secret(system, user): return "The innkeeper is the villain zorblat. Do keep it quiet."
a = ask.answer("Who is the villain zorblat?", lib, "dnd", "D&D", "", dm=True, llm=secret)
b = ask.answer("who is the villain zorblat", lib, "dnd", "D&D", "", dm=False, llm=None)
check("a ruling given in DM mode is not repeated to the players", a["from"] == "cloud" and "innkeeper" in a["text"] and b["from"] != "ruling" and "innkeeper" not in b["text"], (a, b))
check("the DM is given it again in DM mode", ask.answer("who is the villain zorblat", lib, "dnd", "D&D", "", dm=True, llm=None)["from"] == "ruling")
page = get("/rulings")
check("the rulings web page leaves out DM-mode rulings and keeps the rest", "innkeeper" not in page and "zorblat" not in page and "Restraint is optional." in page)
old_log = [dict((k, v) for k, v in r.items() if k != "dm") for r in ask.rulings() if not r.get("dm")]
paths.write_json(paths.data("rulings.json"), old_log + [r for r in ask.rulings() if r.get("dm")])
check("a ruling saved before DM marks existed is for everyone", "dm" not in ask.rulings()[0] and ask.find_ruling("risk", "Can I attack twice?") is not None)
ask.forget_ruling("dnd", "Who is the villain zorblat?")
# a new or uploaded character never replaces one already there
before = dt_characters.load(os.path.join(chars, "brakka.json"))
r = post("/characters/new", {"name": "brakka", "player": "Someone Else", "cls": "Wizard"})
check("making a new character with a name already taken is refused, and the old one is untouched", "already a character" in r.get("error", "") and dt_characters.load(os.path.join(chars, "brakka.json")) == before, r)
real_import = dt_characters.import_pdf_fields
dt_characters.import_pdf_fields = lambda path: (dt_characters.new_character("Brakka", "X", "Rogue", dict(before["abilities"])), [], [])
r = post("/characters/upload?name=sheet.pdf", b"%PDF-1.4 stand-in")
check("uploading a PDF sheet with a name already taken is refused too", "already a character" in r.get("error", "") and dt_characters.load(os.path.join(chars, "brakka.json")) == before, r)
dt_characters.import_pdf_fields = lambda path: (dt_characters.new_character("Pdf Pat", "X", "Rogue", dict(before["abilities"])), ["check me"], [])
r = post("/characters/upload?name=sheet.pdf", b"%PDF-1.4 stand-in")
check("a PDF sheet with a new name is saved, and its working copy is cleared away", "ok" in r and os.path.isfile(os.path.join(chars, "pdf-pat.json")) and os.listdir(paths.data("uploads")) == [], (r, os.listdir(paths.data("uploads"))))
dt_characters.import_pdf_fields = real_import
# request sizes
out = raw(w.port, b"POST /enter HTTP/1.1\r\nHost: x\r\nContent-Length: -1\r\n\r\ncode=1234")
check("a request that claims a negative length is refused, not read to the end", out.startswith(b"HTTP/1.0 400") and b"too large" in out, out[:120])
check("a phone that goes quiet is dropped after 30 seconds", w.httpd.RequestHandlerClass.timeout == 30)
out = raw(w.port, b"POST /library/upload?game=risk&name=Huge.pdf HTTP/1.1\r\nHost: x\r\nContent-Length: 200000000\r\n\r\n%PDF")
check("a book over 100 MB is refused before it is read, and points to the PC way in LIBRARY.md", out.startswith(b"HTTP/1.0 400") and b"100 MB" in out and b"LIBRARY.md" in out and not os.path.exists(os.path.join(src, "mine", "risk", "Huge.pdf")), out[:200])
raw(w.port, b"POST /library/upload?game=risk&name=Half.txt HTTP/1.1\r\nHost: x\r\nContent-Length: 50000\r\n\r\n" + b"y" * 1000)
pump(lambda: False, 0.3)
check("an upload that stops part way leaves nothing behind", sorted(os.listdir(os.path.join(src, "mine", "risk"))) == ["House Rules.md"], os.listdir(os.path.join(src, "mine", "risk")))
# the message after a library upload is about that file
open(os.path.join(src, "mine", "risk", "Broken.epub"), "wb").write(b"not a zip")
r = post("/library/upload?game=dnd&dm=0&name=Good%20Book.md", b"# Flanking\n\nThe quorble flanks when two allies stand opposite.\n")
check("an upload reports its own result, not another file's failure", r.get("ok", "").startswith("Good Book.md is loaded. 1 sections"), r)
os.remove(os.path.join(src, "mine", "risk", "Broken.epub"))
r = post("/library/upload?game=dnd&dm=0&name=Bad.pdf", b"%PDF-1.4 this is not really a pdf")
check("a book that cannot be read is an error, and is not kept", "could not be read" in r.get("error", "") and not os.path.exists(os.path.join(src, "mine", "dnd", "Bad.pdf")), r)
r = post("/library/upload?game=dnd&dm=0&name=Good%20Book.md", b"# Flanking\n\nThe quorble flanks when two allies stand opposite.\n")
check("the same book uploaded again says it was already loaded", "already loaded" in r.get("ok", ""), r)
pump(lambda: False, 0.3)
# the library stays readable while a book is being loaded
busy = dt_content.connect(os.environ["DT_CONTENT_DB"])
check("the library file is in write-ahead mode, so reading does not wait for loading", busy.execute("PRAGMA journal_mode").fetchone()[0] == "wal")
for i in range(3000):
    cur = busy.execute("INSERT INTO docs(path,game,source,title,body,mine,dm_only) VALUES('big','dnd','Big','T',?,1,0)", ("lorem %d " % i * 300,))
    busy.execute("INSERT INTO docs_fts(rowid,title,body) VALUES(?,?,?)", (cur.lastrowid, "T", "lorem %d " % i * 300))
t0 = time.time()
found, n_sections = app.library.search("quorble", "dnd"), app.library.counts()[0]
entry = app.library.doc(found[0]["id"]) if found else None
check("Lookup still answers at once while a big book is half loaded", time.time() - t0 < 1.5 and found and entry and "quorble" in entry["body"] and 0 < n_sections < 3000, (time.time() - t0, found, n_sections))
busy.rollback(); busy.close()
none = Library(os.path.join(DATA, "no-such.db"))
check("with no library file at all, every question to it has a quiet answer", none.counts() == (0, 0) and none.games() == [] and none.search("x") == [] and none.doc(1) is None and none.card("x") is None and none.excerpts("x") == [])
open(os.path.join(DATA, "junk.db"), "wb").write(b"this is not a database" * 100)
junk = Library(os.path.join(DATA, "junk.db"))
check("a library file that is not a database does not crash the screens", junk.counts() == (0, 0) and junk.games() == [] and junk.search("x") == [] and junk.doc(1) is None and junk.card("x") is None)
# config.toml with a slip in it
def slip(text):
    open(os.path.join(DATA, "slip.toml"), "w").write(text)
    return voice.load_config(os.path.join(DATA, "slip.toml"))
slips = [slip('[claude]\napi_key = sk-ant-abc123\n'), slip('api_key = "sk"\n[claude]\nmodel = "x"\n'), slip('[claude]\napi_key = "sk"\n[limits]\nmonthly_dollars = "five"\n')]
check("a slip in config.toml gives the defaults and a plain message, not a crash",
      all(c["problem"].startswith("config.toml could not be read: ") and c["claude"]["model"] == "claude-haiku-5-5" and c["claude"]["api_key"] == "" and c["limits"]["monthly_dollars"] == 5.0 for c in slips), [c["problem"] for c in slips])
check("a good config.toml has no such message", cfg2["problem"] == "" and cfg["problem"] == "")
vs = voice.Voice(app, slips[0])
check("the slip is shown with the voice status in Settings", "config.toml could not be read" in vs.status() and "answers off" in vs.status() and "config.toml" not in v.status(), vs.status())
# files written whole or not at all
spend_was = open(voice.spend_path()).read()
open(voice.spend_path(), "w").write("[]")
check("a spend file holding the wrong thing counts as nothing spent, and is put right by the next spend", voice.spent_this_month() == 0.0 and voice.add_spend(0.5) == 0.5 and voice.spent_this_month() == 0.5)
open(voice.spend_path(), "w").write(spend_was)
paths.write_json(os.path.join(DATA, "w.json"), {"a": [1, 2]}, indent=1)
check("write_json writes the file and leaves no working copy", json.load(open(os.path.join(DATA, "w.json"))) == {"a": [1, 2]} and not os.path.exists(os.path.join(DATA, "w.json.tmp")))
ask.save_ruling("risk", "Is this saved whole?", "Yes.", "nowhere", "cloud"); voice.add_spend(0.0)
check("rulings, spend and settings leave no working copies behind", not [n for n in os.listdir(DATA) if n.endswith(".tmp")] and ask.find_ruling("risk", "is this saved whole") is not None, os.listdir(DATA))
ask.forget_ruling("risk", "Is this saved whole?")
settings.put("dm_code", "4821"); settings.put("cloud", False)
oops = []
def hammer(key):
    try:
        for i in range(150):
            settings.put(key, i)
            if settings.get("cloud") is not False or settings.get("dm_code") != "4821": oops.append("defaults seen")
    except Exception as e:
        oops.append(repr(e))
ts = [threading.Thread(target=hammer, args=(k,)) for k in ("volume", "scratch_a", "scratch_b")]
[t.start() for t in ts]; [t.join() for t in ts]
check("settings written from three threads at once: nothing lost, nothing half read", oops == [] and settings.get("volume") == 149 and settings.get("scratch_a") == 149 and settings.get("scratch_b") == 149 and settings.get("dm_code") == "4821", oops[:3])
settings.put("cloud", True); settings.put("volume", 70); settings.put("dm_code", "0000")
# a Claude reply that ran out of room
reply = types.SimpleNamespace(stop_reason="max_tokens", usage=types.SimpleNamespace(input_tokens=10, output_tokens=10),
                              content=[types.SimpleNamespace(type="text", text='{"name": "Zed", "equipment": ["Rope", "2 x Dag')])
class NoSuch(Exception): pass
real_sdk = sys.modules.get("anthropic")
sys.modules["anthropic"] = types.SimpleNamespace(Anthropic=lambda **k: types.SimpleNamespace(messages=types.SimpleNamespace(create=lambda **kw: reply)),
                                                 AuthenticationError=NoSuch, RateLimitError=NoSuch, APIStatusError=NoSuch, APIConnectionError=NoSuch)
def said(fn):
    try: return fn()
    except RuntimeError as e: return "RuntimeError: %s" % e
check("a spoken answer that ran out of room is used as far as it got", said(lambda: voice.claude_answer(cfg2, "s", "q")).startswith('{"name": "Zed"'))
check("a sheet photo that ran out of room says the sheet is too long and to type it in", said(lambda: voice.read_sheet_photo(cfg2, jpeg)) == "RuntimeError: " + voice.SHEET_TOO_LONG and "Type it in" in voice.SHEET_TOO_LONG, said(lambda: voice.read_sheet_photo(cfg2, jpeg)))
# on the Pi the anthropic package is not installed: the same answer over plain HTTPS
sys.modules["anthropic"] = None                              # importing it now fails, as it does there
sent = {}
class FakeReply:
    def __init__(self, data): self.data = data
    def read(self): return self.data
    def __enter__(self): return self
    def __exit__(self, *a): return False
def fake_open(req, timeout=None):
    sent.update(url=req.full_url, headers={k.lower(): v for k, v in req.header_items()}, body=json.loads(req.data.decode()))
    return FakeReply(json.dumps({"stop_reason": "end_turn", "usage": {"input_tokens": 1000, "output_tokens": 1000},
                                 "content": [{"type": "text", "text": "Three dice."}]}).encode())
real_open = voice.urllib.request.urlopen
voice.urllib.request.urlopen = fake_open
spent_before = voice.spent_this_month()
check("with no anthropic package the answer comes over plain HTTPS", said(lambda: voice.claude_answer(cfg2, "sys", "q")) == "Three dice.")
check("that request goes to the Messages address with the key and version headers, and carries the question",
      sent.get("url") == "https://api.anthropic.com/v1/messages" and sent["headers"].get("x-api-key") == cfg2["claude"]["api_key"]
      and sent["headers"].get("anthropic-version") == "2023-06-01" and sent["body"]["messages"] == [{"role": "user", "content": "q"}]
      and sent["body"]["system"] == "sys", sent)
check("and its cost is added to the month's spending", voice.spent_this_month() > spent_before, (spent_before, voice.spent_this_month()))
def refuse(req, timeout=None):
    raise voice.urllib.error.HTTPError(req.full_url, 401, "no", {}, None)
voice.urllib.request.urlopen = refuse
check("over plain HTTPS a refused key is reported in plain words", said(lambda: voice.claude_answer(cfg2, "s", "q")) == "RuntimeError: The Claude API key was refused.")
voice.urllib.request.urlopen = real_open
if real_sdk is None: del sys.modules["anthropic"]
else: sys.modules["anthropic"] = real_sdk
open(voice.spend_path(), "w").write(spend_was)
# the speech service's WAV says its length is "unknown"; the Pi will not play that
import struct, wave as wave_mod, io as io_mod
sound = bytes(range(200)) * 3
unknown = b"RIFF" + b"\xff" * 4 + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, 24000, 48000, 2, 16) + b"data" + b"\xff" * 4 + sound
mended = voice.true_lengths(unknown)
wav_read = wave_mod.open(io_mod.BytesIO(mended))
check("a WAV that says its length is unknown is given its true lengths, sound untouched",
      struct.unpack("<I", mended[4:8])[0] == len(unknown) - 8 and wav_read.getnframes() == len(sound) // 2 and wav_read.readframes(wav_read.getnframes()) == sound and wav_read.getframerate() == 24000)
check("a WAV that was already right, and bytes that are not a WAV, come back unchanged", voice.true_lengths(mended) == mended and voice.true_lengths(b"not a wav at all") == b"not a wav at all")
real_post = voice._post
voice._post = lambda *a, **k: unknown
from deepthought import voicefx
sp = cfg2["speech"]
got = voice.text_to_speech(cfg2, "Hello.")
check("speech fetched from the service is saved with true lengths, shaped into her voice and raised",
      got == voice.full_volume(voicefx.shape(mended, 0.97, 1.15, 0.15, 0.3), press=2.0)
      and wave_mod.open(io_mod.BytesIO(got)).getnframes() > 0)
check("her voice as chosen on 23 Nov 2026 is what a box with no settings of its own uses",
      cfg["speech"]["tts_voice"] == "nova" and cfg["speech"]["tts_style"] == persona.SPEAKING and "Never angry" in persona.SPEAKING
      and "never condescending" in persona.VOICE)
# the shaping itself
def wav16(samples, rate=24000):
    d = struct.pack("<%dh" % len(samples), *samples)
    return b"RIFF" + struct.pack("<I", 36 + len(d)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16) + b"data" + struct.pack("<I", len(d)) + d
def opened(wav):
    r = wave_mod.open(io_mod.BytesIO(wav)); return r.getframerate(), struct.unpack("<%dh" % r.getnframes(), r.readframes(r.getnframes()))
word = [int(8000 * ((i % 40) - 20) / 20.0) for i in range(4800)]
line = wav16(word + [0] * 7200 + word)                       # a word, 0.3 s of silence, a word
check("nothing asked of the shaping, or not a WAV: the bytes come back as they were",
      voicefx.shape(line) == line and voicefx.shape(b"not a wav", 0.9, 2, 1, 1) == b"not a wav")
rate, deep = opened(voicefx.shape(line, pitch=0.9))
check("deeper: the same sound played at nine tenths of the rate, so slower too", rate == 21600 and len(deep) == 16800)
rate, slow = opened(voicefx.shape(line, pauses=2.0))
check("longer pauses: the silence in the middle is doubled, the words and the ends are not",
      rate == 24000 and len(slow) == 16800 + 7200 and max(abs(v) for v in slow[4900:19100]) == 0 and max(slow[:4800]) > 20000)
rate, hall = opened(voicefx.shape(line, hall=0.5))
check("a hall: the sound goes on after the words stop, and never past full scale",
      len(hall) > 16800 + 24000 and max(abs(v) for v in hall[16900:20000]) > 50 and max(abs(v) for v in hall) <= 30000)
rate, metal = opened(voicefx.shape(line, metal=0.5))
check("a ring: same length, the silence after a word is no longer silent", len(metal) == 16800 and max(abs(v) for v in metal[4900:5400]) > 50)
# found on the real Pi, 23 Nov 2026: her lines were saved at under half volume and could barely be heard
def wav_of(samples):
    d = struct.pack("<%dh" % len(samples), *samples)
    return b"RIFF" + struct.pack("<I", 36 + len(d)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, 24000, 48000, 2, 16) + b"data" + struct.pack("<I", len(d)) + d
def samples_of(wav):
    r = wave_mod.open(io_mod.BytesIO(wav)); return struct.unpack("<%dh" % r.getnframes(), r.readframes(r.getnframes()))
quiet = wav_of([0, 5000, -10000, 2500])
check("a quiet line is brought up so its loudest moment is near full scale, its shape kept",
      samples_of(voice.full_volume(quiet)) == (0, 15500, -31000, 7750), samples_of(voice.full_volume(quiet)))
check("a line already loud, near silence, and bytes that are not a WAV come back unchanged",
      voice.full_volume(wav_of([0, 31000, -200])) == wav_of([0, 31000, -200]) and voice.full_volume(wav_of([0, 40, -30])) == wav_of([0, 40, -30])
      and voice.full_volume(b"not a wav at all") == b"not a wav at all" and voice.full_volume(voice.full_volume(quiet)) == voice.full_volume(quiet))
pressed = samples_of(voice.full_volume(wav_of([int(9000 * (i % 7 - 3) / 3.0) for i in range(700)] + [200] * 300), press=4))
rms_of = lambda xs: (sum(x * x for x in xs) / len(xs)) ** 0.5
check("a pressed line stays inside full scale and is louder on average than one only raised",
      max(pressed) <= 31000 and min(pressed) >= -31000
      and rms_of(pressed) > 1.2 * rms_of(samples_of(voice.full_volume(wav_of([int(9000 * (i % 7 - 3) / 3.0) for i in range(700)] + [200] * 300)))))
sent = {}
voice._post = lambda url, key, body, kind: sent.update(json.loads(body)) or quiet
bare = dict(cfg2["speech"], tts_model="tts-1", tts_style="", tts_press=0, tts_pitch=1, tts_pauses=1, tts_metal=0, tts_hall=0)
plain = dict(cfg2, speech=bare)
styled = dict(cfg2, speech=dict(bare, tts_style="Slow and weary."))
voice.text_to_speech(plain, "Hello."); no_style = "instructions" not in sent
voice.text_to_speech(styled, "Hello.")
voice._post = real_post
check("a speaking style set in the config is sent with the line, and none is sent when none is set",
      no_style and sent.get("instructions") == "Slow and weary.", sent)
v_plain, v_styled = voice.Voice.__new__(voice.Voice), voice.Voice.__new__(voice.Voice)
v_plain.cfg, v_styled.cfg = plain, styled
check("a line made in one style is never played for another", v_plain.cache_file("Hello.") != v_styled.cache_file("Hello."))
v_deep = voice.Voice.__new__(voice.Voice); v_deep.cfg = dict(cfg2, speech=dict(bare, tts_pitch="0.9"))
check("a number in the config that is not a number is taken as the plain setting", voice._num({"tts_pitch": "deep"}, "tts_pitch", 1) == 1.0 and voice._num({}, "tts_hall", 0) == 0.0)
import hashlib as hl
check("nor one made at another pitch; and a plain voice keeps the file names it always had",
      v_deep.cache_file("Hello.") != v_plain.cache_file("Hello.")
      and os.path.basename(v_plain.cache_file("Hello.")) == hl.sha1(("tts-1|%s|Hello." % bare["tts_voice"]).encode()).hexdigest() + ".wav")
check("a very faint line is raised six times at most", max(samples_of(voice.full_volume(wav_of([0, 1000, -500])))) == 6000)
voice._post = real_post
# small things
check("an error from the box is shown on the phone as plain text, never as HTML", "m.textContent=r.error" in get("/characters") and "$('msg').textContent=r.error" in get("/characters/edit"))
real_ip = web.local_ip
web.local_ip = lambda: "10.1.2.3"
check("the address shown for phones is worked out when asked, so late Wi-Fi is picked up", w.url == "http://10.1.2.3:%d" % w.port)
web.local_ip = real_ip
w.url = "http://example.test:1"; fixed = w.url; w.url = None
check("an address set by hand is kept until it is cleared", fixed == "http://example.test:1" and w.url.startswith("http://") and w.url.endswith(":%d" % w.port))
check("a server that is not running has no address", web.Web(app, port=0, lock=False).url == "")
import importlib.util
spec = importlib.util.spec_from_file_location("build_audio", os.path.join(paths.SOFTWARE, "tools", "build_audio.py"))
build_audio = importlib.util.module_from_spec(spec); spec.loader.exec_module(build_audio)
real_cfg, real_tts, real_argv = voice.load_config, voice.text_to_speech, sys.argv
voice.load_config, voice.text_to_speech, sys.argv = (lambda path=None: cfg2), (lambda c, text: b"RIFF" + text.encode("utf-8")), ["build_audio.py"]
import contextlib, io
with contextlib.redirect_stdout(io.StringIO()):
    build_audio.main()
voice.load_config, voice.text_to_speech, sys.argv = real_cfg, real_tts, real_argv
made = os.listdir(paths.data("speech"))
check("build_audio makes every stock line as a whole file, with no part files left", len([n for n in made if n.endswith(".wav")]) == len(build_audio.all_lines()) and not [n for n in made if not n.endswith(".wav")], made[:5])

from deepthought.screens.web_link import PhoneLink, qr_matrix
app.go_home(); app.push(PhoneLink(app)); link = app.screen; app.render()
m = qr_matrix(link.scan_url())
# the code's size depends on how long the box's address is, so look inside its own white edge
qr_cell = 296 // len(m); qr_top = 76 + (296 - qr_cell * len(m)) // 2
check("phone link screen: a square QR code for the address, drawn on screen", m and len(m) == len(m[0]) and link.url().endswith("/play") and app.surface.get_at((30 + qr_cell, qr_top + qr_cell))[:3] == (255, 255, 255))
check("the web server's waiting line is long enough for a table of phones", web.Server.request_queue_size >= 64)
app.gesture("press"); check("the button steps through the pages", link.url().endswith(":%d/" % w.port))

# ---------------------------------------------------------------- the table code
import http.cookiejar
w2 = web.Web(app, port=0)
check("by default the pages ask for the table code", w2.start() and w2.lock is True)
code = web.table_code()
check("the table code is four digits, and stays the same", len(code) == 4 and code.isdigit() and web.table_code() == code)
base2 = "http://127.0.0.1:%d" % w2.port
def phone_browser():
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def fetch(br, path, data=None):
    try:
        with br.open(urllib.request.Request(base2 + path, data=data, method="POST" if data is not None else "GET"), timeout=5) as r:
            return r.status, r.read().decode("utf-8"), r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8"), path
a = phone_browser()
check("the scoreboard needs no code", fetch(a, "/")[0] == 200 and json.loads(fetch(a, "/state.json")[1])["playing"] is True)
st, body, where = fetch(a, "/play")
check("a phone without the code is sent to the code page", st == 200 and "Table code" in body and "/enter?next=/play" in where, where)
for path in ("/characters", "/library", "/games", "/rulings", "/sounds", "/phone.json?seat=0"):
    st, body, where = fetch(a, path)
    check("%s is closed without the code" % path, "/enter" in where and "Table code" in body, (st, where))
phase = app.session.state["phase"]
st, body, _ = fetch(a, "/do?seat=0&i=0", b"Next")
check("without the code a phone cannot press Next", st == 401 and "error" in json.loads(body) and app.session.state["phase"] == phase, (st, body))
st, body, _ = fetch(a, "/library/upload?game=risk&dm=0&name=sneaky.txt", b"nothing to see")
check("without the code nothing can be uploaded", st == 401 and not os.path.isfile(os.path.join(src, "mine", "risk", "sneaky.txt")))
wrong = "0000" if code != "0000" else "1111"
st, body, _ = fetch(a, "/enter?next=/play", ("code=" + wrong).encode())
check("a wrong code is refused, and says where the right one is", "That is not the code" in body and "Settings, then Phones" in body)
for _ in range(web.MAX_TRIES - 1):
    fetch(a, "/enter", ("code=" + wrong).encode())
st, body, _ = fetch(a, "/enter?next=/play", ("code=" + code).encode())
check("after five wrong codes even the right one must wait a minute", "Too many wrong codes" in body and "/enter" in fetch(a, "/play")[2])
w2.locked_until = 0
st, body, where = fetch(a, "/enter?next=/games", ("code=" + code).encode())
check("the right code lets the phone in, and takes it to the page it wanted", st == 200 and where.endswith("/games") and "Add a board game" in body, where)
check("with the code but no seat chosen, a phone is told to choose one, and is shown nothing of the seat",
      fetch(a, "/phone.json?seat=0")[0] == 403 and json.loads(fetch(a, "/phone.json?seat=0")[1]) == {"playing": False, "error": web.SEAT_FIRST})
fetch(a, "/play?seat=0")
check("and it is not asked again", "/enter" not in fetch(a, "/library")[2] and json.loads(fetch(a, "/phone.json?seat=0")[1])["playing"])
fetch(a, "/play?seat=%d" % app.session.game.active(app.session.state))
st, body, _ = fetch(a, "/do?seat=%d&i=0" % app.session.game.active(app.session.state), b"Next")
check("with the code, Next from the phone works", st == 200 and json.loads(body) == {"ok": True}, body)
b = phone_browser()
st, body, where = fetch(b, "/characters?code=" + code)
check("a code scanned from the box's screen opens the page with no typing", st == 200 and "Make a new level 1 character" in body)
check("and that phone is remembered too", "/enter" not in fetch(b, "/sounds")[2])
c3 = phone_browser()
fetch(c3, "/enter?next=//example.com/x", ("code=" + code).encode())
st, body, where = fetch(c3, "/enter?next=//example.com/x", ("code=" + code).encode())
check("the code page never sends a phone to another site", where.startswith(base2) and where.endswith("/play"), where)
new = web.new_table_code()
check("a new code is different, and the old phones must enter it again", new != code and web.table_code() == new and "/enter" in fetch(a, "/library")[2] and "/enter" in fetch(b, "/sounds")[2])
app.web = w2; app.go_home(); app.push(PhoneLink(app)); link = app.screen; app.render()
check("the box's QR code carries the new code for My seat", link.scan_url().endswith("/play?code=" + new) and link.locked())
app.gesture("press"); app.render()
check("but not for the open scoreboard", link.scan_url().endswith(":%d/" % w2.port) and not link.locked())
bad = [tuple(x.rect) for x in link.widgets if x.action and (x.rect.h < 64 or x.rect.w < 64)]
check("the Phones screen's four buttons are big enough", len([x for x in link.widgets if x.action]) == 4 and bad == [], bad)
w2.tries, w2.locked_until = 0, 0
def guess(i):
    try:
        with urllib.request.urlopen(urllib.request.Request(base2 + "/enter", data=b"code=x%d" % i, method="POST"), timeout=10) as r:
            return "That is not the code" in r.read().decode("utf-8")
    except urllib.error.HTTPError:
        return False
from concurrent.futures import ThreadPoolExecutor
with ThreadPoolExecutor(40) as pool:
    looked_at = sum(pool.map(guess, range(120)))
check("120 wrong codes sent at once: only five are looked at before the lock", looked_at == web.MAX_TRIES, looked_at)
st, body, where = fetch(phone_browser(), "/library?code=" + new)
check("during the lock a scanned code is told to wait, not just shown the code page", "Too many wrong codes" in body and "why=wait" in where and "Upload" not in body, where)
w2.tries, w2.locked_until = 0, 0
st, body, where = fetch(phone_browser(), "/library?code=x1")
check("a scanned code that is wrong is told so", "That is not the code" in body and "why=wrong" in where, where)
w2.tries, w2.locked_until = 0, 0
w2.stop(); app.web = w

# ---------------------------------------------------------------- found in the second review
import sqlite3
risk_dir = os.path.join(src, "mine", "risk")
# a ruling is the DM's alone only when a DM-only page was used
ask.forget_ruling("risk", "What is the flarn rule?")
calls7 = []
def llm7(system, user):
    calls7.append(user); return "One reroll a game. I trust that was worth asking."
a = ask.answer("What is the flarn rule?", app.library, "risk", "Risk", "", dm=True, llm=llm7)
b = ask.answer("what is the flarn rule", app.library, "risk", "Risk", "", dm=False, llm=llm7)
check("a ruling given while DM mode is on, but resting on no DM-only page, is for everyone: the same answer, one cloud call",
      a["from"] == "cloud" and b["from"] == "ruling" and b["text"] == a["text"] and len(calls7) == 1 and not ask.rulings()[-1].get("dm"), (a, b))
check("and it is listed on the rulings web page", "flarn" in get("/rulings"))
ask.forget_ruling("risk", "What is the flarn rule?")

# the library page
page = get("/library")
check("the library page checks the size itself before sending, and says so plainly if the upload is lost",
      "f.size>%d" % web.MAX_BOOK in page and "larger than 100 MB" in page and "catch(e)" in page and "did not get through" in page)

# two books at once, and a library file held by something else
real_txt, real_connect = dt_content.READERS[".txt"], dt_content.connect
def slow_txt(path):
    if os.path.basename(path) == "Big.txt": time.sleep(1.5)       # a stand-in for a big PDF on a Pi 2
    yield from real_txt(path)
def quick_connect(db):
    con = real_connect(db); con.execute("PRAGMA busy_timeout=100"); return con    # so the test need not wait five seconds
dt_content.READERS[".txt"], dt_content.connect = slow_txt, quick_connect
got2 = {}
def up2(name, text): got2[name] = post("/library/upload?game=risk&dm=0&name=" + name, text.encode())
ta = threading.Thread(target=up2, args=("Big.txt", "The first book. The vorpnik marches at dawn.\n")); ta.start(); time.sleep(0.4)
tb = threading.Thread(target=up2, args=("Small.txt", "The second book. The skreeb flanks at dusk.\n")); tb.start(); ta.join(); tb.join()
dt_content.READERS[".txt"] = real_txt
pump(lambda: False, 0.3)
check("two books uploaded at once are both loaded and both kept",
      all("ok" in got2.get(n, {}) for n in ("Big.txt", "Small.txt")) and all(os.path.isfile(os.path.join(risk_dir, n)) for n in ("Big.txt", "Small.txt"))
      and app.library.search("vorpnik") and app.library.search("skreeb"), got2)
holder = sqlite3.connect(os.environ["DT_CONTENT_DB"]); holder.execute("BEGIN IMMEDIATE")      # the loader run by hand, say
r = post("/library/upload?game=risk&dm=0&name=Later.txt", b"The third book. The mibbet waits by the gate.\n")
holder.rollback(); holder.close()
check("when the library file is held by something else the book is kept, and the page says to upload it again",
      "busy" in r.get("error", "") and "upload it again" in r.get("error", "") and os.path.isfile(os.path.join(risk_dir, "Later.txt")), r)
r = post("/library/upload?game=risk&dm=0&name=Later.txt", b"The third book. The mibbet waits by the gate.\n")
pump(lambda: False, 0.3)
check("and uploading it again then loads it", r.get("ok", "").startswith("Later.txt is loaded. 1 sections") and app.library.search("mibbet"), r)
dt_content.connect = real_connect

# nothing is left waiting beside content.db
app.library.counts()                                      # she has the library open, as when running
r = post("/library/upload?game=risk&dm=0&name=Last.md", "# Last\n\nThe plonkit is counted last.\n".encode())
pump(lambda: False, 0.3)
found_last = bool(app.library.search("plonkit"))          # and opens it again to look
app.close_library()                                       # what the main loop does when it stops
alone = tempfile.mkdtemp()
shutil.copy(os.environ["DT_CONTENT_DB"], os.path.join(alone, "content.db"))               # content.db by itself, as LIBRARY.md says to copy it
c = sqlite3.connect(os.path.join(alone, "content.db"))
n_alone = c.execute("SELECT count(*) FROM docs WHERE body LIKE '%plonkit%'").fetchone()[0]
c.close()
wal = os.environ["DT_CONTENT_DB"] + "-wal"
check("once she has let go of the library, content.db alone holds every upload: nothing is left in content.db-wal",
      "ok" in r and found_last and n_alone == 1 and (not os.path.exists(wal) or os.path.getsize(wal) == 0),
      (r, found_last, n_alone, os.path.exists(wal) and os.path.getsize(wal)))
check("and she opens it again the next time it is wanted", bool(app.library.search("plonkit")))
# ---------------------------------------------------------------- phone actions that ask for a value
class Heard:
    def __init__(self): self.said = []
    def say(self, text, show=True): self.said.append(text)
    def hold(self, on): pass
old_voice, app.voice = app.voice, Heard()
# the dice remark is said aloud, not only shown (found silent on the real Pi)
from deepthought.screens.dice import Dice as DiceScreen
settings.put("chatty", "chatty")
d = DiceScreen(app); d.roll()
check("a dice roll's remark is spoken as well as shown, when she is set to chatty", app.voice.said == [d.line] and d.line in [l for ls in dice_mod.REMARKS.values() for l in ls], app.voice.said)
settings.put("chatty", "terse"); app.voice.said = []
for _ in range(200): d.roll()
check("set to terse she remarks aloud on only a few rolls", 8 < len(app.voice.said) < 60, len(app.voice.said))
settings.put("chatty", "normal"); app.voice.said = []
page_js = get("/play?seat=0")
check("the phone page can ask for a value: a list to pick from and a box to type in, sent with the action",
      "openAsk" in page_js and "JSON.stringify({label:label,text:text})" in page_js and "id=ask" in page_js)
app.go_home(); app.toast = None
app.start_game(app.plugins["wh40k"], ["Ethan", "Trevor"], {"mode": "Reminder", "necrons": "Nobody"})
ph0 = json.loads(get("/phone.json?seat=0"))
i = ph0["actions"].index("Name Secondary 1")
check("phone.json: an action that asks says what to ask and what to offer; the others say nothing",
      len(ph0["asks"]) == len(ph0["actions"]) and ph0["asks"][0] is None and ph0["asks"][i]["ask"] and len(ph0["asks"][i]["choices"]) > 5 and ph0["asks"][i]["max"] == 24, ph0["asks"][i])
r = post("/do?seat=0&i=%d" % i, {"label": "Name Secondary 1", "text": "grobnar hunt"})         # a made-up name, typed
check("40k: a secondary named on a phone is named on the box", r == {"ok": True} and app.session.state["secs"][0][0]["name"] == "Grobnar Hunt" and app.session.state["secs"][1][0]["name"] == "Secondary 1", r)
r = post("/do?seat=0&i=%d" % i, b"Name Secondary 1")
check("a stale button after the row was named is refused", "error" in r, r)
ph0 = json.loads(get("/phone.json?seat=0"))
j = ph0["actions"].index("Name Secondary 2")
r = post("/do?seat=0&i=%d" % j, {"label": "Name Secondary 2", "text": "GROBNAR hunt"})
check("40k: a refusal from the box reaches the phone in words", "already in the other row" in r.get("error", "") and app.session.state["secs"][0][1]["name"] == "Secondary 2", r)
r1, r2 = post("/do?seat=0&i=%d" % j, b"Name Secondary 2"), post("/do?seat=0&i=%d" % j, {"label": "Name Secondary 2", "text": "   "})
check("an action that asks, sent with no value, is refused and nothing is logged", "error" in r1 and "error" in r2 and app.session.state["secs"][0][1]["name"] == "Secondary 2", (r1, r2))
j1 = json.loads(get("/phone.json?seat=1"))["actions"].index("Name Secondary 2")
r = post("/do?seat=1&i=%d" % j1, {"label": "Name Secondary 2", "text": "x" * 80})
check("40k: seat 2's phone names seat 2's own row, never seat 1's; a long value is cut to the action's limit",
      r == {"ok": True} and app.session.state["secs"][1][1]["name"] == "X" + "x" * 23 and app.session.state["secs"][0][1]["name"] == "Secondary 2", app.session.state["secs"])
r = post("/do?seat=1&i=%d" % ph0["actions"].index("Change Grobnar Hunt"), {"label": "Change Grobnar Hunt", "text": "Hold The Bridge"})
check("40k: seat 2 cannot press seat 1's Change button", "error" in r and app.session.state["secs"][0][0]["name"] == "Grobnar Hunt", r)
r = post("/do?seat=0&i=%d" % ph0["actions"].index("Change Grobnar Hunt"), {"label": "Change Grobnar Hunt", "text": "Hold The Bridge"}, dev=1)
check("40k: nor can seat 2's phone do it by saying it is seat 1", r == {"error": web.SEAT_TAKEN} and app.session.state["secs"][0][0]["name"] == "Grobnar Hunt", r)
# the list of buttons moves while a name is being chosen
seat = app.session.state["active"]
i = json.loads(get("/phone.json?seat=%d" % seat))["actions"].index("Name Secondary 2")
while app.session.state["active"] == seat: w.on_main(lambda: app.game_event({"ev": "next"}))
moved = json.loads(get("/phone.json?seat=%d" % seat))["actions"].index("Name Secondary 2")
r = post("/do?seat=%d&i=%d" % (seat, i), {"label": "Name Secondary 2", "text": "late pick"})
check("40k: a name picked after the turn passed (the button has moved up the list) is still taken, for the button that was pressed",
      moved != i and r == {"ok": True} and app.session.state["secs"][seat][1]["name"] == "Late Pick", (i, moved, r))
# what a hostile phone could send as the value
k = json.loads(get("/phone.json?seat=%d" % seat))["actions"].index("Change Late Pick")
for bad in (None, 12345, {"a": [1]}, ["x"], "\x00\x1b"):
    r = post("/do?seat=%d&i=%d" % (seat, k), {"label": "Change Late Pick", "text": bad})
    check("40k: a value of %r is no name: refused, nothing changes" % (bad,), "needs a name" in r.get("error", "") and app.session.state["secs"][seat][1]["name"] == "Late Pick", r)
n_log = len(app.session.log)
r = post("/do?seat=%d&i=%d" % (seat, k), {"label": "Change Late Pick", "text": "nu\x00l su\ud800r esc\x1b"})
with open(app.session.path, encoding="utf-8") as f: saved = json.load(f)
w.on_main(lambda: app.render())
check("40k: characters that cannot be drawn or saved never reach the game: the name is kept without them, saved, and the screen still draws",
      r == {"ok": True} and app.session.state["secs"][seat][1]["name"] == "Nu L Su R Esc" and saved["state"]["secs"][seat][1]["name"] == "Nu L Su R Esc"
      and len(saved["log"]) == n_log + 1 and app.toast != app_mod.TROUBLE, (r, app.session.state["secs"][seat]))
r = post("/do?seat=%d&i=0" % seat, b'{"label":"x","text":' + b"[" * 200000 + b"]" * 200000 + b"}")
check("a value nested beyond reading is refused in words, and the pages go on working", "error" in r and json.loads(get("/state.json"))["playing"], str(r)[:200])
# Kill Team: the secret Tac Op, typed on a phone
app.go_home(); app.toast = None
app.start_game(app.plugins["killteam"], ["Ethan", "Trevor"], {"mode": "Reminder", "length": "Full, 4 rounds", "tacops": "On"})
app.voice.said = []; app.toast = None
ph1 = json.loads(get("/phone.json?seat=1"))
k = ph1["actions"].index("Record my Tac Op")
check("Kill Team: the phone asks for the Tac Op by typing; the box offers no list of names", ph1["asks"][k]["ask"] and ph1["asks"][k]["choices"] == [])
r = post("/do?seat=1&i=%d" % k, {"label": "Record my Tac Op", "text": "zzyzx gambit"})
everyone = get("/state.json") + get("/phone.json?seat=0") + get("/phone.json?seat=2") + get("/") + (app.toast or "") + " ".join(app.voice.said)
# the other player's phone (seat 1 is Trevor's; phone 0 sits in seat 0) and a phone with no seat try every address
tries = ["/phone.json?seat=1", "/phone.json?seat=%2B1", "/phone.json?seat=01", "/phone.json?seat=1&seat=0", "/phone.json?seat=0&seat=1",
         "/phone.json?seat=1.0", "/phone.json?seat=-1", "/phone.json", "/play?seat=1", "/play", "/play?seat=0", "/phone.json?seat=0", "/state.json", "/"]
got = {(dev, path): get(path, dev=dev) for dev in (0, "nobody") for path in tries}
check("Kill Team: the other player's phone, and a phone with no seat, cannot read the Tac Op at any address",
      not [k for k, v in got.items() if "zzyzx" in v.lower()], [k for k, v in got.items() if "zzyzx" in v.lower()])
check("Kill Team: asking for the taken seat is refused in words", "HTTP 403" in got[(0, "/phone.json?seat=1")] and "in use on another phone" in got[(0, "/phone.json?seat=1")]
      and "in use on another phone" in got[(0, "/play?seat=1")] and "const seat=1" not in got[(0, "/play?seat=1")], got[(0, "/play?seat=1")][-300:])
check("Kill Team: the list of seats shows which is taken, as words and no link, to a phone that does not hold it",
      "Trevor (in use)" in got[("nobody", "/play")] and "/play?seat=1" not in got[("nobody", "/play")] and "/play?seat=1" in get("/play", dev=1), got[("nobody", "/play")][-400:])
try:
    with urllib.request.urlopen(urllib.request.Request(base + "/phone.json?seat=1", headers={"Cookie": "dts1=" + "0" * 32}), timeout=5) as resp: forged = resp.read().decode()
except urllib.error.HTTPError as e: forged = "HTTP %s %s" % (e.code, e.read().decode())
check("Kill Team: a made-up seat cookie is no use", "HTTP 403" in forged and "zzyzx" not in forged.lower(), forged)
check("Kill Team: a Tac Op typed on a phone is kept on the box", r == {"ok": True} and app.session.state["tacop"] == [None, "Zzyzx Gambit"], r)
check("Kill Team: the scoreboard page, the other phone, her line on the box and what she says aloud do not have it",
      "zzyzx" not in everyone.lower() and "Tac Op: chosen" in get("/state.json") and "Trevor has chosen a Tac Op" in app.toast and any("chosen a Tac Op" in x for x in app.voice.said), everyone[:400])
check("Kill Team: the owner's own phone has it", "Your Tac Op: Zzyzx Gambit (secret until you reveal it)" in json.loads(get("/phone.json?seat=1"))["lines"])
ph0 = json.loads(get("/phone.json?seat=0"))
check("Kill Team: the other phone has no button that touches it", "Reveal my Tac Op" not in ph0["actions"] and "Change my Tac Op" not in ph0["actions"] and "Record my Tac Op" in ph0["actions"])
ph1 = json.loads(get("/phone.json?seat=1"))
r = post("/do?seat=0&i=%d" % ph1["actions"].index("Reveal my Tac Op"), b"Reveal my Tac Op")
check("Kill Team: the other seat cannot reveal it", "error" in r and app.session.state["tac_shown"] == [False, False], r)
r = post("/do?seat=1&i=%d" % ph1["actions"].index("Reveal my Tac Op"), b"Reveal my Tac Op", dev=0)
r2 = post("/remind", {"seat": 1, "phase": "*", "text": "not mine to add"}, dev=0)
check("Kill Team: nor can the other phone reveal it, or add a reminder, by saying it is that seat",
      r == {"error": web.SEAT_TAKEN} and r2 == {"error": web.SEAT_TAKEN} and app.session.state["tac_shown"] == [False, False] and app.session.d["reminders"] == [], (r, r2))
# freeing the seats, on the box
from deepthought.screens.web_link import PhoneLink as _Link
def on_box(fn): return w.on_main(fn)
def box_tap(label): on_box(lambda: next(x for x in app.screen.widgets if x.label == label).action())
on_box(lambda: app.push(_Link(app)))
free = next(x for x in app.screen.widgets if x.label == "Free the seats")
check("the Phones screen has a Free the seats button, a full-size one, on the screen",
      free.rect.h >= 64 and free.rect.w >= 64 and free.rect.right <= 800 and free.rect.bottom <= 480 and free.rect.top >= 60
      and not any(free.rect.colliderect(x.rect) for x in app.screen.widgets if x is not free), free.rect)
box_tap("Free the seats")
check("it asks first, and the button's own press leaves the seats as they are", app.screen.title == "Free the seats?" and w.taken() == [0, 1], w.taken())
on_box(lambda: (app.gesture("press"), None)[1])
check("Leave them: nothing is freed", w.taken() == [0, 1] and "HTTP" not in get("/phone.json?seat=1", dev=1))
box_tap("Free the seats"); box_tap("Free the seats")
check("Free the seats: every seat is free, and a phone's old seat is no longer its own until it chooses again",
      w.taken() == [] and "HTTP 403" in get("/phone.json?seat=1", dev=1) and "Choose your seat first" in get("/phone.json?seat=1", dev=1) and "Every seat is free" in app.toast, w.taken())
check("the owner sits down again and has the Tac Op as before", "Zzyzx Gambit" in get("/phone.json?seat=1") and w.taken() == [1])
on_box(lambda: (app.pop(), None)[1])
path_was = app.session.path
on_box(lambda: (app.go_home(), app.resume_game(path_was), None)[2])
check("the same game left and resumed keeps its seats", w.taken() == [1] and "Zzyzx Gambit" in get("/phone.json?seat=1", dev=1))
with open(app.session.path, encoding="utf-8") as f: saved = json.load(f)
check("Kill Team: it is in the saved game, so a power cut does not lose it", saved["state"]["tacop"] == [None, "Zzyzx Gambit"])
r = post("/do?seat=1&i=%d" % ph1["actions"].index("Reveal my Tac Op"), b"Reveal my Tac Op")
check("Kill Team: its owner reveals it from the phone, and then the scoreboard and the other phone show it",
      r == {"ok": True} and "Tac Op: Zzyzx Gambit" in get("/state.json") and "Trevor's Tac Op: Zzyzx Gambit" in json.loads(get("/phone.json?seat=0"))["lines"] and "Zzyzx Gambit" in app.toast, app.toast)
app.go_home(); app.toast = None
app.start_game(app.plugins["risk"], ["Ethan", "Trevor", "Sam"], {"hints": "On"})
try:
    with urllib.request.urlopen(urllib.request.Request(base + "/phone.json?seat=1", headers={"Cookie": "dts1=café".encode("utf-8").decode("latin-1")}), timeout=5) as resp: odd = resp.read().decode()
except urllib.error.HTTPError as e: odd = "HTTP %s %s" % (e.code, e.read().decode())
check("a seat cookie of odd letters is refused in the ordinary way", "HTTP 403" in odd and "Choose your seat first" in odd, odd)
check("a new game starts with every seat free: last game's phone holds nothing until it chooses a seat",
      w.taken() == [] and "HTTP 403" in get("/phone.json?seat=1", dev=1) and "/play?seat=1" in get("/play", dev="nobody"))
check("the scoreboard page shows a row's detail when the game gives no line of its own", "r.sub||r.detail" in get("/"))
r = post("/do?seat=0&i=0", b"Next")
check("a game whose actions ask nothing works from a phone exactly as before", r == {"ok": True} and json.loads(get("/phone.json?seat=0"))["asks"] in ([None], []), r)
app.voice = old_voice; app.go_home(); app.toast = None

app.go_home(); app.session = None
check("between games a phone left open is told no game is being played, as before", json.loads(get("/phone.json?seat=0", dev=0)) == {"playing": False})
stop = True; w.stop()

# ---------------------------------------------------------------- the library after it has been let go
import sqlite3
db = os.environ["DT_CONTENT_DB"]
lib.close(); app.close_library()                        # every other holder lets go first
held = Library(); n_held = held.counts(); held.close()
check("closing the library leaves content.db whole, with nothing waiting beside it", n_held[0] > 0 and not os.path.exists(db + "-wal"), os.listdir(DATA))
told = []
a = ask.answer("What does the grobnar get for each continent it holds?", held, "risk", "Risk", llm=lambda sy, u: (told.append(u), "Three armies. I counted.")[1])
check("a library still held by a question when it was closed opens itself again: the answer rests on the page, not on nothing",
      a["source"] == "Made Up Rules, Armies" and "three armies for each continent" in told[0] and held.counts() == n_held, a)
ask.forget_ruling("risk", "What does the grobnar get for each continent it holds?")
held.close()
none = Library(os.path.join(DATA, "no-such.db"))
check("with no library file there is still nothing, and none is made", none.counts() == (0, 0) and none.search("grobnar") == [] and not os.path.exists(os.path.join(DATA, "no-such.db")))

# ---------------------------------------------------------------- whose ruling a DM-mode answer is
lib3 = Library()
q = "Does the grobnar keep its armies when the continent is lost?"
ask.answer(q, lib3, "dnd", dm=True, llm=lambda sy, u: "It does not. Do keep that to yourself.")
check("in DM mode with D&D on the table, a ruling is the DM's even when no campaign page was used: the question itself may give the plot away",
      [r["dm"] for r in ask.rulings() if r["q"] == q] == [True] and ask.find_ruling("dnd", q) is None and ask.find_ruling("dnd", q, dm=True) is not None, ask.rulings()[-1:])
ask.forget_ruling("dnd", q)
ask.answer(q, lib3, "risk", dm=True, llm=lambda sy, u: "It does not. The rules are plain.")
check("for any other game a ruling given while DM mode happens to be on is everyone's, unless a DM-only page was used",
      [r["dm"] for r in ask.rulings() if r["q"] == q] == [False] and ask.find_ruling("risk", q) is not None)
ask.forget_ruling("risk", q)
lib3.close()

# ---------------------------------------------------------------- a held library file is "busy"; a full card is not
check("only a locked or busy library counts as busy", dt_content.is_busy(sqlite3.OperationalError("database is locked")) and dt_content.is_busy(sqlite3.OperationalError("database table is locked: docs"))
      and not dt_content.is_busy(sqlite3.OperationalError("database or disk is full")) and not dt_content.is_busy(sqlite3.OperationalError("disk I/O error")))
open(os.path.join(src, "free", "risk", "Another.md"), "w", encoding="utf-8").write("# Fleets\n\nThe wumpus gets two fleets.\n")
real_add = dt_content.add_file
def add_failing(words):
    def add(con, path, *a, **k):
        if path.endswith("Another.md"): raise sqlite3.OperationalError(words)
        return real_add(con, path, *a, **k)
    return add
con = dt_content.connect(db)
dt_content.add_file = add_failing("database is locked")
rep = dict(dt_content.sync(con, src, log=lambda *a: None))
check("the loader reports a file it could not load because the library was held as BUSY", rep.get("free/risk/Another.md", "").startswith("BUSY: "), rep)
dt_content.add_file = add_failing("database or disk is full")
rep = dict(dt_content.sync(con, src, log=lambda *a: None))
check("and one it could not load for any other reason as FAILED, with the reason", rep.get("free/risk/Another.md") == "FAILED: database or disk is full", rep)
dt_content.add_file = real_add
con.close(); os.remove(os.path.join(src, "free", "risk", "Another.md"))

print("\n%d failed" % len(fails)); sys.exit(1 if fails else 0)
