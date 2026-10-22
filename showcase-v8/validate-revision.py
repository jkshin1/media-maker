#!/usr/bin/env python3
"""Independent QA for the six scoped Revision 2 changes.

Reads baseline/source/media only. Writes this validator's JSON and text-capture
evidence under out/showcase-v2. Missing completed media/evidence returns WAIT (2),
not PASS. Original narration ASR variants are recorded separately from revision
checks and are not silently reclassified as resolved.
"""
from __future__ import annotations
import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import wave

HERE=Path(__file__).resolve().parent
EXPECTED_SECTIONS=['opening','summary1','task3','task4','task5','summary2','task7','task8','task9','summary3','task11','task12','task13','task14','summary4','task17','task16','ending']

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def pcm(path):
    with wave.open(str(path),'rb') as f:
        assert (f.getframerate(),f.getnchannels(),f.getsampwidth())==(48000,1,2),str(path)
        return f.readframes(f.getnframes())
def run(args,timeout=180):return subprocess.run(args,check=True,capture_output=True,text=True,timeout=timeout)
def path_in(value,root=HERE,out=None):
    p=Path(value)
    for candidate in [p if p.is_absolute() else root/p,root.parent/p,root/'narration'/p.name,(out/p if out else root/p)]:
        if candidate.exists():return candidate
    return p if p.is_absolute() else root/p

