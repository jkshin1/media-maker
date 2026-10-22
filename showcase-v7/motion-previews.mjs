#!/usr/bin/env node
/** Native motion previews: camera held still, approved photograph unchanged. */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {spawn} from 'node:child_process';
import {once} from 'node:events';
import {drawFrame} from './stage.mjs';
const ROOT=path.dirname(fileURLToPath(import.meta.url)),OUT=path.resolve(ROOT,'../out/showcase-v7');
const require=createRequire(import.meta.url);let native;try{native=require('@napi-rs/canvas')}catch{native=require('/Users/jk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@napi-rs/canvas')}
const {createCanvas,loadImage,GlobalFonts}=native;
for(const [f,name] of [['NotoSansCJKkr-Regular.otf','Noto'],['NotoSansCJKkr-Bold.otf','Noto']])GlobalFonts.registerFromPath(path.join(ROOT,'fonts',f),name);
const spec=JSON.parse(fs.readFileSync(path.join(ROOT,'spec.json'))),timeline=JSON.parse(fs.readFileSync(path.join(ROOT,'timeline.json')));
const files=['photo-motion-early.json','photo-motion-middle.json','photo-motion-late.json'];
const profiles=Object.assign({},...files.map(f=>JSON.parse(fs.readFileSync(path.join(ROOT,f))).tasks));
const assets={photoMotionProfiles:profiles,images:{},backgrounds:{},microscopy:{},transitionCanvas:createCanvas(1920,1080),spec,tasks:spec.sections.filter(s=>s.type==='task'),drawTitles:false,drawCaptions:false,freezeTaskBackground:true};
for(const s of spec.sections){if(s.reference_image&&!assets.images[s.reference_image])assets.images[s.reference_image]=await loadImage(path.join(ROOT,s.reference_image));assets.backgrounds[s.id]={};for(let i=0;i<s.cuts.length;i++){const f=s.backgrounds?.[i]||s.cuts[i].photo_crop||s.cuts[i].background||s.photo_crops?.[i];if(f&&fs.existsSync(path.join(ROOT,f)))assets.backgrounds[s.id][i]=await loadImage(path.join(ROOT,f));}}
for(const [id,f]of Object.entries(spec.microscopy||{}))assets.microscopy[id]=await loadImage(path.join(ROOT,f));
for(let i=1;i<=9;i++)assets.images[`opening${i}`]=await loadImage(path.join(ROOT,`assets/opening/cut${String(i).padStart(2,'0')}.png`));
const dir=path.join(OUT,'motion-preview');fs.mkdirSync(dir,{recursive:true});
const canvas=createCanvas(1920,1080),ctx=canvas.getContext('2d'),photo=timeline.entries.filter(e=>e.kind==='cut'&&e.cut_index===0&&profiles[e.section_id]);
const video=process.argv.includes('--video');let enc,done;if(video){enc=spawn('ffmpeg',['-y','-v','error','-f','rawvideo','-pixel_format','rgba','-video_size','1920x1080','-framerate','30','-i','-','-an','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',path.join(dir,'all-first-photos-fixed-camera.mp4')],{stdio:['pipe','inherit','inherit']});done=new Promise((ok,no)=>{enc.once('error',no);enc.once('close',c=>c===0?ok():no(new Error('Preview ffmpeg '+c)))});}
const records=[];
for(const entry of photo){
 const d=entry.end-entry.start;const record={section:entry.section_id,duration:d,action:profiles[entry.section_id].action_ko,images:[]};
 for(const u of [.22,.5,.78]){
  for(const active of [false,true]){
   assets.photoMotion=active;drawFrame(ctx,entry.start+d*u,timeline,spec,assets);const file=`${entry.section_id}_${u.toFixed(2)}_${active?'moving':'static'}.png`;
   fs.writeFileSync(path.join(dir,file),canvas.encodeSync('png'));record.images.push({file,u,active});
  }
 }
 if(video){assets.photoMotion=true;const frames=Math.floor(d*30);for(let f=0;f<frames;f++){drawFrame(ctx,entry.start+f/30,timeline,spec,assets);if(!enc.stdin.write(canvas.data()))await once(enc.stdin,'drain');}}
 records.push(record);console.log('Prepared '+entry.section_id+' '+d.toFixed(3)+'s');
}
if(video){enc.stdin.end();await done;}
fs.writeFileSync(path.join(dir,'preview-records.json'),JSON.stringify({camera_frozen:true,no_audio:true,records},null,2)+'\n');
