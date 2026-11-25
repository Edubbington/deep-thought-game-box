"""Her voice: speech out, speech in, and spoken questions.

Three cloud services, each optional and each set in config.toml:

  [claude]  answers to questions, in her voice (the Anthropic SDK)
  [speech]  text to speech and speech to text (an OpenAI-style speech API)

With no config.toml she still works: lines appear on screen, questions are
typed and answered from the library. Nothing here ever blocks the screen:
network calls run on a worker thread and come back through app.later().

NOT TESTED against the live services: no keys were available when this was
written. The request shapes are from the services' published APIs.
"""
import array
import hashlib
import json
import math
import os
import queue
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid

from . import ask, paths, persona, settings, voicefx

try:
    import tomllib
except ImportError:                                  # Python 3.10 and older
    tomllib = None

DEFAULTS = {"claude": {"api_key": "", "model": "claude-haiku-5-5"},
            "speech": {"api_key": "", "base_url": "https://api.openai.com/v1", "stt_model": "whisper-1",
                       # Her voice, chosen by ear on the real Pi, 23 Nov 2026. Change any of these and
                       # every line already recorded is made again the next time it is wanted.
                       "tts_model": "gpt-4o-mini-tts", "tts_voice": "nova",
                       "tts_style": persona.SPEAKING,   # how to speak; "" for speech models that take no direction
                       "tts_pitch": 0.97,     # 1 = as made; lower = deeper and slower
                       "tts_pauses": 1.15,    # 1 = as made; 2 = every pause twice as long
                       "tts_metal": 0.15,     # 0 to 1: a metallic ring
                       "tts_hall": 0.3,       # 0 to 1: a very large room
                       "tts_press": 2.0},     # 0 = natural; 3 to 8 = pressed louder for a small speaker
            "limits": {"monthly_dollars": 5.0}}
# Dollars per million tokens (input, output), for the monthly cap. Update if prices change.
PRICES = {"claude-haiku-5-5": (0.10, 0.50), "claude-sonnet-5-5": (2.0, 10.0), "claude-opus-5-5": (4.0, 20.0)}
TTS_DOLLARS_PER_1000_CHARS = 0.015
STT_DOLLARS_PER_MINUTE = 0.006


def load_config(path=None):
    """The keys and limits from config.toml. Never raises: a file that cannot be
    read gives the defaults, and cfg["problem"] says what was wrong with it."""
    cfg = {k: dict(v) for k, v in DEFAULTS.items()}
    path = path or os.path.join(paths.SOFTWARE, "config.toml")
    problem = ""
    if tomllib and os.path.isfile(path):
        try:
            with open(path, "rb") as f:
                loaded = tomllib.load(f)
            fresh = {k: dict(v) for k, v in DEFAULTS.items()}
            for section, values in loaded.items():
                if not isinstance(values, dict):
                    raise ValueError("%s is not under a [section] line" % section)
                fresh.setdefault(section, {}).update(values)
            fresh["limits"]["monthly_dollars"] = float(fresh["limits"]["monthly_dollars"])
            for section in ("claude", "speech"):
                fresh[section] = {k: str(v) for k, v in fresh[section].items()}
            cfg = fresh
        except Exception as e:                        # a slip in the file must not stop the box
            problem = "config.toml could not be read: %s" % e
    cfg["claude"]["api_key"] = cfg["claude"]["api_key"] or os.environ.get("ANTHROPIC_API_KEY", "")
    cfg["problem"] = problem
    return cfg


# ---------------------------------------------------------------- spend cap
def spend_path():
    return paths.data("spend.json")


_spend_lock = threading.RLock()                      # the voice worker and the photo page both add to it


def _spend():
    with _spend_lock:
        try:
            with open(spend_path(), encoding="utf-8") as f:
                d = json.load(f)
        except (OSError, ValueError):
            return {}
    return d if isinstance(d, dict) else {}


def spent_this_month():
    try:
        return float(_spend().get(time.strftime("%Y-%m"), 0.0))
    except (TypeError, ValueError):
        return 0.0


