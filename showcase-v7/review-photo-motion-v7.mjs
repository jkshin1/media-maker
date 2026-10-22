#!/usr/bin/env node
/** Independent native-only scope and geometry audit of local photo motion. */
import fs from 'node:fs';import path from 'node:path';import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';import {createHash} from 'node:crypto';
import {drawFrame as newFrame,W,H} from './stage.mjs';
import {drawFrame as oldFrame} from './baseline-v6/stage.mjs';
import {drawTask as newTask} from './task-scenes.js';
import {photoDisplacement,motionPhase,photoMotionContract} from './photo-motion.js';

const ROOT=path.dirname(fileURLToPath(import.meta.url)),OUT=path.resolve(ROOT,'../out/showcase-v7'),DIR=path.join(OUT,'photo-motion-review'),OLD=path.resolve(ROOT,'../showcase-v6');
const require=createRequire(import.meta.url);let native;
try{native=require('@napi-rs/canvas')}catch{native=require('/Users/jk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@napi-rs/canvas')}
const {createCanvas,loadImage,GlobalFonts}=native;
for(const f of ['NotoSansCJKkr-Regular.otf','NotoSansCJKkr-Bold.otf'])GlobalFonts.registerFromPath(path.join(ROOT,'fonts',f),'Noto');
const sha=b=>createHash('sha256').update(b).digest('hex'),fileSha=f=>sha(fs.readFileSync(f)),read=f=>JSON.parse(fs.readFileSync(path.join(ROOT,f))),rel=f=>path.relative(path.resolve(ROOT,'..'),f);
const spec=read('spec.json'),tl=read('timeline.json'),provenance=read('revision6-baseline-provenance.json'),sectionMap=new Map(spec.sections.map(s=>[s.id,s])),snapshot=new Map(provenance.files.map(r=>[r.file,r]));
const configFiles=['photo-motion-early.json','photo-motion-middle.json','photo-motion-late.json'];
const profiles=Object.assign({},...configFiles.map(f=>read(f).tasks));
fs.mkdirSync(DIR,{recursive:true});
const report={status:'RUNNING',scope:'Native RGBA, disabled-motion control, camera-frozen local deformation, source-pose and mesh geometry checks only. This is not encoded-video, audio, continuous-playback or naturalness acceptance.',source_hashes:{},checks:{},photo_motion_contract:photoMotionContract};
function gate(name,pass,detail={}){report.checks[name]={pass:!!pass,...detail};}
function record(file,base=ROOT){const f=path.join(base,file),exists=fs.existsSync(f);return {file,exists,sha256:exists?fileSha(f):null,bytes:exists?fs.statSync(f).size:null};}
const watched=['spec.json','timeline.json','stage.mjs','hero-scenes.js','task-scenes.js','task-visuals-early.js','task-visuals-late.js','photo-motion.js',...configFiles,'narration/ko.json'];
for(const f of watched)report.source_hashes[f]=fileSha(path.join(ROOT,f));
report.original_v6_source=provenance.files.map(r=>{const a=record(r.file,OLD);return {...a,expected_sha256:r.sha256,expected_bytes:r.bytes,unchanged:a.sha256===r.sha256&&a.bytes===r.bytes};});
gate('original_v6_all_273_source_files_unchanged',report.original_v6_source.length===273&&report.original_v6_source.every(r=>r.unchanged),{files:report.original_v6_source.length});
report.immutable_inputs=provenance.files.filter(r=>['spec.json','timeline.json'].includes(r.file)||['assets/','reference/','fonts/','narration/'].some(p=>r.file.startsWith(p))).map(r=>{const a=record(r.file);return {...a,expected_sha256:r.sha256,unchanged:a.sha256===r.sha256&&a.bytes===r.bytes};});
gate('spec_timeline_all_assets_fonts_narration_reference_unchanged',report.immutable_inputs.every(r=>r.unchanged),{files:report.immutable_inputs.length});
const modules=['stage.mjs','hero-scenes.js','task-scenes.js','task-visuals-early.js','task-visuals-late.js'];
report.baseline_modules=modules.map(f=>({file:f,sha256:fileSha(path.join(ROOT,'baseline-v6',f)),matches_provenance:fileSha(path.join(ROOT,'baseline-v6',f))===snapshot.get(f)?.sha256}));
gate('baseline_modules_match_v6',report.baseline_modules.every(r=>r.matches_provenance),{files:5});
gate('stage_hero_early_late_exactly_unchanged',modules.filter(f=>f!=='task-scenes.js').every(f=>fileSha(path.join(ROOT,f))===snapshot.get(f)?.sha256),{files:4});
function removeBackground(t){const a=t.indexOf('function photographicBackground('),b=t.indexOf('\nfunction copy(',a);if(a<0||b<0)throw new Error('Cannot locate background helper');return t.slice(0,a)+t.slice(b);}
const oldTaskCode=fs.readFileSync(path.join(ROOT,'baseline-v6/task-scenes.js'),'utf8'),newTaskCode=fs.readFileSync(path.join(ROOT,'task-scenes.js'),'utf8');
const expected=removeBackground(oldTaskCode).replace('photographicBackground(ctx,section,index,assets.freezeTaskBackground?0:t,d,photoAssets);','photographicBackground(ctx,section,index,t,d,photoAssets,index===0);').replace('export const taskDiversityContract={revision:6,','export const taskDiversityContract={revision:7,');
const actual=removeBackground(newTaskCode).replace("import {drawAnimatedPhoto} from './photo-motion.js';\n",'');
gate('task_scene_changes_limited_to_photo_helper_call_import_and_revision',expected===actual);
gate('profiles_cover_exactly_twelve_tasks',Object.keys(profiles).length===12&&spec.sections.filter(s=>s.type==='task').every(s=>profiles[s.id]),{profiles:Object.keys(profiles)});

