"""Synthesised sound effects for the void look, and the bed that places them on the scene timeline.

No sample library is involved: every sound is generated from noise and sine waves at 48 kHz.
build_bed(scenes, path) writes a stereo WAV the renderer mixes under the narration and music.
"""
import math
import wave

import numpy as np

SR = 48000
rng = np.random.default_rng(12)


def env(n, a, d, s=0.0, r=0.0, sus=1.0):
    """ADSR in seconds -> amplitude curve of n samples."""
    t = np.arange(n) / SR
    total = n / SR
    out = np.ones(n, np.float32) * sus
    out[t < a] = t[t < a] / max(a, 1e-4)
    dm = (t >= a) & (t < a + d)
    out[dm] = 1 - (1 - sus) * (t[dm] - a) / max(d, 1e-4)
    rm = t > total - r
    if r > 0:
        out[rm] *= np.clip((total - t[rm]) / r, 0, 1)
    return out


def lowpass(x, cutoff):
    """One-pole lowpass; cutoff may be an array (sweep)."""
    y = np.zeros_like(x)
    c = np.broadcast_to(np.asarray(cutoff, np.float32), x.shape)
    a = np.exp(-2 * math.pi * c / SR)
    acc = 0.0
    for i in range(len(x)):
        acc = a[i] * acc + (1 - a[i]) * x[i]
        y[i] = acc
    return y


def whoosh(dur=0.7, up=True, gain=0.9):
    n = int(SR * dur)
    noise = rng.normal(0, 1, n).astype(np.float32)
    sweep = np.geomspace(300, 6000, n) if up else np.geomspace(6000, 250, n)
    x = lowpass(noise, sweep) * env(n, 0.08, 0.1, 0.8, 0.3)
    return x / (np.abs(x).max() + 1e-6) * gain


def impact(dur=0.5, gain=1.0):
    n = int(SR * dur)
    t = np.arange(n) / SR
    thump = np.sin(2 * math.pi * (70 * np.exp(-t * 6) + 35) * t) * np.exp(-t * 9)
    click = rng.normal(0, 1, n).astype(np.float32) * np.exp(-t * 60) * 0.5
    x = thump + lowpass(click, 2500)
    return x / (np.abs(x).max() + 1e-6) * gain


def tick(gain=0.6, pitch=1800):
    n = int(SR * 0.08)
    t = np.arange(n) / SR
    x = np.sin(2 * math.pi * pitch * t) * np.exp(-t * 90) + rng.normal(0, 0.2, n) * np.exp(-t * 200)
    return x / (np.abs(x).max() + 1e-6) * gain


def thud(gain=0.9):
    n = int(SR * 0.6)
    t = np.arange(n) / SR
    x = np.sin(2 * math.pi * 55 * t) * np.exp(-t * 7) + 0.3 * np.sin(2 * math.pi * 110 * t) * np.exp(-t * 12)
    return x / (np.abs(x).max() + 1e-6) * gain


def chime(gain=0.6, base=880):
    n = int(SR * 1.6)
    t = np.arange(n) / SR
    x = np.zeros(n, np.float32)
    for k, f in enumerate((1.0, 1.5, 2.0, 3.0)):
        x += np.sin(2 * math.pi * base * f * t + k) * np.exp(-t * (2.2 + k)) / (k + 1)
    return x / (np.abs(x).max() + 1e-6) * gain


def swell(dur=5.0, gain=0.5):
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = np.zeros(n, np.float32)
    for f, g in ((55, 1.0), (110, 0.6), (165, 0.3), (220.5, 0.25)):
        x += np.sin(2 * math.pi * f * t) * g
    x *= env(n, dur * 0.7, 0.1, 1.0, dur * 0.25)
    return x / (np.abs(x).max() + 1e-6) * gain


def rumble(dur, gain=0.35):
    """Brown-ish noise, low-passed: the hole, always there underneath."""
    n = int(SR * dur)
    w = rng.normal(0, 1, n).astype(np.float32)
    b = np.cumsum(w) / 200
    b -= np.convolve(b, np.ones(2000) / 2000, mode="same")
    x = lowpass(b.astype(np.float32), 120)
    wob = 1 + 0.25 * np.sin(2 * math.pi * 0.7 * np.arange(n) / SR)
    x = x * wob
    return x / (np.abs(x).max() + 1e-6) * gain


def build_bed(scenes, path):
    """scenes: list of (id, duration). Places the effects for each scene id; writes a stereo 48 kHz WAV."""
    total = sum(d for _, d in scenes)
    mix = np.zeros(int(SR * (total + 1)), np.float32)

    def put(sound, at, pan=0.0):
        i = int(at * SR)
        j = min(len(mix), i + len(sound))
        if i < len(mix):
            mix[i:j] += sound[: j - i]

    off = 0.0
    for sid, dur in scenes:
        if sid != "end":
            r = rumble(dur, gain=0.28 if sid in ("s1-hook", "s2-name") else 0.18)
            fade = env(len(r), 0.4, 0.0, 1.0, 0.8)
            put(r * fade, off)
        if sid == "s1-hook":
            put(whoosh(0.8, up=True, gain=0.8), off)
            put(impact(gain=0.9), off + 0.15)
            for k, start in enumerate((0.0, 0.5, 1.1, 1.8, 2.7, 3.4)):
                put(whoosh(0.5, up=False, gain=0.35), off + start + 1.6)
        elif sid == "s2-name":
            put(whoosh(0.6, up=True, gain=0.7), off + 0.1)
            put(impact(gain=1.0), off + 0.32)
            put(impact(gain=1.0), off + 0.6)
            for start in (0.2, 1.6, 3.2):
                put(whoosh(0.5, up=False, gain=0.3), off + start + 1.8)
        elif sid == "s3-why":
            for k in range(14):
                put(tick(gain=0.35, pitch=1400 + k * 60), off + 0.7 + k * 0.2)
            put(whoosh(0.9, up=False, gain=0.6), off + 4.6)
            for k in range(6):
                put(tick(gain=0.4, pitch=900), off + 7.2 + 2.4 + k * 0.5)
            put(thud(gain=0.8), off + 11.8 + 1.7)
        elif sid == "s4-damage":
            for k in range(4):
                put(impact(0.35, gain=0.6 if k < 2 else 0.9), off + 0.8 + k * 2.6)
            put(whoosh(1.4, up=False, gain=0.5), off + 10.0)
        elif sid == "s5-fix":
            put(chime(gain=0.6, base=880), off + 0.45)
            put(swell(5.0, gain=0.45), off + 0.4)
            put(chime(gain=0.3, base=1320), off + 3.2)
        elif sid == "end":
            put(chime(gain=0.5, base=660), off + 0.95)
        off += dur
    mix = mix[: int(SR * total)]
    peak = np.abs(mix).max() + 1e-6
    mix = mix / peak * 0.7
    stereo = np.stack([mix, mix], axis=1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((stereo * 32767).astype(np.int16).tobytes())
    return path
