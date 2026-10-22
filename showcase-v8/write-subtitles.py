#!/usr/bin/env python3
"""Export the frozen timeline's exact displayed Korean captions as SRT/VTT.

This reads input files only. It does not rewrite the spec, timing, narration,
alignment evidence, or source cuts. Only voiced `kind == "cut"` entries become
cues; opening and ending narration are included along with all twelve tasks.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def timestamp(frame,fps,separator):
    # SRT/VTT represent milliseconds. Nearest-millisecond rounding retains the
    # exact original frame when converted back at the source frame rate.
    ms=round(frame*1000/fps)
    hours,ms=divmod(ms,3_600_000);minutes,ms=divmod(ms,60_000);seconds,ms=divmod(ms,1000)
    return f'{hours:02}:{minutes:02}:{seconds:02}{separator}{ms:03}'

def parse_ms(value):
    m=re.fullmatch(r'(\d+):(\d{2}):(\d{2})[,.](\d{3})',value)
    assert m,f'Invalid subtitle timestamp: {value}'
    h,mi,s,ms=map(int,m.groups())
    assert mi<60 and s<60
    return ((h*60+mi)*60+s)*1000+ms

def validate_file(path,cues,fps,format):
    text=path.read_text(encoding='utf-8')
    if format=='vtt':
        assert text.startswith('WEBVTT\n\n')
        text=text[len('WEBVTT\n\n'):]
    blocks=text.strip().split('\n\n')
    assert len(blocks)==len(cues),f'{path.name}: wrong cue count'
    previous_end=0
    for index,(block,cue) in enumerate(zip(blocks,cues),1):
        lines=block.splitlines();assert lines[0]==str(index)
        stamps=lines[1].split(' --> ');assert len(stamps)==2
        a,b=map(parse_ms,stamps)
        assert a<b and a>=previous_end,'Subtitle cues overlap or reverse.'
        previous_end=b
        assert round(a*fps/1000)==cue['start_frame']
        assert round(b*fps/1000)==cue['end_frame']
        assert abs(a-cue['start_frame']*1000/fps)<=.500001
        assert abs(b-cue['end_frame']*1000/fps)<=.500001
        assert '\n'.join(lines[2:])==cue['caption'],'Caption text changed during export.'

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--timeline',type=Path,default=HERE/'timeline.json')
    parser.add_argument('--out',type=Path,default=HERE.parent/'out/showcase-v2')
    parser.add_argument('--expected-cues',type=int,default=73)
    args=parser.parse_args()
    frozen=[HERE/'spec.json',args.timeline,HERE/'align.py',HERE/'narration/take.wav',*sorted((HERE/'narration').glob('*.json')),*sorted((HERE/'narration').glob('vo*.wav'))]
    before={str(p):sha(p) for p in frozen if p.exists()}
    timeline=json.loads(args.timeline.read_text(encoding='utf-8'))
    fps=timeline['fps'];frames=timeline['frames'];duration=timeline['duration']
    assert fps==30 and frames==8962,'Unexpected frozen timeline frame count or frame rate.'
    assert abs(duration-frames/fps)<1e-8 and duration<=300
    entries=timeline['entries'];previous=0
    for entry in entries:
        a,b=entry['start_frame'],entry['end_frame']
        assert isinstance(a,int) and isinstance(b,int) and 0<=a<b<=frames
        assert a==previous,'Timeline entries are not contiguous whole frames.'
        assert abs(entry['start']-a/fps)<1e-7 and abs(entry['end']-b/fps)<1e-7
        previous=b
    assert previous==frames
    cues=[entry for entry in entries if entry['kind']=='cut']
    assert len(cues)==args.expected_cues,f'Expected {args.expected_cues} spoken captions, found {len(cues)}.'
    for cue in cues:
        caption=cue['caption']
        assert isinstance(caption,str) and caption.strip() and '-->' not in caption
        assert '\n\n' not in caption and '\r' not in caption
    args.out.mkdir(parents=True,exist_ok=True)
    result=[]
    for format,separator,prefix in [('srt',',',''),('vtt','.','WEBVTT\n\n')]:
        path=args.out/f'subtitles.ko.{format}'
        body='\n\n'.join(f"{i}\n{timestamp(cue['start_frame'],fps,separator)} --> {timestamp(cue['end_frame'],fps,separator)}\n{cue['caption']}" for i,cue in enumerate(cues,1))
        path.write_text(prefix+body+'\n',encoding='utf-8')
        validate_file(path,cues,fps,format)
        result.append({'file':str(path),'cues':len(cues),'sha256':sha(path)})
    assert all(sha(Path(p))==digest for p,digest in before.items()),'A frozen source input changed.'
    print(json.dumps({'status':'PASS','cues':len(cues),'timeline_frames':frames,'timeline_duration':duration,'first_cue_start':cues[0]['start'],'last_cue_end':cues[-1]['end'],'whole_frame_roundtrip':True,'caption_text_preserved':True,'source_inputs_unchanged':True,'outputs':result},ensure_ascii=False))

if __name__=='__main__':main()
