"""Sound bed for The Relay, synthesised at 48 kHz (no samples): footfalls on a wet track, breathing, a low crowd
murmur from the empty stands, a starter's pistol, a scuff on each stumble, a clean slap on each good hand-off,
a soft tone when the baton lights, a beep when the clock stops.

build_bed(events, total, path) takes a list of (time_s, sound_name, gain, pan) plus footfall runs
[(start, end, steps_per_s, gain)] and writes a stereo WAV. render_relay.py derives both from its timeline.
"""
import math
import wave

import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000
rng = np.random.default_rng(6)


def band(x, lo=None, hi=None, order=2):
    if lo and hi:
        sos = butter(order, [lo, hi], btype="band", fs=SR, output="sos")
    elif lo:
        sos = butter(order, lo, btype="high", fs=SR, output="sos")
    else:
        sos = butter(order, hi, btype="low", fs=SR, output="sos")
    return sosfilt(sos, x).astype(np.float32)


def norm(x, gain):
    return (x / (np.abs(x).max() + 1e-9) * gain).astype(np.float32)


def noise(n):
    return rng.normal(0, 1, n).astype(np.float32)


def footfall(gain=0.5, wet=1.0):
    n = int(SR * 0.22)
    t = np.arange(n) / SR
    thump = np.sin(2 * math.pi * (95 * np.exp(-t * 30) + 45) * t) * np.exp(-t * 38)
    splash = band(noise(n), 1800, 7000) * np.exp(-t * 26) * 0.55 * wet
    grit = band(noise(n), 300, 1500) * np.exp(-t * 70) * 0.4
    return norm(thump + splash + grit, gain)


def scuff(gain=0.6):
    n = int(SR * 0.5)
    t = np.arange(n) / SR
    x = band(noise(n), 500, 4500) * (np.exp(-t * 7) * (1 - np.exp(-t * 60)))
    return norm(x, gain)


def breath(gain=0.35, dur=0.42, exhale=True):
    n = int(SR * dur)
    t = np.arange(n) / SR
    envl = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** (0.6 if exhale else 1.4)
    x = band(noise(n), 500, 2600 if exhale else 1800) * envl
    return norm(x, gain)


def pistol(gain=1.0):
    n = int(SR * 1.8)
    t = np.arange(n) / SR
    crack = noise(n) * np.exp(-t * 180)
    body = np.sin(2 * math.pi * 120 * t) * np.exp(-t * 40) * 0.6
    tail = band(noise(n), 200, 3000) * np.exp(-t * 2.6) * 0.22
    echo = np.zeros(n, np.float32)
    d = int(SR * 0.23)
    echo[d:] = crack[:-d] * 0.3
    return norm(crack + body + tail + band(echo, 300, 2500), gain)


def slap(gain=0.6):
    n = int(SR * 0.25)
    t = np.arange(n) / SR
    x = band(noise(n), 800, 5000) * np.exp(-t * 55) + np.sin(2 * math.pi * 210 * t) * np.exp(-t * 40) * 0.5
    return norm(x, gain)


def tone(gain=0.4, base=440.0, dur=2.2):
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = np.zeros(n, np.float32)
    for k, f in enumerate((1.0, 2.0, 3.01, 4.2)):
        x += np.sin(2 * math.pi * base * f * t + k) * np.exp(-t * (1.4 + 1.2 * k)) / (k + 1)
    x *= 1 - np.exp(-t * 40)
    return norm(x, gain)


def beep(gain=0.4):
    n = int(SR * 0.35)
    t = np.arange(n) / SR
    x = np.sin(2 * math.pi * 1320 * t) * (t < 0.22) * (1 - np.exp(-t * 300)) * np.exp(-np.clip(t - 0.18, 0, None) * 40)
    return norm(x, gain)


def whoosh(gain=0.5, dur=1.2):
    n = int(SR * dur)
    t = np.arange(n) / SR
    x = noise(n)
    lo = band(x, 200, 900) * np.sin(np.pi * t / dur) ** 2
    hi = band(x, 1500, 6000) * np.sin(np.pi * t / dur) ** 4 * 0.6
    return norm(lo + hi, gain)


def crowd(total, gain=0.12, swell_at=None):
    """A low murmur from a far crowd: band-limited noise, slowly breathing; a swell around swell_at."""
    n = int(SR * total)
    t = np.arange(n) / SR
    x = band(noise(n), 180, 1400, order=3)
    mod = 0.7 + 0.3 * np.sin(2 * math.pi * 0.11 * t) + 0.15 * np.sin(2 * math.pi * 0.37 * t + 1)
    if swell_at is not None:
        mod = mod + 1.6 * np.exp(-((t - swell_at - 0.8) / 1.3) ** 2)
    return norm(x * mod, gain)


SOUNDS = dict(footfall=footfall, scuff=scuff, breath=breath, pistol=pistol, slap=slap, tone=tone, beep=beep, whoosh=whoosh)


def build_bed(events, runs, total, path, crowd_swell=None):
    n = int(SR * total) + SR
    L = np.zeros(n, np.float32)
    R = np.zeros(n, np.float32)

    def put(x, at, pan):
        i = int(at * SR)
        if i >= n:
            return
        x = x[:n - i]
        L[i:i + len(x)] += x * math.cos((pan + 1) * math.pi / 4) * 1.41
        R[i:i + len(x)] += x * math.sin((pan + 1) * math.pi / 4) * 1.41

    c = crowd(total + 1, 0.10, crowd_swell)
    L[:len(c)] += c
    R[:len(c)] += np.roll(c, 2400)
    for start, end, rate, gain in runs:
        k = 0
        tt = start
        while tt < end:
            put(footfall(gain * rng.uniform(0.8, 1.05), wet=rng.uniform(0.7, 1.2)), tt, 0.25 if k % 2 else -0.25)
            k += 1
            tt += 1.0 / rate * rng.uniform(0.96, 1.04)
    for at, name, gain, pan in events:
        put(SOUNDS[name](gain), at, pan)
    peak = max(np.abs(L).max(), np.abs(R).max(), 1e-6)
    st = np.stack([L, R], 1)[:int(SR * total)] / peak * 0.63   # about 3 dB under the first cut, leaving room for the voice
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())
