#!/usr/bin/env node
/** Read-only media QA: continuous, muted, real-time playback in Chromium.
 * MP4 is served over loopback HTTP with byte ranges. There are no seeks after
 * play(), no rate acceleration, and no project or video source changes.
 */
import puppeteer from 'puppeteer-core';
import { createHash } from 'node:crypto';
import { createReadStream, existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { createServer } from 'node:http';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root=path.dirname(fileURLToPath(import.meta.url));
const out=path.resolve(process.env.SHOWCASE_OUT||path.join(root,'../out/showcase-v8'));
const videoFile=path.join(out,process.env.SHOWCASE_VIDEO||'RD_Process_AI_Fast_Track_Showcase_Revision8.mp4');
const reportFile=path.join(out,process.env.SHOWCASE_REPORT||'playback-validation.json');
const evidence=path.join(out,process.env.SHOWCASE_EVIDENCE||'playback');
const args=process.argv.slice(2);
if(args.includes('--help')){
 console.log('node showcase-v8/playback-check.mjs\nPlays Revision8 at muted 1x from zero to ended; no seeks or pauses.\nCHROME_PATH: Chromium executable. SHOWCASE_OUT: output directory. SHOWCASE_VIDEO: video filename.\nDurations over five minutes require timeline.allow_over_five_minutes === true.\nMissing final file: writes WAIT and exits 2. Validation failure: exits 1.');
 process.exit(0);
}
if(args.length)throw new Error('Unknown argument; use --help.');
mkdirSync(out,{recursive:true});
if(!existsSync(videoFile)){
 writeFileSync(reportFile,JSON.stringify({status:'WAIT',file:videoFile,reason:'Final MP4 is not present. Run this checker after the completed MP4 is copied into place.',playback_started:false},null,2)+'\n');
 console.log(`WAIT: ${videoFile}`);process.exit(2);
}

const spec=JSON.parse(readFileSync(path.join(root,'spec.json'),'utf8'));
const timelineFile=process.env.TIMELINE_FILE||'timeline.json';
const timeline=JSON.parse(readFileSync(path.join(root,timelineFile),'utf8'));
const expected={width:1920,height:1080,fps:30,duration:Number(timeline.duration??timeline.duration_seconds),frames:Number(timeline.frames)};
const allowOverFiveMinutes=timeline.allow_over_five_minutes===true;
if(!Number.isFinite(expected.duration)||expected.duration<=0)throw new Error('Invalid locked timeline duration.');
if(expected.duration>300&&!allowOverFiveMinutes)throw new Error('Locked timeline exceeds five minutes without explicit allowance.');
const tolerance=2/expected.fps;
const candidates=[process.env.CHROME_PATH,
 '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
 '/Applications/Chromium.app/Contents/MacOS/Chromium',
 '/usr/bin/google-chrome','/usr/bin/chromium','/usr/bin/chromium-browser',
 'C:/Program Files/Google/Chrome/Application/chrome.exe',
 'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe'].filter(Boolean);
const chrome=candidates.find(existsSync);
const fileStat=statSync(videoFile);
const report={status:'FAIL',file:videoFile,timeline_file:timelineFile,preview_only:timeline.preview_only===true,final_production_complete:false,browser_executable:chrome||null,expected,
 duration_policy:{allow_over_five_minutes:allowOverFiveMinutes,exceeds_five_minutes:expected.duration>300},
 viewport:{width:1920,height:1080,deviceScaleFactor:1},duration_tolerance_seconds:tolerance,
 method:'Continuous HTMLVideoElement playback over loopback HTTP, starting at 0, muted at 1x; no seeking or pausing during playback.',
 audio_scope:'Muted browser playback verifies video decoding. Audio decoding and narration/BGM checks are separate; no subjective listening claim is made.',
 visual_scope:'Full-size browser screenshots at the initial frame, each of the 87 scene entries, and ended frame; brightness sampled about once per second. This does not prove every rendered frame or subjective design quality.',
 playback_timeout_ms:Math.ceil((expected.duration+60)*1000),
 file_bytes:fileStat.size,page_errors:[],media_errors:[],http_requests:[],http_errors:[],
 screenshot_samples:[],progress:[],screenshot_targets:[],};
function writeReport(){writeFileSync(reportFile,JSON.stringify(report,null,2)+'\n');}
async function digest(file){const hash=createHash('sha256');for await(const chunk of createReadStream(file))hash.update(chunk);return hash.digest('hex');}
function sectionTargets(){
 return timeline.entries.map((e,index)=>{
  const section=spec.sections.find(s=>s.id===e.section_id);
  return {section_id:section.id,section_type:section.type,section_title:section.title,entry_number:index+1,
   kind:e.kind,cut_index:e.cut_index??null,target_seconds:e.start+(e.end-e.start)*.62};
 });
}

const html='<!doctype html><meta charset="utf-8"><title>Showcase playback validation</title><style>html,body{margin:0;width:100%;height:100%;overflow:hidden;background:#080808}video{display:block;position:fixed;inset:0;width:100vw;height:100vh;object-fit:contain;background:#080808}</style><video id="film" playsinline preload="auto"></video>';
let server,browser,page;
try{
 if(!chrome)throw new Error('Chrome/Chromium not found. Set CHROME_PATH.');
 report.sha256=await digest(videoFile);
 report.screenshot_targets=sectionTargets();
 if(report.screenshot_targets.length!==87)throw new Error('Expected 87 scene samples, found '+report.screenshot_targets.length);
 mkdirSync(evidence,{recursive:true});
 server=createServer((req,res)=>{
  const url=new URL(req.url,'http://127.0.0.1');
  if(url.pathname==='/favicon.ico'){res.writeHead(204).end();return;}
  if(url.pathname==='/'){
   if(req.method!=='GET'&&req.method!=='HEAD'){res.writeHead(405).end();return;}
   const data=Buffer.from(html);res.writeHead(200,{'Content-Type':'text/html; charset=utf-8','Content-Length':data.length,'Cache-Control':'no-store'});res.end(req.method==='HEAD'?undefined:data);return;
  }
  if(url.pathname!=='/film.mp4'){res.writeHead(404).end();return;}
  if(req.method!=='GET'&&req.method!=='HEAD'){res.writeHead(405,{'Allow':'GET, HEAD'}).end();return;}
  const total=fileStat.size,headers={'Content-Type':'video/mp4','Accept-Ranges':'bytes','Cache-Control':'no-store'};
  let start=0,end=total-1,status=200;
  if(req.headers.range){
   const range=/^bytes=(\d*)-(\d*)$/.exec(req.headers.range);
   if(!range||(!range[1]&&!range[2])){res.writeHead(416,{...headers,'Content-Range':`bytes */${total}`}).end();return;}
   if(!range[1]){const count=Number(range[2]);if(!Number.isSafeInteger(count)||count<=0){res.writeHead(416,{...headers,'Content-Range':`bytes */${total}`}).end();return;}start=Math.max(0,total-count);}
   else{start=Number(range[1]);if(range[2])end=Math.min(total-1,Number(range[2]));}
   if(!Number.isSafeInteger(start)||!Number.isSafeInteger(end)||start<0||start>=total||end<start){res.writeHead(416,{...headers,'Content-Range':`bytes */${total}`}).end();return;}
   status=206;headers['Content-Range']=`bytes ${start}-${end}/${total}`;
  }
  headers['Content-Length']=end-start+1;
  if(report.http_requests.length<100)report.http_requests.push({method:req.method,status,range:req.headers.range||null,start,end,bytes:end-start+1});
  res.writeHead(status,headers);if(req.method==='HEAD'){res.end();return;}
  const stream=createReadStream(videoFile,{start,end});stream.on('error',error=>{report.http_errors.push(error.message);res.destroy(error);});res.on('close',()=>stream.destroy());stream.pipe(res);
 });
 server.keepAliveTimeout=1000;
 await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
 const source=`http://127.0.0.1:${server.address().port}`;report.source_url=source+'/film.mp4';
 browser=await puppeteer.launch({executablePath:chrome,headless:true,args:[
  '--autoplay-policy=no-user-gesture-required','--hide-scrollbars','--force-device-scale-factor=1','--force-color-profile=srgb',
  '--disable-background-timer-throttling','--disable-renderer-backgrounding','--disable-backgrounding-occluded-windows']});
 report.browser_version=await browser.version();page=await browser.newPage();await page.setViewport(report.viewport);page.setDefaultTimeout(30000);
 page.on('pageerror',error=>report.page_errors.push(error.message));
 await page.goto(source+'/',{waitUntil:'load',timeout:30000});
 report.metadata=await page.evaluate(async config=>{
  const video=document.getElementById('film');video.controls=false;video.autoplay=false;video.loop=false;video.muted=true;video.volume=1;video.playbackRate=1;
  const state=window.__playback={events:[],mediaErrors:[],ended:false,loadedmetadata:false,playResolved:false,startedPerformance:null,startedMediaTime:null,frameCallbacks:0,frameSamples:[],lastSample:-1,firstMediaTime:null,lastMediaTime:null,hasVideoFrameCallback:typeof video.requestVideoFrameCallback==='function'};
  const image=document.createElement('canvas');image.width=160;image.height=90;const context=image.getContext('2d',{willReadFrequently:true});
  const mediaError=()=>video.error?{code:video.error.code,message:video.error.message}:null;
  state.pixelStats=()=>{
   context.drawImage(video,0,0,160,90);const pixels=context.getImageData(0,0,160,90).data;let sum=0,black=0;
   for(let i=0;i<pixels.length;i+=4){const value=.2126*pixels[i]+.7152*pixels[i+1]+.0722*pixels[i+2];sum+=value;if(value<4)black++;}
   return {mean_luma:sum/(pixels.length/4),near_black_fraction:black/(pixels.length/4)};
  };
  const sample=time=>{
   if(!video.videoWidth||time-state.lastSample<.95)return;state.lastSample=time;
   const nearTransition=config.transitions.some(start=>Math.abs(time-start)<.28),initial=time<.75;
   try{const p=state.pixelStats();state.frameSamples.push({media_time:time,...p,near_transition:nearTransition,intentional_initial:initial,suspicious_black:!initial&&!nearTransition&&p.mean_luma<1.5&&p.near_black_fraction>.998});}catch(error){state.mediaErrors.push({code:'PIXELS',message:String(error)});}
  };
  for(const type of ['loadedmetadata','loadeddata','canplay','play','playing','pause','waiting','stalled','seeking','seeked','ratechange','ended','error'])video.addEventListener(type,()=>{
   const error=mediaError();state.events.push({type,currentTime:video.currentTime,wall_seconds:state.startedPerformance===null?null:(performance.now()-state.startedPerformance)/1000,readyState:video.readyState,playbackRate:video.playbackRate,error});
   if(type==='loadedmetadata')state.loadedmetadata=true;if(type==='ended')state.ended=true;if(type==='error')state.mediaErrors.push(error||{code:null,message:'Unknown media error'});
  });
  video.addEventListener('timeupdate',()=>{if(!state.hasVideoFrameCallback)sample(video.currentTime);});
  const ready=new Promise((resolve,reject)=>{
   const timer=setTimeout(()=>reject(new Error('MP4 metadata/first-frame load timed out after 30 seconds')),30000);
   video.addEventListener('loadeddata',()=>{clearTimeout(timer);resolve({width:video.videoWidth,height:video.videoHeight,duration:video.duration,currentTime:video.currentTime,readyState:video.readyState,muted:video.muted,playbackRate:video.playbackRate});},{once:true});
   video.addEventListener('error',()=>{clearTimeout(timer);reject(new Error('Loading MP4: '+JSON.stringify(mediaError())));},{once:true});
  });
  video.src=config.source;video.load();const metadata=await ready;
  if(state.hasVideoFrameCallback){const next=(now,frame)=>{state.frameCallbacks++;if(state.firstMediaTime===null)state.firstMediaTime=frame.mediaTime;state.lastMediaTime=frame.mediaTime;sample(frame.mediaTime);if(!video.ended)video.requestVideoFrameCallback(next);};video.requestVideoFrameCallback(next);}
  return metadata;
 },{source:report.source_url,transitions:timeline.entries.map(e=>e.start)});
 if(report.metadata.width!==expected.width||report.metadata.height!==expected.height||Math.abs(report.metadata.duration-expected.duration)>tolerance)throw new Error('Browser MP4 metadata does not match the locked Full HD timeline.');
 if(report.metadata.currentTime!==0||!report.metadata.muted||report.metadata.playbackRate!==1)throw new Error('Video must load at zero, muted, at normal speed.');
 async function observe(){return await page.evaluate(()=>{
  const v=document.getElementById('film'),q=v.getVideoPlaybackQuality?.(),s=window.__playback;
  return {currentTime:v.currentTime,duration:v.duration,paused:v.paused,ended:v.ended,readyState:v.readyState,networkState:v.networkState,muted:v.muted,playbackRate:v.playbackRate,
   decoded_frames:typeof v.webkitDecodedFrameCount==='number'?v.webkitDecodedFrameCount:q?.totalVideoFrames??null,
   dropped_frames:typeof v.webkitDroppedFrameCount==='number'?v.webkitDroppedFrameCount:q?.droppedVideoFrames??null,
   corrupted_frames:q?.corruptedVideoFrames??null,error:v.error?{code:v.error.code,message:v.error.message}:null,
   wall_seconds:s.startedPerformance===null?null:(performance.now()-s.startedPerformance)/1000};
 });}
 async function screenshot(name,label,target=null){
  const before=await observe(),file=name+'.png';await page.screenshot({path:path.join(evidence,file),type:'png'});const after=await observe();
  const pixels=await page.evaluate(()=>window.__playback.pixelStats());
  report.screenshot_samples.push({label,target_seconds:target,file:path.join('playback',file),screenshot_width:1920,screenshot_height:1080,before,after,pixels});
 }
 await screenshot('000_initial_0.000s','Initial decoded frame',0);
 await page.evaluate(async()=>{const v=document.getElementById('film'),s=window.__playback;s.startedMediaTime=v.currentTime;s.startedPerformance=performance.now();await v.play();s.playResolved=true;});
 report.status='RUNNING';
 const wallStart=Date.now();let nextScreenshot=0,nextLog=0,lastMedia=0,lastAdvance=Date.now();
 console.log(`Playback started: 0.000 / ${expected.duration.toFixed(3)}s, muted, 1x`);
 while(true){
  const current=await observe(),elapsed=(Date.now()-wallStart)/1000;
  if(current.error)throw new Error('Media decoder error: '+JSON.stringify(current.error));
  if(current.playbackRate!==1||!current.muted)throw new Error('Playback speed or mute state changed.');
  if(current.currentTime<lastMedia-tolerance)throw new Error('Playback media time moved backwards.');
  if(current.currentTime>lastMedia+.025){lastAdvance=Date.now();lastMedia=current.currentTime;}
  if(!current.ended&&Date.now()-lastAdvance>20000)throw new Error('Media time stopped advancing for 20 seconds.');
  while(nextScreenshot<report.screenshot_targets.length&&current.currentTime>=report.screenshot_targets[nextScreenshot].target_seconds){
   const target=report.screenshot_targets[nextScreenshot];if(current.ended)throw new Error('Playback ended before the section screenshot '+target.section_id);
   const label=`${String(nextScreenshot+1).padStart(3,'0')}_${target.section_id}_${target.target_seconds.toFixed(3)}s`;await screenshot(label,target.section_title,target.target_seconds);nextScreenshot++;
  }
  if(elapsed>=nextLog||current.ended){report.progress.push(current);console.log(`Playback ${current.currentTime.toFixed(3)}/${current.duration.toFixed(3)}s; wall ${elapsed.toFixed(1)}s; decoded ${current.decoded_frames}; dropped ${current.dropped_frames}`);nextLog=elapsed+15;writeReport();}
  if(current.ended){report.final=current;break;}
  if(Date.now()-wallStart>report.playback_timeout_ms)throw new Error('Real-time playback exceeded the duration plus 60 seconds.');
  await new Promise(resolve=>setTimeout(resolve,250));
 }
 await screenshot('999_final_ended','Final decoded frame after ended',report.final.currentTime);
 const state=await page.evaluate(()=>{
  const s=window.__playback;return {events:s.events,mediaErrors:s.mediaErrors,ended:s.ended,loadedmetadata:s.loadedmetadata,playResolved:s.playResolved,startedMediaTime:s.startedMediaTime,frameCallbacks:s.frameCallbacks,frameSamples:s.frameSamples,firstMediaTime:s.firstMediaTime,lastMediaTime:s.lastMediaTime,hasVideoFrameCallback:s.hasVideoFrameCallback};
 });
 report.events=state.events;report.frame_samples=state.frameSamples;report.media_errors=state.mediaErrors;report.frame_callbacks=state.frameCallbacks;report.video_frame_callback_supported=state.hasVideoFrameCallback;
 report.started_media_time=state.startedMediaTime;report.first_presented_media_time=state.firstMediaTime;report.last_presented_media_time=state.lastMediaTime;
 report.loadedmetadata=state.loadedmetadata;report.play_promise_resolved=state.playResolved;report.ended_event=state.ended;report.playback_wall_seconds=(Date.now()-wallStart)/1000;
 const playingEvents=state.events.filter(e=>e.wall_seconds!==null);
 report.seeks_during_playback=playingEvents.filter(e=>e.type==='seeking').length;
 report.pauses_during_playback=playingEvents.filter(e=>e.type==='pause'&&e.currentTime<report.final.duration-tolerance).length;
 report.suspicious_black_samples=state.frameSamples.filter(s=>s.suspicious_black);
 report.sha256_after_playback=await digest(videoFile);
 const sampleCoverage=state.frameSamples.length>=Math.floor(expected.duration*.70);
 report.pixel_sample_coverage_sufficient=sampleCoverage;
 if(!state.loadedmetadata||!state.playResolved||state.startedMediaTime!==0||!state.ended||!report.final.ended||report.final.error||state.mediaErrors.length||report.page_errors.length||report.http_errors.length||
    report.seeks_during_playback||report.pauses_during_playback||nextScreenshot!==report.screenshot_targets.length||!report.final.decoded_frames||report.final.decoded_frames<expected.frames*.80||
    Math.abs(report.final.currentTime-expected.duration)>tolerance||report.playback_wall_seconds<expected.duration-.75||!sampleCoverage||report.suspicious_black_samples.length||report.sha256!==report.sha256_after_playback){
  throw new Error('Continuous browser playback validation failed; inspect retained events, frame samples and screenshots.');
 }
 report.status='PASS';
}catch(error){report.status='FAIL';report.failure=String(error.stack||error);process.exitCode=1;
 if(page){try{report.failure_observation=await page.evaluate(()=>{const v=document.getElementById('film');return v?{currentTime:v.currentTime,ended:v.ended,paused:v.paused,error:v.error?{code:v.error.code,message:v.error.message}:null,state:window.__playback?{events:window.__playback.events,mediaErrors:window.__playback.mediaErrors}:null}:null;});}catch{}}
}finally{
 if(browser){try{await browser.close();}catch(error){report.browser_close_error=String(error);}}
 if(server){server.closeAllConnections?.();await new Promise(resolve=>server.close(resolve));}
 writeReport();
}
console.log(`${report.status}: ${reportFile}`);if(report.failure)console.error(report.failure);
