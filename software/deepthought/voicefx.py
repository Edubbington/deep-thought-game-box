"""The sound of her voice after the speech service has made it: deeper and slower,
longer pauses, a metallic ring, a very large hall. Plain Python, no extra packages;
everything is worked in blocks so a ten second answer takes about a second on the Pi 2."""
import array
import sys


def _comb(x, delay, back):
    """y[n] = x[n] + back * y[n - delay]: an echo that keeps coming round."""
    out, prev = [], [0.0] * delay
    for i in range(0, len(x), delay):
        prev = [a + back * b for a, b in zip(x[i:i + delay], prev)]
        out.extend(prev)
    return out


def _allpass(x, delay, g):
    """Smears an echo out without colouring it."""
    out, px, py = [], [0.0] * delay, [0.0] * delay
    for i in range(0, len(x), delay):
        bx = x[i:i + delay]
        py = [-g * a + b + g * c for a, b, c in zip(bx, px, py)]
        px = bx
        out.extend(py)
    return out


def _mix(dry, wet, amount):
    return [a + amount * b for a, b in zip(dry, wet)]


def longer_pauses(x, rate, times):
    """Every silence of a sixth of a second or more is made `times` as long (1.6 s at most added)."""
    if times <= 1.0 or not x:
        return x
    frame = int(rate * 0.02)
    top = max(max(x), -min(x)) or 1.0
    quiet = [max(max(x[i:i + frame]), -min(x[i:i + frame])) < 0.03 * top for i in range(0, len(x), frame)]
    out, i, n = [], 0, len(quiet)
    while i < n:
        j = i
        while j < n and quiet[j] == quiet[i]:
            j += 1
        out.extend(x[i * frame:j * frame])
        if quiet[i] and j - i >= 8 and i > 0 and j < n:          # a pause inside the line, not its ends
            out.extend([0.0] * min(int(rate * 1.6), int((times - 1.0) * (j - i) * frame)))
        i = j
    return out


def shape(wav, pitch=1.0, pauses=1.0, metal=0.0, hall=0.0):
    """WAV bytes (16-bit, one channel) in, WAV bytes out.
    pitch   1 = as made; 0.9 = a tenth deeper and slower
    pauses  1 = as made; 2 = every pause twice as long
    metal   0 to 1: a metallic ring on every sound
    hall    0 to 1: how much of a very large room is heard
    Anything that is not such a WAV, or all noughts, comes back unchanged."""
    if (pitch == 1.0 and pauses <= 1.0 and not metal and not hall) or sys.byteorder != "little":
        return wav
    if len(wav) < 44 or wav[:4] != b"RIFF" or wav[8:12] != b"WAVE" or wav[12:16] != b"fmt ":
        return wav
    at = wav.find(b"data", 12)
    if at == -1 or int.from_bytes(wav[34:36], "little") != 16 or int.from_bytes(wav[22:24], "little") != 1:
        return wav
    at += 8
    rate = int.from_bytes(wav[24:28], "little")
    a = array.array("h")
    a.frombytes(wav[at:at + (len(wav) - at) // 2 * 2])
    x = longer_pauses([float(v) for v in a], rate, pauses)
    if metal:
        ring = _comb(x, max(2, int(rate * 0.0062)), 0.72)       # a short echo, 160 times a second: a tube
        ring = _comb(ring, max(2, int(rate * 0.0041)), 0.55)
        x = _mix(x, ring, 0.45 * metal)
    if hall:
        x = x + [0.0] * int(rate * 1.2)                         # room for the sound to die away
        wet = [0.0] * len(x)
        for ms, back in ((29.7, 0.80), (37.1, 0.78), (41.1, 0.76), (43.7, 0.74)):
            wet = _mix(wet, _comb(x, int(rate * ms / 1000.0), back), 0.25)
        wet = _allpass(_allpass(wet, int(rate * 0.005), 0.7), int(rate * 0.0017), 0.7)
        x = _mix(x, wet, 0.5 * hall)
    top = max(max(x), -min(x)) or 1.0
    a = array.array("h", [int(v * 30000.0 / top) for v in x])
    new = max(4000, int(rate * pitch))
    head = bytearray(wav[:at])
    head[24:28] = new.to_bytes(4, "little")
    head[28:32] = (new * 2).to_bytes(4, "little")
    body = a.tobytes()
    head[4:8] = (len(head) - 8 + len(body)).to_bytes(4, "little")
    head[at - 4:at] = len(body).to_bytes(4, "little")
    return bytes(head) + body
