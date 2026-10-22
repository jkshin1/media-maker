/* Revision 2 follows the original storyboard photography.
 * Assets have no text or real task UI. Copy is rendered exclusively in code.
 * Explicit scene seconds drive all motion, allowing repeatable frames. */
const W=1920,H=1080,DURATION=46,cuts=[0,3,7,12,17,22,28,35,42,46];
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
const layers=[...document.querySelectorAll('.scene')],images={};
const canvas=document.getElementById('visual'),ctx=canvas.getContext('2d',{alpha:false});
const buffer=document.createElement('canvas');buffer.width=W;buffer.height=H;
const c=buffer.getContext('2d',{alpha:false});
const clamp=(n,a=0,b=1)=>Math.max(a,Math.min(b,n));
const ease=n=>{n=clamp(n);return n*n*(3-2*n)};
const hash=n=>{const v=Math.sin(n*127.1+311.7)*43758.5453;return v-Math.floor(v)};
const gold='#D4AF7C',warm='#F5D6A6',amber='#FFB347';
function photo(i,t){
 const img=images[i],localDuration=cuts[i+1]-cuts[i],p=clamp(t/localDuration);
 const zoom=1.018+p*.028;let w=W*zoom,h=w*img.height/img.width;if(h<H*zoom){h=H*zoom;w=h*img.width/img.height}
 const dx=(W-w)/2+(p-.5)*(i===2?17:-14),dy=(H-h)/2+(p-.5)*6;
 c.drawImage(img,dx,dy,w,h);return{img,dx,dy,w,h};
}
function glow(x,y,r,alpha){
 c.save();c.globalCompositeOperation='screen';const g=c.createRadialGradient(x,y,0,x,y,r);g.addColorStop(0,`rgba(245,214,166,${alpha})`);g.addColorStop(.17,`rgba(255,179,71,${alpha*.55})`);g.addColorStop(1,'rgba(255,179,71,0)');c.fillStyle=g;c.fillRect(x-r,y-r,r*2,r*2);c.restore();
}
function flow(i,t){
 // Optical gold trails echo the reference, without axes or measured values.
 const controls=i===7?[[75,866],[470,830],[760,515],[1070,236]]:[[0,788],[220,720],[170,394],[1080,424]];
 c.save();c.globalCompositeOperation='screen';
 for(let j=0;j<3;j++){c.beginPath();c.moveTo(controls[0][0],controls[0][1]+j*5);c.bezierCurveTo(controls[1][0],controls[1][1]+j*5,controls[2][0],controls[2][1]+j*5,controls[3][0],controls[3][1]+j*5);c.strokeStyle=j===1?warm:amber;c.lineWidth=j===1?1.8:.8;c.globalAlpha=j===1?.18:.13;c.shadowColor=amber;c.shadowBlur=16;c.stroke()}
 c.restore();
 const q=(.17+t*.1)%1,b=k=>(1-q)**3*controls[0][k]+3*(1-q)**2*q*controls[1][k]+3*(1-q)*q*q*controls[2][k]+q**3*controls[3][k];
 glow(b(0),b(1),44,.14);
}
function gather(t){
 const p=ease(t/1.45);c.save();c.globalCompositeOperation='screen';
 for(let j=0;j<70;j++){const a=hash(j+207)*Math.PI*2,r=950+(520-950)*p+hash(j+81)*50;const x=960+Math.cos(a)*r,y=490+Math.sin(a)*r*.53;c.fillStyle=`rgba(245,214,166,${.1+hash(j)*.34})`;c.beginPath();c.arc(x,y,.7+hash(j+45)*1.4,0,Math.PI*2);c.fill()}
 c.restore();
}
function geometry(i,t){
 c.fillStyle='#080808';c.fillRect(0,0,W,H);photo(i,t);
 // Keep the reference lighting; shade only the copy area slightly.
 if([1,2,3,5,6,7].includes(i)){const g=c.createLinearGradient(1100,0,1920,0);g.addColorStop(0,'#08080800');g.addColorStop(.6,'#08080820');g.addColorStop(1,'#08080843');c.fillStyle=g;c.fillRect(0,0,W,H)}
 if(i===2){const g=c.createRadialGradient(1490,515,130,1490,515,470);g.addColorStop(0,'#080808a0');g.addColorStop(.68,'#08080878');g.addColorStop(1,'#08080800');c.fillStyle=g;c.fillRect(1010,45,910,940)}
 if(i===0){const g=c.createRadialGradient(960,570,160,960,570,650);g.addColorStop(0,'#08080820');g.addColorStop(1,'#08080800');c.fillStyle=g;c.fillRect(0,0,W,H)}
 if(i===1)glow(537,476,90,.055+.015*Math.sin(t*.8));
 if(i===3||i===6||i===7)flow(i,t);
 if(i===4)gather(t);
 if(i===5){
  c.save();c.globalCompositeOperation='screen';const x=140+t*125,g=c.createLinearGradient(x-130,0,x+130,0);g.addColorStop(0,'#F5D6A600');g.addColorStop(.5,'#F5D6A609');g.addColorStop(1,'#F5D6A600');c.fillStyle=g;c.fillRect(70,130,1090,750);c.restore();
 }
 const vignette=c.createRadialGradient(960,510,620,960,510,1180);vignette.addColorStop(0,'#08080800');vignette.addColorStop(1,'#08080855');c.fillStyle=vignette;c.fillRect(0,0,W,H);
}
window.__seek=function(time){
 time=clamp(time,0,DURATION-1/30);let i=cuts.findIndex((n,j)=>j<9&&time>=n&&time<cuts[j+1]);if(i<0)i=8;
 const local=time-cuts[i],blend=i===0?1:ease(local/.32);
 ctx.fillStyle='#080808';ctx.fillRect(0,0,W,H);
 if(i>0&&blend<1){geometry(i-1,cuts[i]-cuts[i-1]-1/30);ctx.drawImage(buffer,0,0)}
 geometry(i,local);ctx.globalAlpha=blend;ctx.drawImage(buffer,0,0);ctx.globalAlpha=1;
 layers.forEach((node,j)=>{
  const shown=j===i||(j===i-1&&blend<1);node.style.display=shown?'block':'none';node.style.opacity=j===i?blend:1-blend;
  const heading=node.querySelector('.headline')||node.querySelector('.title');if(heading)heading.style.transform=`translateY(${j===i?(1-ease(local/.72))*9:0}px)`;
 });
 document.getElementById('caption').textContent=narration[i];
 document.querySelectorAll('.benefit').forEach((el,j)=>{el.style.opacity=ease((local-j*.24)/.65);el.style.transform=`translateX(${(1-ease((local-j*.24)/.65))*13}px)`});
 document.getElementById('scrub').value=time;document.getElementById('time').textContent=`${time.toFixed(1)} / 46.0`;
 window.__state={time,cut:i+1,local,background:`cut${String(i+1).padStart(2,'0')}.png`,abstract_frame_count:i===5?12:i===6?4:i===3?6:0};
};
function fit(){document.getElementById('stage').style.transform=`scale(${Math.min(innerWidth/W,innerHeight/H)})`}
window.addEventListener('resize',fit);fit();
let playing=false,anchor=0,current=0,audio=null;
if(new URLSearchParams(location.search).has('render'))document.getElementById('controls').style.display='none';
document.getElementById('scrub').addEventListener('input',e=>{current=Number(e.target.value);window.__seek(current);if(audio)audio.currentTime=current;anchor=performance.now()-current*1000});
document.getElementById('play').addEventListener('click',async()=>{playing=!playing;document.getElementById('play').textContent=playing?'일시정지':'재생';if(!audio){audio=new Audio('narration/mix.wav');audio.addEventListener('error',()=>{})}if(playing){if(current>=DURATION-.05)current=0;anchor=performance.now()-current*1000;audio.currentTime=current;await audio.play().catch(()=>{});tick()}else audio.pause()});
function tick(){if(!playing)return;current=Math.min((performance.now()-anchor)/1000,DURATION-1/30);window.__seek(current);if(current>=DURATION-1/30){playing=false;document.getElementById('play').textContent='재생';audio.pause()}else requestAnimationFrame(tick)}
window.__ready=Promise.all(Array.from({length:9},(_,i)=>new Promise((resolve,reject)=>{const img=new Image;img.onload=()=>{images[i]=img;resolve()};img.onerror=()=>reject(new Error(`Missing background cut${i+1}`));img.src=`assets/cut${String(i+1).padStart(2,'0')}.png`}))).then(()=>document.fonts.ready).then(()=>{window.__seek(0);return true});
