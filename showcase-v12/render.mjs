#!/usr/bin/env node
import {createRequire} from 'node:module';
import fs from 'node:fs';import path from 'node:path';import {fileURLToPath} from 'node:url';
import {spawn,spawnSync} from 'node:child_process';import {once} from 'node:events';import {createHash} from 'node:crypto';
import {drawFrame,W,H,taskIntroductionContract} from './stage.mjs';
const ROOT=path.dirname(fileURLToPath(import.meta.url)),OUT=path.resolve(ROOT,'../out/showcase-v12');
const require=createRequire(import.meta.url);let native;
try{native=require('@napi-rs/canvas')}catch{native=require('/Users/jk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@napi-rs/canvas')}
const {createCanvas,loadImage,GlobalFonts}=native;
GlobalFonts.registerFromPath(path.join(ROOT,'fonts/NotoSansCJKkr-Regular.otf'),'Noto');GlobalFonts.registerFromPath(path.join(ROOT,'fonts/NotoSansCJKkr-Bold.otf'),'Noto');
const timelineFile=process.env.TIMELINE_FILE||'timeline.json';
const spec=JSON.parse(fs.readFileSync(path.join(ROOT,'spec.json'))),timeline=JSON.parse(fs.readFileSync(path.join(ROOT,timelineFile)));
const authorizationFile='authorization.json';
const authorizationBytes=fs.readFileSync(path.join(ROOT,authorizationFile)),authorization=JSON.parse(authorizationBytes);
const authorizationProvenance={authorization_file:authorizationFile,authorization_sha256:createHash('sha256').update(authorizationBytes).digest('hex'),requested_speech_tempo:authorization.speech_tempo,pitch_cents:authorization.pitch_cents,selected_tone_preview:authorization.selected_tone_preview||null};
if(authorization.revision!==12||authorization.authorization_source!=='direct_user_reply_in_current_chat'||authorization.speech_tempo!==1.15||authorization.pitch_cents!==0||authorization.max_video_seconds!==330)throw new Error('Revision12 requires the direct-user 1.15 speech-tempo, zero-pitch and330-second authorization.');
if(timelineFile==='timeline.json'){
 if(timeline.revision!==12||timeline.preview_only!==false)throw new Error('The default timeline must be the actual Revision12 timeline, explicitly preview_only:false.');
}else if(timeline.revision!==12||timeline.preview_only!==true||!timelineFile.includes('preview'))throw new Error('Alternate timelines require an explicitly named and flagged Revision12 preview.');
const taskIds=spec.sections.filter(s=>s.type==='task').map(s=>s.id),titles=timeline.entries.filter(e=>e.kind==='title'),spoken=timeline.entries.filter(e=>e.kind==='cut'),silent=timeline.entries.filter(e=>e.kind==='silent');
if(timeline.fps!==30||!Number.isInteger(timeline.frames)||timeline.frames<=0||timeline.frames>9900||!Number.isFinite(timeline.duration)||timeline.duration<=0||timeline.duration>330||Math.abs(timeline.frames/30-timeline.duration)>1e-7||timeline.entries.length!==81||spoken.length!==68||titles.length!==12||silent.length!==1)throw new Error('Revision12 requires30fps,81entries(68spoken+12titles+1silent), and at most330seconds.');
let cursor=0;
for(const entry of timeline.entries){
 const section=spec.sections.find(s=>s.id===entry.section_id);
 if(!section||!Number.isFinite(entry.start)||!Number.isFinite(entry.end)||!Number.isInteger(entry.start_frame)||!Number.isInteger(entry.end_frame)||entry.start_frame!==cursor||entry.end_frame<=cursor||Math.abs(entry.start-entry.start_frame/30)>1e-7||Math.abs(entry.end-entry.end_frame/30)>1e-7)throw new Error('Timeline frames/times are not a contiguous valid scene clock: '+entry.section_id);
 if(!['cut','title','silent'].includes(entry.kind))throw new Error('Unsupported timeline kind: '+entry.kind);
 if(entry.kind==='title'){
  if(section.type!=='task'||entry.cut_index!=null||entry.end_frame-entry.start_frame!==60)throw new Error('Every standalone task title must be60frames with no body index.');
  const next=timeline.entries[timeline.entries.indexOf(entry)+1];
  if(!next||next.section_id!==entry.section_id||next.kind!=='cut'||next.cut_index!==0)throw new Error('A standalone task title must immediately precede its voiced first photograph.');
 }else if(!Number.isInteger(entry.cut_index)||!section.cuts[entry.cut_index])throw new Error('Invalid physical body-cut index: '+entry.section_id);
 cursor=entry.end_frame;
}
if(cursor!==timeline.frames||taskIds.length!==12||JSON.stringify(titles.map(e=>e.section_id))!==JSON.stringify(taskIds))throw new Error('Restored task titles must follow the unchanged12-task order.');
if(spoken.some(e=>typeof e.cut_id!=='string'||!e.cut_id)||new Set(spoken.map(e=>e.cut_id)).size!==68)throw new Error('All68 spoken cut IDs must be present and unique.');
const firstPhotos=spoken.filter(e=>taskIds.includes(e.section_id)&&e.cut_index===0);
if(firstPhotos.length!==12||new Set(firstPhotos.map(e=>e.section_id)).size!==12)throw new Error('Revision12 requires exactly one voiced first photograph per task.');
const last=timeline.entries.at(-1);
if(last.kind!=='silent'||last.section_id!=='ending'||last.cut_id!=='ending_cut6'||last.cut_index!==5||last.end_frame-last.start_frame!==120||last.end_frame!==timeline.frames)throw new Error('Revision12 must retain the four-second final silent card.');
if(taskIntroductionContract.revision!==12||taskIntroductionContract.firstPhotoOverlayEnabled!==false||taskIntroductionContract.maxSeconds!==0||taskIntroductionContract.standaloneTitleSeconds!==2||taskIntroductionContract.humanWarp!==false||spec.presentation_overrides?.narration_captions!==false)throw new Error('Standalone-title restoration must disable duplicate first-photo titles, narration captions and human warp.');
const titleRestoration={title_entries:12,frames_per_title:60,seconds_per_title:2,total_title_seconds:24,style_source_revision:8,first_photo_overlay_enabled:false,persistent_task_header:true,human_warp_enabled:false};
fs.mkdirSync(OUT,{recursive:true});
const args=process.argv.slice(2),stills=args.includes('--stills'),fps=30,frames=Math.round(timeline.duration*fps);
const photoCameraProfiles=JSON.parse(fs.readFileSync(path.join(ROOT,'photo-camera-profiles.json'),'utf8')).tasks;
const assets={photoCameraProfiles,images:{},backgrounds:{},videos:{},microscopy:{},transitionCanvas:createCanvas(W,H),spec,tasks:spec.sections.filter(s=>s.type==='task'),drawTitles:false,drawCaptions:false};
const unique=[...new Set(spec.sections.map(s=>s.reference_image).filter(Boolean))],loadedAssetFiles=new Set(unique);
for(const file of unique)assets.images[file]=await loadImage(path.join(ROOT,file));
for(const s of spec.sections){assets.backgrounds[s.id]={};for(let i=0;i<s.cuts.length;i++){const f=s.backgrounds?.[i]||s.cuts[i].photo_crop||s.cuts[i].background||s.photo_crops?.[i];if(f&&fs.existsSync(path.join(ROOT,f))){loadedAssetFiles.add(f);assets.backgrounds[s.id][i]=await loadImage(path.join(ROOT,f));assets.images[f]=assets.backgrounds[s.id][i]}}}
for(const [id,f] of Object.entries(spec.microscopy||{}))if(fs.existsSync(path.join(ROOT,f))){loadedAssetFiles.add(f);assets.microscopy[id]=await loadImage(path.join(ROOT,f));}
// Existing clean opening plates are copied into this package by prepare-assets.py.
for(let i=1;i<=9;i++){const f=`assets/opening/cut${String(i).padStart(2,'0')}.png`;if(fs.existsSync(path.join(ROOT,f))){loadedAssetFiles.add(f);assets.images[`opening${i}`]=await loadImage(path.join(ROOT,f));}}
const inputNames=['render.mjs','photo-camera.js','photo-camera-profiles.json','spec.json',timelineFile,authorizationFile,'stage.mjs','task-scenes.js','task-visuals-early.js','task-visuals-late.js','hero-scenes.js',...loadedAssetFiles,...spec.sections.flatMap(s=>s.backgrounds||[]),...Object.values(spec.microscopy||{}),...Array.from({length:9},(_,i)=>`assets/opening/cut${String(i+1).padStart(2,'0')}.png`),'fonts/NotoSansCJKkr-Regular.otf','fonts/NotoSansCJKkr-Bold.otf'].filter(Boolean);
const inputs=[...new Set(inputNames)].filter(f=>fs.existsSync(path.join(ROOT,f))).map(file=>({file,sha256:createHash('sha256').update(fs.readFileSync(path.join(ROOT,file))).digest('hex')}));
const canvas=createCanvas(W,H),ctx=canvas.getContext('2d');
function hash(buf){return createHash('sha256').update(buf).digest('hex')}
function assertNoDuplicateFirstPhotoTitle(state,entry){
 if(entry.kind==='cut'&&taskIds.includes(entry.section_id)&&entry.cut_index===0&&state.task_introduction?.visible)throw new Error('A large title was redrawn on the voiced first photograph: '+entry.section_id);
}
if(stills){
 const dir=path.join(OUT,timeline.preview_only?'stills-preview':'stills');fs.mkdirSync(dir,{recursive:true});const records=[];
 for(let i=0;i<timeline.entries.length;i++){
  const e=timeline.entries[i],t=e.start+Math.min((e.end-e.start)*.62,(e.end-e.start)-.06);const state=drawFrame(ctx,t,timeline,spec,assets);assertNoDuplicateFirstPhotoTitle(state,e);const f=`${String(i+1).padStart(3,'0')}_${e.section_id}_${e.kind}_${(e.cut_index??0)+1}.png`;
  fs.writeFileSync(path.join(dir,f),canvas.encodeSync('png'));records.push({file:f,time:t,section:e.section_id,kind:e.kind,cut_index:e.cut_index,caption:state.captions,task_introduction:state.task_introduction,task_header:state.task_header});
 }
 const introductionProbes=[];
 for(const entry of firstPhotos){
  const duration=entry.end-entry.start;
  for(const offset of [.5,1,1.5]){const time=entry.start+Math.min(offset,duration-.01),state=drawFrame(ctx,time,timeline,spec,assets);assertNoDuplicateFirstPhotoTitle(state,entry);introductionProbes.push({section:entry.section_id,time,first_photo_overlay_visible:state.task_introduction?.visible===true});}
 }
 const motion=[];for(const e of timeline.entries.filter(x=>x.kind!=='title')){const d=e.end-e.start;drawFrame(ctx,e.start+d*.27,timeline,spec,assets);const a=hash(canvas.data());drawFrame(ctx,e.start+d*.77,timeline,spec,assets);const b=hash(canvas.data());motion.push({section:e.section_id,cut_index:e.cut_index,moving:a!==b});}
 fs.writeFileSync(path.join(OUT,timeline.preview_only?'visual-preview-validation.json':'visual-validation.json'),JSON.stringify({revision:12,status:motion.every(x=>x.moving)?'PASS':'REVIEW',timeline_file:timelineFile,preview_only:timeline.preview_only===true,visual_source_revision:10,authorization_provenance:authorizationProvenance,title_restoration:titleRestoration,audio_verified:false,inputs,records,motion,introduction_probes:introductionProbes,notes:['Frame differences verify visible changes; they do not prove photorealistic human movement.']},null,2)+'\n');console.log(JSON.stringify({stills:records.length,motion_pass:motion.filter(x=>x.moving).length,motion_total:motion.length}));
}else{
 const videoName=process.env.RENDER_FILE||(timeline.preview_only?'visual_preview_silent.mp4':'video_silent.mp4'),reportName=process.env.RENDER_REPORT||(timeline.preview_only?'visual-preview-render-validation.json':'render-validation.json');
 if(timeline.preview_only&&(videoName==='video_silent.mp4'||reportName==='render-validation.json'))throw new Error('Preview render cannot overwrite final-timeline media or receipt names.');
 const file=path.join(OUT,videoName.replace(/\.mp4$/,'.partial.mp4'));const enc=spawn('ffmpeg',['-y','-v','error','-f','rawvideo','-pixel_format','rgba','-video_size',`${W}x${H}`,'-framerate',String(fps),'-i','-','-an','-vf','format=yuv420p','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-movflags','+faststart',file],{stdio:['pipe','inherit','inherit']});
 let failure;const done=new Promise((ok,no)=>{enc.once('error',no);enc.once('close',c=>c===0?ok():no(new Error('ffmpeg exit '+c)))});done.catch(e=>failure=e);enc.stdin.on('error',e=>failure=e);
 const started=Date.now();for(let frame=0;frame<frames;frame++){if(failure)throw failure;const state=drawFrame(ctx,frame/fps,timeline,spec,assets);assertNoDuplicateFirstPhotoTitle(state,state.entry);if(!enc.stdin.write(canvas.data()))await Promise.race([once(enc.stdin,'drain'),done.then(()=>{throw new Error('encoder ended')})]);if(frame%300===0)console.log(`Frame ${frame}/${frames}; elapsed ${((Date.now()-started)/1000).toFixed(1)}s`)}
 enc.stdin.end();await done;const probe=spawnSync('ffprobe',['-v','error','-show_streams','-show_format','-of','json',file],{encoding:'utf8'});if(probe.status)throw new Error(probe.stderr);const meta=JSON.parse(probe.stdout),v=meta.streams.find(s=>s.codec_type==='video');if(v.width!==W||v.height!==H||Number(v.nb_frames)!==frames||v.r_frame_rate!=='30/1')throw new Error('Video metadata mismatch');
 for(const item of inputs)if(hash(fs.readFileSync(path.join(ROOT,item.file)))!==item.sha256)throw new Error('Input changed during rendering: '+item.file);
 const target=path.join(OUT,videoName);fs.renameSync(file,target);fs.writeFileSync(path.join(OUT,reportName),JSON.stringify({revision:12,status:'PASS',timeline_file:timelineFile,preview_only:timeline.preview_only===true,visual_source_revision:10,authorization_provenance:authorizationProvenance,title_restoration:titleRestoration,audio_verified:false,duration:timeline.duration,frames,width:W,height:H,fps,elapsed_seconds:(Date.now()-started)/1000,sha256:hash(fs.readFileSync(target)),inputs},null,2)+'\n');console.log('Rendered '+target);
}
