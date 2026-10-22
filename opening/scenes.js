/* All motion comes from explicit seconds; no random state or CSS timelines.
 * Photos are conceptual scenery. Panels/icons/lines are abstract, without task UI or measurements. */
const W=1920,H=1080,DURATION=46;
const cuts=[0,3,7,12,17,22,28,35,42,46];
const narration=[
'R&D 현업에 AI를 더합니다.',
'더 나은 R&D 공정을 위한 변화가 시작됩니다.',
'현장의 경험과 AI 기술이 만나 새로운 해법을 만들어갑니다.',
'현업의 다양한 과제를 해결하기 위한 도전입니다.',
'현업의 문제를 AI로 해결하는 R&D 공정 AI Fast Track.',
'서로 다른 현업의 고민에서 12개의 AI Agent 과제가 시작됐습니다.',
'현업의 고민을 해결하기 위해 개발한 다양한 AI Agent를 살펴봅니다.',
'업무 효율을 높이고, 데이터 기반의 의사결정과 새로운 분석을 지원합니다.',
'지금부터 12개의 AI Agent 과제를 소개합니다.'
];
const layers=[...document.querySelectorAll('.scene')];
layers.forEach((node,i)=>node.querySelector('.caption').textContent=narration[i]);
const canvas=document.getElementById('visual'),ctx=canvas.getContext('2d',{alpha:false});
const buffer=document.createElement('canvas');buffer.width=W;buffer.height=H;
const c=buffer.getContext('2d',{alpha:false});
const images={};const clamp=(n,a=0,b=1)=>Math.max(a,Math.min(b,n));
const ease=n=>{n=clamp(n);return n*n*(3-2*n)};
const gold='#D4AF7C',warm='#F5D6A6',amber='#FFB347';
const hash=n=>{const v=Math.sin(n*127.1+311.7)*43758.5453;return v-Math.floor(v)};
function pathLine(points,stroke=gold,width=1,alpha=1){c.save();c.globalAlpha*=alpha;c.strokeStyle=stroke;c.lineWidth=width;c.beginPath();points.forEach((p,i)=>i?c.lineTo(...p):c.moveTo(...p));c.stroke();c.restore()}
function photo(name,t,mode='full'){
 const img=images[name];if(!img)return;
 c.save();const zoom=1.025+t*.004;let iw=W*zoom,ih=iw*img.height/img.width;if(ih<H*zoom){ih=H*zoom;iw=ih*img.width/img.height}
 c.drawImage(img,(W-iw)/2-t*1.7,(H-ih)/2,iw,ih);
 if(mode==='rightshade'){const g=c.createLinearGradient(740,0,1850,0);g.addColorStop(0,'#08080800');g.addColorStop(.44,'#0808089c');g.addColorStop(1,'#080808e8');c.fillStyle=g;c.fillRect(0,0,W,H)}
 c.restore();return{img,dx:(W-iw)/2-t*1.7,dy:(H-ih)/2,iw,ih};
}
function ambient(t,center=660){
 const g=c.createRadialGradient(center,550,60,center,550,960);g.addColorStop(0,'#6c451222');g.addColorStop(.5,'#29201619');g.addColorStop(1,'#08080800');c.fillStyle=g;c.fillRect(0,0,W,H);
 for(let i=0;i<95;i++){let x=hash(i+80)*W,y=hash(i+200)*900+Math.sin(t*.18+i)*8;let a=.08+hash(i)*.2;c.fillStyle=`rgba(245,214,166,${a})`;c.beginPath();c.arc(x,y,hash(i+35)*1.7+.4,0,Math.PI*2);c.fill()}
}
function ribbon(t,offset=0,alpha=1){
 c.save();c.globalAlpha*=alpha;for(let i=0;i<5;i++){
 const y=offset+i*16+Math.sin(t*.28+i*.15)*7;c.beginPath();c.moveTo(-100,850+y);c.bezierCurveTo(370,800+y,300,445+y,820,510+y);c.bezierCurveTo(1220,570+y,1410,390+y,2000,300+y);
 c.strokeStyle=i===2?warm:gold;c.lineWidth=i===2?2:1;c.shadowColor=amber;c.shadowBlur=i===2?16:5;c.globalAlpha=alpha*(i===2?.72:.26);c.stroke();
 }c.shadowBlur=0;
 const u=(t*.065+.2)%1,segment=u<.5?0:1,q=segment===0?u*2:(u-.5)*2;
 const pts=segment===0?[[-100,850+offset],[370,800+offset],[300,445+offset],[820,510+offset]]:[[820,510+offset],[1220,570+offset],[1410,390+offset],[2000,300+offset]];
 const b=(k)=>(1-q)**3*pts[0][k]+3*(1-q)**2*q*pts[1][k]+3*(1-q)*q*q*pts[2][k]+q**3*pts[3][k];
 c.globalAlpha=alpha*.7;c.fillStyle=warm;c.shadowColor=amber;c.shadowBlur=18;c.beginPath();c.arc(b(0),b(1),2.8,0,Math.PI*2);c.fill();c.restore();
}
function gather(t){
 const p=ease(t/1.35);c.save();
 for(let j=0;j<68;j++){const a=hash(j+307)*Math.PI*2,r0=780+hash(j+15)*370,r1=510+hash(j+74)*70,r=r0+(r1-r0)*p;
 const x=960+Math.cos(a)*r,y=485+Math.sin(a)*r*.46;c.fillStyle=`rgba(245,214,166,${(.12+hash(j)*.38)*(.5+.5*p)})`;c.beginPath();c.arc(x,y,.8+hash(j+13)*1.4,0,Math.PI*2);c.fill()}
 for(let j=0;j<4;j++){const left=j%2===0,top=j<2,x0=left?100:1820,x1=left?470:1450,y=top?243:750;pathLine([[x0,y+(1-p)*(top?-120:120)],[x0+(x1-x0)*p,y]],gold,1,.25)}c.restore();
}
function wafer(x,y,r,t,alpha=1){
 c.save();c.globalAlpha*=alpha;c.translate(x,y);c.rotate(-.09);c.scale(1,.43);
 const g=c.createRadialGradient(-r*.33,-r*.47,10,0,0,r);g.addColorStop(0,'#9c76444d');g.addColorStop(.62,'#29221c');g.addColorStop(1,'#101010');
 c.fillStyle=g;c.beginPath();c.arc(0,0,r,0,Math.PI*2);c.fill();c.strokeStyle=gold;c.lineWidth=2;c.stroke();c.clip();
 for(let z=-r;z<=r;z+=38){pathLine([[z,-r],[z,r]],gold,1,.24);pathLine([[-r,z],[r,z]],gold,1,.24)}
 for(let i=0;i<26;i++){const x1=(hash(i+50)*2-1)*r,y1=(hash(i+60)*2-1)*r;c.fillStyle='#D4AF7C18';c.fillRect(x1,y1,32,31)}
 c.strokeStyle='#F5D6A6a0';c.lineWidth=2;c.beginPath();c.arc(0,0,r-11,-2.65+t*.022,-.8+t*.022);c.stroke();c.restore();
}
function icon(type,x,y,size,t){
 c.save();c.translate(x,y);c.strokeStyle=warm;c.lineWidth=1.6;c.globalAlpha*=.86;
 if(type%4===0){c.beginPath();c.arc(0,0,size*.35,0,Math.PI*2);c.stroke();for(let j=-2;j<=2;j++){let p=j*size*.105;const len=Math.sqrt((size*.35)**2-p*p);pathLine([[p,-len],[p,len]],gold);pathLine([[-len,p],[len,p]],gold)}}
 if(type%4===1){let pts=[[-.32,-.24],[.28,-.28],[-.21,.26],[.29,.24]].map(p=>p.map(n=>n*size));pathLine([pts[0],pts[1],pts[3],pts[2],pts[0]],gold);pathLine([pts[0],pts[3]],gold,1,.6);for(let p of pts){c.beginPath();c.arc(...p,size*.056,0,Math.PI*2);c.stroke()}}
 if(type%4===2){for(let j=0;j<3;j++){let a=size*(.55-j*.13);c.strokeRect(-a/2,-a/2,a,a)}pathLine([[-size*.35,0],[size*.35,0]],gold,1,.5)}
 if(type%4===3){for(let j=0;j<3;j++){c.beginPath();c.ellipse(0,(j-1)*size*.19,size*.34,size*.09,0,0,Math.PI*2);c.stroke()}pathLine([[-size*.34,-size*.19],[-size*.34,size*.19]],gold);pathLine([[size*.34,-size*.19],[size*.34,size*.19]],gold)}
 c.restore();
}
function panel(x,y,w,h,type,t,alpha=1,photoName){
 c.save();c.globalAlpha*=alpha;c.translate(x,y);
 c.fillStyle='#1A1A1F8c';c.fillRect(0,0,w,h);
 if(photoName){c.save();c.beginPath();c.rect(1,1,w-2,h-2);c.clip();const img=images[photoName];if(img){c.globalAlpha*=.64;c.drawImage(img,0,0,img.width,img.height,-w*.2,-h*.15,w*1.4,h*1.4)}c.restore()}
 c.strokeStyle='#D4AF7C83';c.lineWidth=1;c.strokeRect(0,0,w,h);pathLine([[0,23],[0,0],[32,0]],warm,1.5,.8);pathLine([[w-30,h],[w,h],[w,h-23]],gold,1.5,.8);
 if(!photoName)icon(type,w/2,h/2,Math.min(w,h)*.75,t);
 c.restore();
}
function geometry(i,t){
 c.fillStyle='#080808';c.fillRect(0,0,W,H);
 if(i===0){photo('dome',t);const g=c.createLinearGradient(0,0,0,850);g.addColorStop(0,'#08080822');g.addColorStop(.38,'#08080855');g.addColorStop(1,'#08080800');c.fillStyle=g;c.fillRect(0,0,W,H)}
 if(i===1){const p=photo('wafer',t,'rightshade'); // Move only the pictured head by a few pixels; no invented process screen.
  if(p){c.save();c.translate(Math.sin(t*.5)*7,0);c.beginPath();c.moveTo(155,-40);c.lineTo(730,-40);c.lineTo(730,153);c.lineTo(628,180);c.lineTo(609,248);c.lineTo(548,312);c.lineTo(490,329);c.lineTo(432,320);c.lineTo(386,290);c.lineTo(370,188);c.lineTo(155,134);c.closePath();c.clip();c.drawImage(p.img,p.dx,p.dy,p.iw,p.ih);c.restore();}}
 if(i===2){photo('researcher',t,'rightshade');pathLine([[1015,275],[1015,720]],gold,1,.45)}
 if(i===3){ambient(t);wafer(560,704,464,t);ribbon(t,110,.48);
  [[143,286,288,185,'wafer'],[495,196,267,176,'researcher'],[835,306,257,183,null]].forEach((p,j)=>panel(p[0],p[1]-ease(t/5)*12,p[2],p[3],j,t,ease((t-j*.28)/.8),p[4]));
  for(let j=0;j<3;j++){pathLine([[280+j*285,490],[560,695]],gold,1,.26)}
 }
 if(i===4){ambient(t,960);ribbon(t,60,.7);ribbon(t,-310,.38);wafer(960,760,760,t,.1);const g=c.createRadialGradient(960,488,90,960,488,610);g.addColorStop(0,'#080808bd');g.addColorStop(1,'#08080800');c.fillStyle=g;c.fillRect(0,0,W,H);gather(t);pathLine([[510,234],[510+900*ease(t/.8),234]],gold,1,.5)}
 if(i===5){ambient(t);const unfold=.84+.16*ease(t/1.25);for(let row=0;row<3;row++)for(let col=0;col<4;col++){let j=row*4+col;panel(566+(126+col*228-566)*unfold,514+(249+row*187-514)*unfold,196,151,j,t,ease((t-j*.07)/.7))}pathLine([[1060,240],[1060,827]],gold,1,.35)}
 if(i===6){ambient(t);wafer(558,709,500,t);ribbon(t,90,.64);
  panel(164+Math.sin(t*.23)*8,250,290,191,0,t,1,'wafer');panel(533+Math.sin(t*.2)*11,179,283,182,1,t,1);panel(820+Math.sin(t*.3)*6,429,231,166,2,t,1);
  c.save();c.strokeStyle=gold;c.lineWidth=1;c.globalAlpha=.4;c.beginPath();c.ellipse(590,609,484,264,-.1,-3.14,0);c.stroke();c.restore();}
 if(i===7){ambient(t,730);const reveal=ease(t/4);for(let j=0;j<9;j++){
  const h=(72+j*j*6.2)*ease((t-j*.15)/1.4);const g=c.createLinearGradient(0,840-h,0,840);g.addColorStop(0,'#D4AF7C78');g.addColorStop(1,'#D4AF7C0c');c.fillStyle=g;c.fillRect(151+j*99,840-h,55,h);pathLine([[151+j*99,840-h],[206+j*99,840-h]],gold,1,.7)
 }c.save();c.beginPath();c.moveTo(120,805);c.bezierCurveTo(470,787,623,561,1040,266);c.strokeStyle=warm;c.lineWidth=3;c.shadowColor=amber;c.shadowBlur=22;c.setLineDash([1530]);c.lineDashOffset=1530*(1-reveal);c.stroke();c.restore();
 pathLine([[1007,278],[1040,266],[1029,302]],warm,2,reveal); // No axis, units or data claims: only the approved abstract direction.
 }
 if(i===8){photo('wafer',t*.7);c.fillStyle='#08080870';c.fillRect(0,0,W,H);const g=c.createRadialGradient(960,490,220,960,490,880);g.addColorStop(0,'#08080880');g.addColorStop(1,'#08080800');c.fillStyle=g;c.fillRect(0,0,W,H)}
 const vignette=c.createRadialGradient(960,490,360,960,490,1120);vignette.addColorStop(0,'#08080800');vignette.addColorStop(1,'#080808b0');c.fillStyle=vignette;c.fillRect(0,0,W,H);
}
window.__seek=function(time){
 time=clamp(time,0,DURATION-1/30);let i=cuts.findIndex((n,j)=>j<9&&time>=n&&time<cuts[j+1]);if(i<0)i=8;const local=time-cuts[i],blend=i===0?1:ease(local/.32);
 ctx.fillStyle='#080808';ctx.fillRect(0,0,W,H);
 if(i>0&&blend<1){geometry(i-1,cuts[i]-cuts[i-1]-.0333);ctx.drawImage(buffer,0,0)}
 geometry(i,local);ctx.globalAlpha=blend;ctx.drawImage(buffer,0,0);ctx.globalAlpha=1;
 layers.forEach((node,j)=>{
  const shown=j===i||(j===i-1&&blend<1);node.style.display=shown?'block':'none';node.style.opacity=j===i?blend:1-blend;
  const heading=node.querySelector('.headline')||node.querySelector('.title');if(heading)heading.style.transform=`translateY(${j===i?(1-ease(local/.72))*11:0}px)`;
 });
 document.getElementById('caption').textContent=narration[i];
 document.querySelectorAll('.benefit').forEach((el,j)=>{el.style.opacity=ease((local-j*.26)/.68);el.style.transform=`translateX(${(1-ease((local-j*.26)/.68))*15}px)`});
 document.getElementById('scrub').value=time;document.getElementById('time').textContent=`${time.toFixed(1)} / 46.0`;
 window.__state={time,cut:i+1,local,abstract_frame_count:i===5?12:i===6?3:i===3?3:0};
};
function fit(){document.getElementById('stage').style.transform=`scale(${Math.min(innerWidth/W,innerHeight/H)})`}
window.addEventListener('resize',fit);fit();
let playing=false,anchor=0,current=0,audio=null;
if(new URLSearchParams(location.search).has('render'))document.getElementById('controls').style.display='none';
document.getElementById('scrub').addEventListener('input',e=>{current=Number(e.target.value);window.__seek(current);if(audio)audio.currentTime=current;anchor=performance.now()-current*1000});
document.getElementById('play').addEventListener('click',async()=>{playing=!playing;document.getElementById('play').textContent=playing?'일시정지':'재생';if(!audio){audio=new Audio('narration/mix.wav');audio.addEventListener('error',()=>{})}if(playing){if(current>=DURATION-.05)current=0;anchor=performance.now()-current*1000;audio.currentTime=current;await audio.play().catch(()=>{});tick()}else audio.pause()});
function tick(){if(!playing)return;current=Math.min((performance.now()-anchor)/1000,DURATION-1/30);window.__seek(current);if(current>=DURATION-1/30){playing=false;document.getElementById('play').textContent='재생';audio.pause()}else requestAnimationFrame(tick)}
window.__ready=Promise.all(['dome','wafer','researcher'].map(name=>new Promise((resolve,reject)=>{const img=new Image;img.onload=()=>{images[name]=img;resolve()};img.onerror=()=>reject(new Error(`Missing image assets/${name}.png`));img.src=`assets/${name}.png`}))).then(()=>document.fonts.ready).then(()=>{window.__seek(0);return true});
