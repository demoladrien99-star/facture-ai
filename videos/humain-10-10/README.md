# Deviens un humain 10/10 — TikTok 1080×1920, 60 i/s, ≈57 s

Livrable : `renders/video.mp4`.

## Rebuild

```bash
VOICE=…/fr_FR-tom-medium.onnx WHISPER=…/sherpa-onnx-whisper-small \
  python3 tools/make_vo.py     # voix : 6 prises/phrase, garde la plus intelligible (ASR Whisper)
python3 tools/layout.py       # grille 110 BPM -> assets/timing.js + audio-src/timing.json
python3 tools/build_audio.py  # voix traitée + SFX -> assets/audio/*.wav (HF_MUSIC=1 : ajoute la phonk)
python3 tools/assemble.py     # index.html (hôtes des 7 scènes + pistes audio)
npx hyperframes@0.8.96 lint && npm run check
npx hyperframes@0.8.96 render --quality high --fps 240 --output renders/v-240.mp4
tools/finish.sh               # flou de mouvement tmix 4 -> 60 i/s, loudnorm -15 LUFS / -1.5 dBTP
```

Scènes : `compositions/s01…s07-*.html` (une sous-composition par plan, timeline GSAP en pause,
construite après `document.fonts.load`). Composants partagés (Text Rotate, Number Ticker,
Border Beam, ressort en forme fermée) : `assets/hf10.js`.

Voix : Piper TTS `fr_FR-tom-medium` (français, masculine), choisie parce qu'elle a le meilleur score
d'intelligibilité mesuré par Whisper. Chaque phrase est vérifiée par transcription automatique
(`asr` et `wer` dans `audio-src/vo/segments.json`). Modèles : releases GitHub `k2-fsa/sherpa-onnx`
(`tts-models/vits-piper-fr_FR-tom-medium`, `asr-models/sherpa-onnx-whisper-small`).
Python : `piper-tts`, `sherpa-onnx`, `numpy`, `soundfile` ; ffmpeg requis.
