import {drawCameraPhoto} from './photo-camera.js';
import {drawEarlyTask,earlyVisualPlan} from './task-visuals-early.js';
import {drawLateTask,lateVisualPlan} from './task-visuals-late.js';
/* Deterministic 1920 × 1080 task compositions. No measured values are invented.
 * Public API: loadTaskAssets(spec); drawTask(ctx,section,cut,time,duration,assets).
 * A cut may be a section.cuts object or its zero-based index.
 * Prefer clean photographic plates in assets.backgrounds[section.id][cutIndex].
 * Fallback reference images supply photographic texture only; their storyboard
 * labels and complete panels are never displayed as a finished scene.
 */
const W=1920,H=1080,INK='#080808',GOLD='#D4AF7C',CREAM='#F2EEE7',AMBER='#FFB347';
const FONT='"Noto", "Noto Sans KR", "Noto Sans CJK KR", sans-serif';
const clamp=(n,a=0,b=1)=>Math.max(a,Math.min(b,n));
const ease=n=>{n=clamp(n);return n*n*(3-2*n)};
const hash=n=>{const a=Math.sin(n*127.1+311.7)*43758.5453;return a-Math.floor(a)};
const profiles=[
 {key:'infra',match:/Infra|연구 환경|재오/,name:'연구 환경 Infra',sources:["Lot·장비 이력", "Inline 데이터", "공정 수순", "Recipe", "연계공정 정보"],nav:["조회·추출", "Lot 간 비교", "해석 지원"]},
 {key:'thinfilm',match:/Thinfilm|태민/,name:'Thinfilm Agent',sources:["Lot 현황", "장비 현황", "FDC 모니터링", "공유 DOE 결과"],nav:["현황 조회", "모니터링 Trend", "DOE 공동 확인"]},
 {key:'working',match:/Working Board|우석/,name:'C&C Working Board',sources:["등록 데이터", "여러 표", "관련 자료", "도메인 지식"],nav:["데이터 등록", "자연어 추출", "교차 분석"]},
 {key:'architecture',match:/Architecture|혜선/,name:'Smart Process Architecture',sources:["HyDisk", "Cube", "과거 평가 자료", "전문가 지식"],nav:["평가 목적", "Recipe·근거", "평가 계획"]},
 {key:'monitoring',match:/Monitoring|태관/,name:'Monitoring Data AI Agent',sources:["Smart Factory", "공정 데이터", "장비 데이터", "조회 조건"],nav:["자연어 검색", "Wafer Map", "그래프"]},
 {key:'inline',match:/Inline|지욱/,name:'C&C Inline Data AI Agent',sources:["Lot ID", "메인 공정", "연계공정 데이터"],nav:["데이터 수집", "통합", "상관·이상치", "후보 랭킹", "리포트"]},
 {key:'snm',match:/RSAB|SNM|민희/,name:'RSAB SNM Overlay AI Agent',sources:["SmartDCP", "TAS", "Qoniac"],nav:["Lot ID", "Map", "Trend", "K-param"]},
 {key:'expense',match:/경비|승재/,name:'경비 분석 AI Agent',sources:["경비 실적", "장비 이력", "22개 판단 지표", "절감 검토 후보"],nav:["이력 연결", "후보 분석", "검증 상태"]},
 {key:'daily',match:/Daily Report|도훈/,name:'Equipment Daily Report',sources:["장비 이력", "PM 계획", "장비 이슈", "조회·요약"],nav:["이력·계획 조회", "표준 HTML 보고", "오전 6시 발송"]},
 {key:'cubic',match:/App&Agent|전용 App|현준/,name:'Cubic공정Lab',sources:["Lot·장비 현황", "TEM 현황", "Report", "주말 근무자 정보", "개별 취합"],nav:["Lot 조회", "장비 상태", "TEM 쿼터", "의뢰 현황", "Daily·Weekly Report", "주말근무자 안내"]},
 {key:'tcad',match:/TCAD|TEM 이미지|성후/,name:'TCAD-TEM Labeling Tool',sources:["수동 회전", "측정선 작성", "값 기록", "항목별 정리"],nav:["기울기 분석", "위치 분석", "측정값·좌표", "오버레이", "결과·이력 저장"]},
 {key:'plug',match:/Plug|지은/,name:'Plug 대면적 분석',sources:["DD-SEM 수집", "전처리", "적재", "오계측 후보"],nav:["수집·전처리", "후보 탐지", "리뷰 범위", "자연어 분석"]}
];
// Use all 1080 pixels now that the narration caption band is disabled. Keep
// each photographed monitor's x position, dimensions, shear and UI scale.
// The outer bezel's sheared bounding-box center settles at the midpoint of
// the space below the retained 154 px title band: (154 + 1080) / 2 = 617.
const TITLE_BAND_HEIGHT=154,AFTER_BEZEL_CENTER_Y=(TITLE_BAND_HEIGHT+H)/2;
const baselineAfterLayouts={infra:[640,250,1190,590,-.024],thinfilm:[650,251,1180,590,-.04],working:[658,259,1175,586,.018],architecture:[647,253,1187,585,-.025],monitoring:[657,252,1178,585,-.028],inline:[645,253,1190,590,-.03],snm:[614,259,1215,580,-.02],expense:[650,254,1180,590,-.033],daily:[652,258,1180,586,-.025],cubic:[646,257,1187,585,.016],tcad:[623,259,1203,580,-.02],plug:[620,255,1210,590,-.022]};
export const afterLayouts=Object.freeze(Object.fromEntries(Object.entries(baselineAfterLayouts).map(([key,[x,oldY,w,h,tilt]])=>{
 const y=AFTER_BEZEL_CENTER_Y+9-(h/2-1)-tilt*w/2;
 return[key,Object.freeze({x,y,w,h,tilt,baselineY:oldY,translationY:y-oldY,settledBezelCenterY:AFTER_BEZEL_CENTER_Y,settledScreenCenterY:AFTER_BEZEL_CENTER_Y+1})];
})));
function profile(section){return profiles.find(p=>p.match.test(`${section.title} ${section.owner} ${section.id}`))||profiles[0]}
function shearedBounds(x,y,w,h,tilt,originX,originY){const corners=[[x,y],[x+w,y],[x,y+h],[x+w,y+h]].map(([xx,yy])=>[originX+xx,originY+yy+tilt*xx]);const xs=corners.map(p=>p[0]),ys=corners.map(p=>p[1]);const left=Math.min(...xs),right=Math.max(...xs),top=Math.min(...ys),bottom=Math.max(...ys);return{left,right,top,bottom,width:right-left,height:bottom-top,centerX:(left+right)/2,centerY:(top+bottom)/2}}
export function getTaskPlacement(sectionOrKey,localTime=2){
 const key=typeof sectionOrKey==='string'?sectionOrKey:profile(sectionOrKey).key,layout=afterLayouts[key];if(!layout)throw new Error(`Unknown task profile: ${key}`);
 const t=Math.max(0,Number(localTime)||0),originX=layout.x+12*Math.sin(t*.2),originY=layout.y-9*ease(t/2);
 return{profile:key,...layout,localTime:t,originX,originY,screenBounds:shearedBounds(0,0,layout.w,layout.h,layout.tilt,originX,originY),bezelBounds:shearedBounds(-12,-13,layout.w+24,layout.h+24,layout.tilt,originX,originY)};
}
function box(c,x,y,w,h,r=16){c.beginPath();c.roundRect(x,y,w,h,r)}
function panel(c,x,y,w,h,{fill='#0C1118',line='#D4AF7C66',radius=18}={}){c.fillStyle=fill;box(c,x,y,w,h,radius);c.fill();c.strokeStyle=line;c.lineWidth=2;c.stroke()}
function text(c,s,x,y,size=30,color=CREAM,weight=500){c.font=`${weight} ${size}px ${FONT}`;c.fillStyle=color;c.fillText(String(s),x,y)}
function fit(c,s,x,y,maxW,size=30,color=CREAM,weight=500){c.font=`${weight} ${size}px ${FONT}`;while(c.measureText(s).width>maxW&&size>18){size--;c.font=`${weight} ${size}px ${FONT}`}c.fillStyle=color;c.fillText(s,x,y)}
function lines(c,s,maxW,size,weight=500){c.font=`${weight} ${size}px ${FONT}`;const result=[];for(const para of String(s||'').split('\n')){let row='';for(const ch of para){if(row&&c.measureText(row+ch).width>maxW){result.push(row.trimEnd());row=ch===' '?'':ch}else row+=ch}if(row)result.push(row)}return result}
function glow(c,x,y,r=50,alpha=.5){c.save();c.globalCompositeOperation='screen';const g=c.createRadialGradient(x,y,0,x,y,r);g.addColorStop(0,`rgba(255,237,196,${alpha})`);g.addColorStop(.25,`rgba(255,179,71,${alpha*.42})`);g.addColorStop(1,'#FFB34700');c.fillStyle=g;c.fillRect(x-r,y-r,2*r,2*r);c.restore()}
function line(c,x1,y1,x2,y2,q=1,color=GOLD,width=3){c.strokeStyle=color;c.lineWidth=width;c.lineCap='round';c.beginPath();c.moveTo(x1,y1);c.lineTo(x1+(x2-x1)*clamp(q),y1+(y2-y1)*clamp(q));c.stroke()}
function flow(c,a,b,t,delay=0){const p=ease((t-delay)/1.2);line(c,...a,...b,p,'#D4AF7C77',3);if(p){const q=((Math.max(0,t-delay)*.48)%1)*p,x=a[0]+(b[0]-a[0])*q,y=a[1]+(b[1]-a[1])*q;glow(c,x,y,20,.65)}}
function icon(c,type,x,y,s=36,color=GOLD){c.save();c.translate(x,y);c.strokeStyle=color;c.lineWidth=2.5;c.lineJoin='round';if(type==='doc'){box(c,0,0,s*.75,s,3);c.stroke();for(let j=0;j<3;j++)line(c,6,12+j*7,s*.6,12+j*7,1,color,2)}else if(type==='mail'){box(c,0,0,s,s*.7,3);c.stroke();line(c,0,0,s/2,s*.35,1,color,2);line(c,s,0,s/2,s*.35,1,color,2)}else if(type==='search'){c.beginPath();c.arc(s*.35,s*.35,s*.28,0,Math.PI*2);c.stroke();line(c,s*.56,s*.56,s*.9,s*.9,1,color,3)}else if(type==='database'){for(const yy of [0,s*.35,s*.7]){c.beginPath();c.ellipse(s/2,yy+s*.12,s*.45,s*.12,0,0,Math.PI*2);c.stroke()}line(c,s*.05,s*.12,s*.05,s*.82,1,color,2);line(c,s*.95,s*.12,s*.95,s*.82,1,color,2)}else if(type==='check'){line(c,0,s*.45,s*.3,s*.75,1,color,3);line(c,s*.3,s*.75,s,s*.05,1,color,3)}c.restore()}
function animatedBars(c,x,y,w,h,t,seed=0){c.save();c.beginPath();c.rect(x,y,w,h);c.clip();for(let j=0;j<10;j++){const p=ease((t-.08*j)/.65),bh=h*(.22+.64*hash(j+seed));c.fillStyle=j%3===0?'#FFB347':'#D4AF7C99';c.fillRect(x+j*w/10+7,y+h-bh*p,w/10-14,bh*p)}c.restore()}
function graph(c,x,y,w,h,t,seed=0,color=GOLD){for(let j=0;j<4;j++)line(c,x,y+j*h/3,x+w,y+j*h/3,1,'#FFFFFF12',1);line(c,x,y,x,y+h,1,'#D4AF7C55',2);line(c,x,y+h,x+w,y+h,1,'#D4AF7C55',2);const p=ease(t/1.35),N=48,points=[];for(let j=0;j<N;j++)points.push([x+j*w/(N-1),y+h*(.48+.15*Math.sin(j*.34+seed)+.15*Math.sin(j*.71+seed))]);c.strokeStyle=color;c.lineWidth=3;c.beginPath();points.forEach((a,j)=>{if(j/(N-1)<=p)j?c.lineTo(...a):c.moveTo(...a)});c.stroke();points.forEach((a,j)=>{if(j%4===0&&j/(N-1)<=p){c.fillStyle=color;c.beginPath();c.arc(...a,4,0,Math.PI*2);c.fill()}})}
function rows(c,labels,x,y,w,t,{gap=65,icons=true,selected=-1}={}){labels.forEach((label,j)=>{const q=ease((t-.18*j)/.55);c.save();c.globalAlpha=q;const yy=y+j*gap+(1-q)*15;panel(c,x,yy,w,gap-12,{fill:selected===j?'#514029':'#111922',line:selected===j?GOLD:'#D4AF7C44',radius:10});if(icons)icon(c,'doc',x+18,yy+14,25);fit(c,label,x+(icons?62:20),yy+35,w-(icons?80:40),28);c.restore()})}
function tabs(c,labels,x,y,w,t,{selected=0}={}){const gap=10,bw=(w-(labels.length-1)*gap)/labels.length;labels.forEach((s,j)=>{panel(c,x+j*(bw+gap),y,bw,47,{fill:j===selected?'#D4AF7C':'#151D26',line:j===selected?GOLD:'#D4AF7C44',radius:8});fit(c,s,x+j*(bw+gap)+14,y+31,bw-28,25,j===selected?INK:CREAM,600)})}
function shell(c,p,draw,{x=660,y=250,w=1180,h=590,tilt=-.035,t=0}={}){
 c.save();c.translate(x+12*Math.sin(t*.2),y-9*ease(t/2));c.transform(1,tilt,0,1,0,0);
 c.shadowColor='#000';c.shadowBlur=42;c.shadowOffsetY=20;panel(c,-12,-13,w+24,h+24,{fill:'#07090D',line:'#D4AF7C99',radius:25});c.shadowBlur=0;c.shadowOffsetY=0;
 c.save();box(c,0,0,w,h,17);c.clip();const g=c.createLinearGradient(0,0,w,h);g.addColorStop(0,'#17212B');g.addColorStop(1,'#070C12');c.fillStyle=g;c.fillRect(0,0,w,h);
 icon(c,'database',28,23,31);fit(c,p.name,80,49,w-140,32,CREAM,600);line(c,0,78,w,78,1,'#D4AF7C44',1);
 draw(c,{w,h,bx:28,by:100,bw:w-56,bh:h-130});c.restore();
 // Reflections on the physical bezel remain subordinate to the animated UI.
 const shine=c.createLinearGradient(0,0,w,0);shine.addColorStop(0,'#FFFFFF00');shine.addColorStop(.45,'#FFFFFF04');shine.addColorStop(.5,'#FFFFFF0B');shine.addColorStop(.6,'#FFFFFF00');c.fillStyle=shine;box(c,0,0,w,h,17);c.fill();line(c,w*.44,h+12,w*.56,h+12,1,'#D4AF7C99',4);c.restore()
}
function imageEntry(a){return a?.image||a?.element||a?.canvas||a?.video||a}
function cover(c,entry,x,y,w,h,{zoom=1,fx=.5,fy=.5}={}){const im=imageEntry(entry);if(!im)return false;const iw=im.videoWidth||im.naturalWidth||im.width,ih=im.videoHeight||im.naturalHeight||im.height;if(!(iw&&ih))return false;let sx=0,sy=0,sw=iw,sh=ih;const crop=entry?.crop;if(crop){[sx,sy,sw,sh]=Array.isArray(crop)?crop:[crop.x,crop.y,crop.w,crop.h];if(sw<=1&&sh<=1){sx*=iw;sy*=ih;sw*=iw;sh*=ih}}const r=w/h;if(sw/sh>r){const nw=sh*r;sx+=(sw-nw)*fx;sw=nw}else{const nh=sw/r;sy+=(sh-nh)*fy;sh=nh}const cw=sw/zoom,ch=sh/zoom;sx+=(sw-cw)*fx;sy+=(sh-ch)*fy;c.drawImage(im,sx,sy,cw,ch,x,y,w,h);return true}
function photographicBackground(c,section,i,t,d,assets,enableCamera=false){
 const b=assets?.backgrounds?.[section.id]?.[i]||assets?.backgrounds?.[section.id]?.[String(i)]||assets?.images?.[section.backgrounds?.[i]]||assets?.images?.[section.cuts?.[i]?.background]||assets?.images?.[section.background]||assets?.backgrounds?.[section.id]?.[0]||assets?.images?.[section.backgrounds?.[0]];
 const reference=assets?.images?.[section.reference_image]||assets?.images?.[String(section.reference_image||'').split('/').pop()];
 c.fillStyle=INK;c.fillRect(0,0,W,H);c.save();
 if(b){
  const camera=enableCamera&&i===0&&drawCameraPhoto(c,b,section.id,t,d,assets,{width:W,height:H,headerHeight:TITLE_BAND_HEIGHT});
  if(!camera)cover(c,b,0,0,W,H,{zoom:1.015+.025*clamp(t/d),fx:.48+.02*clamp(t/d),fy:.5});
 }
 else if(reference){
  // Photograph below the first panel's explanatory text. The large replacement
  // monitor conceals the old UI; we preserve the human/workspace photograph.
  const photo={image:imageEntry(reference),crop:[.003,.40,.204,.435]};cover(c,photo,0,0,W,H,{zoom:1.015+.03*clamp(t/d),fx:.31,fy:.60});
 }
 c.restore();const shade=c.createLinearGradient(0,0,W,0);shade.addColorStop(0,'#08080815');shade.addColorStop(.36,'#08080810');shade.addColorStop(1,i===0?'#08080815':'#0808089C');c.fillStyle=shade;c.fillRect(0,0,W,H);
 // Ground the rebuilt monitor in the photographed desk with warm practical light.
 if(i>0)glow(c,1320,870,420,.12);
}
function copy(c,cut,t,assets){
 c.save();const top=c.createLinearGradient(0,0,0,225);top.addColorStop(0,'#080808EE');top.addColorStop(.65,'#080808C8');top.addColorStop(1,'#08080800');c.fillStyle=top;c.fillRect(0,0,W,225);
 c.globalAlpha=ease(t/.3);if(assets.drawTitles!==false){const title=String(cut.title||'').replace(/^CUT\s*\d+\s*[—–-]?\s*/i,'');let ts=68;let titleLines=lines(c,title,1776,ts,700);if(titleLines.length>2){ts=60;titleLines=lines(c,title,1776,ts,700)}titleLines.slice(0,2).forEach((s,j)=>text(c,s,72,98+j*77,ts,CREAM,700));line(c,72,130+(titleLines.length-1)*77,460,130+(titleLines.length-1)*77,1,GOLD,3)}c.globalAlpha=1;
 if(assets.drawCaptions===true){const bottom=c.createLinearGradient(0,840,0,H);bottom.addColorStop(0,'#08080800');bottom.addColorStop(.22,'#080808E8');bottom.addColorStop(1,'#080808F5');c.fillStyle=bottom;c.fillRect(0,840,W,240);const caption=cut.caption??cut.narration??'';let size=42,capLines=lines(c,caption,1776,size,500);if(capLines.length>2){size=40;capLines=lines(c,caption,1776,size,500)}c.textAlign='center';capLines.slice(0,2).forEach((s,j)=>text(c,s,W/2,capLines.length===1?984:950+j*58,size,CREAM,500))}c.restore();
}
function beforeMotion(c,p,t,d,assets,section){
 // These are screen surfaces inside the photographic workspace, rather than
 // floating descriptive cards. Independent focus and manual window selection
 // convey the repeated checking work that the next scene resolves.
 const screenRegions=assets?.screenRegions?.[section.id]||[
  {x:586,y:300,w:496,h:295,tilt:-.06},
  {x:1094,y:240,w:546,h:330,tilt:.05},
  {x:1243,y:627,w:407,h:192,tilt:-.015}
 ];
 const chosen=Math.floor(t*1.1)%screenRegions.length;
 screenRegions.forEach((r,j)=>{const focused=j===chosen,q=ease((t-.15*j)/.55),phase=Math.max(0,t-.15*j);c.save();c.translate(r.x,r.y);c.transform(1,r.tilt||0,0,1,0,0);c.globalAlpha=(focused?.9:.57)*q;
  panel(c,0,0,r.w,r.h,{fill:'#0B131C',line:focused?'#D4AF7C99':'#73818B44',radius:7});c.save();box(c,4,4,r.w-8,r.h-8,4);c.clip();const label=p.sources[j%p.sources.length];fit(c,label,15,34,r.w-30,25,GOLD,600);line(c,0,48,r.w,48,1,'#FFFFFF22',1);
  if(['tcad','plug'].includes(p.key))micrograph(c,12,60,r.w-24,r.h-72,phase,{plug:p.key==='plug',rotate:p.key==='tcad',photo:p.texture});
  else if(j%2===1)graph(c,20,80,r.w-40,r.h-108,phase*.55,j*5,'#8DA5B0');
  else for(let k=0;k<5;k++){const yy=74+k*(r.h-88)/5;c.fillStyle=focused&&k===Math.floor(t*2)%5?'#D4AF7C77':'#DBE3E733';c.fillRect(18,yy,r.w*.34,7);c.fillStyle='#DBE3E72B';c.fillRect(r.w*.45,yy,r.w*.44,7);line(c,15,yy+20,r.w-15,yy+20,1,'#FFFFFF16',1)}
  if(focused){const px=22+(phase*.23%1)*(r.w-70),py=73+(Math.floor(phase*1.8)%4)*(r.h-110)/4;c.fillStyle='#F5D6A6';c.beginPath();c.moveTo(px,py);c.lineTo(px+4,py+19);c.lineTo(px+9,py+12);c.lineTo(px+19,py+12);c.closePath();c.fill();if(phase%1.3<.28){c.strokeStyle='#D4AF7C66';c.lineWidth=2;c.beginPath();c.arc(px,py,12+(phase%1.3)*45,0,Math.PI*2);c.stroke()}}
  c.restore();c.restore();
 });
}
function connectionScene(c,p,t,{labels=p.sources,center='AI Agent'}={}){
 const left=35,right=745,cy=290;labels.forEach((s,j)=>{const x=j%2?right:left,y=115+Math.floor(j/2)*180,q=ease((t-j*.18)/.65);c.save();c.globalAlpha=q;panel(c,x,y,310,120,{line:'#D4AF7C77'});icon(c,'database',x+24,y+30,42);fit(c,s,x+90,y+72,194,29);c.restore();flow(c,[j%2?x:x+310,y+60],[568,cy],t,j*.15)});panel(c,425,cy-65,290,130,{fill:'#35271A',line:GOLD});fit(c,center,455,cy+12,240,35,GOLD,700);glow(c,565,cy,100,.1+.07*Math.sin(t*2));
}
function unifiedScene(c,p,t){
 rows(c,p.sources,28,104,340,t,{gap:72,selected:Math.floor(t*.9)%p.sources.length});panel(c,400,104,724,436,{line:'#D4AF7C55'});text(c,'통합 조회',426,148,31,GOLD,600);tabs(c,p.nav,426,174,670,t,{selected:Math.min(p.nav.length-1,Math.floor(t*.65))});
 for(let j=0;j<5;j++){const y=253+j*53,q=ease((t-.16*j)/.55);c.globalAlpha=q;line(c,426,y+39,1094,y+39,1,'#FFFFFF18',1);c.fillStyle='#D4AF7C33';c.fillRect(426,y,142+hash(j+17)*130,13);c.fillStyle='#E8E5DD44';c.fillRect(760,y,220,13)}c.globalAlpha=1;flow(c,[365,330],[400,330],t,.25);
}
function searchScene(c,p,t,question,labels=p.sources){
 const q=ease(t/.55);panel(c,40,120,1060,104,{fill:'#F2EEE7',line:'#D4AF7C99'});icon(c,'search',66,150,32,INK);const typed=question.slice(0,Math.floor(clamp((t-.25)/1.7)*question.length));fit(c,typed+(Math.floor(t*3)%2?'│':''),120,185,886,34,INK,600);icon(c,'search',1041,153,31,INK);rows(c,labels,66,265,990,t-1.1,{gap:65,selected:Math.floor(Math.max(0,t-1.2)*1.1)%labels.length});
}
function summaryScene(c,p,t){
 panel(c,40,105,510,436);text(c,'관련 자료',65,150,31,GOLD,600);rows(c,p.sources,65,175,460,t,{gap:73});panel(c,582,105,520,436);text(c,'핵심 내용 정리',607,150,31,GOLD,600);
 for(let j=0;j<4;j++){const q=ease((t-.3-j*.3)/.6);c.fillStyle='#D4AF7C18';c.fillRect(607,190+j*76,440*q,34);c.fillStyle='#F2EEE755';c.fillRect(620,202+j*76,370*q,9);c.fillStyle='#F2EEE72A';c.fillRect(620,243+j*76,280*q,7);flow(c,[525,223+j*73],[582,208+j*76],t,.2+j*.25)}
}
function knowledgeScene(c,p,t){
 rows(c,p.sources,30,105,370,t,{gap:83});panel(c,438,105,677,436);text(c,'관련 지식과 경험',468,151,32,GOLD,600);for(let j=0;j<4;j++){const x=510+(j%2)*310,y=235+Math.floor(j/2)*190;icon(c,'doc',x,y,53);fit(c,p.sources[j],x+70,y+38,214,28);flow(c,[390,140+j*83],[x+23,y+25],t,j*.18)}
}
function recommendationScene(c,p,t){
 text(c,'Plan·Recipe 추천',40,143,34,GOLD,700);const labs=['Plan A','Plan B','Plan C'];labs.forEach((s,j)=>{const q=ease((t-.18*j)/.6);c.save();c.globalAlpha=q;panel(c,40+j*358,173+(1-q)*25,334,145,{fill:j===Math.min(2,Math.floor(t*.7))?'#3A2C1B':'#121A22',line:GOLD});text(c,s,62+j*358,232,36,GOLD,700);text(c,'관련 근거',62+j*358,282,25);c.restore()});rows(c,p.sources,40,349,1050,t-.6,{gap:43,icons:false});
}
function chartScene(c,p,t,{mode='line'}={}){
 tabs(c,p.nav,28,102,1100,t,{selected:Math.floor(t*.55)%p.nav.length});panel(c,28,171,692,360);panel(c,746,171,380,360);text(c,mode==='correlation'?'상관관계 분석':'분석 결과',54,214,29,GOLD,600);if(mode==='bars'||mode==='correlation')animatedBars(c,60,258,620,225,t-.25,12);else graph(c,63,262,620,226,t-.25,6);text(c,mode==='correlation'?'연계 공정':'관련 정보',774,214,28,GOLD,600);rows(c,mode==='correlation'?['관련 공정 데이터','GoodDocs 매핑','연계 공정 선별']:p.sources.slice(0,3),771,249,326,t-.4,{gap:79,icons:false});
}
function thinfilmCharts(c,p,t){
 const names=['Lot Trend','Equipment Status','FDC Summary','DOE Result'];
 names.forEach((s,j)=>{const x=28+(j%2)*558,y=105+Math.floor(j/2)*224;panel(c,x,y,533,205);text(c,s,x+23,y+41,29,GOLD,600);const local=t-j*.23;
  if(j===1){const cx=x+269,cy=y+129,r=54,q=ease(local/1.1);c.strokeStyle='#D4AF7C33';c.lineWidth=17;c.beginPath();c.arc(cx,cy,r,0,Math.PI*2);c.stroke();c.strokeStyle=GOLD;c.beginPath();c.arc(cx,cy,r,-Math.PI/2,-Math.PI/2+Math.PI*2*q);c.stroke()}
  else if(j===2)animatedBars(c,x+26,y+71,480,108,local,31);
  else graph(c,x+29,y+76,475,103,local,j*15);
 });
}
function infraMetricScene(c,p,t){
 // This figure is explicitly asserted by the Infra MD, unlike the other
 // conditional metrics omitted elsewhere in the supplied spec.
 text(c,'Lot 1건 분석 시간',40,151,34,GOLD,600);const q=ease(t/.7),r=ease((t-.65)/.7);c.save();c.globalAlpha=q;panel(c,40,202,420,257,{fill:'#101821',line:'#D4AF7C66'});text(c,'기존 약',71,270,33);text(c,'2시간 40분',71,367,51,CREAM,700);c.restore();flow(c,[483,330],[662,330],t,.5);c.save();c.globalAlpha=r;panel(c,680,202,417,257,{fill:'#3B2B19',line:GOLD});text(c,'개선 후',711,270,33,GOLD);text(c,'20분 이내',711,367,55,GOLD,700);c.restore();
}
function thinfilmAssetScene(c,p,t){
 const labs=['DOE 결과','분석 방법','최적 조건 탐색'];labs.forEach((s,j)=>{const x=53+j*360,q=ease((t-j*.24)/.6);c.save();c.globalAlpha=q;icon(c,'doc',x+92,154,83);fit(c,s,x+15,299,283,33,GOLD,600);c.restore();if(j<2)flow(c,[x+217,208],[x+387,208],t,.3+j*.3)});text(c,'DOE 분석 효율화 · 최적 조건 탐색 지원',53,418,37,GOLD,600);text(c,'분석 방법과 탐색 로직을 조직의 자산으로',53,487,29);
}
function tcadComparison(c,p,t){
 panel(c,28,105,533,431);text(c,'R_NIT 정확도 · S/W 정확도',52,153,30,GOLD,600);animatedBars(c,65,218,460,272,t,85);panel(c,590,105,536,431);text(c,'R_NIT vs S/W',615,153,30,GOLD,600);const q=ease((t-.35)/1.2);for(let j=0;j<75*q;j++){const x=636+hash(j+72)*436,y=486-(x-636)*.49+(hash(j+101)-.5)*90;c.fillStyle=j%3?GOLD:'#6F9CAA';c.beginPath();c.arc(x,y,3.6,0,Math.PI*2);c.fill()}line(c,634,489,1087,489,1,'#D4AF7C66',1);line(c,634,201,634,489,1,'#D4AF7C66',1);
}
function shareScene(c,p,t){
 panel(c,35,110,540,420);text(c,'DOE Result',60,157,32,GOLD,600);graph(c,68,215,460,190,t,5);rows(c,['DOE 결과 업데이트','분석 보고서'],65,426,450,t-.3,{gap:47,icons:false});panel(c,680,140,410,345);icon(c,'doc',810,192,77);text(c,'업데이트·공유',749,343,37,GOLD,600);flow(c,[575,322],[680,322],t,.4);text(c,'조직의 지식 자산',750,402,26);
}
function issueScene(c,p,t){
 text(c,'업무 진행 현황',35,142,34,GOLD,700);const cols=['이슈','관련 문서','핵심 내용'];cols.forEach((s,j)=>{text(c,s,50+j*365,199,28,GOLD,600);for(let k=0;k<3;k++){const q=ease((t-.18*k-.2*j)/.5);c.save();c.globalAlpha=q;panel(c,36+j*365,224+k*94+(1-q)*12,338,76);icon(c,'doc',55+j*365,245+k*94,29);c.fillStyle='#F2EEE755';c.fillRect(107+j*365,250+k*94,218,9);c.fillStyle='#F2EEE72A';c.fillRect(107+j*365,274+k*94,155,7);c.restore()}});
}
function wafer(c,cx,cy,r,t,{vector=false,scatter=false,seed=0}={}){
 c.save();c.beginPath();c.arc(cx,cy,r,0,Math.PI*2);c.clip();c.fillStyle='#172332';c.fillRect(cx-r,cy-r,r*2,r*2);const p=ease(t/1.2),n=20;
 for(let j=0;j<n;j++)for(let k=0;k<n;k++){const x=cx-r+(j+.5)*2*r/n,y=cy-r+(k+.5)*2*r/n;if((x-cx)**2+(y-cy)**2>r*r)continue;const z=hash(j*71+k*9+seed);c.globalAlpha=p*(.45+.4*z);c.fillStyle=z>.74?'#FFB347':z>.39?'#D4AF7C':'#4E7891';if(scatter){c.beginPath();c.arc(x+(hash(j+k)-.5)*4,y,2.5,0,Math.PI*2);c.fill()}else if(vector){const a=Math.atan2(y-cy,x-cx)+seed*.1;line(c,x,y,x+Math.cos(a)*8,y+Math.sin(a)*8,1,c.fillStyle,1.4)}else c.fillRect(x-2*r/n*.42,y-2*r/n*.42,2*r/n*.84,2*r/n*.84)}c.globalAlpha=1;
 const sx=cx-r+(t*.28%1)*r*2,g=c.createLinearGradient(sx-26,0,sx+26,0);g.addColorStop(0,'#FFFFFF00');g.addColorStop(.5,'#FFF2CC44');g.addColorStop(1,'#FFFFFF00');c.fillStyle=g;c.fillRect(cx-r,cy-r,r*2,r*2);c.restore();c.strokeStyle='#D4AF7C77';c.lineWidth=2;c.beginPath();c.arc(cx,cy,r,0,Math.PI*2);c.stroke();
}
function mapScene(c,p,t,{monitor=false}={}){
 if(monitor){panel(c,28,105,480,432);text(c,'Wafer Map',53,150,30,GOLD,600);wafer(c,266,344,155,t);panel(c,537,105,589,432);text(c,'그래프',561,150,30,GOLD,600);graph(c,575,222,505,250,t,11);return}
 tabs(c,['Overlay','Residual','MA Bias'],30,100,1096,t,{selected:Math.floor(t*.7)%3});['Overlay','Residual','MA Bias'].forEach((s,j)=>{const x=30+j*369;panel(c,x,175,351,360);text(c,s,x+23,219,30,GOLD,600);wafer(c,x+175,375,132,t-.18*j,{vector:j===0,scatter:j===1,seed:j*23});});
}
function baselineScene(c,p,t){
 panel(c,28,105,555,432);text(c,'Parameter Trend',53,150,30,GOLD,600);text(c,'정상 Baseline / 입력 Wafer',53,192,24);for(let j=0;j<6;j++){const x=80+j*80,q=ease((t-j*.12)/.7),cy=342+(hash(j+2)-.5)*55;line(c,x,245,x,475,q,'#FFFFFF25',1);c.fillStyle='#738F9C';c.fillRect(x-22,cy-37*q,19,74*q);c.fillStyle=AMBER;c.fillRect(x+5,cy-45*q,19,90*q)}panel(c,613,105,512,432);text(c,'정상 대비 Wafer 분포',640,150,29,GOLD,600);wafer(c,871,350,145,t-.3,{scatter:true,seed:27});
}
function kParameterScene(c,p,t){
 panel(c,28,105,540,434);text(c,'K-parameter · Z-score',53,151,30,GOLD,600);rows(c,['장비 정렬/Reticle','노광','CMP','PR'],53,190,490,t,{gap:77,icons:false,selected:Math.floor(t*.85)%4});panel(c,600,105,526,434);text(c,'의심 공정 계층 추정',626,151,29,GOLD,600);rows(c,['정상 Baseline 대비 평가','의심 항목 검토','원인별 솔루션 제시'],626,203,472,t-.4,{gap:102});
}
function expenseInsights(c,p,t){
 panel(c,28,105,645,434);text(c,'경비 트렌드 분석',54,151,31,GOLD,600);graph(c,66,217,560,265,t,14);panel(c,700,105,425,434);text(c,'절감 가능 항목',725,151,30,GOLD,600);rows(c,['주요 절감 아이템','주요 인사이트','기대 효과'],725,193,372,t-.3,{gap:103,icons:false});
}
function reviewScene(c,p,t,{plug=false}={}){
 if(plug){micrograph(c,35,104,615,434,t,{plug:true,measure:true,suspect:true,photo:p.texture});panel(c,676,105,450,432);text(c,'검토 대상 선별',699,154,30,GOLD,600);rows(c,['오계측 의심 항목','검토 대상','담당자 최종 판단'],700,205,400,t-.3,{gap:101,icons:false,selected:Math.min(2,Math.floor(t*.7))});return}
 tabs(c,['전체 제안','검토 중','제외 항목'],30,102,1096,t,{selected:Math.floor(t*.75)%3});text(c,'항목',54,207,27,GOLD,600);text(c,'주요 내용',425,207,27,GOLD,600);text(c,'상태',958,207,27,GOLD,600);for(let j=0;j<4;j++){const yy=233+j*76,q=ease((t-j*.18)/.6);c.globalAlpha=q;line(c,44,yy+59,1095,yy+59,1,'#FFFFFF1C',1);c.fillStyle='#F2EEE744';c.fillRect(55,yy+15,245,9);c.fillRect(425,yy+15,362,9);panel(c,941,yy,153,45,{fill:'#3A2C1B',line:'#D4AF7C77',radius:8});text(c,['검토 중','제외 항목','검토 중','검토 중'][j],958,yy+30,23,GOLD)}c.globalAlpha=1;
}
function reportScene(c,p,t){
 // An HTML document, with no fabricated dates, equipment IDs or report metrics.
 panel(c,225,98,700,454,{fill:'#F2EEE7',line:'#D4AF7C99',radius:12});text(c,'Equipment Daily Report',254,150,34,'#172332',700);text(c,'주요 지표 요약',255,194,24,'#283747',600);
 for(let j=0;j<3;j++){const q=ease((t-j*.17)/.7);c.save();c.globalAlpha=q;panel(c,253+j*211,215,195,66,{fill:'#DBE0E3',line:'#BAC2C6',radius:5});c.fillStyle='#53616A55';c.fillRect(269+j*211,235,151,8);c.fillRect(269+j*211,258,99,6);c.restore()}
 text(c,'장비 현황',255,322,24,'#283747',600);graph(c,256,346,337,127,t-.4,28,'#577D86');text(c,'이슈 요약',632,322,24,'#283747',600);for(let j=0;j<5;j++){c.fillStyle='#53616A44';c.fillRect(632,350+j*25,238*ease((t-.5-j*.12)/.6),7)}
}
function mailScene(c,p,t){
 panel(c,85,106,980,417);text(c,'메일 발송',113,154,36,GOLD,600);const labels=['받는 사람','제목','본문'];labels.forEach((s,j)=>{const y=199+j*65;text(c,s,112,y,27,GOLD);text(c,j===0?'지정된 담당자':j===1?'장비 Daily Report':'완성된 보고서를 전달합니다.',285,y,29);line(c,111,y+20,1032,y+20,1,'#FFFFFF20',1)});panel(c,113,394,686,90);icon(c,'doc',135,415,42);text(c,'HTML 보고서',205,446,31);const sent=t>1.65;panel(c,833,412,202,70,{fill:sent?'#3B2D1E':'#D4AF7C',line:GOLD});text(c,sent?'발송 완료':'발송',864,457,29,sent?GOLD:INK,600);if(sent)icon(c,'check',989,435,22);if(sent){icon(c,'mail',790+clamp((t-1.65)/1.3)*290,315-clamp((t-1.65)/1.3)*60,37);flow(c,[816,347],[1102,256],t-1.65)}
}
function portalScene(c,p,t,{features=false}={}){
 const selected=features?Math.min(p.nav.length-1,Math.floor(clamp(t/(p.duration||3))*p.nav.length)):Math.floor(t*.85)%p.nav.length;rows(c,p.nav,28,101,387,t,{gap:79,selected});panel(c,444,104,681,433);fit(c,p.nav[selected],470,152,630,34,GOLD,600);
 if(selected===2){text(c,'TEM 쿼터 예약',470,204,27);for(let j=0;j<5;j++)for(let k=0;k<3;k++){const q=ease((t-j*.05-k*.1)/.5);panel(c,475+j*123,240+k*78,105,59,{fill:j===Math.floor(t)%5&&k===1?'#6C5027':'#172332',line:'#D4AF7C44',radius:8});c.fillStyle='#D4AF7C33';c.fillRect(489+j*123,261+k*78,76*q,6)}}
 else if(selected===3)reportSceneMini(c,470,190,620,310,t);
 else if(selected===4){icon(c,'mail',720,280,90);text(c,'주말 근무자 메일 발신',535,442,34);}
 else{for(let j=0;j<5;j++){const q=ease((t-j*.12)/.5);c.fillStyle='#F2EEE744';c.fillRect(474,219+j*60,372*q,11);if(selected===1){panel(c,910,207+j*60,167,36,{fill:'#263A37',line:'#D4AF7C55',radius:7});text(c,'장비 Status',925,232,21,GOLD)}line(c,472,250+j*60,1097,250+j*60,1,'#FFFFFF15',1)}}
}
function reportSceneMini(c,x,y,w,h,t){text(c,'Daily / Weekly Report',x,y+38,31,GOLD,600);graph(c,x+10,y+87,w-20,h-105,t,39)}
function micrograph(c,x,y,w,h,t,{plug=false,measure=false,suspect=false,rotate=false,photo=null}={}){
 c.save();box(c,x,y,w,h,12);c.clip();c.fillStyle='#333439';c.fillRect(x,y,w,h);c.translate(x+w/2,y+h/2);if(rotate)c.rotate((1-ease(t/1.4))*.05);
 if(photo){cover(c,photo,-w/2,-h/2,w,h);if(measure&&plug){const q=ease(t/.9),span=Math.min(w,h)*.76;line(c,-span/2,0,span/2,0,q,GOLD,2);line(c,0,-span/2,0,span/2,q,GOLD,2);[-1,1].forEach(sign=>{line(c,sign*span/2,-12,sign*span/2,12,q,GOLD,2);line(c,-12,sign*span/2,12,sign*span/2,q,GOLD,2)});c.globalAlpha=ease((t-.35)/.7);c.strokeStyle=suspect?AMBER:GOLD;c.lineWidth=suspect?3:2;box(c,-span/2-10,-span/2-10,span+20,span+20,6);c.stroke();c.globalAlpha=1} else if(measure)for(let j=0;j<6;j++){const xx=-w*.39+j*w*.145,yy=(hash(j+7)-.5)*h*.5,q=ease((t-j*.16)/.65);line(c,xx-20,yy,xx+28,yy,q,GOLD,2);line(c,xx,yy-24,xx,yy+24,q,GOLD,2)}}
 else if(plug){const cols=9,rows=6;for(let j=0;j<cols;j++)for(let k=0;k<rows;k++){const px=(j-(cols-1)/2)*w/cols,py=(k-(rows-1)/2)*h/rows,rx=w/cols*.25*(.84+.16*hash(j+k)),ry=h/rows*.33;const g=c.createRadialGradient(px,py,rx*.2,px,py,rx*1.8);g.addColorStop(0,'#A7A6A8');g.addColorStop(.5,'#747579');g.addColorStop(.65,'#393B40');g.addColorStop(1,'#69696C');c.fillStyle=g;c.beginPath();c.ellipse(px,py,rx,ry,0,0,Math.PI*2);c.fill();if(measure){const q=ease((t-.025*(j*rows+k))/.5);c.globalAlpha=q;line(c,px-rx,py,px+rx,py,1,GOLD,1.6);line(c,px,py-ry,px,py+ry,1,GOLD,1.6);if(suspect&&((j===3&&k===2)||(j===6&&k===4))){c.strokeStyle=AMBER;c.lineWidth=3;box(c,px-rx-5,py-ry-5,rx*2+10,ry*2+10,3);c.stroke()}c.globalAlpha=1}}}
 else{for(let j=0;j<12;j++){const xx=-w/2+j*w/11,bend=Math.sin(j*.5)*12;c.fillStyle=j%2?'#A4A4A9':'#5D5D62';c.beginPath();c.moveTo(xx-w*.023,-h/2);c.lineTo(xx+w*.023,-h/2);c.lineTo(xx+w*.034+bend,h/2);c.lineTo(xx-w*.036+bend,h/2);c.closePath();c.fill()}for(let j=0;j<1800;j++){c.fillStyle=hash(j)>.5?'#FFFFFF13':'#00000018';c.fillRect(-w/2+hash(j+33)*w,-h/2+hash(j+89)*h,1+hash(j+7)*2,1+hash(j+6)*2)}if(measure){for(let j=0;j<4;j++){const xx=-w*.32+j*w*.22,q=ease((t-j*.22)/.65);line(c,xx-20,-h*.22,xx+30,-h*.22,q,GOLD,2);line(c,xx+30,-h*.22,xx+30,h*.2,q,GOLD,2);line(c,xx-20,h*.2,xx+30,h*.2,q,GOLD,2);glow(c,xx+30,h*.2,15,.2)}}}
 const sx=-w/2+(t*.27%1)*w,g=c.createLinearGradient(sx-22,0,sx+22,0);g.addColorStop(0,'#FFFFFF00');g.addColorStop(.5,'#FFEACC22');g.addColorStop(1,'#FFFFFF00');c.fillStyle=g;c.fillRect(-w/2,-h/2,w,h);c.restore();c.strokeStyle='#D4AF7C66';c.lineWidth=2;box(c,x,y,w,h,12);c.stroke();
}
function measurementScene(c,p,t,{plug=false,tool=false}={}){
 micrograph(c,28,105,692,430,t,{plug,measure:!tool,rotate:!plug,photo:p.texture});panel(c,748,105,378,430);text(c,tool?'이미지 분석 Tool':plug?'CV 인식':'Raw data',770,151,29,GOLD,600);
 rows(c,tool?p.nav:plug?['계측선 분석','Plug 인식','번호 부여']:['R_NIT','S/W','CD','LS','Etch Depth','Sidewall Angle'],770,188,329,t-.2,{gap:tool?65:plug?100:53,icons:false,selected:Math.floor(t*.9)%(tool?p.nav.length:plug?3:6)});
}
function profileScene(c,p,t){
 tabs(c,['CD Profile','Space Profile'],28,102,1097,t,{selected:Math.floor(t*.75)%2});panel(c,28,176,344,360);rows(c,['Lot','Device','Plug ID'],50,205,300,t,{gap:86,icons:false,selected:Math.floor(t*.75)%3});panel(c,400,176,725,360);text(c,Math.floor(t*.75)%2?'Space Profile':'CD Profile',428,219,31,GOLD,600);graph(c,439,269,638,221,t-.2,51);
}
function plugDashboard(c,p,t){
 const selected=Math.floor(t*.8)%2;panel(c,28,106,627,431);text(c,'분석 대시보드',52,153,33,GOLD,600);tabs(c,['Profile 조회','결과 테이블'],53,181,576,t,{selected});if(selected===0)graph(c,71,257,537,240,t,71);else{['Plug','CD Profile','Space Profile'].forEach((s,j)=>text(c,s,73+j*175,282,23,GOLD,600));for(let k=0;k<4;k++){const y=311+k*48,q=ease((t-.08*k)/.55);line(c,72,y+28,602,y+28,1,'#FFFFFF15',1);c.fillStyle='#F2EEE755';c.fillRect(76,y+6,110*q,8);c.fillRect(253,y+6,125*q,8);c.fillRect(428,y+6,126*q,8)}}panel(c,687,106,438,431);text(c,'분석 챗봇',712,153,33,GOLD,600);panel(c,713,203,387,90,{fill:'#D4AF7C',line:GOLD});const s='분석 결과를 확인합니다.';fit(c,s.slice(0,Math.floor(clamp((t-.3)/1.6)*s.length)),732,258,350,28,INK,600);panel(c,713,323,387,162);rows(c,['Profile 조회','결과 테이블'],729,348,350,t-1,{gap:60,icons:false});
}
function researcherResult(c,p,t,{inline=false,monitor=false}={}){
 panel(c,28,105,599,432);text(c,'분석 결과 확인',52,151,33,GOLD,600);
 if(monitor)wafer(c,321,351,145,t,{seed:17});else graph(c,67,214,515,251,t,inline?41:12);
 panel(c,657,105,469,432);text(c,'의사결정 지원',681,151,33,GOLD,600);const labs=inline?['분석 결과 시각화','연계 공정 선별','분석 시간 단축']:['분석 결과 확인','분석 접근성 향상','더 빠른 의사결정'];rows(c,labs,682,203,417,t-.25,{gap:105,icons:false,selected:Math.min(2,Math.floor(clamp(t/p.duration)*3))});
}
function knowledgeResult(c,p,t){
 text(c,'공정 지식과 경험을 활용',37,143,35,GOLD,700);const labels=['과거 평가 이력','유사 사례','실패 사례'];labels.forEach((s,j)=>{const x=42+j*344,q=ease((t-j*.24)/.6);c.save();c.globalAlpha=q;panel(c,x,187,317,121);icon(c,'doc',x+22,219,42);fit(c,s,x+87,251,208,29);c.restore();flow(c,[x+157,308],[567,378],t,.15+j*.2)});panel(c,130,387,931,123,{fill:'#372918',line:GOLD});text(c,'Plan·Recipe 추천과 평가 의사결정 지원',161,459,37,GOLD,600);
}
function collaborationResult(c,p,t){
 panel(c,29,106,594,432);text(c,'핵심 정보 활용',53,152,34,GOLD,600);rows(c,['회의 자료','이슈 요약','관련 문서'],55,200,542,t,{gap:99,selected:Math.min(2,Math.floor(t*.75))});panel(c,655,106,470,432);text(c,'협업과 의사결정 지원',679,152,30,GOLD,600);
 for(let j=0;j<3;j++){const x=741+j*110,q=ease((t-.35-j*.25)/.6);c.save();c.globalAlpha=q;c.strokeStyle=GOLD;c.lineWidth=3;c.beginPath();c.arc(x,264,19,0,Math.PI*2);c.stroke();c.beginPath();c.arc(x,308,30,Math.PI,0);c.stroke();c.restore();flow(c,[622,255+j*57],[x,326],t,.35+j*.25)}text(c,'업무 판단에 활용',686,433,32,GOLD,600);
}
function expenseResult(c,p,t){
 text(c,'절감 기회와 주요 인사이트 확인',38,145,35,GOLD,600);rows(c,['경비 실적','장비 이력','절감 가능 항목'],39,189,439,t,{gap:94,selected:Math.min(2,Math.floor(t*.85))});panel(c,564,187,553,321,{fill:'#302418',line:GOLD});text(c,'분석 시간 단축',594,264,37,GOLD,600);text(c,'절감 기회 조기 발굴',594,350,34);text(c,'효율적인 예산 운영 지원',594,434,31);flow(c,[483,330],[559,330],t,.4);
}
function reportResult(c,p,t){
 panel(c,30,105,628,432,{fill:'#F2EEE7',line:GOLD});text(c,'Equipment Daily Report',55,160,34,'#172332',700);text(c,'완성된 보고서 검토',55,214,28,'#283747',600);graph(c,65,272,532,189,t,23,'#577D86');panel(c,692,105,431,432);text(c,'더 중요한 일에 집중',716,160,30,GOLD,600);rows(c,['보고서 검토','업무 판단','의사결정 지원'],716,217,383,t-.35,{gap:97,icons:false,selected:Math.min(2,Math.floor(t*.85))});
}
function portalResult(c,p,t){
 panel(c,30,106,418,431);text(c,'분산된 업무 환경',55,157,31,GOLD,600);rows(c,p.sources,55,196,368,t,{gap:71,icons:false,selected:Math.floor(t*.85)%4});panel(c,562,106,565,431,{fill:'#302418',line:GOLD});text(c,'하나의 포털',589,157,38,GOLD,700);rows(c,['Lot 조회 · 장비 Status','TEM 쿼터 예약','Daily/Weekly Report'],588,208,513,t-.3,{gap:89,icons:false,selected:Math.min(2,Math.floor(t*.85))});flow(c,[457,320],[558,320],t,.3);text(c,'업무 시간 단축',587,510,29,GOLD,600);
}
function measurementResult(c,p,t){
 micrograph(c,28,105,592,432,t,{photo:p.texture,measure:true,rotate:true});panel(c,650,105,477,432);text(c,'분석 환경 개선',675,154,35,GOLD,600);rows(c,['이미지당 측정 시간 단축','R_NIT 정확도 개선','S/W 정확도 개선'],675,210,423,t-.25,{gap:100,icons:false,selected:Math.min(2,Math.floor(t*.8))});
}
function completionScene(c,p,t,cut){
 if(p.key==='infra'){infraMetricScene(c,p,t);return}
 if(p.key==='thinfilm'){thinfilmAssetScene(c,p,t);return}
 if(p.key==='snm'){kParameterScene(c,p,t);return}
 if(p.key==='plug'){plugDashboard(c,p,t);return}
 if(p.key==='cubic'){portalResult(c,p,t);return}
 // Completed work stays legible, and its actual functional result remains in
 // motion. No unverified percentage, time, count or accuracy is displayed.
 if(p.key==='daily'){reportResult(c,p,t);return}
 if(p.key==='tcad'){measurementResult(c,p,t);return}
 if(p.key==='architecture'){knowledgeResult(c,p,t);return}
 if(p.key==='working'){collaborationResult(c,p,t);return}
 if(p.key==='expense'){expenseResult(c,p,t);return}
 if(p.key==='monitoring'){researcherResult(c,p,t,{monitor:true});return}
 researcherResult(c,p,t,{inline:p.key==='inline'});
}
function taskBody(c,p,i,t,cut){
 if(i===4)return completionScene(c,p,t,cut);
 const key=p.key;
 if(i===1){
  if(['infra','thinfilm'].includes(key))return unifiedScene(c,p,t);
  if(key==='working')return searchScene(c,p,t,'관련 회의 자료와 이슈를 찾아봅니다.');
  if(key==='architecture')return knowledgeScene(c,p,t);
  if(key==='monitoring')return searchScene(c,p,t,'필요한 공정 데이터를 자연어로 조회합니다.');
  if(key==='inline')return searchScene(c,p,t,'Spec-out 사례의 관련 정보를 분석합니다.');
  if(key==='snm')return searchScene(c,p,t,'Lot ID',p.nav.slice(1));
  if(['expense','daily'].includes(key))return connectionScene(c,p,t);
  if(key==='cubic')return portalScene(c,p,t);
  if(key==='tcad')return measurementScene(c,p,t,{tool:true});
  if(key==='plug')return measurementScene(c,p,t,{plug:true});
 }
 if(i===2){
  if(key==='infra')return connectionScene(c,p,t,{center:'데이터 연계'});
  if(key==='thinfilm')return thinfilmCharts(c,p,t);
  if(key==='working')return summaryScene(c,p,t);
  if(key==='architecture')return searchScene(c,p,t,'관련 평가 이력과 공정 경험을 찾아봅니다.');
  if(key==='monitoring')return connectionScene(c,p,t,{center:'통합 조회'});
  if(key==='inline')return connectionScene(c,p,t,{center:'GoodDocs 매핑'});
  if(key==='snm')return mapScene(c,p,t);
  if(key==='expense')return expenseInsights(c,p,t);
  if(key==='daily')return reportScene(c,p,t);
  if(key==='cubic')return portalScene(c,p,t,{features:true});
  if(key==='tcad')return measurementScene(c,p,t);
  if(key==='plug')return reviewScene(c,p,t,{plug:true});
 }
 if(i===3){
  if(key==='infra')return chartScene(c,p,t);
  if(key==='thinfilm')return shareScene(c,p,t);
  if(key==='working')return issueScene(c,p,t);
  if(key==='architecture')return recommendationScene(c,p,t);
  if(key==='monitoring')return mapScene(c,p,t,{monitor:true});
  if(key==='inline')return chartScene(c,p,t,{mode:'correlation'});
  if(key==='snm')return baselineScene(c,p,t);
  if(key==='expense')return reviewScene(c,p,t);
  if(key==='daily')return mailScene(c,p,t);
  if(key==='cubic')return portalScene(c,p,t);
  if(key==='tcad')return tcadComparison(c,p,t);
  if(key==='plug')return profileScene(c,p,t);
 }
}

