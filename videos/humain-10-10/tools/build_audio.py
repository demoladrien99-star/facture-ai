"""Deterministic audio build: VO bus, phonk bed (110 BPM) and SFX bus.

Everything is synthesized locally from audio-src/timing.json (tools/layout.py):
no network, fixed RNG seed, so the same inputs always give the same stems.

Outputs (48 kHz, 16-bit):
  assets/audio/vo.wav     narration, EQ + compression
  assets/audio/music.wav  dark phonk bed, ~10 dB under the voice (only with HF_MUSIC=1)
  assets/audio/sfx.wav    whooshes / impacts / pops / confirm, under the voice
"""
import json, os, subprocess, tempfile
import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SR = 48000
T = json.load(open(os.path.join(ROOT, "audio-src/timing.json")))
BEAT = T["beat"]
TOTAL = T["total"]
N = int(round(TOTAL * SR))
rng = np.random.default_rng(1010)
SC = {s["id"]: s for s in T["scenes"]}
# Final cut is voice + SFX only (no music bed); set HF_MUSIC=1 to rebuild the phonk stem.
WITH_MUSIC = os.environ.get("HF_MUSIC") == "1"


def db(x):
    return 10 ** (x / 20)


def rms_db(x):
    x = x[np.abs(x) > 1e-4]
    return 20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-12)


def place(buf, clip, t, gain=1.0):
    i = int(round(t * SR))
    if i >= len(buf):
        return
    j = min(len(buf), i + len(clip))
    buf[i:j] += clip[: j - i] * gain


def env_exp(n, decay):
    return np.exp(-np.arange(n) / (decay * SR))


def onepole_lp(x, fc):
    a = np.exp(-2 * np.pi * fc / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc
        y[i] = acc
    return y


def bandpass(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))


