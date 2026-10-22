/* Six task-specific workspaces. All geometry and motion use explicit scene time.
 * The caller paints the approved photograph and persistent 154px title header.
 * Current functions and source-qualified figures follow the latest direct-user
 * Revision8 brief. Example IDs, invented measurements and confirmed-cause claims
 * are not added; future plans and human review remain explicit.
 */
const keys=['snm','expense','daily','cubic','tcad','plug'];
const sources={
 snm:['task11','11.RD_공정_AI_Fast_Track_장민희TL_RSAB_SNM_Overlay_영상제작_MD.md','1791965410736.png'],
 expense:['task12','12. RD_공정_AI_Fast_Track_오승재TL_경비분석_절감아이템발굴_MD.md','1791965410805.png'],
 daily:['task13','13. RD_공정_AI_Fast_Track_김도훈TL_Daily_Report_Auto_Mail_System_MD.md','1791965410890.png'],
 cubic:['task14','14. RD_공정_AI_Fast_Track_정현준TL_Cubic공정Lab_App_Agent_MD.md','1791965410941.png'],
 tcad:['task17','17.RD_공정_AI_Fast_Track_김성후TL_TCAD_TEM_Image_Labeling_Tool_MD.md','1791965411046.png'],
 plug:['task16','16.RD_공정_AI_Fast_Track_김지은TL_Plug_대면적데이터분석_MD.md','1791965411099.png']
};
const revision9CutCounts={task11:5,task12:3,task13:5,task14:5,task17:4,task16:5};
const revision8Layouts={"snm":["여러 도구의 반복 조회","Lot ID로 통합 조회","표준 기준으로 진단 지원","분석 시간 변화","근거를 한 화면에서 확인"],"expense":["엑셀 집계와 경험 중심 분석","경비와 장비 이력 연결","증가 원인과 절감 후보 검토","단축 수치와 검증 상태","검토 후보와 확정 실적 구분"],"daily":["매일 반복되는 보고 업무","장비 이력과 계획 수집","오전 6시 표준 보고 메일","보고 작성 시간 변화","검토와 장비 대응에 집중"],"cubic":["여러 시스템과 별도 취합","하나의 앱에서 현황 조회","보고와 근무자 안내 자동화","업무 시간 변화","반복 부담 감소와 데이터 활용"],"tcad":["수동 회전·측정·기록","기울기와 위치 분석","측정 결과와 이력 저장","이미지당 측정 시간 변화","예외 확인과 최종 검증"],"plug":["수동 가공과 육안 검토","계측 데이터 처리 자동화","오계측 후보와 자연어 분석","수집·리뷰 범위 변화","담당자 검토와 향후 확장"]};
const plans={
 snm:[['photographic manual comparison','A manual focus follows the photographed comparison surface.',[420,430,900,470]],['Lot input and five analysis branches','Input focus descends into the five approved analysis menus.',[260,260,1400,640]],['three large wafer maps','Overlay, Residual and MA Bias reveal and scan left to right.',[140,350,1640,570]],['boxplot and wafer comparison','Baseline and input whiskers grow, then the wafer distribution is inspected.',[130,360,1640,570]],['standard diagnosis support and qualified time card','Map, Trend and K-param evidence connect to standard diagnosis support beside source-qualified time figures.',[120,320,1680,610]]],
 expense:[['photographic ledger inspection','A single manual range selection follows ledger rows.',[260,600,1120,330]],['linked cost and equipment history with 22 criteria','Linked records and 22 judgment criteria feed candidate review.',[110,300,1680,630]],['large trend ledger with candidate rail','Trend strokes draw toward the existing saving-candidate labels.',[150,370,1600,560]],['linked criteria and candidate review table','Linked history, judgment criteria and candidates reveal with validation-in-progress status.',[120,320,1680,590]],['qualified analysis-time and validation status','The time figure appears with source attribution, ongoing validation and no confirmed saving amount.',[180,340,1580,560]]],
 daily:[['photographic report writing','A manual reading guide follows the actual paper and screen.',[260,590,1250,350]],['equipment and PM summary into report','Equipment history, PM plans and issue queries feed the standard report.',[130,300,1650,620]],['large white HTML report','Title, summary, equipment chart and issue rows build down the page.',[470,260,980,680]],['scheduled 06:00 HTML report delivery','The standard HTML report feeds a scheduled automatic mail state.',[190,300,1580,610]],['qualified report-writing reduction and human review','20-to-0 minutes and annual 122 hours remain source-qualified beside human review.',[180,320,1580,610]]],
 cubic:[['photographic system switching','A single cursor moves across the photographed work surface.',[520,350,1100,540]],['six-function unified app launcher','Lot, equipment, TEM quota, requests, reports and weekend-staff functions reveal around the app title.',[170,330,1580,560]],['Lot, equipment, reservation and report workbench','Lot rows, equipment badges, reservation slots and report strokes activate in order.',[130,320,1660,640]],['quota and request-led app workflow','The app selection moves into TEM quota/request status and report activity.',[140,330,1650,610]],['unified app and qualified time reduction','Four supported function groups converge into one app beside the qualified 90-percent reduction.',[140,330,1640,570]]],
 tcad:[['photographic manual measurement','A manual bracket is placed on the photographed image work area.',[420,370,1020,570]],['large TEM alignment stage','The real TEM texture rotates gently into alignment beside its tool menu.',[120,280,1600,650]],['image measurements into Raw data','Six measurement brackets draw before the matching Raw data rows reveal.',[120,300,1640,660]],['measurement values, coordinates and saved history','Result rows and measurement-overlay history populate without invented values.',[150,360,1600,580]],['measured image and qualified per-image time','5 minutes to 6 seconds appears with human final verification and error-repair caveats.',[130,330,1610,610]]],
 plug:[['photographic manual tile checking','A manual focus ring follows the photographed large-area image.',[420,390,900,540]],['DD-SEM collection pipeline and real image tiles','Collection, preprocessing and loading lead into image-based candidate detection.',[120,300,1680,640]],['suspect versus normal human review','The suspect detail is selected and the final-judgement control is offered to the person.',[130,340,1650,590]],['natural-language analysis dashboard','The request types and the collected-data/candidate/review dashboard draws.',[150,330,1620,600]],['qualified TAT and single-layer review reduction','The two factual comparisons animate their exact old/new bar ratios with source and single-layer caveats; PROvision remains a future plan.',[140,330,1620,610]]]
};
export const lateVisualPlan=keys.flatMap(profile=>plans[profile].slice(0,revision9CutCounts[sources[profile][0]]).map(([layout,motion,motionFocus],cutIndex)=>({profile,sectionId:sources[profile][0],cutIndex,role:profile==='expense'&&cutIndex===2?'analysis_with_validation_caveat':profile==='tcad'&&cutIndex===3?'result_metric_with_human_validation':['manual_before','input_collection','analysis_action','result_metric','effect_limitations_future'][cutIndex],layout:cutIndex===0?'Approved photograph with fading task introduction and persistent header':revision8Layouts[profile][cutIndex],motion:cutIndex===0?'Caller-owned rigid photograph camera move; introduction fades within this voiced cut':'Explicit scene-time progression: '+revision8Layouts[profile][cutIndex],motionFocus:cutIndex===0?null:profile==='expense'&&cutIndex===2?[130,350,1650,670]:profile==='tcad'&&cutIndex===3?[130,270,1670,740]:motionFocus,decorativeOverlay:cutIndex===0?false:undefined,source:{content:'spec.json',brief:'reference/user-revision9-brief.json',md:`reference/${sources[profile][1]}`,image:`reference/${sources[profile][2]}`,...(profile==='tcad'?{photographicCrop:[.424,.329,.106,.227]}:{})},bodyBounds:[80,190,1760,830],exampleNumbers:false,factualFiguresFromUserBrief:true})));

