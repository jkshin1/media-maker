import {spawnSync} from 'node:child_process';
import {existsSync,mkdirSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
const base=path.dirname(fileURLToPath(import.meta.url));
const out=path.resolve(process.env.OPENING_OUT||path.join(base,'../out/opening-v3'));mkdirSync(out,{recursive:true});
function run(exe,args){const r=spawnSync(exe,args,{cwd:base,stdio:'inherit'});if(r.error)throw r.error;if(r.status!==0)throw new Error(`${exe} exited ${r.status}`)}
if(!process.argv.includes('--reuse-video')){run(process.execPath,['motion-check.mjs']);run(process.execPath,['render.mjs','--stills']);run(process.execPath,['render.mjs']);}
run(process.env.PYTHON||'python3',['audio.py','--output',out]);
const audio=path.join(out,'audio.wav');if(!existsSync(audio))throw new Error('Missing audio.wav');
run('ffmpeg',['-y','-v','error','-i',path.join(out,'video_silent.mp4'),'-i',audio,'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','256k','-ar','48000','-t','46','-movflags','+faststart',path.join(out,'rd-ai-fast-track-opening-v3.mp4')]);
run(process.env.PYTHON||'python3',['verify.py']);
