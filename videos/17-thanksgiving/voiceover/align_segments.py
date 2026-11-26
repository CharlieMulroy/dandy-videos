"""Forced alignment in segments: each line of the segments file is "start end | words said in that stretch".
Aligning short stretches keeps one loose passage from dragging the rest off. Writes word times as JSON.

Usage: python3 videos/17-thanksgiving/voiceover/align_segments.py <audio> <segments.txt> <out.json>
"""
import json
import re
import subprocess
import sys

from pocketsphinx import Decoder

audio, segfile, out = sys.argv[1:4]
res = []
for line in open(segfile):
    if "|" not in line:
        continue
    head, text = line.split("|", 1)
    t0, t1 = map(float, head.split())
    words = re.findall(r"[a-z0-9']+", text.lower().replace("’", "'"))
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(t0), "-to", str(t1), "-i", audio, "-af", "highpass=f=120,lowpass=f=5000",
                          "-ac", "1", "-ar", "16000", "-f", "s16le", "-"], capture_output=True).stdout
    dec = Decoder(samprate=16000, bestpath=False, loglevel="FATAL")
    dec.set_align_text(" ".join(words))
    dec.start_utt()
    dec.process_raw(raw, full_utt=True)
    dec.end_utt()
    if dec.seg() is None:
        print("NO ALIGNMENT:", t0, t1, " ".join(words))
        continue
    for seg in dec.seg():
        w = seg.word
        if w.startswith("<") or w.startswith("["):
            continue
        res.append(dict(word=re.sub(r"\(\d+\)$", "", w), start=round(t0 + seg.start_frame / 100, 2), end=round(t0 + (seg.end_frame + 1) / 100, 2)))
json.dump(res, open(out, "w"), indent=1)
print("|".join(f"{r['start']} {r['word']}" for r in res))
