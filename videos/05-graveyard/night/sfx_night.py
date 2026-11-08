"""Sound bed for video 05's night look.

v2 (Nov 7): the v1 bed was wind over nothing and read as static. Now a slow minor pad carries the whole piece,
with a tolling bell on the open, a whistling (not hissing) wind, a crow, gravel footsteps for the reaper, a low
heartbeat under the funeral, hoofbeats for the rider, the pad resolving from minor to major under him (v4: the separate light swell is gone),
and the end chime.
Synthesised at 48 kHz from sines and noise; reuses helpers from 04's sfx.py. build_bed(scenes, path) -> WAV.
"""
import math
import os
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "04-context-rot", "void"))
from sfx import SR, chime, env, lowpass  # noqa: E402

rng = np.random.default_rng(31)


def tone(freq, n, harmonics=((1, 1.0), (2, 0.35), (3, 0.18), (4, 0.08)), detune=0.0025, phase=0.0):
    t = np.arange(n) / SR
    x = np.zeros(n, np.float32)
    for h, g in harmonics:
        x += np.sin(2 * math.pi * freq * h * t + phase) * g
        x += np.sin(2 * math.pi * freq * h * (1 + detune) * t + phase * 1.3) * g * 0.6
    return x


def pad(chords, seg, gain=0.25):
    """chords: list of lists of frequencies; each held for seg seconds with a slow cross-fade."""
    out = []
    n = int(SR * seg)
    xf = int(SR * 1.8)
    for k, ch in enumerate(chords):
        x = np.zeros(n, np.float32)
        for f in ch:
            x += tone(f, n, phase=k * 0.7) / len(ch)
        # slow tremolo so it breathes
        t = np.arange(n) / SR
        x *= 0.85 + 0.15 * np.sin(2 * math.pi * 0.11 * t + k)
        x *= env(n, xf / SR, 0.0, 1.0, xf / SR)
        out.append(x)
    # overlap-add the cross-fades
    total = np.zeros(int(n * len(chords) - xf * (len(chords) - 1)) + 1, np.float32)
    pos = 0
    for x in out:
        total[pos:pos + n] += x
        pos += n - xf
    return total / (np.abs(total).max() + 1e-6) * gain


def wind(dur, gain=0.16, seed=0):
    """Band-limited whistle rather than hiss: a narrow moving band of noise with a gusting envelope."""
    n = int(SR * dur)
    r = np.random.default_rng(seed)
    w = r.normal(0, 1, n).astype(np.float32)
    t = np.arange(n) / SR
    gust = 0.5 + 0.5 * np.sin(2 * math.pi * 0.05 * t + 1.3) * np.sin(2 * math.pi * 0.019 * t + 0.4)
    centre = 320 + 420 * gust
    hi = lowpass(w, centre * 1.25)
    lo = lowpass(w, centre * 0.8)
    x = (hi - lo) * (0.3 + 0.7 * gust)
    return x / (np.abs(x).max() + 1e-6) * gain


def bell(gain=0.5, base=196.0):
    """One toll: inharmonic partials with long decays."""
    n = int(SR * 5.0)
    t = np.arange(n) / SR
    x = np.zeros(n, np.float32)
    for ratio, g, dec in ((0.5, 0.5, 1.2), (1.0, 1.0, 1.6), (2.0, 0.6, 2.4), (2.41, 0.4, 3.0), (2.98, 0.3, 3.4), (4.5, 0.15, 5.0)):
        x += np.sin(2 * math.pi * base * ratio * t) * g * np.exp(-t * dec)
    x *= env(n, 0.004, 0.1, 1.0, 0.5)
    return x / (np.abs(x).max() + 1e-6) * gain


def crow(gain=0.4):
    out = []
    for k in range(2):
        n = int(SR * 0.26)
        t = np.arange(n) / SR
        f = 540 * np.exp(-t * 2.8) + 170
        ph = np.cumsum(f) / SR
        saw = 2 * (ph % 1) - 1
        x = (saw * 0.7 + rng.normal(0, 0.5, n)) * env(n, 0.02, 0.1, 0.6, 0.1)
        out.append(lowpass(x.astype(np.float32), 2200))
        out.append(np.zeros(int(SR * 0.13), np.float32))
    x = np.concatenate(out)
    return x / (np.abs(x).max() + 1e-6) * gain


def footstep(gain=0.45):
    n = int(SR * 0.3)
    t = np.arange(n) / SR
    thump = np.sin(2 * math.pi * 62 * t) * np.exp(-t * 18)
    crunch = lowpass(rng.normal(0, 1, n).astype(np.float32), 1700) * np.exp(-t * 26) * 0.8
    x = thump + crunch
    return x / (np.abs(x).max() + 1e-6) * gain