def add_spend(dollars):
    month = time.strftime("%Y-%m")
    with _spend_lock:
        d = _spend()
        d[month] = round(spent_this_month() + dollars, 6)
        paths.write_json(spend_path(), d)
    return d[month]


# ---------------------------------------------------------------- the three services
def _claude_http(cfg, body, timeout):
    """The same request with nothing but Python's own library, for the Pi, where the
    anthropic package is not installed. Returns (tokens in, tokens out, stop reason, text)."""
    key = cfg["claude"]["api_key"] or os.environ.get("ANTHROPIC_API_KEY", "")
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode("utf-8"),
                                 method="POST", headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                                                         "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            reply = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 401:
            raise RuntimeError("The Claude API key was refused.")
        if e.code == 429:
            raise RuntimeError("The Claude API is rate limited just now.")
        raise RuntimeError("The Claude API returned an error (%s)." % e.code)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        raise RuntimeError("The network is away.")
    usage = reply.get("usage", {})
    text = " ".join(b.get("text", "") for b in reply.get("content", []) if b.get("type") == "text").strip()
    return usage.get("input_tokens", 0), usage.get("output_tokens", 0), reply.get("stop_reason"), text


def claude_answer(cfg, system, user, timeout=20.0, max_tokens=2000, cut_off=None):
    """One short answer from Claude. user is the question, or a list of content
    blocks (a picture and a question). Raises RuntimeError with a plain message
    on any failure. cut_off is what to say if the reply ran out of room before
    it finished; without it a reply that ran out is used as far as it got.
    Uses the anthropic package where it is installed (the PC) and plain HTTPS
    where it is not (the Pi)."""
    model = cfg["claude"]["model"]
    body = {"model": model, "max_tokens": max_tokens, "system": system,
            "output_config": {"effort": "low"},      # short spoken answers; keep it quick and cheap
            "messages": [{"role": "user", "content": user}]}
    try:
        import anthropic
    except ImportError:
        anthropic = None
    if anthropic is None:
        tokens_in, tokens_out, stop, text = _claude_http(cfg, body, timeout)
    else:
        client = anthropic.Anthropic(api_key=cfg["claude"]["api_key"] or None, timeout=timeout, max_retries=1)
        try:
            response = client.messages.create(**body)
        except anthropic.AuthenticationError:
            raise RuntimeError("The Claude API key was refused.")
        except anthropic.RateLimitError:
            raise RuntimeError("The Claude API is rate limited just now.")
        except anthropic.APIStatusError as e:
            raise RuntimeError("The Claude API returned an error (%s)." % e.status_code)
        except anthropic.APIConnectionError:
            raise RuntimeError("The network is away.")
        tokens_in, tokens_out, stop = response.usage.input_tokens, response.usage.output_tokens, response.stop_reason
        text = " ".join(block.text for block in response.content if block.type == "text").strip()
    price_in, price_out = PRICES.get(model, (4.0, 20.0))
    add_spend((tokens_in * price_in + tokens_out * price_out) / 1e6)
    if stop == "refusal":
        raise RuntimeError("That question was declined.")
    if stop == "max_tokens" and cut_off:
        raise RuntimeError(cut_off)
    return text


SHEET_SYSTEM = ("You are shown a photograph of one player's own tabletop role-playing character sheet. Copy what is "
                "written on it into JSON. Copy only what you can read. Use null for anything missing or unreadable. "
                "Never guess or work out a number that is not written there. Reply with one JSON object and nothing else.")