TEXT_CAPTURE_JS=r'''
import fs from 'node:fs';import path from 'node:path';import {createRequire} from 'node:module';import {createHash} from 'node:crypto';
const root=process.cwd(),require=createRequire(path.join(root,'package.json'));let native;
try{native=require('@napi-rs/canvas')}catch{native=require('/Users/jk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@napi-rs/canvas')}
const{createCanvas,loadImage,GlobalFonts}=native;const{drawFrame}=await import(path.join(root,'stage.mjs'));
const spec=JSON.parse(fs.readFileSync('spec.json')),timeline=JSON.parse(fs.readFileSync('timeline.json'));
GlobalFonts.registerFromPath(path.join(root,'fonts/NotoSansCJKkr-Regular.otf'),'Noto');GlobalFonts.registerFromPath(path.join(root,'fonts/NotoSansCJKkr-Bold.otf'),'Noto');
const assets={images:{},backgrounds:{},videos:{},microscopy:{},transitionCanvas:createCanvas(1920,1080),spec,tasks:spec.sections.filter(s=>s.type==='task'),drawTitles:false,drawCaptions:false};
const cache=new Map();async function im(file){if(!cache.has(file))cache.set(file,await loadImage(path.join(root,file)));return cache.get(file)}
for(const file of new Set(spec.sections.map(s=>s.reference_image).filter(Boolean)))assets.images[file]=await im(file);
for(const s of spec.sections){assets.backgrounds[s.id]={};for(let i=0;i<s.cuts.length;i++){const f=s.backgrounds?.[i]||s.cuts[i].photo_crop||s.cuts[i].background||s.photo_crops?.[i];if(f){assets.backgrounds[s.id][i]=await im(f);assets.images[f]=assets.backgrounds[s.id][i]}}}
for(const[id,file]of Object.entries(spec.microscopy||{}))assets.microscopy[id]=await im(file);
for(let i=1;i<=9;i++){const f=`assets/opening/cut${String(i).padStart(2,'0')}.png`;if(fs.existsSync(f))assets.images[`opening${i}`]=await im(f)}
const canvas=createCanvas(1920,1080),ctx=canvas.getContext('2d'),original=ctx.fillText.bind(ctx);let text=[];
ctx.fillText=function(s,x,y,...rest){const m=ctx.getTransform();text.push({text:String(s),x:m.a*x+m.c*y+m.e,y:m.b*x+m.d*y+m.f,alpha:ctx.globalAlpha,font:ctx.font});return original(s,x,y,...rest)};
const hash=()=>createHash('sha256').update(canvas.data()).digest('hex'),records=[];
for(let i=0;i<timeline.entries.length;i++){const e=timeline.entries[i],t=e.end-Math.min(.06,(e.end-e.start)*.05);text=[];const state=drawFrame(ctx,t,timeline,spec,assets),words=text.slice(),one=hash();text=[];drawFrame(ctx,t,timeline,spec,assets);records.push({entry_index:i,section_id:e.section_id,kind:e.kind,cut_index:e.cut_index,cut_id:e.cut_id,time:t,captions:state.captions,text:words,pixels_deterministic:one===hash()})}
console.log(JSON.stringify({records,scope:'Actual native renderer fillText calls and repeated same-time RGBA hashes; not OCR of baked photographs or the encoded MP4.'}));
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    default_baseline=HERE.parent/'showcase' if (HERE.parent/'showcase/spec.json').exists() else HERE/'baseline'
    p.add_argument('--baseline',type=Path,default=default_baseline)
    p.add_argument('--out',type=Path,default=HERE.parent/'out/showcase-v2')
    p.add_argument('--video',type=Path)
    p.add_argument('--speech-map',type=Path,default=HERE/'narration/speech-edit-map.json')
    p.add_argument('--revision-manifest',type=Path,default=HERE/'narration/revision-manifest.json')
    p.add_argument('--node',default='node')
    args=p.parse_args();out=args.out;out.mkdir(parents=True,exist_ok=True)
    video=args.video or out/'RD_Process_AI_Fast_Track_Showcase_Revision2.mp4'
    report_path=out/'revision-validation.json'
    required=[video,HERE/'spec.json',HERE/'timeline.json',HERE/'baseline-provenance.json',args.speech_map,args.revision_manifest,out/'render-validation.json',out/'visual-validation.json',out/'audio-validation.json',out/'narration-raw.wav',out/'audio.wav',out/'video_silent.mp4']
    report={'status':'WAIT','scope':'Six user-requested Revision 2 checks; technical/content PASS is separate from existing narration ASR spelling/phonetic caveats.','video':str(video),'checks':[],'limitations':[]}
    def save():report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    missing=[str(f) for f in required if not f.exists()]
    if missing:
        report['missing']=missing;save();print(json.dumps({'status':'WAIT','missing':missing},ensure_ascii=False));return 2
    report['status']='RUNNING';save()
    def check(name,ok,**data):
        report['checks'].append({'check':name,'passed':bool(ok),**data})
        if not ok:print('FAIL '+name,flush=True)
    try:
        baseline=args.baseline;spec=read(HERE/'spec.json');oldspec=read(baseline/'spec.json');tl=read(HERE/'timeline.json');oldtl=read(baseline/'timeline.json');provenance=read(HERE/'baseline-provenance.json');speech=read(args.speech_map);revision=read(args.revision_manifest)
        frozen_files=[HERE/'spec.json',HERE/'timeline.json',HERE/'stage.mjs',HERE/'hero-scenes.js',HERE/'task-scenes.js',HERE/'narration/ko.json',HERE/'narration/take.wav',args.speech_map,args.revision_manifest,video]
        frozen={str(f):sha(f) for f in frozen_files}
        check('eighteen_sections_order_unchanged',[s['id'] for s in spec['sections']]==EXPECTED_SECTIONS==[s['id'] for s in oldspec['sections']])
        entries=tl['entries'];oldentries=oldtl['entries'];speech_entries=[e for e in entries if e['kind']=='cut']
        signature=lambda e:(e['section_id'],e['kind'],e.get('cut_index'),e.get('cut_id'),e.get('caption',''))
        check('ninety_one_entries_and_seventy_three_speech_cuts',len(entries)==91 and len(speech_entries)==73 and [signature(e) for e in entries]==[signature(e) for e in oldentries],entries=len(entries),speech_cuts=len(speech_entries))
        check('whole_frame_gapless_timeline',tl['fps']==30 and len(entries)>0 and entries[0]['start_frame']==0 and entries[-1]['end_frame']==tl['frames'] and all(e['start_frame']<e['end_frame'] and abs(e['start']-e['start_frame']/30)<1e-7 and abs(e['end']-e['end_frame']/30)<1e-7 for e in entries) and all(a['end_frame']==b['start_frame'] for a,b in zip(entries,entries[1:])) and abs(tl['duration']-tl['frames']/30)<1e-7)
        if tl['duration']>300:check('longer_duration_explicitly_allowed',tl.get('allow_over_five_minutes') is True,duration=tl['duration'])
        start_end=lambda timeline,sid:(min(e['start'] for e in timeline['entries'] if e['section_id']==sid),max(e['end'] for e in timeline['entries'] if e['section_id']==sid))
        oa,ob=start_end(oldtl,'opening');na,nb=start_end(tl,'opening');extra=(nb-na)-(ob-oa)
        check('opening_extended_four_point_five_seconds',abs(extra-4.5)<=1/30+1e-7,baseline_seconds=ob-oa,revised_seconds=nb-na,additional_seconds=extra)
        old_sections={s['id']:s for s in oldspec['sections']};changes=[]
        for sec in spec['sections']:
            prev=old_sections[sec['id']]
            if len(sec['cuts'])!=len(prev['cuts']):changes.append({'section_id':sec['id'],'field':'cut_count'})
            for field in ['type','title','owner','source_md','reference_image','main_lines','support_lines','backgrounds','restrictions']:
                if sec.get(field)!=prev.get(field):changes.append({'section_id':sec['id'],'field':field})
            for cut,oldcut in zip(sec['cuts'],prev['cuts']):
                for field in ['id','title','scene_title','caption','narration','source_narration','visual','motion','screen_lines','support_lines','ui_labels','source_fields','question','cards']:
                    expected='분산된 업무 환경' if oldcut['id']=='task14_cut1' and field=='title' else oldcut.get(field)
                    if cut.get(field)!=expected:changes.append({'cut_id':cut['id'],'field':field})
        check('only_requested_cubic_title_copy_change',not changes,unexpected_copy_changes=changes)
        exact_expected=json.loads(json.dumps(oldspec))
        next(c for s in exact_expected['sections'] for c in s['cuts'] if c['id']=='task14_cut1')['title']='분산된 업무 환경'
        exact_revised={k:v for k,v in spec.items() if k!='presentation_overrides'}
        check('all_unscoped_spec_fields_identical',exact_revised==exact_expected)
        check('original_palette_and_ui_scene_program_preserved',spec.get('palette')==oldspec.get('palette') and sha(HERE/'task-scenes.js')==sha(baseline/'task-scenes.js'))
        snapshot=provenance['input_files']
        immutable=[rel for rel in snapshot if rel.startswith(('reference/','assets/','fonts/')) or rel in ('narration/ko.json','narration/take.wav','narration/manifest.json','narration/full-script.txt','narration/generated-prompt.txt') or re.fullmatch(r'narration/vo\d+\.wav',rel)]
        bad=[]
        for rel in immutable:
            target=HERE/rel
            if not target.exists() or sha(target)!=snapshot[rel]:bad.append(rel)
        md_count=sum(rel.startswith('reference/') and rel.endswith('.md') for rel in immutable)
        check('all_original_md_photos_fonts_bgm_and_narration_inputs_preserved',not bad and md_count==20 and 'narration/take.wav' in immutable,checked_files=len(immutable),md_files=md_count,mismatches=bad)
        # The source ZIP contains a minimal original snapshot for changed code
        # and configuration. All large immutable inputs are proved directly
        # against baseline-provenance hashes rather than duplicated in that ZIP.
        anchors=['spec.json','timeline.json','stage.mjs','hero-scenes.js','task-scenes.js','narration/ko.json','narration/manifest.json','narration/alignment-report.json']
        anchor_failures=[rel for rel in anchors if not (baseline/rel).exists() or rel not in snapshot or sha(baseline/rel)!=snapshot[rel]]
        if (baseline/'reference').exists():
            source_failures=[rel for rel,value in snapshot.items() if not (baseline/rel).exists() or sha(baseline/rel)!=value]
        else:source_failures=[]
        check('baseline_provenance_matches_source',not anchor_failures and not source_failures,source_final_sha256=provenance.get('source_final_sha256'),baseline_mode='complete original directory' if (baseline/'reference').exists() else 'portable minimal original snapshot plus immutable-input hashes',anchor_failures=anchor_failures,original_source_failures=source_failures)
        stage=(HERE/'stage.mjs').read_text();render_source=(HERE/'render.mjs').read_text();hero=(HERE/'hero-scenes.js').read_text();overrides=spec.get('presentation_overrides',{})
        check('global_narration_captions_disabled',overrides.get('narration_captions') is False and 'spec.presentation_overrides?.narration_captions!==false' in stage and 'drawTitles:false,drawCaptions:false' in render_source)
        check('titles_and_core_ui_text_kept','ctx.fillText(cut.title' in stage and 'drawTask(ctx' in stage and 'drawHero(ctx' in stage)
        check('ending_team_labels_exact',overrides.get('award_teams')=={'김지은 TL':'N-PMA','장민희 TL':'DRAM트랙Photo'})
        visual=read(out/'visual-validation.json');records=visual.get('records',[]);motions=visual.get('motion',[])
        check('all_renderer_caption_metadata_empty',len(records)==91 and all(r.get('caption')==[] for r in records),records=len(records))
        check('every_non_title_entry_has_active_motion',len(motions)==79 and all(r.get('moving') is True for r in motions),motion_records=len(motions))
        print('Checking native displayed text and deterministic same-time frames',flush=True)
        captured=json.loads(subprocess.run([args.node,'--input-type=module','-e',TEXT_CAPTURE_JS],cwd=HERE,check=True,capture_output=True,text=True,timeout=120).stdout)
        (out/'revision-text-capture.json').write_text(json.dumps(captured,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        text_records=captured['records'];check('same_time_native_frames_deterministic',len(text_records)==91 and all(r['pixels_deterministic'] for r in text_records))
        check('native_returned_captions_all_empty',all(r['captions']==[] for r in text_records))
        final_card=next(r for r in text_records if r['section_id']=='ending' and r['cut_index']==5);card_text=[t['text'] for t in final_card['text'] if t['alpha']>.5]
        check('team_owner_labels_actually_drawn',all(t in card_text for t in ['N-PMA','DRAM트랙Photo','김지은 TL','장민희 TL']),drawn_team_owner_labels=[t for t in card_text if t in ['N-PMA','DRAM트랙Photo','김지은 TL','장민희 TL']])
        cubic=next(r for r in text_records if r.get('cut_id')=='task14_cut1');cubic_text=[t['text'] for t in cubic['text']]
        check('cubic_before_annotation_absent_in_native_text','분산된 업무 환경' in cubic_text and not any('(Before)' in t for t in cubic_text))
        report['limitations'].append('Native text capture verifies editable text calls; photographed baked text is checked through unchanged approved assets and separate visual review, not OCR.')
        print('Checking exact ordered audio placements and independent speech-end mapping',flush=True)
        processed_info=revision['processed_master'];processed_path=path_in(processed_info.get('path',processed_info.get('file')),out=out);processed=pcm(processed_path);raw=pcm(out/'narration-raw.wav');placements=revision['placements'];cuts={c['cut_id']:c for c in speech['cuts']};per_cut={c['cut_id']:c for c in revision['per_cut_timing']}
        continuous=speech['processed_continuous']
        check('processed_master_file_hash',sha(processed_path)==processed_info['sha256']==continuous['sha256'] and len(processed)//2==processed_info['sample_count']==continuous['sample_count'] and hashlib.sha256(processed).hexdigest()==continuous['pcm_sha256'],sample_count=len(processed)//2)
        config=read(HERE/'narration/ko.json')
        check('same_original_tempo_voice_and_script',abs(revision['tempo_ratio']-oldtl['tempo'])<1e-10 and abs(speech['tempo_ratio']-oldtl['tempo'])<1e-10 and config==read(baseline/'narration/ko.json'))
        check('original_single_take_model_voice_and_no_new_tts',speech.get('new_tts') is False and speech.get('script_unchanged') is True and speech.get('source_config_sha256')==sha(HERE/'narration/ko.json') and speech['source_master']['sha256']==sha(HERE/'narration/take.wav') and all(speech.get(key)==config.get(key) for key in ['voice_id','voice_name','model_id']) and config.get('generation_mode')=='single_take')
        spec_cuts={c['id']:c for sec in spec['sections'] for c in sec['cuts']}
        check('speech_map_covers_exact_original_captions',len(speech['cuts'])==73 and [c['cut_id'] for c in speech['cuts']]==[e['cut_id'] for e in speech_entries] and len(per_cut)==73 and all(c['caption']==spec_cuts[c['cut_id']]['caption'] and c['safe_boundary_sample']>=c['actual_speech_end_sample'] for c in speech['cuts']))
        report['speech_boundary_caveats']=[{'cut_id':c['cut_id'],'confidence':c.get('confidence'),'continuous_start_overlap':c.get('continuous_start_overlap',False),'character_coverage':c.get('character_coverage')} for c in speech['cuts'] if c.get('confidence')=='REVIEWED_CONTINUOUS_SPEECH_VISUAL_ONLY' or c.get('continuous_start_overlap') or c.get('character_coverage',1)<.9]
        preserved=[];placement_failures=[];last_source=0;last_dest_end=0
        for i,pl in enumerate(placements):
            a,b=pl['source_start_sample'],pl['source_end_sample'];dst=pl['timeline_start_sample'];count=pl['sample_count']
            if a!=last_source or b-a!=count or dst<last_dest_end or raw[dst*2:(dst+count)*2]!=processed[a*2:b*2]:placement_failures.append(i)
            if any(raw[last_dest_end*2:dst*2]):placement_failures.append(f'nonzero_inserted_gap_before_{i}')
            preserved.append(processed[a*2:b*2]);last_source=b;last_dest_end=dst+count
        if any(raw[last_dest_end*2:]):placement_failures.append('nonzero_after_final_placement')
        joined=b''.join(preserved)
        check('all_continuous_processed_pcm_preserved_in_order_with_only_zero_inserted',not placement_failures and joined==processed,placements=len(placements),failures=placement_failures,source_pcm_sha256=hashlib.sha256(processed).hexdigest(),reassembled_pcm_sha256=hashlib.sha256(joined).hexdigest())
        timing_rows=[];timing_failures=[]
        for e in speech_entries:
            c=cuts[e['cut_id']];source_end=c['actual_speech_end_sample'];possible=[pl for pl in placements if pl['section_id']==e['section_id'] and pl['source_start_sample']<=source_end<=pl['source_end_sample'] and (pl.get('cut_id') in (None,e['cut_id']))]
            if len(possible)!=1:timing_failures.append({'cut_id':e['cut_id'],'reason':'speech endpoint has no unique source placement'});continue
            pl=possible[0];actual=pl['timeline_start_sample']+source_end-pl['source_start_sample'];margin=e['end']-actual/48000;declared=per_cut[e['cut_id']]
            ok=actual==declared['actual_speech_end_sample'] and abs(declared['visual_end_seconds']-e['end'])<1e-7 and margin>=-1/48000
            if not ok:timing_failures.append({'cut_id':e['cut_id'],'reason':'spoken tail after transition or mapping mismatch','tail_margin_seconds':margin})
            timing_rows.append({'cut_id':e['cut_id'],'transition_start_seconds':e['end'],'actual_speech_end_seconds':actual/48000,'tail_margin_seconds':margin,'confidence':c.get('confidence')})
        check('all_seventy_three_spoken_tails_finish_before_transition',len(timing_rows)==73 and not timing_failures,checked=len(timing_rows),minimum_tail_margin_seconds=min((r['tail_margin_seconds'] for r in timing_rows),default=None),failures=timing_failures)
        report['per_cut_timing']=timing_rows
        quiet_failures=[]
        for e in entries:
            if e['kind'] not in ('title','summary'):continue
            a=round(e['start']*48000);b=round(e['end']*48000);v=array('h',raw[a*2:b*2]);rms=math.sqrt(sum(x*x for x in v)/max(1,len(v)))/32768
            if rms>10**(-45/20):quiet_failures.append({'section_id':e['section_id'],'kind':e['kind'],'rms_dbfs':20*math.log10(rms)})
        check('task_titles_and_summaries_have_no_narration',not quiet_failures,failures=quiet_failures)
        audio=read(out/'audio-validation.json');check('audio_report_pass_and_matches_final_wave',audio.get('status')=='PASS' and audio.get('audio_sha256')==sha(out/'audio.wav'),status=audio.get('status'))
        print('Checking completed MP4 streams and full decode',flush=True)
        meta=json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)]).stdout);vs=[s for s in meta['streams'] if s['codec_type']=='video'];aud=[s for s in meta['streams'] if s['codec_type']=='audio'];sub=[s for s in meta['streams'] if s['codec_type']=='subtitle']
        check('one_video_one_aac_stream_and_no_subtitle_track',len(vs)==1 and len(aud)==1 and not sub,stream_types=[s['codec_type'] for s in meta['streams']])
        v=vs[0];au=aud[0];check('full_hd_thirty_fps_frame_count',v['width']==1920 and v['height']==1080 and v['r_frame_rate']=='30/1' and int(v['nb_frames'])==tl['frames'],width=v['width'],height=v['height'],frames=v.get('nb_frames'),fps=v['r_frame_rate'])
        check('stereo_aac_48000',au['codec_name']=='aac' and int(au['sample_rate'])==48000 and au['channels']==2)
        check('media_duration_matches_revised_timeline',abs(float(meta['format']['duration'])-tl['duration'])<2/30,duration=meta['format']['duration'],timeline=tl['duration'])
        run(['ffmpeg','-v','error','-i',str(video),'-f','null','-']);check('complete_video_and_audio_decode',True)
        packet_hash=lambda f:run(['ffmpeg','-v','error','-i',str(f),'-map','0:v:0','-c:v','copy','-f','hash','-hash','sha256','-']).stdout.strip()
        check('rendered_video_stream_copied_exactly',packet_hash(video)==packet_hash(out/'video_silent.mp4'))
        render=read(out/'render-validation.json');check('render_report_current_inputs_and_native_video_hash',render.get('status')=='PASS' and render.get('sha256')==sha(out/'video_silent.mp4') and all(sha(HERE/r['file'])==r['sha256'] for r in render['inputs']))
        check('validation_input_files_unchanged',all(sha(Path(f))==value for f,value in frozen.items()))
        prior=read(baseline/'narration/alignment-report.json');report['prior_asr_variants_caution']={'status':prior.get('status'),'fresh_audio_generation':False,'text':'Original ASR spelling/pronunciation ambiguities remain inherited. This validator confirms the scoped changes and PCM/timing preservation, not subjective native pronunciation.'}
        report.update({'status':'PASS' if all(c['passed'] for c in report['checks']) else 'FAIL','file_sha256':sha(video),'duration_seconds':float(meta['format']['duration']),'frames':tl['frames'],'fps':30,'opening_seconds':nb-na,'requests_validated':['Finish each cut narration before transition','Remove duplicated bottom narration captions while retaining titles/core UI','Remove Cubic first-title Before annotation','Add exact team labels to the final two cards','Extend opening by 4.5 seconds','Preserve all other MD/copy/style/order/assets']})
    except Exception as exc:
        report.update({'status':'FAIL','failure':f'{type(exc).__name__}: {exc}'})
    save();print(json.dumps({'status':report['status'],'report':str(report_path),'passed':sum(c['passed'] for c in report['checks']),'checks':len(report['checks']),'failure':report.get('failure')},ensure_ascii=False))
    return 0 if report['status']=='PASS' else 1

if __name__=='__main__':sys.exit(main())