const progress=(k,u,start=0,end=1)=>k.ease(k.clamp((u-start)/(end-start)));
function writing(c,k,x,y,w,n,q,{gap=42,color='#E7E4DB40'}={}){
 for(let j=0;j<n;j++){const p=progress(k,q,j*.07,.48+j*.07);c.fillStyle=color;c.fillRect(x,y+j*gap,w*(j%3===1?.71:.91)*p,7);}
}
function label(c,k,s,x,y,w=600,size=34,color=k.CREAM,weight=600){k.fit(c,s,x,y,w,size,color,weight);}
function plate(c,k,x,y,w,h,{paper=false}={}){k.panel(c,x,y,w,h,{fill:paper?'#F2EEE7':'#0C1118ed',line:paper?'#D4AF7C99':'#D4AF7C77',radius:paper?5:12});}
function route(c,k,points,q,{color=k.GOLD,width=3}={}){
 const lengths=points.slice(1).map((b,i)=>Math.hypot(b[0]-points[i][0],b[1]-points[i][1])),total=lengths.reduce((a,b)=>a+b,0);let left=total*k.clamp(q),tip=points[0];
 c.save();c.strokeStyle=color;c.lineWidth=width;c.lineCap='round';c.beginPath();c.moveTo(...points[0]);
 for(let i=0;i<lengths.length;i++){const a=points[i],b=points[i+1],p=Math.min(1,left/lengths[i]);tip=[a[0]+(b[0]-a[0])*p,a[1]+(b[1]-a[1])*p];c.lineTo(...tip);left-=lengths[i];if(left<=0)break;}
 c.stroke();if(q>0&&q<1)k.glow(c,...tip,18,.36);c.restore();
}
function pointer(c,k,x,y,alpha=1){c.save();c.globalAlpha=alpha;c.fillStyle=k.CREAM;c.strokeStyle=k.INK;c.lineWidth=1;c.beginPath();c.moveTo(x,y);c.lineTo(x+4,y+25);c.lineTo(x+10,y+16);c.lineTo(x+22,y+16);c.closePath();c.fill();c.stroke();c.restore();}
function outline(c,k,x,y,w,h,q,color=k.GOLD){route(c,k,[[x,y+h],[x,y],[x+w,y],[x+w,y+h],[x,y+h]],q,{color,width:2});}

