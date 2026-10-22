#!/usr/bin/env python3
"""Rebuild approved source-clock placement, pitch-only voice and locked music."""
from pathlib import Path
import argparse, hashlib, json, math, re, subprocess, sys, wave
import numpy as np

ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'out/showcase-v10'
RATE=48000
SAMPLES=315*RATE
MUSIC_SHA='12d9b6b71aa83859bad9c53becaa74c4b962113a66b6206a0bec57e8057d1af0'
PLAN_SHA='ff38348f4f94a046381dfc29d357e8a6ebfb14224d4ab011e1706725cbda7abf'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pcmsha(x):return hashlib.sha256(x.tobytes()).hexdigest()
def save(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,ensure_ascii=False,indent=2,default=lambda v:v.item()if isinstance(v,np.generic)else str(v))+'\n')
def run(args,**kw):return subprocess.run([str(x)for x in args],check=True,**kw)
def read16(p,channels):
    with wave.open(str(p))as w:
        assert (w.getframerate(),w.getnchannels(),w.getsampwidth())==(RATE,channels,2)
        return np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').copy().reshape(-1,channels)
def write16(p,x):
    with wave.open(str(p),'wb')as w:w.setnchannels(x.shape[1]);w.setsampwidth(2);w.setframerate(RATE);w.writeframes(x.astype('<i2').tobytes())
def float_wav(p,x):
    run(['ffmpeg','-y','-v','error','-f','f32le','-ar',RATE,'-ac','1','-i','pipe:0','-c:a','pcm_f32le',p],input=x.astype('<f4').tobytes())
