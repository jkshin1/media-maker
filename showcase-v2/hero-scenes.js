/* Photographic hero compositions for the independent showcase film.
 * Every animation is a pure function of the explicitly supplied local seconds.
 * Storyboard surfaces are separated into photos, panels, wafer and editable copy;
 * no storyboard sheet is displayed as a finished scene. Caption space starts at 870.
 */
const W = 1920, BODY = 865;
const C = { black:'#080808', gold:'#D4AF7C', pale:'#F5D6A6', amber:'#FFB347', white:'#F2EEE7' };
const FONT = 'Noto, Noto Sans CJK KR, sans-serif';
const clamp = (v, a=0, b=1) => Math.max(a, Math.min(b, Number(v)||0));
const ease = v => { const p=clamp(v); return p*p*(3-2*p); };
const out = v => 1-(1-clamp(v))**3;
const seed = n => { const q=Math.sin(n*127.1+311.7)*43758.5453; return q-Math.floor(q); };
const basename = s => String(s||'').split(/[\\/]/).pop();
const refs = ['0023','0103','0176','0246','0319','0381','0453','0523','0592','0660','0736','0805','0890','0941','0989','1046','1099','1155'].map(n=>`179196541${n}.png`);
const summaries = ['1791965410103.png','1791965410381.png','1791965410660.png','1791965410989.png'];
const openingNames = ['cut01.png','cut02.png','cut03.png','cut04-clean.png','cut05.png','cut06.png','cut07-clean.png','cut08-clean.png','cut09.png'];
const OPENING_COPY = [
 ['R&D 업무에','AI를 더합니다'],
 ['더 나은 R&D 공정의','내일을 만듭니다'],
 ['사람의 경험과','AI의 가능성을','연결합니다'],
 ['연구와 업무의','새로운 가능성을','열어갑니다'],
 ['R&D 공정','AI Fast Track'],
 ['12개 AI Agent가','만드는 변화'],
 ['현장의 문제를','AI로 해결하는','12개 과제'],
 ['업무 효율화','데이터 기반 의사결정','새로운 분석 관점','더 스마트한 연구 환경'],
 ['R&D 공정','AI Fast Track']
];
const SUMMARY_COPY = [
 [['흩어진 정보를 연결해','더 넓은 가능성을 열다'],['AI가 다양한 데이터와 지식을 연결해','더 정확하고 빠른 R&D 인사이트를 만듭니다.']],
 [['필요한 지식을 찾아','업무에 활용하다'],['흩어진 정보 속에서 필요한 지식을 찾고,','관련 데이터와 연결해 더 나은 업무 판단을 지원합니다.']],
 [['반복 업무를 줄이고','분석에 집중하다'],['데이터 분석과 반복 업무 자동화로','더 효율적인 R&D 환경을 만듭니다.']],
 [['이미지와 데이터를 분석해','더 정교한 연구를 실현하다'],['이미지 측정과 대규모 데이터 분석을 효율화해','더 신뢰도 높은 연구 결과를 지원합니다.']]
];
const DEFAULT_TASKS = [
 ['박재오 TL',"R&D 공정 Eng'r 연구 환경 Infra 구축",'1791965410176.png'],
 ['김태민 TL','Thinfilm Agent - BEOL Thinfilm','1791965410246.png'],
 ['서우석 TL','C&C Working Board Agent','1791965410319.png'],
 ['권혜선 TL','Smart Process Architecture AI Agent','1791965410453.png'],
 ['이태관 TL','Monitoring data 자연어 검색·시각화','1791965410523.png'],
 ['윤지욱 TL','LLM C&C Inline Data','1791965410592.png'],
 ['장민희 TL','RSAB SNM Overlay 열화 원인 분석 및 솔루션 제시 Agent','1791965410736.png'],
 ['오승재 TL','경비 분석 및 절감 아이템 발굴 Agent','1791965410805.png'],
 ['김도훈 TL','장비 Daily Report Auto Mail System','1791965410890.png'],
 ['정현준 TL','Cubic공정Lab 전용 App&Agent','1791965410941.png'],
 ['김성후 TL','TCAD-TEM 이미지 연계를 통한 이미지 Labeling Tool 개발','1791965411046.png'],
 ['김지은 TL','AI Agent 기반 Plug 대면적 데이터 분석 자동화 및 인사이트 도출','1791965411099.png']
].map(([owner,title,image])=>({owner,title,image}));

