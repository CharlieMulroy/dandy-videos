"""Forced alignment of a narration read against its known script: word start and end times.

Usage: python3 videos/17-thanksgiving/voiceover/force_align.py <audio> <script.txt> [--out words.json]

The audio is band-limited to the voice (so a music bed bothers the aligner less), resampled to 16 kHz mono, and
pocketsphinx aligns the exact script words to it. Prints each word with its times; --out saves them as JSON.
"""
import argparse
import json
import re
import subprocess
import tempfile

from pocketsphinx import Decoder

ap = argparse.ArgumentParser()
ap.add_argument("audio")
ap.add_argument("script")
ap.add_argument("--out")
a = ap.parse_args()

text = open(a.script).read().lower()
text = text.replace("’", "'")
words = re.findall(r"[a-z0-9']+", text)
num = {"10": "ten", "3": "three", "1": "one"}
words = [num.get(w, w) for w in words]

wav = tempfile.mktemp(suffix=".raw")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", a.audio, "-af", "highpass=f=120,lowpass=f=5000",
                "-ac", "1", "-ar", "16000", "-f", "s16le", wav], check=True)
dec = Decoder(samprate=16000, bestpath=False, loglevel="FATAL")
dec.set_align_text(" ".join(words))
dec.start_utt()
dec.process_raw(open(wav, "rb").read(), full_utt=True)
dec.end_utt()
out = []
for seg in dec.seg():
    w = seg.word
    if w.startswith("<") or w.startswith("["):
        continue
    out.append(dict(word=re.sub(r"\(\d+\)$", "", w), start=round(seg.start_frame / 100, 2), end=round((seg.end_frame + 1) / 100, 2)))
for o in out:
    print(f"{o['start']:6.2f} {o['end']:6.2f}  {o['word']}")
if a.out:
    json.dump(out, open(a.out, "w"), indent=1)