function scanWafer(c,k,cx,cy,r,u,options={}){
 k.wafer(c,cx,cy,r,1.2,options);const q=progress(k,u,.1,.9),sx=cx-r+2*r*q;c.save();c.beginPath();c.arc(cx,cy,r,0,Math.PI*2);c.clip();const g=c.createLinearGradient(sx-22,0,sx+22,0);g.addColorStop(0,'#FFB34700');g.addColorStop(.5,'#FFF0C755');g.addColorStop(1,'#FFB34700');c.fillStyle=g;c.fillRect(sx-22,cy-r,44,r*2);c.restore();
}
function whiteReport(c,k,x,y,w,h,u,{compact=false}={}){
 c.save();c.shadowColor='#0008';c.shadowBlur=24;c.shadowOffsetY=12;plate(c,k,x,y,w,h,{paper:true});c.shadowBlur=0;c.shadowOffsetY=0;
 const sx=w/1000,sy=h/780;c.translate(x,y);c.scale(sx,sy);const ink='#172332';
 c.save();c.globalAlpha=progress(k,u,0,.18);label(c,k,'Equipment Daily Report',46,76,910,compact?42:48,ink,700);k.line(c,46,103,954,103,1,'#A59C8C',1);c.restore();
 c.save();c.globalAlpha=progress(k,u,.12,.34);label(c,k,'장비 이력·PM 요약',46,162,900,30,ink);writing(c,k,48,193,880,2,progress(k,u,.15,.46),{gap:31,color:'#53616A55'});c.restore();
 c.save();c.globalAlpha=progress(k,u,.26,.49);label(c,k,'장비 이력',46,313,500,30,ink);k.graph(c,54,357,530,240,progress(k,u,.30,.77)*1.35,28,'#577D86');label(c,k,'PM 계획·이슈',642,313,300,30,ink);writing(c,k,642,363,300,6,progress(k,u,.38,.88),{gap:38,color:'#53616A55'});c.restore();
 c.save();c.globalAlpha=progress(k,u,.58,.91);k.line(c,46,661,954,661,1,'#A59C8C',1);writing(c,k,48,694,880,2,progress(k,u,.59,.93),{gap:30,color:'#53616A44'});c.restore();c.restore();
}
function statusTable(c,k,x,y,w,h,u,labels,{heading=null}={}){
 plate(c,k,x,y,w,h);if(heading)label(c,k,heading,x+26,y+47,w-52,34,k.GOLD);
 const top=y+(heading?88:35),gap=(h-(heading?112:60))/labels.length;
 labels.forEach((s,j)=>{const q=progress(k,u,.07+j*.08,.46+j*.08),yy=top+j*gap;c.save();c.globalAlpha=q;label(c,k,s,x+28,yy+30,w*.55,29);writing(c,k,x+w*.58,yy+16,w*.31,1,q,{gap:20});k.line(c,x+24,yy+gap-10,x+w-24,yy+gap-10,1,'#FFFFFF20',1);c.restore();});
}
function factCard(c,k,x,y,w,h,heading,value,notes,u=1){
 c.save();c.globalAlpha=progress(k,u,.04,.30);plate(c,k,x,y,w,h);
 label(c,k,heading,x+32,y+63,w-64,39,k.CREAM,700);
 label(c,k,value,x+32,y+185,w-64,80,k.GOLD,700);
 notes.forEach((note,j)=>label(c,k,note,x+32,y+263+j*54,w-64,33,j===0?k.GOLD:k.CREAM,600));c.restore();
}

function snm(c,p,i,u,k){
 if(i===1){
  plate(c,k,520,225,880,115);label(c,k,'Lot ID',555,294,220,42);k.line(c,745,302,1280,302,progress(k,u,.07,.3),k.GOLD,2);k.icon(c,'search',1300,257,44,k.GOLD);pointer(c,k,1270,315,progress(k,u,.1,.3));
  const menu=[['Overlay Map',340,500],['Residual Map',785,500],['MA Bias Map',1230,500],['Trend 분석',560,740],['K-param 분석',1030,740]];
  menu.forEach(([name,x,y],j)=>{const q=progress(k,u,.19+j*.07,.52+j*.07);route(c,k,[[960,340],[960,410],[x+175,410],[x+175,y]],q);c.save();c.globalAlpha=q;plate(c,k,x,y,350,118);label(c,k,name,x+22,y+72,306,34,k.GOLD);c.restore()});
  label(c,k,'SmartDCP · TAS · Qoniac',250,975,1420,38,k.GOLD,700);
 }else if(i===2){
  ['Overlay','Residual','MA Bias'].forEach((name,j)=>{const x=380+j*580,q=progress(k,u,.03+j*.16,.47+j*.16);c.save();c.globalAlpha=q;label(c,k,name,x-240,295,480,43,k.GOLD,700);scanWafer(c,k,x,610,225,progress(k,u,j*.13,.72+j*.13),{vector:j===0,scatter:j===1,seed:j*23});c.restore()});
 }else if(i===3){
  label(c,k,'한 화면에서 분석 근거 확인',130,270,1000,44,k.GOLD,700);label(c,k,'정상 Baseline / 입력 Wafer',130,323,1000,31);k.line(c,150,895,1125,895,1,'#D4AF7C55',2);
  for(let j=0;j<6;j++){const x=235+j*158,q=progress(k,u,.06+j*.055,.5+j*.055),cy=615+(k.hash(j+2)-.5)*90;for(const[dx,col,span]of[[-27,'#738F9C',96],[27,k.AMBER,120]]){k.line(c,x+dx,cy-span,x+dx,cy+span,q,col,2);k.line(c,x+dx-18,cy-span,x+dx+18,cy-span,q,col,2);k.line(c,x+dx-18,cy+span,x+dx+18,cy+span,q,col,2);c.fillStyle=col;c.globalAlpha=q*.62;c.fillRect(x+dx-22,cy-span*.4,44,span*.8);c.globalAlpha=1;}}
  label(c,k,'표준 진단 기준으로 비교',1230,323,570,35,k.GOLD);label(c,k,'반복 조회·설정 감소',130,995,900,35,k.GOLD);label(c,k,'Map · Trend · K-param 근거',1080,995,710,32,k.GOLD);scanWafer(c,k,1510,650,245,progress(k,u,.35,.98),{scatter:true,seed:27});
 }else{
  label(c,k,'원인 분석·솔루션 제시 지원',120,268,1660,43,k.GOLD,700);
  ['Map 분석 근거','Trend 분석 근거','K-param','표준 진단 기준'].forEach((name,j)=>{const y=355+j*142,q=progress(k,u,.04+j*.08,.43+j*.08);c.save();c.globalAlpha=q;plate(c,k,120,y,630,105);label(c,k,name,150,y+65,570,36);c.restore();route(c,k,[[750,y+52],[870,y+52],[870,620],[1000,620]],q)});
  factCard(c,k,1010,320,790,480,'분석 시간','15분~1시간 → 건당 수분',['자료 기준','반복 조회·설정 부담 완화'],u);
  plate(c,k,1010,845,790,140);label(c,k,'표준 진단을 통한 분석 지원',1040,900,730,34,k.GOLD);label(c,k,'근거 확인 · 담당자 검토',1040,958,730,34);
 }
}