function drawable(x) { return x && (x.width||x.naturalWidth||x.videoWidth) && (x.height||x.naturalHeight||x.videoHeight); }
function dimensions(img) { return [img.naturalWidth||img.videoWidth||img.width, img.naturalHeight||img.videoHeight||img.height]; }
function imageFor(assets, name) { return assets.images?.[name] || assets.images?.[basename(name)] || assets.images?.[`reference/${basename(name)}`] || assets[name]; }
function photo(ctx,img,x,y,w,h,crop=null) {
 if(!drawable(img)) return;
 const [iw,ih]=dimensions(img); let sx=0,sy=0,sw=iw,sh=ih;
 if(crop) { sx=crop[0]*iw; sy=crop[1]*ih; sw=crop[2]*iw; sh=crop[3]*ih; }
 const q=Math.max(w/sw,h/sh),cw=w/q,ch=h/q;
 ctx.drawImage(img,sx+(sw-cw)/2,sy+(sh-ch)/2,cw,ch,x,y,w,h);
}
function polygon(ctx,pts) { ctx.beginPath(); pts.forEach(([x,y],j)=>j?ctx.lineTo(x,y):ctx.moveTo(x,y));ctx.closePath(); }
function curve(points,steps=90) {
 const a=[];for(let i=0;i<=steps;i++){const p=i/steps,q=1-p;a.push([q**3*points[0][0]+3*q*q*p*points[1][0]+3*q*p*p*points[2][0]+p**3*points[3][0],q**3*points[0][1]+3*q*q*p*points[1][1]+3*q*p*p*points[2][1]+p**3*points[3][1]]);}return a;
}
function point(path,p) { const q=clamp(p)*(path.length-1),a=path[Math.floor(q)],b=path[Math.ceil(q)];return[a[0]+(b[0]-a[0])*(q%1),a[1]+(b[1]-a[1])*(q%1)]; }
function trace(ctx,path,start,end) {
 if(end<=start)return;ctx.beginPath();let a=point(path,start);ctx.moveTo(...a);
 for(let j=Math.ceil(start*(path.length-1));j<end*(path.length-1);j++)ctx.lineTo(...path[j]);ctx.lineTo(...point(path,end));
}
function glow(ctx,x,y,r,a=.3) {
 ctx.save();ctx.globalCompositeOperation='screen';const g=ctx.createRadialGradient(x,y,0,x,y,r);
 g.addColorStop(0,`rgba(255,239,194,${a})`);g.addColorStop(.12,`rgba(255,198,95,${a*.7})`);g.addColorStop(.55,`rgba(255,163,58,${a*.15})`);g.addColorStop(1,'rgba(255,179,71,0)');ctx.fillStyle=g;ctx.fillRect(x-r,y-r,r*2,r*2);ctx.restore();
}
function ribbon(ctx,path,t,p=1,width=3,energy=1,s=0) {
 p=clamp(p);if(!p)return;ctx.save();ctx.globalCompositeOperation='screen';ctx.lineCap='round';ctx.lineJoin='round';
 for(const [mult,alpha,col] of [[8,.025,C.amber],[4,.10,C.amber],[1.4,.6,C.gold],[.5,.94,C.pale]]){trace(ctx,path,0,p);ctx.lineWidth=width*mult;ctx.strokeStyle=col;ctx.globalAlpha=alpha*energy;ctx.stroke();}
 for(let k=0;k<4;k++){const q=(t*.16+k*.27+s*.19)%1;if(q>p)continue;trace(ctx,path,Math.max(0,q-.07),q);ctx.lineWidth=width*.8;ctx.strokeStyle='#FFF9DA';ctx.globalAlpha=.8*energy;ctx.stroke();const a=point(path,q);glow(ctx,...a,20+width*2,.26*energy);}
 if(p<1){const a=point(path,p);glow(ctx,...a,50,.7*energy);}ctx.restore();
}
function ellipsePath(cx,cy,rx,ry,start,span) { return Array.from({length:101},(_,j)=>[cx+Math.cos(start+span*j/100)*rx,cy+Math.sin(start+span*j/100)*ry]); }
function orbit(ctx,cx,cy,rx,ry,t,s=0) { const path=ellipsePath(cx,cy,rx,ry,.88*Math.PI,-1.84*Math.PI);ribbon(ctx,path,t,ease((t-s*.12)/1.5),2,.62,s); }
function scan(ctx,cx,cy,rx,ry,t) {
 ctx.save();ctx.beginPath();ctx.ellipse(cx,cy,rx,ry,0,0,Math.PI*2);ctx.clip();ctx.globalCompositeOperation='screen';const x=cx-rx-180+(t*.27%1)*(rx*2+360),g=ctx.createLinearGradient(x-100,0,x+100,0);
 g.addColorStop(0,'#FFB34700');g.addColorStop(.43,'#FFB34728');g.addColorStop(.5,'#FFF5C7bb');g.addColorStop(.58,'#FFB34728');g.addColorStop(1,'#FFB34700');ctx.fillStyle=g;ctx.fillRect(cx-rx,cy-ry,rx*2,ry*2);ctx.restore();
}
function dust(ctx,t,count=45,area=[0,0,W,BODY],a=.6) {
 ctx.save();ctx.globalCompositeOperation='screen';for(let j=0;j<count;j++){const x=area[0]+seed(j+233)*area[2]+Math.sin(t*.5+j)*10,y=area[1]+((seed(j+93)*area[3]-t*(8+seed(j+75)*22)+area[3]*20)%area[3]);ctx.fillStyle=`rgba(255,212,133,${(.1+seed(j+2)*.35)*a})`;ctx.beginPath();ctx.arc(x,y,.5+seed(j+19)*1.55,0,Math.PI*2);ctx.fill();}ctx.restore();
}
function base(ctx,t) {
 ctx.fillStyle=C.black;ctx.fillRect(0,0,W,BODY);
 const g=ctx.createRadialGradient(960,645,50,960,645,1180);g.addColorStop(0,'#37240f');g.addColorStop(.45,'#17120c');g.addColorStop(1,C.black);ctx.fillStyle=g;ctx.fillRect(0,0,W,BODY);dust(ctx,t,34);
}
function darken(ctx,x=0,y=0,w=W,h=BODY,alpha=.32) {ctx.save();ctx.fillStyle=`rgba(8,8,8,${alpha})`;ctx.fillRect(x,y,w,h);ctx.restore();}
function copyShade(ctx,x=1070) { const g=ctx.createLinearGradient(x,0,W,0);g.addColorStop(0,'#08080800');g.addColorStop(.25,'#080808a8');g.addColorStop(.7,'#080808ea');g.addColorStop(1,'#080808ef');ctx.fillStyle=g;ctx.fillRect(x,0,W-x,BODY); }
function wrapped(ctx,text,width,size=50) {
 ctx.font=`600 ${size}px ${FONT}`;const lines=[];
 for(const block of String(text||'').split('\n')) {
  let line='';for(const word of block.split(/\s+/)){
   const candidate=line?`${line} ${word}`:word;
   if(ctx.measureText(candidate).width<=width){line=candidate;continue;}
   if(line){lines.push(line);line='';}
   if(ctx.measureText(word).width<=width){line=word;continue;}
   for(const ch of word){if(ctx.measureText(line+ch).width>width&&line){lines.push(line);line=ch;}else line+=ch;}
  }if(line)lines.push(line);
 }
 return lines;
}
function text(ctx,lines,{x=960,y=210,width=1100,size=84,leading=1.24,align='center',time=2,delay=.25,goldFrom=1,weight=700}={}) {
 lines=Array.isArray(lines)?lines:String(lines||'').split('\n');
 // Font size decreases only to fit the approved words; content is never truncated.
 ctx.font=`${weight} ${size}px ${FONT}`;const longest=Math.max(1,...lines.map(s=>ctx.measureText(String(s)).width));size*=Math.min(1,width/longest);
 ctx.save();ctx.textAlign=align;ctx.textBaseline='top';ctx.shadowColor='#000';ctx.shadowBlur=16;ctx.shadowOffsetY=3;
 lines.forEach((line,j)=>{const p=out((time-delay-j*.13)/.62);ctx.globalAlpha=p;ctx.font=`${weight} ${size}px ${FONT}`;ctx.fillStyle=j>=goldFrom?C.pale:C.white;ctx.fillText(String(line),x,y+j*size*leading+(1-p)*26);});ctx.restore();return size*leading*lines.length;
}
function cornerLine(ctx,x,y,height,t) { const p=ease((t-.08)/.55);ctx.save();ctx.strokeStyle=C.gold;ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(x,y+height/2);ctx.lineTo(x,y+height/2-height*p/2);ctx.moveTo(x,y+height/2);ctx.lineTo(x,y+height/2+height*p/2);ctx.stroke();ctx.restore(); }
function panel(ctx,img,{x,y,w,h,crop,t,delay=0,tilt=0,label=null,photoHeight=null}) {
 const p=out((t-delay)/.72);if(!p)return;ctx.save();ctx.globalAlpha=p;ctx.translate(x+w/2+(1-p)*(x<W/2?-125:125),y+h/2+(1-p)*30);ctx.rotate(tilt*(1-p*.4));ctx.scale(.94+.06*p,.94+.06*p);ctx.translate(-w/2,-h/2);
 ctx.shadowColor='#000';ctx.shadowBlur=30;ctx.fillStyle='#121212';ctx.fillRect(0,0,w,h);ctx.shadowBlur=0;
 photo(ctx,img,3,3,w-6,(photoHeight||h)-6,crop);ctx.strokeStyle=`rgba(212,175,124,${.48+.38*Math.sin(t*1.2+delay)**2})`;ctx.lineWidth=2;ctx.strokeRect(0,0,w,h);
 if(label)text(ctx,label,{x:16,y:h-70,width:w-32,size:24,align:'left',time:t,delay,goldFrom:2});
 const edge=[[0,h],[0,0],[w,0],[w,h],[0,h]];ribbon(ctx,edge,t,ease((t-delay)/1.4),1.5,.54,delay);ctx.restore();
}

