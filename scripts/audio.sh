#!/bin/bash
# Builds Supertonic narration or imports ElevenLabs plugin audio, mixes with BGM,
# then muxes the result onto out/video_silent.mp4.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -x .venv/bin/python ]; then
  echo "Run npm run tts:setup first." >&2; exit 1
fi
CONFIG="${NARRATION_CONFIG:-assets/narration/ko.json}"
ENGINE="${TTS_ENGINE:-$(.venv/bin/python -c 'import json,sys; print(json.load(open(sys.argv[1])).get("default_engine", "elevenlabs"))' "$CONFIG")}"
case "$ENGINE" in supertonic|elevenlabs) ;; *) echo "Unknown TTS_ENGINE: $ENGINE" >&2; exit 1 ;; esac
A="out/audio/$ENGINE"; mkdir -p "$A"
.venv/bin/python scripts/tts.py --engine "$ENGINE" --config "$CONFIG" --output-dir "$A"
IFS='|' read -r BGM BGM_START BGM_GAIN BGM_END_GAIN < <(.venv/bin/python - "$CONFIG" <<'PY'
import json, sys
bgm = json.load(open(sys.argv[1])).get("bgm", {})
path = bgm.get("file", "assets/bgm/mixkit-close-up-1167.mp3")
start = float(bgm.get("start_seconds", 2))
gain = float(bgm.get("gain", 0.42))
ending_gain = float(bgm.get("ending_gain", 0.85))
if not start >= 0 or not 0 <= gain <= 1 or not 0 <= ending_gain <= 1:
    raise ValueError("Invalid BGM offset or gain")
print(path, start, gain, ending_gain, sep="|")
PY
)
if [ ! -f "$BGM" ]; then echo "BGM missing: $BGM" >&2; exit 1; fi
DUR=$(.venv/bin/python -c 'import json,sys; print(json.load(open(sys.argv[1]))["duration_seconds"])' "$CONFIG")
OUT="out/smart-process-architecture-ai-agent-$ENGINE.mp4"

inputs=(); chain=""; mixin=""
while IFS='|' read -r n at; do
  inputs+=(-i "$A/vo$n.wav")
  chain+="[$((n-1)):a]aresample=48000,aformat=channel_layouts=stereo,adelay=${at}:all=1[v$n];"
  mixin+="[v$n]"
done < <(.venv/bin/python -c 'import json,sys; [print(str(c["id"])+"|"+str(c["start_ms"])) for c in json.load(open(sys.argv[1]))["clips"]]' "$CONFIG")
N=$((${#inputs[@]}/2))

ffmpeg -y -loglevel error "${inputs[@]}" \
  -filter_complex "${chain}${mixin}amix=inputs=$N:normalize=0,loudnorm=I=-17:TP=-2:LRA=11,aresample=48000,asetpts=N/SR/TB,apad=whole_dur=${DUR},atrim=0:${DUR}[vo]" \
  -map "[vo]" -ar 48000 "$A/narration.wav"

W="anoisesrc=color=pink:duration=0.8:sample_rate=48000:amplitude=0.6,highpass=f=500,lowpass=f=3500,afade=t=in:d=0.45:curve=qsin,afade=t=out:st=0.45:d=0.35,aformat=channel_layouts=stereo"
ffmpeg -y -loglevel error -i "$A/narration.wav" -ss "$BGM_START" -t "$DUR" -i "$BGM" \
  -f lavfi -i "$W" -f lavfi -i "$W" -f lavfi -i "$W" -f lavfi -i "$W" \
  -filter_complex "
    [0:a]highpass=f=70,asplit[vo][key];
    [1:a]aresample=48000,volume='${BGM_GAIN}+(${BGM_END_GAIN}-${BGM_GAIN})*clip((t-13.6)/0.9,0,1)':eval=frame,afade=t=in:d=0.4,afade=t=out:st=16.2:d=1.8[bg];
    [bg][key]sidechaincompress=threshold=0.03:ratio=3:attack=15:release=350[bgd];
    [2:a]adelay=2600:all=1,volume=0.10[w1];[3:a]adelay=5600:all=1,volume=0.10[w2];
    [4:a]adelay=9600:all=1,volume=0.10[w3];[5:a]adelay=13600:all=1,volume=0.12[w4];
    [bgd][vo][w1][w2][w3][w4]amix=inputs=6:normalize=0,alimiter=limit=0.89:latency=1,asetpts=N/SR/TB,apad=whole_dur=${DUR},atrim=0:${DUR}[out]" \
  -map "[out]" -ar 48000 "$A/mix.wav"

ffmpeg -y -loglevel error -i out/video_silent.mp4 -i "$A/mix.wav" -c:v copy -c:a aac -b:a 256k -movflags +faststart "$OUT"
echo "wrote $OUT"