function expense(c,p,i,u,k){
 const sources=['경비 실적','장비 이력','22개 판단 지표','절감 검토 후보'];
 if(i===1){
  sources.forEach((name,j)=>{const y=280+j*160,q=progress(k,u,.02+j*.09,.4+j*.09);c.save();c.globalAlpha=q;plate(c,k,120,y,480,117);label(c,k,name,145,y+47,430,31,k.GOLD);writing(c,k,145,y+74,420,1,q);c.restore();route(c,k,[[600,y+59],[760,y+59],[920,600]],q)});
  c.save();c.globalAlpha=progress(k,u,.21,.58);c.fillStyle='#35271A';c.strokeStyle=k.GOLD;c.lineWidth=2;c.beginPath();c.arc(940,600,120,0,Math.PI*2);c.fill();c.stroke();label(c,k,'연결 분석',840,610,200,34,k.GOLD);c.restore();route(c,k,[[1060,600],[1190,600],[1260,600]],progress(k,u,.43,.75));
  statusTable(c,k,1260,260,540,680,progress(k,u,.4,1),['비용 증가 원인','실행 가능성','절감 검토 후보'],{heading:'22개 판단 지표'});
 }else if(i===2){
  plate(c,k,105,220,1710,p.cutCount===3?730:755);label(c,k,'경비·장비 이력 연결 분석',145,292,1170,46,k.GOLD,700);k.graph(c,160,390,1125,475,progress(k,u,.07,.82)*1.35,14);
  ['비용 증가 원인','절감 검토 후보','실행 가능성 검토'].forEach((name,j)=>{const y=410+j*185,q=progress(k,u,.3+j*.14,.58+j*.14);route(c,k,[[1235,560],[1330,560],[1375,y]],q);c.save();c.globalAlpha=q;label(c,k,name,1410,y+14,350,35,k.GOLD);writing(c,k,1410,y+52,340,2,q,{gap:32});c.restore()});
 }else if(i===3){
  plate(c,k,110,220,1700,750);k.tabs(c,['연결 이력','판단 지표','후보 검토'],145,250,1630,u,{selected:Math.min(2,Math.floor(u*3))});['검토 항목','분석 근거','검증 상태'].forEach((name,j)=>label(c,k,name,[155,730,1510][j],370,[450,650,270][j],32,k.GOLD));
  ['경비·장비 이력','비용 증가 원인','실행 가능성','절감 검토 후보'].forEach((name,j)=>{const y=410+j*126,q=progress(k,u,.05+j*.08,.4+j*.08);c.save();c.globalAlpha=q;label(c,k,name,155,y+55,500,31);writing(c,k,735,y+38,610,1,q);plate(c,k,1490,y+15,265,63);label(c,k,'검증 중',1520,y+57,205,28,k.GOLD);k.line(c,145,y+106,1775,y+106,1,'#FFFFFF22',1);c.restore()});
 }else{
  statusTable(c,k,120,290,550,640,progress(k,u,0,.8),['경비 실적','장비 이력','절감 검토 후보'],{heading:'연결 분석'});
  factCard(c,k,760,290,1040,640,'분석 시간','80% 이상 단축',['자료 기준','지표·결과 실효성 검증 중','절감액 확정 실적 아님'],u);
 }
}