function cutIndex(section,cut) {
 if(Number.isFinite(cut?.index))return cut.index;
 if(cut?.id!=null){const n=Number(String(cut.id).match(/\d+$/)?.[0]);if(n)return n-1;}
 const found=section.cuts?.indexOf(cut);return found>=0?found:0;
}
function summaryIndex(section) {
 if(Number.isFinite(section.summary_index))return section.summary_index;
 const n=Number(String(section.id||section.title||'').match(/([1-4])\D*$/)?.[1]);return clamp((n||1)-1,0,3);
}
function explicitPlate(assets,section,index,cut) {
 const entry=assets.backgrounds?.[section.id]?.[index] || assets.backgrounds?.[section.id]?.[cut?.id];
 if(drawable(entry))return entry;
 if(drawable(entry?.image))return entry.image;
 if(typeof entry==='string')return imageFor(assets,entry);
 const video=assets.videos?.[section.id]?.[index] || assets.videos?.[`${section.id}:${index}`];
 if(drawable(video))return video;
 return imageFor(assets,cut?.background||cut?.image||'');
}
function openingPlate(ctx,assets,section,i,t,cut) {
 const explicit=explicitPlate(assets,section,i,cut),img=assets.opening?.[i]||imageFor(assets,`opening${i+1}`)||explicit||imageFor(assets,openingNames[i]);
 const z=1.02+.024*ease(t/3),move=Math.sin(t*.2)*8;ctx.save();ctx.translate((1-z)*700+move,(1-z)*470);ctx.scale(z,z);
 if(drawable(img))photo(ctx,img,0,0,W,BODY);else {
  const ref=imageFor(assets,section.reference_image||'1791965410023.png'),col=i%3,row=Math.floor(i/3);
  // Crop only the photography inside the grid cell, excluding headers/captions.
  const crop=[col/3+.006,row*.275+.056,.326,.164];photo(ctx,ref,0,0,W,BODY,crop);darken(ctx,0,0,W,BODY,.32);
 }ctx.restore();
}
function abstractFrames(ctx,t,{count=6,ring=false}={}) {
 const images=[[400,325],[640,430],[880,310],[330,575],[600,665],[940,590]];
 for(let j=0;j<count;j++){
  const col=j%4,row=Math.floor(j/4),x=count===12?70+col*255:images[j%images.length][0],y=count===12?115+row*205:images[j%images.length][1],w=count===12?214:190,h=count===12?154:130;
  const p=out((t-j*.13)/.65);if(!p)continue;ctx.save();ctx.globalAlpha=p;ctx.translate(x+(1-p)*((j%2?-1:1)*130),y+(1-p)*60+Math.sin(t*.6+j)*5);ctx.rotate((j%2?1:-1)*.025);
  ctx.fillStyle='rgba(8,8,8,.82)';ctx.fillRect(0,0,w,h);ctx.strokeStyle=C.gold;ctx.lineWidth=1.5;ctx.strokeRect(0,0,w,h);
  // Geometric wafer / equipment motifs only. They contain no task UI or metrics.
  if(j%3===0){orbit(ctx,w/2,h/2,w*.34,h*.25,t,j);scan(ctx,w/2,h/2,w*.34,h*.25,t+j*.1);}
  else if(j%3===1){ctx.strokeStyle=C.pale;ctx.lineWidth=2;ctx.strokeRect(w*.25,h*.25,w*.5,h*.5);ctx.beginPath();ctx.moveTo(w*.42,h*.25);ctx.lineTo(w*.42,h*.12);ctx.moveTo(w*.58,h*.25);ctx.lineTo(w*.58,h*.12);ctx.stroke();ribbon(ctx,[[w*.25,h*.7],[w*.75,h*.3]],t,ease(t),2,.5,j);}
  else{for(let k=0;k<3;k++)ribbon(ctx,curve([[12,110-k*20],[55,90-k*20],[120,40+k*15],[w-10,25+k*30]]),t,ease((t-j*.1)/1.6),1,.5,j+k);}
  ribbon(ctx,[[0,h],[0,0],[w,0],[w,h]],t,ease((t-j*.13)/.9),1,.4,j);ctx.restore();
 }
 if(ring)orbit(ctx,670,725,560,130,t);
}
function twelvePhotoPanels(ctx,img,t) {
 const panels=[
  [[75,76],[311,143],[311,304],[74,264]],[[349,152],[609,171],[609,324],[349,313]],[[647,172],[901,147],[901,304],[647,324]],[[939,137],[1201,63],[1201,262],[939,306]],
  [[75,306],[311,337],[311,503],[75,496]],[[349,341],[609,354],[609,506],[349,504]],[[647,356],[901,344],[901,505],[647,505]],[[939,337],[1201,303],[1201,498],[939,506]],
  [[75,539],[311,535],[311,686],[75,717]],[[349,535],[609,538],[609,677],[349,685]],[[647,538],[901,538],[901,686],[647,677]],[[939,538],[1201,539],[1201,727],[939,690]]
 ];
 ctx.save();const z=1.02+.024*ease(t/3);ctx.translate((1-z)*700+Math.sin(t*.2)*8,(1-z)*470);ctx.scale(z,z);photo(ctx,img,0,0,W,1080);
 panels.forEach((poly,j)=>{
  const row=Math.floor(j/4),col=j%4,delay=.1+((2-row)*4+col)*.12,p=ease((t-delay)/.55);
  ctx.save();polygon(ctx,poly);ctx.clip();darken(ctx,0,0,1250,800,(1-p)*.88);
  if(p){const x=poly[0][0]-130+((t-delay)*.29%1)*540,g=ctx.createLinearGradient(x-35,0,x+35,0);g.addColorStop(0,'#FFB34700');g.addColorStop(.5,`rgba(255,228,164,${p*.13})`);g.addColorStop(1,'#FFB34700');ctx.fillStyle=g;ctx.fillRect(0,0,1250,800);}ctx.restore();
  ribbon(ctx,poly.concat([poly[0]]),t,ease((t-delay)/1.1),1.6,.5,j);
 });ctx.restore();
}
function benefitIcon(ctx,index,x,y,t) {
 const p=ease(t/.65);ctx.save();ctx.translate(x,y);ctx.strokeStyle=C.gold;ctx.lineWidth=2.5;ctx.beginPath();ctx.arc(0,0,40,-Math.PI/2,-Math.PI/2+Math.PI*2*p);ctx.stroke();ctx.strokeStyle=C.pale;ctx.lineWidth=3;
 if(index===0){ctx.beginPath();ctx.arc(0,0,14,0,Math.PI*2);ctx.stroke();for(let k=0;k<8;k++){const a=k*Math.PI/4;ctx.beginPath();ctx.moveTo(Math.cos(a)*20,Math.sin(a)*20);ctx.lineTo(Math.cos(a)*27,Math.sin(a)*27);ctx.stroke();}}
 else if(index===1){for(let k=0;k<3;k++)ctx.strokeRect(-21+k*15,18-(k+1)*11,9,(k+1)*11);ctx.beginPath();ctx.moveTo(-25,-3);ctx.lineTo(22,-22);ctx.lineTo(12,-23);ctx.moveTo(22,-22);ctx.lineTo(18,-12);ctx.stroke();}
 else if(index===2){ctx.beginPath();ctx.arc(0,-7,17,Math.PI*.12,Math.PI*.88,true);ctx.lineTo(-7,14);ctx.lineTo(7,14);ctx.closePath();ctx.stroke();ctx.beginPath();ctx.moveTo(-6,22);ctx.lineTo(6,22);ctx.stroke();}
 else{ctx.beginPath();ctx.arc(-12,-10,7,0,Math.PI*2);ctx.moveTo(22,-10);ctx.arc(14,-10,7,0,Math.PI*2);ctx.stroke();ctx.beginPath();ctx.moveTo(-26,18);ctx.bezierCurveTo(-26,-1,0,-1,0,18);ctx.moveTo(0,18);ctx.bezierCurveTo(0,-1,28,-1,28,18);ctx.stroke();}ctx.restore();
}
function drawOpening(ctx,section,cut,t,duration,assets) {
 const i=clamp(cutIndex(section,cut),0,8);
 // Only a verified clean title plate can supply this shot's photographic waves.
 // The raw reference grid is never a title-shot fallback.
 if(i===4){const clean=assets.opening?.[4]||imageFor(assets,'opening5')||imageFor(assets,'cut05.png');if(clean)photo(ctx,clean,0,0,W,BODY);else base(ctx,t);}else openingPlate(ctx,assets,section,i,t,cut);
 let lines=cut.main_lines||cut.headline||cut.screen_text||cut.screen_lines||OPENING_COPY[i];if(!Array.isArray(lines))lines=String(lines).split('\n');
 if(!lines.length)lines=OPENING_COPY[i];
 if(lines.length===1&&lines[0].replace(/\s/g,'')===OPENING_COPY[i].join('').replace(/\s/g,''))lines=OPENING_COPY[i];
 if(i===0){
  const paths=[curve([[80,690],[250,230],[740,140],[1120,470]]),curve([[1500,720],[1350,285],[1050,110],[900,180]]),curve([[180,485],[590,195],[1300,180],[1730,530]])];paths.forEach((p,j)=>ribbon(ctx,p,t,ease((t-j*.15)/1.5),2.4,.6,j));
  const fade=1-ease(t/.7);darken(ctx,0,0,W,BODY,fade*.88);const g=ctx.createLinearGradient(0,400,0,BODY);g.addColorStop(0,'#08080800');g.addColorStop(1,'#080808bd');ctx.fillStyle=g;ctx.fillRect(0,400,W,BODY-400);
  cornerLine(ctx,215,505,180,t);text(ctx,lines,{x:255,y:510,width:1410,size:91,align:'left',time:t,delay:.25});glow(ctx,1000,180,220,.2*ease(t/.9));
 }else if(i===1){
  scan(ctx,650,574,630,235,t);orbit(ctx,650,589,633,245,t);orbit(ctx,650,589,588,215,t+.3,1);
  // Shift a clipped photographic tool head separately from its fixed wafer.
  const img=assets.opening?.[i]||imageFor(assets,`opening${i+1}`)||explicitPlate(assets,section,i,cut);
  if(img){ctx.save();const z=1.02+.024*ease(t/3);ctx.translate((1-z)*700+Math.sin(t*.2)*8,(1-z)*470);ctx.scale(z,z);polygon(ctx,[[390,0],[955,0],[930,315],[832,393],[512,381],[410,308]]);ctx.clip();photo(ctx,img,Math.sin(t*.75)*1.8,Math.sin(t*.85)*1.4,W,BODY);ctx.restore();}
  copyShade(ctx);cornerLine(ctx,1220,210,220,t);text(ctx,lines,{x:1260,y:215,width:570,size:73,align:'left',time:t,delay:.32});
 }else if(i===2){
  ribbon(ctx,curve([[120,735],[470,660],[960,565],[1180,332]]),t,ease(t/2),4,.68,4);ribbon(ctx,curve([[50,600],[475,555],[770,255],[1100,230]]),t,ease((t-.3)/2),2,.45,5);copyShade(ctx);
  cornerLine(ctx,1220,215,295,t);text(ctx,lines,{x:1260,y:220,width:570,size:73,align:'left',time:t,delay:.4});
 }else if(i===3){
  abstractFrames(ctx,t,{count:6});const p=curve([[0,800],[530,725],[1030,680],[760,475]]).concat(curve([[760,475],[590,420],[230,402],[440,300]]));ribbon(ctx,p,t,ease(t/2.7),8,.85,3);copyShade(ctx);text(ctx,lines,{x:1250,y:220,width:585,size:72,align:'left',time:t,delay:.62});
 }else if(i===4){
  darken(ctx,0,0,W,BODY,.30);for(let j=0;j<8;j++){const v=(j-3.5)*13;ribbon(ctx,curve([[-20,640+v],[510,290+v],[650,280],[905,455]]),t,ease(t/1.4),j===3?2.6:.8,j===3?.64:.25,j);ribbon(ctx,curve([[1940,100+v],[1550,360],[1260,655],[1030,455+v*.2]]),t,ease(t/1.4),j===3?2.6:.8,j===3?.64:.25,j+8);}dust(ctx,t,90);
  text(ctx,lines,{x:960,y:235,width:1490,size:104,leading:1.20,time:t,delay:.3,goldFrom:1});text(ctx,cut.support_lines||['AI로 더 스마트한 R&D 공정'],{x:960,y:526,width:1450,size:42,time:t,delay:.88,goldFrom:0,weight:400});
 }else if(i===5){
  const clean=assets.opening?.[5]||imageFor(assets,'opening6')||imageFor(assets,'cut06.png');
  // Activate the twelve existing photographic surfaces without doubling the array.
  if(clean)twelvePhotoPanels(ctx,clean,t);else{darken(ctx,0,0,1190,BODY,.80);abstractFrames(ctx,t,{count:12});}
  copyShade(ctx,1130);text(ctx,lines,{x:1270,y:262,width:560,size:75,align:'left',time:t,delay:.65});
 }else if(i===6){
  abstractFrames(ctx,t,{count:4,ring:true});scan(ctx,535,708,510,135,t);ribbon(ctx,curve([[0,815],[330,650],[1030,575],[730,325]]),t,ease(t/2.5),9,.9,7);copyShade(ctx,1110);text(ctx,lines,{x:1250,y:220,width:590,size:74,align:'left',time:t,delay:.62});
 }else if(i===7){
  const path=curve([[-40,810],[410,715],[800,590],[1050,170]]),p=ease((t-.1)/Math.min(3.4,duration*.62));ribbon(ctx,path,t,p,15,.93,8);
  if(p>0){const tip=point(path,p),prev=point(path,Math.max(0,p-.01)),ang=Math.atan2(tip[1]-prev[1],tip[0]-prev[0]);ctx.save();ctx.translate(...tip);ctx.rotate(ang);polygon(ctx,[[0,0],[-95,-44],[-73,-14],[-120,-14],[-120,14],[-73,14],[-95,44]]);ctx.fillStyle=C.pale;ctx.shadowColor=C.amber;ctx.shadowBlur=18;ctx.fill();ctx.restore();}
  copyShade(ctx,1100);lines.forEach((line,j)=>{const age=t-.3-j*.44,p=out(age/.7);if(!p)return;ctx.save();ctx.globalAlpha=p;benefitIcon(ctx,j,1240,180+j*156,age);text(ctx,[line],{x:1310,y:156+j*156,width:525,size:46,align:'left',time:age,delay:0,goldFrom:j===0?0:2});ctx.restore();});
 }else{
  scan(ctx,505,640,630,260,t);orbit(ctx,505,645,635,255,t);ribbon(ctx,curve([[0,820],[410,770],[1170,500],[570,355]]),t,ease(t/2.2),4,.6,9);copyShade(ctx,1000);
  text(ctx,lines,{x:1430,y:244,width:790,size:83,time:t,delay:.25});text(ctx,cut.support_lines||['AI로 만들어가는 R&D의 새로운 변화'],{x:1420,y:495,width:795,size:33,time:t,delay:.8,goldFrom:0,weight:400});
 }dust(ctx,t,26);return {kind:'opening',index:i,motion:true};
}

