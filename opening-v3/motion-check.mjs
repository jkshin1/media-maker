#!/usr/bin/env node
/* Independent rendered-pixel motion check. It freezes only the camera through
 * the public QA hook, reads the actual canvas, and excludes DOM typography. */
import puppeteer from 'puppeteer-core';
import {createServer} from 'node:http';
import {createReadStream,existsSync,mkdirSync,readFileSync,statSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const base=path.dirname(fileURLToPath(import.meta.url));
const output=path.resolve(process.env.OPENING_OUT||path.join(base,'../out/opening-v3'));
const directory=path.join(output,'motion');mkdirSync(directory,{recursive:true});
const cuts=[0,3,7,12,17,22,28,35,42,46];
const W=1920,H=1080,ROI_WIDTH=1235,CHANNEL_THRESHOLD=10,MIN_CHANGED_FRACTION=.002;
const sha=data=>createHash('sha256').update(data).digest('hex');
const digest=file=>sha(readFileSync(file));
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.png':'image/png','.otf':'font/otf','.woff2':'font/woff2','.wav':'audio/wav'};
const server=createServer((req,res)=>{
  try{
    const name=decodeURIComponent(new URL(req.url,'http://127.0.0.1').pathname);
    const file=path.resolve(base,'.'+(name==='/'?'/index.html':name));
    if(path.relative(base,file).startsWith('..')||!statSync(file).isFile()){res.writeHead(404).end();return;}
    res.writeHead(200,{'Content-Type':mime[path.extname(file)]||'application/octet-stream'});createReadStream(file).pipe(res);
  }catch{res.writeHead(404).end();}
});
await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve);});
const url=`http://127.0.0.1:${server.address().port}/index.html?render=1`;
const candidates=[process.env.CHROME_PATH,'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','/usr/bin/google-chrome','/usr/bin/chromium','/usr/bin/chromium-browser','C:/Program Files/Google/Chrome/Application/chrome.exe'].filter(Boolean);
const chrome=candidates.find(existsSync);if(!chrome){server.close();throw new Error('Set CHROME_PATH to Chrome/Chromium.');}
let browser;
try{
  browser=await puppeteer.launch({executablePath:chrome,headless:true,args:['--hide-scrollbars','--force-device-scale-factor=1','--force-color-profile=srgb']});
  const page=await browser.newPage();await page.setViewport({width:W,height:H,deviceScaleFactor:1});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto(url,{waitUntil:'load',timeout:60000});await page.evaluate(async()=>{await window.__ready;await document.fonts.ready;});
  const noCaptions=await page.evaluate(()=>({
    forbidden_nodes:document.querySelectorAll('#caption,.caption,#captionBand,#captionLine,[data-narration-caption]').length,
    scene_nodes:document.querySelectorAll('.scene').length
  }));
  const records=[];
  for(let index=0;index<9;index++){
    const duration=cuts[index+1]-cuts[index];
    const locals=[.65,duration/2,duration-.35];
    await page.evaluate(()=>{window.__freezeCamera=true;window.__motionPixels={first:null,previous:null};});
    const frames=[];
    for(const local of locals){
      const time=cuts[index]+local;
      const snapshot=await page.evaluate(({time,roiWidth,channelThreshold})=>{
        window.__seek(time);
        const canvas=document.getElementById('visual');
        const data=canvas.getContext('2d').getImageData(0,0,roiWidth,1080).data;
        const qa=window.__motionPixels;
        function compare(previous){
          if(!previous)return null;
          let sampled=0,changed=0,sum=0,minX=roiWidth,minY=1080,maxX=-1,maxY=-1;
          for(let y=0;y<1080;y+=2)for(let x=0;x<roiWidth;x+=2){
            const k=(y*roiWidth+x)*4;
            const dr=Math.abs(data[k]-previous[k]),dg=Math.abs(data[k+1]-previous[k+1]),db=Math.abs(data[k+2]-previous[k+2]);
            sampled++;sum+=(dr+dg+db)/3;
            if(Math.max(dr,dg,db)>channelThreshold){changed++;minX=Math.min(minX,x);minY=Math.min(minY,y);maxX=Math.max(maxX,x);maxY=Math.max(maxY,y);}
          }
          return{sampled_pixels:sampled,changed_pixels:changed,changed_fraction:changed/sampled,mean_absolute_rgb_difference:sum/sampled,
            changed_bounds:changed?{left:minX,top:minY,right:maxX,bottom:maxY}:null};
        }
        const againstFirst=compare(qa.first),againstPrevious=compare(qa.previous);
        if(!qa.first)qa.first=new Uint8ClampedArray(data);qa.previous=new Uint8ClampedArray(data);
        const pixels=canvas.toDataURL('image/png');
        window.__seek(time);const repeat=canvas.toDataURL('image/png');
        const hero=typeof window.drawHeroEffect?.geometry==='function'?window.drawHeroEffect.geometry(7,window.__state.local,7):null;
        return{state:{...window.__state},camera_frozen:window.__freezeCamera===true,canvas_width:canvas.width,canvas_height:canvas.height,
          against_first:againstFirst,against_previous:againstPrevious,deterministic_same_time:pixels===repeat,pixels,
          hero:indexForState(window.__state.cut,hero),caption_nodes:document.querySelectorAll('#caption,.caption,#captionBand,#captionLine').length};
        function indexForState(cut,geometry){return cut===8&&geometry?{progress:geometry.progress,tip:geometry.tip,arrived:geometry.arrived}:null;}
      },{time,roiWidth:ROI_WIDTH,channelThreshold:CHANNEL_THRESHOLD});
      const png=Buffer.from(snapshot.pixels.split(',')[1],'base64');delete snapshot.pixels;
      const filename=`cut${String(index+1).padStart(2,'0')}_local${local.toFixed(2)}_camera-frozen.png`;
      writeFileSync(path.join(directory,filename),png);
      frames.push({local_seconds:local,time_seconds:time,file:path.relative(base,path.join(directory,filename)),sha256:sha(png),...snapshot});
    }
    const timelinePass=frames.every(frame=>frame.state.cut===index+1&&frame.state.captions===false&&frame.caption_nodes===0&&frame.canvas_width===W&&frame.canvas_height===H&&frame.camera_frozen&&frame.deterministic_same_time);
    const maxDifference=Math.max(...frames.map(frame=>frame.against_first?.changed_fraction||0));
    const nonCameraMotion=maxDifference>=MIN_CHANGED_FRACTION;
    records.push({cut:index+1,start:cuts[index],end:cuts[index+1],effect:frames.at(-1).state.motion,frames,
      max_changed_fraction_with_camera_frozen:maxDifference,non_camera_pixel_change:nonCameraMotion,timeline_and_caption_gate:timelinePass,
      status:timelinePass&&nonCameraMotion?'PASS':'REVIEW'});
    console.log(`CUT${String(index+1).padStart(2,'0')} ${records.at(-1).status}; changed ${(maxDifference*100).toFixed(2)}% with camera frozen`);
  }
  const heroFrames=records[7].frames.map(frame=>frame.hero);
  const arrowGeometry=heroFrames.every(Boolean)&&heroFrames[0].tip.y-heroFrames.at(-1).tip.y>300&&heroFrames.at(-1).tip.x-heroFrames[0].tip.x>500&&heroFrames.every((state,index)=>index===0||state.progress>=heroFrames[index-1].progress);
  const coreFiles=['index.html','scenes.js','hero-effects.js','spec-checklist.json'];
  const report={status:records.every(record=>record.status==='PASS')&&noCaptions.forbidden_nodes===0&&noCaptions.scene_nodes===9&&arrowGeometry&&!errors.length?'PASS':'REVIEW',
    method:'Three explicit times in each of nine cuts. Full-frame camera is frozen through __freezeCamera. Actual 1920x1080 canvas pixels are compared; DOM title animation is excluded. Repeat-seek pixels must match exactly.',
    scope:'Rendered source motion evidence. This is not final encoded-MP4 playback or subjective audio listening.',
    thresholds:{region:{left:0,top:0,width:ROI_WIDTH,height:H},sampling_stride:2,max_rgb_channel_change_exceeds:CHANNEL_THRESHOLD,min_changed_fraction:MIN_CHANGED_FRACTION,
      rationale:'At least 0.2 percent of sampled left-scene pixels must change by over 10 RGB levels while camera remains fixed; title or caption changes cannot satisfy the gate.'},
    source_files:coreFiles.map(name=>({file:name,sha256:digest(path.join(base,name))})),
    caption_dom:noCaptions,all_nine_timeline:records.every(record=>record.timeline_and_caption_gate),arrow_tip_rises_and_progresses:arrowGeometry,
    records,page_errors:errors,
    limits:['Pixel differences prove local effects remain without global camera movement; photographic object realism and composition require visual inspection.','Arrow geometry establishes an upward travelling tip; visual samples must also show the rendered head and trail.','User-visible copy and final narration are verified separately.']};
  writeFileSync(path.join(base,'motion-review.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify({status:report.status,report:'motion-review.json',nine_cuts:records.length,captions_absent:noCaptions.forbidden_nodes===0,arrow_rises:arrowGeometry},null,2));
  if(report.status!=='PASS')process.exitCode=1;
}finally{
  if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));
}
