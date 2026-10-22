#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
CONFIG="${NARRATION_CONFIG:-assets/narration/ko.json}"
ENGINE="${1:-${TTS_ENGINE:-}}"
if [ -z "$ENGINE" ]; then
  ENGINE=$(node -e 'const fs=require("node:fs"); const c=JSON.parse(fs.readFileSync(process.argv[1], "utf8")); console.log(c.default_engine ?? "elevenlabs")' "$CONFIG")
fi
case "$ENGINE" in supertonic|elevenlabs) ;; *) echo "Unknown TTS_ENGINE: $ENGINE" >&2; exit 1 ;; esac
export UV_CACHE_DIR="$PWD/.cache/uv"
if [ ! -x .venv/bin/python ]; then
  uv venv --python "${TTS_PYTHON:-3.11}" .venv
fi
uv pip sync --python .venv/bin/python requirements-tts.lock
if [ "$ENGINE" = supertonic ]; then
  .venv/bin/python scripts/tts.py --download --engine "$ENGINE" --config "$CONFIG"
else
  echo "ElevenLabs processing dependencies ready. Generate voice clips with the connected Codex plugin, then import WAV files and manifest.json."
fi