const shared={images:{},backgrounds:{},videos:{},microscopy:{},spec,tasks:spec.sections.filter(s=>s.type==='task'),drawTitles:false,drawCaptions:false,photoMotionProfiles:profiles};
for(const f of new Set(spec.sections.map(s=>s.reference_image).filter(Boolean)))shared.images[f]=await loadImage(path.join(ROOT,f));
for(const s of spec.sections){shared.backgrounds[s.id]={};for(let i=0;i<s.cuts.length;i++){const f=s.backgrounds?.[i]||s.cuts[i].photo_crop||s.cuts[i].background||s.photo_crops?.[i];if(f&&fs.existsSync(path.join(ROOT,f))){shared.backgrounds[s.id][i]=await loadImage(path.join(ROOT,f));shared.images[f]=shared.backgrounds[s.id][i];}}}
for(const [id,f]of Object.entries(spec.microscopy||{}))shared.microscopy[id]=await loadImage(path.join(ROOT,f));
for(let i=1;i<=9;i++){const f=path.join(ROOT,`assets/opening/cut${String(i).padStart(2,'0')}.png`);if(fs.existsSync(f))shared.images[`opening${i}`]=await loadImage(f);}
const oldCanvas=createCanvas(W,H),newCanvas=createCanvas(W,H),offCanvas=createCanvas(W,H),frozenCanvas=createCanvas(W,H),stillCanvas=createCanvas(W,H);
const oldCtx=oldCanvas.getContext('2d'),newCtx=newCanvas.getContext('2d'),offCtx=offCanvas.getContext('2d'),frozenCtx=frozenCanvas.getContext('2d'),stillCtx=stillCanvas.getContext('2d');
const assetSet=extra=>({...shared,...extra,transitionCanvas:createCanvas(W,H)}),oldAssets=assetSet({}),newAssets=assetSet({}),offAssets=assetSet({photoMotion:false}),frozenAssets=assetSet({freezeTaskBackground:true}),stillAssets=assetSet({freezeTaskBackground:true,photoMotion:false});
const category=e=>sectionMap.get(e.section_id).type!=='task'?'hero':e.kind==='title'?'task_title':e.cut_index===0?'first_photo':'functional_body';
function difference(a,b){let body=0,header=0,x0=W,y0=H,x1=-1,y1=-1;for(let k=0;k<a.length;k+=4)if(a[k]!==b[k]||a[k+1]!==b[k+1]||a[k+2]!==b[k+2]||a[k+3]!==b[k+3]){const p=k/4,x=p%W,y=Math.floor(p/W);if(y<154)header++;else body++;x0=Math.min(x0,x);y0=Math.min(y0,y);x1=Math.max(x1,x);y1=Math.max(y1,y);}return {changed_body_pixels:body,changed_header_pixels:header,difference_bounds:body+header?[x0,y0,x1+1,y1+1]:null};}
function save(canvas,name,format='png'){const f=path.join(DIR,name+'.'+(format==='jpeg'?'jpg':format));fs.writeFileSync(f,canvas.encodeSync(format,...(format==='jpeg'?[90]:[])));return {file:rel(f),sha256:fileSha(f)};}
report.entries=[];
for(let i=0;i<tl.entries.length;i++){
 const e=tl.entries[i],d=e.end-e.start,kind=category(e),locals=kind==='first_photo'?[.25*d,.50*d,.75*d]:[Math.max(.55,.25*d),Math.max(.55,.60*d),d-.08];
 if(locals.some(t=>t<.5||t>=d)||new Set(locals).size!==3)throw new Error('Invalid post-dissolve times '+i);
 const samples=[];for(const local of locals){const t=e.start+local;oldFrame(oldCtx,t,tl,spec,oldAssets);newFrame(newCtx,t,tl,spec,newAssets);newFrame(offCtx,t,tl,spec,offAssets);const a=Buffer.from(oldCanvas.data()),b=Buffer.from(newCanvas.data()),c=Buffer.from(offCanvas.data());samples.push({time_seconds:t,local_seconds:local,old_rgba_sha256:sha(a),new_rgba_sha256:sha(b),disabled_rgba_sha256:sha(c),exact_rgba_equal:a.equals(b),toggle_off_exact_rgba_equal:a.equals(c),...(kind==='first_photo'?difference(a,b):{})});}
 report.entries.push({entry_index:i,section_id:e.section_id,cut_id:e.cut_id??null,cut_index:e.cut_index??null,kind,samples});
 if((i+1)%15===0)console.log(`Compared ${i+1}/${tl.entries.length} entries with motion-off control`);
}
report.counts=Object.fromEntries(['first_photo','functional_body','task_title','hero'].map(k=>[k,report.entries.filter(r=>r.kind===k).length]));
gate('expected_87_entries_and_categories',tl.entries.length===87&&report.counts.first_photo===12&&report.counts.functional_body===48&&report.counts.task_title===12&&report.counts.hero===15,{counts:report.counts});
for(const [kind,n]of [['functional_body',48],['task_title',12],['hero',15]])gate(kind+'_three_samples_exact_rgba',report.entries.filter(r=>r.kind===kind).every(r=>r.samples.every(s=>s.exact_rgba_equal)),{entries:n,samples:3*n});
gate('motion_disabled_all_87_entries_three_samples_exact_v6',report.entries.every(r=>r.samples.every(s=>s.toggle_off_exact_rgba_equal)),{entries:87,samples:261});
gate('all_twelve_first_photos_changed_without_header_changes',report.entries.filter(r=>r.kind==='first_photo').every(r=>r.samples.every(s=>!s.exact_rgba_equal&&s.changed_body_pixels>0&&s.changed_header_pixels===0)),{entries:12,samples:36});

