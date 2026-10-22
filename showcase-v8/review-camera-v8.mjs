#!/usr/bin/env node
/**
 * Visual-preview camera QA using the estimated timeline. No speech generation,
 * audio mix, final alignment, complete video encode or playback is performed.
 * A direct visual-review receipt in the output report is retained only when
 * its source and native-frame hashes still match this run's evidence exactly.
 */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {createHash} from 'node:crypto';
import {drawCameraPhoto,getCameraState,photoCameraContract} from './photo-camera.js';
import {drawTask} from './task-scenes.js';
import {drawTaskHeader} from './stage.mjs';

const ROOT=path.dirname(fileURLToPath(import.meta.url));
const OUT=path.resolve(ROOT,'../out/showcase-v8');
const DIR=path.join(OUT,'camera-preview');
const REPORT=path.join(OUT,'camera-validation.json');
const require=createRequire(import.meta.url);let native;
try{native=require('@napi-rs/canvas')}catch{native=require('/Users/jk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@napi-rs/canvas')}
const {createCanvas,loadImage,GlobalFonts}=native;
for(const font of ['NotoSansCJKkr-Regular.otf','NotoSansCJKkr-Bold.otf'])GlobalFonts.registerFromPath(path.join(ROOT,'fonts',font),'Noto');
const hash=b=>createHash('sha256').update(b).digest('hex');
const fileHash=p=>hash(fs.readFileSync(p));
const read=f=>JSON.parse(fs.readFileSync(path.join(ROOT,f),'utf8'));
const args=process.argv.slice(2),timelineArgument=args.indexOf('--timeline');
const timelineFile=timelineArgument>=0?args[timelineArgument+1]:'timeline-preview.json';
if(!['timeline-preview.json','timeline.json'].includes(timelineFile))throw new Error('Use --timeline timeline-preview.json or --timeline timeline.json');
const spec=read('spec.json'),timeline=read(timelineFile),profiles=read('photo-camera-profiles.json');
const previewOnly=timeline.preview_only===true;
const baseline=read('revision6-baseline-provenance.json');
const sourceNames=['photo-camera.js','photo-camera-profiles.json','task-scenes.js','spec.json',timelineFile,'stage.mjs','revision6-baseline-provenance.json'];
const sourceHashes=Object.fromEntries(sourceNames.map(f=>[`showcase-v8/${f}`,fileHash(path.join(ROOT,f))]));
const previous=fs.existsSync(REPORT)?JSON.parse(fs.readFileSync(REPORT,'utf8')):null;
fs.mkdirSync(DIR,{recursive:true});
const W=1920,H=1080,HEADER=154,phases=[0,.25,.5,.75,1];
const first=timeline.entries.filter(e=>e.kind==='cut'&&e.cut_index===0&&e.section_id.startsWith('task'));
const tasks=spec.sections.filter(s=>s.type==='task'),taskIds=tasks.map(s=>s.id);
const profileIds=Object.keys(profiles.tasks||{});
const assets={photoCameraProfiles:profiles,images:{},backgrounds:{},videos:{},microscopy:{},transitionCanvas:createCanvas(W,H),spec,tasks,drawTitles:false,drawCaptions:false};
for(const s of spec.sections){
 if(s.reference_image&&!assets.images[s.reference_image])assets.images[s.reference_image]=await loadImage(path.join(ROOT,s.reference_image));
 assets.backgrounds[s.id]={};
 for(let i=0;i<s.cuts.length;i++){
  const f=s.backgrounds?.[i]||s.cuts[i].photo_crop||s.cuts[i].background||s.photo_crops?.[i];
  if(f&&fs.existsSync(path.join(ROOT,f))){assets.backgrounds[s.id][i]=await loadImage(path.join(ROOT,f));assets.images[f]=assets.backgrounds[s.id][i];}
 }
}
for(const [id,f] of Object.entries(spec.microscopy||{}))assets.microscopy[id]=await loadImage(path.join(ROOT,f));

