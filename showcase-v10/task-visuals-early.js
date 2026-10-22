/* Six task-specific, deterministic compositions.
 * The latest direct-user Revision8 brief governs current functions and metrics;
 * source-qualified values and future plans remain explicitly distinguished. The caller paints the
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

function factCard(c,k,x,y,w,h,heading,value,notes,u=1){
 c.save();c.globalAlpha=phase(u,.04,.30);surface(c,k,x,y,w,h,{alpha:.94});
 label(c,k,heading,x+34,y+64,w-68,40,k.CREAM,700);
 label(c,k,value,x+34,y+186,w-68,82,k.GOLD,700);
 notes.forEach((note,j)=>label(c,k,note,x+34,y+263+j*53,w-68,33,j===0?k.GOLD:k.CREAM,600));c.restore();
}

function infra(c,p,i,u,k){
 shade(c,k,.62);
 const sources=['Lot·장비 이력','Inline 데이터','공정 수순','Recipe','연계공정 정보'];
 if(i===1){
  surface(c,k,130,235,1660,710,{alpha:.93});label(c,k,'조회·추출',180,302,460,43,k.GOLD,700);
  sources.forEach((name,j)=>{const y=359+j*105,q=phase(u,.03+j*.07,.38+j*.07);c.save();c.globalAlpha=q;surface(c,k,170,y,400,82,{alpha:.85,r:10});k.icon(c,'database',194,y+17,38);label(c,k,name,255,y+53,280,31);c.restore()});
  const row=Math.min(4,Math.floor(phase(u,.26,.95)*5));c.strokeStyle=k.GOLD;c.lineWidth=2;c.strokeRect(167,359+row*105,406,82);
  label(c,k,'Lot·장비 이력과 Inline',655,309,1000,36,k.GOLD,600);abstractRows(c,k,655,371,1050,475,u,6,{selected:row});route(c,k,[[580,400+row*105],[620,400+row*105],[620,520],[650,520]],u,{width:3});
 }else if(i===2){
  const nodes=[['Lot 이력',170,260],['장비 이력',1390,260],['Inline 데이터',170,650],['Recipe',1390,650],['공정 수순',760,825]];
  nodes.forEach(([name,x,y],j)=>{route(c,k,[[x+180,y+100],[960,y+100],[960,610]],u,{delay:j*.055,width:2.4});surface(c,k,x,y,360,145,{alpha:.88});label(c,k,name,x+28,y+52,310,32,k.GOLD,600);abstractRows(c,k,x+28,y+83,300,45,u,2)});
  c.fillStyle='#251D13DD';c.beginPath();c.arc(960,610,154,0,TAU);c.fill();c.strokeStyle=k.GOLD;c.lineWidth=2;c.stroke();k.icon(c,'database',917,525,80);label(c,k,'정보 연계',843,671,245,38,k.GOLD,700);
 }else if(i===3){
  label(c,k,'Lot 간 차이 비교',145,285,1100,44,k.GOLD,700);surface(c,k,145,335,1140,570);
  ['비교 항목','기준 Lot','비교 Lot'].forEach((name,j)=>label(c,k,name,[185,590,930][j],406,[330,290,290][j],35,k.GOLD));
  ['공정 수순','장비','Recipe'].forEach((name,j)=>{const y=500+j*135,q=phase(u,.04+j*.13,.45+j*.13);c.save();c.globalAlpha=q;label(c,k,name,185,y,330,38);abstractRows(c,k,590,y-15,260,65,u,2,{selected:j===Math.floor(u*3)?0:-1});abstractRows(c,k,930,y-15,260,65,u,2,{selected:j===Math.floor(u*3)?0:-1});k.line(c,175,y+75,1250,y+75,1,'#D4AF7C44',1);c.restore()});
  label(c,k,'공정 결과 해석에 집중',1350,360,440,37,k.GOLD,700);['자료 수집 부담 완화','차이 확인','해석 지원'].forEach((name,j)=>{const y=500+j*165;route(c,k,[[1285,620],[1320,620],[1320,y],[1360,y]],u,{delay:.13+j*.08});label(c,k,name,1370,y+38,405,31)});
 }else{
  label(c,k,'Lot 1건 분석 시간',145,284,1550,43,k.GOLD,600);k.line(c,145,320,1775,320,phase(u,.03,.35),'#D4AF7C66',2);
  label(c,k,'기존 약',165,430,630,45);label(c,k,'2시간 40분',165,587,710,108,k.CREAM,700);label(c,k,'개선 후',1120,430,640,45,k.GOLD);label(c,k,'20분 이내',1110,602,680,128,k.GOLD,700);
  route(c,k,[[760,540],[1060,540]],u,{delay:.1,width:6});k.line(c,1028,516,1060,540,phase(u,.48,.74),k.GOLD,6);k.line(c,1028,564,1060,540,phase(u,.48,.74),k.GOLD,6);
  [[440,785,1],[1430,785,.125]].forEach(([x,y,f])=>{c.strokeStyle='#D4AF7C55';c.lineWidth=8;c.beginPath();c.arc(x,y,84,0,TAU);c.stroke();c.strokeStyle=k.GOLD;c.beginPath();c.arc(x,y,84,-Math.PI/2,-Math.PI/2+TAU*f*phase(u,.14,.88));c.stroke()});
  label(c,k,p.cutCount===4?'추가 개발 계획  |  자동 보고 · 고도화 연구 지원 Agent':'자료 수집·정리 부담 완화',145,987,1630,36,k.CREAM,600);
 }
}

function thinfilm(c,p,i,u,k){
 shade(c,k,.60);
 if(i===1||i===2){
  const names=i===1?['Lot 현황','장비 현황','FDC 모니터링','공유 DOE']:['Lot 모니터링 Trend','장비 모니터링 Trend','FDC Trend','공유 DOE 결과'];
  names.forEach((s,j)=>{const x=125+(j%2)*855,y=235+Math.floor(j/2)*365,local=cap((u-j*.055)/(1-j*.055));surface(c,k,x,y,815,328,{alpha:.90,r:14});label(c,k,s,x+34,y+56,745,37,k.GOLD,600);
   if(j===1){const cx=x+407,cy=y+210,r=86;c.strokeStyle='#D4AF7C30';c.lineWidth=26;c.beginPath();c.arc(cx,cy,r,0,TAU);c.stroke();c.strokeStyle=k.GOLD;c.beginPath();c.arc(cx,cy,r,-Math.PI/2,-Math.PI/2+TAU*phase(local,.04,.87));c.stroke()}
   else if(j===3){for(let a=0;a<10;a++)for(let b=0;b<4;b++){const q=phase(local,.04+(a+b)*.025,.4+(a+b)*.025);c.fillStyle='rgba(212,175,124,'+q*(.12+.6*k.hash(a*7+b))+')';c.fillRect(x+38+a*73,y+99+b*47,65,40)}}
   else plot(c,k,x+37,y+103,738,190,local,{seed:j*15,bars:j===2});
  });
 }else if(i===3){
  paper(c,k,460,230,835,720,u,'DOE Result');
  c.save();c.beginPath();c.rect(488,400,775,260);c.clip();c.fillStyle='#E8E3D8';c.fillRect(488,400,775,260);plot(c,k,515,420,720,210,u,{seed:5});c.restore();
  label(c,k,'DOE 결과 업데이트',500,744,720,32,'#76592E',600);label(c,k,'구성원이 함께 확인',500,804,720,32,'#27313A',500);
  const people=[[1510,340],[1640,620],[1510,855]];people.forEach(([x,y],j)=>{route(c,k,[[1295,590],[1400,590],[x-40,y+25]],u,{delay:.22+j*.07});person(c,k,x,y,60,cap((u-.22-j*.07)/.78))});
  label(c,k,'업데이트·공유',132,328,320,34,k.GOLD,600);label(c,k,'조직의 지식 자산',132,391,320,27);
 }else{
  const cx=640,cy=605,r=253,labels=['DOE 결과','분석 노하우','조직 내 공유'];
  c.strokeStyle='#D4AF7C44';c.lineWidth=2;c.beginPath();c.arc(cx,cy,r,0,TAU);c.stroke();
  labels.forEach((s,j)=>{const a=-Math.PI/2+j*TAU/3,x=cx+Math.cos(a)*r,y=cy+Math.sin(a)*r;c.save();c.globalAlpha=phase(u,j*.11,.4+j*.11);c.fillStyle='#1A1712';c.beginPath();c.arc(x,y,80,0,TAU);c.fill();c.strokeStyle=k.GOLD;c.stroke();k.icon(c,'doc',x-20,y-33,43);label(c,k,s,x-135,y+80,270,31,k.GOLD,600);c.restore()});
  const a=-Math.PI/2+TAU*phase(u,.08,.94);k.glow(c,cx+Math.cos(a)*r,cy+Math.sin(a)*r,38,.28);
  textLines(c,k,'모니터링 Trend ·\nDOE 결과 공유',1110,430,675,49,k.GOLD,700);textLines(c,k,'평가 결과와 분석 노하우를\n조직의 지식 자산으로',1110,650,675,34,k.CREAM,500);
 }
}
function working(c,p,i,u,k){
 shade(c,k,.46);const sources=['분석 데이터','여러 표','관련 자료','참고 문서'];
 if(i===1){
  surface(c,k,135,235,1650,128);label(c,k,'Working Board에 데이터 등록',175,318,1565,48,k.GOLD,700);
  sources.forEach((name,j)=>{const x=145+j*422;paper(c,k,x,465+(j%2)*28,355,480,u,name,{angle:(j-1.5)*.026,delay:.06+j*.06});route(c,k,[[x+177,465],[x+177,410],[960,410],[960,363]],u,{delay:.14+j*.05,width:2})});
 }else if(i===2){
  query(c,k,'여러 데이터에서 필요한 정보를 추출해 비교해 주세요.',135,235,1650,138,u,{size:42});
  paper(c,k,470,430,550,550,u,'필요한 정보 추출');paper(c,k,1080,430,550,550,u,'여러 데이터 교차 분석');
  label(c,k,'등록 데이터',140,455,290,34,k.GOLD);['등록 자료','표 데이터'].forEach((name,j)=>{const y=580+j*180;k.icon(c,'doc',180,y,60);label(c,k,name,135,y+105,295,31);route(c,k,[[300,y+30],[420,y+30],[470,600+j*90]],u,{delay:.12+j*.08,width:2})});
 }else if(i===3){
  label(c,k,'여러 데이터 교차 분석',140,282,1500,44,k.GOLD,700);
  ['등록 데이터','추출 정보','교차 분석'].forEach((name,j)=>label(c,k,name,150+j*365,355,310,33,k.GOLD,600));
  for(let r=0;r<4;r++){const y=400+r*130,q=phase(u,.03+r*.07,.4+r*.07);c.save();c.globalAlpha=q;k.line(c,140,y+96,1210,y+96,1,'#D4AF7C44',1);for(let j=0;j<3;j++){k.icon(c,'doc',150+j*365,y+10,35);abstractRows(c,k,213+j*365,y+19,260,55,u,2)}c.restore()}
  const choice=Math.min(3,Math.floor(phase(u,.25,.92)*4));c.strokeStyle=k.GOLD;c.lineWidth=2;c.strokeRect(135,391+choice*130,1085,109);paper(c,k,1330,336,445,595,u,'연결된 분석 근거',{delay:.2});route(c,k,[[1220,445+choice*130],[1285,445+choice*130],[1285,620],[1330,620]],u,{delay:.15,width:2});
 }else{
  paper(c,k,750,330,420,440,u,'자료·도메인 지식 관리 기반');[[370,500],[1490,450],[1430,760]].forEach(([x,y],j)=>{person(c,k,x,y,80,cap((u-j*.06)/(1-j*.06)));route(c,k,[[960,540],[mix(960,x,.55),mix(540,y,.55)],[x,y+75]],u,{delay:.1+j*.07,width:3})});
  label(c,k,'분석 자료와 도메인 지식',170,916,1600,49,k.GOLD,700);label(c,k,'함께 관리할 수 있는 기반',170,986,1600,36,k.CREAM,600);
 }
}

function architecture(c,p,i,u,k){
 shade(c,k,.58);
 if(i===1){
  const labs=['HyDisk','Cube','과거 평가 자료','전문가 지식'];
  labs.forEach((s,j)=>{const x=135+j*422,y=345+(j%2?0:72),w=355,h=470;paper(c,k,x,y,w,h,u,s,{angle:(j-1.5)*.019,delay:j*.055});if(j<3)route(c,k,[[x+w,y+240],[x+w+66,y+240],[x+w+66,610],[x+w+96,610]],u,{delay:.2+j*.06,width:2})});
  label(c,k,'관련 지식과 경험',140,284,1500,43,k.GOLD,600);
 }else if(i===2){
  query(c,k,'평가 목적을 입력해 내부 자료를 검색합니다.',150,260,1620,185,u,{size:43});
  ['내부 지식 아카이브','과거 평가 자료','Recipe 근거','전문가 지식'].forEach((s,j)=>{const x=155+j*418,y=615;paper(c,k,x,y,345,337,u,s,{angle:0,delay:.23+j*.055});route(c,k,[[960,445],[960,520],[x+170,520],[x+170,615]],u,{delay:.2+j*.055,width:2})});
 }else if(i===3){
  label(c,k,'Recipe와 근거 자료 제안',140,282,1500,44,k.GOLD,700);
  const labs=['Recipe 제안','근거 자료','평가 계획 지원'];
  labs.forEach((s,j)=>{const x=140+j*575,q=phase(u,j*.07,.36+j*.07);c.save();c.globalAlpha=q;surface(c,k,x,340,490,332,{alpha:.90,r:14});label(c,k,s,x+35,415,400,54,k.GOLD,700);k.icon(c,'doc',x+35,459,60);label(c,k,'관련 근거',x+129,506,300,33);abstractRows(c,k,x+36,560,413,75,u,2);c.restore();
   const evidence=['내부 지식 아카이브','과거 평가 자료','전문가 지식'][j];paper(c,k,x+45,750,400,242,u,evidence,{angle:(j-1)*.016,delay:.18+j*.055});route(c,k,[[x+245,672],[x+245,750]],u,{delay:.15+j*.07,width:3})});
 }else{
  const labs=['과거 평가 자료','Recipe·근거 자료','전문가 지식 축적'];label(c,k,'공정 지식과 경험을 활용',145,288,1510,43,k.GOLD,700);
  labs.forEach((s,j)=>{const y=365+j*175;k.icon(c,'doc',180,y,69);label(c,k,s,288,y+48,510,36);route(c,k,[[745,y+34],[900,y+34],[1040,650]],u,{delay:j*.08,width:3})});
  c.save();c.beginPath();c.ellipse(1370,630,350,250,0,0,TAU);c.clip();
  if(p.reference)k.cover(c,{image:p.reference,crop:[.812,.695,.185,.225]},1020,380,700,500);
  c.restore();c.strokeStyle='#D4AF7C99';c.lineWidth=2;c.beginPath();c.ellipse(1370,630,350,250,0,0,TAU);c.stroke();k.glow(c,1370,630,300,.12);const a=phase(u,.1,.95)*TAU;k.glow(c,1370+Math.cos(a)*345,630+Math.sin(a)*245,28,.28);
  label(c,k,'전문가 지식 축적',980,936,815,45,k.GOLD,700);label(c,k,'담당자 변경 후에도 활용할 기반',980,995,815,32,k.CREAM,600);
 }
}
function monitoring(c,p,i,u,k){
 shade(c,k,.59);const sources=['Smart Factory','공정 데이터','장비 데이터','조회 조건'];
 if(i===1){
  label(c,k,'공정 데이터 자연어 조회',170,308,1560,43,k.GOLD,600);query(c,k,'필요한 공정 데이터를 보여주세요.',170,390,1580,190,u,{size:48});
  sources.forEach((name,j)=>{const x=210+j*408,q=phase(u,.32+j*.06,.64+j*.06);c.save();c.globalAlpha=q;k.icon(c,'database',x+90,715,67);label(c,k,name,x,855,360,31,k.CREAM,500);c.restore()});
 }else if(i===2){
  const cy=610;sources.forEach((name,j)=>{const y=280+j*177;k.icon(c,'database',145,y,55);label(c,k,name,236,y+42,410,34);route(c,k,[[620,y+31],[760,y+31],[900,cy]],u,{delay:j*.06,width:3})});
  c.fillStyle='#332719E6';c.beginPath();c.arc(930,cy,128,0,TAU);c.fill();c.strokeStyle=k.GOLD;c.lineWidth=2;c.stroke();label(c,k,'자연어 조회',820,cy+13,250,37,k.GOLD,600);
  route(c,k,[[1060,cy],[1220,cy],[1220,490],[1310,490]],u,{delay:.25,width:4});surface(c,k,1300,300,470,613,{alpha:.88});label(c,k,'조회 결과',1333,371,405,36,k.GOLD,600);abstractRows(c,k,1338,440,392,390,cap((u-.2)/.8),6,{selected:Math.min(5,Math.floor(u*6))});label(c,k,'Smart Factory 조회 · Excel 수동 가공 부담 완화',145,995,1630,35,k.GOLD);
 }else if(i===3){
  label(c,k,'Wafer Map',270,286,700,43,k.GOLD,600);k.wafer(c,585,630,315,phase(u,.02,.72)*2.15,{seed:17});label(c,k,'그래프',1060,286,700,43,k.GOLD,600);plot(c,k,1060,365,690,480,cap((u-.16)/.84),{seed:11});route(c,k,[[915,630],[1000,630],[1000,510],[1040,510]],u,{delay:.28,width:2});
 }else{
  label(c,k,'수동 가공 부담 완화',145,285,850,43,k.GOLD,600);k.wafer(c,530,650,285,phase(u,.02,.72)*2.25,{seed:17});
  factCard(c,k,980,295,810,520,'공정 데이터 조회·시각화 시간','40% 이상 단축',['','공정·장비 간 협업 지원'],u);
  label(c,k,'자료에 기재된 업무 시간 변화',980,930,810,34,k.CREAM);
 }
}

function inline(c,p,i,u,k){
 shade(c,k,.59);
 if(i===1){
  label(c,k,'분석 조건 입력',145,285,1500,43,k.GOLD,700);
  [['Lot ID',145,785],['메인 공정',995,785]].forEach(([name,x,w])=>{surface(c,k,x,335,w,145);label(c,k,name,x+30,395,w-60,35,k.GOLD);k.line(c,x+30,440,x+w-30,440,phase(u,.05,.55),k.CREAM,2)});
  label(c,k,'데이터 수집·통합',145,570,1300,41,k.GOLD);surface(c,k,145,620,1640,330);abstractRows(c,k,185,675,1560,220,u,4,{selected:Math.min(3,Math.floor(u*4))});route(c,k,[[960,480],[960,555],[960,620]],u,{delay:.13,width:3});
 }else if(i===2){
  const labs=['데이터 수집','데이터 통합','상관·이상치 분석'],xs=[140,752,1365];labs.forEach((name,j)=>{label(c,k,name,xs[j],294,460,35,k.GOLD);k.icon(c,j===2?'search':'database',xs[j]+150,335,68)});
  for(let row=0;row<5;row++){const y=500+row*88,q=phase(u,.04+row*.05,.4+row*.05);xs.forEach((x,j)=>{c.fillStyle=j===1?'#D4AF7C66':'#F2EEE744';c.fillRect(x+25,y,400*q,10);c.fillStyle='#F2EEE722';c.fillRect(x+25,y+25,280*q,6)});const dy=(row-2)*17;route(c,k,[[565,y+5],[680,y+5],[752,y+5+dy]],u,{delay:row*.045,width:2});route(c,k,[[1177,y+5+dy],[1270,y+5],[1390,y+5]],u,{delay:.13+row*.045,width:2})}
 }else if(i===3){
  label(c,k,'상관관계·이상치 분석',145,287,1110,44,k.GOLD,600);plot(c,k,150,355,1080,520,u,{scatter:true,seed:41});label(c,k,'원인공정 후보 랭킹',1290,287,500,36,k.GOLD,700);
  ['상위 검토 후보','다음 검토 후보'].forEach((name,j)=>{const y=400+j*165,q=phase(u,.12+j*.12,.48+j*.12);c.save();c.globalAlpha=q;surface(c,k,1290,y,490,110);label(c,k,name,1320,y+65,430,35);c.restore()});paper(c,k,1290,755,490,205,u,'분석 리포트',{delay:.15});label(c,k,'후보 제시 · 원인 확정 아님',1290,1005,500,32,k.GOLD,700);
 }else{
  paper(c,k,145,240,760,735,u,'분석 리포트');['수집·통합','상관관계·이상치','원인공정 후보'].forEach((name,j)=>label(c,k,name,210,460+j*165,630,38,'#27313A',600));
  factCard(c,k,990,280,800,620,'분석 시간','70% 이상 단축',['','원인공정 후보 랭킹·리포트','후보는 담당자가 검토'],u);
 }
}


// Each wrapper follows the latest task-specific spoken sequence exactly. The
// photographic first cut is still exclusively owned by the caller.
function phaseInfra(c,p,i,u,k){
 if(i<4)return infra(c,p,({1:1,2:3,3:4})[i],u,k);
 ['Lot·장비 이력','Inline 데이터','Lot 간 차이 비교'].forEach((name,j)=>{const y=310+j*185;surface(c,k,145,y,580,125);label(c,k,name,175,y+77,520,38,k.GOLD);route(c,k,[[725,y+62],[860,y+62],[860,590],[995,590]],u,{delay:j*.09})});
 surface(c,k,995,330,790,460);label(c,k,'공정 결과 해석에 집중',1035,430,710,49,k.GOLD,700);abstractRows(c,k,1035,520,700,210,u,4);label(c,k,'자료 수집·정리 부담 감소',1035,745,710,35);
 surface(c,k,145,900,1640,110);label(c,k,'추가 개발 계획  |  자동 보고 · 고도화 연구 지원 Agent',180,970,1570,35,k.CREAM,600);
}
function phaseThinfilm(c,p,i,u,k){
 if(i===1){thinfilm(c,p,2,u,k);label(c,k,'웹 플랫폼 통합 조회',145,1005,1630,36,k.GOLD,700);return}if(i===2)return thinfilm(c,p,3,u,k);if(i===4)return thinfilm(c,p,4,u,k);
 ['Lot 현황','장비 현황','FDC'].forEach((name,j)=>{const x=150+j*560;surface(c,k,x,265,490,150);label(c,k,name,x+28,354,430,44,k.GOLD);route(c,k,[[x+245,415],[x+245,490],[960,490],[960,570]],u,{delay:j*.08})});
 surface(c,k,510,570,900,270);label(c,k,'웹 플랫폼 통합 조회',550,635,820,45,k.GOLD,700);abstractRows(c,k,550,695,810,115,u,3);label(c,k,'시스템 이동 감소 · 데이터 가공 부담 감소',150,970,1630,42,k.GOLD,700);
}
function phaseWorking(c,p,i,u,k){
 if(i===1||i===2||i===4){working(c,p,i,u,k);if(i===2)route(c,k,[[1020,660],[1080,660]],u,{delay:.25,width:4});return}
 surface(c,k,400,250,1120,175);label(c,k,'데이터 조회 창구 단일화',445,357,1030,58,k.GOLD,700);
 ['등록 데이터','추출 정보','여러 표','참고 자료'].forEach((name,j)=>{const x=145+j*422;paper(c,k,x,565,355,350,u,name,{delay:j*.06});route(c,k,[[x+177,565],[x+177,485],[960,485],[960,425]],u,{delay:.15+j*.06})});label(c,k,'파일 탐색·반복 취합 부담 감소',150,995,1630,42,k.GOLD,700);
}
function phaseArchitecture(c,p,i,u,k){
 if(i===1){architecture(c,p,2,u,k);label(c,k,'평가 목적 입력 · 내부 지식 아카이브 검색',150,229,1620,35,k.GOLD);return}
 if(i===2)return architecture(c,p,3,u,k);if(i===4)return architecture(c,p,4,u,k);
 ['Recipe 제안','관련 근거 자료'].forEach((name,j)=>{const y=355+j*290;paper(c,k,145,y,560,240,u,name,{delay:j*.10});route(c,k,[[705,y+120],[815,y+120],[815,600],[920,600]],u,{delay:.15+j*.10})});
 paper(c,k,920,255,850,640,u,'평가 계획 수립 지원',{delay:.12});label(c,k,'평가 계획 수립 지원',980,402,730,49,'#27313A',700);label(c,k,'자료 탐색·구두 문의 의존 감소',145,995,1630,40,k.GOLD,700);
}
function phaseMonitoring(c,p,i,u,k){
 if(i===1)return monitoring(c,p,1,u,k);if(i===2){monitoring(c,p,3,u,k);label(c,k,'수동 가공 간소화',270,970,1450,39,k.GOLD,700);return}if(i===3){monitoring(c,p,4,u,k);if(p.cutCount===4)label(c,k,'향후 계획  |  챗봇 자동 알림 · Reporting',145,1005,1630,35,k.GOLD,600);return}
 label(c,k,'공정·장비 간 협업 지원',145,285,1600,46,k.GOLD,700);k.wafer(c,540,650,285,phase(u,.02,.72)*2.25,{seed:17});
 surface(c,k,990,340,800,280);label(c,k,'데이터 접근·시각화 부담 감소',1025,425,730,38,k.CREAM,600);abstractRows(c,k,1025,500,720,85,u,2);route(c,k,[[840,650],[910,650],[910,480],[990,480]],u,{delay:.15});
 surface(c,k,990,715,800,275);label(c,k,'향후 계획',1025,790,730,39,k.GOLD,700);label(c,k,'챗봇 자동 알림',1025,868,730,44);label(c,k,'Reporting',1025,943,730,44);
}
function phaseInline(c,p,i,u,k){
 if(i<4)return inline(c,p,({1:1,2:3,3:4})[i],u,k);
 ['수집·통합','상관·이상치 분석','원인공정 후보 랭킹','리포트'].forEach((name,j)=>{const x=145+j*420;surface(c,k,x,300,370,150);label(c,k,name,x+22,388,326,35,k.GOLD);if(j<3)route(c,k,[[x+370,375],[x+420,375]],u,{delay:j*.08})});
 surface(c,k,350,600,1220,340);label(c,k,'분석 기준 일관 적용',395,685,1130,52,k.GOLD,700);label(c,k,'원인공정 후보 ≠ 확정 원인',395,790,1130,57,k.CREAM,700);label(c,k,'담당자가 후보를 검토',395,878,1130,38,k.GOLD,600);
}
export const earlyRevision9Contract={revision:9,metricCutIndex:3,effectCutIndex:4,metricTasks:['task3','task8','task9'],cutCounts:{task3:4,task4:5,task5:5,task7:5,task8:4,task9:5},roles:['manual_before','input_collection','analysis_action','result_metric','effect_limitations_future'],lastCutCaveats:{task3:'future_auto_reporting_and_advanced_research_agent',task8:'future_chatbot_alerts_and_reporting'},firstPhotoTitleOverlay:true,standaloneTaskTitles:false,source:'spec.json',brief:'reference/user-revision9-brief.json'};
// Kept as an import alias for the existing native audit tooling.
export const earlyRevision8Contract=earlyRevision9Contract;
const drawByKey={infra:phaseInfra,thinfilm:phaseThinfilm,working:phaseWorking,architecture:phaseArchitecture,monitoring:phaseMonitoring,inline:phaseInline};

/** Draw only an owned task; the caller supplies its approved photo first. */
export function drawEarlyTask(c,p,index,t,d,assets,section,k){
 if(!drawByKey[p.key])return false;
 const u=cap(t/Math.max(.01,d));c.save();c.textBaseline='alphabetic';c.textAlign='left';c.beginPath();c.rect(80,190,1760,830);c.clip();
 if(index>0)drawByKey[p.key](c,{...p,cutCount:section.cuts.length,reference:assets.images?.[section.reference_image]},index,u,k);
 c.restore();return true;
}