function drawSummary(ctx,section,cut,t,duration,assets) {
 const i=summaryIndex(section),ref=imageFor(assets,section.reference_image||section.image||summaries[i]);
 base(ctx,t);const custom=explicitPlate(assets,section,0,cut);if(custom){photo(ctx,custom,0,0,W,BODY);darken(ctx,0,0,W,BODY,.24);}
 // The source's angled photographic panels are isolated from the baked headline.
 if(ref){
  panel(ctx,ref,{x:-18,y:45,w:438,h:750,crop:[.006,.022,.288,.867],t,delay:.05,tilt:-.018});
  panel(ctx,ref,{x:1500,y:45,w:438,h:750,crop:[.708,.022,.286,.867],t,delay:.18,tilt:.018});
 }
 const streams=[
  curve([[330,225],[525,280],[650,610],[950,713]]),curve([[318,460],[510,470],[635,689],[980,744]]),
  curve([[1585,210],[1400,260],[1250,615],[980,713]]),curve([[1595,610],[1400,530],[1300,725],[980,755]])
 ];streams.forEach((path,j)=>ribbon(ctx,path,t,ease((t-.6-j*.12)/1.65),j%2?2.2:4,.74,j+i*4));
 // Photographic wafer crop is independently animated from the two panel stacks.
 if(ref){ctx.save();const z=1+.018*ease(t/duration);ctx.translate(960,737);ctx.scale(z,z);ctx.beginPath();ctx.ellipse(0,0,587,143,0,0,Math.PI*2);ctx.clip();photo(ctx,ref,-587,-143,1174,286,[.31,.667,.381,.228]);ctx.restore();}
 orbit(ctx,960,754,685,119,t,0);orbit(ctx,960,752,635,107,t+.4,1);scan(ctx,960,716,536,106,t*.82);glow(ctx,960,642,255,.16+.11*Math.sin(t*1.3)**2);
 const g=ctx.createLinearGradient(0,85,0,625);g.addColorStop(0,'#08080800');g.addColorStop(.19,'#080808fc');g.addColorStop(.78,'#080808fa');g.addColorStop(1,'#08080800');ctx.fillStyle=g;ctx.fillRect(410,85,1090,540);
 const main=section.main_lines||cut.main_lines||SUMMARY_COPY[i][0],support=section.support_lines||cut.support_lines||SUMMARY_COPY[i][1];
 const reveal=Math.min(2.1,duration*.30);text(ctx,main,{x:960,y:214,width:1100,size:85,leading:1.22,time:t,delay:reveal,goldFrom:1});
 const mainAge=t-reveal,p=ease(mainAge/.7);ctx.save();ctx.globalAlpha=p;ctx.strokeStyle=C.gold;ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(670,446);ctx.lineTo(1250,446);ctx.stroke();glow(ctx,960,446,72,.34*p);ctx.restore();
 text(ctx,support,{x:960,y:473,width:1120,size:34,leading:1.42,time:t,delay:reveal+.65,goldFrom:9,weight:400});
 dust(ctx,t,46,[375,565,1165,285]);return {kind:'summary',index:i,motion:true};
}

