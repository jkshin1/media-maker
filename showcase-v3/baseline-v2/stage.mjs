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
 ctx.font='400 48px Noto';ctx.fillStyle='#F5D6A6';ctx.fillText(section.owner||'',174,y+lines.length*size*1.38+48);
 ctx.globalAlpha=1;
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
function paintFrame(ctx,t,timeline,spec,assets){
 const entry=timeline.entries.find(e=>t>=e.start&&t<e.end)||timeline.entries.at(-1);const section=spec.sections.find(s=>s.id===entry.section_id);
 const local=Math.max(0,t-entry.start),dur=entry.end-entry.start;ctx.save();ctx.fillStyle='#080808';ctx.fillRect(0,0,W,H);
 const cut=entry.cut_index==null?section.cuts[0]:section.cuts[entry.cut_index];
 if(entry.kind==='title')drawTitle(ctx,section,local,dur,assets);
 else if(section.type==='task')drawTask(ctx,section,cut,local,dur,assets);
 else drawHero(ctx,section,cut,local,dur,assets);
 let captions=[];
 // User revision: narration captions are disabled; storyboard titles and core UI text remain.
 if(spec.presentation_overrides?.narration_captions!==false&&entry.kind!=='title'&&section.type!=='summary')captions=drawCaption(ctx,entry.caption||cut?.caption||'');
 if(section.type==='task'&&entry.kind!=='title'){
  ctx.fillStyle='#080808e0';ctx.fillRect(0,0,W,154);ctx.fillStyle=CREAM;ctx.font='700 62px Noto';ctx.textBaseline='top';ctx.textAlign='left';ctx.fillText(cut.title,108,55);
  ctx.strokeStyle='#D4AF7C90';ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(108,139);ctx.lineTo(1812,139);ctx.stroke();
 }
 // Source storyboard score values remain hidden in the representative card.
 if(section.type==='ending'&&entry.cut_index===5&&local>=.12){const q=1-Math.min(1,Math.max(0,(local-.12)/.68));ctx.fillStyle='#14212A';ctx.fillRect(1572+170*q*q*q,74+26*q*q*q,76,176);}
 ctx.restore();return{entry,section,cut,captions};
}
export function drawFrame(ctx,t,timeline,spec,assets){
 const entry=timeline.entries.find(e=>t>=e.start&&t<e.end)||timeline.entries.at(-1),local=t-entry.start;
 const state=paintFrame(ctx,t,timeline,spec,assets);
 if(entry.start>0&&local<.45&&assets.transitionCanvas){
  const buffer=assets.transitionCanvas,bctx=buffer.getContext('2d');
  const current=buffer;
  bctx.clearRect(0,0,W,H);bctx.drawImage(ctx.canvas,0,0);
  paintFrame(ctx,entry.start-1/timeline.fps,timeline,spec,assets);
  const p=Math.min(1,Math.max(0,local/.45));ctx.save();ctx.globalAlpha=p*p*(3-2*p);ctx.drawImage(current,0,0);ctx.restore();
 }
 return state;
}
