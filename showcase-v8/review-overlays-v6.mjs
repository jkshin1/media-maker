#!/usr/bin/env node
/** Native RGBA audit of the twelve decorative first-photo overlays only. */
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {createHash} from 'node:crypto';
import {drawFrame as drawNew,W,H} from './stage.mjs';
import {drawFrame as drawOld} from './baseline-v5/stage.mjs';

const ROOT=path.dirname(fileURLToPath(import.meta.url));
const OUT=path.resolve(ROOT,'../out/showcase-v6');
const DIR=path.join(OUT,'overlay-review');
const OLD=path.resolve(ROOT,'../showcase-v5');
const require=createRequire(import.meta.url);let native;
try{native=require('@napi-rs/canvas')}catch{native=require('/Users/jk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@napi-rs/canvas')}
const {createCanvas,loadImage,GlobalFonts}=native;
for(const f of ['NotoSansCJKkr-Regular.otf','NotoSansCJKkr-Bold.otf'])GlobalFonts.registerFromPath(path.join(ROOT,'fonts',f),'Noto');
const json=f=>JSON.parse(fs.readFileSync(f));
const sha=b=>createHash('sha256').update(b).digest('hex');
const fileSha=f=>sha(fs.readFileSync(f));
const rel=f=>path.relative(path.resolve(ROOT,'..'),f);
const spec=json(path.join(ROOT,'spec.json')),tl=json(path.join(ROOT,'timeline.json'));
const provenance=json(path.join(ROOT,'revision5-baseline-provenance.json'));
const snapshot=new Map(provenance.files.map(f=>[f.file,f]));
const sectionMap=new Map(spec.sections.map(s=>[s.id,s]));
fs.mkdirSync(DIR,{recursive:true});
const checks={};const report={status:'RUNNING',scope:'Native RGBA comparison of 87 timeline entries at three post-dissolve times per entry; original v5 workspace/source locks; first-photo overlay before/after evidence. No encoded-video or audio playback acceptance.',checks};
function gate(name,pass,detail){checks[name]={pass:!!pass,...detail};}
function hashRecord(file,root=ROOT){const p=path.join(root,file);return {file,exists:fs.existsSync(p),sha256:fs.existsSync(p)?fileSha(p):null,bytes:fs.existsSync(p)?fs.statSync(p).size:null};}
const watched=['spec.json','timeline.json','stage.mjs','hero-scenes.js','task-scenes.js','task-visuals-early.js','task-visuals-late.js','narration/ko.json'];
const startHashes=watched.map(f=>hashRecord(f));
report.source_hashes=Object.fromEntries(startHashes.map(r=>[r.file,r.sha256]));

const originalRows=provenance.files.map(r=>{const actual=hashRecord(r.file,OLD);return {...actual,expected_sha256:r.sha256,expected_bytes:r.bytes,unchanged:actual.sha256===r.sha256&&actual.bytes===r.bytes};});
report.original_v5_workspace={source:rel(OLD),expected_files:259,files:originalRows};
gate('original_v5_all_259_source_files_unchanged',originalRows.length===259&&originalRows.every(r=>r.unchanged),{count:originalRows.length});
const immutable=provenance.files.filter(r=>['spec.json','timeline.json','narration/ko.json'].includes(r.file)||['assets/','reference/','fonts/','narration/'].some(p=>r.file.startsWith(p)));
report.immutable_inputs=immutable.map(r=>{const actual=hashRecord(r.file);return {...actual,expected_sha256:r.sha256,unchanged:actual.sha256===r.sha256&&actual.bytes===r.bytes};});
gate('spec_timeline_narration_assets_fonts_reference_unchanged',report.immutable_inputs.every(r=>r.unchanged),{count:immutable.length});
report.baseline_code=['stage.mjs','hero-scenes.js','task-scenes.js','task-visuals-early.js','task-visuals-late.js'].map(file=>{const old=path.join(ROOT,'baseline-v5',file);return {file,sha256:fileSha(old),expected_sha256:snapshot.get(file)?.sha256,matches_v5:fileSha(old)===snapshot.get(file)?.sha256};});
gate('baseline_render_modules_match_original',report.baseline_code.every(r=>r.matches_v5),{count:5});
gate('stage_and_hero_files_exactly_unchanged',['stage.mjs','hero-scenes.js'].every(f=>fileSha(path.join(ROOT,f))===fileSha(path.join(ROOT,'baseline-v5',f))),{count:2});
const oldDispatch=fs.readFileSync(path.join(ROOT,'baseline-v5/task-scenes.js'),'utf8'),newDispatch=fs.readFileSync(path.join(ROOT,'task-scenes.js'),'utf8');
gate('task_dispatch_code_unchanged_except_contract_revision',oldDispatch.replace('export const taskDiversityContract={revision:5,','export const taskDiversityContract={revision:6,')===newDispatch,{allowed_metadata_change:'taskDiversityContract.revision: 5 to 6 only'});

