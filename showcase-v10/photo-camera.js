/**
 * Rigid camera reframing of approved photographs.  Each view is one ordinary
 * source rectangle drawn with a uniform scale: no mesh, cutouts, body motion,
 * invented detail or photographic pixel changes.  Time is always cut-local.
 */
const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
const number=(v,fallback)=>Number.isFinite(Number(v))?Number(v):fallback;
const ease=v=>{v=clamp(v);return v*v*(3-2*v)};
const mix=(a,b,q)=>a+(b-a)*q;

export const photoCameraContract=Object.freeze({
 revision:8,baselineRevision:6,method:'Uniform-scale source-photo pan/push and optional related-view dissolve',
 explicitCutLocalTime:true,firstPhotoOnly:true,rigidImageGeometry:true,
 humanWarp:false,meshWarp:false,cutoutLayers:false,externalGeneration:false,
 generatedDetails:false,decorativeOverlays:false,headerHeight:154,
 minZoom:1,maxZoom:1.12,maxViews:2,dissolveSeconds:.28,
 oneViewThroughSeconds:3.5,minimumTwoViewSeconds:4.2,
 profileSource:'assets.photoCameraProfiles.tasks or assets.photoCameraProfiles',
 focalPointMeaning:'fx/fy select the remaining crop margins using the original cover() convention',
 preserved:['approved photograph pixels and aspect ratio','persistent header','other content cuts','titles','opening','ending','audio','timeline'],
});
export const contract=photoCameraContract;

function resolveProfile(profileOrId,assets){
 if(profileOrId&&typeof profileOrId==='object')return profileOrId;
 const profiles=assets?.photoCameraProfiles;
 return profiles?.tasks?.[profileOrId]||profiles?.[profileOrId]||null;
}
function pose(value={}){
 return {zoom:clamp(number(value.zoom,1.025),1,photoCameraContract.maxZoom),fx:clamp(number(value.fx,.5)),fy:clamp(number(value.fy,.5))};
}
function cameraView(view,q,index,weight=1,travel=1){
 const from=pose(view?.start),to=pose(view?.end||view?.start),p=ease(q)*travel;
 return {index,label_ko:view?.label_ko||'',progress:clamp(q),weight,
  zoom:mix(from.zoom,to.zoom,p),fx:mix(from.fx,to.fx,p),fy:mix(from.fy,to.fy,p)};
}

/**
 * Pure, deterministic camera state. Pass a profile directly for independent
 * geometry inspection, or a task ID plus the same assets object as drawTask.
 * Returns null when that task has no profile. No timeline values are changed.
 */
export function getCameraState(profileOrId,localTime,duration,assets={}){
 const profile=resolveProfile(profileOrId,assets);if(!profile)return null;
 const d=Math.max(.01,number(duration,.01)),t=clamp(number(localTime,0),0,d),u=t/d;
 const threshold=Math.max(photoCameraContract.minimumTwoViewSeconds,number(profile.two_view_min_seconds,6.2));
 const two=d>photoCameraContract.oneViewThroughSeconds&&d>=threshold&&profile.views?.length>=2;
 if(!two){
  const view=profile.single||profile.views?.[0];if(!view)return null;
  // Retain a purposeful move in short cuts while reducing its travel speed.
  const travel=clamp(d/5.5,.42,1),current=cameraView(view,u,0,1,travel);
  return {task_id:typeof profileOrId==='string'?profileOrId:null,localTime:t,duration:d,normalizedTime:u,
   viewCount:1,blend:0,transition:null,layers:[current],purpose_ko:profile.purpose_ko||'',...current};
 }
 const seconds=clamp(number(profile.dissolve_seconds,.28),.24,.32);
 const middle=d*clamp(number(profile.split_at,.52),.42,.58),begin=middle-seconds/2,end=middle+seconds/2;
 const blend=ease((t-begin)/seconds);
 const first=cameraView(profile.views[0],t/end,0,1-blend);
 const second=cameraView(profile.views[1],(t-begin)/(d-begin),1,blend);
 const dominant=blend<.5?first:second;
 return {task_id:typeof profileOrId==='string'?profileOrId:null,localTime:t,duration:d,normalizedTime:u,
  viewCount:2,blend,transition:{start:begin,end,seconds,active:t>begin&&t<end},
  layers:[first,second],purpose_ko:profile.purpose_ko||'',zoom:dominant.zoom,fx:dominant.fx,fy:dominant.fy};
}

function imageEntry(entry){return entry?.image||entry?.element||entry?.canvas||entry?.video||entry}
function sourceRect(entry,im,view,width,height){
 const iw=im.videoWidth||im.naturalWidth||im.width,ih=im.videoHeight||im.naturalHeight||im.height;
 if(!(iw>0&&ih>0))return null;
 let sx=0,sy=0,sw=iw,sh=ih;
 if(entry?.crop){
  [sx,sy,sw,sh]=Array.isArray(entry.crop)?entry.crop:[entry.crop.x,entry.crop.y,entry.crop.w,entry.crop.h];
  if(sw<=1&&sh<=1){sx*=iw;sy*=ih;sw*=iw;sh*=ih}
 }
 if(!(sw>0&&sh>0))return null;
 const ratio=width/height;
 if(sw/sh>ratio){const next=sh*ratio;sx+=(sw-next)*view.fx;sw=next}
 else{const next=sw/ratio;sy+=(sh-next)*view.fy;sh=next}
 const cw=sw/view.zoom,ch=sh/view.zoom;sx+=(sw-cw)*view.fx;sy+=(sh-ch)*view.fy;
 return {x:sx,y:sy,width:cw,height:ch,scaleX:width/cw,scaleY:height/ch};
}

/**
 * Draw only the first-photo body area. The caller retains its original cover()
 * fallback when this returns false. A related-view dissolve uses an opaque
 * first view and blends the second over it, avoiding a dark midpoint.
 */
export function drawCameraPhoto(ctx,entry,taskId,localTime,duration,assets={},options={}){
 if(assets.photoCamera===false)return false;
 const state=getCameraState(taskId,localTime,duration,assets),im=imageEntry(entry);
 if(!state||!im)return false;
 const width=Math.max(1,number(options.width,1920)),height=Math.max(1,number(options.height,1080));
 const headerHeight=clamp(number(options.headerHeight,154),0,height);
 const layers=state.layers.map(layer=>({...layer,source:sourceRect(entry,im,layer,width,height)}));
 if(layers.some(layer=>!layer.source))return false;
 ctx.save();ctx.beginPath();ctx.rect(0,headerHeight,width,height-headerHeight);ctx.clip();
 const alpha=ctx.globalAlpha;
 const draw=(layer,a)=>{const r=layer.source;ctx.globalAlpha=alpha*a;ctx.drawImage(im,r.x,r.y,r.width,r.height,0,0,width,height)};
 if(layers.length===1)draw(layers[0],1);
 else if(state.blend>=1)draw(layers[1],1);
 else{draw(layers[0],1);if(state.blend>0)draw(layers[1],state.blend)}
 ctx.restore();return true;
}
