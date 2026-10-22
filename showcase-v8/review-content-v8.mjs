#!/usr/bin/env node
// Independent native-draw content audit. No speech service or production writes.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {createHash} from 'node:crypto';
import {drawFrame,W,H} from './stage.mjs';
import {drawFrame as baselineDrawFrame} from './baseline-v6/stage.mjs';
import {getCameraState,photoCameraContract} from './photo-camera.js';
const HERE=path.dirname(fileURLToPath(import.meta.url)),OUT=path.resolve(HERE,'../out/showcase-v8'),DIR=path.join(OUT,'content-review');
const read=f=>JSON.parse(fs.readFileSync(path.join(HERE,f),'utf8'));
const hash=b=>createHash('sha256').update(b).digest('hex');
const fileHash=f=>hash(fs.readFileSync(path.join(HERE,f)));
const norm=s=>String(s??'').normalize('NFKC').replace(/[\s·ㆍ|,.:;~→≠\-–—/%()]/g,'').toLowerCase();
const brief=read('reference/user-revision8-brief.json'),spec=read('spec.json'),content=read('revision8-content.json');
const timelineFile=process.env.TIMELINE_FILE||'timeline-preview.json',timeline=read(timelineFile),baselineSpec=read('baseline-v6/spec.json');
const sourceFiles=['review-content-v8.mjs','reference/user-revision8-brief.json','revision8-content.json','spec.json',timelineFile,'narration/ko.json','stage.mjs','hero-scenes.js','task-scenes.js','task-visuals-early.js','task-visuals-late.js','photo-camera.js','photo-camera-profiles.json','render.mjs','revision6-baseline-provenance.json','baseline-v6/spec.json','baseline-v6/stage.mjs','baseline-v6/hero-scenes.js','fonts/NotoSansCJKkr-Regular.otf','fonts/NotoSansCJKkr-Bold.otf'];
const sourceHashes=Object.fromEntries(sourceFiles.map(f=>[f,fileHash(f)]));
const require=createRequire(import.meta.url);let native;try{native=require('@napi-rs/canvas')}catch{native=require('/Users/jk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@napi-rs/canvas')}
const {createCanvas,loadImage,GlobalFonts}=native;for(const f of ['Regular','Bold'])GlobalFonts.registerFromPath(path.join(HERE,`fonts/NotoSansCJKkr-${f}.otf`),'Noto');
fs.mkdirSync(DIR,{recursive:true});
const assets={photoCameraProfiles:read('photo-camera-profiles.json').tasks,images:{},backgrounds:{},videos:{},microscopy:{},transitionCanvas:createCanvas(W,H),spec,tasks:spec.sections.filter(s=>s.type==='task'),drawTitles:false,drawCaptions:false};
const imageFiles=new Set(spec.sections.map(s=>s.reference_image).filter(Boolean));
for(const s of spec.sections)for(let i=0;i<s.cuts.length;i++){const f=s.backgrounds?.[i]||s.cuts[i].photo_crop||s.cuts[i].background||s.photo_crops?.[i];if(f)imageFiles.add(f)}
for(const f of Object.values(spec.microscopy||{}))imageFiles.add(f);
for(let i=1;i<=9;i++)imageFiles.add(`assets/opening/cut${String(i).padStart(2,'0')}.png`);
for(const f of imageFiles)if(fs.existsSync(path.join(HERE,f))){assets.images[f]=await loadImage(path.join(HERE,f));sourceHashes[f]=fileHash(f)}
for(const s of spec.sections){assets.backgrounds[s.id]={};for(let i=0;i<s.cuts.length;i++){const f=s.backgrounds?.[i]||s.cuts[i].photo_crop||s.cuts[i].background||s.photo_crops?.[i];if(f&&assets.images[f])assets.backgrounds[s.id][i]=assets.images[f]}}
for(const [id,f]of Object.entries(spec.microscopy||{}))if(assets.images[f])assets.microscopy[id]=assets.images[f];
for(let i=1;i<=9;i++)assets.images[`opening${i}`]=assets.images[`assets/opening/cut${String(i).padStart(2,'0')}.png`];
const canvas=createCanvas(W,H),ctx=canvas.getContext('2d');let captured=[];
const orig=ctx.fillText.bind(ctx);
ctx.fillText=function(value,x,y,maxWidth){
 const s=String(value),alpha=ctx.globalAlpha,font=ctx.font,m=ctx.measureText(s),mat=ctx.getTransform(),size=Number((font.match(/([\d.]+)px/)||[])[1]||0);
 let left=x,right=x+m.width,top,bottom;if(ctx.textAlign==='center'){left-=m.width/2;right-=m.width/2}else if(['right','end'].includes(ctx.textAlign)){left-=m.width;right-=m.width}
 if(ctx.textBaseline==='top'){top=y;bottom=y+size*1.25}else if(ctx.textBaseline==='middle'){top=y-size*.6;bottom=y+size*.65}else{top=y-(m.actualBoundingBoxAscent||size);bottom=y+(m.actualBoundingBoxDescent||size*.2)}
 const points=[[left,top],[right,top],[left,bottom],[right,bottom]].map(([a,b])=>[mat.a*a+mat.c*b+mat.e,mat.b*a+mat.d*b+mat.f]);
 const bounds={left:Math.min(...points.map(p=>p[0])),right:Math.max(...points.map(p=>p[0])),top:Math.min(...points.map(p=>p[1])),bottom:Math.max(...points.map(p=>p[1]))};
 if(s.trim()&&alpha>.05)captured.push({text:s,font,alpha,x,y,bounds,font_size:size,transform:[mat.a,mat.b,mat.c,mat.d,mat.e,mat.f],scope:bounds.top<154?'header_or_title':'body'});
 return maxWidth===undefined?orig(value,x,y):orig(value,x,y,maxWidth);
};
const records=[],checks={},issues=[],taskEntries=timeline.entries.filter(e=>brief.order.includes(e.section_id));
const add=(id,pass,details)=>{checks[id]={pass:!!pass,details};if(!pass)issues.push({check:id,...(typeof details==='object'?details:{details})})};
const phases=[.62,.90];
for(const e of taskEntries){
 const s=spec.sections.find(s=>s.id===e.section_id),d=e.end-e.start,cut=e.kind==='title'?null:s.cuts[e.cut_index],samples=[];
 for(const fraction of phases){captured=[];const t=e.start+d*fraction,state=drawFrame(ctx,t,timeline,spec,assets);const png=canvas.encodeSync('png');
  const name=`${e.section_id}_${e.kind==='title'?'title':`cut${e.cut_index+1}`}_${Math.round(fraction*100)}.png`;if(fraction===.62)fs.writeFileSync(path.join(DIR,name),png);
  samples.push({fraction,time_seconds:t,native_rgba_sha256:hash(canvas.data()),native_png_sha256:hash(png),native_file:fraction===.62?path.relative(OUT,path.join(DIR,name)):null,drawn_text:captured.map(x=>({...x})),captions:state.captions,header:state.task_header});
 }
 records.push({section_id:s.id,kind:e.kind,cut_id:cut?.id||null,cut_index:e.cut_index,title:cut?.title||s.title,narration_draft:cut?.narration||'',spoken_draft:cut?.spoken_text||'',support_lines_metadata_only:cut?.support_lines||[],start:e.start,end:e.end,samples});
}
add('exact_task_order',JSON.stringify(spec.sections.filter(s=>s.type==='task').map(s=>s.id))===JSON.stringify(brief.order),{expected:brief.order,actual:spec.sections.filter(s=>s.type==='task').map(s=>s.id)});
add('twelve_titles_sixty_body_cuts',records.length===72&&records.filter(x=>x.kind==='title').length===12&&records.filter(x=>x.kind==='cut').length===60,{titles:records.filter(x=>x.kind==='title').length,body_cuts:records.filter(x=>x.kind==='cut').length,samples:records.length*phases.length});
add('titles_teams_owners_match_authoritative_brief',brief.order.every(id=>{const a=brief.tasks[id],s=spec.sections.find(x=>x.id===id);return['title','team','owner'].every(k=>a[k]===s[k])}),{tasks:12});
add('actual_headers_show_latest_identity',records.every(r=>r.samples.every(p=>{const b=brief.tasks[r.section_id],h=p.header;return h&&h.task_title===b.title&&h.team===b.team&&h.owner===b.owner&&norm(h.records.filter(x=>x.role==='task_title').map(x=>x.text).join(''))===norm(b.title)&&h.records.some(x=>x.role==='owner'&&x.text===`${b.team} · ${b.owner}`)})),{records:72,samples:144});
add('no_narration_caption_drawn',spec.presentation_overrides?.narration_captions===false&&records.every(r=>r.samples.every(p=>p.captions.length===0)),{native_samples:144});
add('draft_script_merged_without_word_change',brief.order.every(id=>{const s=spec.sections.find(s=>s.id===id);return s.cuts.length===5&&s.cuts.every((c,i)=>c.narration===content.tasks[id].cuts[i].narration&&c.spoken_text===content.tasks[id].cuts[i].spoken_text)}),{note:'Draft text only; does not establish actual spoken coverage.'});
const voiceConfig=read('narration/ko.json'),taskBlocks=voiceConfig.blocks.filter(b=>brief.order.includes(b.section_id));
add('draft_voice_config_has_exact_task_order_and_script',JSON.stringify(taskBlocks.map(b=>b.section_id))===JSON.stringify(brief.order)&&taskBlocks.every(b=>b.cuts.length===5&&b.cuts.every((c,i)=>c.spoken_text===content.tasks[b.section_id].cuts[i].spoken_text&&c.text===content.tasks[b.section_id].cuts[i].narration)),{generation_mode:voiceConfig.generation_mode,voice_name:voiceConfig.voice_name,narration_status:'Draft configuration only; no actual voice validation.'});
const heroEquality=['opening','ending'].map(id=>({section_id:id,spec_deep_equal:JSON.stringify(spec.sections.find(s=>s.id===id))===JSON.stringify(baselineSpec.sections.find(s=>s.id===id))}));
add('opening_ending_source_sections_and_renderer_unchanged',heroEquality.every(x=>x.spec_deep_equal)&&fileHash('hero-scenes.js')===fileHash('baseline-v6/hero-scenes.js'),heroEquality);
const baselineAssets=read('revision6-baseline-provenance.json').files.filter(x=>/^(assets|fonts|reference)\//.test(x.file));
const assetIdentity=baselineAssets.map(x=>({file:x.file,baseline_sha256:x.sha256,current_sha256:fs.existsSync(path.join(HERE,x.file))?fileHash(x.file):null}));
add('original_reference_photos_assets_and_fonts_unchanged',assetIdentity.every(x=>x.current_sha256===x.baseline_sha256),{files:assetIdentity.length,mismatches:assetIdentity.filter(x=>x.current_sha256!==x.baseline_sha256)});
const baseCanvas=createCanvas(W,H),baseCtx=baseCanvas.getContext('2d'),heroSamples=[];
for(const e of timeline.entries.filter(e=>['opening','ending'].includes(e.section_id))){const t=e.start+(e.end-e.start)*.62;drawFrame(ctx,t,timeline,spec,assets);const current=hash(canvas.data());baselineDrawFrame(baseCtx,t,timeline,spec,assets);heroSamples.push({section_id:e.section_id,cut_index:e.cut_index,time_seconds:t,equal:current===hash(baseCanvas.data())})}
add('fifteen_hero_midpoints_rgba_equal_baseline6',heroSamples.length===15&&heroSamples.every(x=>x.equal),heroSamples);
const taskText=id=>records.filter(r=>r.section_id===id&&r.kind==='cut').flatMap(r=>r.samples.flatMap(p=>p.drawn_text.filter(x=>x.scope==='body').map(x=>x.text))).join('\n');
const requirements={
 task11:[['input and evidence',/Lot ID/i,/Map/i,/Trend/i,/K-param/i,/표준 진단/],['qualified analysis-time card',/15분.?1시간/,/건당 수분/,/자료 기준/],['support rather than autonomous correction',/지원/,/담당자 검토/]],
 task13:[['collection and report',/장비 이력/,/PM 계획/,/HTML/],['scheduled automation',/오전 6시/,/자동 발송/],['qualified efficiency',/20분\s*→\s*0분/,/122시간/,/자료 기준/]],
 task7:[['input and archive',/평가 목적/,/지식 아카이브/],['supported recommendations',/Recipe/,/근거 자료/,/평가 계획/,/전문가 지식/]],
 task17:[['analysis outputs',/기울기/,/측정 위치/,/측정값/,/좌표/,/오버레이/,/이력 저장/],['qualified metric',/5분\s*→\s*6초/,/자료 기준/],['human review and new-image errors',/최종 검증/,/누락.?오류 보완/]],
 task5:[['registration and extraction',/Working Board/,/등록/,/자연어|필요한 정보를 추출/,/추출/],['cross-analysis',/교차 분석/],['single access and knowledge',/조회 창구/,/도메인 지식/]],
 task9:[['input and chain',/Lot ID/,/메인 공정/,/수집/,/통합/,/상관/,/이상치/,/리포트/],['candidate not confirmed',/후보 랭킹/,/원인 확정 아님/],['qualified metric',/70% 이상 단축/,/자료 기준/]],
 task4:[['web integrated monitoring',/Lot/,/장비/,/FDC/,/Trend/],['shared DOE and knowledge',/DOE/,/함께 확인|공유/,/노하우/,/조직/]],
 task12:[['linked basis',/경비/,/장비 이력/,/22개 판단 지표/],['candidate and feasibility',/절감 검토 후보/,/실행 가능성/],['qualified unvalidated metric',/80% 이상 단축/,/자료 기준/,/실효성 검증 중/,/확정 실적 아님/]],
 task3:[['query and comparison',/Lot/,/장비 이력/,/Inline/,/공정 수순/,/Recipe/],['qualified metric',/2시간 40분/,/20분 이내/,/자료 기준/],['future reporting not current',/향후 계획|추가 개발 계획/,/자동 보고/,/고도화 연구 지원 Agent/]],
 task8:[['query and charts',/자연어/,/공정 데이터/,/Wafer Map/,/그래프/],['qualified metric',/40% 이상 단축/,/자료 기준/],['future notification/reporting',/향후 계획/,/챗봇 자동 알림/,/Reporting/]],
 task14:[['single app functions',/하나의 앱/,/Lot/,/장비 상태/,/TEM 쿼터/,/의뢰 현황/,/Daily.?Weekly Report/,/주말 근무자 안내/],['qualified metric and reuse',/90% 이상 단축/,/자료 기준/,/축적 데이터/]],
 task16:[['original input and candidates',/DD-SEM/,/전처리/,/적재/,/오계측 후보/,/자연어/],['scope-qualified metrics',/1200초\s*→\s*75초/,/317건\s*→\s*19건/,/자료 기준/,/단일 층 검증/],['human decision and future',/최종 판단/,/향후 계획/,/PROvision/]]
};
const factChecks=[];
for(const id of brief.order){const body=taskText(id);for(const [label,...patterns]of requirements[id]){const missing=patterns.filter(rx=>!rx.test(body)).map(String),finding={section_id:id,fact:label,pass:missing.length===0,missing,matched_patterns:patterns.filter(rx=>rx.test(body)).map(String)};factChecks.push(finding)}}
add('required_function_metric_and_caveat_visible_in_actual_body_text',factChecks.every(x=>x.pass),{requirements:factChecks.length,missing:factChecks.filter(x=>!x.pass)});
const allActual=records.flatMap(r=>r.samples.flatMap(s=>s.drawn_text.map(x=>x.text))).join('\n');
add('no_unsupported_plan_abc_or_confirmed_cause',!(/Plan\s*[ABC]\b|원인\s*확정\s*완료|절감\s*실적\s*확정|자동\s*보정\s*완료/i.test(allActual)),{basis:'Checks actual fillText calls only; unused legacy handlers are not considered displayed.'});
add('confirmed_equipment_spelling_dd_sem',/DD-SEM/.test(taskText('task16'))&&!/CD-SEM/.test(allActual),{confirmed_by:'Latest direct user correction back to DD-SEM, incorporated in authoritative brief.',spoken_equipment_term:'계측 데이터'});
const permittedNumbers={task11:['15','1'],task13:['6','06:00','20','0','122'],task7:[],task17:['5','6'],task5:[],task9:['70'],task4:[],task12:['22','80'],task3:['1','2','40','20'],task8:['1','40'],task14:['5','90'],task16:['1200','75','317','19']};
const numericText=brief.order.map(id=>({section_id:id,text:[...new Set(taskText(id).split('\n').filter(s=>/\d/.test(s)))],unsupported_tokens:[...new Set((taskText(id).match(/\d+(?::\d+)?/g)||[]).filter(x=>!permittedNumbers[id].includes(x)))]}));
add('coded_numeric_labels_only_use_user_supplied_values',numericText.every(x=>x.unsupported_tokens.length===0),{tasks:numericText,note:'Native coded labels only; photograph/source-image pixels are not OCR-transcribed by this audit.'});
const bodyOverflow=records.flatMap(r=>r.samples.flatMap(s=>s.drawn_text.filter(x=>x.scope==='body'&&x.alpha>=.5&&(x.bounds.left<78||x.bounds.right>1842||x.bounds.bottom>1022)).map(x=>({section_id:r.section_id,cut_id:r.cut_id,fraction:s.fraction,...x}))));
add('body_text_within_authored_safe_area',bodyOverflow.length===0,{possible_clipping:bodyOverflow,note:'Conservative projected ink bounds; visual check may distinguish harmless metric overestimate from actual clipping.'});
const cameraRows=records.filter(r=>r.kind==='cut'&&r.cut_index===0).map(r=>{const s=getCameraState(r.section_id,(r.end-r.start)*.62,r.end-r.start,assets);return{section_id:r.section_id,duration:r.end-r.start,view_count:s?.viewCount,camera:s}});
add('camera_first_photo_only_rigid_affine_no_human_warp',photoCameraContract.firstPhotoOnly&&photoCameraContract.rigidImageGeometry&&!photoCameraContract.humanWarp&&!photoCameraContract.meshWarp&&cameraRows.every(x=>x.view_count>=1)&&!fs.readFileSync(path.join(HERE,'task-scenes.js'),'utf8').includes('photoDisplacement'),{contract:photoCameraContract,first_photos:cameraRows});
const perCutAlignment=records.filter(r=>r.kind==='cut'&&r.cut_index===3&&content.tasks[r.section_id].cuts[3].metric).map(r=>{const metric=content.tasks[r.section_id].cuts[3].metric;const text=r.samples.flatMap(s=>s.drawn_text.filter(x=>x.scope==='body').map(x=>x.text)).join('\n');const expectations=requirements[r.section_id].find(x=>x[0].includes('metric')||x[0].includes('efficiency')||x[0].includes('analysis-time'));const patterns=(expectations||[]).slice(1);return{section_id:r.section_id,cut_id:r.cut_id,narration:r.narration_draft,metric,metric_visible_same_cut:patterns.length>0&&patterns.every(rx=>rx.test(text)),actual_body_text:[...new Set(r.samples.flatMap(s=>s.drawn_text.filter(x=>x.scope==='body').map(x=>x.text)))]}});
add('metric_card_matches_its_narration_cut',perCutAlignment.every(x=>x.metric_visible_same_cut),{mismatches:perCutAlignment.filter(x=>!x.metric_visible_same_cut),note:'Timing is only a preview, but the cut index and associated script are already authored.'});
// Minimum semantic evidence for the newly authored phases, independent of
// support_lines/spec metadata. Specific wording can differ without failing.
const cutSemantics={
 task11:{1:[/Lot ID/,/Map/,/Trend/,/K-param/],2:[/표준 진단/,/원인 분석|솔루션/],4:[/근거/,/반복 조회|반복 설정|한 화면/]},
 task13:{1:[/장비 이력/,/PM 계획/],2:[/오전 6시|06:00/,/HTML/,/자동 발송/],4:[/메일 확인|메일 검토|확인·검토/,/장비 대응/]},
 task7:{1:[/평가 목적/,/아카이브|지식 검색/],2:[/Recipe/,/근거/],3:[/평가 계획/,/탐색|문의|의존/],4:[/전문가 지식/,/축적|담당자/]},
 task17:{1:[/기울기/,/측정 위치/],2:[/측정값/,/좌표/,/오버레이/,/이력 저장/],4:[/최종 검증/,/누락.?오류/,/검토|예외/]},
 task5:{1:[/Working Board/,/등록/],2:[/자연어|필요한 정보를 추출/,/추출/,/교차 분석/],3:[/조회 창구/,/단일화|취합 부담/],4:[/자료/,/도메인 지식/]},
 task9:{1:[/Lot ID/,/메인 공정/,/수집/,/통합/],2:[/상관/,/이상치/,/후보 랭킹/,/리포트/],4:[/기준|일관|분석 흐름/,/후보/,/확정.*아님|≠\s*확정 원인|담당자가?\s*(후보를\s*)?검토/]},
 task4:{1:[/웹|통합/,/현황|Trend/],2:[/DOE/,/함께 확인|공동 확인|공유/],3:[/시스템 이동/,/가공 부담/],4:[/평가 결과|DOE 결과/,/노하우/,/공유|조직/]},
 task12:{1:[/경비/,/장비 이력/,/22개 판단 지표/],2:[/비용 증가/,/절감 검토 후보/,/실행 가능성/],4:[/후보/,/확정.*아님|확정.*구분|≠\s*확정 절감 실적/,/장비 이력|실행 가능성/]},
 task3:{1:[/Lot/,/장비 이력/,/Inline/,/조회|추출/],2:[/Lot 간/,/공정 수순/,/장비/,/Recipe/],4:[/해석/,/향후 계획|추가 개발 계획/,/자동 보고/]},
 task8:{1:[/자연어/,/공정 데이터/],2:[/Wafer Map/,/그래프/,/가공/],4:[/협업/,/향후 계획/,/챗봇 자동 알림/,/Reporting/]},
 task14:{1:[/Lot/,/장비 상태/,/TEM 쿼터/,/의뢰 현황/],2:[/Daily.?Weekly Report|Daily.*Weekly/,/주말 근무자/,/자동화|자동/],4:[/반복 조회|취합|보고 부담/,/축적 데이터/]},
 task16:{1:[/DD-SEM 수집/,/전처리/,/적재/],2:[/오계측 후보/,/대시보드/,/자연어/],4:[/담당자/,/검토 범위/,/향후 계획/,/PROvision/]}
};
const semanticChecks=[];
for(const [id,cuts]of Object.entries(cutSemantics))for(const [index,patterns]of Object.entries(cuts)){
 const r=records.find(r=>r.section_id===id&&r.kind==='cut'&&r.cut_index===Number(index));
 const body=r.samples.flatMap(s=>s.drawn_text.filter(t=>t.scope==='body').map(t=>t.text)).join('\n');
 const missing=patterns.filter(rx=>!rx.test(body)).map(String);
 semanticChecks.push({section_id:id,cut_id:r.cut_id,pass:missing.length===0,missing,narration:r.narration_draft,actual_body_text:[...new Set(r.samples.flatMap(s=>s.drawn_text.filter(t=>t.scope==='body').map(t=>t.text)))]});
}
add('all_new_cut_semantic_phases_match_actual_body',semanticChecks.every(x=>x.pass),{tested_cuts:semanticChecks.length,mismatches:semanticChecks.filter(x=>!x.pass)});
for(const [f,h]of Object.entries(sourceHashes))if(fileHash(f)!==h)throw new Error('Source changed during review: '+f);
add('source_snapshot_stable_during_audit',true,{files:Object.keys(sourceHashes).length});
const report={status:Object.values(checks).every(x=>x.pass)?'PASS':'REVIEW',scope:'Revision8 independent native-draw factual/visual audit at the selected timeline; not an audio, encoded-video, playback, external verification, or factual efficacy validation.',delivery_status:timeline.preview_only?'VISUAL_PREVIEW_ONLY':'VISUAL_TIMELINE_AUDIT_ONLY',final_production_complete:false,preview_timing:timeline.preview_only===true,timing_basis:timeline.timing_basis||null,estimated_duration_seconds:timeline.duration,voice_generation_performed:false,final_voice_validation:false,final_narration_status:timeline.preview_only?'BLOCKED_PENDING_COMPLETE_TAKE':'PENDING_INDEPENDENT_AUDIO_VALIDATION',narration_status_basis:timeline.preview_only?'Root reports the latest authorized generation could not be submitted because the ElevenLabs connector became unavailable. This visual audit neither retries generation nor validates a final take.':'Root reports a new full single take with all sixty task sentences anchored. Independent audio validation is pending and is not established by this visual audit.',baseline_revision:6,excluded_revision7_person_warp:true,source_hashes:sourceHashes,checks,issues,counts:{tasks:12,title_entries:12,body_cuts:60,task_entry_samples:144,hero_midpoint_samples:15},fact_checks:factChecks,cut_metric_alignment:perCutAlignment,cut_semantic_checks:semanticChecks,actual_rendered_text:records,limitations:['Native text is captured at 62% and 90% of each selected-timeline cut. Its measured body coordinates are conservative and do not prove all text is visually unobscured.','First-photo problem context remains in the narration script and retained title; no descriptive labels are added over the approved photographs.','Spoken text and support_lines are reported separately and are never counted as actual rendered body text.','No new voice was generated or requested by this audit. No independent audio/word-boundary, full video render, or playback validation is claimed.']};
fs.writeFileSync(path.join(OUT,'revision8-content-validation.json'),JSON.stringify(report,null,2)+'\n');
// Five 12-frame contact sheets document all 60 body views, not encoded video.
const bodies=records.filter(r=>r.kind==='cut');for(let page=0;page<5;page++){const sheet=createCanvas(1920,1560),c=sheet.getContext('2d');c.fillStyle='#111';c.fillRect(0,0,1920,1560);for(let j=0;j<12;j++){const row=bodies[page*12+j];if(!row)continue;const im=await loadImage(path.join(OUT,row.samples[0].native_file)),x=(j%3)*640,y=Math.floor(j/3)*390;c.drawImage(im,x,y,640,360);c.fillStyle='#eee';c.font='20px Noto';c.fillText(`${row.cut_id}: ${row.title}`,x+10,y+385)}fs.writeFileSync(path.join(DIR,`body-contact-${page+1}.jpg`),sheet.encodeSync('jpeg'))}
console.log(JSON.stringify({status:report.status,report:path.join(OUT,'revision8-content-validation.json'),checks:Object.keys(checks).length,failed:Object.entries(checks).filter(([,v])=>!v.pass).map(([k])=>k),source_files:Object.keys(sourceHashes).length}));
