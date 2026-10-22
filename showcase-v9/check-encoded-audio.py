#!/usr/bin/env python3
"""Check final AAC transport against an independent encode of the approved mix."""
from pathlib import Path
import hashlib,json,subprocess

ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'out/showcase-v9'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(a):return subprocess.run(a,check=True,capture_output=True)

def main():
    video=OUT/'RD_Process_AI_Fast_Track_Showcase_Revision9.mp4'
    mix=OUT/'audio.wav';tl=json.loads((ROOT/'timeline.json').read_text())
    audit=OUT/'encoded-audio';audit.mkdir(exist_ok=True)
    reference=audit/'independent-reference.m4a'
    run(['ffmpeg','-y','-v','error','-i',str(mix),'-map','0:a:0','-c:a','aac','-b:a','192k','-ar','48000','-ac','2',str(reference)])
    decoded=[]
    for source in [video,reference]:
        decoded.append(run(['ffmpeg','-v','error','-xerror','-i',str(source),'-map','0:a:0','-f','s16le','-acodec','pcm_s16le','-ar','48000','-ac','2','-']).stdout)
    meta=json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)]).stdout)
    a=next(s for s in meta['streams']if s['codec_type']=='audio')
    samples=len(decoded[0])//4;expected=tl['frames']*1600
    checks={'final_pcm_matches_independent_aac_reference':decoded[0]==decoded[1],
            'decoded_audio_is_nonempty':bool(decoded[0]),'aac_48k_stereo':a['codec_name']=='aac'and a['sample_rate']=='48000'and a['channels']==2,
            'audio_start_zero':abs(float(a.get('start_time',0)))<1/48000,
            'audio_duration_matches':abs(float(a['duration'])-tl['duration'])<1/30,
            'decoded_samples_within_one_aac_padding_frame':expected<=samples<expected+1024,
            'container_within315':float(meta['format']['duration'])<=315.001}
    report={'revision':9,'status':'PASS'if all(checks.values())else'FAIL','checks':checks,
            'final_sha256':sha(video),'mix_sha256':sha(mix),'reference_aac_sha256':sha(reference),
            'final_decoded_pcm_sha256':hashlib.sha256(decoded[0]).hexdigest(),
            'independent_decoded_pcm_sha256':hashlib.sha256(decoded[1]).hexdigest(),
            'decoded_samples':samples,'timeline_samples':expected,'audio_start_time':a.get('start_time'),
            'duration':a['duration'],'tempo':1,
            'scope':'Full final AAC decode equals an independently encoded reference from the verified PCM mix. ASR, source word coverage and subjective listening are separate checks.'}
    (OUT/'encoded-audio-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':report['status'],'checks':checks}))
    assert all(checks.values())
if __name__=='__main__':main()
