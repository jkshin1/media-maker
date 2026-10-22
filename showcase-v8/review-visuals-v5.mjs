#!/usr/bin/env node
/** Review locked content, text bounds and task-specific motion before encoding. */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {createHash} from 'node:crypto';
import {drawFrame,measureTaskHeader} from './stage.mjs';
import {drawFrame as drawBaselineFrame} from './baseline-v4/stage.mjs';
import {drawTask,taskDiversityContract} from './task-scenes.js';
const root=path.dirname(fileURLToPath(import.meta.url)),out=path.resolve(root,'../out/showcase-v5');
const require=createRequire(import.meta.url);let native;
try{native=require('@napi-rs/canvas')}catch{native=require('/Users/jk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@napi-rs/canvas')}
const {createCanvas,loadImage,GlobalFonts}=native;
for(const [file,name] of [['NotoSansCJKkr-Regular.otf','Noto'],['NotoSansCJKkr-Bold.otf','Noto']])GlobalFonts.registerFromPath(path.join(root,'fonts',file),name);
const read=f=>JSON.parse(fs.readFileSync(f)),digest=b=>createHash('sha256').update(b).digest('hex');
const spec=read(path.join(root,'spec.json')),tl=read(path.join(root,'timeline.json'));
const assets={images:{},backgrounds:{},videos:{},microscopy:{},transitionCanvas:createCanvas(1920,1080),spec,tasks:spec.sections.filter(s=>s.type==='task'),drawTitles:false,drawCaptions:false};
for(const f of new Set(spec.sections.map(s=>s.reference_image).filter(Boolean)))assets.images[f]=await loadImage(path.join(root,f));
for(const s of spec.sections){assets.backgrounds[s.id]={};for(let i=0;i<s.cuts.length;i++){const f=s.backgrounds?.[i]||s.cuts[i].photo_crop||s.cuts[i].background||s.photo_crops?.[i];if(f&&fs.existsSync(path.join(root,f))){assets.backgrounds[s.id][i]=await loadImage(path.join(root,f));assets.images[f]=assets.backgrounds[s.id][i]}}}
for(const [id,f] of Object.entries(spec.microscopy||{}))assets.microscopy[id]=await loadImage(path.join(root,f));
for(let i=1;i<=9;i++)assets.images[`opening${i}`]=await loadImage(path.join(root,`assets/opening/cut${String(i).padStart(2,'0')}.png`));
fs.mkdirSync(out,{recursive:true});fs.mkdirSync(path.join(out,'motion-review'),{recursive:true});
const canvas=createCanvas(1920,1080),ctx=canvas.getContext('2d'),baselineCanvas=createCanvas(1920,1080),baselineCtx=baselineCanvas.getContext('2d');
const lockFiles=['spec.json','timeline.json','hero-scenes.js','stage.mjs','narration/ko.json','narration/take.wav','narration/processed-continuous-v4.wav','narration/revision-manifest-v4.json'];
const oldInventory=read(path.join(root,'revision4-baseline-provenance.json')).files;
const baselineHashes=new Map(oldInventory.map(r=>[r.file,r.sha256]));
const locked=lockFiles.map(file=>({file,unchanged:digest(fs.readFileSync(path.join(root,file)))===baselineHashes.get(file)}));
const previousSource=oldInventory.map(r=>({file:r.file,unchanged:fs.existsSync(path.resolve(root,'../showcase-v4',r.file))?digest(fs.readFileSync(path.resolve(root,'../showcase-v4',r.file)))===r.sha256:null}));
let recording=false;const textRecords=[];const fillText=ctx.fillText.bind(ctx);
ctx.fillText=(value,x,y,...args)=>{
 if(recording){const s=String(value),m=ctx.measureText(s),tr=ctx.getTransform(),xx=Number(x),yy=Number(y);let l=xx,r=xx+m.width;
  if(ctx.textAlign==='right'||ctx.textAlign==='end'){l=xx-m.width;r=xx}else if(ctx.textAlign==='center'){l=xx-m.width/2;r=xx+m.width/2}
  let top=yy-(m.actualBoundingBoxAscent||0),bottom=yy+(m.actualBoundingBoxDescent||0);
  const corners=[[l,top],[r,top],[r,bottom],[l,bottom]].map(([a,b])=>({x:tr.a*a+tr.c*b+tr.e,y:tr.b*a+tr.d*b+tr.f}));
  textRecords.push({text:s,font:ctx.font,alpha:ctx.globalAlpha,bounds:{left:Math.min(...corners.map(p=>p.x)),right:Math.max(...corners.map(p=>p.x)),top:Math.min(...corners.map(p=>p.y)),bottom:Math.max(...corners.map(p=>p.y))}});
 }return fillText(value,x,y,...args);
};
const taskRows=[];const headers=[];
for(const e of tl.entries){const section=spec.sections.find(s=>s.id===e.section_id);if(section.type!=='task')continue;
 const cut=section.cuts[e.cut_index??0];headers.push(measureTaskHeader(ctx,section,cut,e.kind));if(e.kind==='title')continue;
 const d=e.end-e.start,t=d*.62;recording=true;const a=textRecords.length;drawTask(ctx,section,cut,t,d,assets);recording=false;
 const records=textRecords.slice(a).filter(r=>r.alpha>.15&&r.text.trim());
 const outside=records.filter(r=>r.bounds.left<50||r.bounds.right>1870||r.bounds.top<166||r.bounds.bottom>1040);
 const frames=[];for(const phase of [.18,.5,.84]){drawTask(ctx,section,cut,d*phase,d,{...assets,freezeTaskBackground:true});const file=`${section.id}_cut${e.cut_index+1}_${Math.round(phase*100)}.jpg`;fs.writeFileSync(path.join(out,'motion-review',file),canvas.encodeSync('jpeg',85));frames.push({phase,file,sha256:digest(canvas.data())});}
 taskRows.push({section:section.id,cut_index:e.cut_index,cut_title:cut.title,records,outside_safe_body:outside,motion_frames:frames,fixed_background_frames_differ:new Set(frames.map(r=>r.sha256)).size===3});
}
const heroRows=[];
for(const e of tl.entries){const section=spec.sections.find(s=>s.id===e.section_id);if(section.type==='task')continue;
 for(const phase of [.25,.62,.9]){const t=e.start+Math.max(.47,(e.end-e.start)*phase);if(t>=e.end)continue;
  drawFrame(ctx,t,tl,spec,assets);drawBaselineFrame(baselineCtx,t,tl,spec,{...assets,transitionCanvas:createCanvas(1920,1080)});
  heroRows.push({section:e.section_id,cut_index:e.cut_index,time:t,exact_pixels_unchanged:digest(canvas.data())===digest(baselineCanvas.data())});
 }
}
const report={status:'READY_FOR_VISUAL_REVIEW',scope:'Source locks, measured body text and fixed-background triptychs. A frame difference alone is not creative or functional acceptance.',locks:locked,previous_source_unchanged:previousSource.every(r=>r.unchanged===null)?null:previousSource.every(r=>r.unchanged),previous_source_files:previousSource.length,headers:headers.length,task_body_cuts:taskRows.length,plans:taskDiversityContract.plans,hero_samples:heroRows,task_reviews:taskRows,text_bounds_flags:taskRows.flatMap(r=>r.outside_safe_body.map(f=>({section:r.section,cut_index:r.cut_index,...f}))),motion_frame_difference_pass:taskRows.filter(r=>r.fixed_background_frames_differ).length};
fs.writeFileSync(path.join(out,'source-visual-review.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({status:report.status,locked:locked.every(r=>r.unchanged),previous_source_unchanged:report.previous_source_unchanged,hero_samples:heroRows.length,heroes_unchanged:heroRows.every(r=>r.exact_pixels_unchanged),headers:headers.length,task_body_cuts:taskRows.length,text_flags:report.text_bounds_flags.length,moving_frames:report.motion_frame_difference_pass}));
if(locked.some(r=>!r.unchanged)||report.previous_source_unchanged===false||heroRows.some(r=>!r.exact_pixels_unchanged))process.exitCode=1;
