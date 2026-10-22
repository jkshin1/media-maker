#!/usr/bin/env python3
"""Bind final media, complete speech and approved pause edits to current sources."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parent
WORKSPACE=ROOT.parent
OUT=WORKSPACE/'out/showcase-v9'
def load(p):return json.loads(p.read_text())
def sha(p):
    h=hashlib.sha256()
    with p.open('rb')as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def locate(n):
    p=Path(n)
    return p if p.is_absolute()else WORKSPACE/p if p.parts[0].startswith('showcase-v')or p.parts[0]=='out'else ROOT/p
def main():
    names=['render-validation.json','visual-validation.json','audio-validation.json','mux-validation.json',
           'playback-validation.json','narration-coverage-validation.json','pause-edit-review.json',
           'native-visual-review.json','encoded-visual-review.json','encoded-audio-validation.json']
    assert all((OUT/n).exists()for n in names),'Required actual media reviews are not complete.'
    rs={n:load(OUT/n)for n in names};tl=load(ROOT/'timeline.json')
    video=OUT/'RD_Process_AI_Fast_Track_Showcase_Revision9.mp4';vh=sha(video);checks={}
    def add(k,v,details=None):checks[k]={'pass':bool(v),'details':details}
    for n,r in rs.items():add('receipt_'+n,r.get('status')=='PASS')
    for n in ['mux-validation.json','playback-validation.json','encoded-audio-validation.json','encoded-visual-review.json']:
        add('video_binding_'+n,vh in [rs[n].get(k)for k in ['sha256','file_sha256','video_sha256','final_sha256']])
    changed=[];bindings=0
    for n,r in rs.items():
        for row in r.get('inputs',[])+r.get('input_bindings',[])+[{'file':k,'sha256':v}for k,v in r.get('source_hashes',{}).items()]:
            p=locate(row['file']);bindings+=1
            if not p.is_file()or sha(p)!=row['sha256']:changed.append({'receipt':n,'file':row['file']})
    add('current_input_bindings',not changed,{'count':bindings,'mismatches':changed})
    add('timeline68_plus_card',not tl.get('preview_only')and tl['revision']==9 and len(tl['entries'])==69 and len(tl['audio_segments'])==68)
    add('hard315_without_acceleration',tl['tempo']==1 and tl['duration']<=315 and tl['frames']<=9450 and all(s['tempo']==1 for s in tl['audio_segments']))
    add('contiguous_video_frames',tl['entries'][0]['start_frame']==0 and tl['entries'][-1]['end_frame']==tl['frames']and all(a['end_frame']==b['start_frame']for a,b in zip(tl['entries'],tl['entries'][1:])))
    add('card_four_seconds',tl['entries'][-1]['kind']=='silent'and tl['entries'][-1]['end_frame']-tl['entries'][-1]['start_frame']==120)
    audio=rs['audio-validation.json'];mux=rs['mux-validation.json'];p=rs['playback-validation.json']
    speech=rs['narration-coverage-validation.json'];pause=rs['pause-edit-review.json']
    add('actual_speech_and_pause_review_bindings',speech.get('working_master_sha256')==audio.get('working_master_sha256')
        and speech.get('timeline_sha256')==sha(ROOT/'timeline.json')
        and speech.get('pause_edit_map_sha256')==audio.get('pause_edit_map_sha256')
        and speech.get('plan_sha256')==pause.get('plan_sha256')==audio.get('approved_pause_plan_sha256')
        and speech.get('spoken_samples_removed')==0 and speech.get('spoken_lines_present')==68
        and speech.get('safe_boundaries')==67 and speech.get('speech_tempo')==1)
    add('render_pcm_mux_bindings',sha(OUT/'video_silent.mp4')==rs['render-validation.json']['sha256']and sha(OUT/'audio.wav')==audio['audio_sha256']==mux['pcm_mix_sha256'])
    add('authorized_original_speed_ending',audio.get('ending_reuse_exception_authorized')is True and audio.get('generation_mode')=='single_take_with_authorized_original_ending_reuse'and audio.get('fresh_body_narration')is True and audio['tempo']==1)
    add('continuous_cua_browser_playback',p.get('actual',{}).get('ended')is True and p.get('actual',{}).get('rate')==1 and p.get('actual',{}).get('muted')is True and p.get('persisted_screenshots')==71 and p.get('sha256_after_playback')==vh and all(p.get('checks',{}).values()),{'scope':'Muted continuous decoding and visual samples; subjective human listening remains separate.'})
    original=ROOT/'narration/elevenlabs/take.wav'
    add('incomplete_original_preserved',sha(original)=='b2e19801305df1f1e2624fca327b14943f9d04f696271869b09225afc42ba12b')
    base=load(ROOT/'baseline-v8-provenance.json')
    changes=[r['file']for r in base['files']if sha(WORKSPACE/'showcase-v8'/r['file'])!=r['sha256']]
    add('all_revision8_source_unchanged',not changes,{'files':len(base['files']),'changed':changes})
    add('revision8_video_unchanged',sha(WORKSPACE/'out/showcase-v8/RD_Process_AI_Fast_Track_Showcase_Revision8.mp4')=='b39b15513c15de7978fe9cf329a72eb786d3518be8d0a0bb9ec6bdf8db819521')
    add('accepted_revision6_video_unchanged',sha(WORKSPACE/'out/showcase-v6/RD_Process_AI_Fast_Track_Showcase_Revision6.mp4')=='fda536f61d1fba62a920b4cbbd64e5fb1b9739868e52282a317a5e4d9a4e2e3c')
    passed=sum(c['pass']for c in checks.values())
    result={'revision':9,'status':'PASS'if passed==len(checks)else'FAIL','created_at_utc':datetime.now(timezone.utc).isoformat(),
            'final_sha256':vh,'duration_seconds':tl['duration'],'frames':tl['frames'],'preview_only':False,
            'production_complete':passed==len(checks),'human_acceptance':'PENDING_USER_REVIEW','checks':checks,
            'checks_passed':passed,'checks_total':len(checks),
            'receipts':[{'file':n,'sha256':sha(OUT/n),'status':r['status']}for n,r in rs.items()],
            'limitations':['ASR notation variants and their regional reviews are retained in the speech receipt.','Whole muted browser playback and objective audio checks do not constitute subjective human listening acceptance.','Source archive reproduction is recorded separately.']}
    (OUT/'final-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'checks_passed':passed,'checks_total':len(checks),'video_sha256':vh}))
    assert passed==len(checks)
if __name__=='__main__':main()
