/**
 * Bounded 2.5D photographic motion. Every pixel is sampled from the approved
 * photograph. A continuous mesh moves a few hand/arm/shoulder regions without
 * cutout duplicates, generated content, floating graphics or audio changes.
 * Coordinates in the profiles are relative to the original photograph.
 */
const clamp=(x,a=0,b=1)=>Math.min(b,Math.max(a,x));
const smooth=x=>{x=clamp(x);return x*x*(3-2*x)};
const cache=new WeakMap();

export const photoMotionContract={
 revision:7,method:'Continuous local 2D mesh deformation of original photograph',
 firstPhotoOnly:true,externalGeneration:false,newContentSynthesized:false,
 cameraIndependent:true,explicitSceneTime:true,sourceGridPixels:25,
 noCutoutLayers:true,noDecorativeOverlays:true,noFaceSynthesis:true,
 preserved:['all photograph assets','headers','other body cuts','titles','opening','ending','timeline','complete approved audio'],
};

/** A single smooth movement which starts and ends at the photographed pose. */
export function motionPhase(control,t,d){
 const u=clamp(t/Math.max(.01,d));
 const start=control.start??.08,end=control.end??.94;
 if(u<=start||u>=end)return 0;
 const q=(u-start)/(end-start),v=Math.sin(Math.PI*q);
 return v*v;
}

function protection(x,y,profile,w,h){
 let factor=1;
 // Keep the edge of the original photograph anchored to prevent exposed gaps.
 const edge=Math.min(x,y,w-x,h-y);
 factor*=smooth(edge/26);
 for(const p of profile.protected||[]){
  const [a,b,rw,rh]=p.rect,[x0,y0,x1,y1]=[a*w,b*h,(a+rw)*w,(b+rh)*h];
  const dx=Math.max(x0-x,0,x-x1),dy=Math.max(y0-y,0,y-y1);
  factor*=smooth(Math.hypot(dx,dy)/(p.feather_px??22));
 }
 return factor;
}

/** Source-pixel displacement; testable independently of any camera drift. */
export function photoDisplacement(x,y,w,h,profile,t,d){
 let dx=0,dy=0;
 for(const control of profile.controls||[]){
  const phase=motionPhase(control,t,d);if(!phase)continue;
  const [cx,cy]=control.center,[rx,ry]=control.radius;
  const nx=(x-cx*w)/(rx*w),ny=(y-cy*h)/(ry*h),r2=nx*nx+ny*ny;
  if(r2>=1)continue;
  const weight=(1-r2)**3*phase;
  // Move amplitudes are authored in the original 1254px photograph space.
  const unit=w/1254,m=control.move||[0,0];
  let vx=m[0]*unit,vy=m[1]*unit;
  if(control.rotation_deg){
   const pivot=control.pivot||control.center,angle=control.rotation_deg*Math.PI/180;
   const px=x-pivot[0]*w,py=y-pivot[1]*h;
   vx+=Math.cos(angle)*px-Math.sin(angle)*py-px;
   vy+=Math.sin(angle)*px+Math.cos(angle)*py-py;
  }
  dx+=vx*weight;dy+=vy*weight;
 }
 const a=protection(x,y,profile,w,h);return[dx*a,dy*a];
}

function geometry(image){
 let g=cache.get(image);if(g)return g;
 const w=image.naturalWidth||image.width,h=image.naturalHeight||image.height;
 const step=25,cols=Math.ceil(w/step),rows=Math.ceil(h/step),points=[];
 for(let j=0;j<=rows;j++)for(let i=0;i<=cols;i++)points.push({x:Math.min(w,i*step),y:Math.min(h,j*step)});
 g={w,h,cols,rows,points};cache.set(image,g);return g;
}

