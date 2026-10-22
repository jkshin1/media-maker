/* Six task-specific, deterministic compositions.
 * Approved source MDs govern the functional scope; storyboard example metrics
 * and unsupported automatic decisions are never added. The caller paints the
 * approved photographic workspace first and owns the persistent top header.
 */
const TAU=Math.PI*2;
const cap=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
const smooth=v=>{v=cap(v);return v*v*(3-2*v)};
const phase=(u,a=0,b=1)=>smooth((u-a)/(b-a));
const mix=(a,b,p)=>a+(b-a)*p;
const sourceInfo={
 infra:['task3','3.RD_공정_AI_Fast_Track_박재오TL_영상제작_MD_확정시안기준.md','1791965410176.png'],
 thinfilm:['task4','4.RD_공정_AI_Fast_Track_김태민TL_Thinfilm_Agent_영상제작_MD.md','1791965410246.png'],
 working:['task5','5.RD_공정_AI_Fast_Track_서우석TL_CC_Working_Board_Agent_영상제작_MD.md','1791965410319.png'],
 architecture:['task7','7.RD_공정_AI_Fast_Track_권혜선TL_Smart_Process_Architecture_AI_Agent_MD.md','1791965410453.png'],
 monitoring:['task8','1-8.RD_공정_AI_Fast_Track_이태관TL_Monitoring_Data_자연어검색_시각화_MD.md','1791965410523.png'],
 inline:['task9','9.RD_공정_AI_Fast_Track_윤지욱TL_LLM_CnC_Inline_Data_분석_MD.md','1791965410592.png']
};
function shade(c,k,alpha=.60){
 // The caller grades the complete photographic plate. Do not paint a second
 // inset matte with visible rectangular edges around the safe content area.
}

