"""The web pages the box serves on the home network (port 8080).

  /             the shared scoreboard (the Chromebook at the end of the table)
  /play         a player's own phone: pick a seat, then your own buttons
  /characters   make a D&D character or upload a fillable PDF sheet
  /library      upload your own rulebooks so Lookup can search them
  /games        add a board game to the box
  /rulings      every ruling the box has given
  /sounds       the DM's soundboard (your own audio files)

Built on Python's own http.server: no extra packages. Anything that touches
the game runs on the main loop through app.later(), never on a web thread.
The scoreboard is open to anyone on the home Wi-Fi: it only shows what is on
the table anyway. Every other page asks for the four-digit table code shown on
the box under Settings, Phones. The code scanned from the box's screen carries
the code with it. It keeps a guest's phone from changing things by accident;
it travels unencrypted, so it is not protection against someone determined.
"""
import hashlib
import hmac
import html
import json
import os
import re
import secrets
import socket
import sqlite3
import sys
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Server(ThreadingHTTPServer):
    """The default waiting line is five connections. On the Pi 2 a table of phones
    all refreshing at once overflowed it, and the extra ones were cut off."""
    request_queue_size = 128
    daemon_threads = True

from . import ask, paths, settings

sys.path.insert(0, paths.SOFTWARE)
import dt_characters  # noqa: E402
import dt_content  # noqa: E402

PORT = 8080
MAX_UPLOAD = 400 * 1024 * 1024
MAX_BOOK = 100 * 1024 * 1024                     # a book is read on the box itself, and the Pi 2 has 1 GB
BOOK_TOO_BIG = ("That file is larger than 100 MB, which is more than the box can read by itself. Put it in the "
                "content folder on the PC and build the library there: see LIBRARY.md, The folder way.")
UPLOAD_LOST = "The upload did not get through. Check this device is still on the Wi-Fi and the box is on, then try again."
BOOK_TYPES = (".pdf", ".epub", ".txt", ".md")
SOUND_TYPES = (".wav", ".ogg")
OPEN = ("index", "state_json", "enter")          # pages that never ask for the code
MAX_TRIES, LOCK_SECS = 5, 60
LOCKED_OUT = "Too many wrong codes. Wait a minute, then try again."
WRONG_CODE = "That is not the code. It is on the box: Settings, then Phones."
WHY = {"wait": LOCKED_OUT, "wrong": WRONG_CODE}       # what the code page says after a refused link
LIBRARY_BUSY = ("%s is on the box, but the library was busy with something else, so it cannot be searched yet. "
                "Wait a minute, then upload it again.")
_index_lock = threading.Lock()                        # one book is read into the library at a time
SEAT_TAKEN = "That seat is in use on another phone. On the box: Settings, Phones, Free the seats."
SEAT_FIRST = "Choose your seat first: open My seat on this phone."


def table_code():
    """The four-digit code for the web pages. Made up the first time it is needed."""
    code = settings.get("web_code")
    if not code:
        code = settings.put("web_code", "%04d" % secrets.randbelow(10000))
    return str(code)


def new_table_code():
    """A fresh code. Every phone has to enter it again."""
    old = table_code()
    while True:
        code = "%04d" % secrets.randbelow(10000)
        if code != old:
            return settings.put("web_code", code)


def token():
    """What a phone keeps in a cookie once it has given the right code."""
    key = settings.get("web_key") or settings.put("web_key", secrets.token_hex(16))
    return hmac.new(key.encode(), table_code().encode(), hashlib.sha256).hexdigest()[:32]

CSS = """body{margin:0;background:#0B0F14;color:#EAF0F6;font-family:system-ui,sans-serif;font-size:18px}
main{max-width:760px;margin:0 auto;padding:16px}h1{font-size:26px;margin:8px 0 16px}h2{font-size:20px;margin:24px 0 8px}
a{color:#6CB6FF}nav{background:#151C26;border-bottom:1px solid #2F3B4D;padding:12px 16px}nav a{margin-right:16px;text-decoration:none}
.card{background:#151C26;border:1px solid #2F3B4D;border-radius:14px;padding:14px 16px;margin:10px 0}
button,.btn{background:#1D2633;color:#EAF0F6;border:1px solid #2F3B4D;border-radius:12px;font-size:20px;padding:14px 18px;
margin:6px 6px 6px 0;min-height:56px;cursor:pointer}button.main{background:#EAF0F6;color:#0B0F14}
input,select,textarea{background:#0B0F14;color:#EAF0F6;border:1px solid #2F3B4D;border-radius:10px;font-size:18px;padding:10px;
margin:4px 0 12px;width:100%;box-sizing:border-box}label{color:#A9B8CA;display:block}
.dim{color:#A9B8CA}.big{font-size:64px;font-weight:700;line-height:1}.row{display:flex;justify-content:space-between;align-items:center}
.pill{background:#EAF0F6;color:#0B0F14;border-radius:999px;padding:2px 12px;font-size:16px;font-weight:600}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}#msg{color:#FFA64D;min-height:24px}"""
NAV = [("/", "Scoreboard"), ("/play", "My seat"), ("/characters", "Characters"), ("/library", "Library"),
       ("/games", "Games"), ("/rulings", "Rulings"), ("/sounds", "Sounds")]


LIST_JS = r'''async function make(){const d={};['name','player','cls','species','background','edition','str','dex','con','int','wis','cha']
.forEach(k=>d[k]=document.getElementById(k).value);show(await (await fetch('/characters/new',{method:'POST',body:JSON.stringify(d)})).json())}
async function up(){const f=document.getElementById('pdf').files[0];if(!f)return;
show(await (await fetch('/characters/upload?name='+encodeURIComponent(f.name),{method:'POST',body:f})).json())}
function shrink(file){return new Promise((ok,no)=>{const img=new Image();img.onload=()=>{const k=Math.min(1,1600/Math.max(img.width,img.height));
const c=document.createElement('canvas');c.width=Math.round(img.width*k);c.height=Math.round(img.height*k);
c.getContext('2d').drawImage(img,0,0,c.width,c.height);c.toBlob(b=>b?ok(b):no(),'image/jpeg',0.85)};img.onerror=no;img.src=URL.createObjectURL(file)})}
async function photo(){const f=document.getElementById('photo').files[0];if(!f)return;const m=document.getElementById('msg');
m.textContent='Reading the photo. This takes up to a minute; keep this page open.';let b;
try{b=await shrink(f)}catch(e){m.textContent='This phone could not open that picture. Try a JPEG.';return}
const r=await (await fetch('/characters/photo',{method:'POST',headers:{'Content-Type':'image/jpeg'},body:b})).json();
if(r.ok&&r.slug){m.innerHTML=r.ok+(r.todo&&r.todo.length?'<ul>'+r.todo.map(t=>'<li>'+t+'</li>').join('')+'</ul>':'')+
'<a class=btn href="/characters/edit?name='+r.slug+'">Check it against the paper</a>'}else show(r)}
function show(r){const m=document.getElementById('msg');if(r.error){m.textContent=r.error;return}
m.innerHTML=(r.ok||'')+(r.todo?'<ul>'+r.todo.map(t=>'<li>'+t+'</li>').join('')+'</ul>':'');
if(r.ok)setTimeout(()=>location.reload(),4000)}'''

