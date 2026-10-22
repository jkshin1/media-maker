import {drawTask} from './task-scenes.js';
import {drawHero} from './hero-scenes.js';

export const W=1920,H=1080;
export const GOLD='#D4AF7C',CREAM='#F2EEE7';
export function wrap(ctx,text,width){
 const parts=String(text||'').split(/\s+/), lines=[];let line='';
 for(const part of parts){const trial=line?line+' '+part:part;if(ctx.measureText(trial).width>width&&line){lines.push(line);line=part}else line=trial}if(line)lines.push(line);
 return lines.flatMap(l=>{if(ctx.measureText(l).width<=width)return[l];const a=[];let b='';for(const ch of l){if(ctx.measureText(b+ch).width>width&&b){a.push(b);b=''}b+=ch}if(b)a.push(b);return a});
}
export function textBlock(ctx,text,x,y,width,size,lineHeight,color=CREAM,weight=400,align='left'){
 ctx.save();ctx.font=`${weight} ${size}px Noto`;ctx.fillStyle=color;ctx.textAlign=align;ctx.textBaseline='top';
 const lines=wrap(ctx,text,width);lines.forEach((l,i)=>ctx.fillText(l,x,y+i*lineHeight));ctx.restore();return lines.length*lineHeight;
}
function background(ctx,img,t){if(!img)return;const scale=Math.max(W/img.width,H/img.height)*1.035;ctx.drawImage(img,(W-img.width*scale)/2+Math.sin(t*.23)*6,(H-img.height*scale)/2,img.width*scale,img.height*scale)}
export function drawTitle(ctx,section,t,duration,assets){
 background(ctx,assets.backgrounds?.[section.id]?.[0]||assets.images?.[section.reference_image],t);
 const g=ctx.createLinearGradient(0,0,W,0);g.addColorStop(0,'#080808ed');g.addColorStop(.58,'#080808e3');g.addColorStop(1,'#0808088a');ctx.fillStyle=g;ctx.fillRect(0,0,W,H);
 const fade=Math.min(1,t/.32);ctx.globalAlpha=fade;
 ctx.strokeStyle=GOLD;ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(130,258);ctx.lineTo(130,258+Math.min(420,t*620));ctx.stroke();
 ctx.font='700 36px Noto';ctx.fillStyle=GOLD;ctx.textBaseline='top';ctx.fillText('R&D 공정  |  AI FAST TRACK',174,231);
 let size=84;ctx.font=`700 ${size}px Noto`;let lines=wrap(ctx,section.title,1530);while(lines.length>3&&size>70){size-=2;ctx.font=`700 ${size}px Noto`;lines=wrap(ctx,section.title,1530)}
 const y=384-(lines.length-2)*44;lines.forEach((l,i)=>{ctx.fillStyle=CREAM;ctx.fillText(l,174,y+i*(size*1.38))});
 ctx.font='400 48px Noto';ctx.fillStyle='#F5D6A6';ctx.fillText([section.team,section.owner].filter(Boolean).join('  |  '),174,y+lines.length*size*1.38+48);
 ctx.globalAlpha=1;
}
export const taskIntroductionContract={revision:9,firstPhotoOnly:true,sameContinuousPhoto:true,maxSeconds:2,standaloneTitleSeconds:0,addsTimelineSilence:false,persistentHeaderAlwaysVisible:true,bodyArea:[0,154,W,H-154],humanWarp:false};
/** Title exposure is part of the voiced first photograph, not a separate shot. */
export function drawTaskIntroduction(ctx,section,t,duration){
 const end=Math.min(taskIntroductionContract.maxSeconds,Math.max(.01,duration));
 const fadeStart=Math.max(.24,end-.68),enter=Math.min(.22,end*.2);
 const opacity=Math.min(1,Math.max(0,t/enter))*Math.min(1,Math.max(0,(end-t)/(end-fadeStart)));
 if(opacity<=0)return {visible:false,opacity:0,end_seconds:end,records:[]};
 ctx.save();ctx.beginPath();ctx.rect(0,154,W,H-154);ctx.clip();ctx.globalAlpha=opacity;
 const gradient=ctx.createLinearGradient(0,0,W,0);gradient.addColorStop(0,'#080808e8');gradient.addColorStop(.6,'#080808cf');gradient.addColorStop(1,'#08080815');ctx.fillStyle=gradient;ctx.fillRect(0,154,W,H-154);
 ctx.textBaseline='top';ctx.textAlign='left';let size=84;ctx.font=`700 ${size}px Noto`;let titleLines=wrap(ctx,section.title,1530);
 while(titleLines.length>3&&size>64){size-=2;ctx.font=`700 ${size}px Noto`;titleLines=wrap(ctx,section.title,1530)}
 if(titleLines.length>3)throw new Error('First-photo task introduction exceeds three lines: '+section.title);
 const lineHeight=size*1.24,blockHeight=titleLines.length*lineHeight+88,y=154+(H-154-blockHeight)/2,records=[];
 ctx.strokeStyle=GOLD;ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(130,y);ctx.lineTo(130,y+blockHeight);ctx.stroke();
 for(let i=0;i<titleLines.length;i++){ctx.fillStyle=CREAM;ctx.fillText(titleLines[i],174,y+i*lineHeight);records.push({role:'intro_task_title',text:titleLines[i],x:174,y:y+i*lineHeight,font_size:size})}
 const identity=[section.team,section.owner].filter(Boolean).join('  |  ');ctx.font='400 46px Noto';ctx.fillStyle=GOLD;ctx.fillText(identity,174,y+titleLines.length*lineHeight+24);records.push({role:'intro_team_owner',text:identity,x:174,y:y+titleLines.length*lineHeight+24,font_size:46});
 ctx.restore();return {visible:true,opacity,end_seconds:end,records};
}
export function drawCaption(ctx,text){
 if(!text)return[];ctx.save();let size=40;ctx.font=`400 ${size}px Noto`;let lines=wrap(ctx,text,1680);
 while(lines.length>2&&size>34){size-=1;ctx.font=`400 ${size}px Noto`;lines=wrap(ctx,text,1680)}
 if(lines.length>2)throw new Error('Caption exceeds two lines: '+text);
 const h=lines.length*(size*1.4)+24,y=1010-h;
 const gradient=ctx.createLinearGradient(0,862,0,H);gradient.addColorStop(0,'#08080800');gradient.addColorStop(.3,'#080808d9');gradient.addColorStop(1,'#080808fa');ctx.fillStyle=gradient;ctx.fillRect(0,852,W,H-852);
 ctx.strokeStyle='#D4AF7C75';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(120,y-15);ctx.lineTo(1800,y-15);ctx.stroke();
 ctx.textAlign='center';ctx.textBaseline='top';ctx.fillStyle=CREAM;lines.forEach((l,i)=>ctx.fillText(l,W/2,y+i*size*1.4));ctx.restore();
 return lines.map((l,i)=>({text:l,left:120,right:1800,top:y+i*size*1.4,bottom:y+(i+1)*size*1.4,font_size:size}));
}