function taskList(section,assets) {
 const tasks=section.tasks||assets.tasks||assets.spec?.sections?.filter(s=>s.type==='task')||[];
 if(tasks.length!==12)return DEFAULT_TASKS;
 return tasks.map((s,i)=>({owner:s.owner||s.owner_name||DEFAULT_TASKS[i].owner,title:s.title||s.task_name||DEFAULT_TASKS[i].title,image:s.reference_image||s.image||DEFAULT_TASKS[i].image}));
}
function taskPhoto(assets,task) { return imageFor(assets,task.image)||imageFor(assets,DEFAULT_TASKS.find(s=>s.owner===task.owner)?.image); }
function gallery(ctx,section,assets,t,{spread=false,small=false}={}) {
 const tasks=taskList(section,assets);
 tasks.forEach((task,j)=>{
  const col=j%4,row=Math.floor(j/4),p=out((t-j*.07)/.68),w=small?225:432,h=small?150:226;
  let x=small?40+col*265:60+col*461,y=small?65+row*198:65+row*252;
  if(spread){x=col<2?-100+col*265:1495+(col-2)*265;y=120+row*210;}
  const img=taskPhoto(assets,task);ctx.save();ctx.globalAlpha=p*(small?.54:1);ctx.translate(x+(1-p)*(col<2?-370:370),y+(1-p)*(row===0?-170:170));ctx.rotate((1-p)*(j%2?-.10:.10));
  ctx.fillStyle='#111111';ctx.shadowColor='#000';ctx.shadowBlur=22;ctx.fillRect(0,0,w,h);ctx.shadowBlur=0;
  photo(ctx,img,2,2,w-4,small?h-4:130,[.21,.26,.185,.455]);ctx.strokeStyle=C.gold;ctx.lineWidth=1.6;ctx.strokeRect(0,0,w,h);
  if(!small){const nameLines=wrapped(ctx,task.title,w-32,18);text(ctx,nameLines,{x:16,y:142,width:w-32,size:18,leading:1.16,align:'left',time:t,delay:j*.07,goldFrom:9,weight:500});text(ctx,[task.owner],{x:w-16,y:197,width:w-32,size:22,align:'right',time:t,delay:j*.07+.25,goldFrom:0});}
  ribbon(ctx,[[0,h],[0,0],[w,0],[w,h]],t,ease((t-j*.07)/1.1),1,.5,j);ctx.restore();
 });
}
function endingWafer(ctx,assets,t,section) {
 const ref=imageFor(assets,section.reference_image||'1791965411155.png'),clean=assets.opening?.[8]||imageFor(assets,'opening9');
 // The lower strip of the third storyboard cell contains only the wafer.
 // Exclude its baked headline and support copy from the photographic element.
 if(clean||ref){ctx.save();ctx.beginPath();ctx.ellipse(960,746,708,118,0,0,Math.PI*2);ctx.clip();photo(ctx,clean||ref,250,608,1420,252,clean?[.03,.48,.51,.40]:[.718,.378,.27,.109]);ctx.restore();}
 orbit(ctx,960,744,765,113,t);orbit(ctx,960,744,685,98,t+.4,1);scan(ctx,960,721,600,90,t);glow(ctx,960,630,340,.20);
}
function finalTaskCard(ctx,assets,task,x,t,delay,mode,team) {
 const p=out((t-delay)/.68),w=832,h=746,y=50;ctx.save();ctx.globalAlpha=p;ctx.translate(x+(1-p)*(x<W/2?-170:170),y+26*(1-p));
 ctx.shadowColor='#000';ctx.shadowBlur=30;ctx.fillStyle='#121210';ctx.fillRect(0,0,w,h);ctx.shadowBlur=0;
 const img=taskPhoto(assets,task),leftCrop=mode==='plug'?[.204,.277,.161,.458]:[.405,.276,.180,.533],rightCrop=mode==='plug'?[.606,.28,.174,.488]:[.812,.273,.174,.528];
 // Two independent UI surfaces keep the storyboard's transition arrows out.
 photo(ctx,img,24,24,384,398,leftCrop);photo(ctx,img,424,24,384,398,rightCrop);
 ctx.strokeStyle='rgba(212,175,124,.42)';ctx.lineWidth=1;ctx.strokeRect(24,24,384,398);ctx.strokeRect(424,24,384,398);
 ctx.strokeStyle=C.gold;ctx.lineWidth=2;ctx.strokeRect(0,0,w,h);ribbon(ctx,[[0,h],[0,0],[w,0],[w,h],[0,h]],t,ease((t-delay)/1.25),1.7,.7,delay);
 if(mode==='plug'){
  for(let j=0;j<6;j++){const q=ease((t-delay-.18-j*.10)/.4);if(!q)continue;const px=50+(j%3)*109,py=98+Math.floor(j/3)*130;ctx.globalAlpha=p*q*.85;ctx.strokeStyle=C.pale;ctx.lineWidth=2;ctx.strokeRect(px,py,88,86);ctx.beginPath();ctx.moveTo(px,py+43);ctx.lineTo(px+88*q,py+43);ctx.stroke();}
 }else{
  for(let j=0;j<4;j++){const q=ease((t-delay-.2-j*.16)/.45);ctx.globalAlpha=p*q*.75;orbit(ctx,118+(j%2)*174,132+Math.floor(j/2)*197,70,65,t-delay,j);}
 }
 ctx.save();ctx.beginPath();ctx.rect(424,24,384,398);ctx.clip();const sweep=424+((t-delay)*.18%1)*384;const g=ctx.createLinearGradient(sweep-42,0,sweep+42,0);g.addColorStop(0,'#FFB34700');g.addColorStop(.5,'#FFF5C736');g.addColorStop(1,'#FFB34700');ctx.fillStyle=g;ctx.fillRect(424,24,384,398);ctx.restore();
 ctx.globalAlpha=p;const titleLines=wrapped(ctx,task.title,w-96,39);text(ctx,titleLines,{x:w/2,y:460,width:w-96,size:39,leading:1.34,time:t,delay:delay+.4,goldFrom:9});
 text(ctx,[team],{x:w/2,y:634,width:w-100,size:30,time:t,delay:delay+.52,goldFrom:9,weight:500});
 text(ctx,[task.owner],{x:w/2,y:681,width:w-100,size:47,time:t,delay:delay+.62,goldFrom:0});ctx.restore();
}
function drawEnding(ctx,section,cut,t,duration,assets) {
 const i=clamp(cutIndex(section,cut),0,5);base(ctx,t);const custom=explicitPlate(assets,section,i,cut);if(custom){photo(ctx,custom,0,0,W,BODY);darken(ctx,0,0,W,BODY,.32);}
 if(i===0||i===1){gallery(ctx,section,assets,t+(i===1?3:0));if(i===1){for(let j=0;j<3;j++)ribbon(ctx,curve([[75,210+j*252],[600,180+j*252],[1250,190+j*252],[1820,210+j*252]]),t,ease(t/1.4),1.3,.4,j);}}
 else if(i===2){
  gallery(ctx,section,assets,t+.8,{spread:true,small:true});endingWafer(ctx,assets,t,section);
  text(ctx,['12개의 도전,','새로운 변화의 시작'],{x:960,y:180,width:1300,size:94,time:t,delay:.15,goldFrom:1});
  text(ctx,['업무 효율화부터 데이터 분석,','더 나은 연구 환경까지'],{x:960,y:433,width:1260,size:40,leading:1.35,time:t,delay:.48,goldFrom:9,weight:400});
 }else if(i===3){
  endingWafer(ctx,assets,t,section);const left=DEFAULT_TASKS[11],right=DEFAULT_TASKS[6];
  panel(ctx,taskPhoto(assets,left),{x:185,y:120,w:630,h:454,crop:[.2,.27,.39,.48],t,delay:.12,tilt:-.045});
  panel(ctx,taskPhoto(assets,right),{x:1105,y:120,w:630,h:454,crop:[.4,.27,.39,.48],t,delay:.26,tilt:.045});
  ribbon(ctx,curve([[960,747],[910,644],[595,556],[500,432]]),t,ease(t/1.3),5,.85,1);ribbon(ctx,curve([[960,747],[1010,644],[1310,556],[1420,432]]),t,ease((t-.2)/1.3),5,.85,2);
 }else if(i===4){
  gallery(ctx,section,assets,t+.8,{spread:true,small:true});endingWafer(ctx,assets,t,section);
  text(ctx,['12개의 AI Agent가 만든 변화'],{x:960,y:243,width:1450,size:64,time:t,delay:.1,goldFrom:9});
  text(ctx,['이제 두 개의 우수 과제를','만나봅니다.'],{x:960,y:347,width:1450,size:89,leading:1.20,time:t,delay:.35,goldFrom:0});
  for(let j=0;j<2;j++)ribbon(ctx,curve([[960,658],[850+j*220,690],[530+j*840,645],[380+j*1160,496]]),t,ease((t-.35)/1.4),3,.6,j);
 }else{
  // Final cards show the approved task title, team and owner inside each card.
  // The team sits above its owner; this final card remains without narration.
  const tasks=taskList(section,assets),plug=tasks.find(s=>s.owner.includes('김지은'))||DEFAULT_TASKS[11],overlay=tasks.find(s=>s.owner.includes('장민희'))||DEFAULT_TASKS[6];
  finalTaskCard(ctx,assets,plug,90,t,0,'plug','N-PMA');finalTaskCard(ctx,assets,overlay,998,t,.12,'overlay','DRAM트랙Photo');
 }dust(ctx,t,28);return {kind:'ending',index:i,motion:true,silent:i===3||i===5};
}

