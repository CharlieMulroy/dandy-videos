"""Find where each narration line starts in a recording: speech chunks from ffmpeg silencedetect,
words from pocketsphinx. Prints chunks with their first words so the scene durations and captions
can be set from them.

Usage: python3 videos/02-maya/lofi/align.py <audio file> [--noise -32dB] [--gap 0.45]
"""
import argparse
import re
import subprocess
import tempfile

from pocketsphinx import AudioFile

ap = argparse.ArgumentParser()
ap.add_argument("audio")
ap.add_argument("--noise", default="-32dB")
ap.add_argument("--gap", type=float, default=0.45)
a = ap.parse_args()

wav = tempfile.mktemp(suffix=".wav")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", a.audio, "-ac", "1", "-ar", "16000", wav], check=True)
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", wav], capture_output=True, text=True).stdout.strip())
log = subprocess.run(["ffmpeg", "-i", wav, "-af", f"silencedetect=noise={a.noise}:d={a.gap}", "-f", "null", "-"], capture_output=True, text=True).stderr
starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", log)]
ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
# speech chunks are the gaps between silences
bounds, cur = [], 0.0
for s_, e_ in zip(starts, ends + [dur]):
    if s_ - cur > 0.25:
        bounds.append((cur, s_))
    cur = e_
if dur - cur > 0.25:
    bounds.append((cur, dur))
words = []
for phrase in AudioFile(audio_file=wav):
    for seg in phrase.seg():
        if seg.word not in ("<s>", "</s>", "<sil>", "[SPEECH]") and not seg.word.startswith("<"):
            words.append((seg.start_frame / 100.0, seg.end_frame / 100.0, seg.word))
print(f"duration {dur:.2f}s, {len(bounds)} speech chunks")
for i, (b0, b1) in enumerate(bounds):
    ws = [w for w in words if b0 - 0.05 <= w[0] <= b1]
    print(f"{i + 1:2d}  {b0:6.2f} - {b1:6.2f}  {' '.join(w[2] for w in ws)[:90]}")