def heartbeat(dur, bpm=58, gain=0.3):
    n = int(SR * dur)
    x = np.zeros(n, np.float32)
    beat = int(SR * 60 / bpm)
    kn = int(SR * 0.25)
    kt = np.arange(kn) / SR
    k1 = np.sin(2 * math.pi * 48 * kt) * np.exp(-kt * 22)
    k2 = np.sin(2 * math.pi * 42 * kt) * np.exp(-kt * 26) * 0.7
    for i in range(0, n - beat, beat):
        x[i:i + kn] += k1
        j = i + int(SR * 0.22)
        x[j:j + kn] += k2
    x *= env(n, 2.0, 0.0, 1.0, 1.5)
    return x / (np.abs(x).max() + 1e-6) * gain


def hoofbeats(dur, gain=0.5, approach=True):
    """Canter: three beats and a rest per stride, each a thud with a short click; grows louder as it approaches."""
    n = int(SR * dur)
    x = np.zeros(n, np.float32)
    stride = 0.62
    kn = int(SR * 0.16)
    kt = np.arange(kn) / SR
    thud = np.sin(2 * math.pi * 90 * kt) * np.exp(-kt * 30)
    click = lowpass(rng.normal(0, 1, kn).astype(np.float32), 3000) * np.exp(-kt * 70) * 0.5
    hit = thud + click
    t0 = 0.0
    while t0 < dur:
        for off in (0.0, 0.14, 0.3):
            i = int((t0 + off) * SR)
            if i + kn < n:
                g = (0.25 + 0.75 * min(1.0, (t0 / dur) * 1.6)) if approach else 1.0
                x[i:i + kn] += hit * g
        t0 += stride
    return x / (np.abs(x).max() + 1e-6) * gain


def build_bed(scenes, path):
    total = sum(d for _, d in scenes)
    mix = np.zeros(int(SR * (total + 2)), np.float32)

    def put(sound, at):
        i = int(at * SR)
        j = min(len(mix), i + len(sound))
        if i < len(mix):
            mix[i:j] += sound[: j - i]

    starts = {}
    off = 0.0
    for sid, dur in scenes:
        starts[sid] = (off, dur)
        off += dur
    end_at = starts["end"][0]
    # the pad: A minor, F, D minor, E, repeating slowly; the E is sounding as the rider comes in, and the same pad
    # resolves to A major under him (v4: no separate light swell, which read as a synth horn)
    am, fm, dm, e = (110.0, 130.8, 164.8, 220.0), (87.3, 110.0, 130.8, 174.6), (73.4, 110.0, 146.8, 174.6), (82.4, 123.5, 164.8, 207.7)
    amaj = (110.0, 138.6, 164.8, 220.0, 277.2)
    seg = 7.0
    rider_at = starts["s5-rider"][0]
    minor_len = rider_at + 2.6
    nchords = int(math.ceil(minor_len / (seg - 1.8))) + 1
    minor = pad([am, fm, dm, e] * (nchords // 4 + 1), seg, gain=0.22)[: int(SR * minor_len)]
    put(minor * env(len(minor), 0.5, 0, 1.0, 2.5), 0.0)
    major_at = rider_at + 1.0
    major_len = total - major_at
    major = pad([amaj] * (int(major_len / (seg - 1.8)) + 2), seg, gain=0.24)[: int(SR * major_len)]
    put(major * env(len(major), 2.2, 0, 1.0, 2.5), major_at)
    put(wind(total, gain=0.05), 0.0)
    for sid, (at, dur) in starts.items():
        if sid == "s1-wide":
            put(bell(gain=0.45), at + 0.4)
            put(bell(gain=0.35), at + 3.6)
            put(crow(gain=0.3), at + 2.2)
        elif sid == "s2-push":
            put(crow(gain=0.2), at + 4.0)
        elif sid == "s3-reveal":
            for k in range(6):
                put(footstep(gain=0.28 + 0.03 * k), at + 1.4 + k * 1.15)
            put(bell(gain=0.3, base=146.8), at + 4.6)
        elif sid == "s4-weeks":
            put(heartbeat(dur, gain=0.2), at)
            for k, a in enumerate((4.4, 8.9)):
                put(footstep(gain=0.4 + 0.15 * k), at + a)
        elif sid == "s5-rider":
            put(hoofbeats(5.2, gain=0.42), at + 0.2)
        elif sid == "end":
            put(chime(gain=0.45, base=880), at + 0.8)
    mix = mix[: int(SR * total)]
    mix = mix / (np.abs(mix).max() + 1e-6) * 0.72
    stereo = np.stack([mix, mix], axis=1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((stereo * 32767).astype(np.int16).tobytes())
    return path
