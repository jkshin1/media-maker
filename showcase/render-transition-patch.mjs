#!/usr/bin/env node
/* Lossless sparse overlay for the revised scene transitions.
 * Usage:
 *   node showcase/render-transition-patch.mjs
 *   node showcase/render-transition-patch.mjs --test
 *   node showcase/render-transition-patch.mjs --verify-existing
 *   node showcase/render-transition-patch.mjs --full-entry ending:5
 * --full-entry uses section_id:zero_based_cut_index. It is useful for a visual
 * correction that must persist after the first 0.45 seconds of an entry.
 * The source MP4 and existing render modules are read-only inputs.
 */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {createHash} from 'node:crypto';
import {spawn,spawnSync} from 'node:child_process';
import {once} from 'node:events';
import {drawFrame,W,H} from './stage.mjs';

const ROOT=path.dirname(fileURLToPath(import.meta.url));
const OUT=path.resolve(ROOT,'../out/showcase');
const argv=process.argv.slice(2),fullEntryKeys=new Set();
let test=false,verifyExisting=false,testFrameCount=20,outputOverride,sourceOverride;
for(let i=0;i<argv.length;i++){
 const arg=argv[i];
 if(arg==='--test')test=true;
 else if(arg==='--verify-existing')verifyExisting=true;
 else if(arg==='--test-frames'){test=true;testFrameCount=Number(argv[++i]);}
 else if(arg==='--full-entry')fullEntryKeys.add(argv[++i]);
 else if(arg==='--output')outputOverride=argv[++i];
 else if(arg==='--source')sourceOverride=argv[++i];
 else throw new Error(`Unknown argument: ${arg}`);
}
if(!Number.isInteger(testFrameCount)||testFrameCount<2)throw new Error('Test frame count must be an integer of at least 2.');
const require=createRequire(import.meta.url);
let native;try{native=require('@napi-rs/canvas')}catch{native=require('/Users/jk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@napi-rs/canvas')}
const {createCanvas,loadImage,GlobalFonts}=native;
const specPath=path.join(ROOT,'spec.json');
const timelinePath=path.join(ROOT,process.env.TIMELINE_FILE||'timeline.json');
const spec=JSON.parse(fs.readFileSync(specPath)),timeline=JSON.parse(fs.readFileSync(timelinePath));
const fps=Number(timeline.fps),totalFrames=Number(timeline.frames||Math.round(timeline.duration*fps)),windowSeconds=.45;
if(W!==1920||H!==1080||fps!==30)throw new Error('Sparse patch requires the original 1920x1080, 30fps canvas.');
if(!Number.isInteger(totalFrames)||totalFrames<1||timeline.duration>300)throw new Error('Invalid timeline frame count or five-minute cap.');
const source=path.resolve(sourceOverride||path.join(OUT,'RD_Process_AI_Fast_Track_Showcase.mp4'));
const output=path.resolve(outputOverride||path.join(OUT,test?'transition-patch-test.mov':'transition-patch.mov'));
if(source===output)throw new Error('Overlay output must not replace the source MP4.');
const reportPath=path.join(path.dirname(output),test?'transition-patch-test-validation.json':'transition-patch-validation.json');
const partial=output.replace(/\.mov$/i,'')+'.partial.mov';
const hash=buf=>createHash('sha256').update(buf).digest('hex');
function fileHash(file){
 const digest=createHash('sha256'),fd=fs.openSync(file,'r'),chunk=Buffer.allocUnsafe(8*1024*1024);
 try{let count;while((count=fs.readSync(fd,chunk,0,chunk.length,null))>0)digest.update(chunk.subarray(0,count));return digest.digest('hex');}
 finally{fs.closeSync(fd);}
}
function ffprobe(file){const r=spawnSync('ffprobe',['-v','error','-show_streams','-show_format','-of','json',file],{encoding:'utf8'});if(r.status!==0)throw new Error(`ffprobe failed: ${r.stderr}`);return JSON.parse(r.stdout)}
const sourceMeta=ffprobe(source),sourceVideo=sourceMeta.streams.find(s=>s.codec_type==='video');
if(!sourceVideo||sourceVideo.width!==W||sourceVideo.height!==H||sourceVideo.r_frame_rate!=='30/1'||Number(sourceVideo.nb_frames)!==totalFrames)throw new Error('Original MP4 metadata does not match the locked timeline.');
const sourceHash=fileHash(source);
const sourceAudio=sourceMeta.streams.filter(s=>s.codec_type==='audio').map(s=>({codec:s.codec_name,sample_rate:Number(s.sample_rate),channels:s.channels}));