// Remove only the old named decorative helper, dispatch branch and plan metadata.
// Every other byte of both implementation modules must still match.
function removeFunction(text,name){const from=text.indexOf(`function ${name}(`);if(from<0)throw new Error('Missing old helper '+name);const end=text.indexOf('\n}\n',from);if(end<0)throw new Error('Missing helper end '+name);return text.slice(0,from)+text.slice(end+3);}
const oldEarly=fs.readFileSync(path.join(ROOT,'baseline-v5/task-visuals-early.js'),'utf8');
const newEarly=fs.readFileSync(path.join(ROOT,'task-visuals-early.js'),'utf8');
const oldLate=fs.readFileSync(path.join(ROOT,'baseline-v5/task-visuals-late.js'),'utf8');
const newLate=fs.readFileSync(path.join(ROOT,'task-visuals-late.js'),'utf8');
const stripPlan=t=>t.split('\n').filter(l=>!l.startsWith(' profile,sectionId:sourceInfo')&&!l.startsWith('export const lateVisualPlan=')).join('\n').replace(/\n\s*\n/g,'\n');
const earlyExpected=removeFunction(oldEarly,'before').replace('if(index===0)before(c,p,u,k);else drawByKey[p.key]','if(index>0)drawByKey[p.key]');
const lateExpected=removeFunction(oldLate,'manualPhoto').replace('if(index===0)manualPhoto(c,p,u,k);\n else{','if(index>0){');
gate('early_module_only_helper_dispatch_and_plan_metadata_changed',stripPlan(earlyExpected)===stripPlan(newEarly),{removed_helper:'before'});
gate('late_module_only_helper_dispatch_and_plan_metadata_changed',stripPlan(lateExpected)===stripPlan(newLate),{removed_helper:'manualPhoto'});
const {earlyVisualPlan}=await import('./task-visuals-early.js');
const {lateVisualPlan}=await import('./task-visuals-late.js');
const {earlyVisualPlan:oldEarlyPlan}=await import('./baseline-v5/task-visuals-early.js');
const {lateVisualPlan:oldLatePlan}=await import('./baseline-v5/task-visuals-late.js');
const plans=[...earlyVisualPlan,...lateVisualPlan],oldPlans=[...oldEarlyPlan,...oldLatePlan];
gate('after_cut_plan_metadata_unchanged',plans.filter(p=>p.cutIndex>0).every(p=>JSON.stringify(p)===JSON.stringify(oldPlans.find(o=>o.sectionId===p.sectionId&&o.cutIndex===p.cutIndex))),{count:48});
gate('first_photo_plan_metadata_photos_only',plans.filter(p=>p.cutIndex===0).length===12&&plans.filter(p=>p.cutIndex===0).every(p=>p.decorativeOverlay===false&&p.motionFocus===null),{count:12});

