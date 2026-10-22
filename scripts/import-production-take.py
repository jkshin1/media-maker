#!/usr/bin/env python3
"""Import verified sentence cuts from a continuous production narration take."""
import argparse
import hashlib
import json
from pathlib import Path
import wave

ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--voice-dir", type=Path, required=True)
    args = parser.parse_args()
    voice_dir = args.voice_dir.resolve()
    config_path = ROOT / "production/narration/ko.json"
    config = read(config_path)
    alignment = read(voice_dir / "alignment.json")
    receipt_path = voice_dir / "web/receipt.json"
    receipt = read(receipt_path)
    master = voice_dir / "take.wav"
    settings = config["elevenlabs"]
    prompt = "\n".join([settings["delivery_tag"]] + [c["text"] for c in config["clips"]])
    assert settings["generation_mode"] == "single_take"
    assert receipt["generated_prompt"] == prompt
    assert receipt["voice_id"] == settings["voice"]
    assert receipt["model_id"] == settings["model_id"]
    assert receipt["voice_settings"] == settings["voice_settings"]
    assert alignment["source_script_sha256"] == digest(config_path)
    assert alignment["master_sha256"] == digest(master)
    assert alignment["all_50_blocks_present"] and alignment["ending_present"]
    assert alignment["all_49_boundaries_word_and_waveform_safe"]
    assert alignment["all_clips_fit_current_slots_after_edge_trim"]
    blocks = alignment["blocks"]
    assert len(blocks) == len(config["clips"])
    with wave.open(str(master), "rb") as source:
        assert (source.getframerate(), source.getnchannels(), source.getsampwidth()) == (48000, 1, 2)
        params = source.getparams()
        pcm = source.readframes(source.getnframes())
    out = ROOT / "production/narration/elevenlabs"
    out.mkdir(parents=True, exist_ok=True)
    (out / "take.wav").write_bytes(master.read_bytes())
    source_sha = digest(master)
    records = []
    previous_end = 0
    for clip, block in zip(config["clips"], blocks):
        assert clip["id"] == block["id"] and clip["text"] == block["expected_text"]
        start, end = block["source_start_sample"], block["source_end_sample"]
        assert start == previous_end and 0 <= start < end <= params.nframes
        assert block["fits_current_slot_after_edge_trim"]
        path = out / f"vo{clip['id']}.wav"
        with wave.open(str(path), "wb") as target:
            target.setparams(params)
            target.writeframes(pcm[start * 2:end * 2])
        records.append({"id": clip["id"], "text": clip["text"],
                        "delivery_tag": settings["delivery_tag"], "generated_prompt": prompt,
                        "file": path.name, "sha256": digest(path),
                        "source_take_sha256": source_sha,
                        "source_start_sample": start, "source_end_sample": end,
                        "source_start_ms": start / 48, "source_end_ms": end / 48,
                        "source_receipt": str(receipt_path.relative_to(ROOT)),
                        "word_and_waveform_validation": str((voice_dir / "alignment.json").relative_to(ROOT))})
        previous_end = end
    assert previous_end == params.nframes
    manifest = {"provider": "ElevenLabs", "model_id": settings["model_id"],
                "voice_id": settings["voice"], "voice_name": receipt["voice_name"],
                "voice_settings": settings["voice_settings"], "generation_mode": "single_take",
                "status": "COMPLETE", "missing_clips": [],
                "source_take": {"file": "take.wav", "sha256": source_sha,
                                "generated_prompt": prompt, "source_filename": receipt["source_filename"],
                                "sample_rate": 48000, "duration_seconds": params.nframes / 48000,
                                "transport": "website", "variant": receipt["variant"],
                                "generation_id": receipt["generation_id"]}, "clips": records}
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    receipt.update(status="COMPLETE_SOURCE_AND_CUT_VERIFICATION", all_blocks_and_ending_present=True,
                   all_cuts_word_and_waveform_safe=True, all_clips_fit_slots=True,
                   alignment=str((voice_dir / "alignment.json").relative_to(ROOT)))
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"status": "IMPORTED", "clips": len(records), "master_sha256": source_sha}))


if __name__ == "__main__":
    main()
