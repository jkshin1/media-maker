#!/usr/bin/env python3
"""Validate the soft-transition revision without altering either MP4 or sources.

Checks ordered AAC packet payload hashes and timestamps, decoded frame count,
locked scene metadata, 0.45 s transition provenance, and preserved score masks.
Writes comparison PNGs and a separate soft-transitions-validation.json report.
"""
from pathlib import Path
from fractions import Fraction
import argparse
import hashlib
import json
import math
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out" / "showcase"
FPS = 30
FRAMES = 8962
DURATION = FRAMES / FPS
MASK = {"x": 1572, "y": 74, "w": 76, "h": 176, "dx": 170, "dy": 26,
        "delay": .12, "entrance_duration": .68, "rgb": [20, 33, 42]}


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run(args, *, binary=False, timeout=300):
    result = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            check=False, timeout=timeout)
    if result.returncode:
        raise RuntimeError("Command failed: " + " ".join(map(str, args[:6])) + "\n" +
                           result.stderr.decode("utf-8", errors="replace")[-5000:])
    return result.stdout if binary else result.stdout.decode("utf-8")


def probe(path, ffprobe):
    return json.loads(run([ffprobe, "-v", "error", "-show_streams", "-show_format",
                           "-show_data_hash", "sha256", "-of", "json", str(path)]))


def decoded_frames(path, ffprobe):
    data = json.loads(run([ffprobe, "-v", "error", "-select_streams", "v:0", "-count_frames",
                           "-show_entries", "stream=nb_read_frames", "-of", "json", str(path)]))
    return int(data["streams"][0]["nb_read_frames"])


def audio_packets(path, ffprobe):
    data = json.loads(run([ffprobe, "-v", "error", "-select_streams", "a:0", "-show_packets",
                           "-show_data_hash", "sha256", "-show_entries",
                           "packet=pts,dts,duration,size,data_hash", "-of", "json", str(path)]))
    packets = data.get("packets", [])
    if not packets or any(not p.get("data_hash") for p in packets):
        raise RuntimeError("AAC packet payload hashes are missing: " + str(path))
    payloads = [(int(p["size"]), p["data_hash"]) for p in packets]
    timing = [(p.get("pts"), p.get("dts"), p.get("duration")) for p in packets]
    digest = hashlib.sha256(json.dumps(payloads, separators=(",", ":")).encode()).hexdigest()
    return {"payloads": payloads, "timing": timing, "sha256": digest, "count": len(packets)}


def frame_pixels(path, time, rectangle, ffmpeg):
    x, y, w, h = rectangle
    raw = run([ffmpeg, "-v", "error", "-ss", f"{time:.6f}", "-i", str(path),
               "-vf", f"format=rgb24,crop={w}:{h}:{x}:{y}", "-frames:v", "1", "-an",
               "-pix_fmt", "rgb24", "-f", "rawvideo", "-"], binary=True, timeout=60)
    if len(raw) != w * h * 3:
        raise RuntimeError(f"Wrong extracted RGB size at {time}: {len(raw)}")
    return raw


def lumas(raw):
    return [.2126 * raw[i] + .7152 * raw[i + 1] + .0722 * raw[i + 2]
            for i in range(0, len(raw), 3)]


def pixel_stats(raw):
    values = lumas(raw)
    white = sum(raw[i] > 125 and raw[i + 1] > 125 and raw[i + 2] > 125
                for i in range(0, len(raw), 3))
    orange = sum(raw[i] > 145 and raw[i] > raw[i + 1] * 1.4 and raw[i + 2] < 125
                 for i in range(0, len(raw), 3))
    return {"mean_luma": sum(values) / len(values), "max_luma": max(values),
            "white_ink_pixels": white, "orange_ink_pixels": orange, "pixels": len(values)}