// Geometry is evaluated independently of rasterization and camera transforms.
function geometry(profile,w,h){
 const phases=[.2,.5,.8],step=photoMotionContract.sourceGridPixels||25,xs=[],ys=[];for(let x=0;x<w;x+=step)xs.push(x);xs.push(w);for(let y=0;y<h;y+=step)ys.push(y);ys.push(h);
 let min=Infinity,max=-Infinity,areaMin=Infinity,areaMax=-Infinity,maxMove=0,pointCount=0,triangleCount=0,endpointMax=0,protectedMax=0;
 const disp=(x,y,u)=>photoDisplacement(x,y,w,h,profile,u,1),area=(a,b,c)=>(b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]);
 for(const u of phases){const moved=[];for(const y of ys)for(const x of xs){const v=disp(x,y,u),left=disp(x-.5,y,u),right=disp(x+.5,y,u),top=disp(x,y-.5,u),bottom=disp(x,y+.5,u),det=(1+right[0]-left[0])*(1+bottom[1]-top[1])-(bottom[0]-top[0])*(right[1]-left[1]);min=Math.min(min,det);max=Math.max(max,det);maxMove=Math.max(maxMove,Math.hypot(...v));moved.push([x+v[0],y+v[1]]);pointCount++;for(const end of [0,1])endpointMax=Math.max(endpointMax,Math.hypot(...disp(x,y,end)));}
  for(let j=0;j<ys.length-1;j++)for(let i=0;i<xs.length-1;i++){const n=j*xs.length+i,ids=[n,n+1,n+xs.length+1,n+xs.length],s=[[xs[i],ys[j]],[xs[i+1],ys[j]],[xs[i+1],ys[j+1]],[xs[i],ys[j+1]]];for(const q of [[0,1,2],[0,2,3]]){const ratio=area(...q.map(k=>moved[ids[k]]))/area(...q.map(k=>s[k]));areaMin=Math.min(areaMin,ratio);areaMax=Math.max(areaMax,ratio);triangleCount++;}}
  for(const p of profile.protected||[]){const [x,y,rw,rh]=p.rect;for(const fx of [.05,.5,.95])for(const fy of [.05,.5,.95])protectedMax=Math.max(protectedMax,Math.hypot(...disp((x+rw*fx)*w,(y+rh*fy)*h,u)));}
 }
 const handControls=profile.controls.filter(c=>/손|팔|펜|연필|검지|마커|hand|wrist|forearm/i.test(c.label)),uSet=[...new Set([...phases,...handControls.map(c=>((c.start??.08)+(c.end??.94))/2)])];
 let handMax=0,handAt=null;for(const c of handControls)for(const u of uSet)for(let j=-5;j<=5;j++)for(let i=-5;i<=5;i++){if(i*i+j*j>25)continue;const x=(c.center[0]+c.radius[0]*i/5)*w,y=(c.center[1]+c.radius[1]*j/5)*h,v=disp(x,y,u),m=Math.hypot(...v);if(m>handMax){handMax=m;handAt={x,y,phase:u,vector:v,control:c.label};}}
 return {jacobian:{min,max,phases,grid_step_source_pixels:step,grid_point_samples:pointCount,triangle_area_ratio_min:areaMin,triangle_area_ratio_max:areaMax,triangle_samples:triangleCount,max_displacement_source_px:maxMove},hand_roi:{max_displacement_source_px:handMax,at:handAt,method:'Source-coordinate sampling inside hand/forearm control ellipses at .2/.5/.8 and each control pulse peak; excludes camera.'},endpoint_max_displacement_source_px:endpointMax,protected_interior_max_displacement_source_px:protectedMax};
}
report.camera_frozen=[];const contact=[];
for(const e of tl.entries.filter(e=>category(e)==='first_photo')){
 const section=sectionMap.get(e.section_id),d=e.end-e.start,profile=profiles[e.section_id],photo=shared.backgrounds[e.section_id][0],w=photo.width,h=photo.height,samples=[];
 for(const phase of [.25,.5,.75]){const t=e.start+d*phase;newFrame(frozenCtx,t,tl,spec,frozenAssets);newFrame(stillCtx,t,tl,spec,stillAssets);const a=Buffer.from(frozenCanvas.data()),b=Buffer.from(stillCanvas.data());const proof=phase===.5?{enabled:save(frozenCanvas,e.section_id+'_frozen_motion50'),disabled:save(stillCanvas,e.section_id+'_frozen_original50')}:{enabled:save(frozenCanvas,e.section_id+'_frozen_motion'+Math.round(phase*100),'jpeg')};samples.push({phase,time_seconds:t,enabled_rgba_sha256:sha(a),disabled_rgba_sha256:sha(b),...difference(a,b),proof});if(phase===.5)contact.push({section_id:e.section_id,enabled:proof.enabled,disabled:proof.disabled});}
 const midpoint=e.start+d*.5;newFrame(frozenCtx,midpoint,tl,spec,frozenAssets);const a=sha(frozenCanvas.data());newFrame(frozenCtx,e.start+d*.31,tl,spec,frozenAssets);newFrame(frozenCtx,midpoint,tl,spec,frozenAssets);const deterministic=a===sha(frozenCanvas.data());
 const endpoints=[];for(const local of [0,d]){frozenCtx.clearRect(0,0,W,H);stillCtx.clearRect(0,0,W,H);newTask(frozenCtx,section,section.cuts[0],local,d,frozenAssets);newTask(stillCtx,section,section.cuts[0],local,d,stillAssets);endpoints.push({local_seconds:local,enabled_rgba_sha256:sha(frozenCanvas.data()),disabled_rgba_sha256:sha(stillCanvas.data()),exact_rgba_equal:Buffer.from(frozenCanvas.data()).equals(Buffer.from(stillCanvas.data())),all_control_phases_zero:profile.controls.every(c=>motionPhase(c,local,d)===0)});}
 report.camera_frozen.push({section_id:e.section_id,action_ko:profile.action_ko,source_dimensions:[w,h],samples,deterministic_out_of_order_rerender:deterministic,source_pose_endpoints:endpoints,...geometry(profile,w,h)});
 console.log('Checked camera-independent motion and geometry: '+e.section_id);
}
gate('camera_frozen_body_changes_at_three_samples_all_twelve',report.camera_frozen.every(r=>r.samples.every(s=>s.changed_body_pixels>0&&s.changed_header_pixels===0)),{entries:12,samples:36});
gate('photo_motion_explicit_time_deterministic',report.camera_frozen.every(r=>r.deterministic_out_of_order_rerender),{entries:12});
gate('motion_pulse_returns_to_original_source_pose',report.camera_frozen.every(r=>r.endpoint_max_displacement_source_px===0&&r.source_pose_endpoints.every(s=>s.exact_rgba_equal&&s.all_control_phases_zero)),{entries:12,endpoint_raster_comparisons:24});
gate('protected_region_interior_displacement_zero',report.camera_frozen.every(r=>r.protected_interior_max_displacement_source_px===0),{entries:12});
gate('mesh_jacobian_and_triangle_areas_bounded_positive',report.camera_frozen.every(r=>r.jacobian.min>.6&&r.jacobian.max<1.4&&r.jacobian.triangle_area_ratio_min>.6&&r.jacobian.triangle_area_ratio_max<1.4),{entries:12,phases:[.2,.5,.8],bounds:[.6,1.4]});
gate('actual_hand_roi_source_displacement_exceeds_1_5px',report.camera_frozen.every(r=>r.hand_roi.max_displacement_source_px>1.5),{entries:12,minimum_source_pixels:1.5,excludes_camera:true});
const sheet=createCanvas(1920,1920),sc=sheet.getContext('2d');sc.fillStyle='#080808';sc.fillRect(0,0,1920,1920);sc.fillStyle='#F2EEE7';sc.font='700 25px Noto';sc.fillText('Camera fixed | original pose / local motion | twelve first-photo cuts',20,35);
for(let i=0;i<contact.length;i++){const x=(i%2)*960,y=65+Math.floor(i/2)*307;sc.font='700 19px Noto';sc.fillStyle='#D4AF7C';sc.fillText(contact[i].section_id+'  original',x+12,y+22);sc.fillText('local motion',x+492,y+22);for(const [j,k]of ['disabled','enabled'].entries()){const im=await loadImage(path.resolve(ROOT,'..',contact[i][k].file));sc.drawImage(im,x+j*480,y+29,480,270);}}
report.native_proof_contact=save(sheet,'camera-frozen-twelve-contact','jpeg');
report.summary={unmodified_entries:75,non_photo_samples:225,non_photo_exact_match_samples:report.entries.filter(r=>r.kind!=='first_photo').flatMap(r=>r.samples).filter(s=>s.exact_rgba_equal).length,off_toggle_samples:261,off_toggle_exact_match_samples:report.entries.flatMap(r=>r.samples).filter(s=>s.toggle_off_exact_rgba_equal).length,first_photo_changed_samples:report.entries.filter(r=>r.kind==='first_photo').flatMap(r=>r.samples).filter(s=>!s.exact_rgba_equal).length,camera_frozen_motion_samples:36,source_photo_pose_endpoint_comparisons:24};
report.dissolve_scope_note='The existing 0.45-second transition is unchanged. An outgoing first-photo deformation can appear during the next cut dissolve. Equality comparisons use times at least 0.5 seconds after the new entry starts.';
gate('inputs_frozen_during_audit',Object.entries(report.source_hashes).every(([f,h])=>fileSha(path.join(ROOT,f))===h),{files:watched.length});
report.limitations=['Native sampled RGBA equality proves the listed frames only; it is not every-frame video comparison.','Nonzero body difference and source-space hand displacement prove local motion independent of camera, not anatomical realism or human acceptance.','The finite-difference Jacobian and actual triangle area ratios are sampled at the stated source grid and phases; they are not an exhaustive continuous-time bound.','No external generation, new voice, encoding or continuous playback was performed by this script.'];
report.status=Object.values(report.checks).every(c=>c.pass)?'PASS':'FAIL';report.generated_at=new Date().toISOString();report.qa_script_sha256=fileSha(fileURLToPath(import.meta.url));
const target=path.join(OUT,'photo-motion-validation.json');fs.writeFileSync(target,JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({status:report.status,checks_passed:Object.values(report.checks).filter(c=>c.pass).length,checks_total:Object.keys(report.checks).length,summary:report.summary,failed_checks:Object.entries(report.checks).filter(([,c])=>!c.pass).map(([k])=>k),report:target}));if(report.status!=='PASS')process.exitCode=1;