SHEET_PROMPT = """Use exactly these keys:
"name", "player", "species", "background": text
"classlevel": text such as "Fighter 3" or "Wizard (Evoker) 5" or "Fighter 3 / Rogue 2"
"str", "dex", "con", "int", "wis", "cha": the ability SCORES (usually 3 to 20), not the modifiers
"saves": list of the abilities whose saving throw is marked proficient, as "str", "dex", "con", "int", "wis", "cha"
"skills": list of the skill names marked proficient, in lower case
"hp_max", "hp_current", "hp_temp", "ac", "speed": numbers
"cp", "sp", "ep", "gp", "pp": coins, numbers
"equipment": list of items, each as text, with a count first if there is one, such as "2 x Dagger"
"spells": list of spell names
"features": list of the names of features and traits
"notes": any other short text worth keeping"""
SHEET_KEYS = ("name", "player", "species", "background", "classlevel", "str", "dex", "con", "int", "wis", "cha", "saves",
              "skills", "hp_max", "hp_current", "hp_temp", "ac", "speed", "cp", "sp", "ep", "gp", "pp", "equipment",
              "spells", "features", "notes")
PHOTO_TYPES = ("image/jpeg", "image/png", "image/webp")
SHEET_TOO_LONG = "That sheet has too much on it to read in one go. Type it in instead."


def sheet_json(text):
    """The model's reply as the boxes of the character form. Anything it added
    that is not a box on the form is dropped."""
    a, b = text.find("{"), text.rfind("}")
    try:
        d = json.loads(text[a:b + 1]) if 0 <= a < b else None
    except ValueError:
        d = None
    if not isinstance(d, dict):
        raise RuntimeError("I could not read that photo. Try again in better light, or type the sheet in.")
    out = {}
    for k in SHEET_KEYS:
        v = d.get(k)
        if k in ("equipment", "spells", "features") and isinstance(v, list):
            v = "\n".join(str(x) for x in v if x)
        elif k in ("saves", "skills"):
            v = [str(x).lower() for x in v] if isinstance(v, list) else []
        if v is not None:
            out[k] = v
    return out


def read_sheet_photo(cfg, image, media_type="image/jpeg"):
    """Send a photo of a paper character sheet to Claude and get the form boxes
    back. The photo goes to the cloud; nothing is kept there by this program."""
    import base64
    if media_type not in PHOTO_TYPES:
        raise RuntimeError("That is not a photo I can read. Use a JPEG or PNG.")
    content = [{"type": "image", "source": {"type": "base64", "media_type": media_type,
                                            "data": base64.standard_b64encode(image).decode("ascii")}},
               {"type": "text", "text": SHEET_PROMPT}]
    return sheet_json(claude_answer(cfg, SHEET_SYSTEM, content, timeout=60.0, max_tokens=4000, cut_off=SHEET_TOO_LONG))


def _post(url, key, body, content_type, timeout=30):
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Authorization": "Bearer " + key, "Content-Type": content_type})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError("The speech service returned an error (%s)." % e.code)
    except (urllib.error.URLError, TimeoutError, OSError):
        raise RuntimeError("The network is away.")


def true_lengths(wav):
    """WAV bytes with their two length fields set to the real lengths.
    Found on the real Pi, 22 Nov 2026: the speech service sends a WAV whose lengths say
    "unknown" (all bits set). The PC plays that; the Pi refuses it with "Out of memory"
    and she stays silent. Bytes that are not a WAV come back unchanged."""
    if len(wav) < 12 or wav[:4] != b"RIFF" or wav[8:12] != b"WAVE":
        return wav
    out, i = bytearray(wav), 12
    out[4:8] = (len(wav) - 8).to_bytes(4, "little")
    while i + 8 <= len(wav):
        size = int.from_bytes(wav[i + 4:i + 8], "little")
        if wav[i:i + 4] == b"data":
            out[i + 4:i + 8] = (len(wav) - i - 8).to_bytes(4, "little")   # the sound runs to the end
            break
        i += 8 + size + (size & 1)
    return bytes(out)


