#!/usr/bin/env python3
"""Gate the scoped natural-voice revision and unchanged visual/audio clock."""
from pathlib import Path
import hashlib,json,wave

ROOT=Path(__file__).resolve().parent;OUT=ROOT.parent/'out/showcase-v11'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def good(d):return str(d.get('status','')).startswith('PASS')and bool(d.get('checks'))and all(v.get('pass')is True if isinstance(v,dict)else v is True for v in d['checks'].values())
def main():
    checks={};reports={};missing=[]
    names=['audio-validation.json','independent-audio-validation.json','speech-preservation-validation.json','mux-validation.json','visual-preservation-validation.json','encoded-audio-validation.json']
    for name in names:
        p=OUT/name
        if not p.exists():missing.append(name);checks['receipt_'+name]=False;continue
        d=load(p);reports[name]=d;checks['receipt_'+name]=good(d)
    audio=reports.get('audio-validation.json',{});ind=reports.get('independent-audio-validation.json',{});speech=reports.get('speech-preservation-validation.json',{})
    mux=reports.get('mux-validation.json',{});visual=reports.get('visual-preservation-validation.json',{});encoded=reports.get('encoded-audio-validation.json',{})
    provenance=load(ROOT/'baseline-provenance.json');timeline=load(ROOT/'timeline.json');auth=load(ROOT/'authorization.json')
    video=OUT/'RD_Process_AI_Fast_Track_Showcase_Revision11.mp4';vh=sha(video)if video.exists()else None
    checks['final_video_exists']=video.exists()
    checks['same_exact315s_timeline']=sha(ROOT/'timeline.json')==provenance['timeline_sha256']==sha(ROOT/'visual-source-v10/timeline.json')and timeline['frames']==9450 and timeline['duration']==315
    checks['direct_pitch_removal_authorization']=auth['authorization_source']=='direct_user_request_in_current_chat'and auth['pitch_shift_cents']==0 and auth['pitch_or_time_processor_allowed']is False
    checks['natural_voice_rate1_no_pitch_processor']=audio.get('pitch_cents')==0 and audio.get('speech_tempo')==1 and audio.get('no_pitch_processor')is True and audio.get('no_time_processor')is True
    checks['all_original68_speech_unchanged']=speech.get('spoken_lines_preserved')==68 and speech.get('safe_boundary_count')==67 and speech.get('source_identity_sha256')==audio.get('source_identity_sha256')
    checks['current_speech_and_independent_review_bindings']=speech.get('audio_validation_sha256')==sha(OUT/'audio-validation.json')and speech.get('audio_processing_manifest_sha256')==sha(ROOT/'audio-processing-manifest.json')and speech.get('independent_audio_review_sha256')==sha(OUT/'independent-audio-validation.json')and speech.get('narration_sha256')==audio.get('files',{}).get('narration.wav',{}).get('sha256')
    checks['independent_whole_voice_single_gain_identity']=ind.get('voice_changed_sample_count_vs_single_gain')==0 and ind.get('maximum_absolute_sample_error')==0 and ind.get('narration_sha256')==audio.get('files',{}).get('narration.wav',{}).get('sha256')
    mismatches=[]
    for name,r in reports.items():
        b=r.get('input_bindings',{})
        rows=b.items()if isinstance(b,dict)else((x['file'],x['sha256'])for x in b)
        for path,h in rows:
            p=ROOT/path
            if not p.is_file()or sha(p)!=h:mismatches.append({'receipt':name,'file':path})
    checks['current_scoped_input_bindings']=not mismatches
    errors=[]
    for n,channels in [('narration-raw.wav',1),('narration.wav',1),('bgm-loop.wav',2),('audio.wav',2)]:
        p=OUT/n
        try:
            with wave.open(str(p))as w:assert(w.getframerate(),w.getnchannels(),w.getsampwidth(),w.getnframes())==(48000,channels,2,15120000)
            assert sha(p)==audio['files'][n]['sha256']
        except (OSError,AssertionError,KeyError,wave.Error):errors.append(n)
    checks['four_current315s_48kWAVs']=not errors
    checks['raw_original_byte_identity']=audio.get('files',{}).get('narration-raw.wav',{}).get('sha256')==provenance['baseline_raw_sha256']
    checks['music_byte_identity']=audio.get('files',{}).get('bgm-loop.wav',{}).get('sha256')==provenance['baseline_music_sha256']
    for name in ['mux-validation.json','visual-preservation-validation.json','encoded-audio-validation.json']:
        r=reports.get(name,{})
        checks['actual_final_video_'+name]=vh is not None and r.get('final_video_sha256',r.get('final_sha256'))==vh
    checks['current_mux_mix_and_clock']=mux.get('pcm_mix_sha256')==audio.get('audio_sha256')and mux.get('duration_seconds')==315 and mux.get('frames')==9450
    checks['visual_packets_and_reused_full_playback_proof']=visual.get('video_stream_sha256')==mux.get('video_stream_sha256')and visual.get('mux_validation_sha256')==sha(OUT/'mux-validation.json')and visual.get('baseline_full_playback_sha256')==sha(ROOT/'baseline-reviews/playback-validation.json')
    checks['current_AAC_source_mix_and_voice']=encoded.get('mixed_source_sha256')==audio.get('audio_sha256')and encoded.get('narration_sha256')==audio.get('files',{}).get('narration.wav',{}).get('sha256')
    snapshots=[r for r in provenance['source_files']if not(ROOT/'visual-source-v10'/r['file']).is_file()or sha(ROOT/'visual-source-v10'/r['file'])!=r['sha256']]
    checks['original172_source_snapshot_unchanged']=not snapshots and len(provenance['source_files'])==172
    mdqa=load(OUT/'narration-timeline-validation.json');checks['68_MD_lines_and_times_unchanged']=mdqa['status']=='PASS'and mdqa['spoken_entries']==68 and mdqa['timestamps_and_text_unchanged']is True
    complete=not missing and all(checks.values())
    report={'revision':11,'status':'PASS'if complete else'PENDING'if missing else'FAIL','production_complete':complete,'human_acceptance':'PENDING_USER_REVIEW',
        'final_sha256':vh,'duration_seconds':315,'frames':9450,'speech_tempo':1,'pitch_cents':0,'source_identity_sha256':audio.get('source_identity_sha256'),
        'timeline_sha256':sha(ROOT/'timeline.json'),'checks':checks,'checks_passed':sum(checks.values()),'checks_total':len(checks),'missing_evidence':missing,'input_mismatches':mismatches,
        'receipts':[{'file':n,'sha256':sha(OUT/n),'status':d['status']}for n,d in reports.items()],
        'input_bindings':{n:sha(ROOT/n)for n in ['audio.py','finish.py','validate-final.py','review-encoded-audio.py','authorization.json','baseline-provenance.json','timeline.json','audio-processing-manifest.json']},
        'scope_limits':['No new TTS, pitch, time, EQ or compression processing. Original Kyung source waveform is preserved apart from one constant level multiplier and PCM quantization.','Current315s video packets are identical to the previously fully replayed visual track; no redundant new browser playback or visual render was performed.','Original-source ASR spelling uncertainties remain in historical baseline speech review; this revision introduces no new words or phonemes. Subjective human listening acceptance is pending.','Source archive/fresh four-WAV reproduction is verified separately.']}
    (OUT/'final-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':report['status'],'passed':sum(checks.values()),'total':len(checks),'missing':missing,'failed':[k for k,v in checks.items()if not v]}));raise SystemExit(0 if complete else 2)
if __name__=='__main__':main()