function daily(c,p,i,u,k){
 if(i===1){
  ['장비 이력','PM 계획','이슈 조회','조회·요약'].forEach((name,j)=>{const y=280+j*165,q=progress(k,u,.03+j*.1,.42+j*.1);c.save();c.globalAlpha=q;k.icon(c,'database',150,y,74,k.GOLD);label(c,k,name,260,y+48,430,43);c.restore();route(c,k,[[650,y+34],[850,y+34],[1020,600]],q)});route(c,k,[[1020,600],[1120,600]],progress(k,u,.4,.76));whiteReport(c,k,1120,250,660,700,progress(k,u,.38,1),{compact:true});
 }else if(i===2){
  whiteReport(c,k,470,210,980,790,u);label(c,k,'표준 HTML 보고서',1490,895,320,35,k.GOLD);route(c,k,[[1460,835],[1600,835],[1680,885]],progress(k,u,.62,.94));
 }else if(i===3){
  whiteReport(c,k,140,250,660,700,1,{compact:true});plate(c,k,920,230,885,720);label(c,k,'오전 6시 표준 메일 자동 발송',960,294,790,41,k.GOLD,700);
  const fields=[['받는 사람','담당자'],['제목','장비 Daily Report'],['본문','장비 이력·PM 계획 요약']];fields.forEach(([a,b],j)=>{const y=375+j*108,q=progress(k,u,.04+j*.09,.36+j*.09);c.save();c.globalAlpha=q;label(c,k,a,960,y,190,30,k.GOLD);label(c,k,b,1190,y,560,30);k.line(c,960,y+31,1765,y+31,1,'#FFFFFF20',1);c.restore()});
  plate(c,k,965,690,570,88);k.icon(c,'doc',989,711,42,k.GOLD);label(c,k,'HTML 보고서',1058,746,440,32);const q=progress(k,u,.25,.73);route(c,k,[[800,610],[868,610],[868,734],[965,734]],q);c.save();c.globalAlpha=q<1?1:0;k.icon(c,'doc',800+165*q,610+124*q,38,k.GOLD);c.restore();plate(c,k,1340,820,425,80);label(c,k,u>.76?'06:00 발송 완료':'06:00 자동 발송',1370,872,365,32,k.GOLD);
 }else{
  whiteReport(c,k,140,270,760,690,progress(k,u,.02,.78));c.save();c.globalAlpha=progress(k,u,.04,.30);plate(c,k,990,270,810,690);label(c,k,'일일 보고 작성',1025,337,740,39);label(c,k,'20분 → 0분',1025,455,740,88,k.GOLD,700);label(c,k,'자료 기준',1025,522,740,34,k.GOLD);label(c,k,'연간 약 122시간 절감',1025,628,740,57,k.GOLD,700);label(c,k,'담당자는 메일 확인·검토',1025,751,740,35);label(c,k,'장비 대응에 집중',1025,818,740,35);c.restore();
 }
}

function equipmentRow(c,k,x,y,w,u){
 label(c,k,'장비 Status',x,y-24,w,32,k.GOLD);for(let j=0;j<4;j++){const xx=x+j*w/4,q=progress(k,u,j*.1,.49+j*.1);c.save();c.globalAlpha=q;k.panel(c,xx+12,y,w/4-25,180,{fill:'#17212B',line:'#D4AF7C88',radius:8});k.line(c,xx+42,y+45,xx+w/4-55,y+45,1,k.GOLD,2);c.strokeStyle='#D4AF7C66';c.strokeRect(xx+42,y+71,w/4-100,61);c.fillStyle='#D4AF7C';c.fillRect(xx+w/4-70,y+151,24*q,9);c.restore();}
}
function reservation(c,k,x,y,w,h,u){
 label(c,k,'TEM 쿼터',x,y-22,w,32,k.GOLD);const cols=5,rows=3;for(let row=0;row<rows;row++)for(let col=0;col<cols;col++){const xx=x+col*w/cols,yy=y+row*h/rows,q=progress(k,u,.015*(row*cols+col),.48+.015*(row*cols+col));c.save();c.globalAlpha=q;const selected=row===1&&col===2;k.panel(c,xx+5,yy+5,w/cols-10,h/rows-10,{fill:selected&&u>.5?'#5D4529':'#14202A',line:selected&&u>.5?k.GOLD:'#D4AF7C44',radius:4});c.restore();}pointer(c,k,x+w*.49,y+h*.47,progress(k,u,.4,.77));
}
function cubic(c,p,i,u,k){
 const nav=['Lot 조회','장비 상태','TEM 쿼터','의뢰 현황','Daily·Weekly Report','주말 근무자 안내'];
 if(i===1){
  plate(c,k,170,235,1580,720);label(c,k,'Cubic공정Lab',650,335,830,64,k.GOLD,700);const points=[[260,430],[780,430],[1300,430],[260,710],[780,710],[1300,710]];
  nav.forEach((name,j)=>{const[x,y]=points[j],q=progress(k,u,.03+j*.08,.41+j*.08);c.save();c.globalAlpha=q;plate(c,k,x,y,360,160);k.icon(c,j===5?'mail':j===4?'doc':'database',x+22,y+25,45,k.GOLD);label(c,k,name,x+22,y+117,316,31);c.restore()});
 }else if(i===2){
  statusTable(c,k,120,255,1035,260,progress(k,u,0,.45),['Lot 조회','의뢰 현황'],{heading:'통합 현황'});equipmentRow(c,k,145,625,985,progress(k,u,.16,.7));reservation(c,k,1230,315,555,300,progress(k,u,.29,.87));
  plate(c,k,1220,695,575,265);label(c,k,'Daily·Weekly Report',1245,748,525,31,k.GOLD);k.graph(c,1250,790,510,95,progress(k,u,.42,.94)*1.35,39);k.icon(c,'mail',1270,910,35,k.GOLD);label(c,k,'주말 근무자 안내',1330,940,430,30);
 }else if(i===3){
  plate(c,k,120,230,1680,740);k.tabs(c,nav,150,255,1620,u,{selected:Math.min(5,Math.floor(u*6))});reservation(c,k,180,405,1000,400,progress(k,u,.08,.85));label(c,k,'TEM 쿼터 · 의뢰 현황',200,900,950,38,k.GOLD);plate(c,k,1260,355,480,540);label(c,k,'Daily·Weekly Report',1285,420,430,31,k.GOLD);k.graph(c,1300,470,395,185,progress(k,u,.3,.92)*1.35,39);writing(c,k,1300,715,395,3,progress(k,u,.35,.93),{gap:48});
 }else{
  ['Lot·장비 현황','TEM 쿼터·의뢰','Daily·Weekly Report','주말 근무자 안내'].forEach((name,j)=>{const y=325+j*155,q=progress(k,u,j*.07,.35+j*.07);c.save();c.globalAlpha=q;k.icon(c,j===3?'mail':'doc',140,y,54,k.GOLD);label(c,k,name,225,y+43,450,35);c.restore();route(c,k,[[670,y+28],[760,y+28],[760,620],[850,620]],q)});
  plate(c,k,815,510,250,160);label(c,k,'하나의 앱',845,605,190,37,k.GOLD,700);factCard(c,k,1120,280,680,660,'보고·취합 업무 시간','90% 이상 단축',['자료 기준','반복 조회·취합·보고 부담 완화','축적 데이터의 분석 활용'],u);
 }
}