function surface(c,k,x,y,w,h,{paper=false,alpha=.91,r=18}={}){
 c.save();c.globalAlpha*=alpha;k.panel(c,x,y,w,h,{fill:paper?'#E8E3D8':'#10171D',line:paper?'#D4AF7C99':'#D4AF7C70',radius:r});c.restore();
}
function label(c,k,s,x,y,w,size=32,color=k.CREAM,weight=500){k.fit(c,String(s),x,y,w,size,color,weight)}
function textLines(c,k,s,x,y,w,size=40,color=k.CREAM,weight=600){
 const a=k.lines(c,s,w,size,weight);a.forEach((s,j)=>k.text(c,s,x,y+j*size*1.32,size,color,weight));return a.length*size*1.32;
}
function abstractRows(c,k,x,y,w,h,u,count=5,{paper=false,selected=-1}={}){
 const gap=h/count;
 for(let j=0;j<count;j++){
  const p=phase(u,.03+j*.045,.39+j*.045),yy=y+j*gap;
  if(j===selected){c.fillStyle=paper?'#D4AF7C55':'#D4AF7C22';c.fillRect(x-9,yy-13,w+18,gap-8)}
  c.fillStyle=paper?'#47515A66':'#F2EEE766';c.fillRect(x,yy,w*(.48+.23*k.hash(j+11))*p,9);
  c.fillStyle=paper?'#47515A35':'#F2EEE72F';c.fillRect(x,yy+21,w*(.3+.2*k.hash(j+29))*p,6);
  k.line(c,x,yy+gap-17,x+w,yy+gap-17,1,paper?'#47515A22':'#FFFFFF16',1);
 }
}
function pathPoint(points,q){
 q=cap(q);const lengths=points.slice(1).map((p,i)=>Math.hypot(p[0]-points[i][0],p[1]-points[i][1]));let remain=q*lengths.reduce((a,b)=>a+b,0);
 for(let j=0;j<lengths.length;j++){if(remain<=lengths[j]||j===lengths.length-1){const p=cap(remain/Math.max(1,lengths[j]));return[mix(points[j][0],points[j+1][0],p),mix(points[j][1],points[j+1][1],p)]}remain-=lengths[j]}return points[0];
}
function route(c,k,points,u,{delay=0,width=3,color=k.GOLD}={}){
 const v=cap((u-delay)/(1-delay)),draw=phase(v,.02,.68),travel=phase(v,.08,.96),end=pathPoint(points,draw);
 c.save();c.lineWidth=width;c.strokeStyle=color;c.lineCap='round';c.beginPath();c.moveTo(...points[0]);
 const N=90;for(let j=1;j<=Math.ceil(draw*N);j++)c.lineTo(...pathPoint(points,Math.min(draw,j/N)));c.lineTo(...end);c.stroke();
 if(v>.03&&v<.985){const p=pathPoint(points,travel);k.glow(c,p[0],p[1],20,.35);c.fillStyle='#F5D6A6';c.beginPath();c.arc(p[0],p[1],3.5,0,TAU);c.fill()}c.restore();
}
function plot(c,k,x,y,w,h,u,{seed=0,bars=false,scatter=false}={}){
 c.save();c.beginPath();c.rect(x-4,y-4,w+8,h+8);c.clip();
 for(let j=0;j<4;j++)k.line(c,x,y+j*h/3,x+w,y+j*h/3,1,'#F2EEE71D',1);
 k.line(c,x,y,x,y+h,1,'#D4AF7C70',2);k.line(c,x,y+h,x+w,y+h,1,'#D4AF7C70',2);
 if(bars){
  for(let j=0;j<10;j++){const q=phase(u,.02+j*.035,.45+j*.035),hh=h*(.22+.60*k.hash(j+seed));c.fillStyle=j%3===0?k.AMBER:'#D4AF7CBA';c.fillRect(x+18+j*(w-30)/10,y+h-hh*q,(w-30)/10-15,hh*q)}
 }else if(scatter){
  const q=phase(u,.03,.82);
  for(let j=0;j<72*q;j++){const xx=x+30+k.hash(j+seed+33)*(w-60),yy=y+h-30-(xx-x)*(.72*h/w)+(k.hash(j+seed+91)-.5)*h*.40;c.fillStyle=j%4?k.GOLD:'#C9D0D3';c.beginPath();c.arc(xx,yy,4,0,TAU);c.fill()}
 }else{
  const pts=Array.from({length:45},(_,j)=>[x+j*w/44,y+h*(.47+.17*Math.sin(j*.32+seed)+.12*Math.sin(j*.71+seed))]),q=phase(u,.02,.84);
  c.strokeStyle=k.GOLD;c.lineWidth=4;c.beginPath();pts.forEach((p,j)=>{if(j/44<=q)j?c.lineTo(...p):c.moveTo(...p)});c.stroke();
  pts.forEach((p,j)=>{if(j%5===0&&j/44<=q){c.fillStyle='#F5D6A6';c.beginPath();c.arc(...p,4.5,0,TAU);c.fill()}});
 }
 const scan=x+w*phase(u,.16,.96);k.line(c,scan,y,scan,y+h,1,'#F5D6A649',1.4);c.restore();
}
function paper(c,k,x,y,w,h,u,title,{angle=0,delay=0}={}){
 const q=phase(u,delay,.36+delay);c.save();c.globalAlpha=q;c.translate(x+w/2,y+h/2+(1-q)*24);c.rotate(angle);c.translate(-w/2,-h/2);
 c.shadowColor='#00000088';c.shadowBlur=25;surface(c,k,0,0,w,h,{paper:true,r:6,alpha:1});c.shadowBlur=0;
 k.icon(c,'doc',24,26,34,'#785E36');label(c,k,title,76,57,w-98,28,'#27313A',600);
 abstractRows(c,k,28,98,w-56,h-118,u,5,{paper:true,selected:Math.floor(phase(u,.45,.90)*4)});c.restore();
}
function person(c,k,x,y,r,u){
 c.save();c.globalAlpha=phase(u,.12,.42);c.strokeStyle=k.GOLD;c.lineWidth=3;c.beginPath();c.arc(x,y,r*.32,0,TAU);c.stroke();c.beginPath();c.arc(x,y+r*.83,r*.66,Math.PI,0);c.stroke();c.restore();
}
function query(c,k,s,x,y,w,h,u,{size=42}={}){
 surface(c,k,x,y,w,h,{paper:true,r:20});k.icon(c,'search',x+28,y+h/2-21,45,'#25313B');
 const shown=s.slice(0,Math.floor(phase(u,.07,.57)*s.length));const amount=textLines(c,k,shown,x+110,y+h/2-9,w-230,size,'#202B35',600);
 const q=phase(u,.58,.82);c.fillStyle='#D4AF7C';c.beginPath();c.roundRect(x+w-92,y+22,66,h-44,12);c.fill();
 k.line(c,x+w-73,y+h/2,x+w-44,y+h/2,q,'#26313A',3);k.line(c,x+w-53,y+h/2-10,x+w-43,y+h/2,q,'#26313A',3);k.line(c,x+w-53,y+h/2+10,x+w-43,y+h/2,q,'#26313A',3);return amount;
}