export const taskHeaderContract={width:W,height:H,taskOnly:true,band:[0,0,W,154],leftRegion:[108,8,930,138],rightRegion:[1110,8,702,138],cutTitleFontSize:62,taskTitleFontSize:29,ownerFontSize:27,maxTaskTitleLines:3,persistentDuringTitleAndBody:true,drawAfterDissolve:true,changesNonTaskPixels:false};
const headerCache=new WeakMap();
function balancedHeaderLines(ctx,value,width){
 const lines=wrap(ctx,value,width),words=String(value||'').trim().split(/\s+/);
 if(lines.length!==2)return lines;
 let best=lines,score=Infinity;
 for(let i=1;i<words.length;i++){
  const candidate=[words.slice(0,i).join(' '),words.slice(i).join(' ')],sizes=candidate.map(s=>ctx.measureText(s).width);
  if(sizes.some(v=>v>width))continue;
  const difference=Math.abs(sizes[0]-sizes[1]);if(difference<score){score=difference;best=candidate;}
 }
 return best;
}
function headerTextRecord(ctx,text,x,y,size,weight,align,role){
 ctx.font=`${weight} ${size}px Noto`;ctx.textAlign='left';ctx.textBaseline='top';
 const m=ctx.measureText(text),origin=align==='right'?x-m.width:x;
 // Advance width is conservative across mixed Korean/Latin font runs; some
 // native runtimes report ink-right bounds for only the last shaped run.
 const left=origin-Math.max(0,m.actualBoundingBoxLeft||0),right=origin+Math.max(m.width,m.actualBoundingBoxRight||0);
 return {role,text,x,y,font_size:size,weight,align,font:`${weight} ${size}px Noto`,bounds:{left,right,top:y-(m.actualBoundingBoxAscent??0),bottom:y+(m.actualBoundingBoxDescent??size*1.3)}};
}
/** Measure exactly the lines drawn by the persistent task header. */
export function measureTaskHeader(ctx,section,cut={},kind='cut'){
 if(section.type!=='task')return null;
 ctx.save();const tagRight=1812,tagWidth=702,bandHeight=154,records=[];
 let tagSize=29,tagLines;
 do{ctx.font=`700 ${tagSize}px Noto`;tagLines=balancedHeaderLines(ctx,section.title,tagWidth);if(tagLines.length<=3)break;tagSize--;}while(tagSize>=26);
 if(tagLines.length>3)throw new Error('Persistent task title exceeds the header: '+section.title);
 const tagLineHeight=tagSize*1.22,ownerY=tagLines.length*tagLineHeight+8;
 const tagRecords=tagLines.map((s,i)=>headerTextRecord(ctx,s,tagRight,i*tagLineHeight,tagSize,700,'right','task_title'));
 tagRecords.push(headerTextRecord(ctx,[section.team,section.owner].filter(Boolean).join(' · '),tagRight,ownerY,27,400,'right','owner'));
 const tagTop=Math.min(...tagRecords.map(r=>r.bounds.top)),tagBottom=Math.max(...tagRecords.map(r=>r.bounds.bottom));
 const tagOffset=(bandHeight-(tagBottom-tagTop))/2-tagTop;
 for(const r of tagRecords){r.y+=tagOffset;r.bounds.top+=tagOffset;r.bounds.bottom+=tagOffset;records.push(r);}
 let cutLines=[],cutSize=62;
 if(kind!=='title'){
  let relative;
  do{
   ctx.font=`700 ${cutSize}px Noto`;cutLines=wrap(ctx,cut.title||'',930);
   relative=cutLines.map((s,i)=>headerTextRecord(ctx,s,108,i*cutSize*1.13,cutSize,700,'left','cut_title'));
   const top=Math.min(...relative.map(r=>r.bounds.top)),bottom=Math.max(...relative.map(r=>r.bounds.bottom));
   if(cutLines.length<=2&&bottom-top<=138)break;cutSize-=2;
  }while(cutSize>=46);
  if(cutLines.length>2)throw new Error('Cut title exceeds the persistent header: '+cut.title);
  const top=Math.min(...relative.map(r=>r.bounds.top)),bottom=Math.max(...relative.map(r=>r.bounds.bottom));
  const offset=cutLines.length===1?55:(bandHeight-(bottom-top))/2-top;
  for(const r of relative){r.y+=offset;r.bounds.top+=offset;r.bounds.bottom+=offset;records.push(r);}
 }
 for(const r of records){const left=r.role==='cut_title'?104:1106,right=r.role==='cut_title'?1042:1816;if(r.bounds.top<0||r.bounds.bottom>154||r.bounds.left<left||r.bounds.right>right)throw new Error('Persistent header text is outside its band: '+r.text);}
 ctx.restore();return {section_id:section.id,kind,task_title:section.title,team:section.team||'',owner:section.owner||'',cut_title:kind==='title'?null:cut.title||'',task_title_lines:tagLines,cut_title_lines:cutLines,task_title_font_size:tagSize,cut_title_font_size:kind==='title'?null:cutSize,owner_font_size:27,band:[0,0,W,bandHeight],left_region:[108,8,930,138],right_region:[1110,8,702,138],records};
}
export function drawTaskHeader(ctx,section,cut={},kind='cut'){
 if(section.type!=='task')return null;
 let cache=headerCache.get(ctx);if(!cache){cache=new Map();headerCache.set(ctx,cache);}
 const key=JSON.stringify([section.id,section.title,section.team,section.owner,kind,kind==='title'?'':cut.title]);
 let layout=cache.get(key);if(!layout){layout=measureTaskHeader(ctx,section,cut,kind);cache.set(key,layout);}
 ctx.save();ctx.globalAlpha=1;
 // The opaque band also prevents the outgoing cut's text from showing through
 // when the new task identity replaces it at the start of a dissolve.
 ctx.fillStyle='#080808';if(kind==='title')ctx.fillRect(1078,0,W-1078,154);else ctx.fillRect(0,0,W,154);
 ctx.strokeStyle='#D4AF7C90';ctx.lineWidth=1;
 if(kind!=='title'){ctx.beginPath();ctx.moveTo(108,153);ctx.lineTo(1812,153);ctx.stroke();}
 ctx.beginPath();ctx.moveTo(1074,24);ctx.lineTo(1074,130);ctx.stroke();
 ctx.textBaseline='top';for(const r of layout.records){ctx.font=r.font;ctx.textAlign=r.align;ctx.fillStyle=r.role==='owner'?GOLD:CREAM;ctx.fillText(r.text,r.x,r.y);}
 ctx.restore();return layout;
}
function paintFrame(ctx,t,timeline,spec,assets,legacyTaskTitle=false){
 const entry=timeline.entries.find(e=>t>=e.start&&t<e.end)||timeline.entries.at(-1);const section=spec.sections.find(s=>s.id===entry.section_id);
 const local=Math.max(0,t-entry.start),dur=entry.end-entry.start;ctx.save();ctx.fillStyle='#080808';ctx.fillRect(0,0,W,H);
 const cut=entry.cut_index==null?section.cuts[0]:section.cuts[entry.cut_index];
 if(entry.kind==='title')drawTitle(ctx,section,local,dur,assets);
 else if(section.type==='task')drawTask(ctx,section,cut,local,dur,assets);
 else drawHero(ctx,section,cut,local,dur,assets);
 const taskIntroduction=section.type==='task'&&entry.cut_index===0?drawTaskIntroduction(ctx,section,local,dur):null;
 let captions=[];
 // User revision: narration captions are disabled; storyboard titles and core UI text remain.
 if(spec.presentation_overrides?.narration_captions!==false&&entry.kind!=='title'&&section.type!=='summary')captions=drawCaption(ctx,entry.caption||cut?.caption||'');
 if(legacyTaskTitle&&section.type==='task'&&entry.kind!=='title'){
  ctx.fillStyle='#080808e0';ctx.fillRect(0,0,W,154);ctx.fillStyle=CREAM;ctx.font='700 62px Noto';ctx.textBaseline='top';ctx.textAlign='left';ctx.fillText(cut.title,108,55);
  ctx.strokeStyle='#D4AF7C90';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(108,139);ctx.lineTo(1812,139);ctx.stroke();
 }
 // Source storyboard score values remain hidden in the representative card.
 if(section.type==='ending'&&entry.cut_index===5&&local>=.12){const q=1-Math.min(1,Math.max(0,(local-.12)/.68));ctx.fillStyle='#14212A';ctx.fillRect(1572+170*q*q*q,181.5+26*q*q*q,76,176);}
 ctx.restore();return{entry,section,cut,captions,task_introduction:taskIntroduction};
}
export function drawFrame(ctx,t,timeline,spec,assets){
 const entry=timeline.entries.find(e=>t>=e.start&&t<e.end)||timeline.entries.at(-1),local=t-entry.start;
 const state=paintFrame(ctx,t,timeline,spec,assets);
 if(entry.start>0&&local<.45&&assets.transitionCanvas){
  const buffer=assets.transitionCanvas,bctx=buffer.getContext('2d');
  const current=buffer;
  bctx.clearRect(0,0,W,H);bctx.drawImage(ctx.canvas,0,0);
  // Hero transitions retain their original outgoing composition. Task identity
  // is drawn only after the composite, so it never leaks into a hero scene.
  paintFrame(ctx,entry.start-1/timeline.fps,timeline,spec,assets,true);
  const p=Math.min(1,Math.max(0,local/.45));ctx.save();ctx.globalAlpha=p*p*(3-2*p);ctx.drawImage(current,0,0);ctx.restore();
 }
 state.task_header=drawTaskHeader(ctx,state.section,state.cut,entry.kind);return state;
}