def comparison(original, candidate, time, target, ffmpeg):
    # Both sides are decoded from the delivered MP4s at the same media time.
    run([ffmpeg, "-y", "-v", "error", "-ss", f"{time:.6f}", "-i", str(original),
         "-ss", f"{time:.6f}", "-i", str(candidate), "-filter_complex",
         "[0:v]scale=960:540:flags=lanczos[a];[1:v]scale=960:540:flags=lanczos[b];"
         "[a][b]hstack=inputs=2[v]", "-map", "[v]", "-frames:v", "1", "-an", "-update", "1", str(target)], timeout=90)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, default=OUT / "RD_Process_AI_Fast_Track_Showcase.mp4")
    parser.add_argument("--candidate", type=Path, default=OUT / "RD_Process_AI_Fast_Track_Showcase_Soft_Transitions.mp4")
    parser.add_argument("--metadata", type=Path, default=OUT / "soft-transitions-metadata.json")
    args = parser.parse_args()
    report_path = OUT / "soft-transitions-validation.json"
    report = {"status": "WAIT", "original": str(args.original), "candidate": str(args.candidate),
              "metadata": str(args.metadata), "checks": [], "comparisons": [], "score_mask_samples": [],
              "notes": ["Comparison PNGs show the original on the left and revised video on the right.",
                        "AAC payload equality is proved by ordered per-packet SHA-256 hashes and sizes; timing is checked separately.",
                        "Scene titles/intervals are anchored to original render-validation.json input hashes.",
                        "Transition images and mask pixel samples supplement metadata; full browser playback is a separate check."]}
    OUT.mkdir(parents=True, exist_ok=True)

    def save():
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def check(name, passed, **evidence):
        report["checks"].append({"check": name, "passed": bool(passed), **evidence})

    missing = [str(p) for p in [args.original, args.candidate, args.metadata] if not p.exists()]
    if missing:
        report["missing"] = missing
        save()
        print("WAIT: " + ", ".join(missing))
        return 2
    report["status"] = "RUNNING"
    try:
        ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
        if not ffmpeg or not ffprobe:
            raise RuntimeError("ffmpeg and ffprobe must be available on PATH")
        metadata = read_json(args.metadata)
        timeline, spec = read_json(HERE / "timeline.json"), read_json(HERE / "spec.json")
        baseline = read_json(OUT / "render-validation.json")
        input_hashes = {item["file"]: item["sha256"] for item in baseline.get("inputs", [])}
        report["metadata_contents"] = metadata
        report["original_sha256"], report["candidate_sha256"] = sha(args.original), sha(args.candidate)
        check("source_video_identity", metadata.get("source_video_sha256") == report["original_sha256"],
              metadata_source=metadata.get("source_video_sha256"), original=report["original_sha256"])
        hashes = {name: sha(HERE / name) for name in ["spec.json", "timeline.json", "hero-scenes.js", "task-scenes.js"]}
        for name, current in hashes.items():
            check("unchanged_source_" + name, current == input_hashes.get(name),
                  original_render_sha256=input_hashes.get(name), current_sha256=current)
        check("metadata_program_identity", metadata.get("source_spec_sha256") == hashes["spec.json"] and
              metadata.get("source_timeline_sha256") == hashes["timeline.json"],
              spec_sha256=hashes["spec.json"], timeline_sha256=hashes["timeline.json"])
        starts = [e["start"] for e in timeline["entries"] if e["start"] > 0]
        supplied = metadata.get("transition_starts", [])
        check("transition_start_list", len(starts) == len(supplied) and
              all(abs(float(a) - float(b)) < 1e-9 for a, b in zip(starts, supplied)),
              expected=starts, supplied=supplied)
        stage = (HERE / "stage.mjs").read_text(encoding="utf-8").replace(" ", "")
        check("gold_sweep_removed", metadata.get("gold_sweep_removed") is True and
              "local<.22" not in stage and "assets.transitionCanvas" in stage and "local<.45" in stage,
              metadata_flag=metadata.get("gold_sweep_removed"), stage_sha256=sha(HERE / "stage.mjs"))
        check("patch_stage_identity", metadata.get("stage_sha256") == sha(HERE / "stage.mjs"),
              metadata_stage=metadata.get("stage_sha256"), current_stage=sha(HERE / "stage.mjs"))
        check("gentle_crossdissolve_length", abs(float(metadata.get("transition_seconds", -1)) - .45) < 1e-12 and
              "p*p*(3-2*p)" in stage, seconds=metadata.get("transition_seconds"), easing="smoothstep")
        check("production_patch_not_test", metadata.get("test_only") is False and
              int(metadata.get("overlay_frames", -1)) == FRAMES, overlay_frames=metadata.get("overlay_frames"))
        report["scene_program"] = [{"id": s["id"], "type": s["type"], "title": s["title"], "owner": s.get("owner", ""),
                                    "intervals": [{k: e.get(k) for k in ["kind", "cut_index", "start_frame", "end_frame", "start", "end"]}
                                                  for e in timeline["entries"] if e["section_id"] == s["id"]]}
                                   for s in spec["sections"]]
        save()
        print("Checking final MP4 metadata, decoded frames and encoded AAC packets…", flush=True)
        original_meta, candidate_meta = probe(args.original, ffprobe), probe(args.candidate, ffprobe)
        ov = next(s for s in original_meta["streams"] if s["codec_type"] == "video")
        cv = next(s for s in candidate_meta["streams"] if s["codec_type"] == "video")
        oa = next(s for s in original_meta["streams"] if s["codec_type"] == "audio")
        ca = next(s for s in candidate_meta["streams"] if s["codec_type"] == "audio")
        original_count, candidate_count = decoded_frames(args.original, ffprobe), decoded_frames(args.candidate, ffprobe)
        check("video_frame_count", original_count == candidate_count == FRAMES and
              int(ov.get("nb_frames", -1)) == int(cv.get("nb_frames", -1)) == FRAMES,
              original_decoded=original_count, candidate_decoded=candidate_count, expected=FRAMES)
        check("video_dimensions_fps", all(s.get("width") == 1920 and s.get("height") == 1080 and
              Fraction(s["r_frame_rate"]) == FPS and Fraction(s["avg_frame_rate"]) == FPS for s in [ov, cv]),
              original={k: ov.get(k) for k in ["width", "height", "r_frame_rate", "avg_frame_rate"]},
              candidate={k: cv.get(k) for k in ["width", "height", "r_frame_rate", "avg_frame_rate"]})
        original_candidate_delta = abs(float(ov["duration"]) - float(cv["duration"]))
        locked_delta = abs(float(cv["duration"]) - DURATION)
        quantization_tolerance = .001
        check("video_duration_unchanged", original_candidate_delta < 1e-6 and
              locked_delta < quantization_tolerance,
              original=ov["duration"], candidate=cv["duration"], locked=DURATION,
              original_candidate_delta=original_candidate_delta,
              original_candidate_tolerance=1e-6, locked_delta=locked_delta,
              quantization_tolerance_seconds=quantization_tolerance)
        check("container_duration_unchanged", abs(float(original_meta["format"]["duration"]) -
              float(candidate_meta["format"]["duration"])) <= .001,
              original=original_meta["format"]["duration"], candidate=candidate_meta["format"]["duration"])
        audio_fields = ["codec_name", "sample_rate", "channels", "channel_layout", "time_base", "start_time", "extradata_hash"]
        check("audio_stream_parameters", all(oa.get(k) == ca.get(k) for k in audio_fields) and ca["codec_name"] == "aac",
              original={k: oa.get(k) for k in audio_fields}, candidate={k: ca.get(k) for k in audio_fields})
        op, cp = audio_packets(args.original, ffprobe), audio_packets(args.candidate, ffprobe)
        check("aac_packet_payloads_identical", op["payloads"] == cp["payloads"],
              original_packets=op["count"], candidate_packets=cp["count"],
              original_ordered_hash=op["sha256"], candidate_ordered_hash=cp["sha256"])
        check("aac_packet_timing_identical", op["timing"] == cp["timing"], packet_count=cp["count"])
        save()

        sample_dir = OUT / "transition-validation"
        sample_dir.mkdir(parents=True, exist_ok=True)
        final_entry = next(e for e in timeline["entries"] if e["section_id"] == "ending" and e.get("cut_index") == 5)
        previous_time = final_entry["start"] - 1 / FPS
        for local in [.2, .4, 16 / FPS, 296.5 - final_entry["start"]]:
            time = final_entry["start"] + local
            q = 1 - min(1, max(0, (local - MASK["delay"]) / MASK["entrance_duration"]))
            rect = [math.ceil(MASK["x"] + MASK["dx"] * q ** 3) + 4,
                    math.ceil(MASK["y"] + MASK["dy"] * q ** 3) + 4,
                    MASK["w"] - 8, MASK["h"] - 8]
            raw = frame_pixels(args.candidate, time, rect, ffmpeg)
            stats = pixel_stats(raw)
            row = {"time": time, "local_time": local, "inner_mask_rectangle": rect, "pixel_statistics": stats}
            if local < .45:
                # During a dissolve, outgoing card imagery may legitimately show
                # beneath the dark incoming mask. Compare against that known
                # outgoing image rather than falsely demanding a black rectangle.
                previous = frame_pixels(args.original, previous_time, rect, ffmpeg)
                p = max(0, min(1, local / .45))
                alpha = p * p * (3 - 2 * p)
                predicted = [previous[i] * (1 - alpha) + MASK["rgb"][i % 3] * alpha
                             for i in range(len(previous))]
                observed_luma, expected_luma = lumas(raw), [.2126 * predicted[i] + .7152 * predicted[i + 1] + .0722 * predicted[i + 2]
                                                          for i in range(0, len(predicted), 3)]
                differences = [a - b for a, b in zip(observed_luma, expected_luma)]
                excess = sum(value > 35 for value in differences)
                mean_error = sum(abs(value) for value in differences) / len(differences)
                passed = excess <= len(differences) * .01 and mean_error < 15
                row["dissolve_reference"] = {"incoming_alpha": alpha, "outgoing_time": previous_time,
                                               "positive_luma_excess_pixels": excess, "mean_absolute_luma_error": mean_error,
                                               "model": "Outgoing decoded pixels blended with the known masked incoming RGB; codec tolerance is allowed."}
            else:
                passed = stats["mean_luma"] < 45 and stats["white_ink_pixels"] <= 15 and stats["orange_ink_pixels"] <= 15
            row["passed"] = passed
            report["score_mask_samples"].append(row)
            check(f"score_mask_{time:.3f}s", passed, evidence=row)
            name = f"score_mask_{time:.3f}s_original-left_soft-right.png"
            comparison(args.original, args.candidate, time, sample_dir / name, ffmpeg)
            report["comparisons"].append({"time": time, "file": str((sample_dir / name).relative_to(OUT)), "purpose": "Score mask and final-card dissolve"})

        chosen = []
        for predicate in [lambda e: e["section_id"] == "opening" and e.get("cut_index") == 1,
                          lambda e: e["section_id"] == "task3" and e["kind"] == "title",
                          lambda e: e["section_id"] == "task3" and e.get("cut_index") == 1 and e["kind"] != "title",
                          lambda e: e["section_id"] == "summary2",
                          lambda e: e["section_id"] == "task11" and e.get("cut_index") == 2]:
            entry = next((e for e in timeline["entries"] if e["start"] > 0 and predicate(e)), None)
            if entry and entry not in chosen:
                chosen.append(entry)
        for index, entry in enumerate(chosen, 1):
            time = entry["start"] + 3 / FPS
            name = f"{index:02d}_{entry['section_id']}_{time:.3f}s_original-left_soft-right.png"
            comparison(args.original, args.candidate, time, sample_dir / name, ffmpeg)
            report["comparisons"].append({"time": time, "section_id": entry["section_id"],
                                           "file": str((sample_dir / name).relative_to(OUT)), "purpose": "Representative scene-entry transition"})
        report["candidate_sha256_after_checks"] = sha(args.candidate)
        check("candidate_unchanged_during_validation", report["candidate_sha256_after_checks"] == report["candidate_sha256"])
        report["status"] = "PASS" if all(item["passed"] for item in report["checks"]) else "FAIL"
    except Exception as error:
        report["status"] = "FAIL"
        report["failure"] = str(error)
    save()
    print(f"{report['status']}: {report_path}")
    failed = [item["check"] for item in report["checks"] if not item["passed"]]
    if failed:
        print("Failed checks: " + ", ".join(failed))
    if report.get("failure"):
        print(report["failure"], file=sys.stderr)
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