const revision8Layouts={"infra":["Lot별 분산 정보 조사","앱에서 조회·추출","Lot 간 차이 비교","Lot 1건 분석 시간 변화","해석 집중과 추가 개발 계획"],"thinfilm":["분산 조회와 개인별 평가 결과","웹에서 현황 통합 조회","DOE 결과 공동 확인","시스템 이동과 가공 부담 감소","평가 결과와 노하우 공유"],"working":["파일 탐색과 수동 취합","Working Board에 데이터 등록","자연어 추출과 교차 분석","데이터 조회 창구 단일화","자료와 도메인 지식 함께 관리"],"architecture":["흩어진 자료와 전문가 의존","평가 목적을 입력","Recipe와 근거를 함께 제안","평가 계획 수립 지원","전문가 지식을 지속 활용"],"monitoring":["개별 조회와 엑셀 가공","자연어로 공정 데이터 조회","Wafer Map과 그래프 시각화","업무 시간 변화","협업 지원과 향후 계획"],"inline":["Spec out 이후 수동 조사","Lot ID와 메인 공정 입력","분석부터 후보와 리포트까지","분석 시간 변화","일관된 원인 탐색 지원"]};
const plan={
 infra:[
  ['Photographic manual-monitor search; no extra windows','One restrained focus gesture follows the physical work surfaces',[400,300,1220,600]],
  ['Wide integrated-app workbench','Five source menus appear; selection moves down while the shared record view fills',[160,350,1550,540]],
  ['Full-width five-source data lineage','Source-to-center paths draw, data travels, and source graphs reveal',[160,260,1610,720]],
  ['Lot route, equipment and Recipe comparison','Three comparison rows reveal between reference and comparison Lot data',[145,340,1610,510]],
  ['Source-qualified Lot time comparison and separate future plan','The time arrow completes; automatic reporting and advanced research Agent remain future plans',[150,360,1600,550]]
 ],
 thinfilm:[
  ['Original lab/monitor photograph','One physical screen focus travels along the approved pointing gesture',[520,340,1070,400]],
  ['Four functional workspace regions','Lot, equipment, FDC, DOE regions reveal and their data diagrams complete',[120,235,1675,700]],
  ['Four large actual function visualizations','Trend draws, status ring fills, FDC bars grow, DOE grid reveals sequentially',[120,235,1675,700]],
  ['Large unfolded DOE report and shared-user constellation','Report graph draws, update highlights and lines reach successive users',[450,250,1260,670]],
  ['Shared DOE knowledge loop','A light follows DOE results, analysis knowledge and organization sharing',[280,300,1480,650]]
 ],
 working:[
  ['Original paper/meeting-material photograph','A gentle paper-selection underline follows the document work area',[420,640,1100,300]],
  ['Working Board registration and source documents','Registered data and source documents flow into the board',[135,240,1650,710]],
  ['Natural-language extraction with paired source pages','A natural-language request connects registered data to extracted information',[140,255,1320,715]],
  ['Cross-analysis register with linked evidence','Registered data and extracted information connect through comparison rows',[140,340,1640,590]],
  ['Document-centered human collaboration','Information routes complete from the central document to three people',[320,330,1260,510]]
 ],
 architecture:[
  ['Original research/reference-material photograph','A restrained focus moves between the physical papers and monitor',[520,360,980,520]],
  ['Depth-staggered knowledge archive','Prior evidence papers unfold and incomplete knowledge routes join',[130,300,1650,650]],
  ['Explicit approved Plan/Recipe question and evidence pages','Question types once, then connections lead to four source documents',[150,260,1620,690]],
  ['Recipe, evidence and evaluation-plan support','The three supported functions reveal beside their source documents',[140,340,1640,650]],
  ['Evidence routes toward photographed wafer workspace','Three documented knowledge sources feed the visible physical result area',[160,340,1590,580]]
 ],
 monitoring:[
  ['Original multi-monitor data-lookup photograph','A slow read focus crosses physical system screens',[580,380,1070,360]],
  ['Large natural-language composer with source identifiers','Question types, one send action completes, source identifiers reveal',[170,390,1580,490]],
  ['Asymmetric source-to-agent-to-result pipeline','Four sources flow into one lookup junction and continue to result rows',[145,280,1625,630]],
  ['Wafer Map dominates; one large graph balances the right','Wafer cells reveal and scan; graph draws after the map',[260,315,1490,630]],
  ['Wafer result, qualified time reduction and separate future plan','The map scans beside a qualified 40-percent time card; alerts and Reporting remain future plans',[270,365,1480,550]]
 ],
 inline:[
  ['Original Inline data-review photograph','A read focus moves along existing table/condition regions',[630,350,940,430]],
  ['Lot ID and main-process inputs above collected data','Input fields activate and data collection/integration rows assemble',[160,350,1600,590]],
  ['Collection-to-integration-to-analysis ribbon','Unnumbered data rows and correlation/outlier routes travel left-to-right',[140,335,1640,610]],
  ['Correlation plane and candidate-cause ranking','Analysis points build; candidate ranks appear without confirming a cause',[145,350,1630,550]],
  ['Analysis report and source-qualified time card','Report sections reveal beside a qualified 70-percent time-reduction figure',[145,355,1630,600]]
 ]
};
export const earlyVisualPlan=Object.entries(plan).flatMap(([profile,cuts])=>cuts.slice(0,earlyRevision9Contract.cutCounts[sourceInfo[profile][0]]).map(([layout,motion,motionFocus],cutIndex)=>({
 profile,sectionId:sourceInfo[profile][0],cutIndex,role:cutIndex===3&&['infra','monitoring'].includes(profile)?'result_metric_with_future_caveat':earlyRevision9Contract.roles[cutIndex],layout:cutIndex===0?'Approved photograph with fading task introduction and persistent header':revision8Layouts[profile][cutIndex],motion:cutIndex===0?'Caller-owned rigid photograph camera move; introduction fades within this voiced cut':'Explicit scene-time progression: '+revision8Layouts[profile][cutIndex],motionFocus:cutIndex===0?null:cutIndex===3&&['infra','monitoring'].includes(profile)?[145,285,1640,730]:motionFocus,decorativeOverlay:cutIndex===0?false:undefined,
 source:{content:'spec.json',brief:'reference/user-revision9-brief.json',md:'reference/'+sourceInfo[profile][1],image:'reference/'+sourceInfo[profile][2],cut:'CUT '+(cutIndex+1)}
})));
