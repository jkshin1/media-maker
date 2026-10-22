#!/usr/bin/env python3
"""Import the one completed generation; this never calls speech generation."""
from pathlib import Path
import argparse, hashlib, json, subprocess, urllib.request, wave

ROOT = Path(__file__).resolve().parent
def sha(data): return hashlib.sha256(data).hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--fetch', action='store_true')
    args = parser.parse_args()
    receipt = json.loads((ROOT/'narration/generation-receipt.private.json').read_text())
    generation = receipt['generations'][0]
    assert len(receipt['generations']) == receipt['generations_count'] == 1
    assert generation['status'] == 'completed'
    destination = ROOT/'narration/elevenlabs'
    destination.mkdir(exist_ok=True)
    original = destination/f"generated-{generation['id']}.mp3"
    if not original.exists():
        assert args.fetch, 'The completed provider MP3 must be downloaded with --fetch once.'
        with urllib.request.urlopen(generation['content_url'], timeout=60) as response:
            content = response.read()
        assert len(content) > 100000
        original.write_bytes(content)
    master = destination/'take.wav'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(original), '-ar', '48000', '-ac', '1', '-c:a', 'pcm_s16le', str(master)], check=True)
    with wave.open(str(master)) as stream:
        params = stream.getparams()
        pcm = stream.readframes(params.nframes)
    prompt = ROOT/'narration/generated-prompt.txt'
    assert receipt['requested_prompt']+'\n' == prompt.read_text()
    proof = {key: receipt[key] for key in ['flow_id','node_id','session_ids','voice_id','model_id','generation_mode','generations_count']}
    proof.update(generation_id=generation['id'], provider_status=generation['status'], provider_duration_seconds=generation['duration_secs'], provider_price=generation['price'], original_file=original.relative_to(ROOT).as_posix(), original_sha256=sha(original.read_bytes()), master_file=master.relative_to(ROOT).as_posix(), master_sha256=sha(master.read_bytes()), master_pcm_sha256=sha(pcm), samples=params.nframes, sample_rate=params.framerate, channels=params.nchannels, sample_width=params.sampwidth, source_seconds=params.nframes/params.framerate, prompt_file=prompt.relative_to(ROOT).as_posix(), prompt_file_sha256=sha(prompt.read_bytes()), requested_prompt_sha256=sha(receipt['requested_prompt'].encode()), tone_preview_selected=4, tone_generation_id='jNBpdsn3DW247ttAh5dS', pitch_or_tempo_applied_to_original=False, completeness='PENDING_LOCAL_ASR_AND_WAVEFORM_REVIEW', settings_limit='Connected schema exposes voice/language only. No stability, similarity or generation-speed parameter is claimed as applied.')
    (destination/'import-provenance.json').write_text(json.dumps(proof, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(proof, ensure_ascii=False))

if __name__ == '__main__': main()
