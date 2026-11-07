"""Sound bed for video 05's night look: wind, a crow, gravel footsteps, a low drone, dirt, and the end chime.

Synthesised from noise and sines at 48 kHz like 04's sfx.py, whose helpers it reuses.
build_bed(scenes, path) writes a stereo WAV the renderer mixes under the narration.
"""
import math
import os
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "04-context-rot", "void"))
from sfx import SR, chime, env, lowpass, swell, thud  # noqa: E402

rng = np.random.default_rng(31)


def wind(dur, gain=0.3, seed=0):
    """Filtered noise with a slow gusting envelope and a moving cutoff."""
    n = int(SR * dur)
    r = np.random.default_rng(seed)
    w = r.normal(0, 1, n).astype(np.float32)
    t = np.arange(n) / SR
    gust = 0.55 + 0.45 * np.sin(2 * math.pi * 0.07 * t + 1.3) * np.sin(2 * math.pi * 0.023 * t)
    cutoff = 350 + 450 * gust
    x = lowpass(w, cutoff) * gust
    x -= lowpass(x, 40)  # take the rumble out so it reads as air, not a hole
    return x / (np.abs(x).max() + 1e-6) * gain


def crow(gain=0.5):
    """Two rough caws: a sawtooth-ish tone with a fast pitch drop and noise."""
    out = []
    for k in range(2):
        n = int(SR * 0.28)
        t = np.arange(n) / SR
        f = 520 * np.exp(-t * 2.5) + 180
        ph = np.cumsum(f) / SR
        saw = 2 * (ph % 1) - 1
        x = (saw * 0.7 + rng.normal(0, 0.5, n)) * env(n, 0.02, 0.1, 0.6, 0.1)
        x = lowpass(x.astype(np.float32), 2200)
        out.append(x)
        out.append(np.zeros(int(SR * 0.12), np.float32))
    x = np.concatenate(out)
    return x / (np.abs(x).max() + 1e-6) * gain


def footstep(gain=0.45):
    """A heel on gravel: a low thump and a short crunch."""
    n = int(SR * 0.3)
    t = np.arange(n) / SR
    thump = np.sin(2 * math.pi * 65 * t) * np.exp(-t * 18)
    crunch = lowpass(rng.normal(0, 1, n).astype(np.float32), 1800) * np.exp(-t * 28) * 0.8
    x = thump + crunch
    return x / (np.abs(x).max() + 1e-6) * gain


def drone(dur, gain=0.3, base=41.2):
    """Low detuned sines, slow swell; the reaper's presence."""
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = np.zeros(n, np.float32)
    for f, g in ((base, 1.0), (base * 1.005, 0.8), (base * 2, 0.35), (base * 2.98, 0.15)):
        x += np.sin(2 * math.pi * f * t) * g
    x *= env(n, min(2.5, dur * 0.4), 0.0, 1.0, min(2.0, dur * 0.3))
    return x / (np.abs(x).max() + 1e-6) * gain


def dirt(gain=0.6):
    """Earth shifting: a bandpassed noise swell with grit."""
    n = int(SR * 1.4)
    t = np.arange(n) / SR
    x = lowpass(rng.normal(0, 1, n).astype(np.float32), 900) * env(n, 0.5, 0.3, 0.7, 0.5)
    x += lowpass(rng.normal(0, 1, n).astype(np.float32), 300) * np.exp(-t * 3) * 0.6
    return x / (np.abs(x).max() + 1e-6) * gain


def build_bed(scenes, path):
    total = sum(d for _, d in scenes)
    mix = np.zeros(int(SR * (total + 1)), np.float32)

    def put(sound, at):
        i = int(at * SR)
        j = min(len(mix), i + len(sound))
        if i < len(mix):
            mix[i:j] += sound[: j - i]

    put(wind(total, gain=0.28), 0.0)
    off = 0.0
    for sid, dur in scenes:
        if sid == "s1-stone":
            put(crow(gain=0.35), off + 1.6)
        elif sid == "s2-row":
            put(crow(gain=0.25), off + 5.2)
        elif sid == "s3-reaper":
            put(drone(dur + 2, gain=0.3), off)
            put(footstep(gain=0.5), off + 3.2)
            put(thud(gain=0.7), off + 4.1)
        elif sid == "s4-funeral":
            put(drone(dur, gain=0.22, base=36.7), off)
            for k, at in enumerate((4.3, 8.6)):
                put(footstep(gain=0.4 + 0.15 * k), off + at)
            put(dirt(gain=0.6), off + 10.4)
            put(thud(gain=0.6), off + 11.6)
        elif sid == "s5-gate":
            for k in range(6):
                put(footstep(gain=0.3), off + 0.6 + k * 0.95)
            put(swell(5.0, gain=0.3), off + 2.5)
            put(chime(gain=0.35, base=660), off + 3.0)
        elif sid == "end":
            put(chime(gain=0.5, base=880), off + 0.8)
        off += dur
    mix = mix[: int(SR * total)]
    mix = mix / (np.abs(mix).max() + 1e-6) * 0.7
    stereo = np.stack([mix, mix], axis=1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((stereo * 32767).astype(np.int16).tobytes())
    return path