def full_volume(wav, peak=31000, most=6.0, press=0.0):
    """WAV bytes (16-bit) made as loud as they go without distorting: the loudest moment
    is brought up to nearly full scale. Found on the real Pi, 23 Nov 2026: the speech
    service's lines peak at well under half scale, and through her small speaker Ethan
    could barely hear them. Anything that is not such a WAV comes back unchanged."""
    if len(wav) < 44 or wav[:4] != b"RIFF" or wav[8:12] != b"WAVE":
        return wav
    i, bits = 12, 0
    while i + 8 <= len(wav):
        size = int.from_bytes(wav[i + 4:i + 8], "little")
        if wav[i:i + 4] == b"fmt ":
            bits = int.from_bytes(wav[i + 22:i + 24], "little")
        if wav[i:i + 4] == b"data":
            break
        i += 8 + size + (size & 1)
    else:
        return wav
    end = len(wav) - ((len(wav) - i - 8) & 1)
    if bits != 16 or sys.byteorder != "little":
        return wav
    a = array.array("h")
    a.frombytes(wav[i + 8:end])
    loudest = max(max(a), -min(a)) if a else 0
    gain = min(most, peak / float(loudest)) if loudest >= 200 else 1.0     # near silence is left alone
    if gain <= 1.02 and not press:
        return wav
    if not press or loudest < 200:
        a = array.array("h", [int(x * gain) for x in a])
        return wav[:i + 8] + a.tobytes() + wav[end:]
    # Pressed: still too quiet for a room at full scale (measured with her own microphone:
    # the speaker follows the signal faithfully, there is just not much of it). So the deep
    # notes her small speaker cannot make are taken out, and the quiet parts of each word
    # are pushed up towards the loud parts. Louder, at some cost in naturalness.
    rate = int.from_bytes(wav[20 + 4:20 + 8], "little") or 24000
    k = 1.0 / (1.0 + 2 * math.pi * 300.0 / rate)      # high pass at 300 Hz, twice
    out, x1, y1, x2, y2 = [], 0.0, 0.0, 0.0, 0.0
    for x in a:
        y1 = k * (y1 + x - x1); x1 = x
        y2 = k * (y2 + y1 - x2); x2 = y1
        out.append(y2)
    top = max(max(out), -min(out)) or 1.0
    d, scale, tanh = press / top, peak / math.tanh(press), math.tanh
    a = array.array("h", [int(scale * tanh(d * y)) for y in out])
    return wav[:i + 8] + a.tobytes() + wav[end:]


def _num(s, key, default):
    """A number from the config, which may hold it as text; a slip there gives the plain default."""
    try:
        return float(s.get(key, default))
    except (TypeError, ValueError):
        return float(default)


def text_to_speech(cfg, text):
    """Returns WAV bytes."""
    s = cfg["speech"]
    ask_for = {"model": s["tts_model"], "voice": s["tts_voice"], "input": text, "response_format": "wav"}
    if s.get("tts_style"):
        ask_for["instructions"] = s["tts_style"]
    body = json.dumps(ask_for).encode()
    audio = _post(s["base_url"].rstrip("/") + "/audio/speech", s["api_key"], body, "application/json")
    add_spend(len(text) / 1000.0 * TTS_DOLLARS_PER_1000_CHARS)
    audio = voicefx.shape(true_lengths(audio), _num(s, "tts_pitch", 1), _num(s, "tts_pauses", 1),
                          _num(s, "tts_metal", 0), _num(s, "tts_hall", 0))
    return full_volume(audio, press=_num(s, "tts_press", 0))


def speech_to_text(cfg, wav_path, seconds=5.0):
    s = cfg["speech"]
    boundary = uuid.uuid4().hex
    with open(wav_path, "rb") as f:
        audio = f.read()
    parts = [b"--" + boundary.encode(), b'Content-Disposition: form-data; name="model"', b"", s["stt_model"].encode(),
             b"--" + boundary.encode(), b'Content-Disposition: form-data; name="file"; filename="question.wav"',
             b"Content-Type: audio/wav", b"", audio, b"--" + boundary.encode() + b"--", b""]
    out = _post(s["base_url"].rstrip("/") + "/audio/transcriptions", s["api_key"], b"\r\n".join(parts),
                "multipart/form-data; boundary=" + boundary)
    add_spend(seconds / 60.0 * STT_DOLLARS_PER_MINUTE)
    return json.loads(out.decode("utf-8")).get("text", "").strip()


