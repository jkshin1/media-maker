#!/usr/bin/env python3
"""Validate current Revision10 media and separately bound technical reviews."""
from pathlib import Path
import json
from finish import ROOT,OUT,PLAN_SHA,SOURCE_ID,preflight,load,save,sha,locate,binding_rows,receipt_good,has_hash

POST_RECEIPTS=['mux-validation.json','playback-validation.json','encoded-visual-review.json','encoded-audio-validation.json']

def main():
    checks,receipts,missing,tl=preflight()
    def add(name,passed,details=None):checks[name]={'pass':bool(passed),'details':details}
    for name in POST_RECEIPTS:
        path=OUT/name
        if not path.is_file():missing.append(name);add('receipt_'+name,False,'MISSING_EVIDENCE');continue
        try:
            receipts[name]=load(path);r=receipts[name]
            mux_technical=name=='mux-validation.json' and r.get('status')=='PENDING_FINAL_SPEECH' and r.get('technical_mux_pass') is True and all(r.get('checks',{}).values())
            add('receipt_'+name,receipt_good(r) or mux_technical,r.get('status'))
        except (ValueError,OSError) as exc:add('receipt_'+name,False,str(exc))
    final=OUT/'RD_Process_AI_Fast_Track_Showcase_Revision10.mp4'
    if not final.is_file():missing.append(final.name);add('final_video_present',False,'MISSING_EVIDENCE');video_sha=None
    else:video_sha=sha(final);add('final_video_present',True)
    source_audio=sha(OUT/'audio.wav') if (OUT/'audio.wav').is_file() else None
    voice_sha=sha(OUT/'narration.wav') if (OUT/'narration.wav').is_file() else None
    timeline_sha=sha(ROOT/'timeline.json')
    for name in POST_RECEIPTS:
        r=receipts.get(name,{})
        add('current_final_video_'+name,bool(video_sha) and has_hash(r,video_sha,['final_video_sha256','final_sha256','sha256','file_sha256','video_sha256']))
        bad=[]
        for row in binding_rows(r):
            path=locate(row['file'])
            if not path.is_file() or sha(path)!=row['sha256']:bad.append(row['file'])
        add('current_inputs_'+name,not bad,{'mismatches':bad})
    mux=receipts.get('mux-validation.json',{});encoded=receipts.get('encoded-audio-validation.json',{});play=receipts.get('playback-validation.json',{})
    add('mux_current315s_clock_and_PCM',mux.get('pcm_mix_sha256')==source_audio and mux.get('timeline_sha256')==timeline_sha and mux.get('frames')==9450 and mux.get('duration_seconds')==315 and mux.get('audio_target_bitrate')==256000)
    add('encoded_audio_current_mix_voice_and_source_identity',encoded.get('mixed_source_sha256')==source_audio and encoded.get('narration_sha256')==voice_sha and encoded.get('timeline_sha256')==timeline_sha and encoded.get('source_identity_sha256')==SOURCE_ID)
    actual=play.get('actual',{})
    add('actual_continuous_browser_playback_ended_at_rate1',actual.get('ended') is True and actual.get('rate')==1 and play.get('sha256_after_playback')==video_sha and play.get('persisted_screenshots',0)>=69,{'scope':'Continuous browser playback and persisted visual samples; subjective human listening is not implied.'})
    if play.get('expected',{}).get('duration') is not None:add('playback_expected315s',abs(play['expected']['duration']-315)<.001)
    if actual.get('currentTime') is not None:add('playback_reached315s',abs(actual['currentTime']-315)<.05)
    # Every mux prerequisite is explicitly bound, so a later report edit or a
    # rerun with different PCM cannot inherit an earlier successful mux gate.
    stale=[]
    for row in mux.get('preflight_receipts',[]):
        path=OUT/row['file']
        if not path.is_file() or sha(path)!=row['sha256']:stale.append(row['file'])
    add('mux_prerequisite_receipts_unchanged',bool(mux.get('preflight_receipts')) and not stale,{'mismatches':stale})
    passed=sum(c['pass'] for c in checks.values());complete=passed==len(checks) and not missing
    result={'revision':10,'status':'PASS' if complete else 'PENDING' if missing else 'FAIL','production_complete':complete,'human_acceptance':'PENDING_USER_REVIEW','final_sha256':video_sha,'duration_seconds':315,'frames':9450,'speech_tempo':1,'pitch_cents':315,'generation_mode':'two_part_with_user_authorization','two_part_exception_authorized':True,'retime_exception_authorized':True,'approved_plan_sha256':PLAN_SHA,'source_identity_sha256':SOURCE_ID,'timeline_sha256':timeline_sha,'missing_evidence':missing,'checks':checks,'checks_passed':passed,'checks_total':len(checks),'input_bindings':{'finish.py':sha(ROOT/'finish.py'),'validate-final.py':sha(Path(__file__).resolve()),'timeline.json':timeline_sha},'receipts':[{'file':name,'sha256':sha(OUT/name),'status':r.get('status')} for name,r in receipts.items()],'limitations':['This technical completion gate does not claim subjective human tone/pronunciation acceptance. ASR variants remain in the final speech receipt.','Source archive CRC/hash and fresh-source reproduction are verified separately.','The final card has zero raw narration; measured quiet pitch-processor decay is explicitly documented rather than cut or faded.']}
    save(OUT/'final-validation.json',result);print(json.dumps({'status':result['status'],'checks_passed':passed,'checks_total':len(checks),'missing':missing,'video_sha256':video_sha}));raise SystemExit(0 if complete else 2)

if __name__=='__main__':main()
