#!/usr/bin/env python3
"""Local Supertonic TTS or imported audio generated with the ElevenLabs plugin."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("HF_HOME", str(ROOT / ".cache/huggingface"))
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
MODEL_CONFIGS = {"supertonic": "supertonic.json", "elevenlabs": "elevenlabs.json"}
ELEVENLABS_VOICE_SETTINGS = ("stability", "similarity_boost", "style", "use_speaker_boost", "speed")


def read_config(path):
    config = json.loads(Path(path).read_text())
    previous_end = 0
    for n, clip in enumerate(config["clips"], 1):
        if (clip["id"] != n or not clip["text"].strip()
                or not previous_end <= clip["start_ms"] < clip["end_ms"]
                or clip["end_ms"] > config["duration_seconds"] * 1000):
            raise ValueError(f"Invalid clip or overlapping timing: {clip}")
        previous_end = clip["end_ms"]
    if not config["clips"]:
        raise ValueError("Narration requires at least one clip")
    return config


def model_info(engine):
    return json.loads((ROOT / "models" / MODEL_CONFIGS[engine]).read_text())


def elevenlabs_generation_settings(settings, info):
    """Use one saved configuration for generation instructions and audio imports."""
    if info["voice_id"] != settings["voice"] or info["model_id"] != settings["model_id"]:
        raise ValueError("ElevenLabs voice/model configuration differs between narration and model settings")
    tag = settings.get("delivery_tag", "").strip()
    voice_settings = settings.get("voice_settings")
    if voice_settings is None:
        voice_settings = {field: settings[field] for field in ELEVENLABS_VOICE_SETTINGS if field in settings}
    if not isinstance(voice_settings, dict):
        raise ValueError("ElevenLabs voice_settings must be a JSON object")
    voice_settings = dict(voice_settings)
    return tag, voice_settings


def generation_prompt(text, delivery_tag):
    return f"{delivery_tag} {text}" if delivery_tag else text


def generation_mode(settings):
    mode = settings.get("generation_mode", "per_clip")
    if mode not in ("per_clip", "single_take"):
        raise ValueError(f"Unknown ElevenLabs generation_mode: {mode}")
    return mode


def single_take_prompt(clips, delivery_tag):
    """Keep the delivery instruction once, then narrate all scenes together."""
    return "\n".join(([delivery_tag] if delivery_tag else []) + [clip["text"] for clip in clips])


def print_prompts(engine, config, voice=None):
    """Print ready-to-use inputs without generating speech or using credits."""
    settings = dict(config[engine])
    if voice:
        settings["voice"] = voice
    info = model_info(engine)
    result = {"engine": engine, "model_id": settings.get("model_id", info.get("model_id")),
              "voice_id": settings["voice"], "voice_name": info.get("voice_name", settings["voice"])}
    if engine == "elevenlabs":
        tag, voice_settings = elevenlabs_generation_settings(settings, info)
        mode = generation_mode(settings)
        result.update(delivery_tag=tag, voice_settings=voice_settings, generation_mode=mode,
                      integration="Generate through the connected ElevenLabs plugin or web TTS, then import WAV/provenance")
        if mode == "single_take":
            result["generated_prompt"] = single_take_prompt(config["clips"], tag)
    else:
        tag = ""
        mode = "per_clip"
        result["voice_settings"] = settings
    result["clips"] = [{"id": clip["id"], "text": clip["text"],
                        "start_ms": clip["start_ms"], "end_ms": clip["end_ms"]}
                       for clip in config["clips"]]
    if mode == "per_clip":
        for clip in result["clips"]:
            clip["generated_prompt"] = generation_prompt(clip["text"], tag)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def download(engine):
    if engine != "supertonic":
        raise ValueError("ElevenLabs uses the connected Codex plugin; there is no model to download.")
    from huggingface_hub import snapshot_download
    info = model_info(engine)
    snapshot_download(repo_id=info["repo_id"], revision=info["revision"],
                      local_dir=ROOT / info["local_dir"], max_workers=4)
    print(f"Downloaded {engine}: {info['local_dir']}", flush=True)


def load_engine(engine):
    # Never fetch a model, tokenizer, or send text to a remote API at inference time.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    info = model_info(engine)
    directory = ROOT / info["local_dir"]
    if not (directory / "config.json").exists():
        raise FileNotFoundError(f"Model missing. Run npm run tts:setup -- {engine}")
    import onnxruntime as ort
    ort.disable_telemetry_events()
    from supertonic import TTS
    return TTS(model="supertonic-3", model_dir=directory, auto_download=False,
               intra_op_num_threads=8, inter_op_num_threads=1)


def synthesize(model, engine, text, settings, seed):
    import numpy as np
    np.random.seed(seed)
    audio, duration = model.synthesize(
        text, voice_style=model.get_voice_style(settings["voice"]), lang="ko",
        total_steps=settings["steps"], speed=settings["speed"])
    # ONNX output is padded to a latent block boundary; retain its reported duration.
    length = round(float(duration[0]) * model.sample_rate)
    return audio.reshape(-1)[:length], model.sample_rate


def trim_edges(audio, sample_rate):
    """Remove only boundary silence; keep internal pauses and 60 ms at each edge."""
    import numpy as np
    if not len(audio) or not np.isfinite(audio).all():
        raise RuntimeError("TTS returned empty or non-finite samples")
    active = np.flatnonzero(np.abs(audio) > 10 ** (-50 / 20))
    if not len(active):
        raise RuntimeError("TTS returned silence")
    pad = round(sample_rate * 0.06)
    return audio[max(0, active[0] - pad):min(len(audio), active[-1] + pad + 1)]


def imported_sources(directory, clips, settings, info, configured_clips=None):
    """Bind imported speech to its original text, voice, model, and audio bytes."""
    manifest_path = directory / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"ElevenLabs source manifest missing: {manifest_path}. "
                                "Import the plugin-generated audio and its provenance first.")
    manifest = json.loads(manifest_path.read_text())
    delivery_tag, voice_settings = elevenlabs_generation_settings(settings, info)
    mode = generation_mode(settings)
    if manifest.get("generation_mode", "per_clip") != mode:
        raise ValueError("ElevenLabs manifest generation_mode differs from current configuration. "
                         "Generate the narration using npm run tts:prompts and import its provenance.")
    expected = {"provider": "ElevenLabs", "voice_id": settings["voice"],
                "model_id": settings["model_id"], "voice_name": info["voice_name"]}
    if voice_settings:
        expected["voice_settings"] = voice_settings
    for field, value in expected.items():
        if manifest.get(field) != value:
            raise ValueError(f"ElevenLabs manifest {field} differs from current configuration. "
                             "Regenerate and import the selected voice before building.")
    entries = {}
    for entry in manifest.get("clips", []):
        if entry.get("id") in entries:
            raise ValueError(f"Duplicate ElevenLabs source clip: {entry.get('id')}")
        entries[entry.get("id")] = entry
    source_take = None
    take_audio = None
    take_sample_rate = None
    full_prompt = None
    if mode == "single_take":
        import numpy as np
        import soundfile as sf
        full_prompt = single_take_prompt(configured_clips or clips, delivery_tag)
        source_take = manifest.get("source_take")
        if (not isinstance(source_take, dict) or source_take.get("file") != "take.wav"
                or source_take.get("generated_prompt") != full_prompt):
            raise ValueError("ElevenLabs single_take master does not match the full narration prompt/file")
        take_path = directory / "take.wav"
        if not take_path.exists():
            raise FileNotFoundError(f"ElevenLabs single_take master missing: {take_path}")
        take_digest = hashlib.sha256(take_path.read_bytes()).hexdigest()
        if source_take.get("sha256") != take_digest:
            raise ValueError("ElevenLabs single_take master checksum differs from manifest.json")
        take_audio, take_sample_rate = sf.read(take_path, dtype="float32", always_2d=True)
        if take_sample_rate != 48000 or take_audio.shape[1] != 1:
            raise ValueError("ElevenLabs single_take master must be a 48000 Hz mono WAV")
        if not len(take_audio) or not np.isfinite(take_audio).all():
            raise ValueError("ElevenLabs single_take master contains empty or non-finite audio")
    sources = {}
    previous_source_end = 0
    for clip in clips:
        if clip["id"] not in entries:
            raise FileNotFoundError(f"ElevenLabs source clip {clip['id']} missing from {manifest_path}. "
                                    "Complete plugin generation for this clip and import its WAV/provenance "
                                    "before building the full narration.")
        entry = entries[clip["id"]]
        filename = "sample.wav" if clip["id"] == "sample" else f"vo{clip['id']}.wav"
        if entry.get("text") != clip["text"] or entry.get("file") != filename:
            raise ValueError(f"ElevenLabs source clip {clip['id']} does not match its current text/file. "
                             "Regenerate this clip and update manifest.json.")
        expected_prompt = full_prompt if mode == "single_take" else generation_prompt(clip["text"], delivery_tag)
        if (mode == "single_take" or delivery_tag) and (
                entry.get("delivery_tag") != delivery_tag or entry.get("generated_prompt") != expected_prompt):
            raise ValueError(f"ElevenLabs source clip {clip['id']} does not match its current delivery tag/prompt. "
                             "Regenerate this clip using npm run tts:prompts and update manifest.json.")
        if mode == "single_take":
            start, end = entry.get("source_start_sample"), entry.get("source_end_sample")
            if (entry.get("source_take_sha256") != source_take["sha256"]
                    or isinstance(start, bool) or isinstance(end, bool)
                    or not isinstance(start, int) or not isinstance(end, int)
                    or not previous_source_end <= start < end <= len(take_audio)):
                raise ValueError(f"ElevenLabs source clip {clip['id']} has invalid master hash/cut boundaries")
            for field, sample in (("source_start_ms", start), ("source_end_ms", end)):
                if field in entry and (not isinstance(entry[field], (int, float))
                                       or abs(entry[field] - sample / take_sample_rate * 1000) > 0.01):
                    raise ValueError(f"ElevenLabs source clip {clip['id']} {field} differs from its sample boundary")
            previous_source_end = end
        path = directory / filename
        if not path.exists():
            raise FileNotFoundError(f"ElevenLabs audio missing: {path}. Generate it with the connected "
                                    "ElevenLabs plugin and import its WAV clips first.")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if entry.get("sha256") != digest:
            raise ValueError(f"ElevenLabs source clip {clip['id']} checksum differs from manifest.json")
        if mode == "single_take":
            clip_audio, clip_sample_rate = sf.read(path, dtype="float32", always_2d=True)
            if (clip_sample_rate != take_sample_rate
                    or not np.array_equal(clip_audio, take_audio[start:end])):
                raise ValueError(f"ElevenLabs source clip {clip['id']} is not the recorded cut from the single_take master")
        sources[clip["id"]] = {"path": path, "sha256": digest, "provenance": entry}
    return sources, hashlib.sha256(manifest_path.read_bytes()).hexdigest(), source_take


def generate(engine, config, output, text=None, voice=None, force=False, import_audio_dir=None,
             sample_clip=None):
    import numpy as np
    import soundfile as sf
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    settings = dict(config[engine])
    if voice:
        settings["voice"] = voice
    info = model_info(engine)
    preview = text is not None or sample_clip is not None
    if text is not None:
        clips = [{"id": "sample", "text": text}]
    elif sample_clip is not None:
        clips = [clip for clip in config["clips"] if clip["id"] == sample_clip]
        if not clips:
            raise ValueError(f"Sample clip {sample_clip} is not present in narration configuration")
    else:
        clips = config["clips"]
    sources = {}
    if engine == "elevenlabs":
        directory = Path(import_audio_dir or ROOT / "assets/narration/elevenlabs")
        sources, manifest_sha256, source_take = imported_sources(directory, clips, settings, info, config["clips"])
    model = None
    records = []
    timing_errors = []
    for clip in clips:
        name = "sample" if preview else f"vo{clip['id']}"
        wav_path = output / f"{name}.wav"
        meta_path = output / f"{name}.json"
        key_data = {"model": info, "settings": settings, "text": clip["text"], "id": clip["id"],
                    "seed": config["seed"], "pipeline_version": 2}
        if engine == "elevenlabs":
            key_data["source_sha256"] = sources[clip["id"]]["sha256"]
            key_data["source_provenance"] = sources[clip["id"]]["provenance"]
            key_data["source_take"] = source_take
        key = hashlib.sha256(json.dumps(key_data, sort_keys=True).encode()).hexdigest()
        cached = json.loads(meta_path.read_text()) if meta_path.exists() else {}
        if not force and wav_path.exists() and cached.get("cache_key") == key:
            if not preview:
                cached.update(start_ms=clip["start_ms"], end_ms=clip["end_ms"])
                if cached["duration_seconds"] > (clip["end_ms"] - clip["start_ms"]) / 1000:
                    timing_errors.append(f"Clip {clip['id']}: {cached['duration_seconds']:.2f}s exceeds its slot")
                meta_path.write_text(json.dumps(cached, ensure_ascii=False, indent=2) + "\n")
            records.append(cached)
            print(f"Reused {wav_path}", flush=True)
            continue
        if engine == "supertonic" and model is None:
            print(f"Loading local {engine} model...", flush=True)
            model = load_engine(engine)
        started = time.perf_counter()
        seed = config["seed"] + (int(clip["id"]) if clip["id"] != "sample" else 0)
        if engine == "elevenlabs":
            audio, sample_rate = sf.read(sources[clip["id"]]["path"], dtype="float32", always_2d=True)
            audio = audio.mean(axis=1)
        else:
            audio, sample_rate = synthesize(model, engine, clip["text"], settings, seed)
        raw = output / "raw" / f"{name}.wav"
        raw.parent.mkdir(exist_ok=True)
        sf.write(raw, audio, sample_rate, subtype="PCM_16")
        audio = trim_edges(audio, sample_rate)
        duration = len(audio) / sample_rate
        # Reject overlong speech instead of cutting words or accelerating narration.
        if not preview and duration > (clip["end_ms"] - clip["start_ms"]) / 1000:
            timing_errors.append(f"Clip {clip['id']} needs {duration:.2f}s, but its slot is "
                                 f"{(clip['end_ms'] - clip['start_ms']) / 1000:.2f}s. Raw audio: {raw}")
        sf.write(wav_path, audio, sample_rate, subtype="PCM_16")
        record = {"cache_key": key, "engine": engine, "model": info, "settings": settings,
                  "text": clip["text"], "seed": seed, "clip_id": clip["id"],
                  "sample_rate": sample_rate, "duration_seconds": duration,
                  "generation_seconds": time.perf_counter() - started,
                  "peak": float(np.abs(audio).max()), "path": str(wav_path.resolve())}
        if engine == "elevenlabs":
            record.update(source_path=str(sources[clip["id"]]["path"].resolve()),
                          source_sha256=key_data["source_sha256"],
                          source_provenance=key_data["source_provenance"])
        if not preview:
            record.update(start_ms=clip["start_ms"], end_ms=clip["end_ms"])
        meta_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
        records.append(record)
        print(f"{wav_path}: {duration:.2f}s, generated in {record['generation_seconds']:.2f}s", flush=True)
    if timing_errors:
        raise ValueError("\n".join(timing_errors) + "\nShorten the text or adjust the scene timing.")
    receipt = {"engine": engine, "model": info, "offline": engine == "supertonic",
               "integration": "local_model" if engine == "supertonic" else "plugin_audio_import",
               "preview": preview, "duration_seconds": config["duration_seconds"], "clips": records}
    if engine == "elevenlabs":
        receipt["source_manifest_sha256"] = manifest_sha256
        receipt["generation_mode"] = generation_mode(settings)
        if source_take:
            receipt["source_take"] = source_take
    (output / "generation.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=MODEL_CONFIGS, default=os.getenv("TTS_ENGINE"))
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--prompts", action="store_true", help="Print the saved voice/model/settings and generation prompts without using credits")
    parser.add_argument("--config", type=Path, default=ROOT / "assets/narration/ko.json")
    parser.add_argument("--output-dir", type=Path)
    preview = parser.add_mutually_exclusive_group()
    preview.add_argument("--text", help="Generate a preview without a timing limit; ElevenLabs needs sample.wav and a matching manifest entry")
    preview.add_argument("--sample-clip", type=int, help="Preview one configured clip without a timing limit")
    parser.add_argument("--voice")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--import-audio-dir", type=Path, help="Folder containing ElevenLabs vo1.wav, vo2.wav, etc.")
    args = parser.parse_args()
    try:
        config = read_config(args.config)
        engine = args.engine or config.get("default_engine", "elevenlabs")
        if engine not in MODEL_CONFIGS:
            raise ValueError(f"Unknown default_engine: {engine}")
        if args.download:
            download(engine)
            return
        if args.prompts:
            print_prompts(engine, config, args.voice)
            return
        preview_output = args.text is not None or args.sample_clip is not None
        output = args.output_dir or ROOT / ("out/comparison" if preview_output else "out/audio") / engine
        generate(engine, config, output, args.text, args.voice, args.force,
                 args.import_audio_dir, args.sample_clip)
    except (ValueError, RuntimeError, FileNotFoundError) as error:
        parser.exit(1, f"error: {error}\n")


if __name__ == "__main__":
    main()