def ffmpeg(args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


# ---------------------------------------------------------------- VO bus
def build_vo():
    vo = np.zeros(N)
    for item in T["vo"]:
        with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
            ffmpeg(["-i", os.path.join(ROOT, item["file"]), "-ar", str(SR), "-ac", "1", tmp.name])
            x, _ = sf.read(tmp.name)
        f = int(0.004 * SR)
        x[:f] *= np.linspace(0, 1, f)
        x[-f:] *= np.linspace(1, 0, f)
        place(vo, x, item["at"])
    raw = os.path.join(ROOT, "audio-src/vo_raw.wav")
    sf.write(raw, vo, SR)
    out = os.path.join(ROOT, "assets/audio/vo.wav")
    chain = ("highpass=f=75,equalizer=f=220:t=q:w=1:g=-2,"
             "equalizer=f=3200:t=q:w=1.2:g=4,equalizer=f=7000:t=q:w=1:g=2,"
             "acompressor=threshold=-22dB:ratio=4:attack=4:release=90:makeup=5,"
             "alimiter=limit=0.8")
    ffmpeg(["-i", raw, "-af", chain, "-ar", str(SR), "-c:a", "pcm_s16le", out])
    os.remove(raw)
    y, _ = sf.read(out)
    return y


# ---------------------------------------------------------------- instruments
def kick():
    n = int(0.42 * SR)
    t = np.arange(n) / SR
    f = 45 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    k = np.sin(ph) * env_exp(n, 0.16)
    k[: int(0.003 * SR)] += rng.standard_normal(int(0.003 * SR)) * 0.4
    return np.tanh(k * 2.2) * 0.9


def b808(freq, length, slide_to=None):
    n = int(length * SR)
    t = np.arange(n) / SR
    f = np.full(n, freq)
    if slide_to:
        s = int(n * 0.55)
        f[s:] = freq + (slide_to - freq) * (1 - np.exp(-(t[s:] - t[s]) * 30))
    ph = 2 * np.pi * np.cumsum(f) / SR
    e = np.minimum(1, t / 0.005) * np.exp(-t / (length * 0.7))
    return np.tanh(np.sin(ph) * e * 3.0) * 0.55


def clap():
    n = int(0.22 * SR)
    x = bandpass(rng.standard_normal(n), 900, 5200)
    e = np.zeros(n)
    for off in (0, 0.009, 0.018):
        i = int(off * SR)
        e[i:] += env_exp(n - i, 0.012 if off < 0.018 else 0.07)
    return x * e * 0.35


def hat(open_=False):
    n = int((0.18 if open_ else 0.05) * SR)
    x = bandpass(rng.standard_normal(n), 7000, 16000)
    return x * env_exp(n, 0.06 if open_ else 0.012) * (0.22 if open_ else 0.16)


def cowbell(freq, length=0.16):
    n = int(length * SR)
    t = np.arange(n) / SR
    sq = np.sign(np.sin(2 * np.pi * freq * t)) + np.sign(np.sin(2 * np.pi * freq * 1.48 * t))
    x = bandpass(sq, 350, 4200)
    return x * env_exp(n, 0.06) * 0.12


# F minor phonk riff (16th grid, 2 bars); None = rest
F4 = 349.23
NOTE = {n: F4 * 2 ** (s / 12) for n, s in
        {"F": 0, "Ab": 3, "Bb": 5, "C": 7, "Db": 8, "Eb": 10, "F5": 12}.items()}
RIFF = ["F5", None, "C", None, "Db", None, "C", "Ab", None, "F", None, "Ab", "C", None, "Db", None,
        "F5", None, "C", None, "Eb", None, "Db", "C", None, "Ab", None, "C", "Bb", None, "Ab", None]
BASS = [(0, 43.65, 1.5, None), (6, 43.65, 0.5, None), (8, 51.91, 1.4, None),
        (14, 65.41, 0.9, 58.27)]  # (16th index in 2 bars / 2, freq, beats, slide)


def build_music():
    m = np.zeros(N)
    six = BEAT / 4
    total_beats = int(round(TOTAL / BEAT))
    cta = int(round(SC["s07-cta"]["start"] / BEAT))
    recap = int(round(SC["s06-recap"]["start"] / BEAT))
    mind = int(round(SC["s05-meditation-entourage"]["start"] / BEAT))
    K, C = kick(), clap()
    for b in range(total_beats):
        t = b * BEAT
        in_bar = b % 4
        drums = b < cta - 1  # one-beat stop before the CTA, then the drop-out
        if drums:
            place(m, K, t)
            if in_bar == 2 and b % 8 == 6:
                place(m, K, t + 2 * six, 0.8)
            if in_bar in (1, 3):
                place(m, C, t)
            for s in range(4 if b >= recap or b % 8 == 7 else 2):
                step = six if (b >= recap or b % 8 == 7) else 2 * six
                place(m, hat(), t + s * step, 0.7 + 0.3 * (s % 2 == 0))
            if b >= mind and in_bar == 3:
                place(m, hat(True), t + 2 * six)
        # 808 line, restarts every 2 bars
        if b < cta - 1 and b % 8 == 0:
            for idx, f, beats, slide in BASS:
                fr = f * (2 ** (-2 / 12) if b >= mind and (b // 8) % 2 else 1)
                place(m, b808(fr, beats * BEAT, slide), t + idx * 2 * six)
    # cowbell riff everywhere; low-passed and softer under the CTA
    bell = np.zeros(N)
    step = 0
    t = 0.0
    while t < TOTAL:
        nme = RIFF[step % len(RIFF)]
        if nme:
            place(bell, cowbell(NOTE[nme]), t)
        step += 1
        t = step * six
    cta_t = SC["s07-cta"]["start"]
    ci = int(cta_t * SR)
    bell[ci:] = onepole_lp(bell[ci:], 1200) * 1.6
    m += bell
    # sub drone under the CTA drop-out so the bed "falls" rather than stops
    n = N - ci
    tt = np.arange(n) / SR
    drone = (np.sin(2 * np.pi * 43.65 * tt) * 0.25 + np.sin(2 * np.pi * 87.3 * tt) * 0.08)
    drone *= np.minimum(1, tt / 0.4)
    m[ci:] += drone
    # 1 s fade at the very end
    f = int(1.0 * SR)
    m[-f:] *= np.linspace(1, 0, f) ** 1.5
    return np.tanh(m * 1.1) * 0.8


# ---------------------------------------------------------------- SFX
def whoosh(length=0.45, up=True, gain=1.0):
    n = int(length * SR)
    x = rng.standard_normal(n)
    t = np.arange(n) / n
    fc = (600 + 5000 * t) if up else (5600 - 5000 * t)
    y = np.zeros(n)
    acc = 0.0
    for i in range(n):
        a = np.exp(-2 * np.pi * fc[i] / SR)
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    y = y - onepole_lp(y, 250)
    e = np.sin(np.pi * t) ** 2
    return y * e * 0.9 * gain


def impact():
    n = int(0.7 * SR)
    t = np.arange(n) / SR
    f = 38 + 70 * np.exp(-t * 18)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(n, 0.22)
    x += onepole_lp(rng.standard_normal(n), 400) * env_exp(n, 0.04) * 2.5
    return np.tanh(x * 1.8) * 0.7


def pop():
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    f = 900 * np.exp(-t * 25) + 320
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(n, 0.03) * 0.5


def tick():
    n = int(0.05 * SR)
    return bandpass(rng.standard_normal(n), 2000, 9000) * env_exp(n, 0.008) * 0.5


def confirm():
    out = np.zeros(int(0.9 * SR))
    for k, (f, t0) in enumerate(((698.46, 0.0), (1046.5, 0.11))):
        n = len(out) - int(t0 * SR)
        t = np.arange(n) / SR
        tone = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)) * env_exp(n, 0.25)
        out[int(t0 * SR):] += tone * np.minimum(1, t / 0.004) * 0.3
    return out


def vo_at(scene, i, off=0.0):
    s = SC[scene]
    return s["start"] + s["sentences"][i]["start"] + off


def beat_at(scene, n):
    return SC[scene]["start"] + n * BEAT


# Cue sheet: mirrors the reveal times authored in compositions/*.html
# (each scene reads the same HF_TIMING vo starts / beat offsets).
def cues():
    W, I, P, Tk, C = "whoosh", "impact", "pop", "tick", "confirm"
    s1, s2, s3, s4, s5, s6, s7 = (s["id"] for s in T["scenes"])
    return [
        (W, beat_at(s1, 0)), (W, beat_at(s1, 1)), (I, beat_at(s1, 1) + 0.12),
        (W, beat_at(s1, 3)), (Tk, beat_at(s1, 4)), (Tk, beat_at(s1, 5)), (Tk, beat_at(s1, 6)),
        (W, beat_at(s2, 0)), (W, vo_at(s2, 1)), (I, vo_at(s2, 1, 0.6)),
        (W, vo_at(s2, 2)), (W, vo_at(s2, 3)),
        (P, vo_at(s3, 0)), (W, vo_at(s3, 1)), (P, vo_at(s3, 2)), (W, vo_at(s3, 3)),
        (I, vo_at(s3, 4)),
        (W, vo_at(s4, 0)), (I, vo_at(s4, 0, 0.12)), (W, vo_at(s4, 0, 0.55)),
        (W, vo_at(s4, 1)), (I, vo_at(s4, 2, 1.0)), (W, vo_at(s4, 2, 1.25)),
        (P, vo_at(s5, 0)), (W, vo_at(s5, 1)), (W, vo_at(s5, 2)),
        (P, vo_at(s5, 3)), (W, vo_at(s5, 4)), (W, vo_at(s5, 5)), (W, vo_at(s5, 6)),
        (W, beat_at(s6, 0)), (P, beat_at(s6, 1)), (P, beat_at(s6, 2)), (P, beat_at(s6, 3)),
        (P, beat_at(s6, 4)),
        (W, vo_at(s7, 0)), (I, vo_at(s7, 0, 0.12)), (W, vo_at(s7, 1)), (C, vo_at(s7, 2)),
    ]


def build_sfx():
    fx = np.zeros(N)
    bank = {"whoosh": lambda: whoosh(0.42, gain=0.8), "impact": impact, "pop": pop,
            "tick": tick, "confirm": confirm}
    for name, t in cues():
        clip = bank[name]()
        lead = 0.3 if name == "whoosh" else 0.0  # whoosh peaks on the reveal
        place(fx, clip, max(0.0, t - lead))
    return fx


def main():
    os.makedirs(os.path.join(ROOT, "assets/audio"), exist_ok=True)
    vo = build_vo()
    vo_level = rms_db(vo)
    stems = {}
    if WITH_MUSIC:
        music = build_music()
        stems["music"] = music * db(vo_level - 10 - rms_db(music))
    sfx = build_sfx()
    stems["sfx"] = sfx * db(vo_level - 12 - rms_db(sfx))
    for name, x in stems.items():
        sf.write(os.path.join(ROOT, f"assets/audio/{name}.wav"), np.clip(x, -1, 1), SR,
                 subtype="PCM_16")
    print(f"vo {vo_level:.1f} dBFS rms | " + " | ".join(
        f"{k} {rms_db(v):.1f}" for k, v in stems.items()) + f" | {TOTAL:.2f}s")


if __name__ == "__main__":
    main()
