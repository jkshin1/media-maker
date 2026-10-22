#!/usr/bin/env python3
"""Import exact PCM sentence cuts from the approved single take.

Requires the bundled local Whisper transcripts in transcription/. Does not
generate remote audio or send audio to an external transcription service.
"""
import array
import difflib
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import wave

HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def norm(text):
    text = re.sub(r"R\s*&\s*D", "알앤디", text, flags=re.I)
    text = re.sub(r"AI", "에이아이", text, flags=re.I)
    text = re.sub(r"Agent", "에이전트", text, flags=re.I)
    text = text.replace("아이전트", "에이전트")
    text = re.sub(r"12\s*개", "열두개", text)
    return re.sub(r"[^0-9a-z가-힣]", "", text.lower())


def main():
    config = read(HERE / "ko.json")
    receipt = read(HERE / "receipt.json")
    transcript = read(HERE / "transcription/take.json")
    assert len(config["clips"]) == len(transcript["segments"]) == 9
    with wave.open(str(HERE / "take.wav"), "rb") as source:
        params = source.getparams()
        assert (params.framerate, params.nchannels, params.sampwidth) == (48000, 1, 2)
        pcm = source.readframes(params.nframes)
    samples = array.array("h", pcm)
    result = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(HERE / "take.wav"),
        "-af", "silencedetect=noise=-45dB:d=0.1", "-f", "null", "-"],
        capture_output=True, text=True, check=True)
    (HERE / "transcription/silencedetect.log").write_text(result.stderr)
    pauses, start = [], None
    for line in result.stderr.splitlines():
        sm = re.search(r"silence_start: ([0-9.]+)", line)
        em = re.search(r"silence_end: ([0-9.]+)", line)
        if sm:
            start = float(sm.group(1))
        if em and start is not None:
            pauses.append((start, float(em.group(1))))
            start = None
    # These are long inter-sentence pauses in this immutable master, in order.
    sentence_pauses = [p for p in pauses if p[1] - p[0] > .4]
    assert len(sentence_pauses) == 8
    boundaries = [0] + [round((a + b) / 2 * params.framerate)
                        for a, b in sentence_pauses] + [params.nframes]
    reviews = []
    for i, (pause, sample) in enumerate(zip(sentence_pauses, boundaries[1:-1])):
        previous = transcript["segments"][i]["words"][-1]
        following = transcript["segments"][i + 1]["words"][0]
        seconds = sample / params.framerate
        status = previous["end"] < seconds < following["start"]
        targeted = None
        if i == 5:
            # Whisper attached the first word's start to the previous segment's
            # end. A separate transcript of audio beginning at this exact cut
            # confirms the complete following sentence and first word survive.
            targeted = read(HERE / "transcription/boundary7.json")
            expected = config["clips"][6]["text"]
            assert difflib.SequenceMatcher(None, norm(expected), norm(targeted["text"])).ratio() > .99
            assert abs(seconds - 25.9133125) < .001
            status = previous["end"] < seconds
        assert status, (i + 1, previous, following, seconds)
        center = samples[max(0, sample - 1200):sample + 1200]
        rms = math.sqrt(sum(v * v for v in center) / len(center)) / 32768
        assert rms < 10 ** (-45 / 20)
        reviews.append({"after_block": i + 1, "cut_sample": sample,
            "cut_seconds": seconds, "waveform_pause_seconds": list(pause),
            "previous_last_word": previous, "following_first_word": following,
            "waveform_center_50ms_rms_dbfs": 20 * math.log10(max(rms, 1e-12)),
            "transcript_boundary_verified": True,
            "targeted_following_sentence_transcript": targeted["text"] if targeted else None,
            "timestamp_caveat": "Full-take ASR first-word onset includes the leading pause. Exact-cut isolated transcription confirms the complete first word and sentence." if targeted else None})
    records = []
    threshold = 32768 * 10 ** (-50 / 20)
    timeline_offsets = [.12, .18, .25, .3, .04, .25, .45, .4, .15]
    for clip, segment, a, b, offset in zip(config["clips"], transcript["segments"],
            boundaries, boundaries[1:], timeline_offsets):
        similarity = difflib.SequenceMatcher(None, norm(clip["text"]), norm(segment["text"]), autojunk=False).ratio()
        assert similarity >= .9, (clip["id"], similarity, segment["text"])
        file = HERE / f"vo{clip['id']}.wav"
        with wave.open(str(file), "wb") as target:
            target.setparams(params)
            target.writeframes(pcm[a * 2:b * 2])
        with wave.open(str(file), "rb") as verify:
            assert verify.readframes(verify.getnframes()) == pcm[a * 2:b * 2]
        active = [i for i, value in enumerate(samples[a:b]) if abs(value) > threshold]
        assert active
        trim_a, trim_b = max(0, active[0] - 2880), min(b - a, active[-1] + 3841)
        trimmed_duration = (trim_b - trim_a) / params.framerate
        slot = (clip["end_ms"] - clip["start_ms"]) / 1000
        tempo = max(1., trimmed_duration / (slot - offset - .07))
        assert tempo <= 1.2, (clip["id"], tempo)
        records.append({**clip, "file": file.name, "sha256": sha(file),
            "recognized_text": segment["text"].strip(),
            "normalized_character_similarity": round(similarity, 6),
            "source_start_sample": a, "source_end_sample": b,
            "source_duration_seconds": (b - a) / params.framerate,
            "timeline_trim_start_sample": trim_a, "timeline_trim_end_sample": trim_b,
            "trimmed_duration_seconds": trimmed_duration, "tempo_ratio": tempo,
            "timeline_start_seconds": clip["start_ms"] / 1000 + offset,
            "timeline_end_seconds": clip["start_ms"] / 1000 + offset + trimmed_duration / tempo,
            "exact_source_pcm_match": True})
    manifest = {"provider": receipt["provider"], "model_id": receipt["model_id"],
        "voice_id": receipt["voice_id"], "voice_name": receipt["voice_name"],
        "generation_mode": "single_take", "generated_prompt": receipt["generated_prompt"],
        "generation_id": receipt["generation_id"], "status": "COMPLETE_ASR_COVERAGE_AND_SAFE_PCM_CUTS",
        "source_take": {"file": "take.wav", "sha256": sha(HERE / "take.wav"),
            "source_mp3_sha256": sha(HERE / "source.mp3"), "sample_rate": 48000,
            "channels": 1, "sample_width_bytes": 2, "samples": params.nframes,
            "duration_seconds": params.nframes / params.framerate,
            "conversion": "Unaltered remote MP3 decoded/resampled to 48000 Hz mono PCM16."},
        "transcript_verification": {"engine": "local OpenAI Whisper small",
            "external_audio_transfer": False, "all_nine_sentences_covered": True,
            "last_sentence_present": True, "recognized_text": transcript["text"],
            "transcript_sha256": sha(HERE / "transcription/take.json"),
            "limitations": "ASR spelling and word timings are approximate. R&D, AI, Agent and 12 pronunciation variants are normalized. This is sentence coverage evidence, not a claim of character-perfect ASR."},
        "boundary_reviews": reviews, "clips": records,
        "voice_settings": {"requested": receipt["requested_voice_settings"],
            "actual_exposed": receipt["actual_exposed_parameters"],
            "limitation": receipt["settings_limitation"]},
        "timing_adjustment": {"requested_cut09": [42, 45], "actual_cut09": [42, 46],
            "reason": "The exact final sentence takes about 3.6 seconds at natural speed. The specification requests approximately 45 seconds and natural pacing; +1 second avoids a rushed final line."}}
    (HERE / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"sentence_coverage": "9/9", "safe_boundaries": "8/8", "exact_pcm_cuts": "9/9",
        "clips": [{"id": x["id"], "tempo": x["tempo_ratio"],
            "timeline": [x["timeline_start_seconds"], x["timeline_end_seconds"]]} for x in records]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
