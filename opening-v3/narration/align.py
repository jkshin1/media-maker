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
    text = re.sub(r"Fast\s*Track", "패스트트랙", text, flags=re.I)
    text = text.replace("아이전트", "에이전트")
    text = re.sub(r"12\s*개", "열두개", text)
    return re.sub(r"[^0-9a-z가-힣]", "", text.lower())


def main():
    config = read(HERE / "ko.json")
    receipt = read(HERE / "receipt.json")
    transcript = read(HERE / "transcription/take.json")
    assert receipt["generated_prompt"] == config["generated_prompt"]
    assert "R&D" not in config["generated_prompt"]
    assert config["generated_prompt"].count("알앤디") == 3
    assert sum(c["text"].count("R&D") for c in config["clips"]) == 3
    assert all(c["spoken_text"] == c["text"].replace("R&D", "알앤디") for c in config["clips"])
    assert config["clips"][0]["spoken_text"] == "알앤디 업무에 AI를 더합니다."
    assert "소개합니다" in transcript["segments"][-1]["text"]
    assert "업무" in transcript["segments"][0]["text"]
    assert "현업" not in transcript["segments"][0]["text"]
    assert "공정" in transcript["segments"][1]["text"]
    assert "변화" in transcript["segments"][1]["text"]
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
    # Select each pause from its transcript sentence boundary, not from a
    # minimum duration alone: short quiet intervals can occur inside words.
    sentence_pauses = []
    for previous, following in zip(transcript["segments"], transcript["segments"][1:]):
        previous_end = previous["words"][-1]["end"]
        following_first = following["words"][0]
        eligible = [p for p in pauses if p[0] >= previous_end - .5
            and p[1] <= following_first["end"] and p[1] - p[0] >= .18]
        assert eligible, (previous["id"], previous_end, following_first)
        sentence_pauses.append(max(eligible, key=lambda p: p[1] - p[0]))
    boundaries = [0] + [round((a + b) / 2 * params.framerate)
                        for a, b in sentence_pauses] + [params.nframes]
    reviews = []
    for i, (pause, sample) in enumerate(zip(sentence_pauses, boundaries[1:-1])):
        previous = transcript["segments"][i]["words"][-1]
        following = transcript["segments"][i + 1]["words"][0]
        seconds = sample / params.framerate
        status = previous["end"] < seconds < following["start"]
        targeted = None
        targeted_previous = None
        if not status:
            # Whisper attached the first word's start to the previous segment's
            # end. A separate transcript of audio beginning at this exact cut
            # confirms the complete following sentence and first word survive.
            targeted = read(HERE / f"transcription/boundary{i + 2}.json")
            targeted_source = read(HERE / f"transcription/boundary{i + 2}-source.json")
            expected = config["clips"][i + 1]["spoken_text"]
            assert difflib.SequenceMatcher(None, norm(expected), norm(targeted["text"])).ratio() > .99
            assert targeted_source["source_start_sample"] == sample
            if previous["end"] >= seconds:
                targeted_previous = read(HERE / f"transcription/boundary{i + 1}-previous.json")
                previous_source = read(HERE / f"transcription/boundary{i + 1}-previous-source.json")
                assert previous_source["source_end_sample"] == sample
                previous_expected = config["clips"][i]["spoken_text"]
                assert difflib.SequenceMatcher(None, norm(previous_expected), norm(targeted_previous["text"])).ratio() > .99
            status = True
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
            "targeted_previous_sentence_transcript": targeted_previous["text"] if targeted_previous else None,
            "timestamp_caveat": "Full-take ASR boundary timestamps include the adjacent pause. Exact-cut isolated transcriptions confirm the complete sentence and edge words." if targeted else None})
    records = []
    threshold = 32768 * 10 ** (-50 / 20)
    timeline_offsets = [.12, .18, .25, .3, .04, .25, .45, .4, .15]
    for clip, segment, a, b, offset in zip(config["clips"], transcript["segments"],
            boundaries, boundaries[1:], timeline_offsets):
        similarity = difflib.SequenceMatcher(None, norm(clip["spoken_text"]), norm(segment["text"]), autojunk=False).ratio()
        reviewed_text = None
        spelling_caveat = None
        if similarity < .9:
            reviewed = read(HERE / f"transcription/block{clip['id']}-review.json")
            reviewed_source = read(HERE / f"transcription/block{clip['id']}-review-source.json")
            assert reviewed_source["source_start_sample"] == a and reviewed_source["source_end_sample"] == b
            reviewed_text = reviewed["text"]
            similarity = difflib.SequenceMatcher(None, norm(clip["spoken_text"]), norm(reviewed_text), autojunk=False).ratio()
        assert similarity >= .9, (clip["id"], similarity, segment["text"])
        file = HERE / f"vo{clip['id']}.wav"
        with wave.open(str(file), "wb") as target:
            target.setparams(params)
            target.writeframes(pcm[a * 2:b * 2])
        with wave.open(str(file), "rb") as verify:
            assert verify.readframes(verify.getnframes()) == pcm[a * 2:b * 2]
        active = [i for i, value in enumerate(samples[a:b]) if abs(value) > threshold]
        assert active
        pre_pad, post_pad = (960, 1440) if clip["id"] == 9 else (2880, 3840)
        trim_a, trim_b = max(0, active[0] - pre_pad), min(b - a, active[-1] + post_pad + 1)
        trimmed_duration = (trim_b - trim_a) / params.framerate
        slot = (clip["end_ms"] - clip["start_ms"]) / 1000
        offset = min(offset, max(0., slot - trimmed_duration - .04))
        tempo = max(1., trimmed_duration / (slot - offset - .04))
        assert tempo <= 1.1, (clip["id"], tempo)
        records.append({**clip, "file": file.name, "sha256": sha(file),
            "recognized_text": segment["text"].strip(),
            "isolated_sentence_review_text": reviewed_text,
            "ASR_spelling_caveat": spelling_caveat,
            "normalized_character_similarity": round(similarity, 6),
            "source_start_sample": a, "source_end_sample": b,
            "source_duration_seconds": (b - a) / params.framerate,
            "timeline_trim_start_sample": trim_a, "timeline_trim_end_sample": trim_b,
            "trim_edge_padding_samples": [pre_pad, post_pad],
            "trimmed_duration_seconds": trimmed_duration, "tempo_ratio": tempo,
            "timeline_start_seconds": clip["start_ms"] / 1000 + offset,
            "timeline_end_seconds": clip["start_ms"] / 1000 + offset + trimmed_duration / tempo,
            "exact_source_pcm_match": True})
    manifest = {"provider": receipt["provider"], "model_id": receipt["model_id"],
        "voice_id": receipt["voice_id"], "voice_name": receipt["voice_name"],
        "generation_mode": "single_take", "generated_prompt": receipt["generated_prompt"],
        "pronunciation_map": config["pronunciation_map"],
        "approved_display_script": [c["text"] for c in config["clips"]],
        "spoken_script": [c["spoken_text"] for c in config["clips"]],
        "first_sentence_revision": {"before": "알앤디 현업에 AI를 더합니다.",
            "after": "알앤디 업무에 AI를 더합니다.", "actual_ASR": transcript["segments"][0]["text"],
            "업무_present": True, "현업_absent_from_first_sentence": True},
        "pronunciation_verification": {"requested_form": "알앤디", "spoken_prompt_occurrences": 3,
            "display_R_and_D_occurrences_preserved": 3,
            "unprompted_ASR_canonical_R_and_D_occurrences": transcript["text"].count("R&D"),
            "unprompted_ASR_limit": "Whisper can canonicalize the Korean pronunciation 알앤디 as the Latin spelling R&D. The source prompt preserves 알앤디 in all three positions; this revision does not claim a new independent accent comparison."},
        "generation_id": receipt["generation_id"], "status": "COMPLETE_ASR_COVERAGE_AND_SAFE_PCM_CUTS",
        "rejected_take": receipt["rejected_take"],
        "source_take": {"file": "take.wav", "sha256": sha(HERE / "take.wav"),
            "source_mp3_sha256": sha(HERE / "source.mp3"), "sample_rate": 48000,
            "channels": 1, "sample_width_bytes": 2, "samples": params.nframes,
            "duration_seconds": params.nframes / params.framerate,
            "conversion": "Unaltered remote MP3 decoded/resampled to 48000 Hz mono PCM16."},
        "transcript_verification": {"engine": "local OpenAI Whisper small",
            "external_audio_transfer": False, "all_nine_sentences_covered": True,
            "last_sentence_present": True, "recognized_text": transcript["text"],
            "character_perfect_ASR": False,
            "spelling_caveats": [r["ASR_spelling_caveat"] for r in records if r["ASR_spelling_caveat"]],
            "transcript_sha256": sha(HERE / "transcription/take.json"),
            "limitations": "ASR spelling and word timings are approximate. Unprompted Whisper may canonicalize spoken Korean 알앤디 as R&D. AI, Agent and 12 pronunciation variants are normalized. This is sentence coverage evidence, not a claim of character-perfect ASR."},
        "boundary_reviews": reviews, "clips": records,
        "voice_settings": {"requested": receipt["requested_voice_settings"],
            "actual_exposed": receipt["actual_exposed_parameters"],
            "limitation": receipt["settings_limitation"]},
        "timing_adjustment": {"requested_cut09": [42, 45], "actual_cut09": [42, 46],
            "reason": "Retains the approved v1 46-second timeline. The final approved sentence requires more than three seconds at natural speed."}}
    (HERE / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"sentence_coverage": "9/9", "safe_boundaries": "8/8", "exact_pcm_cuts": "9/9",
        "clips": [{"id": x["id"], "tempo": x["tempo_ratio"],
            "timeline": [x["timeline_start_seconds"], x["timeline_end_seconds"]]} for x in records]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