def measure(p):
    r=run(['ffmpeg','-hide_banner','-nostats','-i',p,'-af','loudnorm=I=-18.5:TP=-1:LRA=7:print_format=json','-f','null','-'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    rows=re.findall(r'\{\s*"input_i".*?\}',r.stderr,re.S)
    assert rows,'Loudness measurement unavailable'
    d=json.loads(rows[-1]);return {k:float(d[k])for k in ['input_i','input_tp','input_lra','input_thresh']}
def rms(x,hop):
    y=x[:len(x)//hop*hop].astype(np.float64).reshape(-1,hop)
    return np.sqrt(np.mean(y*y,axis=1))
def correlation(a,b):
    a=a-a.mean();b=b-b.mean();return float(np.dot(a,b)/math.sqrt(float(np.dot(a,a)*np.dot(b,b))))
def db(v):return float(20*np.log10(max(float(v),1e-15)))
def main():
    p=argparse.ArgumentParser();p.add_argument('--skip-raw',action='store_true');args=p.parse_args()
    OUT.mkdir(parents=True,exist_ok=True);audit=OUT/'audio-audit';audit.mkdir(exist_ok=True)
    authfile=ROOT/'narration/retime-tone-authorization.json';auth=json.loads(authfile.read_text())
    assert auth['authorization_source']=='direct_user_reply_in_current_chat'and auth['pitch_cents']==315 and auth['speech_tempo']==1
    assert sha(ROOT/'narration/retime/approved-plan.json')==PLAN_SHA==auth['approved_proposal_sha256']
    assert auth['duration_seconds']==315 and auth['frames']==9450
    if not args.skip_raw:
        run([sys.executable,ROOT/'place-narration-v10.py','--apply-approved-plan','--raw-only'])
    rawfile=OUT/'narration-raw.wav';raw=read16(rawfile,1)[:,0]
    assert len(raw)==SAMPLES and not np.any(raw[311*RATE:]),'Raw voice/card duration mismatch'
    raw_sha=sha(rawfile)
    binary=OUT/'pitch-narration';stamp=OUT/'pitch-binary-provenance.json';swift=ROOT/'pitch-narration.swift'
    rebuild=not binary.exists()or not stamp.exists()
    if not rebuild:
        old=json.loads(stamp.read_text());rebuild=old.get('source_sha256')!=sha(swift)or old.get('binary_sha256')!=sha(binary)
    if rebuild:
        log=run(['swiftc','-module-cache-path','/private/tmp/media-maker-swift-cache',swift,'-o',binary],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        (OUT/'pitch-compile.log').write_text(log.stdout+log.stderr)
        save(stamp,{'source_sha256':sha(swift),'binary_sha256':sha(binary),'offline_only':True})
    untrimmed=audit/'narration-pitch-untrimmed.wav';engine_receipt=audit/'pitch-engine.json'
    rendered=run([binary,rawfile,untrimmed,engine_receipt],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    (audit/'pitch-engine.log').write_text(rendered.stdout+rendered.stderr)
    engine=json.loads(engine_receipt.read_text())
    assert engine['rate']==1 and engine['pitch_cents']==315 and engine['source_frames']==SAMPLES
    assert engine['smoothness']==32 and engine['render_quality']==127
    assert engine['spectral_coherence']['value']==engine['transient_preservation']['value']==1
    assert engine['reported_latency_seconds']==0 and engine['reported_au_latency_seconds']==0
    decoded=run(['ffmpeg','-v','error','-i',untrimmed,'-f','f32le','-ar',RATE,'-ac','1','-'],stdout=subprocess.PIPE).stdout
    full=np.frombuffer(decoded,dtype='<f4');lead=engine['lead_padding_frames']
    assert len(full)==engine['written_untrimmed_frames']==SAMPLES+5*RATE
    pitched=full[lead:lead+SAMPLES].copy();assert len(pitched)==len(raw)
    source=raw.astype(np.float64)/32768
    coarse_source=rms(source,480);coarse_out=rms(full,480)
    candidates=range(95,106);cs={i:correlation(coarse_source,coarse_out[i:i+len(coarse_source)])for i in candidates};best=max(cs,key=cs.get)
    fine_source=rms(source,48);fine_out=rms(full,48)
    candidates=range(best*10-10,best*10+11);fs={i:correlation(fine_source,fine_out[i:i+len(fine_source)])for i in candidates};best_fine=max(fs,key=fs.get)
    assert abs(best_fine-1000)<=2 and cs[best]>.90 and fs[best_fine]>.70,'Pitch-only source clock changed; review before trimming'
    before=db(np.max(rms(full[:lead],480)));after=db(np.max(rms(full[lead+SAMPLES:],480)))
    assert before< -55 and after< -55,'Discarded flush padding contains possible voice'
    aligned=audit/'narration-pitch-aligned.wav';float_wav(aligned,pitched)
    measured=measure(aligned);gain_db=-18.5-measured['input_i']
    musicfile=ROOT/'assets/bgm/revision9-approved-music.wav';assert sha(musicfile)==MUSIC_SHA
    music_source=read16(musicfile,2);assert len(music_source)==round(314.5*RATE)
    music=np.zeros((SAMPLES,2),dtype='<i2');music[:len(music_source)]=music_source
    def combine(g):
        voice=np.rint(pitched.astype(np.float64)*(10**(g/20))*32768).astype(np.int64)
        summed=voice[:,None]+music.astype(np.int64)
        return voice,summed
    voice,mixed=combine(gain_db)
    desired_peak=32768*10**(-1/20)
    while max(float(np.max(np.abs(mixed))),float(np.max(np.abs(voice))))>desired_peak:
        gain_db-=.1;voice,mixed=combine(gain_db)
    assert np.max(np.abs(mixed))<32767 and np.max(np.abs(voice))<32767
    voice16=voice.astype('<i2').reshape(-1,1);mix16=mixed.astype('<i2')
    write16(OUT/'narration.wav',voice16);write16(OUT/'bgm-loop.wav',music);write16(OUT/'audio.wav',mix16)
    voice_level=measure(OUT/'narration.wav');mix_level=measure(OUT/'audio.wav')
    assert abs(voice_level['input_i']-(-18.5))<1.1,'Peak constraint reduced the voice too far'
    assert mix_level['input_tp']<0 and not np.any(mix16==32767)and not np.any(mix16==-32768)
    assert np.array_equal(mix16.astype(np.int32)-voice16.astype(np.int32),music.astype(np.int32))
    assert not np.any(music[len(music_source):])and np.array_equal(music[:len(music_source)],music_source)
    # A pitch processor can leave a very quiet decay after the raw source ends.
    # Measure it explicitly; never truncate/fade the preserved source to force
    # a sample-perfect zero at the visual card boundary.
    card=voice16[311*RATE:,0].astype(np.float64)/32768
    card_peak=db(np.max(np.abs(card)))
    card_first_10ms_rms=db(np.sqrt(np.mean(card[:480]**2)))
    card_after_50ms_zero=not np.any(voice16[311*RATE+2400:])
    card_above_minus55=np.flatnonzero(np.abs(card)>10**(-55/20))
    card_tail_ms=(int(np.flatnonzero(card)[-1])+1)/48 if np.any(card)else 0
    card_quiet=card_peak< -50 and card_first_10ms_rms< -60 and card_after_50ms_zero
    assert card_quiet,'Possible audible voice remains in the final card; review without truncating words'
    assert sha(rawfile)==raw_sha
    inputfiles=['mix-v10-audio.py','pitch-narration.swift','audio.py','place-narration-v10.py','timeline.json','spec.json',
        'narration/retime-tone-authorization.json','narration/retime/approved-plan.json','narration/retime/independent-review.json',
        'narration/two-part-sources.json','narration/placement-manifest.json','assets/bgm/revision9-approved-music.wav']
    inputs=[{'file':s,'sha256':sha(ROOT/s)}for s in inputfiles]
    files={n:{'file':n,'sha256':sha(OUT/n),'samples':SAMPLES,'sample_rate':RATE,'channels':1 if n.startswith('narration')else 2}for n in ['narration-raw.wav','narration.wav','bgm-loop.wav','audio.wav']}
    dsp={'status':'PASS','scope':'Authorized pitch-only clock/flush/level processing; final speech recognition and human listening are separate.',
        'authorization_sha256':sha(authfile),'source_raw_sha256':raw_sha,'engine_receipt_sha256':sha(engine_receipt),
        'pitch_cents':315,'speech_tempo':1,'source_samples':SAMPLES,'aligned_samples':SAMPLES,'lead_samples':lead,
        'coarse_envelope_correlation':cs[best],'fine_envelope_correlation':fs[best_fine],
        'observed_envelope_offset_ms':best_fine-1000,'untrimmed_sha256':sha(untrimmed),'aligned_float_sha256':sha(aligned),
        'discarded_before_peak_10ms_rms_dbfs':before,'discarded_after_peak_10ms_rms_dbfs':after,
        'constant_gain_db':gain_db,'voice_level':voice_level,'final_card_voice_peak_dbfs':card_peak,
        'final_card_first_10ms_rms_dbfs':card_first_10ms_rms,'final_card_after_50ms_literal_zero':card_after_50ms_zero,
        'final_card_processor_tail_ms':card_tail_ms,
        'final_card_above_minus55_duration_ms':len(card_above_minus55)/48,
        'final_card_raw_literal_zero':True,'processor_tail_was_not_cut_or_faded':True,
        'formant_preservation_claimed':False,'subjective_tone_match_claimed':False,'inputs':inputs}
    save(OUT/'dsp-validation.json',dsp)
    checks={'approved_315_second_audio_clock':len(raw)==SAMPLES,'authorized_rate_one_pitch315':True,
        'offline_pitch_flush_and_alignment':abs(best_fine-1000)<=2,'music_complete_prefix_pcm_exact':np.array_equal(music[:len(music_source)],music_source),
        'only_half_second_music_zero_tail_added':len(music)-len(music_source)==24000,'integer_voice_plus_music_sum_exact':True,
        'no_sample_clipping':np.max(np.abs(mixed))<32767,'true_peak_below_zero':mix_level['input_tp']<0,
        'final_card_contains_only_measured_sub50ms_quiet_processor_decay':card_quiet,'raw_source_clock_unchanged':sha(rawfile)==raw_sha}
    report={'revision':10,'status':'PASS','generation_mode':'two_part_with_user_authorization','two_part_exception_authorized':True,
        'speech_tempo':1,'tempo':1,'pitch_cents':315,'duration_seconds':315,'frames':9450,'sample_rate':RATE,'samples':SAMPLES,
        'source_identity_sha256':auth['source_identity_sha256'],'timeline_sha256':sha(ROOT/'timeline.json'),
        'placement_manifest_sha256':sha(ROOT/'narration/placement-manifest.json'),'audio_sha256':sha(OUT/'audio.wav'),
        'music_source_sha256':MUSIC_SHA,'music_source_pcm_sha256':pcmsha(music_source),'music_output_pcm_sha256':pcmsha(music),
        'constant_voice_gain_db':gain_db,'voice_measurement':voice_level,'mix_measurement':mix_level,
        'files':files,'checks':checks,'checks_passed':sum(checks.values()),'checks_total':len(checks),'inputs':inputs,
        'limitations':['All68 utterances after DSP must be checked in the separately bound final speech receipt.','Technical processing checks are separate from subjective tone and pronunciation acceptance.']}
    save(ROOT/'narration/audio-processing-manifest.json',{'revision':10,'authorization':str(authfile.relative_to(ROOT)),
        'speech_tempo':1,'pitch_cents':315,'generation_mode':report['generation_mode'],'timeline_sha256':report['timeline_sha256'],
        'source_identity_sha256':report['source_identity_sha256'],'placement_manifest_sha256':report['placement_manifest_sha256'],
        'pitch_source':'pitch-narration.swift','pitch_source_sha256':sha(swift),'constant_voice_gain_db':gain_db,
        'raw_source_sha256':raw_sha,'music_source':'assets/bgm/revision9-approved-music.wav','music_source_sha256':MUSIC_SHA,
        'music_zero_tail_samples':24000,'outputs':files})
    save(OUT/'audio-validation.json',report)
    print(json.dumps({'status':'PASS','duration':315,'pitch_cents':315,'gain_db':gain_db,'checks':len(checks),'voice_lufs':voice_level['input_i'],'mix_true_peak':mix_level['input_tp']}))
if __name__=='__main__':main()
