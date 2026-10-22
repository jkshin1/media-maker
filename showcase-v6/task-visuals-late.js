/* Six task-specific workspaces. All geometry and motion use explicit scene time.
 * The caller paints the approved photograph and persistent 154px title header.
 * No example measurements, amounts, IDs, performance figures or new claims.
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
const plans={
 snm:[['photographic manual comparison','A manual focus follows the photographed comparison surface.',[420,430,900,470]],['Lot input and five analysis branches','Input focus descends into the five approved analysis menus.',[260,260,1400,640]],['three large wafer maps','Overlay, Residual and MA Bias reveal and scan left to right.',[140,350,1640,570]],['boxplot and wafer comparison','Baseline and input whiskers grow, then the wafer distribution is inspected.',[130,360,1640,570]],['suspected process hierarchy','K-parameter rows connect to a tentative layer and solution-review path.',[120,320,1680,610]]],
 expense:[['photographic ledger inspection','A single manual range selection follows ledger rows.',[260,600,1120,330]],['source ledgers into analysis','Four source ledgers feed one analysis path and an output ledger.',[110,300,1680,630]],['large trend ledger with candidate rail','Trend strokes draw toward the existing saving-candidate labels.',[150,370,1600,560]],['full-width review table','The review tabs and included/excluded status rows activate in sequence.',[120,320,1680,590]],['analysis-to-budget handoff','A source ledger settles beside the three approved effect phrases.',[180,340,1580,560]]],
 daily:[['photographic report writing','A manual reading guide follows the actual paper and screen.',[260,590,1250,350]],['data pipes into report','SmartMES, GMS, IPA and Datalake feed a report document.',[130,300,1650,620]],['large white HTML report','Title, summary, equipment chart and issue rows build down the page.',[470,260,980,680]],['report attachment and mail delivery','The document travels into the attachment row, then the send state changes.',[190,300,1580,610]],['report review on the photograph','The completed paper highlights connect to review, judgement and decision support.',[180,320,1580,610]]],
 cubic:[['photographic system switching','A single cursor moves across the photographed work surface.',[520,350,1100,540]],['portal function launcher','The five approved portal functions become available around the home title.',[170,330,1580,560]],['Lot, equipment, reservation and report workbench','Lot rows, equipment badges, reservation slots and report strokes activate in order.',[130,320,1660,640]],['reservation-led portal workflow','The portal selection moves into the calendar and report activity.',[140,330,1650,610]],['systems-to-portal consolidation','The four source names converge into one portal and its approved functions.',[140,330,1640,570]]],
 tcad:[['photographic manual measurement','A manual bracket is placed on the photographed image work area.',[420,370,1020,570]],['large TEM alignment stage','The real TEM texture rotates gently into alignment beside its tool menu.',[120,280,1600,650]],['image measurements into Raw data','Six measurement brackets draw before the matching Raw data rows reveal.',[120,300,1640,660]],['Raw data to large scatter view','Accuracy comparison strokes and R_NIT versus S/W points accumulate.',[150,360,1600,580]],['measured image and approved effects','The measured image settles while three existing effect phrases reveal.',[130,330,1610,610]]],
 plug:[['photographic manual tile checking','A manual focus ring follows the photographed large-area image.',[420,390,900,540]],['large CV tile field','Detection frames and measurement lines traverse the actual Plug texture tiles.',[120,300,1680,640]],['suspect versus normal human review','The suspect detail is selected and the final-judgement control is offered to the person.',[130,340,1650,590]],['full-width profile retrieval','The existing filters select CD and Space Profile while their curves draw.',[150,330,1620,600]],['table, profile and chatbot workbench','A result row feeds the profile and the neutral analysis chat request.',[140,330,1620,610]]]
};
export const lateVisualPlan=keys.flatMap(profile=>plans[profile].map(([layout,motion,motionFocus],cutIndex)=>({profile,sectionId:sources[profile][0],cutIndex,layout:cutIndex===0?'Approved photograph and retained header only':layout,motion:cutIndex===0?'Existing photograph camera drift only; no decorative pointer or guide':motion,motionFocus:cutIndex===0?null:motionFocus,decorativeOverlay:cutIndex===0?false:undefined,source:{md:`reference/${sources[profile][1]}`,image:`reference/${sources[profile][2]}`,...(profile==='tcad'?{photographicCrop:[.424,.329,.106,.227]}:{})},bodyBounds:[80,190,1760,830],exampleNumbers:false})));

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
 c.save();c.globalAlpha=progress(k,u,.12,.34);label(c,k,'주요 지표 요약',46,162,900,30,ink);writing(c,k,48,193,880,2,progress(k,u,.15,.46),{gap:31,color:'#53616A55'});c.restore();
 c.save();c.globalAlpha=progress(k,u,.26,.49);label(c,k,'장비 현황',46,313,500,30,ink);k.graph(c,54,357,530,240,progress(k,u,.30,.77)*1.35,28,'#577D86');label(c,k,'이슈 요약',642,313,300,30,ink);writing(c,k,642,363,300,6,progress(k,u,.38,.88),{gap:38,color:'#53616A55'});c.restore();
 c.save();c.globalAlpha=progress(k,u,.58,.91);k.line(c,46,661,954,661,1,'#A59C8C',1);writing(c,k,48,694,880,2,progress(k,u,.59,.93),{gap:30,color:'#53616A44'});c.restore();c.restore();
}
function statusTable(c,k,x,y,w,h,u,labels,{heading=null}={}){
 plate(c,k,x,y,w,h);if(heading)label(c,k,heading,x+26,y+47,w-52,34,k.GOLD);
 const top=y+(heading?88:35),gap=(h-(heading?112:60))/labels.length;
 labels.forEach((s,j)=>{const q=progress(k,u,.07+j*.08,.46+j*.08),yy=top+j*gap;c.save();c.globalAlpha=q;label(c,k,s,x+28,yy+30,w*.55,29);writing(c,k,x+w*.58,yy+16,w*.31,1,q,{gap:20});k.line(c,x+24,yy+gap-10,x+w-24,yy+gap-10,1,'#FFFFFF20',1);c.restore();});
}
function snm(c,p,i,u,k){
 if(i===1){
  plate(c,k,520,225,880,115);label(c,k,'Lot ID',555,294,220,42,k.CREAM);const q=progress(k,u,.07,.3);k.line(c,745,302,1280,302,q,k.GOLD,2);k.icon(c,'search',1300,257,44,k.GOLD);pointer(c,k,1270,315,progress(k,u,.1,.3));
  const menu=[['Overlay Map',340,530],['Residual Map',785,530],['MA Bias Map',1230,530],['Trend 분석',560,800],['K-parameter 분석',1030,800]];
  menu.forEach(([s,x,y],j)=>{const q=progress(k,u,.19+j*.08,.54+j*.08);route(c,k,[[960,340],[960,420],[x+175,420],[x+175,y]],q);c.save();c.globalAlpha=q;plate(c,k,x,y,350,118);label(c,k,s,x+22,y+72,306,34,k.GOLD);c.restore();});
 }else if(i===2){
  ['Overlay','Residual','MA Bias'].forEach((s,j)=>{const x=380+j*580,q=progress(k,u,.03+j*.16,.47+j*.16);c.save();c.globalAlpha=q;label(c,k,s,x-240,295,480,43,k.GOLD,700);scanWafer(c,k,x,610,225,progress(k,u,j*.13,.72+j*.13),{vector:j===0,scatter:j===1,seed:j*23});c.restore();});
 }else if(i===3){
  label(c,k,'Parameter Trend',130,270,1000,44,k.GOLD,700);label(c,k,'정상 Baseline / 입력 Wafer',130,323,1000,31);k.line(c,150,895,1125,895,1,'#D4AF7C55',2);
  for(let j=0;j<6;j++){const x=235+j*158,q=progress(k,u,.06+j*.055,.5+j*.055),cy=615+(k.hash(j+2)-.5)*90;for(const [dx,col,span]of[[-27,'#738F9C',96],[27,k.AMBER,120]]){k.line(c,x+dx,cy-span,x+dx,cy+span,q,col,2);k.line(c,x+dx-18,cy-span,x+dx+18,cy-span,q,col,2);k.line(c,x+dx-18,cy+span,x+dx+18,cy+span,q,col,2);c.fillStyle=col;c.globalAlpha=q*.62;c.fillRect(x+dx-22,cy-span*.4,44,span*.8);c.globalAlpha=1;}}
  label(c,k,'정상 대비 Wafer 분포',1230,323,570,35,k.GOLD);scanWafer(c,k,1510,650,245,progress(k,u,.35,.98),{scatter:true,seed:27});
 }else{
  label(c,k,'K-parameter · Z-score',120,266,850,43,k.GOLD,700);const names=['장비 정렬/Reticle','노광','CMP','PR'];
  names.forEach((s,j)=>{const y=340+j*140,q=progress(k,u,.04+j*.08,.46+j*.08);c.save();c.globalAlpha=q;plate(c,k,120,y,590,104);label(c,k,s,150,y+64,530,35);c.restore();route(c,k,[[710,y+52],[850,y+52],[950,610]],q);});
  c.save();c.globalAlpha=progress(k,u,.32,.66);plate(c,k,950,493,380,230);label(c,k,'의심 공정 계층 추정',977,578,326,34,k.GOLD);label(c,k,'의심 항목 검토',977,647,326,30);c.restore();
  const out=['정상 Baseline 대비 평가','의심 항목 검토','원인별 솔루션 제시'];out.forEach((s,j)=>{const y=350+j*230,q=progress(k,u,.48+j*.07,.79+j*.07);route(c,k,[[1330,608],[1390,608],[1390,y+50],[1440,y+50]],q);c.save();c.globalAlpha=q;label(c,k,s,1450,y+63,350,31,k.CREAM);k.line(c,1450,y+88,1800,y+88,q,k.GOLD,2);c.restore();});
 }
}
function expense(c,p,i,u,k){
 if(i===1){
  p.sources.forEach((s,j)=>{const y=280+j*160,q=progress(k,u,.02+j*.09,.4+j*.09);c.save();c.globalAlpha=q;plate(c,k,120,y,480,117);label(c,k,s,145,y+47,430,31,k.GOLD);writing(c,k,145,y+74,420,1,q);c.restore();route(c,k,[[600,y+59],[760,y+59],[920,600]],q);});
  c.save();c.globalAlpha=progress(k,u,.21,.58);c.fillStyle='#35271A';c.strokeStyle=k.GOLD;c.lineWidth=2;c.beginPath();c.arc(940,600,120,0,Math.PI*2);c.fill();c.stroke();label(c,k,'AI Agent',850,610,180,33,k.GOLD);c.restore();route(c,k,[[1060,600],[1190,600],[1260,600]],progress(k,u,.43,.75));
  statusTable(c,k,1260,260,540,680,progress(k,u,.4,1),['경비 실적','장비 이력','절감 가능 항목'],{heading:'데이터 분석 및 판단 지표 생성'});
 }else if(i===2){
  plate(c,k,105,220,1710,755);label(c,k,'경비 트렌드 분석',145,292,1170,46,k.GOLD,700);k.graph(c,160,390,1125,475,progress(k,u,.07,.82)*1.35,14);
  const names=['주요 절감 아이템','주요 인사이트','기대 효과'];names.forEach((s,j)=>{const y=410+j*185,q=progress(k,u,.3+j*.14,.58+j*.14);route(c,k,[[1235,560],[1330,560],[1375,y]],q);c.save();c.globalAlpha=q;label(c,k,s,1410,y+14,350,35,k.GOLD);writing(c,k,1410,y+52,340,2,q,{gap:32});c.restore();});
 }else if(i===3){
  plate(c,k,110,220,1700,750);const tab=Math.min(2,Math.floor(u*3));k.tabs(c,['전체 제안','검토 중','제외 항목'],145,250,1630,u,{selected:tab});
  ['항목','주요 내용','상태'].forEach((s,j)=>label(c,k,s,[155,730,1510][j],370,[450,650,270][j],32,k.GOLD));
  p.sources.forEach((s,j)=>{const y=410+j*126,q=progress(k,u,.05+j*.08,.4+j*.08),state=j===2?'제외 항목':'검토 중';c.save();c.globalAlpha=q;label(c,k,s,155,y+55,500,31);writing(c,k,735,y+38,610,1,q);plate(c,k,1490,y+15,265,63);label(c,k,state,1520,y+57,205,28,k.GOLD);k.line(c,145,y+106,1775,y+106,1,'#FFFFFF22',1);if((tab===1&&state==='검토 중')||(tab===2&&state==='제외 항목'))outline(c,k,141,y+2,1639,105,progress(k,u,.3,.95));c.restore();});
 }else{
  statusTable(c,k,150,290,530,620,progress(k,u,0,.8),['경비 실적','장비 이력','절감 가능 항목'],{heading:'분석 결과'});
  const names=['분석 시간 단축','절감 기회 조기 발굴','효율적인 예산 운영 지원'];names.forEach((s,j)=>{const y=405+j*205,q=progress(k,u,.15+j*.17,.48+j*.17);route(c,k,[[680,590],[810,590],[880,y]],q);c.save();c.globalAlpha=q;k.icon(c,j===0?'doc':j===1?'search':'check',910,y-45,54,k.GOLD);label(c,k,s,1010,y+1,740,49,k.GOLD,700);c.restore();});
 }
}
function daily(c,p,i,u,k){
 if(i===1){
  p.sources.forEach((s,j)=>{const y=280+j*165,q=progress(k,u,.03+j*.1,.42+j*.1);c.save();c.globalAlpha=q;k.icon(c,'database',150,y,74,k.GOLD);label(c,k,s,260,y+48,430,43);c.restore();route(c,k,[[650,y+34],[850,y+34],[1020,600]],q);});
  route(c,k,[[1020,600],[1120,600]],progress(k,u,.4,.76));whiteReport(c,k,1120,250,660,700,progress(k,u,.38,1),{compact:true});
 }else if(i===2){whiteReport(c,k,470,210,980,790,u);label(c,k,'HTML 보고서',1550,895,260,35,k.GOLD);route(c,k,[[1460,835],[1600,835],[1680,885]],progress(k,u,.62,.94));}
 else if(i===3){
  whiteReport(c,k,140,250,660,700,1,{compact:true});plate(c,k,920,230,885,720);label(c,k,'메일 발송',960,294,790,43,k.GOLD,700);
  const fields=[['받는 사람','지정된 담당자'],['제목','장비 Daily Report'],['본문','완성된 보고서를 전달합니다.']];fields.forEach(([a,b],j)=>{const y=375+j*108,q=progress(k,u,.04+j*.09,.36+j*.09);c.save();c.globalAlpha=q;label(c,k,a,960,y,190,30,k.GOLD);label(c,k,b,1190,y,560,30);k.line(c,960,y+31,1765,y+31,1,'#FFFFFF20',1);c.restore();});
  plate(c,k,965,690,570,88);k.icon(c,'doc',989,711,42,k.GOLD);label(c,k,'HTML 보고서',1058,746,440,32);const q=progress(k,u,.25,.73);route(c,k,[[800,610],[868,610],[868,734],[965,734]],q);c.save();c.globalAlpha=q<1?1:0;k.icon(c,'doc',800+165*q,610+124*q,38,k.GOLD);c.restore();
  const sent=u>.76;plate(c,k,1510,820,255,80);label(c,k,sent?'발송 완료':'발송',1540,872,195,32,k.GOLD);pointer(c,k,1640,856,progress(k,u,.56,.75));if(sent)k.icon(c,'check',1730,842,24,k.GOLD);
 }else{
  whiteReport(c,k,170,270,840,690,1);const names=['보고서 검토','업무 판단','의사결정 지원'];names.forEach((s,j)=>{const y=430+j*205,q=progress(k,u,.13+j*.16,.5+j*.16);route(c,k,[[1010,580],[1110,580],[1160,y]],q);c.save();c.globalAlpha=q;k.icon(c,j===0?'doc':j===1?'search':'check',1190,y-45,50,k.GOLD);label(c,k,s,1290,y,480,48,k.CREAM,700);c.restore();});
 }
}
function equipmentRow(c,k,x,y,w,u){
 label(c,k,'장비 Status',x,y-24,w,32,k.GOLD);for(let j=0;j<4;j++){const xx=x+j*w/4,q=progress(k,u,j*.1,.49+j*.1);c.save();c.globalAlpha=q;k.panel(c,xx+12,y,w/4-25,180,{fill:'#17212B',line:'#D4AF7C88',radius:8});k.line(c,xx+42,y+45,xx+w/4-55,y+45,1,k.GOLD,2);c.strokeStyle='#D4AF7C66';c.strokeRect(xx+42,y+71,w/4-100,61);c.fillStyle='#D4AF7C';c.fillRect(xx+w/4-70,y+151,24*q,9);c.restore();}
}
function reservation(c,k,x,y,w,h,u){
 label(c,k,'TEM 쿼터 예약',x,y-22,w,32,k.GOLD);const cols=5,rows=3;for(let row=0;row<rows;row++)for(let col=0;col<cols;col++){const xx=x+col*w/cols,yy=y+row*h/rows,q=progress(k,u,.015*(row*cols+col),.48+.015*(row*cols+col));c.save();c.globalAlpha=q;const selected=row===1&&col===2;k.panel(c,xx+5,yy+5,w/cols-10,h/rows-10,{fill:selected&&u>.5?'#5D4529':'#14202A',line:selected&&u>.5?k.GOLD:'#D4AF7C44',radius:4});c.restore();}pointer(c,k,x+w*.49,y+h*.47,progress(k,u,.4,.77));
}
function cubic(c,p,i,u,k){
 if(i===1){
  plate(c,k,170,235,1580,720);label(c,k,'Cubic공정Lab',650,335,830,64,k.GOLD,700);const points=[[260,470],[780,470],[1300,470],[520,730],[1040,730]];
  p.nav.forEach((s,j)=>{const [x,y]=points[j],q=progress(k,u,.03+j*.1,.45+j*.1);c.save();c.globalAlpha=q;plate(c,k,x,y,360,160);k.icon(c,j===4?'mail':j===3?'doc':'database',x+22,y+25,45,k.GOLD);label(c,k,s,x+22,y+117,316,31,k.CREAM);c.restore();});
 }else if(i===2){
  statusTable(c,k,120,255,1035,260,progress(k,u,0,.45),['Lot 조회'],{heading:'Lot 조회'});equipmentRow(c,k,145,625,985,progress(k,u,.16,.7));reservation(c,k,1230,315,555,300,progress(k,u,.29,.87));
  plate(c,k,1220,695,575,265);label(c,k,'Daily/Weekly Report',1245,748,525,31,k.GOLD);k.graph(c,1250,790,510,95,progress(k,u,.42,.94)*1.35,39);k.icon(c,'mail',1290,910,35,k.GOLD);label(c,k,'주말 근무자 메일 발신',1350,940,410,26);
 }else if(i===3){
  plate(c,k,120,230,1680,740);k.tabs(c,p.nav,150,255,1620,u,{selected:Math.min(4,Math.floor(u*5))});
  reservation(c,k,180,405,1000,460,progress(k,u,.08,.85));plate(c,k,1260,355,480,540);label(c,k,'Daily/Weekly Report',1285,420,430,31,k.GOLD);k.graph(c,1300,470,395,185,progress(k,u,.3,.92)*1.35,39);writing(c,k,1300,715,395,3,progress(k,u,.35,.93),{gap:48});
 }else{
  p.sources.forEach((s,j)=>{const x=180+j*420,q=progress(k,u,j*.08,.4+j*.08);c.save();c.globalAlpha=q;k.icon(c,'doc',x,300,60,k.GOLD);label(c,k,s,x+85,346,310,32);c.restore();route(c,k,[[x+85,380],[x+85,470],[960,560]],q);});
  plate(c,k,650,555,620,125);label(c,k,'하나의 포털',750,636,420,47,k.GOLD,700);const names=['Lot 조회 · 장비 Status','TEM 쿼터 예약','Daily/Weekly Report'];names.forEach((s,j)=>{const q=progress(k,u,.22+j*.08,.48+j*.08);route(c,k,[[960,680],[960,730],[340+j*590,730]],q);c.save();c.globalAlpha=q;label(c,k,s,145+j*590,797,480,31);c.restore();});c.save();c.globalAlpha=progress(k,u,.08,.42);label(c,k,'업무 시간 단축',690,953,700,60,k.GOLD,700);c.restore();
 }
}
function tcad(c,p,i,u,k){
 if(i===1){
  k.micrograph(c,110,250,1130,710,progress(k,u,.03,.86)*1.4,{rotate:true,photo:p.texture});label(c,k,'TCAD-TEM Labeling Tool',1310,298,480,37,k.GOLD,700);k.rows(c,p.nav,1310,350,475,progress(k,u,.12,.93)*2.3,{gap:113,icons:false,selected:Math.min(4,Math.floor(u*5))});
 }else if(i===2){
  k.micrograph(c,110,245,1100,720,1.4,{photo:p.texture});label(c,k,'Raw data',1320,292,440,43,k.GOLD,700);const names=['R_NIT','S/W','CD','LS','Etch Depth','Sidewall Angle'];
  names.forEach((s,j)=>{const q=progress(k,u,.03+j*.08,.39+j*.08),yy=380+j*94,px=330+j*105,py=420+(j%3)*135;k.line(c,px-42,py,px+110,py,q,k.GOLD,3);k.line(c,px-42,py-15,px-42,py+15,q,k.GOLD,2);k.line(c,px+110,py-15,px+110,py+15,q,k.GOLD,2);route(c,k,[[px+110,py],[1170,py],[1270,yy]],progress(k,u,.13+j*.08,.52+j*.08),{width:1.5});c.save();c.globalAlpha=q;label(c,k,s,1320,yy+12,430,32);writing(c,k,1320,yy+34,430,1,q);c.restore();});
 }else if(i===3){
  plate(c,k,115,230,1690,735);label(c,k,'R_NIT 정확도',155,320,500,37,k.GOLD);label(c,k,'S/W 정확도',155,575,500,37,k.GOLD);
  for(let j=0;j<2;j++){const y=390+j*255,q=progress(k,u,.05+j*.17,.6+j*.17);for(let n=0;n<4;n++){c.fillStyle=n%2?k.GOLD:'#738F9C';c.fillRect(190+n*98,y+150-(80+n*15)*q,62,(80+n*15)*q);}}
  label(c,k,'R_NIT vs S/W',805,320,890,43,k.GOLD,700);k.line(c,805,875,1740,875,1,'#D4AF7C55',2);k.line(c,805,375,805,875,1,'#D4AF7C55',2);const q=progress(k,u,.16,.95);for(let j=0;j<90*q;j++){const x=840+k.hash(j+72)*850,y=840-(x-840)*.47+(k.hash(j+101)-.5)*140;c.fillStyle=j%3?k.GOLD:'#738F9C';c.beginPath();c.arc(x,y,4.2,0,Math.PI*2);c.fill();}
 }else{
  k.micrograph(c,130,270,980,670,progress(k,u,0,.7)*1.4,{photo:p.texture,rotate:true,measure:true});const names=['이미지당 측정 시간 단축','R_NIT 정확도 개선','S/W 정확도 개선'];names.forEach((s,j)=>{const y=420+j*210,q=progress(k,u,.12+j*.17,.51+j*.17);route(c,k,[[1110,600],[1170,600],[1220,y]],q);c.save();c.globalAlpha=q;label(c,k,s,1270,y+8,500,39,k.GOLD,700);k.line(c,1270,y+44,1770,y+44,q,k.GOLD,2);c.restore();});
 }
}
function plugTiles(c,p,u,k){
 // Eight different approved source tiles: do not duplicate one hole into an
 // apparent dataset. Crop only the image grid, above all example ID labels.
 const cols=4,rows=2,w=355,h=310,gap=40;
 for(let row=0;row<rows;row++)for(let col=0;col<cols;col++){
  const x=180+col*(w+gap),y=285+row*(h+22),j=row*cols+col,q=progress(k,u,.04*j,.43+.04*j);
  const sourceCol=col,sourceRow=row;
  const tile=p.reference?{image:p.reference,crop:[.194+sourceCol*.045,.329+sourceRow*.083,.045,.083]}:p.texture;
  k.micrograph(c,x,y,w,h,1.4,{plug:true,photo:tile});outline(c,k,x+9,y+9,w-18,h-18,q);
  k.line(c,x+35,y+h/2,x+w-35,y+h/2,q,k.GOLD,2);k.line(c,x+w/2,y+25,x+w/2,y+h-25,q,k.GOLD,2);
 }
 const q=progress(k,u,.05,.96);label(c,k,'CV 인식',140,980,500,34,k.GOLD);route(c,k,[[380,965],[380+1390*q,965]],q,{width:3});
}

function plug(c,p,i,u,k){
 if(i===1)plugTiles(c,p,u,k);
 else if(i===2){
  const suspect=p.reference?{image:p.reference,crop:[.392,.326,.076,.151]}:p.texture,normal=p.reference?{image:p.reference,crop:[.478,.326,.086,.151]}:p.texture;
  k.micrograph(c,130,345,510,510,progress(k,u,0,.75)*1.4,{plug:true,photo:suspect,measure:true,suspect:true});k.micrograph(c,700,345,510,510,1.4,{plug:true,photo:normal,measure:true});label(c,k,'오계측 의심 항목',145,295,485,35,k.AMBER);label(c,k,'정상',720,295,470,35);
  statusTable(c,k,1300,250,490,600,progress(k,u,.12,.93),['오계측 의심 항목','검토 대상'],{heading:'검토 대상 선별'});plate(c,k,1300,890,490,88);label(c,k,'담당자 최종 판단',1325,946,440,33,k.GOLD);pointer(c,k,1660,920,progress(k,u,.54,.95));route(c,k,[[640,600],[1250,600],[1300,560]],progress(k,u,.22,.77));
 }else if(i===3){
  k.tabs(c,['CD Profile','Space Profile'],130,235,1660,u,{selected:u<.5?0:1});statusTable(c,k,130,345,335,420,progress(k,u,0,.8),['Lot','Device','Plug ID']);k.micrograph(c,145,805,305,185,1.4,{plug:true,photo:p.texture});
  label(c,k,u<.5?'CD Profile':'Space Profile',560,359,1190,43,k.GOLD,700);const q=progress(k,u,.08,.93);for(let j=0;j<4;j++)k.graph(c,560,410,1190,515,q*1.35+j*.06,51+j*5,[k.GOLD,'#738F9C','#A1A9BF',k.AMBER][j]);
 }else{
  plate(c,k,120,235,1680,325);label(c,k,'분석 대시보드',155,290,800,40,k.GOLD,700);const headers=['Plug','CD Profile','Space Profile'];headers.forEach((s,j)=>label(c,k,s,165+j*540,355,500,31,k.GOLD));for(let row=0;row<3;row++){const yy=405+row*48,q=progress(k,u,.04+row*.1,.43+row*.1);writing(c,k,170,yy,1500,1,q);k.line(c,155,yy+27,1765,yy+27,1,'#FFFFFF18',1);}
  label(c,k,'Profile 조회',145,635,950,35,k.GOLD);k.graph(c,150,690,955,280,progress(k,u,.18,.88)*1.35,71);plate(c,k,1220,605,580,375);label(c,k,'분석 챗봇',1250,663,520,35,k.GOLD);plate(c,k,1250,705,520,95);const msg='분석 결과를 확인합니다.',q=progress(k,u,.22,.75);label(c,k,msg.slice(0,Math.floor(q*msg.length)),1270,766,480,31);c.save();c.globalAlpha=progress(k,u,.55,.96);label(c,k,'Profile 조회',1270,863,480,29);label(c,k,'결과 테이블',1270,925,480,29);c.restore();
 }
}

/** Returns true only for the six late task profiles; never paints the header. */
export function drawLateTask(c,p,index,t,d,assets,section,k){
 if(!keys.includes(p.key))return false;
 const u=k.clamp(t/Math.max(.01,d));c.save();c.textBaseline='alphabetic';c.textAlign='left';c.beginPath();c.rect(80,190,1760,830);c.clip();
 if(index>0){
  const reference=assets.images?.[section.reference_image]||assets.images?.[String(section.reference_image||'').split('/').pop()];
  // The earlier tiny microscopy asset contained a photographed UI window.
  // Use only the actual TEM cross-section in the supplied concept instead.
  const texture=p.key==='tcad'&&reference?{image:reference,crop:[.424,.329,.106,.227]}:p.texture;
  ({snm,expense,daily,cubic,tcad,plug}[p.key])(c,{...p,texture,reference},index,u,k);
 }
 c.restore();return true;
}
