#!/usr/bin/env python3
"""Rebuild the standalone opening mix from imported single-take narration.

No network access or generation is performed. Requires Python 3 and FFmpeg.
"""
import argparse
import array
import hashlib
import json
import math
from pathlib import Path
import subprocess
import wave

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args):
    return subprocess.run(args, capture_output=True, text=True, check=True)


def loudness(path):
    result = run(["ffmpeg", "-hide_banner", "-i", str(path), "-af",
        "loudnorm=I=-17:TP=-1.8:LRA=7:print_format=json", "-f", "null", "-"])
    return json.JSONDecoder().raw_decode(result.stderr[result.stderr.rfind("{\n"):])[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "out/opening-v2")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    conf = read(HERE / "narration/ko.json")
    manifest = read(HERE / "narration/manifest.json")
    duration = float(conf["duration_seconds"])
    assert len(conf["clips"]) == len(manifest["clips"]) == 9
    assert manifest["transcript_verification"]["all_nine_sentences_covered"]
    master = HERE / "narration/take.wav"
    assert sha(master) == manifest["source_take"]["sha256"]
    with wave.open(str(master), "rb") as w:
        assert (w.getframerate(), w.getnchannels(), w.getsampwidth()) == (48000, 1, 2)
        pcm = w.readframes(w.getnframes())
    timeline = array.array("h", [0]) * round(duration * 48000)
    verified = []
    for i, clip in enumerate(manifest["clips"]):
        source = HERE / "narration" / clip["file"]
        assert sha(source) == clip["sha256"]
        with wave.open(str(source), "rb") as w:
            source_pcm = w.readframes(w.getnframes())
        a, b = clip["source_start_sample"], clip["source_end_sample"]
        assert source_pcm == pcm[a * 2:b * 2]
        assert 0 <= clip["timeline_start_seconds"] < clip["timeline_end_seconds"] <= duration
        assert clip["timeline_end_seconds"] <= clip["end_ms"] / 1000
        ta, tb = clip["timeline_trim_start_sample"], clip["timeline_trim_end_sample"]
        tempo = float(clip["tempo_ratio"])
        assert 1. <= tempo <= 1.1, "Narration may only receive a mild tempo adjustment when its scene slot requires it."
        delay_samples = round(clip["timeline_start_seconds"] * 48000)
        values = array.array("h", source_pcm[ta * 2:tb * 2])
        if tempo > 1.:
            tempo_source = out / f"tempo-source{clip['id']}.wav"
            tempo_output = out / f"tempo-cut{clip['id']}.wav"
            with wave.open(str(tempo_source), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(48000)
                w.writeframes(values.tobytes())
            run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-i", str(tempo_source), "-af", f"atempo={tempo:.12f}",
                "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(tempo_output)])
            with wave.open(str(tempo_output), "rb") as w:
                values = array.array("h", w.readframes(w.getnframes()))
        assert delay_samples + len(values) <= len(timeline)
        assert delay_samples + len(values) <= round(clip["end_ms"] / 1000 * 48000)
        timeline[delay_samples:delay_samples + len(values)] = values
        verified.append({"id": clip["id"], "exact_source_pcm": True,
            "tempo_ratio": tempo, "start_seconds": clip["timeline_start_seconds"],
            "planned_end_seconds": clip["timeline_end_seconds"],
            "end_seconds": (delay_samples + len(values)) / 48000})
    raw = out / "narration-raw.wav"
    with wave.open(str(raw), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(48000)
        w.writeframes(timeline.tobytes())
    measured = loudness(raw)
    normalizer = (f"loudnorm=I=-17:TP=-1.8:LRA=7:measured_I={measured['input_i']}:"
        f"measured_TP={measured['input_tp']}:measured_LRA={measured['input_lra']}:"
        f"measured_thresh={measured['input_thresh']}:offset={measured['target_offset']}:linear=true")
    voice = out / "narration.wav"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(raw),
        "-af", "highpass=f=70," + normalizer, "-t", str(duration), "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", str(voice)])
    bgm = HERE / "narration/bgm/music.mp3"
    bgm_metadata = read(HERE / "narration/bgm/provenance.json")
    assert sha(bgm) == bgm_metadata["sha256"]
    assert sha(HERE / "narration/bgm/license.html") == bgm_metadata["license"]["proof_sha256"]
    bgm_conf = conf["bgm"]
    fade_out = duration - bgm_conf["fade_out_seconds"]
    graph = (f"[0:a]asplit=2[sidechain][speech];"
        f"[1:a]atrim=start={bgm_conf['start_seconds']}:duration={duration},asetpts=PTS-STARTPTS,"
        f"aresample=48000,highpass=f=70,lowpass=f=10000,volume={bgm_conf['gain']},"
        f"afade=t=in:st=0:d={bgm_conf['fade_in_seconds']},"
        f"afade=t=out:st={fade_out}:d={bgm_conf['fade_out_seconds']}[music];"
        "[music][sidechain]sidechaincompress=threshold=0.015:ratio=5:attack=20:release=320:makeup=1[ducked];"
        f"[speech][ducked]amix=inputs=2:normalize=0:dropout_transition=0,"
        f"alimiter=limit=0.794328:level=false,atrim=duration={duration}[mix]")
    final = out / "audio.wav"
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(voice),
        "-i", str(bgm), "-filter_complex", graph, "-map", "[mix]", "-ar", "48000",
        "-ac", "2", "-t", str(duration), "-c:a", "pcm_s16le", str(final)])
    run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(final), "-f", "null", "-"])
    with wave.open(str(final), "rb") as w:
        metadata = {"sample_rate": w.getframerate(), "channels": w.getnchannels(),
            "sample_width_bytes": w.getsampwidth(), "samples": w.getnframes(),
            "duration_seconds": w.getnframes() / w.getframerate()}
        assert metadata["samples"] == round(duration * 48000)
        assert (metadata["sample_rate"], metadata["channels"]) == (48000, 2)
    report = {"status": "PASS", "output": str(final.relative_to(ROOT)) if final.is_relative_to(ROOT) else str(final),
        "sha256": sha(final), "metadata": metadata, "decode": "PASS",
        "source_master_sha256": sha(master), "narration_config_sha256": sha(HERE / "narration/ko.json"),
        "manifest_sha256": sha(HERE / "narration/manifest.json"),
        "single_take": True, "all_nine_sentences_covered": True, "safe_boundaries": 8,
        "pronunciation_map": manifest["pronunciation_map"],
        "pronunciation_verification": manifest["pronunciation_verification"],
        "clips": verified, "narration_loudness_source": measured,
        "narration_loudness_final": loudness(voice), "mix_loudness_final": loudness(final),
        "bgm": {"title": bgm_metadata["title"], "artist": bgm_metadata["artist"],
            "sha256": sha(bgm), "license": bgm_metadata["license"], "settings": bgm_conf,
            "sidechain_ducking": {"threshold": .015, "ratio": 5, "attack_ms": 20, "release_ms": 320}},
        "timing_adjustment": manifest["timing_adjustment"],
        "limits": ["Local Whisper sentence coverage and waveform cuts are verified; ASR spelling and timestamps are approximate.",
            "Creative Studio does not expose saved stability/similarity settings; the default values were used and cannot be independently confirmed.",
            "This report validates the audio mix only. Final MP4 mux, video stream, playback and visual checks remain separate."]}
    (out / "audio-validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    (HERE / "narration/mix.wav").write_bytes(final.read_bytes())
    print(json.dumps({"status": report["status"], "output": str(final), "metadata": metadata,
        "integrated_lufs": report["mix_loudness_final"]["input_i"],
        "true_peak_dbtp": report["mix_loudness_final"]["input_tp"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