export async function loadTaskAssets(spec,options={}){
 const images={},backgrounds={};const sections=spec.sections||spec.scenes||[];const paths=new Set();
 for(const s of sections){if(s.type!=='task')continue;if(s.reference_image)paths.add(s.reference_image);if(s.background)paths.add(s.background);for(const path of s.backgrounds||[])if(path)paths.add(typeof path==='string'?path:path.path);for(const cut of s.cuts||[])if(cut.background)paths.add(cut.background)}
 const nativeLoader=options.loadImage||spec.loadImage||globalThis.__showcaseLoadImage;
 await Promise.all([...paths].map(async path=>{let im;if(nativeLoader){im=await nativeLoader(options.basePath?`${options.basePath.replace(/\/$/,'')}/${path}`:path)}else if(typeof Image!=='undefined'){im=await new Promise((resolve,reject)=>{const image=new Image();image.onload=()=>resolve(image);image.onerror=()=>reject(new Error(`Missing task image: ${path}`));image.src=path})}else throw new Error('Native canvas requires loadTaskAssets(spec,{loadImage,basePath}) or preloaded assets.images.');images[path]=im;images[String(path).split('/').pop()]=im}));
 for(const s of sections.filter(s=>s.type==='task'))if(s.backgrounds)backgrounds[s.id]=s.backgrounds.map(path=>path?(typeof path==='string'?images[path]:{image:images[path.path],crop:path.crop}):null);
 return {images,backgrounds};
}

