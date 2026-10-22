#!/usr/bin/env python3
"""Check the final MP4's decoded AAC against the approved mixed PCM clock."""
from pathlib import Path
import hashlib,json,math,re,subprocess,wave
import numpy as np

ROOT=Path(__file__).resolve().parent;OUT=ROOT.parent/'out/showcase-v11'
RATE=48000;SAMPLES=315*RATE
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(args,**kw):return subprocess.run([str(x)for x in args],check=True,**kw)
def level(x):return float(20*np.log10(max(float(np.sqrt(np.mean(x*x))),1e-15)))
def main():
    film=OUT/'RD_Process_AI_Fast_Track_Showcase_Revision11.mp4'
    mixed=OUT/'audio.wav';voice=OUT/'narration.wav'
    timeline=json.loads((ROOT/'timeline.json').read_text())
    assert timeline['duration']==315 and timeline['frames']==9450
    original_sha=sha(film)
    with wave.open(str(mixed))as w:
        assert(w.getframerate(),w.getnchannels(),w.getsampwidth(),w.getnframes())==(RATE,2,2,SAMPLES)
        source=np.frombuffer(w.readframes(SAMPLES),dtype='<i2').astype(np.float64).reshape(-1,2)/32768
    decoded=run(['ffmpeg','-v','error','-xerror','-i',film,'-map','0:a:0','-f','f32le','-ar',RATE,'-ac','2','-'],stdout=subprocess.PIPE).stdout
    actual=np.frombuffer(decoded,dtype='<f4').astype(np.float64).reshape(-1,2)
    assert len(actual)>=SAMPLES and len(actual)-SAMPLES<=1024
    paired=actual[:SAMPLES];error=paired-source
    correlation=float(np.sum(paired*source)/math.sqrt(float(np.sum(paired*paired)*np.sum(source*source))))
    snr_db=level(source)-level(error)
    blocks=[]
    for start in range(0,SAMPLES,RATE):
        a=source[start:start+RATE];b=paired[start:start+RATE]
        al=level(a);bl=level(b)
        blocks.append({'start_seconds':start/RATE,'source_rms_dbfs':al,'decoded_rms_dbfs':bl,'difference_db':bl-al})
    active=[r for r in blocks if r['source_rms_dbfs']> -55]
    peak=float(np.max(np.abs(actual)));extra=actual[SAMPLES:]
    extra_peak=float(np.max(np.abs(extra)))if len(extra)else 0
    log=run(['ffmpeg','-hide_banner','-nostats','-i',film,'-map','0:a:0','-af','loudnorm=I=-18.5:TP=-1:LRA=7:print_format=json','-f','null','-'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    metrics=json.loads(re.findall(r'\{\s*"input_i".*?\}',log.stderr,re.S)[-1])
    checks={'final_input_stable':sha(film)==original_sha,'full_315_second_audio_decodes':len(actual)>=SAMPLES,
        'AAC_padding_at_most_one_frame':len(actual)-SAMPLES<=1024,
        'decoded_waveform_matches_source_clock':correlation>.99,'codec_signal_to_error_ratio_above_20dB':snr_db>20,
        'no_one_second_active_block_dropout':all(abs(r['difference_db'])<1 for r in active),
        'decoded_peak_below_full_scale':peak<1,'measured_true_peak_below_zero':float(metrics['input_tp'])<0,
        'AAC_tail_padding_quiet':extra_peak<10**(-60/20)}
    report={'status':'PASS'if all(checks.values())else'FAIL','revision':11,
        'scope':'Actual final AAC strict decoding and comparison with approved voice-plus-music PCM; no subjective listening claim.',
        'final_video':film.name,'final_video_sha256':original_sha,'final_sha256':original_sha,
        'mixed_source_sha256':sha(mixed),'narration_sha256':sha(voice),'timeline_sha256':sha(ROOT/'timeline.json'),
        'source_identity_sha256':timeline['source_identity_sha256'],'decoded_samples':len(actual),'expected_samples':SAMPLES,
        'AAC_padding_samples':len(actual)-SAMPLES,'sample_rate':RATE,'channels':2,'correlation':correlation,
        'signal_to_codec_error_db':snr_db,'decoded_sample_peak':peak,'extra_padding_peak':extra_peak,
        'loudness':metrics,'one_second_block_measurements':blocks,'checks':checks,'checks_passed':sum(checks.values()),'checks_total':len(checks)}
    (OUT/'encoded-audio-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k]for k in ['status','correlation','signal_to_codec_error_db','AAC_padding_samples','checks_passed','checks_total']}))
    if report['status']!='PASS':raise SystemExit(1)
if __name__=='__main__':main()
