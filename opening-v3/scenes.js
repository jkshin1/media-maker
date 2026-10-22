/* v3: nine deterministic motion compositions. All display copy is HTML text.
 * Optical trails illustrate connection and direction; no measured task results.
 * Clean plates allow the light to be drawn on, instead of leaving a static path. */
const W=1920,H=1080,DURATION=46,cuts=[0,3,7,12,17,22,28,35,42,46];
const layers=[...document.querySelectorAll('.scene')],images={};
const canvas=document.getElementById('visual'),ctx=canvas.getContext('2d',{alpha:false});
const buffer=document.createElement('canvas');buffer.width=W;buffer.height=H;
const c=buffer.getContext('2d',{alpha:false});
const clamp=(n,a=0,b=1)=>Math.max(a,Math.min(b,n));
const ease=n=>{n=clamp(n);return n*n*(3-2*n)};
const out=n=>1-(1-clamp(n))**3;
const hash=n=>{const v=Math.sin(n*127.1+311.7)*43758.5453;return v-Math.floor(v)};
const gold='#D4AF7C',warm='#F5D6A6',amber='#FFB347';
const assetNames=Array.from({length:9},(_,i)=>`cut${String(i+1).padStart(2,'0')}${[3,6,7].includes(i)?'-clean':''}.png`);
const effectNames=['globe_connections','wafer_scan_orbits','human_ai_link_flow','ascending_s_ribbon','wave_convergence','twelve_panel_activation','ascending_wafer_orbit','rising_hero_arrow','wafer_scan_finale'];
// Split existing approved headlines into revealable lines without changing text.
for(const el of document.querySelectorAll('.headline')){
 const parts=el.innerHTML.split(/<br\s*\/?\s*>/i);el.innerHTML=parts.map(s=>`<span class="textLine"><span>${s}</span></span>`).join('');
}
function cubic(points,q){const r=1-q;return{x:r*r*r*points[0][0]+3*r*r*q*points[1][0]+3*r*q*q*points[2][0]+q*q*q*points[3][0],y:r*r*r*points[0][1]+3*r*r*q*points[1][1]+3*r*q*q*points[2][1]+q*q*q*points[3][1]}}
function curve(segments){const arr=[];for(const seg of segments)for(let k=0;k<=80;k++)arr.push(cubic(seg,k/80));return arr}
function at(path,q){const z=clamp(q)*(path.length-1),a=path[Math.floor(z)],b=path[Math.min(path.length-1,Math.ceil(z))],f=z%1;return{x:a.x+(b.x-a.x)*f,y:a.y+(b.y-a.y)*f}}
const routes={
 globe:[[[[100,970],[100,645],[530,445],[780,440]]],[[[1590,995],[1660,600],[1260,430],[1000,350]]],[[[350,780],[610,460],[1190,425],[1480,735]]],[[[120,750],[450,325],[985,190],[1380,530]]]],
 link:[[[[110,1070],[220,760],[670,700],[1040,385]]],[[[-60,945],[450,935],[700,560],[1130,460]]]],
 corridor:[[[0,1080],[430,1000],[1300,835],[835,661]],[[835,661],[640,572],[320,562],[416,496]],[[416,496],[530,424],[1000,421],[766,346]]],
 preview:[[[30,1100],[670,995],[1350,820],[805,676]],[[805,676],[575,597],[5,510],[240,418]],[[240,418],[520,400],[430,304],[590,240]]],
 finale:[[[0,1050],[450,1080],[1350,680],[460,585]]]
};
const paths={globe:routes.globe.map(curve),link:routes.link.map(curve),corridor:curve(routes.corridor),preview:curve(routes.preview),finale:curve(routes.finale)};
function glow(x,y,r,alpha){
 c.save();c.globalCompositeOperation='screen';const g=c.createRadialGradient(x,y,0,x,y,r);g.addColorStop(0,`rgba(255,245,218,${alpha})`);g.addColorStop(.12,`rgba(255,201,100,${alpha*.8})`);g.addColorStop(.44,`rgba(255,158,44,${alpha*.22})`);g.addColorStop(1,'rgba(255,179,71,0)');c.fillStyle=g;c.fillRect(x-r,y-r,r*2,r*2);c.restore();
}
function trace(path,a,b,width,color,alpha){
 if(b<=a||b<=0)return;c.save();c.globalAlpha=alpha;c.strokeStyle=color;c.lineWidth=width;c.lineCap='round';c.lineJoin='round';c.beginPath();let pt=at(path,a);c.moveTo(pt.x,pt.y);for(let k=Math.floor(a*(path.length-1))+1;k<b*(path.length-1);k++){pt=path[k];c.lineTo(pt.x,pt.y)}pt=at(path,b);c.lineTo(pt.x,pt.y);c.stroke();c.restore();
}
function ribbon(path,progress,t,{width=9,energy=1,seed=0}={}){
 progress=clamp(progress);c.save();c.globalCompositeOperation='screen';
 trace(path,0,progress,width*6,amber,.035*energy);trace(path,0,progress,width*3,amber,.1*energy);trace(path,0,progress,width*1.4,'#eab44f',.55*energy);trace(path,0,progress,width*.55,'#ffe0a0',.94*energy);trace(path,0,progress,Math.max(1.1,width*.18),'#fff6d9',.98*energy);
 for(let j=0;j<5;j++){const q=(t*.16+j*.22+seed*.13)%1;if(q>progress)continue;trace(path,Math.max(0,q-.12),q,width*.28,'#fffbea',.7*energy);const pt=at(path,q);glow(pt.x,pt.y,24+width*2,.45*energy)}
 if(progress>0&&progress<1){const pt=at(path,progress);glow(pt.x,pt.y,55+width*3,.92*energy)}
 for(let j=0;j<46;j++){const q=(hash(j+seed*87)+t*.10)%1;if(q>progress)continue;const pt=at(path,q),n=(hash(j+13)-.5)*22;const x=pt.x+n,y=pt.y+(hash(j+65)-.5)*38;c.fillStyle=`rgba(255,220,155,${(.3+hash(j)*.6)*energy})`;c.beginPath();c.arc(x,y,.6+hash(j+9)*1.65,0,Math.PI*2);c.fill()}
 c.restore();
}
function camera(i,t){
 const p=clamp((window.__freezeCamera?0:t)/(cuts[i+1]-cuts[i]));
 const start=[1.11,1.01,1.075,1.065,1.07,1.045,1.08,1,1.015][i],end=[1.01,1.095,1.005,1.01,1.005,1.005,1.005,1,1.085][i];
 const z=start+(end-start)*p,anchor=i===0?960:i===4?960:620;return{z,dx:(1-z)*anchor,dy:(1-z)*(i===0?400:600)};
}
function photo(i){const img=images[i];let w=W,h=w*img.height/img.width;if(h<H){h=H;w=h*img.width/img.height}c.drawImage(img,(W-w)/2,(H-h)/2,w,h)}
function ellipsePath(cx,cy,rx,ry,start,span){const points=[];for(let j=0;j<=150;j++){const a=start+span*j/150;points.push({x:cx+rx*Math.cos(a),y:cy+ry*Math.sin(a)})}return points}
function orbital(cx,cy,rx,ry,t,seed=0){
 const path=ellipsePath(cx,cy,rx,ry,Math.PI*.9,-Math.PI*1.9),p=ease((t-seed*.14)/1.4);ribbon(path,p,t,{width:2.2,energy:.55,seed});
 const q=(t*.19+seed*.29)%1,pt=at(path,q);glow(pt.x,pt.y,38,.7);
}
function waferScan(cx,cy,rx,ry,t){
 c.save();c.beginPath();c.ellipse(cx,cy,rx,ry,0,0,Math.PI*2);c.clip();c.globalCompositeOperation='screen';const q=(t*.28)%1,x=cx-rx-180+q*(rx*2+360);const g=c.createLinearGradient(x-110,0,x+110,0);g.addColorStop(0,'#FFB34700');g.addColorStop(.4,'#FFB34714');g.addColorStop(.5,'#FFF0B9aa');g.addColorStop(.6,'#FFB34720');g.addColorStop(1,'#FFB34700');c.fillStyle=g;c.fillRect(cx-rx,cy-ry,rx*2,ry*2);c.restore();
}
function dust(t,count,area={x:0,y:250,w:1180,h:850},energy=1){c.save();c.globalCompositeOperation='screen';for(let j=0;j<count;j++){const x=area.x+hash(j+230)*area.w+Math.sin(t*.5+j)*12,y=area.y+(hash(j+455)*area.h-t*(18+hash(j+76)*42)+area.h*6)%area.h;c.fillStyle=`rgba(255,212,133,${(.15+.45*hash(j+2))*energy})`;c.beginPath();c.arc(x,y,.6+hash(j+59)*1.9,0,Math.PI*2);c.fill()}c.restore()}
function sceneGlobe(t){
 paths.globe.forEach((path,j)=>{const p=ease((t-j*.25)/1.7);ribbon(path,p,t,{width:2.6,energy:.8,seed:j+2});const pt=at(path,p);if(p>0)glow(pt.x,pt.y,45,.6)});
 glow(965,155,300,.12+.26*ease(t/.9));dust(t,55,{x:0,y:150,w:1920,h:900},.6);
}
function sceneWafer(t){
 waferScan(630,613,597,256,t);orbital(625,630,593,235,t,0);orbital(625,630,545,209,t+.35,1);
 const p=curve([[[630,210],[625,340],[608,410],[615,544]]]);ribbon(p,ease(t/.9),t,{width:3,energy:.5});glow(618,535,66,.35+.2*Math.sin(t*3));dust(t,28);
}
function sceneHuman(t){
 for(let j=0;j<paths.link.length;j++)ribbon(paths.link[j],ease((t-j*.42)/2.4),t,{width:j?2.5:4.5,energy:.72,seed:j+8});
 const base=at(paths.link[0],clamp(t/2.9));for(let j=0;j<3;j++){const q=(t*.6+j*.34)%1;c.save();c.strokeStyle=`rgba(245,214,166,${(1-q)*.26})`;c.lineWidth=1.5;c.beginPath();c.arc(1040,385,12+q*70,0,Math.PI*2);c.stroke();c.restore()}dust(t,30,{x:90,y:450,w:1040,h:630});
}
function panelShine(x,y,w,h,slant,t,delay){
 const p=ease((t-delay)/.6);if(p<=0)return;c.save();c.globalCompositeOperation='screen';c.beginPath();c.moveTo(x,y);c.lineTo(x+w,y+slant);c.lineTo(x+w,y+h+slant);c.lineTo(x,y+h);c.closePath();c.clip();
 const q=(t-delay)*.55%1,s=x-w+q*w*3,g=c.createLinearGradient(s-45,0,s+45,0);g.addColorStop(0,'#FFB34700');g.addColorStop(.5,`rgba(255,223,153,${.12*p})`);g.addColorStop(1,'#FFB34700');c.fillStyle=g;c.fillRect(x,y-60,w,h+120);c.restore();
 // A short traveling edge glint avoids turning photographs into schematic UI.
 const path=[{x,y:y+h},{x,y},{x:x+w,y:y+slant}];ribbon(path,clamp((t-delay)/1.15),t,{width:1.6,energy:.38,seed:delay+6});
}
function sceneCorridor(t){
 ribbon(paths.corridor,ease((t-.08)/3.45),t,{width:13,energy:1,seed:2});
 // Companion streaks share the reference S curve and climb from the foreground.
 c.save();c.translate(-9,10);ribbon(paths.corridor,ease((t-.31)/3.5),t,{width:2.1,energy:.7,seed:9});c.restore();
 [[53,4,231,404,118],[344,154,151,254,65],[539,247,126,156,36],[700,304,79,100,25],[830,331,80,100,0],[951,332,122,117,0]].forEach((a,j)=>panelShine(...a,t,1.05+j*.24));dust(t,65);
}
function sceneTitle(t){
 const p=ease(t/1.65);
 for(let j=0;j<10;j++){
  const offset=(j-4.5)*11,wave=Math.sin(t*1.1+j*.24)*24;
  const a=curve([[[-100,920+offset],[240,700+offset],[470,370+wave],[920,560+offset*.28]]]);
  const b=curve([[[2020,165+offset],[1640,250+offset],[1450,775+wave],[1000,560+offset*.28]]]);
  ribbon(a,p,t,{width:j===4?3:1,energy:j===4?.65:.2,seed:j});ribbon(b,p,t,{width:j===4?3:1,energy:j===4?.65:.2,seed:j+8});
 }
 c.save();c.globalCompositeOperation='screen';for(let j=0;j<125;j++){const a=hash(j+31)*Math.PI*2,phase=(hash(j+74)+t*.19)%1,r=940-phase*450,x=960+Math.cos(a)*r,y=520+Math.sin(a)*r*.55;c.fillStyle=`rgba(255,217,147,${(.12+.65*hash(j+3))*(.6+.4*p)})`;c.beginPath();c.arc(x,y,.6+hash(j+57)*2,0,Math.PI*2);c.fill()}c.restore();glow(350+200*p,565,170,.16);glow(1550-200*p,470,180,.18);
}
const panelGrid=[[[74.64, 75.75], [311.2, 143.46], [311.2, 304.14], [73.49, 263.97]], [[349.09, 151.5], [608.61, 171.01], [608.61, 323.66], [349.09, 313.33]], [[646.51, 172.16], [901.44, 146.91], [901.44, 304.14], [646.51, 323.66]], [[939.33, 136.58], [1201.15, 63.12], [1201.15, 261.68], [939.33, 306.44]], [[74.64, 306.44], [311.2, 337.43], [311.2, 502.7], [74.64, 495.81]], [[349.09, 340.87], [608.61, 353.5], [608.61, 506.14], [349.09, 503.85]], [[646.51, 355.79], [901.44, 344.31], [901.44, 504.99], [646.51, 504.99]], [[939.33, 337.43], [1201.15, 303.0], [1201.15, 498.11], [939.33, 506.14]], [[74.64, 539.43], [311.2, 534.84], [311.2, 686.33], [74.64, 717.32]], [[349.09, 534.84], [608.61, 538.28], [608.61, 677.15], [349.09, 685.19]], [[646.51, 538.28], [901.44, 538.28], [901.44, 686.33], [646.51, 677.15]], [[939.33, 538.28], [1201.15, 539.43], [1201.15, 726.5], [939.33, 689.78]]];
function polygonPath(points){return points.map(([x,y])=>({x,y})).concat([{x:points[0][0],y:points[0][1]}])}
function scenePanels(t){
 // Twelve photo panel surfaces light up bottom-to-top, one physical panel each.
 panelGrid.forEach((poly,j)=>{
  const row=Math.floor(j/4),col=j%4,order=(2-row)*4+col,delay=.12+order*.22,p=ease((t-delay)/.55);
  c.save();c.beginPath();poly.forEach(([x,y],k)=>k?c.lineTo(x,y):c.moveTo(x,y));c.closePath();c.clip();c.fillStyle=`rgba(8,8,8,${(1-p)*.72})`;c.fillRect(0,0,1250,850);if(p>0){c.globalCompositeOperation='screen';c.fillStyle=`rgba(255,204,119,${Math.sin(p*Math.PI)*.16})`;c.fillRect(0,0,1250,850)}c.restore();
  if(p>0){const edge=polygonPath(poly);ribbon(edge,p,t,{width:1.5,energy:.35,seed:j});const pt=at(edge,((t-delay)*.14)%1);glow(pt.x,pt.y,19,.28)}
 });
 const path=curve([[[0,1040],[520,1040],[1380,790],[1110,568]],[[1110,568],[1040,420],[130,675],[225,380]],[[225,380],[320,185],[1000,270],[1120,140]]]);
 ribbon(path,ease(t/3.6),t,{width:3.5,energy:.7,seed:12});dust(t,42,{x:0,y:600,w:1230,h:480});
 // Restore the foreground researcher over the optical panel layer.
 c.save();c.beginPath();const silhouette=[[271,941],[271,775],[283,692],[316,610],[400,565],[402,472],[417,433],[447,407],[481,405],[508,420],[525,453],[528,504],[516,551],[563,575],[597,620],[626,705],[633,775],[624,941]];silhouette.forEach(([x,y],j)=>j?c.lineTo(x*W/1672,y*H/941):c.moveTo(x*W/1672,y*H/941));c.closePath();c.clip();photo(5);c.restore();
}
function scenePreview(t){
 ribbon(paths.preview,ease((t-.08)/3.95),t,{width:15,energy:.98,seed:7});
 c.save();c.translate(6,-15);ribbon(paths.preview,ease((t-.35)/4),t,{width:3,energy:.75,seed:3});c.restore();
 [[78,30,314,275,111],[463,125,207,157,65],[731,173,369,286,-131],[539,336,175,145,19]].forEach((a,j)=>panelShine(...a,t,.9+j*.5));
 dust(t,80);waferScan(410,783,470,227,t*.74);
}
function sceneFinale(t){
 waferScan(340,803,692,334,t);ribbon(paths.finale,ease(t/2.15),t,{width:5.5,energy:.75,seed:17});
 orbital(331,836,710,264,t*.8,2);dust(t,70,{x:0,y:100,w:1220,h:980});glow(710,548,165,.1+.12*Math.sin(t*1.1)**2);
}
const drawScenes=[sceneGlobe,sceneWafer,sceneHuman,sceneCorridor,sceneTitle,scenePanels,scenePreview,null,sceneFinale];
function geometry(i,t){
 c.globalAlpha=1;c.globalCompositeOperation='source-over';c.fillStyle='#080808';c.fillRect(0,0,W,H);const cam=camera(i,t);c.save();c.translate(cam.dx,cam.dy);c.scale(cam.z,cam.z);photo(i);
 if(drawScenes[i])drawScenes[i](t);if(window.drawHeroEffect)window.drawHeroEffect(c,i,t,cuts[i+1]-cuts[i]);c.restore();
 // Typography remains readable, while the left-side optical animation is exposed.
 if([1,2,3,5,6,7].includes(i)){const g=c.createLinearGradient(1120,0,1920,0);g.addColorStop(0,'#08080800');g.addColorStop(.62,'#08080818');g.addColorStop(1,'#08080842');c.fillStyle=g;c.fillRect(0,0,W,H)}
 if(i===2){const g=c.createRadialGradient(1490,515,130,1490,515,470);g.addColorStop(0,'#080808a0');g.addColorStop(.68,'#08080878');g.addColorStop(1,'#08080800');c.fillStyle=g;c.fillRect(1010,45,910,940)}
 const v=c.createRadialGradient(960,520,650,960,520,1250);v.addColorStop(0,'#08080800');v.addColorStop(1,'#08080845');c.fillStyle=v;c.fillRect(0,0,W,H);
}
function animateCopy(node,local){
 node.querySelectorAll('.textLine>span').forEach((el,j)=>{const p=out((local-.08-j*.16)/.82);el.style.opacity=p;el.style.transform=`translateY(${(1-p)*65}px)`;el.style.filter=`blur(${(1-p)*3}px)`});
 node.querySelectorAll('.title .ko,.title .en,.title .subtitle,.titleRule').forEach((el,j)=>{const delay=el.classList.contains('en')?.25:el.classList.contains('subtitle')?.65:el.classList.contains('titleRule')?.55:.08,p=out((local-delay)/.95);el.style.opacity=p;el.style.transform=`translateY(${(1-p)*42}px) scale(${.97+.03*p})`;el.style.filter=`blur(${(1-p)*4}px)`;if(el.classList.contains('en')){const shine=.6+.4*Math.sin(Math.max(0,local-.4)*1.4);el.style.textShadow=`0 4px 22px #000b,0 0 ${8+shine*14}px #D4AF7C${Math.round(18+shine*26).toString(16)}`}});
 node.querySelectorAll('.benefit').forEach((el,j)=>{const p=out((local-.35-j*.57)/.78);el.style.opacity=p;el.style.transform=`translateX(${(1-p)*54}px)`;const svg=el.querySelector('svg');svg.style.filter=`drop-shadow(0 0 ${5+Math.sin(local*1.6-j)*3}px #FFB34760)`;const circle=svg.querySelector('circle');circle.style.strokeDasharray='126';circle.style.strokeDashoffset=String(126*(1-p))});
}
window.__seek=function(time){
 time=clamp(time,0,DURATION-1/30);let i=cuts.findIndex((n,j)=>j<9&&time>=n&&time<cuts[j+1]);if(i<0)i=8;
 const local=time-cuts[i],blend=i===0?1:ease(local/.26);ctx.fillStyle='#080808';ctx.fillRect(0,0,W,H);
 if(i>0&&blend<1){geometry(i-1,cuts[i]-cuts[i-1]-1/30);ctx.drawImage(buffer,0,0)}geometry(i,local);ctx.globalAlpha=blend;ctx.drawImage(buffer,0,0);ctx.globalAlpha=1;
 layers.forEach((node,j)=>{const shown=j===i||(j===i-1&&blend<1);node.style.display=shown?'block':'none';node.style.opacity=j===i?blend:1-blend;if(shown)animateCopy(node,j===i?local:cuts[i]-cuts[i-1])});
 document.getElementById('scrub').value=time;document.getElementById('time').textContent=`${time.toFixed(1)} / 46.0`;
 const progress=i===3?ease((local-.08)/3.45):i===6?ease((local-.08)/3.95):i===7?clamp(local/3.5):ease(local/2.4);
 window.__state={time,cut:i+1,local,background:assetNames[i],captions:false,motion:effectNames[i],progress,abstract_frame_count:i===5?12:i===6?4:i===3?6:0};
};
function fit(){document.getElementById('stage').style.transform=`scale(${Math.min(innerWidth/W,innerHeight/H)})`}
window.addEventListener('resize',fit);fit();let playing=false,anchor=0,current=0,audio=null;
if(new URLSearchParams(location.search).has('render'))document.getElementById('controls').style.display='none';
document.getElementById('scrub').addEventListener('input',e=>{current=Number(e.target.value);window.__seek(current);if(audio)audio.currentTime=current;anchor=performance.now()-current*1000});
document.getElementById('play').addEventListener('click',async()=>{playing=!playing;document.getElementById('play').textContent=playing?'일시정지':'재생';if(!audio){audio=new Audio('narration/mix.wav');audio.addEventListener('error',()=>{})}if(playing){if(current>=DURATION-.05)current=0;anchor=performance.now()-current*1000;audio.currentTime=current;await audio.play().catch(()=>{});tick()}else audio.pause()});
function tick(){if(!playing)return;current=Math.min((performance.now()-anchor)/1000,DURATION-1/30);window.__seek(current);if(current>=DURATION-1/30){playing=false;document.getElementById('play').textContent='재생';audio.pause()}else requestAnimationFrame(tick)}
window.__ready=Promise.all(Array.from({length:9},(_,i)=>new Promise((resolve,reject)=>{const img=new Image;img.onload=()=>{images[i]=img;resolve()};img.onerror=()=>reject(new Error(`Missing background ${assetNames[i]}`));img.src=`assets/${assetNames[i]}`}))).then(()=>document.fonts.ready).then(()=>{window.__seek(0);return true});