function infra(c,p,i,u,k){
 shade(c,k,.62);
 if(i===1){
  surface(c,k,130,235,1660,710,{alpha:.93});label(c,k,'통합 조회',180,302,460,43,k.GOLD,700);
  const labs=p.sources;labs.forEach((s,j)=>{const y=359+j*105,q=phase(u,.03+j*.07,.38+j*.07);c.save();c.globalAlpha=q;surface(c,k,170,y,400,82,{alpha:.85,r:10});k.icon(c,'database',194,y+17,38);label(c,k,s,255,y+53,280,31);c.restore()});
  const row=Math.min(4,Math.floor(phase(u,.26,.95)*5));c.strokeStyle=k.GOLD;c.lineWidth=2;c.strokeRect(167,359+row*105,406,82);
  label(c,k,'데이터 연계',655,309,900,36,k.GOLD,600);abstractRows(c,k,655,371,1050,475,u,6,{selected:row});
  route(c,k,[[580,400+row*105],[620,400+row*105],[620,520],[650,520]],u,{width:3});
 }else if(i===2){
  const nodes=[['공정 이력',170,260],['장비 데이터',1390,260],['Lot 데이터',170,650],['FDC 데이터',1390,650],['연계 공정',760,825]];
  for(let j=0;j<nodes.length;j++){const[s,x,y]=nodes[j];route(c,k,[[x+180,y+100],[960,y+100],[960,610]],u,{delay:j*.055,width:2.4});surface(c,k,x,y,360,145,{alpha:.88});label(c,k,s,x+28,y+52,310,32,k.GOLD,600);if(j===1||j===3)plot(c,k,x+27,y+74,305,48,cap(u-j*.045),{seed:j*7});else abstractRows(c,k,x+28,y+83,300,45,u,2)}
  c.fillStyle='#251D13DD';c.beginPath();c.arc(960,610,154,0,TAU);c.fill();c.strokeStyle=k.GOLD;c.lineWidth=2;c.stroke();k.icon(c,'database',917,525,80);label(c,k,'데이터 연계',843,671,245,38,k.GOLD,700);
 }else if(i===3){
  label(c,k,'분석 결과',150,288,1050,43,k.GOLD,700);plot(c,k,150,345,1095,500,u,{seed:6});
  label(c,k,'관련 정보',1320,288,420,36,k.GOLD,600);const labs=p.sources.slice(0,3);
  labs.forEach((s,j)=>{const y=357+j*164,q=phase(u,.12+j*.10,.55+j*.10);c.save();c.globalAlpha=q;k.icon(c,'doc',1320,y,42);label(c,k,s,1388,y+38,355,30);abstractRows(c,k,1388,y+68,320,60,u,2);c.restore()});
 }else{
  label(c,k,'Lot 1건 분석 시간',145,284,1400,43,k.GOLD,600);k.line(c,145,320,1775,320,phase(u,.03,.35),'#D4AF7C66',2);
  label(c,k,'기존 약',165,430,630,45);label(c,k,'2시간 40분',165,587,710,108,k.CREAM,700);
  label(c,k,'개선 후',1120,430,640,45,k.GOLD);label(c,k,'20분 이내',1110,602,680,128,k.GOLD,700);
  route(c,k,[[760,540],[1060,540]],u,{delay:.1,width:6});k.line(c,1028,516,1060,540,phase(u,.48,.74),k.GOLD,6);k.line(c,1028,564,1060,540,phase(u,.48,.74),k.GOLD,6);
  [[440,795,1],[1430,795,.125]].forEach(([x,y,f])=>{c.strokeStyle='#D4AF7C55';c.lineWidth=8;c.beginPath();c.arc(x,y,94,0,TAU);c.stroke();c.strokeStyle=k.GOLD;c.beginPath();c.arc(x,y,94,-Math.PI/2,-Math.PI/2+TAU*f*phase(u,.14,.88));c.stroke();k.line(c,x,y,x+Math.cos(-Math.PI/2+phase(u,.12,.9)*Math.PI*.7)*56,y+Math.sin(-Math.PI/2+phase(u,.12,.9)*Math.PI*.7)*56,1,k.CREAM,3)});
 }
}
function thinfilm(c,p,i,u,k){
 shade(c,k,.60);
 if(i===1||i===2){
  const names=i===1?p.sources:['Lot Trend','Equipment Status','FDC Summary','DOE Result'];
  names.forEach((s,j)=>{const x=125+(j%2)*855,y=235+Math.floor(j/2)*365,local=cap((u-j*.055)/(1-j*.055));surface(c,k,x,y,815,328,{alpha:.90,r:14});label(c,k,s,x+34,y+56,745,37,k.GOLD,600);
   if(j===1){const cx=x+407,cy=y+210,r=86;c.strokeStyle='#D4AF7C30';c.lineWidth=26;c.beginPath();c.arc(cx,cy,r,0,TAU);c.stroke();c.strokeStyle=k.GOLD;c.beginPath();c.arc(cx,cy,r,-Math.PI/2,-Math.PI/2+TAU*phase(local,.04,.87));c.stroke()}
   else if(j===3){for(let a=0;a<10;a++)for(let b=0;b<4;b++){const q=phase(local,.04+(a+b)*.025,.4+(a+b)*.025);c.fillStyle='rgba(212,175,124,'+q*(.12+.6*k.hash(a*7+b))+')';c.fillRect(x+38+a*73,y+99+b*47,65,40)}}
   else plot(c,k,x+37,y+103,738,190,local,{seed:j*15,bars:j===2});
  });
 }else if(i===3){
  paper(c,k,460,230,835,720,u,'DOE Result');
  c.save();c.beginPath();c.rect(488,400,775,260);c.clip();c.fillStyle='#E8E3D8';c.fillRect(488,400,775,260);plot(c,k,515,420,720,210,u,{seed:5});c.restore();
  label(c,k,'DOE 결과 업데이트',500,744,720,32,'#76592E',600);label(c,k,'분석 보고서',500,804,720,32,'#27313A',500);
  const people=[[1510,340],[1640,620],[1510,855]];people.forEach(([x,y],j)=>{route(c,k,[[1295,590],[1400,590],[x-40,y+25]],u,{delay:.22+j*.07});person(c,k,x,y,60,cap((u-.22-j*.07)/.78))});
  label(c,k,'업데이트·공유',132,328,320,34,k.GOLD,600);label(c,k,'조직의 지식 자산',132,391,320,27);
 }else{
  const cx=640,cy=605,r=253,labels=['DOE 결과','분석 방법','최적 조건 탐색'];
  c.strokeStyle='#D4AF7C44';c.lineWidth=2;c.beginPath();c.arc(cx,cy,r,0,TAU);c.stroke();
  labels.forEach((s,j)=>{const a=-Math.PI/2+j*TAU/3,x=cx+Math.cos(a)*r,y=cy+Math.sin(a)*r;c.save();c.globalAlpha=phase(u,j*.11,.4+j*.11);c.fillStyle='#1A1712';c.beginPath();c.arc(x,y,80,0,TAU);c.fill();c.strokeStyle=k.GOLD;c.stroke();k.icon(c,'doc',x-20,y-33,43);label(c,k,s,x-135,y+80,270,31,k.GOLD,600);c.restore()});
  const a=-Math.PI/2+TAU*phase(u,.08,.94);k.glow(c,cx+Math.cos(a)*r,cy+Math.sin(a)*r,38,.28);
  textLines(c,k,'DOE 분석 효율화 ·\n최적 조건 탐색 지원',1110,430,675,49,k.GOLD,700);textLines(c,k,'분석 방법과 탐색 로직을\n조직의 자산으로',1110,650,675,34,k.CREAM,500);
 }
}
function working(c,p,i,u,k){
 shade(c,k,.46);
 if(i===1){
  query(c,k,'관련 회의 자료와 이슈를 찾아봅니다.',135,242,1650,124,u,{size:42});
  p.sources.forEach((s,j)=>paper(c,k,145+j*422,465+(j%2)*28,355,480,u,s,{angle:(j-1.5)*.026,delay:.13+j*.06}));
 }else if(i===2){
  paper(c,k,470,255,490,715,u,'핵심 내용');paper(c,k,970,255,490,715,u,'관련 이슈');
  c.strokeStyle='#9A784555';c.lineWidth=3;c.beginPath();c.moveTo(965,278);c.lineTo(965,965);c.stroke();
  label(c,k,'참고 자료',146,330,290,32,k.GOLD,600);p.sources.slice(0,3).forEach((s,j)=>{const y=440+j*190;k.icon(c,'doc',175,y,66);label(c,k,s,135,y+104,300,29);route(c,k,[[300,y+30],[430,y+30],[490,540+j*65]],u,{delay:.12+j*.07,width:2})});
  route(c,k,[[990,456],[1210,456],[1210,630]],u,{delay:.2,width:3});
 }else if(i===3){
  label(c,k,'업무 진행 현황',140,282,1100,41,k.GOLD,700);
  ['이슈','관련 문서','핵심 내용'].forEach((s,j)=>label(c,k,s,150+j*365,355,310,30,k.GOLD,600));
  for(let r=0;r<4;r++){const y=400+r*130,q=phase(u,.03+r*.07,.4+r*.07);c.save();c.globalAlpha=q;k.line(c,140,y+96,1210,y+96,1,'#D4AF7C44',1);for(let j=0;j<3;j++){k.icon(c,'doc',150+j*365,y+10,35);abstractRows(c,k,213+j*365,y+19,260,55,u,2)}c.restore()}
  const choice=Math.min(3,Math.floor(phase(u,.25,.92)*4));c.strokeStyle=k.GOLD;c.lineWidth=2;c.strokeRect(135,391+choice*130,1085,109);
  paper(c,k,1330,336,445,595,u,'관련 자료',{delay:.2});route(c,k,[[1220,445+choice*130],[1285,445+choice*130],[1285,620],[1330,620]],u,{delay:.15,width:2});
 }else{
  const center=[930,540];paper(c,k,750,350,360,420,u,'핵심 정보 활용');
  [[390,500],[1460,450],[1290,765]].forEach(([x,y],j)=>{person(c,k,x,y,88,cap((u-j*.06)/(1-j*.06)));route(c,k,[[center[0],center[1]],[mix(center[0],x,.55),mix(center[1],y,.55)],[x,y+75]],u,{delay:.1+j*.07,width:3})});
  textLines(c,k,'더 빠르고 효율적인 C&C 협업',200,914,1520,58,k.GOLD,700);textLines(c,k,'필요한 정보를 찾아 업무와 의사결정에 활용',200,986,1520,32,k.CREAM,500);
 }
}
function architecture(c,p,i,u,k){
 shade(c,k,.58);
 if(i===1){
  const labs=p.sources;
  labs.forEach((s,j)=>{const x=135+j*422,y=345+(j%2?0:72),w=355,h=470;paper(c,k,x,y,w,h,u,s,{angle:(j-1.5)*.019,delay:j*.055});if(j<3)route(c,k,[[x+w,y+240],[x+w+66,y+240],[x+w+66,610],[x+w+96,610]],u,{delay:.2+j*.06,width:2})});
  label(c,k,'관련 지식과 경험',140,284,1500,43,k.GOLD,600);
 }else if(i===2){
  query(c,k,'이 공정 조건에서는 어떤 Plan과 Recipe를 검토해야 할까?',150,260,1620,185,u,{size:43});
  p.sources.forEach((s,j)=>{const x=155+j*418,y=615;paper(c,k,x,y,345,337,u,s,{angle:0,delay:.23+j*.055});route(c,k,[[960,445],[960,520],[x+170,520],[x+170,615]],u,{delay:.2+j*.055,width:2})});
 }else if(i===3){
  label(c,k,'Plan·Recipe 추천',140,282,1500,44,k.GOLD,700);
  const labs=['Plan A','Plan B','Plan C'];
  labs.forEach((s,j)=>{const x=140+j*575,q=phase(u,j*.07,.36+j*.07);c.save();c.globalAlpha=q;surface(c,k,x,340,490,332,{alpha:.90,r:14});label(c,k,s,x+35,415,400,54,k.GOLD,700);k.icon(c,'doc',x+35,459,60);label(c,k,'관련 근거',x+129,506,300,33);abstractRows(c,k,x+36,560,413,75,u,2);c.restore();
   const evidence=['과거 평가 이력','유사 사례','실패 사례'][j];paper(c,k,x+45,750,400,242,u,evidence,{angle:(j-1)*.016,delay:.18+j*.055});route(c,k,[[x+245,672],[x+245,750]],u,{delay:.15+j*.07,width:3})});
 }else{
  const labs=['과거 평가 이력','유사 사례','실패 사례'];label(c,k,'공정 지식과 경험을 활용',145,288,1510,43,k.GOLD,700);
  labs.forEach((s,j)=>{const y=365+j*175;k.icon(c,'doc',180,y,69);label(c,k,s,288,y+48,510,36);route(c,k,[[745,y+34],[900,y+34],[1040,650]],u,{delay:j*.08,width:3})});
  c.save();c.beginPath();c.ellipse(1370,630,350,250,0,0,TAU);c.clip();
  if(p.reference)k.cover(c,{image:p.reference,crop:[.812,.695,.185,.225]},1020,380,700,500);
  c.restore();c.strokeStyle='#D4AF7C99';c.lineWidth=2;c.beginPath();c.ellipse(1370,630,350,250,0,0,TAU);c.stroke();k.glow(c,1370,630,300,.12);const a=phase(u,.1,.95)*TAU;k.glow(c,1370+Math.cos(a)*345,630+Math.sin(a)*245,28,.28);
  textLines(c,k,'Plan·Recipe 추천과 평가 의사결정 지원',980,936,815,40,k.GOLD,600);
 }
}
function monitoring(c,p,i,u,k){
 shade(c,k,.59);
 if(i===1){
  label(c,k,'Monitoring Data AI Agent',170,308,1560,43,k.GOLD,600);
  query(c,k,'필요한 공정 데이터를 자연어로 조회합니다.',170,390,1580,190,u,{size:48});
  p.sources.forEach((s,j)=>{const x=210+j*408,q=phase(u,.32+j*.06,.64+j*.06);c.save();c.globalAlpha=q;k.icon(c,'database',x+90,715,67);label(c,k,s,x,855,360,31,k.CREAM,500);c.restore()});
 }else if(i===2){
  const cy=610;p.sources.forEach((s,j)=>{const y=280+j*177;k.icon(c,'database',145,y,55);label(c,k,s,236,y+42,410,34);route(c,k,[[620,y+31],[760,y+31],[900,cy]],u,{delay:j*.06,width:3})});
  c.fillStyle='#332719E6';c.beginPath();c.arc(930,cy,128,0,TAU);c.fill();c.strokeStyle=k.GOLD;c.lineWidth=2;c.stroke();label(c,k,'통합 조회',843,cy+13,220,38,k.GOLD,600);
  route(c,k,[[1060,cy],[1220,cy],[1220,490],[1310,490]],u,{delay:.25,width:4});surface(c,k,1300,300,470,613,{alpha:.83});label(c,k,'분석 결과 확인',1333,371,405,34,k.GOLD,600);abstractRows(c,k,1338,440,392,390,cap((u-.2)/.8),6,{selected:Math.min(5,Math.floor(u*6))});
 }else if(i===3){
  label(c,k,'Wafer Map',270,286,700,43,k.GOLD,600);k.wafer(c,585,630,315,phase(u,.02,.72)*2.15,{seed:17});
  label(c,k,'그래프',1060,286,700,43,k.GOLD,600);plot(c,k,1060,365,690,480,cap((u-.16)/.84),{seed:11});
  route(c,k,[[915,630],[1000,630],[1000,510],[1040,510]],u,{delay:.28,width:2});
 }else{
  label(c,k,'분석 결과 확인',180,295,930,43,k.GOLD,600);k.wafer(c,570,650,285,phase(u,.02,.72)*2.25,{seed:17});
  const labs=['분석 결과 확인','분석 접근성 향상','더 빠른 의사결정'];labs.forEach((s,j)=>{const y=410+j*178,q=phase(u,.12+j*.12,.49+j*.12);c.save();c.globalAlpha=q;k.line(c,1055,y+35,1735,y+35,1,'#D4AF7C55',1);label(c,k,s,1095,y,650,43,j===2?k.GOLD:k.CREAM,j===2?700:500);c.restore();route(c,k,[[855,650],[995,650],[995,y-13],[1060,y-13]],u,{delay:.17+j*.09,width:2})});
 }
}
function inline(c,p,i,u,k){
 shade(c,k,.59);
 if(i===1){
  label(c,k,'C&C Inline Data',180,288,1020,43,k.GOLD,600);surface(c,k,185,350,1080,365,{alpha:.88});abstractRows(c,k,226,407,995,264,u,5,{selected:Math.min(4,Math.floor(phase(u,.12,.84)*5))});
  k.icon(c,'doc',1465,392,108);label(c,k,'GoodDocs',1352,587,410,37,k.GOLD,600);route(c,k,[[1280,535],[1430,535]],u,{delay:.12,width:3});
  query(c,k,'Spec-out 사례의 관련 정보를 분석합니다.',165,791,1600,142,u,{size:41});
 }else if(i===2){
  const labs=['C&C Inline Data','GoodDocs 매핑','관련 공정 데이터'],xs=[140,752,1365];
  labs.forEach((s,j)=>{label(c,k,s,xs[j],294,460,35,k.GOLD,600);k.icon(c,j===1?'doc':'database',xs[j]+150,335,68)});
  for(let row=0;row<5;row++){const y=500+row*88,q=phase(u,.04+row*.05,.4+row*.05);[140,752,1365].forEach((x,j)=>{c.fillStyle=j===1?'#D4AF7C66':'#F2EEE744';c.fillRect(x+25,y,400*q,10);c.fillStyle='#F2EEE722';c.fillRect(x+25,y+25,280*q,6)});
   const dy=(row-2)*17;route(c,k,[[565,y+5],[680,y+5],[752,y+5+dy]],u,{delay:row*.045,width:2});route(c,k,[[1177,y+5+dy],[1270,y+5],[1390,y+5]],u,{delay:.13+row*.045,width:2})}
  route(c,k,[[978,444],[978,954]],u,{delay:.06,width:1.4});
 }else if(i===3){
  label(c,k,'상관관계 분석',145,287,1110,44,k.GOLD,600);plot(c,k,150,355,1110,520,u,{scatter:true,seed:41});
  label(c,k,'연계 공정',1350,287,425,39,k.GOLD,600);['관련 공정 데이터','GoodDocs 매핑','연계 공정 선별'].forEach((s,j)=>{const y=400+j*179,q=phase(u,.12+j*.12,.48+j*.12);c.save();c.globalAlpha=q;k.icon(c,'doc',1350,y,44);label(c,k,s,1414,y+38,350,30);k.line(c,1350,y+82,1778,y+82,1,'#D4AF7C66',1);c.restore()});
 }else{
  label(c,k,'분석 결과 시각화',145,287,1550,44,k.GOLD,600);plot(c,k,150,370,890,440,u,{seed:41});
  const labs=['분석 결과 시각화','연계 공정 선별','분석 시간 단축'];labs.forEach((s,j)=>{const y=386+j*175,q=phase(u,.12+j*.11,.5+j*.11);c.save();c.globalAlpha=q;label(c,k,s,1230,y+30,550,40,j===2?k.GOLD:k.CREAM,j===2?700:500);k.line(c,1228,y+70,1765,y+70,1,'#D4AF7C55',1);c.restore();route(c,k,[[1060,590],[1150,590],[1150,y],[1208,y]],u,{delay:.14+j*.07,width:2})});
  label(c,k,'의사결정 지원',160,946,1500,45,k.GOLD,600);
 }
}

