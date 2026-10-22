#!/usr/bin/env python3
"""Independent Revision 3 source, layout, and unchanged-audio validation.

Run --source-only before the final video is ready. Complete validation requires
the new native render and MP4. Missing evidence returns WAIT (2), never PASS.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
EXPECTED_V2_SHA='44f841056822f53d0646ee5c55e3968730d9cb96f4c7cbec4088807866b956a2'
ANCHORS=['spec.json','timeline.json','stage.mjs','hero-scenes.js','task-scenes.js','narration/ko.json']
HISTORICAL_URL_JSON={
    'narration/receipt.json','narration/generation-result.json',
    'narration/fast-receipt.json','narration/fast-generation-failure.json',
}

def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def run(args,timeout=180):
    return subprocess.run(args,check=True,capture_output=True,text=True,timeout=timeout)
def packaged_redaction_matches(relative,original_sha,actual_sha,redactions,portable):
    """Only declared historical URL removals may differ in a portable package."""
    record=redactions.get(relative,{})
    return (portable and relative in HISTORICAL_URL_JSON
            and record.get('original_sha256')==original_sha
            and record.get('packaged_sha256')==actual_sha
            and bool(record.get('removed_fields')))

NATIVE_JS=r'''
import fs from 'node:fs';import path from 'node:path';import {createRequire} from 'node:module';import {createHash} from 'node:crypto';
const root=process.cwd(),base=process.env.LAYOUT_BASELINE,require=createRequire(path.join(root,'package.json'));let native;
try{native=require('@napi-rs/canvas')}catch{native=require('/Users/jk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@napi-rs/canvas')}
const {createCanvas,loadImage,GlobalFonts}=native;
const {drawFrame}=await import(path.join(root,'stage.mjs')),{drawFrame:drawOld}=await import(path.join(base,'stage.mjs'));
const {heroSceneContract}=await import(path.join(root,'hero-scenes.js')),{taskSceneContract,getTaskPlacement}=await import(path.join(root,'task-scenes.js'));
const spec=JSON.parse(fs.readFileSync('spec.json')),timeline=JSON.parse(fs.readFileSync('timeline.json'));
GlobalFonts.registerFromPath(path.join(root,'fonts/NotoSansCJKkr-Regular.otf'),'Noto');GlobalFonts.registerFromPath(path.join(root,'fonts/NotoSansCJKkr-Bold.otf'),'Noto');
const assets={images:{},backgrounds:{},videos:{},microscopy:{},transitionCanvas:createCanvas(1920,1080),spec,tasks:spec.sections.filter(s=>s.type==='task'),drawTitles:false,drawCaptions:false},cache=new Map();
async function im(file){if(!cache.has(file))cache.set(file,await loadImage(path.join(root,file)));return cache.get(file)}
for(const file of new Set(spec.sections.map(s=>s.reference_image).filter(Boolean)))assets.images[file]=await im(file);
for(const s of spec.sections){assets.backgrounds[s.id]={};for(let i=0;i<s.cuts.length;i++){const f=s.backgrounds?.[i]||s.cuts[i].photo_crop||s.cuts[i].background||s.photo_crops?.[i];if(f){assets.backgrounds[s.id][i]=await im(f);assets.images[f]=assets.backgrounds[s.id][i]}}}
for(const[id,f]of Object.entries(spec.microscopy||{}))assets.microscopy[id]=await im(f);
for(let i=1;i<=9;i++)assets.images['opening'+i]=await im('assets/opening/cut'+String(i).padStart(2,'0')+'.png');
function instrument(){
 const canvas=createCanvas(1920,1080),ctx=canvas.getContext('2d');let calls={text:[],rect:[],bezel:[],images:[]};
 const box=(x,y,w,h)=>{const m=ctx.getTransform(),p=[[x,y],[x+w,y],[x,y+h],[x+w,y+h]].map(([a,b])=>[m.a*a+m.c*b+m.e,m.b*a+m.d*b+m.f]);return {left:Math.min(...p.map(v=>v[0])),right:Math.max(...p.map(v=>v[0])),top:Math.min(...p.map(v=>v[1])),bottom:Math.max(...p.map(v=>v[1]))}};
 const ft=ctx.fillText.bind(ctx);ctx.fillText=function(s,x,y,...rest){calls.text.push({text:String(s),font:ctx.font,alpha:ctx.globalAlpha});return ft(s,x,y,...rest)};
 const rc=ctx.rect.bind(ctx);ctx.rect=function(x,y,w,h){calls.rect.push({local:[x,y,w,h],bounds:box(x,y,w,h)});return rc(x,y,w,h)};
 const rr=ctx.roundRect.bind(ctx);ctx.roundRect=function(x,y,w,h,...rest){if(x===-12&&y===-13&&w>1100&&h>560)calls.bezel.push(box(x,y,w,h));return rr(x,y,w,h,...rest)};
 const di=ctx.drawImage.bind(ctx);ctx.drawImage=function(image,...a){let d;if(a.length===4)d=a;else if(a.length===8)d=a.slice(4);if(d&&d[2]>=1800&&d[3]>=800)calls.images.push(box(...d));return di(image,...a)};
 return {canvas,ctx,reset(){calls={text:[],rect:[],bezel:[],images:[]}},get(){return calls}};
}
const now=instrument(),old=instrument(),records=[],H=1080,W=1920;
const hash=c=>createHash('sha256').update(c.data()).digest('hex');
function stripStats(data){let sum=0,sum2=0,n=0,nonblack=0;for(let y=865;y<H;y+=4)for(let x=0;x<W;x+=4){const j=(y*W+x)*4,r=data[j],g=data[j+1],b=data[j+2],l=(r+g+b)/3;sum+=l;sum2+=l*l;n++;if(Math.max(Math.abs(r-8),Math.abs(g-8),Math.abs(b-8))>3)nonblack++}return {samples:n,mean:sum/n,std:Math.sqrt(Math.max(0,sum2/n-(sum/n)**2)),nonblack_fraction:nonblack/n}}
// Native canvas exposes its affine matrix at float precision.
function sameBounds(a,b){return !!a&&['left','right','top','bottom'].every(k=>Math.abs(a[k]-b[k])<.0001)}
for(let i=0;i<timeline.entries.length;i++){
 const e=timeline.entries[i],section=spec.sections.find(s=>s.id===e.section_id),d=e.end-e.start;
 const local=Math.max(.01,d-Math.min(.06,d*.05)),t=e.start+local;
 now.reset();const state=drawFrame(now.ctx,t,timeline,spec,assets),calls=now.get(),one=hash(now.canvas),pixels=Buffer.from(now.canvas.data());
 now.reset();drawFrame(now.ctx,t,timeline,spec,assets);const deterministic=one===hash(now.canvas);
 old.reset();drawOld(old.ctx,t,timeline,spec,assets);const before=old.get(),oldHash=hash(old.canvas);
 const words=x=>x.text.filter(t=>t.alpha>.0001).map(t=>[t.text,t.font]);
 const hero=section.type!=='task',after=section.type==='task'&&e.kind!=='title'&&e.cut_index>0;
 let placement=null,bezelObserved=null;
 if(after){placement=getTaskPlacement(section,local);bezelObserved=calls.bezel.find(b=>sameBounds(b,placement.bezelBounds))||null}
 records.push({entry_index:i,section_id:e.section_id,kind:e.kind,cut_index:e.cut_index,cut_id:e.cut_id,time:t,local_seconds:local,captions:state.captions,text:calls.text,text_and_font_unchanged:JSON.stringify(words(calls))===JSON.stringify(words(before)),deterministic,pixel_sha256:one,pixels_same_as_v2:one===oldHash,
 hero,hero_full_height_clip:hero?calls.rect.some(r=>r.local.join(',')==='0,0,1920,1080'):null,bottom_strip:hero?stripStats(pixels):null,baseline_bottom_strip:hero?stripStats(old.canvas.data()):null,large_photograph_bounds:hero?calls.images:undefined,after,placement,observed_bezel_bounds:bezelObserved,all_observed_bezel_bounds:after?calls.bezel:undefined,bezel_matches_actual_draw:after?!!bezelObserved:null});
}
const placements=[];
for(const section of spec.sections.filter(s=>s.type==='task'))for(const local of [0,.5,1,2,4,10])placements.push({section_id:section.id,local_seconds:local,...getTaskPlacement(section,local)});
console.log(JSON.stringify({hero_contract:heroSceneContract,task_contract:taskSceneContract,records,placements,scope:'Actual native draw calls, pixels and shared placement contract. Final encoded frames require separate visual review.'}));
'''

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline',type=Path)
    p.add_argument('--out',type=Path,default=HERE.parent/'out/showcase-v3')
    p.add_argument('--video',type=Path)
    p.add_argument('--baseline-video',type=Path,default=HERE.parent/'out/showcase-v2/RD_Process_AI_Fast_Track_Showcase_Revision2.mp4')
    p.add_argument('--node',default='node')
    p.add_argument('--source-only',action='store_true')
    args=p.parse_args();out=args.out;out.mkdir(parents=True,exist_ok=True)
    baseline=args.baseline or (HERE.parent/'showcase-v2' if (HERE.parent/'showcase-v2/spec.json').exists() else HERE/'baseline-v2')
    video=args.video or out/'RD_Process_AI_Fast_Track_Showcase_Revision3.mp4'
    report={'status':'WAIT','scope':'Revision 3 independent layout/content/audio-preservation validation','checks':[],'limitations':[]}
    target=out/('layout-source-validation.json' if args.source_only else 'layout-validation.json')
    def save():target.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    def check(name,ok,**data):
        report['checks'].append({'check':name,'passed':bool(ok),**data})
        if not ok:print('FAIL '+name,flush=True)
    required=[HERE/'spec.json',HERE/'timeline.json',HERE/'layout-baseline-provenance.json',HERE/'narration/approved-mix.m4a',HERE/'narration/approved-mix-provenance.json',*[baseline/f for f in ANCHORS]]
    if not args.source_only:required += [video,out/'video_silent.mp4',out/'render-validation.json',out/'visual-validation.json',out/'mux-validation.json',out/'contact-sheet-manifest.json']
    missing=[str(f) for f in required if not f.exists()]
    if missing:report['missing']=missing;save();print(json.dumps({'status':'WAIT','missing':missing}));return 2
    try:
        source=read(HERE/'layout-baseline-provenance.json');files={r['file']:r for r in source['files']}
        frozen_names=['spec.json','timeline.json','stage.mjs','hero-scenes.js','task-scenes.js','render.mjs','narration/ko.json','narration/approved-mix.m4a','layout-baseline-provenance.json']
        frozen={f:sha(HERE/f) for f in frozen_names}
        oldbad=[f for f,r in files.items() if not (baseline/f).exists() or sha(baseline/f)!=r['sha256']]
        portable=not (baseline/'reference').exists()
        if portable:oldbad=[f for f in ANCHORS if not (baseline/f).exists() or sha(baseline/f)!=files[f]['sha256']]
        check('v2_original_source_snapshot_unchanged',len(files)==201 and not oldbad,files=201,mode='portable six-file baseline plus immutable input hashes' if portable else 'all original v2 files',mismatches=oldbad)
        immutable=[f for f in files if f.startswith(('reference/','assets/','fonts/','narration/'))]
        redactions=source.get('packaged_json_redactions',{});accepted_redactions=[];bad=[]
        for f in immutable:
            target_file=HERE/f
            if not target_file.exists():bad.append(f);continue
            actual=sha(target_file)
            if actual==files[f]['sha256']:continue
            if packaged_redaction_matches(f,files[f]['sha256'],actual,redactions,portable):
                accepted_redactions.append({'file':f,**redactions[f]})
            else:bad.append(f)
        check('all_v2_md_images_fonts_voice_bgm_and_narration_evidence_unchanged',not bad and sum(f.startswith('reference/') and f.endswith('.md') for f in immutable)==20,checked_files=len(immutable),mismatches=bad)
        report['historical_url_redactions']={'portable_mode':portable,'accepted':accepted_redactions,'scope':'Only the four explicitly declared historical narration JSON files may use their exact packaged hash after URL removal. Workspace mode always requires original hashes.'}
        check('spec_timeline_and_voice_configuration_byte_identical',all(sha(HERE/f)==sha(baseline/f)==files[f]['sha256'] for f in ['spec.json','timeline.json','narration/ko.json']))
        spec=read(HERE/'spec.json');tl=read(HERE/'timeline.json');oldtl=read(baseline/'timeline.json')
        check('exact_duration_frame_count_and_ninety_one_entry_order',tl==oldtl and tl['frames']==9214 and tl['fps']==30 and abs(tl['duration']-9214/30)<1e-8 and len(tl['entries'])==91 and sum(e['kind']=='cut' for e in tl['entries'])==73,duration_seconds=tl['duration'],frames=tl['frames'])
        ap=read(HERE/'narration/approved-mix-provenance.json');approved=HERE/'narration/approved-mix.m4a'
        check('approved_audio_file_and_v2_provenance',sha(approved)==ap['sha256'] and ap['source_sha256']==EXPECTED_V2_SHA)
        print('Checking actual native layouts and unchanged displayed text',flush=True)
        import os
        env={**os.environ,'LAYOUT_BASELINE':str(baseline.resolve())}
        native=json.loads(subprocess.run([args.node,'--input-type=module','-e',NATIVE_JS],cwd=HERE,env=env,check=True,capture_output=True,text=True,timeout=180).stdout)
        (out/'native-layout-validation.json').write_text(json.dumps(native,ensure_ascii=False,indent=2)+'\n')
        rows=native['records'];heroes=[r for r in rows if r['hero']];after=[r for r in rows if r['after']]
        hc=native.get('hero_contract') or {};tc=native.get('task_contract') or {}
        check('native_ninety_one_frames_deterministic',len(rows)==91 and all(r['deterministic'] for r in rows))
        check('every_displayed_word_and_font_preserved',all(r['text_and_font_unchanged'] for r in rows),changed_entries=[r['entry_index']+1 for r in rows if not r['text_and_font_unchanged']])
        check('all_narration_caption_metadata_empty',all(r['captions']==[] for r in rows) and spec['presentation_overrides']['narration_captions'] is False)
        final=next(r for r in rows if r['section_id']=='ending' and r['cut_index']==5);words=[t['text'] for t in final['text']]
        check('exact_award_teams_and_owners_retained',all(w in words for w in ['N-PMA','김지은 TL','DRAM트랙Photo','장민희 TL']))
        cubic=next(r for r in rows if r.get('cut_id')=='task14_cut1')
        check('cubic_first_title_stays_clean',any(t['text']=='분산된 업무 환경' for t in cubic['text']) and not any('(Before)' in t['text'] for t in cubic['text']))
        check('nineteen_hero_scenes_use_full_1080_clip',len(heroes)==19 and all(r['hero_full_height_clip'] for r in heroes),hero_scenes=len(heroes))
        check('all_hero_bottom_215_pixels_contain_composition',all(r['bottom_strip']['nonblack_fraction']>.01 and r['bottom_strip']['std']>.35 for r in heroes),minimum_nonblack_fraction=min(r['bottom_strip']['nonblack_fraction'] for r in heroes),minimum_std=min(r['bottom_strip']['std'] for r in heroes))
        check('hero_caption_reservation_removed_and_content_balanced',hc.get('height')==1080 and hc.get('authoredHeight')==865 and abs(hc.get('contentOffsetY',-999)-107.5)<1e-8 and hc.get('captionReservedHeight')==0,contract=hc)
        check('forty_eight_after_monitor_bounds_match_actual_native_draws',len(after)==48 and all(r['bezel_matches_actual_draw'] for r in after),after_cuts=len(after))
        places=native['placements'];settled=[v for v in places if v['local_seconds']>=2]
        check('all_twelve_monitor_profiles_center_in_available_full_height',len(places)==72 and all(abs(v['bezelBounds']['centerY']-617)<1e-7 for v in settled) and all(v['bezelBounds']['top']>=154 and v['bezelBounds']['bottom']<=1080 for v in places) and tc.get('captionArea') is None and tc.get('contentArea')==[0,154,1920,926],placement_samples=len(places))
        check('all_twelve_before_photographs_remain_pixel_identical',all(r['pixels_same_as_v2'] for r in rows if r['section_id'].startswith('task') and r['kind']=='cut' and r['cut_index']==0))
        if not args.source_only:
            print('Checking final MP4 and exact approved AAC packets',flush=True)
            meta=json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(video)]).stdout)
            vs=[s for s in meta['streams'] if s['codec_type']=='video'];aud=[s for s in meta['streams'] if s['codec_type']=='audio'];subs=[s for s in meta['streams'] if s['codec_type']=='subtitle']
            check('one_full_hd_video_one_aac_and_no_subtitle_track',len(vs)==1 and len(aud)==1 and not subs and vs[0]['width']==1920 and vs[0]['height']==1080 and vs[0]['r_frame_rate']=='30/1' and int(vs[0]['nb_frames'])==9214 and aud[0]['codec_name']=='aac' and int(aud[0]['sample_rate'])==48000 and aud[0]['channels']==2)
            check('final_duration_unchanged',abs(float(meta['format']['duration'])-tl['duration'])<1/30)
            def packets(path):
                o=json.loads(run(['ffprobe','-v','error','-select_streams','a:0','-show_packets','-show_entries','packet=pts,dts,duration,size,data_hash','-show_data_hash','sha256','-of','json',str(path)]).stdout)
                return o['packets']
            actual=packets(video);saved=packets(approved)
            check('final_aac_packet_bytes_and_timing_exactly_match_approved',actual==saved,packets=len(actual),audio_reencoded=False)
            if args.baseline_video.exists():
                check('original_v2_final_video_unchanged',sha(args.baseline_video)==EXPECTED_V2_SHA)
                original=packets(args.baseline_video)
                check('all_aac_packets_exactly_equal_original_v2',actual==original,packets=len(original))
            else:report['limitations'].append('Original v2 MP4 is absent in this portable source package. The approved AAC and its v2 SHA provenance remain available for exact packet comparison.')
            packet_hash=lambda f:run(['ffmpeg','-v','error','-i',str(f),'-map','0:v:0','-c:v','copy','-f','hash','-hash','sha256','-']).stdout.strip()
            check('new_native_video_stream_copied_exactly',packet_hash(video)==packet_hash(out/'video_silent.mp4'))
            render=read(out/'render-validation.json')
            check('native_render_hashes_match_current_inputs',render.get('status')=='PASS' and render['sha256']==sha(out/'video_silent.mp4') and all(sha(HERE/r['file'])==r['sha256'] for r in render['inputs']),render_inputs=len(render['inputs']))
            visual=read(out/'visual-validation.json')
            check('all_ninety_one_final_stills_have_no_captions_and_active_motion',len(visual['records'])==91 and all(r['caption']==[] for r in visual['records']) and len(visual['motion'])==79 and all(r['moving'] for r in visual['motion']))
            contact=read(out/'contact-sheet-manifest.json')
            current_stills={r['file']:r for r in visual['records']}
            def current_contact_image(record):
                original=Path(record['file']);path=original if original.exists() else out/'stills'/original.name
                return path.exists() and sha(path)==record['sha256'] and original.name in current_stills
            check('contact_sheets_cover_all_ninety_one_current_stills',len(contact['records'])==91 and len({Path(r['file']).name for r in contact['records']})==91 and all(current_contact_image(r) for r in contact['records']) and all(sha(HERE/f)==h for f,h in contact['source_hashes'].items()),stills=len(contact['records']),sheet_pages=len(contact['pages']))
            mux=read(out/'mux-validation.json')
            check('mux_receipt_matches_exact_final_video',mux['status']=='PASS' and mux['final_sha256']==sha(video) and mux['approved_audio_sha256']==sha(approved) and mux['audio_reencoded'] is False and mux['timeline_edited'] is False)
            run(['ffmpeg','-v','error','-i',str(video),'-f','null','-'])
            check('complete_final_video_and_audio_decode',True)
            report.update({'video':str(video),'file_sha256':sha(video),'frames':9214,'duration_seconds':float(meta['format']['duration']),'approved_aac_packet_count':len(actual)})
        check('source_inputs_unchanged_during_validation',all(sha(HERE/f)==h for f,h in frozen.items()))
        report['limitations'].append('Native geometry and pixel checks do not replace reviewing the 91-cut contact sheets and encoded final playback. Existing narration ASR variants are inherited; narration is not regenerated or reprocessed.')
        report['status']=('SOURCE_PASS' if args.source_only else 'PASS') if all(c['passed'] for c in report['checks']) else 'FAIL'
    except Exception as exc:report.update({'status':'FAIL','failure':str(type(exc).__name__)+': '+str(exc)})
    save();print(json.dumps({'status':report['status'],'report':str(target),'checks':len(report['checks']),'passed':sum(c['passed'] for c in report['checks']),'failure':report.get('failure')},ensure_ascii=False))
    return 0 if report['status'] in ['PASS','SOURCE_PASS'] else 1

if __name__=='__main__':sys.exit(main())