const failures=[],records=[],isolation=[],photoHashes=[],geometry=[];
const canvas=createCanvas(W,H),ctx=canvas.getContext('2d');
const rawDraw=ctx.drawImage.bind(ctx);let capture=false,calls=[];
ctx.drawImage=(...args)=>{if(capture)calls.push(args);return rawDraw(...args)};
const clear=()=>{ctx.globalAlpha=1;ctx.fillStyle='#080808';ctx.fillRect(0,0,W,H)};
const headerHash=()=>hash(ctx.getImageData(0,0,W,HEADER).data);
const sourceGraph=new Map();
function walk(file){
 if(sourceGraph.has(file))return;
 const code=fs.readFileSync(file,'utf8');sourceGraph.set(file,code);
 const regex=/(?:import|export)\s+(?:[^'";]*?\s+from\s*)?['"]([^'"]+)['"]/g;
 for(const match of code.matchAll(regex))if(match[1].startsWith('.')){
  const child=path.resolve(path.dirname(file),match[1]);if(fs.existsSync(child))walk(child);
 }
}
walk(path.join(ROOT,'stage.mjs'));walk(path.join(ROOT,'task-scenes.js'));
const forbiddenImports=[...sourceGraph].filter(([p,code])=>/showcase-v7|photo-motion\.(?:js|mjs)|drawAnimatedPhoto/.test(p+'\n'+code)).map(([p])=>path.relative(ROOT,p));

for(const entry of first){
 const id=entry.section_id,section=tasks.find(s=>s.id===id),d=entry.end-entry.start,profile=profiles.tasks?.[id];
 if(!section||!profile){failures.push(`${id}: missing section or profile`);continue;}
 const sourceFile=section.backgrounds[0],im=assets.backgrounds[id][0],actual=fileHash(path.join(ROOT,sourceFile));
 const expected=baseline.files.find(x=>x.file===sourceFile);
 photoHashes.push({task_id:id,file:sourceFile,sha256:actual,baseline_sha256:expected?.sha256||null,byte_exact_to_accepted_revision6:actual===expected?.sha256,width:im.width,height:im.height});
 const threshold=Math.max(photoCameraContract.minimumTwoViewSeconds,profile.two_view_min_seconds??6.2);
 const expectedViews=d>photoCameraContract.oneViewThroughSeconds&&d>=threshold&&profile.views?.length>=2?2:1;
 const firstState=getCameraState(id,0,d,assets),sampleRecords=[];
 const contact=createCanvas(W,252),cc=contact.getContext('2d');cc.fillStyle='#080808';cc.fillRect(0,0,W,252);
 for(let j=0;j<phases.length;j++){
  const u=phases[j],t=u===1?Math.max(0,d-1/30):d*u;
  const state=getCameraState(id,t,d,assets);
  if(state.viewCount!==expectedViews)failures.push(`${id}: wrong duration-dependent view count`);
  if(JSON.stringify(state)!==JSON.stringify(getCameraState(id,t,d,assets)))failures.push(`${id}: nondeterministic camera state`);
  clear();ctx.fillStyle='#35506A';ctx.fillRect(0,0,W,HEADER);ctx.fillStyle='#D4AF7C';ctx.fillRect(257,17,357,51);
  const beforeHeader=headerHash();capture=true;calls=[];
  const success=drawCameraPhoto(ctx,im,id,t,d,assets);capture=false;
  const unchangedHeader=beforeHeader===headerHash();
  if(!success||!unchangedHeader)failures.push(`${id}: draw failed or header overwritten`);
  const cropCalls=calls.map(a=>{
   const [image,sx,sy,sw,sh,dx,dy,dw,dh]=a;
   const safe=a.length===9&&sx>=-1e-7&&sy>=-1e-7&&sx+sw<=image.width+1e-7&&sy+sh<=image.height+1e-7;
   const rigid=a.length===9&&Math.abs(sw/sh-dw/dh)<1e-10;
   if(!safe||!rigid)failures.push(`${id}: unsafe/nonuniform source rectangle`);
   return{source:[sx,sy,sw,sh],target:[dx,dy,dw,dh],source_bounds_safe:safe,uniform_scale:rigid};
  });
  geometry.push({task_id:id,u,local_time:t,header_unchanged:unchangedHeader,calls:cropCalls});
  clear();drawTask(ctx,section,section.cuts[0],t,d,{...assets,photoCamera:true});const header=drawTaskHeader(ctx,section,section.cuts[0],'cut');
  const rgba=hash(canvas.data()),headerPixels=headerHash();const file=`${id}_${u.toFixed(2)}.png`;
  fs.writeFileSync(path.join(DIR,file),canvas.encodeSync('png'));
  clear();drawTask(ctx,section,section.cuts[0],t,d,{...assets,photoCamera:true});drawTaskHeader(ctx,section,section.cuts[0],'cut');
  const deterministic=rgba===hash(canvas.data());if(!deterministic)failures.push(`${id}: nondeterministic native frame`);
  const frame={u,local_time:t,view_count:state.viewCount,blend:state.blend,layers:state.layers,source_bounds_safe:cropCalls.every(x=>x.source_bounds_safe),uniform_scale:cropCalls.every(x=>x.uniform_scale),module_header_unchanged:unchangedHeader,rgba_sha256:rgba,png_sha256:fileHash(path.join(DIR,file)),file:`camera-preview/${file}`,header_rgba_sha256:headerPixels,header_layout:header,deterministic};
  sampleRecords.push(frame);cc.drawImage(canvas,j*384,32,384,216);cc.fillStyle='#F2EEE7';cc.font='16px sans-serif';cc.fillText(`${id}  ${d.toFixed(3)}s  u=${u.toFixed(2)}`,j*384+10,22);
 }
 if(new Set(sampleRecords.map(x=>x.header_rgba_sha256)).size!==1)failures.push(`${id}: persistent header changed across camera phases`);
 if(sampleRecords[0].rgba_sha256===sampleRecords.at(-1).rgba_sha256)failures.push(`${id}: no visible native camera framing change`);
 const contactFile=`${id}-camera-sequence.jpg`;fs.writeFileSync(path.join(DIR,contactFile),contact.encodeSync('jpeg',92));
 for(let index=1;index<section.cuts.length;index++){
  const event=timeline.entries.find(e=>e.kind==='cut'&&e.section_id===id&&e.cut_index===index),dur=event?event.end-event.start:5,t=dur*.43;
  clear();drawTask(ctx,section,section.cuts[index],t,dur,{...assets,photoCamera:true});const enabled=hash(canvas.data());
  clear();drawTask(ctx,section,section.cuts[index],t,dur,{...assets,photoCamera:false});const disabled=hash(canvas.data());
  const identical=enabled===disabled;if(!identical)failures.push(`${id}: camera affected later body cut ${index+1}`);
  isolation.push({task_id:id,cut_index:index,local_time:t,duration:dur,camera_enabled_rgba_sha256:enabled,camera_disabled_rgba_sha256:disabled,byte_identical:identical});
 }
 clear();drawTask(ctx,section,section.cuts[0],d*.43,d,{...assets,photoCamera:true,legacyTaskComposition:true});const legacyOn=hash(canvas.data());
 clear();drawTask(ctx,section,section.cuts[0],d*.43,d,{...assets,photoCamera:false,legacyTaskComposition:true});const legacyOff=hash(canvas.data());
 if(legacyOn!==legacyOff)failures.push(`${id}: camera affected legacy helper default`);
 const bounds=[];for(const duration of [2,3.5,4.2,d,10])for(let i=0;i<=100;i++){
  const state=getCameraState(id,duration*i/100,duration,assets);
  if(duration<=3.5&&state.viewCount!==1)failures.push(`${id}: multiple views in a short cut`);
  for(const layer of state.layers)bounds.push(layer.zoom>=1&&layer.zoom<=1.12&&layer.fx>=0&&layer.fx<=1&&layer.fy>=0&&layer.fy<=1);
 }
 if(!bounds.every(Boolean))failures.push(`${id}: camera zoom/focal bounds`);
 records.push({task_id:id,preview_duration:d,expected_view_count:expectedViews,actual_view_count:firstState.viewCount,two_view_min_seconds:threshold,action_ko:profile.purpose_ko,short_cut_single_view:true,zoom_and_focal_bounds_pass:bounds.every(Boolean),legacy_unchanged:legacyOn===legacyOff,contact_file:`camera-preview/${contactFile}`,frames:sampleRecords});
}

const moduleCode=fs.readFileSync(path.join(ROOT,'photo-camera.js'),'utf8'),taskCode=fs.readFileSync(path.join(ROOT,'task-scenes.js'),'utf8');
const checks={
 selected_timeline_is_explicit_and_valid:Array.isArray(timeline.entries)&&timeline.entries.length>0&&(timelineFile!=='timeline-preview.json'||previewOnly),
 exactly_twelve_task_first_photos:first.length===12&&new Set(first.map(e=>e.section_id)).size===12,
 exactly_twelve_profiles_for_twelve_tasks:profileIds.length===12&&taskIds.length===12&&profileIds.every(id=>taskIds.includes(id))&&first.every(e=>profileIds.includes(e.section_id)),
 all_original_photo_bytes_match_accepted_revision6:photoHashes.length===12&&photoHashes.every(x=>x.byte_exact_to_accepted_revision6),
 source_crop_safe_and_uniform_rigid_scale:geometry.every(r=>r.calls.length>0&&r.calls.every(x=>x.source_bounds_safe&&x.uniform_scale)),
 pure_module_keeps_header_pixels_unchanged:geometry.every(r=>r.header_unchanged),
 same_native_camera_time_renders_exact_pixels:records.every(r=>r.frames.every(f=>f.deterministic)),
 header_pixels_fixed_across_all_five_phases:records.every(r=>new Set(r.frames.map(f=>f.header_rgba_sha256)).size===1),
 duration_based_view_counts_match_profiles:records.every(r=>r.actual_view_count===r.expected_view_count),
 short_cuts_single_view_and_zoom_at_most_1_12:records.every(r=>r.short_cut_single_view&&r.zoom_and_focal_bounds_pass),
 all_twelve_camera_framings_actually_change:records.every(r=>r.frames[0].rgba_sha256!==r.frames.at(-1).rgba_sha256),
 all_forty_eight_later_body_cuts_camera_toggle_identical:isolation.length===48&&isolation.every(r=>r.byte_identical),
 legacy_helper_default_unchanged:records.every(r=>r.legacy_unchanged),
 first_photo_only_callsite_guards:taskCode.includes('enableCamera&&i===0&&drawCameraPhoto(')&&taskCode.includes('d,photoAssets,index===0)'),
 no_revision7_person_warp_in_active_dependency_graph:forbiddenImports.length===0,
 camera_module_no_mesh_or_nonrigid_transform:photoCameraContract.humanWarp===false&&photoCameraContract.meshWarp===false&&!/ctx\.(?:transform|setTransform|scale|rotate)\(/.test(moduleCode),
 frozen_camera_sources_unchanged_during_run:Object.entries(sourceHashes).every(([p,h])=>fileHash(path.resolve(ROOT,'..',p))===h)
};
for(const [name,pass] of Object.entries(checks))if(!pass)failures.push(name);
const frameHashes=Object.fromEntries(records.flatMap(r=>r.frames.map(f=>[f.file,f.png_sha256])));
const receipt=previous?.direct_visual_review;
const receiptMatches=receipt?.status==='PASS'&&JSON.stringify(receipt.source_hashes)===JSON.stringify(sourceHashes)&&JSON.stringify(receipt.native_png_hashes)===JSON.stringify(frameHashes);
const automaticPass=failures.length===0;
const report={
 status:automaticPass?(receiptMatches?'PASS':'REVIEW_REQUIRED'):'FAIL',automated_status:automaticPass?'PASS':'FAIL',revision:8,
 scope:'Visual camera preview using '+timelineFile+'. Original photographs are rigidly cropped/scaled; no person warp, generated motion, extra marks, new speech, audio alignment or completed movie is validated here.',
 timeline_file:timelineFile,timing_status:previewOnly?'ESTIMATED_VISUAL_PREVIEW_ONLY':'CAMERA_ONLY_ON_SELECTED_TIMELINE_NO_AUDIO_VERIFICATION',preview_only:previewOnly,final_audio_verified:false,final_timing_verified:false,full_video_reencoded:false,playback_review_performed:false,
 generated_at_utc:new Date().toISOString(),source_hashes:sourceHashes,
 contract:photoCameraContract,checks,checks_passed:Object.values(checks).filter(Boolean).length,checks_total:Object.keys(checks).length,failures,
 task_count:records.length,native_sample_count:records.reduce((n,r)=>n+r.frames.length,0),sample_phases:phases,
 source_photo_baseline:'revision6-baseline-provenance.json (local immutable SHA records; adjacent revision6 folder is not required)',source_photos:photoHashes,
 active_dependency_files:[...sourceGraph.keys()].map(p=>path.relative(ROOT,p)),forbidden_imports:forbiddenImports,
 framing_records:records,rigid_source_rectangle_tests:geometry,later_cut_isolation:isolation,
 direct_visual_review:receiptMatches?receipt:{status:'PENDING',performed:false,required:'Inspect all 12 native camera sequences and full start/mid/end samples, then record a source/pixel-bound receipt in this report.'},
 reproducibility_note:'Automated geometry/isolation checks rerun independently. A stored direct visual review is retained only while every source hash and all 60 native PNG hashes match exactly. Timing is estimated and remains outside final-audio approval.'
};
fs.writeFileSync(REPORT,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({status:report.status,automated_status:report.automated_status,checks:`${report.checks_passed}/${report.checks_total}`,tasks:records.length,native_samples:report.native_sample_count,two_view_tasks:records.filter(r=>r.actual_view_count===2).map(r=>r.task_id),failures,report:REPORT}));
if(!automaticPass)process.exitCode=1;