const windows=[];
for(const entry of timeline.entries){
 const key=`${entry.section_id}:${entry.cut_index??0}`;
 const full=fullEntryKeys.has(key);
 if(entry.start<=0&&!full)continue;
 const startFrame=Number.isInteger(entry.start_frame)?entry.start_frame:Math.round(entry.start*fps);
 const endTime=full?entry.end:Math.min(entry.end,entry.start+windowSeconds);
 // A frame at start+13/30 is inside the 0.45 second window; the next is not.
 const endFrame=Math.min(totalFrames,Math.ceil(endTime*fps-1e-8));
 windows.push({section_id:entry.section_id,kind:entry.kind,cut_index:entry.cut_index??null,start_frame:startFrame,end_frame:endFrame,frame_count:endFrame-startFrame,mode:full?'full-entry':'transition',start:entry.start,end:endTime});
}
for(const key of fullEntryKeys)if(!windows.some(w=>`${w.section_id}:${w.cut_index??0}`===key))throw new Error(`Unknown full-entry selector: ${key}`);
const active=new Uint8Array(totalFrames);
for(const w of windows)for(let f=w.start_frame;f<w.end_frame;f++)active[f]=1;
const firstActive=active.findIndex(v=>v===1);
if(firstActive<0)throw new Error('No transition windows exist.');
const startFrame=test?Math.max(0,firstActive-2):0;
const frameCount=test?Math.min(testFrameCount,totalFrames-startFrame):totalFrames;
const endFrame=startFrame+frameCount;
const expectedNativeFrames=Array.from(active.subarray(startFrame,endFrame)).reduce((a,b)=>a+b,0);
const disk=fs.statfsSync(path.dirname(source));
const availableDiskBytes=Number(disk.bavail)*Number(disk.bsize);
// QTRLE is lossless. Allow even uncompressed-sized active pictures plus a
// generous blank-frame/container reserve before beginning the long pipe.
const estimatedMaximumPatchBytes=expectedNativeFrames*W*H*4+frameCount*W*4+256*1024*1024;
if(!verifyExisting&&availableDiskBytes<estimatedMaximumPatchBytes)throw new Error(`Insufficient disk headroom: ${availableDiskBytes} available, ${estimatedMaximumPatchBytes} reserved bytes.`);

GlobalFonts.registerFromPath(path.join(ROOT,'fonts/NotoSansCJKkr-Regular.otf'),'Noto');
GlobalFonts.registerFromPath(path.join(ROOT,'fonts/NotoSansCJKkr-Bold.otf'),'Noto');
const assets={images:{},backgrounds:{},videos:{},microscopy:{},transitionCanvas:createCanvas(W,H),spec,tasks:spec.sections.filter(s=>s.type==='task'),drawTitles:false,drawCaptions:false};
const inputFiles=new Set(['spec.json',path.relative(ROOT,timelinePath),'stage.mjs','task-scenes.js','hero-scenes.js','fonts/NotoSansCJKkr-Regular.otf','fonts/NotoSansCJKkr-Bold.otf']);
const imageCache=new Map();
async function imageFile(file){
 if(typeof file!=='string')throw new Error('Asset paths must be strings.');
 const absolute=path.join(ROOT,file);if(!fs.existsSync(absolute))throw new Error(`Missing patch asset: ${file}`);
 inputFiles.add(file);if(!imageCache.has(file))imageCache.set(file,await loadImage(absolute));return imageCache.get(file);
}
for(const file of [...new Set(spec.sections.map(s=>s.reference_image).filter(Boolean))])assets.images[file]=await imageFile(file);
for(const section of spec.sections){
 assets.backgrounds[section.id]={};
 for(let i=0;i<section.cuts.length;i++){
  const file=section.backgrounds?.[i]||section.cuts[i].photo_crop||section.cuts[i].background||section.photo_crops?.[i];
  if(file){const im=await imageFile(file);assets.backgrounds[section.id][i]=im;assets.images[file]=im;}
 }
}
for(const [id,file] of Object.entries(spec.microscopy||{}))assets.microscopy[id]=await imageFile(file);
for(let i=1;i<=9;i++){const file=`assets/opening/cut${String(i).padStart(2,'0')}.png`;if(fs.existsSync(path.join(ROOT,file)))assets.images[`opening${i}`]=await imageFile(file);}
const inputs=[...inputFiles].sort().map(file=>({file,sha256:fileHash(path.resolve(ROOT,file))}));