/** Load inputs in either the browser renderer or the bundled Node Canvas runtime.
 * Calling renderers may merge their own images/backgrounds/videos into this object.
 * Missing optional old clean plates are recorded; required references throw errors.
 */
export async function loadHeroAssets(spec={}) {
 let load;
 if(typeof Image!=='undefined')load=url=>new Promise((resolve,reject)=>{const img=new Image();img.onload=()=>resolve(img);img.onerror=()=>reject(new Error(`Hero image failed: ${url}`));img.src=url;});
 else{
  let canvas;
  for(const candidate of ['@napi-rs/canvas','/Users/jk/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@napi-rs/canvas/index.js']){try{canvas=await import(candidate);break;}catch{}}
  if(!canvas)throw new Error('Hero asset loader needs @napi-rs/canvas or a browser Image implementation.');load=canvas.loadImage||canvas.default?.loadImage;
 }
 const assets={images:{},opening:[],backgrounds:{},videos:{},spec,tasks:spec.sections?.filter(s=>s.type==='task'),loadWarnings:[]};
 const node=typeof Image==='undefined';
 const resolve=path=>node?new URL(path,import.meta.url).pathname:path;
 await Promise.all(refs.map(async name=>{const img=await load(resolve(`./reference/${name}`));assets.images[name]=img;assets.images[`reference/${name}`]=img;}));
 await Promise.all(openingNames.map(async(name,i)=>{
  let failure;for(const path of [`./assets/opening/cut${String(i+1).padStart(2,'0')}.png`,`../opening-v3/assets/${name}`]){
   try{const img=await load(resolve(path));assets.opening[i]=img;assets.images[name]=img;assets.images[`opening${i+1}`]=img;return;}catch(e){failure=e;}
  }assets.loadWarnings.push(failure.message);
 }));
 for(const section of spec.sections||[]){
  const names=[section.reference_image,section.image,...(section.cuts||[]).map(c=>c.background||c.image)].filter(Boolean);
  for(const name of names){if(imageFor(assets,name))continue;try{const img=await load(resolve(name));assets.images[name]=img;assets.images[basename(name)]=img;}catch(e){assets.loadWarnings.push(e.message);}}
 }
 return assets;
}

/** Draw into the caption-safe upper 1920 × 865 composition area. */
export function drawHero(ctx,section,cut={},localTime=0,duration=1,assets={}) {
 const t=Math.max(0,Number(localTime)||0);ctx.save();ctx.beginPath();ctx.rect(0,0,W,BODY);ctx.clip();
 let result;
 if(section.type==='summary')result=drawSummary(ctx,section,cut,t,duration,assets);
 else if(section.type==='ending')result=drawEnding(ctx,section,cut,t,duration,assets);
 else result=drawOpening(ctx,section,cut,t,duration,assets);
 ctx.restore();return result;
}