const shared={images:{},backgrounds:{},videos:{},microscopy:{},spec,tasks:spec.sections.filter(s=>s.type==='task'),drawTitles:false,drawCaptions:false};
for(const f of new Set(spec.sections.map(s=>s.reference_image).filter(Boolean)))shared.images[f]=await loadImage(path.join(ROOT,f));
for(const s of spec.sections){shared.backgrounds[s.id]={};for(let i=0;i<s.cuts.length;i++){const f=s.backgrounds?.[i]||s.cuts[i].photo_crop||s.cuts[i].background||s.photo_crops?.[i];if(f&&fs.existsSync(path.join(ROOT,f))){shared.backgrounds[s.id][i]=await loadImage(path.join(ROOT,f));shared.images[f]=shared.backgrounds[s.id][i];}}}
for(const [id,f]of Object.entries(spec.microscopy||{}))if(fs.existsSync(path.join(ROOT,f)))shared.microscopy[id]=await loadImage(path.join(ROOT,f));
for(let i=1;i<=9;i++){const f=path.join(ROOT,`assets/opening/cut${String(i).padStart(2,'0')}.png`);if(fs.existsSync(f))shared.images[`opening${i}`]=await loadImage(f);}
const oldAssets={...shared,transitionCanvas:createCanvas(W,H)},newAssets={...shared,transitionCanvas:createCanvas(W,H)};
const oldCanvas=createCanvas(W,H),newCanvas=createCanvas(W,H),oldCtx=oldCanvas.getContext('2d'),newCtx=newCanvas.getContext('2d');
const category=e=>sectionMap.get(e.section_id).type!=='task'?'hero':e.kind==='title'?'task_title':e.cut_index===0?'first_photo':'functional_body';
function compare(t){drawOld(oldCtx,t,tl,spec,oldAssets);drawNew(newCtx,t,tl,spec,newAssets);const a=Buffer.from(oldCanvas.data()),b=Buffer.from(newCanvas.data());return {time_seconds:t,old_rgba_sha256:sha(a),new_rgba_sha256:sha(b),exact_rgba_equal:a.equals(b)};}
function difference(){const a=oldCanvas.data(),b=newCanvas.data();let n=0,x0=W,y0=H,x1=-1,y1=-1,header=0;for(let p=0;p<a.length;p+=4)if(a[p]!==b[p]||a[p+1]!==b[p+1]||a[p+2]!==b[p+2]||a[p+3]!==b[p+3]){const pixel=p/4,x=pixel%W,y=Math.floor(pixel/W);n++;if(y<154)header++;x0=Math.min(x0,x);x1=Math.max(x1,x);y0=Math.min(y0,y);y1=Math.max(y1,y);}return {changed_pixels:n,changed_header_pixels:header,difference_bounds:n?[x0,y0,x1+1,y1+1]:null};}
function savePair(stem){const oldFile=path.join(DIR,stem+'_v5.jpg'),newFile=path.join(DIR,stem+'_v6.jpg');fs.writeFileSync(oldFile,oldCanvas.encodeSync('jpeg',90));fs.writeFileSync(newFile,newCanvas.encodeSync('jpeg',90));return {old:rel(oldFile),new:rel(newFile),old_sha256:fileSha(oldFile),new_sha256:fileSha(newFile)};}
const rows=[],contact=[];
for(let index=0;index<tl.entries.length;index++){
 const e=tl.entries[index],d=e.end-e.start,kind=category(e);
 const times=[Math.max(.55,d*.25),Math.max(.55,d*.60),d-.08].map(t=>e.start+t);
 if(new Set(times).size!==3||times.some(t=>t>=e.end||t-e.start<.5))throw new Error('Invalid sample times '+index);
 const samples=[];
 for(let j=0;j<times.length;j++){const row=compare(times[j]);if(kind==='first_photo'){Object.assign(row,difference(),savePair(`${e.section_id}_photo_${j+1}`));if(j===1)contact.push({section:e.section_id,title:sectionMap.get(e.section_id).title,old:row.old,new:row.new});}samples.push(row);}
 rows.push({entry_index:index,section_id:e.section_id,cut_id:e.cut_id??null,cut_index:e.cut_index??null,kind,start_seconds:e.start,end_seconds:e.end,samples});
 if((index+1)%15===0)console.log(`Compared ${index+1}/${tl.entries.length} entries`);
}
report.entries=rows;report.counts=Object.fromEntries(['first_photo','functional_body','task_title','hero'].map(k=>[k,rows.filter(r=>r.kind===k).length]));
gate('timeline_has_87_entries_and_expected_categories',tl.entries.length===87&&report.counts.first_photo===12&&report.counts.functional_body===48&&report.counts.task_title===12&&report.counts.hero===15,{counts:report.counts});
for(const [k,n]of [['functional_body',48],['task_title',12],['hero',15]]){const selected=rows.filter(r=>r.kind===k);gate(k+'_all_three_samples_exact_rgba',selected.length===n&&selected.every(r=>r.samples.every(s=>s.exact_rgba_equal)),{entries:n,samples:n*3});}
const photos=rows.filter(r=>r.kind==='first_photo');
gate('all_twelve_first_photos_changed_at_all_three_samples',photos.every(r=>r.samples.every(s=>!s.exact_rgba_equal&&s.changed_pixels>0)),{entries:12,samples:36});
gate('photo_changes_exclude_persistent_header_and_stay_in_body',photos.every(r=>r.samples.every(s=>s.changed_header_pixels===0&&s.difference_bounds[0]>=80&&s.difference_bounds[1]>=190&&s.difference_bounds[2]<=1840&&s.difference_bounds[3]<=1020)),{samples:36});
// The old first-photo component remains in its outgoing .45 s dissolve only.
report.following_cut_dissolve_samples=tl.entries.filter(e=>category(e)==='functional_body'&&e.cut_index===1).map(e=>({section_id:e.section_id,allowed_reason:'Outgoing first-photo overlay removal naturally propagates into the existing 0.45-second dissolve; functional scene code is unchanged.',...compare(e.start+.20)}));
report.dissolve_scope_note='Exact-match samples start at least 0.5 seconds into each entry. A changed outgoing first-photo overlay may change the next cut during its existing 0.45-second dissolve; this is within scope, not a new functional-scene change.';
const exact122=compare(122);const old122=path.join(DIR,'exact_122_000_v5.png'),new122=path.join(DIR,'exact_122_000_v6.png');fs.writeFileSync(old122,oldCanvas.encodeSync('png'));fs.writeFileSync(new122,newCanvas.encodeSync('png'));
report.exact_122_seconds={...exact122,...difference(),old:rel(old122),new:rel(new122),old_png_sha256:fileSha(old122),new_png_sha256:fileSha(new122)};
gate('user_example_exact_122_seconds_is_changed_first_photo',tl.entries.some(e=>e.section_id==='task8'&&e.cut_index===0&&122>=e.start&&122<e.end)&&!exact122.exact_rgba_equal&&report.exact_122_seconds.changed_header_pixels===0,{time:122});