FORM_JS = r'''const was=%s,old=%s;const $=i=>document.getElementById(i);
const plain=['name','player','edition','species','background','classlevel','hit_die','str','dex','con','int','wis','cha','hp_max','hp_current','hp_temp','ac','speed','cp','sp','ep','gp','pp','equipment','spells','features','notes'];
if(old){plain.forEach(k=>{if(old[k]!==null&&old[k]!==undefined)$(k).value=old[k]});
['saves','skills','expertise'].forEach(g=>(old[g]||[]).forEach(v=>{const b=document.querySelector('input[data-g="'+g+'"][value="'+v+'"]');if(b)b.checked=true}))}
function mod(){['str','dex','con','int','wis','cha'].forEach(a=>{const v=parseInt($(a).value);$('m_'+a).textContent=isNaN(v)?'':((v>=10?'+':'')+Math.floor((v-10)/2))})}
document.querySelectorAll('.grid input').forEach(i=>i.addEventListener('input',mod));mod();
async function save(){const d={};plain.forEach(k=>d[k]=$(k).value);
['saves','skills','expertise'].forEach(g=>d[g]=[...document.querySelectorAll('input[data-g="'+g+'"]:checked')].map(b=>b.value));
const r=await (await fetch('/characters/save?was='+encodeURIComponent(was),{method:'POST',body:JSON.stringify(d)})).json();
if(r.error){$('msg').textContent=r.error;return}
$('msg').innerHTML=(r.ok||'')+(r.todo&&r.todo.length?'<ul>'+r.todo.map(t=>'<li>'+t+'</li>').join('')+'</ul>':'');
if(r.ok){$('msg').scrollIntoView();if(r.slug&&r.slug!==was)setTimeout(()=>location.href='/characters/edit?name='+r.slug,2500)}}'''


def page(title, body, script=""):
    nav = "".join('<a href="%s">%s</a>' % (u, n) for u, n in NAV)
    return ("<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,"
            "initial-scale=1'><title>%s · Deep Thought</title><style>%s</style></head><body><nav>%s</nav><main>"
            "<h1>%s</h1>%s</main><script>%s</script></body></html>" % (html.escape(title), CSS, nav, html.escape(title),
                                                                         body, script)).encode("utf-8")


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40]


def safe_name(name, allowed):
    """A file name with no folders in it and an allowed ending, or None."""
    name = os.path.basename(name.replace("\\", "/")).strip()
    name = re.sub(r"[^A-Za-z0-9 ._()'&-]", "", name)[:120].strip(" .")
    return name if name and os.path.splitext(name)[1].lower() in allowed else None


