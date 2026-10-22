#!/usr/bin/env node
import {createRequire} from 'node:module';
import fs from 'node:fs';import path from 'node:path';import {fileURLToPath} from 'node:url';
import {spawn,spawnSync} from 'node:child_process';import {once} from 'node:events';import {createHash} from 'node:crypto';
import {drawFrame,W,H} from './stage.mjs';
const ROOT=path.dirname(fileURLToPath(import.meta.url)),OUT=path.resolve(ROOT,'../out/showcase-v3');
const require=createRequire(import.meta.url);let native;
try{native=require('@napi-rs/canvas')}catch{native=require('/Users/jk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@napi-rs/canvas')}
const {createCanvas,loadImage,GlobalFonts}=native;
GlobalFonts.registerFromPath(path.join(ROOT,'fonts/NotoSansCJKkr-Regular.otf'),'Noto');GlobalFonts.registerFromPath(path.join(ROOT,'fonts/NotoSansCJKkr-Bold.otf'),'Noto');
const spec=JSON.parse(fs.readFileSync(path.join(ROOT,'spec.json'))),timeline=JSON.parse(fs.readFileSync(path.join(ROOT,process.env.TIMELINE_FILE||'timeline.json')));
if(timeline.duration>300&&!timeline.allow_over_five_minutes)throw new Error('Five-minute limit exceeded without user override');
fs.mkdirSync(OUT,{recursive:true});
const args=process.argv.slice(2),stills=args.includes('--stills'),fps=30,frames=Math.round(timeline.duration*fps);
const assets={images:{},backgrounds:{},videos:{},microscopy:{},transitionCanvas:createCanvas(W,H),spec,tasks:spec.sections.filter(s=>s.type==='task'),drawTitles:false,drawCaptions:false};
const unique=[...new Set(spec.sections.map(s=>s.reference_image).filter(Boolean))];
for(const file of unique)assets.images[file]=await loadImage(path.join(ROOT,file));
for(const s of spec.sections){assets.backgrounds[s.id]={};for(let i=0;i<s.cuts.length;i++){const f=s.backgrounds?.[i]||s.cuts[i].photo_crop||s.cuts[i].background||s.photo_crops?.[i];if(f&&fs.existsSync(path.join(ROOT,f))){assets.backgrounds[s.id][i]=await loadImage(path.join(ROOT,f));assets.images[f]=assets.backgrounds[s.id][i]}}}
for(const [id,f] of Object.entries(spec.microscopy||{}))if(fs.existsSync(path.join(ROOT,f)))assets.microscopy[id]=await loadImage(path.join(ROOT,f));
// Existing clean opening plates are copied into this package by prepare-assets.py.
for(let i=1;i<=9;i++){const f=`assets/opening/cut${String(i).padStart(2,'0')}.png`;if(fs.existsSync(path.join(ROOT,f)))assets.images[`opening${i}`]=await loadImage(path.join(ROOT,f));}
const inputNames=['spec.json','timeline.json','stage.mjs','task-scenes.js','hero-scenes.js',...unique,...spec.sections.flatMap(s=>s.backgrounds||[]),...Object.values(spec.microscopy||{}),...Array.from({length:9},(_,i)=>`assets/opening/cut${String(i+1).padStart(2,'0')}.png`),'fonts/NotoSansCJKkr-Regular.otf','fonts/NotoSansCJKkr-Bold.otf'].filter(Boolean);
const inputs=[...new Set(inputNames)].filter(f=>fs.existsSync(path.join(ROOT,f))).map(file=>({file,sha256:createHash('sha256').update(fs.readFileSync(path.join(ROOT,file))).digest('hex')}));
const canvas=createCanvas(W,H),ctx=canvas.getContext('2d');
function hash(buf){return createHash('sha256').update(buf).digest('hex')}
if(stills){
 const dir=path.join(OUT,'stills');fs.mkdirSync(dir,{recursive:true});const records=[];
 for(let i=0;i<timeline.entries.length;i++){
  const e=timeline.entries[i],t=e.start+Math.min((e.end-e.start)*.62,(e.end-e.start)-.06);const state=drawFrame(ctx,t,timeline,spec,assets);const f=`${String(i+1).padStart(3,'0')}_${e.section_id}_${e.kind}_${(e.cut_index??0)+1}.png`;
  fs.writeFileSync(path.join(dir,f),canvas.encodeSync('png'));records.push({file:f,time:t,section:e.section_id,kind:e.kind,cut_index:e.cut_index,caption:state.captions});
 }
 const motion=[];for(const e of timeline.entries.filter(x=>x.kind!=='title')){const d=e.end-e.start;drawFrame(ctx,e.start+d*.27,timeline,spec,assets);const a=hash(canvas.data());drawFrame(ctx,e.start+d*.77,timeline,spec,assets);const b=hash(canvas.data());motion.push({section:e.section_id,cut_index:e.cut_index,moving:a!==b});}
 fs.writeFileSync(path.join(OUT,'visual-validation.json'),JSON.stringify({status:motion.every(x=>x.moving)?'PASS':'REVIEW',records,motion,notes:['Frame differences verify visible changes; they do not prove photorealistic human movement.']},null,2)+'\n');console.log(JSON.stringify({stills:records.length,motion_pass:motion.filter(x=>x.moving).length,motion_total:motion.length}));
}else{
 const file=path.join(OUT,'video_silent.partial.mp4');const enc=spawn('ffmpeg',['-y','-v','error','-f','rawvideo','-pixel_format','rgba','-video_size',`${W}x${H}`,'-framerate',String(fps),'-i','-','-an','-vf','format=yuv420p','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-movflags','+faststart',file],{stdio:['pipe','inherit','inherit']});
 let failure;const done=new Promise((ok,no)=>{enc.once('error',no);enc.once('close',c=>c===0?ok():no(new Error('ffmpeg exit '+c)))});done.catch(e=>failure=e);enc.stdin.on('error',e=>failure=e);
 const started=Date.now();for(let frame=0;frame<frames;frame++){if(failure)throw failure;drawFrame(ctx,frame/fps,timeline,spec,assets);if(!enc.stdin.write(canvas.data()))await Promise.race([once(enc.stdin,'drain'),done.then(()=>{throw new Error('encoder ended')})]);if(frame%300===0)console.log(`Frame ${frame}/${frames}; elapsed ${((Date.now()-started)/1000).toFixed(1)}s`)}
 enc.stdin.end();await done;const probe=spawnSync('ffprobe',['-v','error','-show_streams','-show_format','-of','json',file],{encoding:'utf8'});if(probe.status)throw new Error(probe.stderr);const meta=JSON.parse(probe.stdout),v=meta.streams.find(s=>s.codec_type==='video');if(v.width!==W||v.height!==H||Number(v.nb_frames)!==frames||v.r_frame_rate!=='30/1')throw new Error('Video metadata mismatch');
 for(const item of inputs)if(hash(fs.readFileSync(path.join(ROOT,item.file)))!==item.sha256)throw new Error('Input changed during rendering: '+item.file);
 const target=path.join(OUT,'video_silent.mp4');fs.renameSync(file,target);fs.writeFileSync(path.join(OUT,'render-validation.json'),JSON.stringify({status:'PASS',duration:timeline.duration,frames,width:W,height:H,fps,elapsed_seconds:(Date.now()-started)/1000,sha256:hash(fs.readFileSync(target)),inputs},null,2)+'\n');console.log('Rendered '+target);
}