const sheet=createCanvas(1920,1920),sc=sheet.getContext('2d');sc.fillStyle='#080808';sc.fillRect(0,0,1920,1920);sc.fillStyle='#F2EEE7';sc.font='700 27px Noto';sc.fillText('12 first-photo cuts | v5 before / v6 after | midpoint samples',24,37);
for(let i=0;i<contact.length;i++){const row=Math.floor(i/2),col=i%2,x=col*960,y=65+row*307;sc.fillStyle='#D4AF7C';sc.font='700 19px Noto';sc.fillText(contact[i].section+'  v5 before',x+12,y+22);sc.fillText('v6 after',x+492,y+22);for(const [j,key]of ['old','new'].entries()){const img=await loadImage(path.resolve(ROOT,'..',contact[i][key]));sc.drawImage(img,x+j*480,y+29,480,270);}}
const sheetFile=path.join(DIR,'first-photo-before-after-contact.jpg');fs.writeFileSync(sheetFile,sheet.encodeSync('jpeg',92));report.contact_sheet={file:rel(sheetFile),sha256:fileSha(sheetFile),pairs:12,sample:'middle of each reviewed first-photo entry',layout:'two task pairs per row; each task v5 left, v6 right'};
gate('source_inputs_remained_frozen_during_audit',startHashes.every(r=>fileSha(path.join(ROOT,r.file))===r.sha256),{count:startHashes.length});
report.limitations=['RGBA checks prove equality only at the stated 225 unchanged-entry samples and changed-photo sample points; they do not claim every rendered frame is equal.','Before/after images and contact sheet are native canvas evidence, not decoded video frames.','No narration, BGM, encoded media or continuous playback was generated or reviewed by this script.','Static module normalization checks limit implementation changes to removed first-photo helpers/dispatch plus first-photo plan metadata.'];
report.status=Object.values(checks).every(c=>c.pass)?'PASS':'FAIL';report.generated_at=new Date().toISOString();report.qa_script_sha256=fileSha(fileURLToPath(import.meta.url));
const output=path.join(OUT,'overlay-removal-validation.json');fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({status:report.status,checks_passed:Object.values(checks).filter(c=>c.pass).length,checks_total:Object.keys(checks).length,counts:report.counts,unchanged_samples:225,changed_photo_samples:36,report:output,failed_checks:Object.keys(checks).filter(k=>!checks[k].pass)}));if(report.status!=='PASS')process.exitCode=1;