export function drawTaskLegacy(ctx,section,cut,localTime,cutDuration,assets={}){
 const cuts=section.cuts||[];let index=typeof cut==='number'?cut:cuts.indexOf(cut);if(index<0)index=Number(cut?.index??cut?.cut_index??0);const data=typeof cut==='number'?(cuts[index]||{}):(cut||{});index=clamp(index,0,4);const time=Math.max(0,Number(localTime)||0),duration=Math.max(.01,Number(cutDuration)||4);const p={...profile(section),duration,texture:assets?.microscopy?.[section.id]};
 ctx.save();photographicBackground(ctx,section,index,time,duration,assets);
 // Before is a full photographed work situation. The original problem is
 // conveyed by narration, without floating descriptive labels on the photo.
 if(index===0)beforeMotion(ctx,p,time,duration,assets,section);
 if(index>0){
  const {x,y,w,h,tilt}=afterLayouts[p.key];
  // Functions use a 1154x590 local UI coordinate space; scale once here.
  shell(ctx,p,(c)=>{c.save();c.scale(w/1154,h/590);taskBody(c,p,index,time,data);c.restore()},{x,y,w,h,tilt,t:time});
 }
 if(assets.drawTitles!==false||assets.drawCaptions===true)copy(ctx,data,time,assets);ctx.restore();
}