function triangle(ctx,image,source,dest){
 const [s0,s1,s2]=source,[p0,p1,p2]=dest;
 const det=(s1.x-s0.x)*(s2.y-s0.y)-(s2.x-s0.x)*(s1.y-s0.y);
 if(!det)return;
 const a=((p1.x-p0.x)*(s2.y-s0.y)-(p2.x-p0.x)*(s1.y-s0.y))/det;
 const b=((p1.y-p0.y)*(s2.y-s0.y)-(p2.y-p0.y)*(s1.y-s0.y))/det;
 const c=((p2.x-p0.x)*(s1.x-s0.x)-(p1.x-p0.x)*(s2.x-s0.x))/det;
 const d=((p2.y-p0.y)*(s1.x-s0.x)-(p1.y-p0.y)*(s2.x-s0.x))/det;
 const e=p0.x-a*s0.x-c*s0.y,f=p0.y-b*s0.x-d*s0.y;
 const center={x:(p0.x+p1.x+p2.x)/3,y:(p0.y+p1.y+p2.y)/3};
 // Slightly overlap the same continuous texture at shared edges to suppress
 // antialias seams. There is an unwarped original photograph below the mesh.
 const pad=.48,expanded=dest.map(p=>{const dx=p.x-center.x,dy=p.y-center.y,l=Math.hypot(dx,dy);return{x:p.x+pad*dx/l,y:p.y+pad*dy/l}});
 ctx.save();ctx.beginPath();ctx.moveTo(expanded[0].x,expanded[0].y);ctx.lineTo(expanded[1].x,expanded[1].y);ctx.lineTo(expanded[2].x,expanded[2].y);ctx.closePath();ctx.clip();
 ctx.transform(a,b,c,d,e,f);
 const minX=Math.max(0,Math.min(s0.x,s1.x,s2.x)-2),minY=Math.max(0,Math.min(s0.y,s1.y,s2.y)-2);
 const maxX=Math.min(image.width,Math.max(s0.x,s1.x,s2.x)+2),maxY=Math.min(image.height,Math.max(s0.y,s1.y,s2.y)+2);
 ctx.drawImage(image,minX,minY,maxX-minX,maxY-minY,minX,minY,maxX-minX,maxY-minY);ctx.restore();
}

/** Draw the same photographic crop as cover(), then locally deform it. */
export function drawAnimatedPhoto(ctx,image,profile,t,d,{zoom=1,fx=.5,fy=.5,width=1920,height=1080,enabled=true}={}){
 if(!image||!profile||!enabled)return false;
 const {w,h,cols,rows,points}=geometry(image);let sx=0,sy=0,sw=w,sh=h;
 const ratio=width/height;if(sw/sh>ratio){const nw=sh*ratio;sx+=(sw-nw)*fx;sw=nw}else{const nh=sw/ratio;sy+=(sh-nh)*fy;sh=nh}
 const cw=sw/zoom,ch=sh/zoom;sx+=(sw-cw)*fx;sy+=(sh-ch)*fy;
 // Identical source and target rectangles to the existing cover renderer.
 ctx.drawImage(image,sx,sy,cw,ch,0,0,width,height);
 if(!(profile.controls||[]).some(p=>motionPhase(p,t,d)>0))return true;
 const moved=points.map(p=>{const [dx,dy]=photoDisplacement(p.x,p.y,w,h,profile,t,d);return{x:p.x+dx,y:p.y+dy,amount:Math.abs(dx)+Math.abs(dy)}});
 ctx.save();ctx.beginPath();ctx.rect(0,154,width,height-154);ctx.clip();
 ctx.scale(width/cw,height/ch);ctx.translate(-sx,-sy);
 for(let j=0;j<rows;j++)for(let i=0;i<cols;i++){
  const k=j*(cols+1)+i,idx=[k,k+1,k+cols+2,k+cols+1];
  const s=idx.map(n=>points[n]);if(s[2].x<sx||s[0].x>sx+cw||s[2].y<sy||s[0].y>sy+ch)continue;
  const p=idx.map(n=>moved[n]);if(p.every(q=>q.amount<.002))continue;
  triangle(ctx,image,[s[0],s[1],s[2]],[p[0],p[1],p[2]]);
  triangle(ctx,image,[s[0],s[2],s[3]],[p[0],p[2],p[3]]);
 }
 ctx.restore();return true;
}