def local_ip():
    """This machine's address on the home network. Sends nothing."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


# ---------------------------------------------------------------- what the pages show
def state(app):
    """The shared scoreboard. Only what every player may see."""
    s = app.session
    said = "" if getattr(app, "toast_private", False) else app.toast or ""      # a line for the DM's eyes stays on the box
    if not s:
        return {"playing": False, "said": said, "last": app.last_game or ""}
    board = s.game.scoreboard(s)
    left, title = s.game.strip(s)
    return {"playing": True, "game": s.game.name, "left": left, "title": title, "active": s.game.active(s.state),
            "players": s.players, "rows": board.get("rows", []), "note": board.get("note", ""), "said": said}


def phone(app, seat):
    s = app.session
    if not s or not 0 <= seat < len(s.players):
        return {"playing": False}
    view = s.game.phone(s, seat)
    left, title = s.game.strip(s)
    return {"playing": True, "name": s.players[seat], "left": left, "title": title,
            "yours": s.game.active(s.state) == seat, "lines": view.get("lines", []),
            "actions": [a["label"] for a in view.get("actions", [])], "phases": s.game.phases(),
            # one entry per action: None, or what to ask the player before sending it
            "asks": [({"ask": str(a["ask"]), "choices": [str(c) for c in a.get("choices", [])][:60],
                       "max": int(a.get("max", ASK_MAX))} if a.get("ask") else None) for a in view.get("actions", [])],
            "reminders": [r["text"] for r in s.d["reminders"] if r["player"] == seat]}


ASK_MAX = 40          # letters in a value a player types or picks for an action that asks for one


def printable(text):
    """What a player typed, as letters that can be shown and saved: anything
    that is not a string is nothing, and characters with no shape (a NUL, an
    escape, half of a broken emoji) become spaces."""
    if not isinstance(text, str):
        return ""
    return "".join(ch if ch.isprintable() else " " for ch in text)


def phone_do(app, seat, index, label, text=None):
    """Run one of a player's own actions. Checked again here, on the main loop,
    so a stale phone cannot do something that is no longer allowed.
    An action with "ask" needs a value (typed or picked on the phone): it is
    tidied, cut to the action's "max" letters and added to the event as "text".
    The game decides whether it is acceptable; if it refuses, the phone is told why."""
    s = app.session
    if not s or not 0 <= seat < len(s.players):
        return "No game is being played."
    actions = s.game.phone(s, seat).get("actions", [])
    if not 0 <= index < len(actions) or actions[index]["label"] != label:
        # The list may have moved while the player was choosing (a turn passed, a button
        # came or went). If exactly one action still has that label, it is the one meant.
        same = [k for k, a in enumerate(actions) if a["label"] == label]
        if len(same) != 1:
            return "That is no longer possible. The screen has moved on."
        index = same[0]
    ev = actions[index]["ev"]
    if actions[index].get("ask"):
        text = " ".join(printable(text).split())[:int(actions[index].get("max", ASK_MAX))].strip()
        if not text:
            return "That needs a name."
        ev = dict(ev, text=text)
        n = len(s.log)
        app.game_event(ev)
        if len(s.log) == n and not s.finished:
            return app.toast or "That was refused."
        return ""
    app.game_event(ev)
    return ""


class Web:
    def __init__(self, app, port=PORT, lock=None):
        self.app, self.port = app, port
        self.lock = settings.get("web_lock") if lock is None else lock
        self.tries, self.locked_until = 0, 0.0
        self.code_lock = threading.Lock()             # one guess at the table code at a time
        self.httpd = None
        self._url = None
        self.seat_lock = threading.Lock()
        self.seats, self.seats_for = {}, None         # seat number -> the cookie its phone holds, for one game

    @property
    def url(self):
        """The address to type on a phone. Worked out each time it is asked
        for, so it is right even if the Wi-Fi came up after the program did."""
        if self._url is not None:
            return self._url
        return "http://%s:%d" % (local_ip(), self.port) if self.httpd else ""

    @url.setter
    def url(self, value):
        self._url = value

    def start(self):
        web = self

        class Handler(BaseHTTPRequestHandler):
            timeout = 30                              # a phone that goes quiet does not hold a thread for ever

            def log_message(self, *a):
                pass

            def do_GET(self):
                web.handle(self, "GET")

            def do_POST(self):
                web.handle(self, "POST")

        try:
            self.httpd = Server(("0.0.0.0", self.port), Handler)
        except OSError:
            return False                              # port in use: the box works without the pages
        self.port = self.httpd.server_address[1]
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        return True

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()

    def on_main(self, fn, wait=3.0):
        """Run fn on the main loop and wait for its answer."""
        done, box = threading.Event(), {}

        def job():
            try:
                box["r"] = fn()
            except Exception as e:
                box["r"] = "Error: %s" % e
            done.set()
        self.app.later(job)
        done.wait(wait)
        return box.get("r", "The box did not answer in time.")

    # ---- plumbing
    def send(self, h, body, kind="text/html; charset=utf-8", code=200):
        if isinstance(body, (dict, list)):
            body, kind = json.dumps(body).encode("utf-8"), "application/json"
        elif isinstance(body, str):
            body = body.encode("utf-8")
        h.send_response(code)
        h.send_header("Content-Type", kind)
        h.send_header("Content-Length", str(len(body)))
        h.send_header("Cache-Control", "no-store")
        for name, value in getattr(h, "extra", ()):
            h.send_header(name, value)
        h.end_headers()
        h.wfile.write(body)

    def body(self, h, limit=1 << 20):
        n = int(h.headers.get("Content-Length") or 0)
        if not 0 <= n <= limit:                       # a negative length would read until the phone hangs up
            raise ValueError("That is too large.")
        return h.rfile.read(n)

    def save_upload(self, h, dest, limit=MAX_UPLOAD, too_big=None):
        """Stream a raw upload to a file, so a big PDF never sits in memory."""
        n = int(h.headers.get("Content-Length") or 0)
        if n > limit and too_big:
            raise ValueError(too_big)
        if not 0 < n <= limit:
            raise ValueError("The file is empty or larger than %d MB." % (limit >> 20))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        part = "%s.%s.part" % (dest, secrets.token_hex(4))    # two uploads of one name do not share it
        try:
            with open(part, "wb") as f:
                left = n
                while left > 0:
                    block = h.rfile.read(min(1 << 20, left))
                    if not block:
                        raise ValueError("The upload stopped part way.")
                    f.write(block)
                    left -= len(block)
            os.replace(part, dest)
        finally:
            if os.path.isfile(part):                  # stopped part way: leave nothing behind
                os.remove(part)

    def handle(self, h, method):
        url = urllib.parse.urlparse(h.path)
        q = {k: v[0] for k, v in urllib.parse.parse_qs(url.query).items()}
        route = getattr(self, "%s_%s" % (method.lower(), url.path.strip("/").replace("/", "_").replace(".", "_") or "index"), None)
        h.extra = []
        try:
            if not route:
                return self.send(h, page("Not found", "<p>There is nothing at this address.</p>"), code=404)
            if self.lock and route.__name__.split("_", 1)[1] not in OPEN and not self.allowed(h, q):
                if method == "GET":
                    why = getattr(h, "why", "")       # a code in the link was refused: say so on the code page
                    h.extra.append(("Location", "/enter?next=" + urllib.parse.quote(url.path) + ("&why=" + why if why else "")))
                    return self.send(h, "", code=303)
                return self.send(h, {"error": "Enter the table code first: open /enter on this phone."}, code=401)
            route(h, q)
        except ValueError as e:
            self.send(h, {"error": str(e)}, code=400)
        except Exception as e:                        # a bad request must never take the box down
            self.send(h, {"error": "Something went wrong: %s" % e}, code=500)

    # ---- seats: one phone to a seat
    # The table code lets a phone in; it does not say whose phone it is. The first
    # phone to open a seat in a game is given a cookie for that seat, and from then
    # on only that phone may read the seat's page or press its buttons. The claims
    # live here, not on disk: a new game, or the box starting again, frees every seat.
    def _claims(self):
        """The claims for the game on the table (call with seat_lock held)."""
        s = self.app.session
        key = (s.path or id(s)) if s else None
        if key != self.seats_for:
            self.seats, self.seats_for = {}, key
        return self.seats

    @staticmethod
    def _seat_cookie(h, seat):
        for part in (h.headers.get("Cookie") or "").split(";"):
            name, _, value = part.strip().partition("=")
            if name == "dts%d" % seat:
                return value
        return ""

    def holds(self, h, seat):
        """Is this the phone that sits in that seat?"""
        with self.seat_lock:
            want = self._claims().get(seat)
            return bool(want) and hmac.compare_digest(self._seat_cookie(h, seat).encode("utf-8", "replace"), want.encode())

    def claim(self, h, seat):
        """Give this phone the seat if nobody has it. True if it now holds it."""
        with self.seat_lock:
            seats = self._claims()
            if seat in seats:
                return hmac.compare_digest(self._seat_cookie(h, seat).encode("utf-8", "replace"), seats[seat].encode())
            seats[seat] = secrets.token_hex(16)
            h.extra.append(("Set-Cookie", "dts%d=%s; Path=/; Max-Age=31536000; HttpOnly; SameSite=Lax" % (seat, seats[seat])))
            return True

    def taken(self):
        """Seat numbers that a phone holds in the game on the table."""
        with self.seat_lock:
            return sorted(self._claims())

    def free_seats(self):
        """Every phone must choose its seat again (the button on the box's Phones screen)."""
        with self.seat_lock:
            self._claims().clear()

    def seat_refusal(self, h, seat):
        """Empty if this phone holds the seat, otherwise what to tell it."""
        if self.holds(h, seat):
            return ""
        return SEAT_TAKEN if seat in self.taken() else SEAT_FIRST

    # ---- the table code
    def allowed(self, h, q):
        """Has this phone given the code? A code in the address (from the QR on
        the box) counts, and leaves the cookie so it is only needed once."""
        want = token()
        for part in (h.headers.get("Cookie") or "").split(";"):
            name, _, value = part.strip().partition("=")
            if name == "dt" and hmac.compare_digest(value, want):
                return True
        if "code" not in q:
            return False
        said = self.try_code(h, q["code"])
        h.why = "" if not said else "wait" if said == LOCKED_OUT else "wrong"
        return said == ""

    def try_code(self, h, code):
        """Empty string if the code is right, otherwise what to tell the person."""
        with self.code_lock:                          # so many phones guessing at once still get five tries
            now = time.monotonic()
            if now < self.locked_until:
                return LOCKED_OUT
            if hmac.compare_digest("".join(str(code).split()).encode(), table_code().encode()):
                self.tries = 0
                h.extra.append(("Set-Cookie", "dt=%s; Path=/; Max-Age=31536000; HttpOnly; SameSite=Lax" % token()))
                return ""
            self.tries += 1
            if self.tries >= MAX_TRIES:
                self.tries, self.locked_until = 0, now + LOCK_SECS
            return WRONG_CODE

    def get_enter(self, h, q, said=""):
        said = said or WHY.get(q.get("why", ""), "")
        nxt = q.get("next", "/play")
        nxt = nxt if re.fullmatch(r"/[a-z]*", nxt) else "/play"
        body = ("<p>These pages can change things on the box, so they ask for the table code once. "
                "It is on the box: Settings, then Phones.</p><form method=post action='/enter?next=%s'>"
                "<label>Table code</label><input name=code inputmode=numeric autocomplete=off maxlength=8 autofocus>"
                "<button class=main>Enter</button></form><div id=msg>%s</div>") % (nxt, html.escape(said))
        self.send(h, page("Table code", body))

    def post_enter(self, h, q):
        form = urllib.parse.parse_qs(self.body(h).decode("utf-8", "replace"))
        said = self.try_code(h, (form.get("code") or [""])[0])
        if said:
            return self.get_enter(h, q, said)
        nxt = q.get("next", "/play")
        h.extra.append(("Location", nxt if re.fullmatch(r"/[a-z]*", nxt) else "/play"))
        self.send(h, "", code=303)

    # ---- scoreboard
    def get_index(self, h, q):
        body = "<div id=board class=dim>Waiting for the box…</div><p id=said class=dim></p>"
        script = """async function tick(){try{const s=await (await fetch('/state.json')).json();const b=document.getElementById('board');
if(!s.playing){b.innerHTML='<p>No game is being played.</p><p>'+esc(s.last)+'</p>';}else{let o='<p class=dim>'+esc(s.left)+' · '+esc(s.title)+'</p>';
s.rows.forEach((r,i)=>{o+='<div class="card row"><div><div>'+esc(r.name)+(i===s.active?' <span class=pill>turn</span>':'')+(r.out?' <span class=dim>out</span>':'')+
'</div><div class=dim>'+esc(r.sub||r.detail||'')+'</div></div><div class=big>'+esc(String(r.value??''))+'</div></div>';});
o+='<p class=dim>'+esc(s.note)+'</p>';b.innerHTML=o;}document.getElementById('said').textContent=s.said;}catch(e){}}
function esc(t){const d=document.createElement('div');d.textContent=t??'';return d.innerHTML}tick();setInterval(tick,1000);"""
        self.send(h, page("Scoreboard", body, script))

    def get_state_json(self, h, q):
        self.send(h, self.on_main(lambda: state(self.app)))

    # ---- a player's phone
    def get_play(self, h, q):
        s = self.app.session
        if not s:
            return self.send(h, page("My seat", "<p>No game is being played. Start one on the box, then reload.</p>"))
        players = list(s.players)
        seat = int(q["seat"]) if re.fullmatch(r"[0-9]{1,3}", q.get("seat", "")) else -1
        if not 0 <= seat < len(players):              # no seat chosen yet: the names, and which are already taken
            taken, links = self.taken(), ""
            for i, n in enumerate(players):
                if i in taken and not self.holds(h, i):
                    links += "<span class=btn style='opacity:.5'>%s (in use)</span> " % html.escape(n)
                else:
                    links += '<a class=btn href="/play?seat=%d">%s</a> ' % (i, html.escape(n))
            return self.send(h, page("Who are you?", "<p>" + links + "</p><p class=dim>One phone to a seat. A seat marked "
                                     "in use is freed on the box: Settings, Phones, Free the seats.</p>"))
        if not self.claim(h, seat):
            return self.send(h, page("Seat in use", "<p>%s</p><p><a class=btn href='/play'>Back</a></p>" % html.escape(SEAT_TAKEN)))
        body = ("<div id=view class=dim>Waiting…</div><div id=msg></div><div id=ask></div><h2>Don't forget…</h2>"
                "<p class=dim>Type a reminder once. The box says it at the right moment.</p><select id=phase></select>"
                "<input id=text maxlength=120 placeholder='e.g. roll for my aura'><button onclick=remind()>Add reminder</button>"
                "<div id=rem class=dim></div>")
        script = """const seat=%d;let filled=false,cur=null;
async function tick(){try{const s=await (await fetch('/phone.json?seat='+seat)).json();cur=s;const v=document.getElementById('view');
if(s.error){v.innerHTML='<p>'+esc(s.error)+'</p><p><a class=btn href="/play">Choose a seat</a></p>';return}
if(!s.playing){v.innerHTML='<p>No game is being played.</p>';return}
let o='<p class=dim>'+esc(s.left)+' · '+esc(s.title)+'</p><h2>'+esc(s.name)+(s.yours?' <span class=pill>your turn</span>':'')+'</h2>';
s.lines.forEach(l=>o+='<div class=card>'+esc(l)+'</div>');
s.actions.forEach((a,i)=>o+='<button class="'+(i===0?'main':'')+'" onclick="act('+i+',this.textContent)">'+esc(a)+'</button>');
v.innerHTML=o;if(!filled){const p=document.getElementById('phase');p.innerHTML='<option value="*">Every phase</option>'+
s.phases.map(x=>'<option value="'+esc(x[0])+'">'+esc(x[1])+'</option>').join('');filled=true}
document.getElementById('rem').innerHTML=s.reminders.map(r=>'<div class=card>'+esc(r)+'</div>').join('');}catch(e){}}
function act(i,label){const a=cur&&cur.asks?cur.asks[i]:null;if(a){openAsk(i,label,a)}else{send(i,label,null)}}
async function send(i,label,text){const r=await (await fetch('/do?seat='+seat+'&i='+i,{method:'POST',
body:text===null?label:JSON.stringify({label:label,text:text})})).json();
document.getElementById('msg').textContent=r.error||'';if(!r.error)document.getElementById('ask').innerHTML='';tick()}
function openAsk(i,label,a){const b=document.getElementById('ask');b.innerHTML='';
const h=document.createElement('h2');h.textContent=a.ask;b.appendChild(h);
a.choices.forEach(c=>{const x=document.createElement('button');x.textContent=c;x.onclick=()=>send(i,label,c);b.appendChild(x)});
const t=document.createElement('input');t.maxLength=a.max;t.placeholder=a.choices.length?'or type it':'type it here';b.appendChild(t);
const ok=document.createElement('button');ok.className='main';ok.textContent='Use what I typed';
ok.onclick=()=>{if(t.value.trim())send(i,label,t.value)};b.appendChild(ok);
const no=document.createElement('button');no.textContent='Cancel';no.onclick=()=>{b.innerHTML=''};b.appendChild(no);b.scrollIntoView()}
async function remind(){const t=document.getElementById('text');if(!t.value.trim())return;
await fetch('/remind',{method:'POST',body:JSON.stringify({seat:seat,phase:document.getElementById('phase').value,text:t.value})});t.value='';tick()}
function esc(t){const d=document.createElement('div');d.textContent=t??'';return d.innerHTML}tick();setInterval(tick,1500);""" % seat
        self.send(h, page("My seat", body, script))

    def seat_of(self, value):
        """A seat number from a request, or -1."""
        return int(value) if isinstance(value, int) and not isinstance(value, bool) else (
            int(value) if isinstance(value, str) and re.fullmatch(r"[0-9]{1,3}", value) else -1)

    def get_phone_json(self, h, q):
        seat = self.seat_of(q.get("seat"))
        if not self.app.session:                      # between games a phone left open just waits
            return self.send(h, {"playing": False})
        why = self.seat_refusal(h, seat)
        if why:                                       # not this phone's seat: nothing of the seat's is sent
            return self.send(h, {"playing": False, "error": why}, code=403)
        self.send(h, self.on_main(lambda: phone(self.app, seat)))

    def post_do(self, h, q):
        label, text = self.body(h).decode("utf-8", "replace"), None
        if label.startswith("{"):                 # an action that asks for a value: {"label": ..., "text": ...}
            try:
                d = json.loads(label)
                label, text = str(d.get("label", "")), d.get("text")
                text = text if isinstance(text, str) else ""       # null, a number, a list: not a typed value
            except (ValueError, AttributeError, RecursionError):
                pass
        seat = self.seat_of(q.get("seat"))
        why = self.seat_refusal(h, seat)
        if why:
            return self.send(h, {"error": why}, code=403)
        index = int(q["i"]) if re.fullmatch(r"[0-9]{1,4}", q.get("i", "")) else -1
        err = self.on_main(lambda: phone_do(self.app, seat, index, label, text))
        self.send(h, {"error": err} if err else {"ok": True})

    def post_remind(self, h, q):
        d = json.loads(self.body(h).decode("utf-8"))
        if not isinstance(d, dict):
            raise ValueError("That is not a reminder.")
        seat = self.seat_of(d.get("seat"))
        why = self.seat_refusal(h, seat)
        if why:
            return self.send(h, {"error": why}, code=403)

        def add():
            s = self.app.session
            if s and 0 <= seat < len(s.players):
                s.add_reminder(seat, str(d.get("phase", "*")), printable(d.get("text")))
            return True
        self.on_main(add)
        self.send(h, {"ok": True})

    # ---- D&D characters
    def get_characters(self, h, q):
        folder, cards = paths.data("characters"), ""
        for name in sorted(os.listdir(folder)):
            if name.endswith(".json"):
                try:
                    c = dt_characters.load(os.path.join(folder, name))
                    line = dt_characters.show(c).split("\n")[0] if not any(
                        v is None for v in c["abilities"].values()) else c.get("name", name)
                    problems = dt_characters.check(c)
                    cards += "<div class='card row'><div>%s<div class=dim>%s</div></div><a class=btn href='/characters/edit?name=%s'>Edit</a></div>" % (
                        html.escape(line), html.escape("%d things to check" % len(problems) if problems else "Ready"),
                        name[:-5])
                except Exception:
                    cards += "<div class=card>%s <span class=dim>(could not be read)</span></div>" % html.escape(name)
        classes = "".join("<option>%s</option>" % c.title() for c in sorted(dt_characters.HIT_DIE))
        abil = "".join("<div><label>%s</label><input id=%s type=number min=1 max=30 value=10></div>" % (
            dt_characters.ABILITY_NAMES[a], a) for a in dt_characters.ABILITIES)
        body = ("%s<h2>Type in a whole sheet</h2><p class=dim>For a character you already have on paper: every box, "
                "at any level.</p><a class=btn href='/characters/edit'>Type in a sheet</a>"
                "<h2>Photo of a paper sheet</h2><p class=dim>Take a clear photo of the front of the sheet. The photo is "
                "sent to the cloud to be read, then you check every number against the paper. Needs the Claude key and "
                "the cloud switched on.</p><input type=file id=photo accept='image/*'><button onclick=photo()>Read photo</button>"
                "<h2>Make a new level 1 character</h2><label>Character name</label><input id=name><label>Player</label><input id=player>"
                "<label>Class</label><select id=cls>%s</select><label>Species</label><input id=species>"
                "<label>Background</label><input id=background><label>Rules</label><select id=edition><option>2024</option>"
                "<option>2014</option></select><div class=grid>%s</div><button class=main onclick=make()>Create</button>"
                "<h2>Upload a fillable PDF sheet</h2><p class=dim>The official form-fillable sheet, with the boxes typed in. "
                "A scan or photo will not work here.</p><input type=file id=pdf accept='.pdf'><button onclick=up()>Upload</button>"
                "<div id=msg></div>") % (cards or "<p class=dim>No characters yet.</p>", classes, abil)
        script = LIST_JS
        self.send(h, page("Characters", body, script))

    def post_characters_new(self, h, q):
        d = json.loads(self.body(h).decode("utf-8"))
        name = " ".join(str(d.get("name", "")).split())[:40]
        if not name:
            raise ValueError("The character needs a name.")
        abilities = {a: int(d.get(a) or 10) for a in dt_characters.ABILITIES}
        if any(not 1 <= v <= 30 for v in abilities.values()):
            raise ValueError("Ability scores run from 1 to 30.")
        c = dt_characters.new_character(name, str(d.get("player", ""))[:40], str(d.get("cls", "Fighter")), abilities,
                                        species=str(d.get("species", ""))[:40], background=str(d.get("background", ""))[:40],
                                        edition=str(d.get("edition", "2024")))
        self.store_character(c)                       # never over a character already called that
        self.send(h, {"ok": "%s is saved. Still to choose, from your own book:" % html.escape(name),
                      "todo": [html.escape(t) for t in dt_characters.creation_todo(c)]})

    def character_path(self, name):
        """The saved file for a character named in an address, or None. Never outside the folder."""
        name = dt_characters.slug(str(name or ""))
        path = os.path.join(paths.data("characters"), name + ".json")
        return path if os.path.isfile(path) else None

    def get_characters_edit(self, h, q):
        path = self.character_path(q.get("name")) if q.get("name") else None
        if q.get("name") and not path:
            return self.send(h, page("Not found", "<p>There is no character called that.</p>"), code=404)
        old = dt_characters.to_form(dt_characters.load(path)) if path else None
        box = lambda key, label, kind="text", extra="": "<div><label>%s</label><input id=%s type=%s %s></div>" % (label, key, kind, extra)
        abil = "".join("<div><label>%s <span id=m_%s class=pill></span></label><input id=%s type=number min=1 max=30></div>" % (
            dt_characters.ABILITY_NAMES[a], a, a) for a in dt_characters.ABILITIES)
        tick = lambda group, value, label: ("<label><input type=checkbox data-g=%s value='%s' style='width:auto'> %s</label>" % (
            group, value, html.escape(label)))
        saves = "".join(tick("saves", a, dt_characters.ABILITY_NAMES[a]) for a in dt_characters.ABILITIES)
        skills = "".join(tick("skills", k, "%s (%s)" % (k.capitalize(), dt_characters.SKILLS[k].upper()))
                         for k in sorted(dt_characters.SKILLS))
        expert = "".join(tick("expertise", k, k.capitalize()) for k in sorted(dt_characters.SKILLS))
        coins = "".join(box(k, k.upper(), "number", "min=0 value=0") for k in ("cp", "sp", "ep", "gp", "pp"))
        body = ("<p class=dim>Copy your sheet into these boxes. I work out modifiers, proficiency bonus and spell slots; "
                "you tell me what is written on the paper.</p>"
                + box("name", "Character name", extra="maxlength=40") + box("player", "Player", extra="maxlength=40")
                + box("classlevel", "Class and level, like Fighter 3 or Fighter 3 / Rogue 2. Subclass in brackets: Wizard (Evoker) 5")
                + box("hit_die", "Hit die, only if I do not know the class (6, 8, 10 or 12)", "number")
                + box("species", "Species", extra="maxlength=40") + box("background", "Background", extra="maxlength=40")
                + "<label>Rules</label><select id=edition><option>2024</option><option>2014</option></select>"
                "<h2>Ability scores</h2><div class=grid>" + abil + "</div>"
                "<h2>Hit points and armour</h2><div class=grid>" + box("hp_max", "Hit point maximum", "number")
                + box("hp_current", "Current", "number") + box("hp_temp", "Temporary", "number", "value=0")
                + box("ac", "Armour Class", "number") + box("speed", "Speed", "number", "value=30") + "</div>"
                "<h2>Saving throws you are proficient in</h2><p class=dim>Tick none and I use the usual two for the class.</p>" + saves
                + "<h2>Skills you are proficient in</h2>" + skills
                + "<details><summary>Expertise (tick only skills ticked above)</summary>" + expert + "</details>"
                "<h2>Coins</h2><div class=grid>" + coins + "</div>"
                "<h2>Gear</h2><label>One thing to a line. A count first if there are several: 2 x Dagger</label>"
                "<textarea id=equipment rows=6></textarea>"
                "<h2>Spells</h2><label>Names only, one to a line</label><textarea id=spells rows=4></textarea>"
                "<h2>Features and traits</h2><label>Names only, one to a line</label><textarea id=features rows=4></textarea>"
                "<h2>Notes</h2><textarea id=notes rows=4></textarea>"
                "<button class=main onclick=save()>Save</button><div id=msg></div>")
        blob = lambda v: json.dumps(v).replace("</", "<\\/")
        slug_was = os.path.basename(path)[:-5] if path else ""
        self.send(h, page("Edit " + old["name"] if old else "Type in a sheet", body, FORM_JS % (blob(slug_was), blob(old))))

    def store_character(self, c, was=None):
        """Save a character from the form or a photo. Refuses to write over a
        different character that happens to share the name."""
        folder = paths.data("characters")
        new = os.path.join(folder, dt_characters.slug(c["name"]) + ".json")
        if os.path.isfile(new) and (not was or os.path.abspath(new) != os.path.abspath(was)):
            raise ValueError("There is already a character called that. Open it from the list and edit it instead.")
        dt_characters.save(c, folder)
        if was and os.path.abspath(new) != os.path.abspath(was):
            os.remove(was)                            # the character was renamed
        return os.path.basename(new)[:-5]

    def post_characters_save(self, h, q):
        d = json.loads(self.body(h).decode("utf-8"))
        if not isinstance(d, dict):
            raise ValueError("That is not a character sheet.")
        was = self.character_path(q.get("was")) if q.get("was") else None
        if q.get("was") and not was:
            raise ValueError("That character is no longer on the box. Go back to the list.")
        if not d.get("saves"):
            d.pop("saves", None)                      # none ticked: use the class's usual two
        c, problems = dt_characters.from_form(d, dt_characters.load(was) if was else None)
        slug_now = self.store_character(c, was)
        self.send(h, {"ok": "%s is saved.%s" % (html.escape(c["name"]), " Things to check:" if problems else ""),
                      "todo": [html.escape(p) for p in problems], "slug": slug_now})

    def post_characters_photo(self, h, q):
        from . import voice as voice_mod
        v = self.app.voice
        if not v or not v.can_answer():
            raise ValueError("Reading a photo needs the cloud, and it is off or has no key. Type the sheet in instead.")
        kind = (h.headers.get("Content-Type") or "image/jpeg").split(";")[0].strip().lower()
        image = self.body(h, limit=8 << 20)
        if len(image) < 1000:
            raise ValueError("That photo is empty.")
        try:
            d = voice_mod.read_sheet_photo(v.cfg, image, kind)
        except RuntimeError as e:
            raise ValueError(str(e))
        if not d.get("saves"):
            d.pop("saves", None)
        try:
            c, problems = dt_characters.from_form(d)
        except ValueError as e:
            raise ValueError("I could not read enough of that photo. %s Or type the sheet in." % e)
        dt_characters.log(c, "Read from a photo of a paper sheet")
        slug_now = self.store_character(c)
        self.send(h, {"ok": "%s is saved, as I read it. A photo is easy to misread, so check every number." % html.escape(c["name"]),
                      "todo": [html.escape(p) for p in problems], "slug": slug_now})

    def post_characters_upload(self, h, q):
        if not safe_name(q.get("name", ""), (".pdf",)):
            raise ValueError("Upload a PDF file.")
        tmp = os.path.join(paths.data("uploads"), "sheet-%s.pdf" % secrets.token_hex(4))
        self.save_upload(h, tmp, MAX_BOOK)
        try:
            c, warnings, unused = dt_characters.import_pdf_fields(tmp)
        except ValueError as e:
            raise ValueError(str(e))
        finally:
            if os.path.isfile(tmp):
                os.remove(tmp)
        if not c.get("name"):
            raise ValueError("The sheet has no character name filled in.")
        c["name"] = " ".join(str(c["name"]).split())[:40]
        self.store_character(c)                       # never over a character already called that
        self.send(h, {"ok": "%s is saved. Check these on the box before playing:" % html.escape(c["name"]),
                      "todo": [html.escape(w) for w in warnings]})

    # ---- the library
    def get_library(self, h, q):
        games = "".join("<option value=%s>%s</option>" % (g["id"], html.escape(g["name"])) for g in self.app.games)
        sections, cards = self.app.library.counts()
        body = ("<p>%d sections and %d Magic cards are loaded.</p><h2>Add one of your own books</h2><p class=dim>PDF, EPUB, "
                "text or Markdown, up to 100 MB. The file stays on the box. A scanned PDF with no text layer cannot be searched.</p>"
                "<label>Game</label><select id=game>%s</select><label><input type=checkbox id=dm style='width:auto'> "
                "DM only (an adventure or campaign book: hidden from players)</label><input type=file id=file "
                "accept='.pdf,.epub,.txt,.md'><button class=main onclick=up()>Upload</button><div id=msg></div>") % (
                    sections, cards, games)
        script = """async function up(){const f=document.getElementById('file').files[0];if(!f)return;const m=document.getElementById('msg');
if(f.size>MAX_BOOK){m.textContent=TOO_BIG;return}
m.textContent='Uploading… keep this page open.';try{const r=await (await fetch('/library/upload?game='+document.getElementById('game').value+
'&dm='+(document.getElementById('dm').checked?1:0)+'&name='+encodeURIComponent(f.name),{method:'POST',body:f})).json();m.textContent=r.error||r.ok}
catch(e){m.textContent=LOST}}""".replace("MAX_BOOK", str(MAX_BOOK)).replace("TOO_BIG", json.dumps(BOOK_TOO_BIG)).replace("LOST", json.dumps(UPLOAD_LOST))
        self.send(h, page("Library", body, script))

    def post_library_upload(self, h, q):
        game = q.get("game", "")
        if game not in [g["id"] for g in self.app.games]:
            raise ValueError("Pick a game from the list.")
        name = safe_name(q.get("name", ""), BOOK_TYPES)
        if not name:
            raise ValueError("That file type is not supported. Use PDF, EPUB, text or Markdown.")
        parts = ["mine", game] + (["campaigns"] if q.get("dm") == "1" else []) + [name]
        dest = os.path.join(paths.content_dir(), *parts)
        self.save_upload(h, dest, MAX_BOOK, BOOK_TOO_BIG)
        try:
            note = self.index_library("/".join(parts))
        except sqlite3.OperationalError as e:         # the library file was held by something else (the loader
            if not dt_content.is_busy(e):             # run by hand, say): nothing is wrong with the book.
                raise                                 # Anything else (a full card) is said as it is
            note = "BUSY"
        if note.startswith("BUSY"):
            raise ValueError(LIBRARY_BUSY % name)     # the file is kept; the next upload or sync reads it
        if note.startswith("FAILED"):                 # it would fail again at every later upload: take it away
            os.remove(dest)
            raise ValueError("%s could not be read, so it was not kept. %s" % (name, note[len("FAILED: "):]))
        if note.startswith("NO TEXT"):
            raise ValueError("%s has no text I can read: it looks like a scan. Run it through OCR, then upload it again." % name)
        self.send(h, {"ok": "%s is loaded. %s" % (name, note)})

    def index_library(self, key=None):
        """Re-read the content folders into content.db, then let the box see it.
        Returns what the loader said about the file with this key (its place
        under the content folder), not about whatever it happened to read last."""
        with _index_lock:                             # two uploads at once would lock each other out
            con = dt_content.connect(paths.content_db())
            try:
                report = dict(dt_content.sync(con, paths.content_dir(), log=lambda *a: None))
            finally:
                try:                                  # into content.db itself, so a copy of that one file is whole
                    con.rollback()
                    con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                except sqlite3.Error:
                    pass
                con.close()
        self.app.later(self.app.reload_library)
        return report.get(key, "It was already loaded, and has not changed.")

    # ---- adding a game
    def get_games(self, h, q):
        have = "".join("<div class=card>%s <span class=dim>%s</span></div>" % (
            html.escape(g["name"]), "ready" if g["status"] == "ready" else "not built yet") for g in self.app.games)
        body = ("%s<h2>Add a board game</h2><p class=dim>For a game with turns and something to count. Write the "
                "how-to-play notes in your own words; upload the rulebook itself under Library.</p>"
                "<label>Name</label><input id=name maxlength=24><label>One line about it</label><input id=blurb maxlength=28>"
                "<div class=grid><div><label>Fewest players</label><input id=lo type=number value=2 min=1 max=6></div>"
                "<div><label>Most players</label><input id=hi type=number value=4 min=1 max=6></div>"
                "<div><label>Wins at (blank: none)</label><input id=at type=number></div></div>"
                "<label>Parts of a turn, separated by commas (blank: none)</label><input id=phases placeholder='Roll, Trade, Build'>"
                "<label>What to count</label><input id=tracker value=Points maxlength=16>"
                "<label><input type=checkbox id=low style='width:auto'> Lowest score wins</label>"
                "<label>How to play, in your own words</label><textarea id=teach rows=6></textarea>"
                "<button class=main onclick=add()>Add game</button><div id=msg></div>") % have
        script = """async function add(){const d={};['name','blurb','lo','hi','at','phases','tracker','teach'].forEach(k=>d[k]=document.getElementById(k).value);
d.low=document.getElementById('low').checked;const r=await (await fetch('/games/new',{method:'POST',body:JSON.stringify(d)})).json();
document.getElementById('msg').textContent=r.error||r.ok;if(r.ok)setTimeout(()=>location.reload(),2500)}"""
        self.send(h, page("Games", body, script))

    def post_games_new(self, h, q):
        d = json.loads(self.body(h).decode("utf-8"))
        name = " ".join(str(d.get("name", "")).split())[:24]
        gid = slug(name)
        if not gid:
            raise ValueError("The game needs a name.")
        if gid in [g["id"] for g in self.app.games]:
            raise ValueError("There is already a game called that.")
        lo, hi = sorted((max(1, min(6, int(d.get("lo") or 2))), max(1, min(6, int(d.get("hi") or 4)))))
        tracker = " ".join(str(d.get("tracker") or "Points").split())[:16]
        g = {"id": gid, "name": name, "blurb": (" ".join(str(d.get("blurb", "")).split()) or "A game from the shelf")[:28],
             "order": 100, "players": [lo, hi], "trackers": [{"name": tracker, "start": 0, "step": 1, "min": None}],
             "lowest_wins": bool(d.get("low"))}
        phases = [p.strip()[:16] for p in str(d.get("phases", "")).split(",") if p.strip()][:8]
        if phases:
            g["phases"] = phases
        if str(d.get("at", "")).strip():
            g["win"] = {"tracker": tracker, "at": int(d["at"])}
            if g["win"]["at"] <= 0:               # everyone starts on nought: the game would be over before it began
                raise ValueError("Wins at must be more than nought. Leave it blank for a game with no winning score.")
        folder = paths.data("games", gid)
        notes = str(d.get("teach", "")).strip()[:6000]
        if notes:
            paths.write_json(os.path.join(folder, "teach.json"), [{"title": "How to play " + name, "text": notes}], indent=1)
        paths.write_json(os.path.join(folder, "game.json"), g, indent=2)
        self.app.later(self.app.reload_games)
        self.send(h, {"ok": "%s is on the box. Find it under Play." % name})

    # ---- rulings
    def get_rulings(self, h, q):
        rows = "".join("<div class=card><div class=dim>%s · %s</div><b>%s</b><p>%s</p><div class=dim>%s</div></div>" % (
            html.escape(r.get("date", "")), html.escape(self.app.game_name(r.get("game")) or "Any game"),
            html.escape(r.get("q", "")), html.escape(r.get("answer", "")), html.escape(r.get("source", "")))
            for r in reversed(ask.rulings()) if not r.get("dm"))      # a DM-mode ruling may give the adventure away
        self.send(h, page("Rulings", rows or "<p class=dim>No rulings yet. Hold the button on the box and ask something.</p>"))

    # ---- soundboard
    def get_sounds(self, h, q):
        folder = paths.data("sounds")
        names = sorted(n for n in os.listdir(folder) if n.lower().endswith(SOUND_TYPES))
        buttons = "".join('<button onclick="play(this.textContent)">%s</button>' % html.escape(n) for n in names)
        body = ("<p>%s</p><button onclick=\"play('')\">Stop</button><h2>Add a sound</h2><p class=dim>Your own WAV or OGG "
                "files only.</p><input type=file id=file accept='.wav,.ogg'><button onclick=up()>Upload</button>"
                "<div id=msg></div>") % (buttons or "<span class=dim>No sounds yet.</span>")
        script = """async function play(n){await fetch('/sounds/play?name='+encodeURIComponent(n),{method:'POST'})}
async function up(){const f=document.getElementById('file').files[0];if(!f)return;const r=await (await fetch('/sounds/upload?name='+
encodeURIComponent(f.name),{method:'POST',body:f})).json();document.getElementById('msg').textContent=r.error||r.ok;if(r.ok)location.reload()}"""
        self.send(h, page("Sounds", body, script))

    def post_sounds_play(self, h, q):
        name = q.get("name", "")
        if not name:
            self.app.later(self.app.hw.stop_sound)
            return self.send(h, {"ok": True})
        name = safe_name(name, SOUND_TYPES)
        path = os.path.join(paths.data("sounds"), name or "")
        if not name or not os.path.isfile(path):
            raise ValueError("There is no sound called that.")
        self.app.later(lambda: self.app.hw.play(path))
        self.send(h, {"ok": True})

    def post_sounds_upload(self, h, q):
        name = safe_name(q.get("name", ""), SOUND_TYPES)
        if not name:
            raise ValueError("Upload a WAV or OGG file.")
        self.save_upload(h, os.path.join(paths.data("sounds"), name))
        self.send(h, {"ok": "%s added." % name})


def attach(app, port=PORT):
    web = Web(app, port)
    app.web = web if web.start() else None
    return app.web
