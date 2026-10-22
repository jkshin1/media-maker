#!/usr/bin/env python3
"""Import a verified continuous ElevenLabs take and mix the full production."""
import argparse
import copy
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command, capture=False):
    print("running " + Path(command[0]).name, flush=True)
    return subprocess.run(command, cwd=ROOT, check=True, text=True,
                          capture_output=capture)


def probe(path):
    result = run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)], True)
    return json.loads(result.stdout)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stream_hash(path):
    result = run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:v:0", "-c", "copy",
                  "-f", "hash", "-hash", "sha256", "-"], True)
    return result.stdout.strip()


def audio_stream_hash(path, decoded=False):
    codec = "pcm_s16le" if decoded else "copy"
    result = run(["ffmpeg", "-v", "error", "-i", str(path), "-map", "0:a:0", "-c:a", codec,
                  "-f", "hash", "-hash", "sha256", "-"], True)
    return result.stdout.strip()


def preserve_audio(args, config, storyboard, silent, render_report_path, out):
    """Use a verified prior final's AAC stream for a visual-only revision."""
    source = args.preserve_audio_from.resolve()
    source_report_path = source.parent / "audio-validation.json"
    source_report = json.loads(source_report_path.read_text())
    duration = float(config["duration_seconds"])
    expected_frames = round(duration * int(storyboard.get("fps", 30)))
    if (source_report.get("status") != "PASS"
            or source_report.get("sha256") != sha256(source)
            or source_report.get("narration_config_sha256") != sha256(args.config)
            or source_report.get("import_manifest_sha256") != sha256(args.import_audio_dir / "manifest.json")
            or abs(float(source_report.get("duration_seconds", 0)) - duration) > 1e-6):
        raise ValueError("Prior audio verification or current narration inputs differ")
    if abs(float(source_report["bgm"]["ending_gain_start_seconds"]) - float(storyboard["ending"]["start"])) > 1e-6:
        raise ValueError("Ending position has changed; prior audio cannot be preserved")
    if args.ending_start is not None and abs(args.ending_start - float(storyboard["ending"]["start"])) > 1e-6:
        raise ValueError("Cannot alter ending audio gain when preserving the prior audio")
    source_probe = probe(source)
    source_audio = next(stream for stream in source_probe["streams"] if stream["codec_type"] == "audio")
    if (source_audio.get("codec_name") != "aac" or source_audio.get("sample_rate") != "48000"
            or source_audio.get("channels") != 2
            or abs(float(source_audio.get("duration", 0)) - duration) > 1 / int(storyboard.get("fps", 30))):
        raise ValueError("Prior final audio format or duration differs")
    prior_encoded_hash = audio_stream_hash(source)
    prior_pcm_hash = audio_stream_hash(source, decoded=True)
    prior_mix = source.parent / "audio/mix.wav"
    active_mix = out / "audio/mix.wav"
    if not prior_mix.is_file() or not active_mix.is_file() or sha256(prior_mix) != sha256(active_mix):
        raise ValueError("Original mix WAV has changed or is missing")
    final_output = out / "rd-process-ai-fast-track.mp4"
    final = out / "rd-process-ai-fast-track.partial.mp4"
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), "-i", str(source),
         "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "copy",
         "-movflags", "+faststart", str(final)])
    metadata = probe(final)
    video = next(stream for stream in metadata["streams"] if stream["codec_type"] == "video")
    audio = next(stream for stream in metadata["streams"] if stream["codec_type"] == "audio")
    if ((video["width"], video["height"], video["r_frame_rate"]) !=
            (int(storyboard.get("width", 1920)), int(storyboard.get("height", 1080)), f"{int(storyboard.get('fps', 30))}/1")
            or int(video.get("nb_frames", 0)) != expected_frames
            or abs(float(metadata["format"]["duration"]) - duration) > 1 / int(storyboard.get("fps", 30))
            or audio.get("sample_rate") != "48000" or audio.get("channels") != 2
            or abs(float(audio.get("duration", 0)) - duration) > 1 / int(storyboard.get("fps", 30))):
        raise ValueError("Preserved-audio final media validation failed")
    run(["ffmpeg", "-v", "error", "-i", str(final), "-f", "null", "-"])
    video_hash, final_video_hash = stream_hash(silent), stream_hash(final)
    encoded_hash = audio_stream_hash(final)
    pcm_hash = audio_stream_hash(final, decoded=True)
    if video_hash != final_video_hash or encoded_hash != prior_encoded_hash or pcm_hash != prior_pcm_hash:
        raise ValueError("Copied video or preserved audio differs from its verified source")
    final.replace(final_output)
    report = copy.deepcopy(source_report)
    report.update({"status": "PASS", "file": str(final_output.relative_to(ROOT)), "sha256": sha256(final_output),
                   "video_stream_sha256": final_video_hash, "video_stream_copy_verified": True,
                   "decode_verified": True, "audio_regenerated": False, "bgm_regenerated": False,
                   "audio_stream_copy_verified": True, "audio_pcm_identity_verified": True,
                   "audio_encoded_stream_sha256": encoded_hash, "audio_decoded_pcm_sha256": pcm_hash,
                   "preserved_audio_source": str(source.relative_to(ROOT)),
                   "preserved_audio_source_sha256": sha256(source), "mix_wav_sha256": sha256(active_mix),
                   "storyboard_sha256": sha256(args.storyboard),
                   "html_sha256": sha256(ROOT / "production/src/index.html"),
                   "narration_config_sha256": sha256(args.config),
                   "render_validation_sha256": sha256(render_report_path)})
    (out / "audio-validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("wrote " + str(final_output) + "; prior AAC and decoded PCM are identical", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "production/narration/ko.json")
    parser.add_argument("--import-audio-dir", type=Path, default=ROOT / "production/narration/elevenlabs")
    parser.add_argument("--storyboard", type=Path, default=ROOT / "production/storyboard.json")
    parser.add_argument("--ending-start", type=float, help="Override the storyboard ending start for BGM gain")
    parser.add_argument("--check-inputs", action="store_true", help="Validate source paths and timing without rendering or importing")
    parser.add_argument("--preserve-audio-from", type=Path, help="Copy AAC from a verified prior final for a visual-only revision; do not regenerate speech or BGM")
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    storyboard = json.loads(args.storyboard.read_text())
    duration = float(config["duration_seconds"])
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("Invalid production duration")
    if config.get("default_engine") != "elevenlabs" or config["elevenlabs"].get("generation_mode") != "single_take":
        raise ValueError("Full production requires the saved ElevenLabs single_take default")
    storyboard_duration = float(storyboard["duration_seconds"])
    width = int(storyboard.get("width", 1920))
    height = int(storyboard.get("height", 1080))
    fps = int(storyboard.get("fps", 30))
    if not math.isfinite(storyboard_duration) or abs(storyboard_duration - duration) > 1e-6:
        raise ValueError("Storyboard and narration durations differ")
    if min(width, height, fps) <= 0 or abs(duration * fps - round(duration * fps)) > 1e-6:
        raise ValueError("Invalid storyboard dimensions or frame timing")
    ending_start = float(args.ending_start if args.ending_start is not None else storyboard["ending"]["start"])
    if not 0 <= ending_start < duration:
        raise ValueError("Ending gain start must be inside the video")
    clips = config["clips"]
    previous_end = 0
    for index, clip in enumerate(clips, 1):
        if (clip["id"] != index or not clip["text"].strip()
                or not previous_end <= clip["start_ms"] < clip["end_ms"] <= duration * 1000):
            raise ValueError(f"Invalid production clip timing: {clip}")
        previous_end = clip["end_ms"]
    if not clips:
        raise ValueError("Production requires narration clips")
    bgm = config["bgm"]
    bgm_path = ROOT / bgm["file"]
    bgm_start = float(bgm.get("start_seconds", 0))
    gain = float(bgm.get("gain", 0.3))
    ending_gain = float(bgm.get("ending_gain", 0.6))
    if not (math.isfinite(bgm_start) and bgm_start >= 0 and 0 <= gain <= 1 and 0 <= ending_gain <= 1):
        raise ValueError("Invalid BGM offset or gains")
    out = ROOT / "out/production"
    audio_dir = out / "audio"
    silent = out / "video_silent.mp4"
    render_report_path = out / "render-validation.json"
    source_paths = [silent, render_report_path, bgm_path, args.import_audio_dir / "take.wav", args.import_audio_dir / "manifest.json"]
    source_paths += [args.import_audio_dir / f"vo{clip['id']}.wav" for clip in clips]
    missing = [str(path) for path in source_paths if not path.is_file()]
    if missing:
        raise FileNotFoundError("Production sources are not ready: " + ", ".join(missing))
    render_report = json.loads(render_report_path.read_text())
    if (render_report.get("status") != "PASS"
            or render_report.get("storyboard_sha256") != sha256(args.storyboard)
            or render_report.get("html_sha256") != sha256(ROOT / "production/src/index.html")):
        raise ValueError("Silent render verification does not match the current storyboard and HTML")
    video_probe = probe(silent)
    video_stream = next(stream for stream in video_probe["streams"] if stream["codec_type"] == "video")
    expected_frames = round(duration * fps)
    if abs(float(video_probe["format"]["duration"]) - duration) > 1 / fps:
        raise ValueError("Silent production duration differs from narration config")
    if (video_stream["width"], video_stream["height"], video_stream["r_frame_rate"]) != (width, height, f"{fps}/1"):
        raise ValueError("Silent production dimensions or fps differ from storyboard")
    if int(video_stream.get("nb_frames", 0)) != expected_frames:
        raise ValueError(f"Silent production must have {expected_frames} video frames")
    if args.check_inputs:
        print(json.dumps({"status": "SOURCES_PRESENT", "duration_seconds": duration, "clips": len(clips),
                          "frames": expected_frames, "ending_gain_start_seconds": ending_start}, indent=2))
        return
    if args.preserve_audio_from:
        preserve_audio(args, config, storyboard, silent, render_report_path, out)
        return
    audio_dir.mkdir(parents=True, exist_ok=True)
    run([sys.executable, str(ROOT / "scripts/tts.py"), "--engine", "elevenlabs", "--config", str(args.config),
         "--import-audio-dir", str(args.import_audio_dir), "--output-dir", str(audio_dir)])
    # One loudness measurement across the entire placed narration preserves its relative delivery.
    inputs = []
    filters = []
    labels = []
    for index, clip in enumerate(clips):
        inputs += ["-i", str(audio_dir / f"vo{clip['id']}.wav")]
        label = f"v{index}"
        filters.append(f"[{index}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={clip['start_ms']}:all=1[{label}]")
        labels.append(f"[{label}]")
    base = ";".join(filters) + ";" + "".join(labels) + f"amix=inputs={len(clips)}:normalize=0,highpass=f=70"
    measured = run(["ffmpeg", "-hide_banner", "-y", *inputs, "-filter_complex",
                    base + ",loudnorm=I=-17:TP=-2:LRA=11:print_format=json[vo]", "-map", "[vo]", "-f", "null", "-"], True)
    matches = re.findall(r"\{\s*\"input_i\"[\s\S]*?\}", measured.stderr)
    if not matches:
        raise RuntimeError("ffmpeg loudness measurement did not return JSON")
    loudness = json.loads(matches[-1])
    if not all(math.isfinite(float(loudness[key])) for key in
               ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")):
        raise ValueError("Narration loudness measurement is not finite")
    norm = (f"loudnorm=I=-17:TP=-2:LRA=11:measured_I={loudness['input_i']}:"
            f"measured_TP={loudness['input_tp']}:measured_LRA={loudness['input_lra']}:"
            f"measured_thresh={loudness['input_thresh']}:offset={loudness['target_offset']}:linear=true")
    narration = audio_dir / "narration.wav"
    run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex",
         base + f",{norm},aresample=48000,asetpts=N/SR/TB,apad=whole_dur={duration},atrim=0:{duration}[vo]",
         "-map", "[vo]", "-ar", "48000", "-c:a", "pcm_s16le", str(narration)])
    bgm_duration = float(probe(bgm_path)["format"]["duration"]) - bgm_start
    if bgm_duration < 1:
        raise ValueError("BGM offset leaves less than one second")
    requested_overlap = float(bgm.get("loop_overlap_seconds", 3.0))
    if not math.isfinite(requested_overlap) or requested_overlap < 0:
        raise ValueError("Invalid BGM loop overlap")
    overlap = min(requested_overlap, bgm_duration / 5)
    repeats = max(1, math.ceil((duration - overlap) / (bgm_duration - overlap)))
    bg_inputs = []
    bg_filters = []
    for index in range(repeats):
        bg_inputs += ["-ss", str(bgm_start), "-i", str(bgm_path)]
        bg_filters.append(f"[{index}:a]aresample=48000,aformat=channel_layouts=stereo,asetpts=N/SR/TB[b{index}]")
    last_label = "b0"
    for index in range(1, repeats):
        next_label = f"loop{index}"
        if overlap > 0:
            bg_filters.append(f"[{last_label}][b{index}]acrossfade=d={overlap}:c1=qsin:c2=qsin[{next_label}]")
        else:
            bg_filters.append(f"[{last_label}][b{index}]concat=n=2:v=0:a=1[{next_label}]")
        last_label = next_label
    bg_filters.append(f"[{last_label}]apad=whole_dur={duration},atrim=0:{duration}[bg]")
    bed = audio_dir / "bgm-continuous.wav"
    run(["ffmpeg", "-y", "-loglevel", "error", *bg_inputs, "-filter_complex", ";".join(bg_filters),
         "-map", "[bg]", "-ar", "48000", "-c:a", "pcm_s16le", str(bed)])
    fade_start = max(0, duration - 3)
    mix = audio_dir / "mix.wav"
    mix_filter = (
        "[0:a]asplit[vo][key];"
        f"[1:a]volume='{gain}+({ending_gain}-{gain})*clip((t-{ending_start})/1.5,0,1)':eval=frame,"
        f"afade=t=in:d=0.7,afade=t=out:st={fade_start}:d=3[bg];"
        "[bg][key]sidechaincompress=threshold=0.03:ratio=3:attack=15:release=350[bgd];"
        f"[bgd][vo]amix=inputs=2:normalize=0,alimiter=limit=0.89:latency=1,asetpts=N/SR/TB,"
        f"apad=whole_dur={duration},atrim=0:{duration}[mix]"
    )
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(narration), "-i", str(bed),
         "-filter_complex", mix_filter, "-map", "[mix]", "-ar", "48000", "-c:a", "pcm_s16le", str(mix)])
    final_output = out / "rd-process-ai-fast-track.mp4"
    final = out / "rd-process-ai-fast-track.partial.mp4"
    # Fixed audio padding avoids -shortest dropping a final video frame.
    run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), "-i", str(mix),
         "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
         "-movflags", "+faststart", str(final)])
    final_probe = probe(final)
    final_video = next(stream for stream in final_probe["streams"] if stream["codec_type"] == "video")
    final_audio = next(stream for stream in final_probe["streams"] if stream["codec_type"] == "audio")
    if (final_video["width"], final_video["height"], final_video["r_frame_rate"]) != (width, height, f"{fps}/1"):
        raise ValueError("Final video dimensions or fps differ from storyboard")
    if int(final_video.get("nb_frames", 0)) != expected_frames:
        raise ValueError(f"Expected {expected_frames} video frames")
    if abs(float(final_probe["format"]["duration"]) - duration) > 1 / fps:
        raise ValueError("Final duration differs from config")
    if final_audio.get("sample_rate") != "48000" or final_audio.get("channels") != 2:
        raise ValueError("Final audio must be stereo 48000 Hz")
    if abs(float(final_audio.get("duration", duration)) - duration) > 1 / fps:
        raise ValueError("Final audio duration differs from config")
    run(["ffmpeg", "-v", "error", "-i", str(final), "-f", "null", "-"])
    silent_hash, final_stream_hash = stream_hash(silent), stream_hash(final)
    if silent_hash != final_stream_hash:
        raise ValueError("Muxed production video stream changed")
    final.replace(final_output)
    final = final_output
    source_manifest = json.loads((args.import_audio_dir / "manifest.json").read_text())
    report = {
        "status": "PASS", "file": str(final.relative_to(ROOT)), "sha256": sha256(final),
        "duration_seconds": duration, "width": final_video["width"], "height": final_video["height"],
        "fps": final_video["r_frame_rate"], "frames": expected_frames, "audio_sample_rate": 48000, "audio_channels": 2,
        "video_stream_sha256": final_stream_hash, "video_stream_copy_verified": True, "decode_verified": True,
        "generation_mode": "single_take", "voice_id": config["elevenlabs"]["voice"],
        "model_id": config["elevenlabs"]["model_id"],
        "source_take_sha256": source_manifest["source_take"]["sha256"],
        "all_clips_same_take": True, "scene_timing_verified": True, "narration_playback_speed": 1.0,
        "voice_settings": config["elevenlabs"]["voice_settings"], "clips": len(clips),
        "import_manifest_sha256": sha256(args.import_audio_dir / "manifest.json"),
        "storyboard_sha256": sha256(args.storyboard),
        "narration_config_sha256": sha256(args.config),
        "render_validation_sha256": sha256(render_report_path),
        "narration_loudness_measurement": loudness,
        "bgm": {**bgm, "loop_repeats": repeats, "loop_overlap_seconds": overlap if repeats > 1 else 0,
                "ending_gain_start_seconds": ending_start},
        "limits": "Importer verifies sample provenance and scene fit. Transcript word boundary review must be recorded separately.",
    }
    (out / "audio-validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print("wrote " + str(final), flush=True)


if __name__ == "__main__":
    main()