function tcad(c,p,i,u,k){
 const names=['R_NIT','S/W','CD','LS','Etch Depth','Sidewall Angle'];
 if(i===1){
  k.micrograph(c,110,250,1130,710,progress(k,u,.03,.86)*1.4,{rotate:true,photo:p.texture});label(c,k,'이미지 기울기·위치 분석',1310,298,480,37,k.GOLD,700);k.rows(c,['기울기 분석','측정 위치 분석','측정값·좌표 생성','측정선 오버레이','결과·이력 저장'],1310,350,475,progress(k,u,.12,.93)*2.3,{gap:113,icons:false,selected:Math.min(4,Math.floor(u*5))});
 }else if(i===2){
  k.micrograph(c,110,245,1100,720,1.4,{photo:p.texture});label(c,k,'측정값 · 좌표',1320,292,440,43,k.GOLD,700);
  names.forEach((name,j)=>{const q=progress(k,u,.03+j*.08,.39+j*.08),yy=380+j*94,px=330+j*105,py=420+(j%3)*135;k.line(c,px-42,py,px+110,py,q,k.GOLD,3);k.line(c,px-42,py-15,px-42,py+15,q,k.GOLD,2);k.line(c,px+110,py-15,px+110,py+15,q,k.GOLD,2);route(c,k,[[px+110,py],[1170,py],[1270,yy]],progress(k,u,.13+j*.08,.52+j*.08),{width:1.5});c.save();c.globalAlpha=q;label(c,k,name,1320,yy+12,430,32);writing(c,k,1320,yy+34,430,1,q);c.restore()});label(c,k,'측정선 오버레이 자동 생성',140,1000,1080,36,k.GOLD,700);label(c,k,'결과·이력 저장',1320,1000,440,35,k.GOLD,700);
 }else if(i===3){
  plate(c,k,115,230,1070,735);label(c,k,'측정 결과',150,300,1000,43,k.GOLD,700);['항목','측정값','좌표'].forEach((name,j)=>label(c,k,name,[155,520,850][j],375,[310,280,280][j],34,k.GOLD));
  names.forEach((name,j)=>{const yy=450+j*75,q=progress(k,u,.03+j*.08,.39+j*.08);c.save();c.globalAlpha=q;label(c,k,name,155,yy,330,30);writing(c,k,520,yy-17,250,1,q);writing(c,k,850,yy-17,250,1,q);k.line(c,150,yy+25,1140,yy+25,1,'#FFFFFF20',1);c.restore()});
  label(c,k,'담당자 검토·예외 확인',1260,300,530,40,k.GOLD,700);['누락·오류 확인','결과·예외 검토','사람의 최종 검증'].forEach((name,j)=>{const y=410+j*185,q=progress(k,u,.1+j*.14,.48+j*.14);route(c,k,[[1185,590],[1225,590],[1225,y+55],[1260,y+55]],q);c.save();c.globalAlpha=q;plate(c,k,1260,y,530,130);label(c,k,name,1290,y+80,470,37);c.restore()});
 }else{
  k.micrograph(c,130,270,980,670,progress(k,u,0,.7)*1.4,{photo:p.texture,rotate:true,measure:true});factCard(c,k,1190,270,610,690,'이미지당 측정','5분 → 6초',['자료 기준','담당자 최종 검증 필요','누락·오류 보완 필요'],u);
 }
}

function plugTiles(c,p,u,k){
 const cols=4,rows=2,w=310,h=270,gap=90;
 for(let row=0;row<rows;row++)for(let col=0;col<cols;col++){
  const x=190+col*(w+gap),y=390+row*(h+22),j=row*cols+col,q=progress(k,u,.04*j,.43+.04*j),tile=p.reference?{image:p.reference,crop:[.194+col*.045,.329+row*.083,.045,.083]}:p.texture;
  k.micrograph(c,x,y,w,h,1.4,{plug:true,photo:tile});outline(c,k,x+9,y+9,w-18,h-18,q);k.line(c,x+35,y+h/2,x+w-35,y+h/2,q,k.GOLD,2);k.line(c,x+w/2,y+25,x+w/2,y+h-25,q,k.GOLD,2);
 }
 label(c,k,'계측 이미지 적재',140,1000,1640,36,k.GOLD);
}