# ---------------------------------------------------------------- the voice
class Voice:
    def __init__(self, app, cfg=None):
        self.app, self.cfg = app, cfg or load_config()
        self.jobs = queue.Queue()
        self.record_started = None
        self.last_answer = None
        self.worker = threading.Thread(target=self._work, daemon=True)
        self.worker.start()

    # ---- what is switched on
    def under_cap(self):
        return spent_this_month() < float(self.cfg["limits"]["monthly_dollars"])

    def cloud_on(self):
        return bool(settings.get("cloud")) and self.under_cap()

    def can_answer(self):
        return self.cloud_on() and bool(self.cfg["claude"]["api_key"])

    def can_speak(self):
        return bool(self.cfg["speech"]["api_key"])

    def can_hear(self):
        return self.cloud_on() and self.can_speak() and self.app.hw.has_mic()

    def status(self):
        """One line for Settings."""
        bits = ["answers " + ("on" if self.can_answer() else "off"), "speech " + ("on" if self.can_speak() else "off"),
                "mic " + ("on" if self.can_hear() else "off")]
        line = ", ".join(bits) + ". $%.2f of $%.2f this month" % (spent_this_month(), float(self.cfg["limits"]["monthly_dollars"]))
        if self.cfg.get("problem"):                    # a slip in config.toml: she runs on the defaults and says so
            line += ". " + self.cfg["problem"]
        return line

    # ---- speech out
    def cache_file(self, text):
        s = self.cfg["speech"]
        how = "%s|%s" % (s["tts_model"], s["tts_voice"])
        shaping = [s.get("tts_style") or ""] + [_num(s, k, d) for k, d in
                   (("tts_press", 0), ("tts_pitch", 1), ("tts_pauses", 1), ("tts_metal", 0), ("tts_hall", 0))]
        if shaping != ["", 0.0, 1.0, 1.0, 0.0, 0.0]:       # a line is tied to everything that shapes its sound
            how += "|" + "|".join(str(v) for v in shaping)
        key = hashlib.sha1(("%s|%s" % (how, text)).encode("utf-8")).hexdigest()
        return os.path.join(paths.data("speech"), key + ".wav")

    def say(self, text, show=True):
        """Speak a line. Lines already made are played from disk, with no network."""
        if show:
            self.app.say(text, speak=False)
        if not text or not self.can_speak():
            return
        path = self.cache_file(text)
        if os.path.isfile(path):
            self.app.hw.play(path)
        elif self.cloud_on():
            self.jobs.put(("speak", text))

    def line(self, moment, optional=False):
        """Say one of her stock lines for a moment."""
        if optional and not persona.optional(settings.get("chatty")):
            return
        self.say(persona.line(moment))

    # ---- speech in: hold the button
    def hold(self, down):
        hw = self.app.hw
        if down:
            if self.can_hear():
                self.record_started = time.monotonic()
                hw.record_start()
                hw.ring("listening", level=1.0)        # the ring shows the microphone is live
            return
        if self.record_started is not None:
            seconds, self.record_started = time.monotonic() - self.record_started, None
            wav = hw.record_stop()
            self.app.screen.show_ring() if hasattr(self.app.screen, "show_ring") else hw.ring("breathe")
            if seconds < 0.6 or not wav:               # an accident, not a question
                return
            hw.ring("thinking")
            self.jobs.put(("hear", wav, seconds))
        else:
            self.type_question()

    def type_question(self):
        """No microphone, or the cloud is off: ask by typing."""
        from .screens.common import TextEntry
        why = "" if self.app.hw.has_mic() else "No microphone. "
        self.app.say(why + "Type your question.", speak=False)
        self.app.push(TextEntry(self.app, "Ask", "", self.ask, "Ask", max_len=60))

    # ---- questions
    def ask(self, question):
        if not question.strip():
            return
        self.app.hw.ring("thinking")
        self.app.say("You asked: %s" % question, speak=False)
        self.jobs.put(("ask", question))

    def _context(self):
        s = self.app.session
        if not s:
            return None, "", ""
        phases = dict(s.game.phases())
        key = s.game.phase(s.state)
        return s.game.id, s.game.name, phases.get(key, key)

    def _llm(self):
        if not self.can_answer():
            return None
        return lambda system, user: claude_answer(self.cfg, system, user)

    def _answer(self, question):
        game, name, phase = self._context()
        return ask.answer(question, self.app.library, game, name, phase, dm=self.app.dm, llm=self._llm(),
                          table=self.table_now())

    def table_now(self):
        """What she can see for herself, in words, to go with a question: the time, and
        from the shared scoreboard (only what every player may see) whose turn and the scores."""
        from . import web
        out = [time.strftime("The time is %H:%M on %A (say it only if asked).")]
        try:
            st = web.state(self.app)
        except Exception:
            st = {"playing": False}
        if st.get("playing"):
            where = ", ".join(x for x in (st.get("title"), st.get("left")) if x)
            out.append("On your screen now: %s." % where if where else "A game is in play.")
            seat = st.get("active")
            if isinstance(seat, int) and 0 <= seat < len(st["players"]):
                out.append("It is %s's turn." % st["players"][seat])
            rows = ["%s %s" % (r.get("name"), r.get("value")) for r in st.get("rows", []) if r.get("value") not in ("", None)]
            if rows:
                out.append("Scoreboard%s: %s." % ((" (%s)" % st["note"]) if st.get("note") else "", ", ".join(rows)))
        else:
            out.append("No game is in play on you just now.")
        return " ".join(out)

    def show_answer(self, question, result):
        from .screens.common import Pages
        hw, screen = self.app.hw, self.app.screen
        screen.show_ring() if hasattr(screen, "show_ring") else hw.ring("breathe")
        self.last_answer = (question, result)
        labels = {"ruling": "As I ruled on %s" % result.get("date", "an earlier night"), "cloud": "Deep Thought",
                  "library": "From the library, as written", "none": "Deep Thought"}
        body = result["text"]
        if result.get("source"):
            body += "\n\nSource: " + result["source"]
        if result["from"] == "library" and not self.can_answer():
            body += "\n\n(" + ("Spoken answers are off: this is the page itself." if not self.under_cap() or
                               not settings.get("cloud") else "No Claude key is set: this is the page itself.") + ")"
        if result.get("note"):                         # the cloud was tried and did not answer
            body += "\n\n(%s Lookup, scoring and tracking are not affected.)" % result["note"]
        self.app.toast = None
        self.app.push(Pages(self.app, "You asked", labels[result["from"]], [(question, body)]))
        if result["from"] in ("cloud", "ruling", "none"):
            self.say(result["text"], show=False)

    # ---- the worker thread: everything that waits on the network
    def _work(self):
        while True:
            job = self.jobs.get()
            try:
                if job[0] == "speak":
                    path = self.cache_file(job[1])
                    if not os.path.isfile(path):
                        audio = text_to_speech(self.cfg, job[1])
                        with open(path + ".tmp", "wb") as f:
                            f.write(audio)
                        os.replace(path + ".tmp", path)
                    self.app.later(lambda p=path: self.app.hw.play(p))
                elif job[0] == "hear":
                    question = speech_to_text(self.cfg, job[1], job[2])
                    if question:
                        self.app.later(lambda q=question: self.app.say("You asked: %s" % q, speak=False))
                        result = self._answer(question)
                        self.app.later(lambda q=question, r=result: self.show_answer(q, r))
                    else:
                        self.app.later(lambda: (self.app.hw.ring("breathe"), self.app.say("I heard nothing I could use.")))
                elif job[0] == "ask":
                    result = self._answer(job[1])
                    self.app.later(lambda q=job[1], r=result: self.show_answer(q, r))
            except Exception as e:                    # a failed call must never stop the box
                self.app.later(lambda e=e: (self.app.hw.ring("breathe"), self.app.say(str(e) or "Something went wrong.", speak=False)))


def attach(app):
    """Give the app a voice. Always succeeds: with no keys she is text only."""
    app.voice = Voice(app)
    return app.voice