const drawByKey={infra,thinfilm,working,architecture,monitoring,inline};
/** Draw only an owned task; the caller supplies its approved photo first. */
export function drawEarlyTask(c,p,index,t,d,assets,section,k){
 if(!drawByKey[p.key])return false;
 const u=cap(t/Math.max(.01,d));c.save();c.textBaseline='alphabetic';c.textAlign='left';c.beginPath();c.rect(80,190,1760,830);c.clip();
 if(index>0)drawByKey[p.key](c,{...p,reference:assets.images?.[section.reference_image]},index,u,k);
 c.restore();return true;
}

const plan={
 infra:[
  ['Photographic manual-monitor search; no extra windows','One restrained focus gesture follows the physical work surfaces',[400,300,1220,600]],
  ['Wide integrated-app workbench','Five source menus appear; selection moves down while the shared record view fills',[160,350,1550,540]],
  ['Full-width five-source data lineage','Source-to-center paths draw, data travels, and source graphs reveal',[160,260,1610,720]],
  ['Large analytical plot and related-source register','Plot draws left-to-right; related rows reveal; reading cursor traverses the graph',[145,340,1610,510]],
  ['Large time comparison with physical clock arcs','Approved old/new durations hold while the arrow and clock arcs complete',[150,360,1600,550]]
 ],
 thinfilm:[
  ['Original lab/monitor photograph','One physical screen focus travels along the approved pointing gesture',[520,340,1070,400]],
  ['Four functional workspace regions','Lot, equipment, FDC, DOE regions reveal and their data diagrams complete',[120,235,1675,700]],
  ['Four large actual function visualizations','Trend draws, status ring fills, FDC bars grow, DOE grid reveals sequentially',[120,235,1675,700]],
  ['Large unfolded DOE report and shared-user constellation','Report graph draws, update highlights and lines reach successive users',[450,250,1260,670]],
  ['Circular DOE knowledge loop','A single light follows DOE results, analysis method and search-logic nodes',[280,300,1480,650]]
 ],
 working:[
  ['Original paper/meeting-material photograph','A gentle paper-selection underline follows the document work area',[420,640,1100,300]],
  ['Wide search composer and fanned physical documents','Question types; four results arrive and settle as individual papers',[135,240,1650,710]],
  ['Open paired document pages with linked reference margins','Source highlights travel into the selected content; paper lines reveal',[140,255,1320,715]],
  ['Issue register opening a related document','List rows assemble, one neutral selection moves and opens its related paper',[140,340,1640,590]],
  ['Document-centered human collaboration','Information routes complete from the central document to three people',[320,330,1260,510]]
 ],
 architecture:[
  ['Original research/reference-material photograph','A restrained focus moves between the physical papers and monitor',[520,360,980,520]],
  ['Depth-staggered knowledge archive','Prior evidence papers unfold and incomplete knowledge routes join',[130,300,1650,650]],
  ['Explicit approved Plan/Recipe question and evidence pages','Question types once, then connections lead to four source documents',[150,260,1620,690]],
  ['Three Plan candidates with separate evidence documents','Candidates reveal in order; each connects to its supporting record',[140,340,1640,650]],
  ['Evidence routes toward photographed wafer workspace','Three documented knowledge sources feed the visible physical result area',[160,340,1590,580]]
 ],
 monitoring:[
  ['Original multi-monitor data-lookup photograph','A slow read focus crosses physical system screens',[580,380,1070,360]],
  ['Large natural-language composer with source identifiers','Question types, one send action completes, source identifiers reveal',[170,390,1580,490]],
  ['Asymmetric source-to-agent-to-result pipeline','Four sources flow into one lookup junction and continue to result rows',[145,280,1625,630]],
  ['Wafer Map dominates; one large graph balances the right','Wafer cells reveal and scan; graph draws after the map',[260,315,1490,630]],
  ['Wafer result and readable decision-support outcomes','Map scans once; result routes and outcome text reveal sequentially',[270,365,1480,550]]
 ],
 inline:[
  ['Original Inline data-review photograph','A read focus moves along existing table/condition regions',[630,350,940,430]],
  ['Large data table with low analysis-request strip','Conditions/table rows highlight; approved generic analysis request types',[160,350,1600,590]],
  ['Full-width record-to-GoodDocs-to-process ribbon mapping','Unnumbered record rows assemble and mapping routes travel left-to-right',[140,335,1640,610]],
  ['Large unnumbered correlation plane and process register','Scatter points build and related-process entries appear in order',[145,350,1630,550]],
  ['Analysis curve connecting to process-selection outcomes','Curve and branches draw; outcome fields settle without new performance figures',[145,355,1630,600]]
 ]
};
export const earlyVisualPlan=Object.entries(plan).flatMap(([profile,cuts])=>cuts.map(([layout,motion,motionFocus],cutIndex)=>({
 profile,sectionId:sourceInfo[profile][0],cutIndex,layout:cutIndex===0?'Approved photograph and retained header only':layout,motion:cutIndex===0?'Existing photograph camera drift only; no decorative focus mark or cursor':motion,motionFocus:cutIndex===0?null:motionFocus,decorativeOverlay:cutIndex===0?false:undefined,
 source:{md:'reference/'+sourceInfo[profile][1],image:'reference/'+sourceInfo[profile][2],cut:'CUT '+(cutIndex+1)}
})));