function plug(c,p,i,u,k){
 if(i===1){
  ['DD-SEM 수집','전처리','적재'].forEach((name,j)=>{const x=140+j*570,q=progress(k,u,j*.08,.38+j*.08);c.save();c.globalAlpha=q;plate(c,k,x,230,500,115);label(c,k,name,x+28,302,444,43,k.GOLD);c.restore();if(j<2)route(c,k,[[x+500,288],[x+570,288]],q)});plugTiles(c,p,u,k);
 }else if(i===2){
  const suspect=p.reference?{image:p.reference,crop:[.392,.326,.076,.151]}:p.texture,normal=p.reference?{image:p.reference,crop:[.478,.326,.086,.151]}:p.texture;
  k.micrograph(c,130,345,510,510,progress(k,u,0,.75)*1.4,{plug:true,photo:suspect,measure:true,suspect:true});k.micrograph(c,700,345,510,510,1.4,{plug:true,photo:normal,measure:true});label(c,k,'오계측 후보',145,295,485,37,k.AMBER);label(c,k,'정상 비교',720,295,470,37);
  statusTable(c,k,1300,250,490,600,progress(k,u,.12,.93),['오계측 후보','검토 대상'],{heading:'검토 범위 축소'});plate(c,k,1300,890,490,88);label(c,k,'담당자 최종 판단',1325,946,440,33,k.GOLD);pointer(c,k,1660,920,progress(k,u,.54,.95));route(c,k,[[640,600],[1250,600],[1300,560]],progress(k,u,.22,.77));
 }else if(i===3){
  label(c,k,'담당자 검토 범위 축소',140,280,1640,44,k.GOLD,700);plate(c,k,140,325,1640,125);const msg='검토 대상을 확인합니다.';label(c,k,msg.slice(0,Math.floor(progress(k,u,.05,.50)*msg.length)),175,404,1560,43);
  statusTable(c,k,140,510,480,455,progress(k,u,.12,.88),['수집 데이터','오계측 후보','검토 결과'],{heading:'분석 조건'});label(c,k,'분석 대시보드',720,530,1060,39,k.GOLD);k.graph(c,720,590,1060,350,progress(k,u,.20,.94)*1.35,51);
 }else{
  factCard(c,k,120,260,810,590,'수집 TAT','1200초 → 75초',['자료 기준','수집·전처리·적재 자동화'],u);factCard(c,k,990,260,810,590,'리뷰 대상','317건 → 19건',['자료 기준 · 단일 층 검증','담당자 검토 범위 축소','최종 판단은 담당자'],u);
  [[120,75/1200],[990,19/317]].forEach(([x,ratio])=>{const q=progress(k,u,.15,.86),width=746;c.fillStyle='#F2EEE744';c.fillRect(x+32,712,width,14);c.fillStyle=k.GOLD;c.fillRect(x+32,764,width*(1-q+ratio*q),17)});
  label(c,k,'검토 대상 수치는 단일 층 검증 결과',120,980,1680,35,k.CREAM,600);
 }
}


