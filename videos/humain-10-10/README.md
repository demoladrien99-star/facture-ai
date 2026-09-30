# Deviens un humain 10/10 — TikTok 1080×1920, 60 i/s, ≈52 s

Livrable : `renders/video.mp4`.

## Rebuild

```bash
python3 tools/tighten_vo.py   # (optionnel) resserre les pauses des prises Piper
python3 tools/layout.py       # grille 110 BPM -> assets/timing.js + audio-src/timing.json
python3 tools/build_audio.py  # voix traitée, phonk, SFX -> assets/audio/*.wav
python3 tools/assemble.py     # index.html (hôtes des 7 scènes + pistes audio)
npx hyperframes@0.8.96 lint && npm run check
npx hyperframes@0.8.96 render --quality high --fps 240 --output renders/v-240.mp4
tools/finish.sh               # flou de mouvement tmix 4 -> 60 i/s, loudnorm -15 LUFS / -1.5 dBTP
```

Scènes : `compositions/s01…s07-*.html` (une sous-composition par plan, timeline GSAP en pause,
construite après `document.fonts.load`). Composants partagés (Text Rotate, Number Ticker,
Border Beam, ressort en forme fermée) : `assets/hf10.js`.

Voix : Piper TTS, voix française masculine `fr-gilles-low` (prises dans `audio-src/vo/`).
Python : `numpy`, `soundfile` ; ffmpeg requis.