export const taskSceneContract={width:W,height:H,titleFontSize:68,captionFontSize:40,captionArea:null,captionsDefault:false,titleBandHeight:TITLE_BAND_HEIGHT,contentArea:[0,TITLE_BAND_HEIGHT,W,H-TITLE_BAND_HEIGHT],afterBezelCenterY:AFTER_BEZEL_CENTER_Y,afterLayouts,placementFunction:'getTaskPlacement(sectionOrKey,localTime)',beforePlacementUnchanged:true,deterministic:true,profiles:profiles.map(p=>p.key)};

const visualKit={W,H,INK,GOLD,CREAM,AMBER,FONT,clamp,ease,hash,shearedBounds,box,panel,text,fit,lines,glow,line,flow,icon,animatedBars,graph,rows,tabs,shell,imageEntry,cover,beforeMotion,connectionScene,unifiedScene,searchScene,summaryScene,knowledgeScene,recommendationScene,chartScene,thinfilmCharts,infraMetricScene,thinfilmAssetScene,tcadComparison,shareScene,issueScene,wafer,mapScene,baselineScene,kParameterScene,expenseInsights,reviewScene,reportScene,mailScene,portalScene,reportSceneMini,micrograph,measurementScene,profileScene,plugDashboard,researcherResult,knowledgeResult,collaborationResult,expenseResult,reportResult,portalResult,measurementResult,completionScene,taskBody};