// Phase dispatch follows revision8-content.json, not the older scene order.
function phaseSnm(c,p,i,u,k){
 if(i===1)return snm(c,p,1,u,k);if(i===3)return snm(c,p,4,u,k);if(i===4)return snm(c,p,3,u,k);
 ['Overlay','Residual','MA Bias'].forEach((name,j)=>{const x=360+j*600;label(c,k,name,x-190,285,380,41,k.GOLD);scanWafer(c,k,x,505,165,progress(k,u,j*.10,.72+j*.10),{vector:j===0,scatter:j===1,seed:j*23})});
 plate(c,k,150,760,650,190);label(c,k,'표준 진단 기준 적용',185,840,580,42,k.GOLD,700);label(c,k,'Map · Trend · K-param',185,905,580,34);route(c,k,[[800,855],[990,855]],progress(k,u,.15,.85),{width:4});plate(c,k,990,760,790,190);label(c,k,'원인 분석·솔루션 검토 지원',1025,840,720,40,k.GOLD,700);label(c,k,'분석 근거를 바탕으로 검토',1025,905,720,34);
}
function phaseExpense(c,p,i,u,k){
 if(p.cutCount===3){expense(c,p,i,u,k);if(i===2)label(c,k,'검증 중  ·  절감 검토 후보 ≠ 확정 절감 실적',130,1005,1660,35,k.GOLD,700);return}
 expense(c,p,({1:1,2:2,3:4,4:3})[i],u,k);if(i===4)label(c,k,'절감 검토 후보 ≠ 확정 절감 실적',130,1005,1660,38,k.GOLD,700);
}
function phaseDaily(c,p,i,u,k){
 if(i<4)return daily(c,p,({1:1,2:3,3:4})[i],u,k);
 whiteReport(c,k,140,270,840,690,progress(k,u,.03,.78));label(c,k,'담당자 확인·검토',1110,290,680,46,k.GOLD,700);
 ['메일 확인','보고서 검토','장비 대응'].forEach((name,j)=>{const y=420+j*190,q=progress(k,u,.08+j*.16,.45+j*.16);route(c,k,[[980,610],[1050,610],[1050,y+50],[1110,y+50]],q);c.save();c.globalAlpha=q;plate(c,k,1110,y,680,125);k.icon(c,j===2?'check':'doc',1140,y+34,48,k.GOLD);label(c,k,name,1230,y+80,520,43);c.restore()});
}
function phaseCubic(c,p,i,u,k){
 if(i===3)return cubic(c,p,4,u,k);
 if(i===1){
  statusTable(c,k,120,255,1035,280,progress(k,u,0,.55),['Lot 조회','장비 상태'],{heading:'하나의 앱에서 통합 조회'});equipmentRow(c,k,145,650,985,progress(k,u,.12,.75));reservation(c,k,1230,315,555,270,progress(k,u,.22,.87));statusTable(c,k,1220,700,575,250,progress(k,u,.20,.95),['의뢰 현황'],{heading:'TEM 의뢰'});return;
 }
 if(i===2){
  label(c,k,'Daily·Weekly Report 자동화',140,275,1620,44,k.GOLD,700);['Daily Report','Weekly Report'].forEach((name,j)=>{const x=140+j*850;plate(c,k,x,325,790,400);label(c,k,name,x+32,390,726,42,k.GOLD);k.graph(c,x+35,435,720,175,progress(k,u,.04+j*.12,.72+j*.12)*1.35,39+j);writing(c,k,x+35,660,710,1,progress(k,u,.20,.88))});
  plate(c,k,140,800,1640,180);k.icon(c,'mail',180,840,66,k.GOLD);label(c,k,'주말 근무자 안내 자동화',290,905,1010,48,k.GOLD,700);route(c,k,[[1300,890],[1665,890]],progress(k,u,.24,.90),{width:4});k.icon(c,'check',1700,865,45,k.GOLD);return;
 }
 ['반복 조회','취합','보고'].forEach((name,j)=>{const y=320+j*190;plate(c,k,140,y,500,130);label(c,k,name,175,y+80,430,42,k.GOLD);route(c,k,[[640,y+65],[815,y+65],[815,575],[1000,575]],progress(k,u,j*.10,.65+j*.10))});
 label(c,k,'축적 데이터 분석 활용',1050,310,740,45,k.GOLD,700);k.graph(c,1050,390,740,430,progress(k,u,.12,.92)*1.35,41);label(c,k,'반복 조회·취합·보고 부담 감소',145,985,1630,43,k.GOLD,700);
}
function phaseTcad(c,p,i,u,k){
 tcad(c,p,({1:1,2:2,3:4,4:3})[i],u,k);if(i===4||(p.cutCount===4&&i===3))label(c,k,'새 이미지의 측정 누락·오류 보완 필요',145,1005,1640,35,k.GOLD,700);
}
function phasePlug(c,p,i,u,k){
 if(i===1)return plug(c,p,1,u,k);if(i===3)return plug(c,p,4,u,k);if(i===4){plug(c,p,3,u,k);label(c,k,'향후 계획  |  PROvision 확장',140,1005,1640,39,k.GOLD,700);return}
 const suspect=p.reference?{image:p.reference,crop:[.392,.326,.076,.151]}:p.texture,normal=p.reference?{image:p.reference,crop:[.478,.326,.086,.151]}:p.texture;
 label(c,k,'이미지 기반 오계측 후보 탐지',130,280,930,43,k.GOLD,700);label(c,k,'오계측 후보',145,330,420,32,k.AMBER);label(c,k,'정상 비교',630,330,420,32);
 k.micrograph(c,130,365,430,430,progress(k,u,0,.78)*1.4,{plug:true,photo:suspect,measure:true,suspect:true});k.micrograph(c,615,365,430,430,1.4,{plug:true,photo:normal,measure:true});plate(c,k,130,855,915,110);label(c,k,'담당자 최종 판단',170,928,835,43,k.GOLD,700);
 plate(c,k,1120,245,680,720);label(c,k,'대시보드 자연어 분석',1150,310,620,37,k.GOLD,700);plate(c,k,1150,355,620,165);const a='오계측 후보와 검토 결과를',b='보여주세요.',q=progress(k,u,.06,.58),shown=Math.floor(q*(a.length+b.length));label(c,k,a.slice(0,Math.min(a.length,shown)),1180,421,560,32);label(c,k,b.slice(0,Math.max(0,shown-a.length)),1180,485,560,32);statusTable(c,k,1150,560,620,340,progress(k,u,.20,.92),['수집 데이터','오계측 후보','검토 결과']);
}
export const lateRevision9Contract={revision:9,metricCutIndex:3,effectCutIndex:4,metricTasks:['task11','task13','task17','task14','task16'],cutCounts:revision9CutCounts,roles:['manual_before','input_collection','analysis_action','result_metric','effect_limitations_future'],noMetricTasks:['task12'],lastCutCaveats:{task12:'ongoing_validation_candidates_not_confirmed_savings',task17:'human_validation_and_new_image_errors'},standaloneTaskTitles:false,source:'spec.json',brief:'reference/user-revision9-brief.json'};
export const lateRevision8Contract=lateRevision9Contract;
const drawLatePhase={snm:phaseSnm,expense:phaseExpense,daily:phaseDaily,cubic:phaseCubic,tcad:phaseTcad,plug:phasePlug};

/** Returns true only for the six late task profiles; never paints the header. */
export function drawLateTask(c,p,index,t,d,assets,section,k){
 if(!keys.includes(p.key))return false;
 const u=k.clamp(t/Math.max(.01,d));c.save();c.textBaseline='alphabetic';c.textAlign='left';c.beginPath();c.rect(80,190,1760,830);c.clip();
 if(index>0){
  const reference=assets.images?.[section.reference_image]||assets.images?.[String(section.reference_image||'').split('/').pop()];
  // The earlier tiny microscopy asset contained a photographed UI window.
  // Use only the actual TEM cross-section in the supplied concept instead.
  const texture=p.key==='tcad'&&reference?{image:reference,crop:[.424,.329,.106,.227]}:p.texture;
  drawLatePhase[p.key](c,{...p,cutCount:section.cuts.length,texture,reference},index,u,k);
 }
 c.restore();return true;
}
