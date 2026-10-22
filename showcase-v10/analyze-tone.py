#!/usr/bin/env python3
"""Approximate raw voiced pitch and level, never alter production audio."""
from pathlib import Path
import argparse, hashlib, json, subprocess
import numpy as np

ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'out/showcase-v10'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def analyze(path,a,b):
    raw=subprocess.run(['ffmpeg','-v','error','-ss',str(a),'-t',str(b-a),'-i',str(path),'-ar','8000','-ac','1','-f','f32le','-'],check=True,stdout=subprocess.PIPE).stdout
    x=np.frombuffer(raw,dtype='<f4');n=512;step=160;values=[]
    for k in range(0,len(x)-n,step):
        z=x[k:k+n].astype(float)
        if np.sqrt(np.mean(z*z))<10**(-38/20):continue
        z-=z.mean();ds=np.zeros(115)
        for tau in range(1,115):ds[tau]=np.sum((z[:-tau]-z[tau:])**2)
        cm=np.ones(115);cm[1:]=ds[1:]*np.arange(1,115)/np.maximum(np.cumsum(ds[1:]),1e-15)
        candidates=[i for i in range(20,114)if cm[i]<.18 and cm[i]<=cm[i-1] and cm[i]<=cm[i+1]]
        if not candidates:continue
        t=candidates[0];ym,y0,yp=cm[t-1:t+2];den=ym-2*y0+yp;t2=t+.5*(ym-yp)/den if den else t
        values.append(8000/t2)
    active=x[x*x>10**(-45/10)]
    return {'file':str(path),'file_sha256':sha(path),'range_seconds':[a,b],
        'f0_median_hz':float(np.median(values)),'f0_p25_hz':float(np.percentile(values,25)),
        'f0_p75_hz':float(np.percentile(values,75)),'voiced_windows':len(values),
        'active_rms_dbfs':float(20*np.log10(np.sqrt(np.mean(active**2))))}
def main():
    p=argparse.ArgumentParser();p.add_argument('--ending-start',type=float);p.add_argument('--part2-end',type=float,default=196.32);args=p.parse_args()
    cases=[('old_body',ROOT.parent/'out/showcase-v9/narration-raw.wav',0,294.7),
        ('preferred_old_ending',ROOT.parent/'showcase-v9/narration/recovery/approved-ending-original.wav',0,15.62),
        ('new_part1',ROOT/'narration/two-parts/part1/take.wav',0,193.92),
        ('new_part2',ROOT/'narration/two-parts/part2/take.wav',0,args.part2_end)]
    if args.ending_start is not None:
        cases.extend([('new_part2_body',ROOT/'narration/two-parts/part2/take.wav',0,args.ending_start),
            ('new_part2_ending',ROOT/'narration/two-parts/part2/take.wav',args.ending_start,args.part2_end)])
    result={'status':'ANALYSIS_ONLY','scope':'Approximate pitch/level trends. Does not prove subjective tone, voice quality, or human acceptance.',
        'method':'YIN-like first periodic minimum below0.18; 8kHz analysis resampling only;64ms frames/20ms hop;70-400Hz. Content, intonation and octave errors affect values.',
        'production_audio_modified':False,'cases':{name:analyze(f,a,b)for name,f,a,b in cases}}
    (OUT/'two-part-tone-analysis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