/** Task-specific full-frame treatments; original title/narration timing stays in stage. */
export function drawTask(ctx,section,cut,localTime,cutDuration,assets={}){
 if(assets.legacyTaskComposition)return drawTaskLegacy(ctx,section,cut,localTime,cutDuration,assets);
 const cuts=section.cuts||[];let index=typeof cut==='number'?cut:cuts.indexOf(cut);
 if(index<0)index=Number(cut?.index??cut?.cut_index??0);
 index=clamp(index,0,4);const data=typeof cut==='number'?(cuts[index]||{}):(cut||{});
 const t=Math.max(0,Number(localTime)||0),d=Math.max(.01,Number(cutDuration)||4);
 const p={...profile(section),duration:d,texture:assets?.microscopy?.[section.id]};
 ctx.save();ctx.textBaseline="alphabetic";
 // Full-resolution approved task photograph replaces the tiny storyboard
 // background crops now exposed by the wider, monitor-free compositions.
 const photo=assets.backgrounds?.[section.id]?.[0];
 const photoAssets=index>0&&photo?{...assets,backgrounds:{...assets.backgrounds,[section.id]:{...assets.backgrounds[section.id],[index]:photo}}}:assets;
 photographicBackground(ctx,section,index,assets.freezeTaskBackground?0:t,d,photoAssets,index===0);
 if(index>0){const g=ctx.createLinearGradient(0,0,W,0);g.addColorStop(0,'#08080894');g.addColorStop(.5,'#08080880');g.addColorStop(1,'#08080857');ctx.fillStyle=g;ctx.fillRect(0,TITLE_BAND_HEIGHT,W,H-TITLE_BAND_HEIGHT);}
 // Reserve the retained persistent header. Each task owns its complete body.
 ctx.beginPath();ctx.rect(0,TITLE_BAND_HEIGHT,W,H-TITLE_BAND_HEIGHT);ctx.clip();
 const handled=drawEarlyTask(ctx,p,index,t,d,assets,section,visualKit)||drawLateTask(ctx,p,index,t,d,assets,section,visualKit);
 if(!handled)throw new Error('No bespoke visual treatment for '+p.key);
 if(assets.drawTitles!==false||assets.drawCaptions===true)copy(ctx,data,t,assets);
 ctx.restore();
}
export const taskDiversityContract={revision:8,width:W,height:H,bodyArea:[0,154,1920,926],commonAfterMonitor:false,approvedPhotosPreserved:true,photographicBeforeLabels:false,explicitSceneTime:true,get plans(){return [...earlyVisualPlan,...lateVisualPlan]}};