fs.mkdirSync(path.dirname(output),{recursive:true});
const canvas=createCanvas(W,H),ctx=canvas.getContext('2d');
const transparent=Buffer.alloc(W*H*4,0);
const validationSamples=[];
let nativeFrames=0,transparentFrames=0,priorSnapshot;
const started=Date.now();
function alphaRange(bytes){let min=255,max=0;for(let k=3;k<bytes.length;k+=4){const a=bytes[k];if(a<min)min=a;if(a>max)max=a}return {min,max}}
const sampleNativeFrame=Math.min(firstActive+7,endFrame-1);
if(verifyExisting){
 if(!fs.existsSync(output))throw new Error(`Completed overlay does not exist: ${output}`);
 const priorPath=path.join(path.dirname(output),'transition-patch-test-validation.json');
 if(fs.existsSync(priorPath)){
  priorSnapshot=JSON.parse(fs.readFileSync(priorPath));
  if(priorSnapshot.source_video.sha256!==sourceHash)throw new Error('Source video differs from the earlier alpha proof.');
  for(const input of priorSnapshot.inputs||[])if(fileHash(path.resolve(ROOT,input.file))!==input.sha256)throw new Error(`Source changed since earlier alpha proof: ${input.file}`);
 }
 for(const frame of [...new Set([startFrame,sampleNativeFrame])]){
  let pixels;if(active[frame]){drawFrame(ctx,frame/fps,timeline,spec,assets);pixels=canvas.data();}else pixels=transparent;
  const alpha=alphaRange(pixels);validationSamples.push({global_frame:frame,overlay_frame:frame-startFrame,time:frame/fps,active:Boolean(active[frame]),rgba_sha256:hash(pixels),alpha_min:alpha.min,alpha_max:alpha.max});
 }
 nativeFrames=expectedNativeFrames;transparentFrames=frameCount-nativeFrames;
 console.log(`Verifying existing ${frameCount}-frame overlay; encoding skipped.`);
}else{
const encoder=spawn('ffmpeg',['-y','-v','error','-f','rawvideo','-pixel_format','rgba','-video_size',`${W}x${H}`,'-framerate',String(fps),'-i','-','-an','-c:v','qtrle','-pix_fmt','argb',partial],{stdio:['pipe','inherit','inherit']});
let encoderFailure;
const encoded=new Promise((resolve,reject)=>{encoder.once('error',reject);encoder.once('close',code=>code===0?resolve():reject(new Error(`Patch encoder exited ${code}`)))});
encoded.catch(error=>{encoderFailure=error});encoder.stdin.on('error',error=>{encoderFailure=error});
for(let frame=startFrame;frame<endFrame;frame++){
 if(encoderFailure)throw encoderFailure;
 let pixels;
 if(active[frame]){drawFrame(ctx,frame/fps,timeline,spec,assets);pixels=canvas.data();nativeFrames++;}
 else{pixels=transparent;transparentFrames++;}
 if(frame===startFrame||frame===sampleNativeFrame){const alpha=alphaRange(pixels);validationSamples.push({global_frame:frame,overlay_frame:frame-startFrame,time:frame/fps,active:Boolean(active[frame]),rgba_sha256:hash(pixels),alpha_min:alpha.min,alpha_max:alpha.max});}
 if(!encoder.stdin.write(pixels))await Promise.race([once(encoder.stdin,'drain'),encoded.then(()=>{throw new Error('Patch encoder ended before all frames were supplied.');})]);
 if((frame-startFrame)%300===0)console.log(`Patch frame ${frame-startFrame}/${frameCount}; native ${nativeFrames}; elapsed ${((Date.now()-started)/1000).toFixed(1)}s`);
}
encoder.stdin.end();await encoded;
}
const verificationFile=verifyExisting?output:partial;
const metadata=ffprobe(verificationFile),stream=metadata.streams.find(s=>s.codec_type==='video');
if(!stream||stream.width!==W||stream.height!==H||stream.r_frame_rate!=='30/1'||stream.codec_name!=='qtrle'||stream.pix_fmt!=='argb'||Number(stream.nb_frames)!==frameCount||metadata.streams.some(s=>s.codec_type==='audio'))throw new Error('Encoded overlay dimensions, alpha format, frame count or stream layout mismatch.');
const decodedSamples=[];
for(const sample of validationSamples){
 const decode=spawnSync('ffmpeg',['-v','error','-i',verificationFile,'-vf',`select=eq(n\\,${sample.overlay_frame}),format=rgba`,'-frames:v','1','-f','rawvideo','-'],{maxBuffer:W*H*4+65536});
 if(decode.status!==0||decode.stdout.length!==W*H*4)throw new Error(`Overlay sample decode failed at ${sample.overlay_frame}: ${decode.stderr.toString()}`);
 const decoded=decode.stdout,alpha=alphaRange(decoded),sha256=hash(decoded);
 if(sha256!==sample.rgba_sha256)throw new Error(`Lossless RGBA sample mismatch at ${sample.overlay_frame}`);
 decodedSamples.push({overlay_frame:sample.overlay_frame,active:sample.active,rgba_sha256:sha256,alpha_min:alpha.min,alpha_max:alpha.max,lossless_matches:true});
}
const alphaDecode=spawnSync('ffmpeg',['-v','error','-i',verificationFile,'-map','0:v:0','-vf','crop=1:1:0:0,alphaextract','-vsync','0','-f','rawvideo','-pix_fmt','gray','-'],{maxBuffer:frameCount+65536});
if(alphaDecode.status!==0||alphaDecode.stdout.length!==frameCount)throw new Error(`Full-frame alpha timeline decode failed: ${alphaDecode.stderr.toString()}`);
let encodedOpaqueFrames=0,encodedTransparentFrames=0;
for(let i=0;i<frameCount;i++){
 const actual=alphaDecode.stdout[i],expected=active[startFrame+i]?255:0;
 if(actual!==expected)throw new Error(`Alpha timeline mismatch at global frame ${startFrame+i}: expected ${expected}, received ${actual}`);
 if(actual===255)encodedOpaqueFrames++;else encodedTransparentFrames++;
}
for(const input of inputs)if(fileHash(path.resolve(ROOT,input.file))!==input.sha256)throw new Error(`Render input changed while creating patch: ${input.file}`);
if(fileHash(source)!==sourceHash)throw new Error('Original MP4 changed while creating overlay.');
if(!verifyExisting)fs.renameSync(partial,output);
const report={status:'PASS',scope:test?`${frameCount}-frame alpha/codec proof for first transition window`:'Full-length sparse transition overlay; final source/overlay mux remains separate',output,path_sha256:fileHash(output),source_video:{file:source,sha256:sourceHash,frames:totalFrames,audio_streams:sourceAudio,unchanged:true},width:W,height:H,fps,codec:stream.codec_name,pixel_format:stream.pix_fmt,has_alpha:true,has_audio:false,output_frames:frameCount,output_seconds:frameCount/fps,start_global_frame:startFrame,source_timeline_duration:timeline.duration,window_seconds:windowSeconds,transition_window_count:windows.filter(w=>w.mode==='transition').length,full_entry_selectors:[...fullEntryKeys],native_frames:nativeFrames,transparent_frames:transparentFrames,expected_active_frames:expectedNativeFrames,elapsed_seconds:(Date.now()-started)/1000,disk:{available_bytes_before:availableDiskBytes,reserved_maximum_patch_bytes:estimatedMaximumPatchBytes,actual_patch_bytes:fs.statSync(output).size},windows,decoded_rgba_samples:decodedSamples,inputs,notes:['All timing uses explicit global frame/fps time.','Inactive frames are zero in every RGBA channel; active frames replace the complete scene transition with the new stage renderer.','The lossless overlay has no audio and does not edit the original source MP4. Preserve the original audio stream when muxing the final revision.','Full-entry selectors are required for corrections that persist beyond a transition window.']};
report.verify_existing=verifyExisting;
report.encoding_skipped=verifyExisting;
report.earlier_alpha_proof_input_snapshot_matched=verifyExisting?Boolean(priorSnapshot):null;
report.decoded_alpha_timeline={frames:alphaDecode.stdout.length,opaque_frames:encodedOpaqueFrames,transparent_frames:encodedTransparentFrames,all_frames_match_expected_windows:true,sampling:'top-left alpha pixel on every decoded frame; complete RGBA/alpha checks on representative opaque and transparent frames'};
fs.writeFileSync(reportPath,JSON.stringify(report,null,2)+'\n');
const stageText=fs.readFileSync(path.join(ROOT,'stage.mjs'),'utf8');
const metadataPath=path.join(path.dirname(output),test?'soft-transitions-test-metadata.json':'soft-transitions-metadata.json');
fs.writeFileSync(metadataPath,JSON.stringify({gold_sweep_removed:stageText.includes('local<.45')&&stageText.includes('assets.transitionCanvas')&&!stageText.includes('local<.22'),transition_seconds:windowSeconds,transition_starts:timeline.entries.filter(e=>e.start>0).map(e=>e.start),source_spec_sha256:fileHash(specPath),source_timeline_sha256:fileHash(timelinePath),stage_sha256:fileHash(path.join(ROOT,'stage.mjs')),source_video_sha256:sourceHash,overlay_sha256:report.path_sha256,overlay_frames:frameCount,test_only:test},null,2)+'\n');
console.log(JSON.stringify({status:'PASS',output,report:reportPath,frames:frameCount,native_frames:nativeFrames,transparent_frames:transparentFrames,codec:stream.codec_name,pix_fmt:stream.pix_fmt,source_unchanged:true}));
