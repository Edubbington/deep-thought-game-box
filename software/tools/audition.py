"""Hear a few candidate voices for her, one after another, through her own speaker.
Costs about a cent. Stop her program first (it holds the speaker):
    sudo systemctl stop deepthought;  python3 tools/audition.py;  sudo systemctl start deepthought
    python3 tools/audition.py --play     plays the ones already made again, makes nothing new"""
import copy
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from deepthought import paths, persona, voice, voicefx  # noqa: E402

STYLE = persona.SPEAKING
LINE = "I am Deep Thought. I have considered your question for some time. It is Sam's turn. Do try to keep up."
# name, voice, style, pitch, pauses, metal, hall, loudness
VOICES = [("one", "coral", STYLE, 0.97, 1.15, 0.15, 0.3, 2), ("two", "sage", STYLE, 0.97, 1.15, 0.15, 0.3, 2),
          ("three", "shimmer", STYLE, 0.97, 1.15, 0.15, 0.3, 2), ("four", "nova", STYLE, 0.97, 1.15, 0.15, 0.3, 2),
          ("five", "coral", STYLE, 0.97, 1.15, 0.15, 0.3, 5)]


if __name__ == "__main__":
    cfg = voice.load_config()
    out = paths.data("audition")
    os.makedirs(out, exist_ok=True)
    for name, who, style, pitch, pauses, metal, hall, press in VOICES:
        path = os.path.join(out, "%s.wav" % name)
        if "--play" not in sys.argv and not os.path.isfile(path):
            c = copy.deepcopy(cfg)
            c["speech"].update(tts_model="gpt-4o-mini-tts", tts_voice=who, tts_style=style, tts_press=0)
            try:
                audio = voice.text_to_speech(c, "Voice %s. %s" % (name, LINE))
            except Exception as e:
                print("voice %s (%s) could not be made: %s" % (name, who, str(e)[:200]))
                continue
            with open(path, "wb") as f:
                f.write(voice.full_volume(voicefx.shape(audio, pitch, pauses, metal, hall), press=press))
        if os.path.isfile(path):
            print("playing voice %s: %s, pitch %s, pauses %s, metal %s, hall %s" % (name, who, pitch, pauses, metal, hall), flush=True)
            subprocess.call(["aplay", "-q", path])
            time.sleep(1.5)
