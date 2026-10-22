#!/usr/bin/env node
import puppeteer from 'puppeteer-core';
import {spawn,spawnSync} from 'node:child_process';
import {once} from 'node:events';
import {createHash} from 'node:crypto';
import {createReadStream,existsSync,mkdirSync,readFileSync,readdirSync,renameSync,statSync,writeFileSync} from 'node:fs';
import {createServer} from 'node:http';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const base=path.dirname(fileURLToPath(import.meta.url));
const out=path.resolve(process.env.OPENING_OUT||path.join(base,'../out/opening-v3'));
const config=JSON.parse(readFileSync(path.join(base,'spec-checklist.json')));
const {width,height,fps,duration}=config.output;
const args=process.argv.slice(2),stills=args.includes('--stills');
if(args.includes('--help')){console.log('node render.mjs [--stills] [--times 1.5,4,8] [--serve]\nCHROME_PATH: Chrome/Chromium executable. OPENING_OUT: output directory.');process.exit(0)}
for(let i=0;i<args.length;i++){if(args[i]==='--times'){i++;continue}if(!['--stills','--serve'].includes(args[i]))throw new Error('Unknown argument '+args[i])}
mkdirSync(out,{recursive:true});
const digest=f=>createHash('sha256').update(readFileSync(f)).digest('hex');
function inventory(dir){return readdirSync(dir,{withFileTypes:true}).filter(e=>!['node_modules','__pycache__'].includes(e.name)).flatMap(e=>{const f=path.join(dir,e.name);if(e.isDirectory())return inventory(f);return[f]})}
const inputs=inventory(base).filter(f=>/\.(html|js|json|png|otf|woff2)$/.test(f)&&!path.relative(base,f).split(path.sep).includes('narration')).map(f=>({file:path.relative(base,f),sha256:digest(f)}));
const mime={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.json':'application/json','.png':'image/png','.jpg':'image/jpeg','.otf':'font/otf','.woff2':'font/woff2','.wav':'audio/wav'};
const server=createServer((req,res)=>{
 try{const url=decodeURIComponent(new URL(req.url,'http://127.0.0.1').pathname);const f=path.resolve(base,'.'+(url==='/'?'/index.html':url));if(path.relative(base,f).startsWith('..')||!statSync(f).isFile()){res.writeHead(404).end();return}
 res.writeHead(200,{'Content-Type':mime[path.extname(f)]||'application/octet-stream'});createReadStream(f).pipe(res)}catch{res.writeHead(404).end()}
});
await new Promise((resolve,reject)=>{server.once('error',reject);server.listen(0,'127.0.0.1',resolve)});
const url=`http://127.0.0.1:${server.address().port}/index.html`;
if(args.includes('--serve')){console.log('Preview: '+url);console.log('Ctrl+C to stop');process.on('SIGINT',()=>server.close(()=>process.exit(0)))}else{
 let browser,encoder,encoderFailure;
 try{
 const candidates=[process.env.CHROME_PATH,'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','/usr/bin/google-chrome','/usr/bin/chromium','/usr/bin/chromium-browser','C:/Program Files/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Google/Chrome/Application/chrome.exe'].filter(Boolean);
 const chrome=candidates.find(existsSync);if(!chrome)throw new Error('Chrome/Chromium not found. Set CHROME_PATH to your executable.');
 browser=await puppeteer.launch({executablePath:chrome,headless:true,args:['--hide-scrollbars','--force-device-scale-factor=1','--force-color-profile=srgb']});
 const page=await browser.newPage();await page.setViewport({width,height,deviceScaleFactor:1});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(url+'?render=1',{waitUntil:'load',timeout:60000});await page.evaluate(async()=>{await window.__ready;await document.fonts.ready});
 if(errors.length)throw new Error(errors.join('; '));
 async function seek(t){await page.evaluate(time=>window.__seek(time),t);if(errors.length)throw new Error(errors.join('; '))}
 if(stills){
 const custom=args.indexOf('--times');const times=custom>=0?args[custom+1].split(',').map(Number):[0,1.5,3.1,4.7,7.1,9.5,12.1,14.5,17.1,17.8,19.5,22.1,23.3,25,28.1,31.5,35.1,38.5,42.1,44,45.9];
 const dir=path.join(out,'stills');mkdirSync(dir,{recursive:true});const records=[];
 for(const time of times){if(!Number.isFinite(time)||time<0||time>=duration)throw new Error('Invalid still time');await seek(time);const f=path.join(dir,`still_${time.toFixed(2)}.png`);await page.screenshot({path:f,type:'png'});
 const layout=await page.evaluate(()=>{
 const issues=[],texts=[];for(const el of document.querySelectorAll('.scene,#caption')){if(getComputedStyle(el).display==='none'||Number(getComputedStyle(el).opacity)<.05)continue;
 const walk=document.createTreeWalker(el,NodeFilter.SHOW_TEXT);let n;while(n=walk.nextNode()){if(!n.textContent.trim())continue;const p=n.parentElement;if(getComputedStyle(p).opacity==='0')continue;const range=document.createRange();range.selectNodeContents(n);for(const r of range.getClientRects()){if(!r.width)continue;texts.push({text:n.textContent.trim(),left:r.left,top:r.top,right:r.right,bottom:r.bottom});if(r.left<78||r.right>1842||r.top<75||r.bottom>1005)issues.push({text:n.textContent.trim(),left:r.left,top:r.top,right:r.right,bottom:r.bottom})}}
 }return{state:window.__state,texts,issues};});records.push({time,...layout});console.log('Still '+time+' cut'+layout.state.cut+' issues='+layout.issues.length)}
 const count=records.reduce((n,r)=>n+r.issues.length,0);writeFileSync(path.join(out,'layout-validation.json'),JSON.stringify({status:count?'REVIEW':'PASS',issue_count:count,safe_margins:{left:78,right:78,top:75,bottom:75},records},null,2)+'\n');
 if(count)throw new Error(`Layout has ${count} text bounds issues; inspect layout-validation.json`);
 }else{
 const partial=path.join(out,'video_silent.partial.mp4');const target=path.join(out,'video_silent.mp4');
 encoder=spawn('ffmpeg',['-y','-v','error','-f','image2pipe','-framerate',String(fps),'-c:v','mjpeg','-i','-','-vf','scale=out_color_matrix=bt709:out_range=tv,format=yuv420p','-c:v','libx264','-preset','fast','-crf','17','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-movflags','+faststart',partial],{stdio:['pipe','inherit','inherit']});
 const done=new Promise((resolve,reject)=>{encoder.once('error',reject);encoder.once('close',code=>code===0?resolve():reject(new Error('ffmpeg exit '+code)))});done.catch(e=>{encoderFailure=e});encoder.stdin.on('error',e=>encoderFailure=e);
 const start=Date.now(),frames=fps*duration;
 for(let frame=0;frame<frames;frame++){if(encoderFailure)throw encoderFailure;await seek(frame/fps);const jpg=await page.screenshot({type:'jpeg',quality:95,optimizeForSpeed:true});if(!encoder.stdin.write(jpg))await Promise.race([once(encoder.stdin,'drain'),done.then(()=>{throw new Error('Encoder closed early')})]);if(frame%90===0)console.log(`Frame ${frame}/${frames}; elapsed ${((Date.now()-start)/1000).toFixed(1)}s`)}
 encoder.stdin.end();await done;
 const probe=spawnSync('ffprobe',['-v','error','-show_streams','-show_format','-of','json',partial],{encoding:'utf8'});if(probe.status!==0)throw new Error(probe.stderr);const meta=JSON.parse(probe.stdout),v=meta.streams.find(s=>s.codec_type==='video');
 if(v.width!==width||v.height!==height||v.r_frame_rate!==fps+'/1'||Number(v.nb_frames)!==frames||Math.abs(Number(meta.format.duration)-duration)>1/fps)throw new Error('Render dimensions/timing failed');
 for(const item of inputs)if(digest(path.join(base,item.file))!==item.sha256)throw new Error('Input mutated during render: '+item.file);
 renameSync(partial,target);writeFileSync(path.join(out,'render-validation.json'),JSON.stringify({status:'PASS',width,height,fps,duration,frames,elapsed_seconds:(Date.now()-start)/1000,sha256:digest(target),inputs},null,2)+'\n');console.log('Rendered '+target);
 }
 }finally{if(encoder&&encoder.exitCode===null)encoder.kill('SIGTERM');if(browser)await browser.close();await new Promise(resolve=>server.close(resolve))}
}
