"""Generate the voice-over, one sentence at a time, and keep the clearest take.

Voice: Piper `fr_FR-tom-medium` (French male), from the sherpa-onnx model release:
  https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/vits-piper-fr_FR-tom-medium.tar.bz2
Checker: Whisper small (sherpa-onnx) transcribes every take; the take with the lowest
word error rate against the script wins (ties -> the take closest to the median length).
  https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-whisper-small.tar.bz2

  VOICE=/path/fr_FR-tom-medium.onnx WHISPER=/path/sherpa-onnx-whisper-small python3 tools/make_vo.py

Writes audio-src/vo/seg<line>_<n>.wav and audio-src/vo/segments.json
(ONLY=1,5 regenerates just those script lines).
"""
import difflib, json, os, re, subprocess, sys, tempfile
import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOICE = os.environ["VOICE"]
WHISPER = os.environ["WHISPER"].rstrip("/") + "/"
TAKES = int(os.environ.get("TAKES", "6"))
LENGTH = os.environ.get("LENGTH", "0.92")

# Spoken spelling for the TTS only (the on-screen text is unchanged).
SAY = {"bodybuilder": "bodibildeur", "Lis dix pages": "Lire dix pages", "Huit heures, pas sept.": "Huit heures, et pas sept."}
NUM = {"50": "cinquante", "2": "deux", "10": "dix", "12": "douze", "8": "huit", "7": "sept",
       "5": "cinq", "3": "trois"}


def norm(t):
    t = t.lower().replace("’", "'")
    t = re.sub(r"(\d+)\s*h\b", lambda m: NUM.get(m.group(1), m.group(1)) + " heures", t)
    t = re.sub(r"\d+", lambda m: NUM.get(m.group(0), m.group(0)), t)
    t = re.sub(r"[^\w' ]|-", " ", t)
    return t.split()


def wer(ref, hyp):
    r, h = norm(ref), norm(hyp)
    sm = difflib.SequenceMatcher(None, r, h)
    return 1 - sum(b.size for b in sm.get_matching_blocks()) / max(1, len(r))


def main():
    import sherpa_onnx
    rec = sherpa_onnx.OfflineRecognizer.from_whisper(
        encoder=WHISPER + "small-encoder.int8.onnx", decoder=WHISPER + "small-decoder.int8.onnx",
        tokens=WHISPER + "small-tokens.txt", language="fr", task="transcribe", num_threads=4)

    def transcribe(x, sr):
        if sr != 16000:
            n = int(len(x) * 16000 / sr)
            x = np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x)
        # Whisper tends to drop a first syllable that starts right at t=0: pad with silence.
        x = np.concatenate([np.zeros(8000), x, np.zeros(4800)])
        s = rec.create_stream()
        s.accept_waveform(16000, x.astype(np.float32))
        rec.decode_stream(s)
        return s.result.text.strip()

    lines = [l.strip() for l in open(os.path.join(ROOT, "audio-src/vo/script.txt")) if l.strip()]
    only = set(os.environ.get("ONLY", "").split(",")) - {""}
    path = os.path.join(ROOT, "audio-src/vo/segments.json")
    out = json.load(open(path)) if only and os.path.exists(path) else {}
    tmp = tempfile.mkdtemp()
    for li, line in enumerate(lines, 1):
        if only and str(li) not in only:
            continue
        out[str(li)] = []
        for si, text in enumerate(s for s in re.split(r"(?<=[.])\s+", line) if s.strip()):
            spoken = text
            for a, b in SAY.items():
                spoken = spoken.replace(a, b)
            takes = []
            for r in range(TAKES):
                fn = os.path.join(tmp, f"t{li}_{si}_{r}.wav")
                subprocess.run([sys.executable, "-m", "piper", "-m", VOICE, "--length-scale", LENGTH,
                                "-f", fn], input=spoken.encode(), capture_output=True, check=True)
                x, sr = sf.read(fn)
                idx = np.where(np.abs(x) > 0.01)[0]
                x = x[max(0, idx[0] - int(0.06 * sr)): idx[-1] + int(0.08 * sr)]
                hyp = transcribe(x, sr)
                takes.append((wer(text, hyp), len(x) / sr, x, sr, hyp))
            med = float(np.median([t[1] for t in takes]))
            takes.sort(key=lambda t: (round(t[0], 3), abs(t[1] - med)))
            w, d, x, sr, hyp = takes[0]
            f = int(0.005 * sr)
            x[:f] *= np.linspace(0, 1, f)
            x[-f:] *= np.linspace(1, 0, f)
            rel = f"audio-src/vo/seg{li}_{si}.wav"
            sf.write(os.path.join(ROOT, rel), x, sr)
            out[str(li)].append({"text": text, "file": rel, "dur": round(d, 3),
                                 "wer": round(w, 3), "asr": hyp})
            print(f"{li}.{si} wer {w:.2f} {d:5.2f}s  {text}  ->  {hyp}", flush=True)
    json.dump(dict(sorted(out.items(), key=lambda kv: int(kv[0]))), open(path, "w"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
