"""Shorten long internal pauses in the Piper VO takes (punchier coach delivery).

Any quiet run longer than MAX_GAP is cut down to KEEP seconds with short
crossfades. Rewrites audio-src/vo/tight/*.wav and the durations in
audio-src/vo/segments.json (fields file/dur)."""
import json, os
import numpy as np, soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_GAP, KEEP, THR, WIN = 0.14, 0.09, 0.015, 0.01

path = os.path.join(ROOT, "audio-src/vo/segments.json")
segs = json.load(open(path))
os.makedirs(os.path.join(ROOT, "audio-src/vo/tight"), exist_ok=True)
for line in segs.values():
    for s in line:
        src = s.get("raw", s["file"])
        x, sr = sf.read(os.path.join(ROOT, src))
        h = int(WIN * sr)
        quiet = np.array([np.sqrt((x[i:i + h] ** 2).mean()) < THR for i in range(0, len(x), h)])
        out, i, n = [], 0, len(quiet)
        pos = 0
        while i < n:
            j = i
            while j < n and quiet[j] == quiet[i]:
                j += 1
            a, b = i * h, min(len(x), j * h)
            chunk = x[a:b]
            inner = i > 0 and j < n
            if quiet[i] and inner and (b - a) / sr > MAX_GAP:
                k = int(KEEP * sr) // 2
                f = min(k, int(0.01 * sr))
                head, tail = chunk[:k].copy(), chunk[-k:].copy()
                head[-f:] *= np.linspace(1, 0, f)
                tail[:f] *= np.linspace(0, 1, f)
                chunk = np.concatenate([head, tail])
            out.append(chunk)
            i = j
        y = np.concatenate(out)
        dst = "audio-src/vo/tight/" + os.path.basename(src)
        sf.write(os.path.join(ROOT, dst), y, sr)
        s["raw"], s["file"], s["dur"] = src, dst, round(len(y) / sr, 3)
json.dump(segs, open(path, "w"), ensure_ascii=False, indent=1)
for k, line in segs.items():
    print(k, [s["dur"] for s in line])
