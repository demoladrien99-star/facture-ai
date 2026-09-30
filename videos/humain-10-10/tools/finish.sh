#!/usr/bin/env bash
# Post: 240 fps render -> 4-frame motion blur -> 60 fps, two-pass loudnorm -15 LUFS / -1.5 dBTP.
set -euo pipefail
cd "$(dirname "$0")/.."
IN=renders/v-240.mp4
M=$(ffmpeg -hide_banner -i "$IN" -af loudnorm=I=-15:TP=-1.5:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
g() { echo "$M" | python3 -c "import json,sys;print(json.load(sys.stdin)['$1'])"; }
LN="loudnorm=I=-15:TP=-1.5:LRA=11:measured_I=$(g input_i):measured_TP=$(g input_tp):measured_LRA=$(g input_lra):measured_thresh=$(g input_thresh):offset=$(g target_offset):linear=true"
ffmpeg -y -loglevel error -i "$IN" \
  -vf "tmix=frames=4:weights='1 1 1 1',fps=60" \
  -af "$LN,aresample=48000" \
  -c:v libx264 -crf 16 -preset slow -pix_fmt yuv420p -movflags +faststart \
  -c:a aac -b:a 256k renders/video.mp4
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate:format=duration -of compact renders/video.mp4
ffmpeg -hide_banner -i renders/video.mp4 -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):"
