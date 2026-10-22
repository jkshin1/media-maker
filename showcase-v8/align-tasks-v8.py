#!/usr/bin/env python3
"""Align a complete continuous Korean take without deleting spoken content.

Inputs: ko.json blocks, Whisper word timestamps, and 48 kHz mono PCM master.
Outputs: exact section cuts/provenance, coverage report, word-safe timeline.
Run with bundled Python (NumPy is used only for waveform silence inspection).
No narration generation and no resampling/time stretching occurs here.
"""
from __future__ import annotations
import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
import re
import unicodedata
import wave

ROOT=Path(__file__).resolve().parent

def digest(data): return hashlib.sha256(data).hexdigest()
def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def normalize(text, pronunciation, owners=None):
    """Normalize ASR notation while carrying each character's source word ID."""
    chars=[]; ids=[]
    for i,c in enumerate(text):
        for out in unicodedata.normalize('NFKC',c).lower():
            if not out.isspace(): chars.append(out);ids.append(owners[i] if owners is not None else i)
    value=''.join(chars)
    aliases=dict(pronunciation)
    aliases.update({'CNC':'씨앤씨','씨엔씨':'씨앤씨','SW':'에스더블유','MA':'엠에이','아이전트':'에이전트','써머리':'서머리','12개':'열두개','십이개':'열두개','1건':'한건','2시간':'두시간','40분':'사십분','20분':'이십분','PM':'피엠','K-파라미터':'케이파라미터','1일':'일일','5개':'다섯개'})
    for source,target in sorted(aliases.items(),key=lambda pair:len(pair[0]),reverse=True):
        source=unicodedata.normalize('NFKC',source).lower().replace(' ','')
        target=unicodedata.normalize('NFKC',target).lower().replace(' ','')
        if not source or source==target: continue
        offset=0
        while True:
            pos=value.find(source,offset)
            if pos<0: break
            old=ids[pos:pos+len(source)]
            mapped=[old[min(len(old)-1,int(i*len(old)/max(1,len(target))))] for i in range(len(target))]
            value=value[:pos]+target+value[pos+len(source):]
            ids=ids[:pos]+mapped+ids[pos+len(source):]
            offset=pos+len(target)
    keep=[i for i,c in enumerate(value) if c.isalnum()]
    return ''.join(value[i] for i in keep),[ids[i] for i in keep]

def edit_align(expected,actual):
    """Global Levenshtein alignment; traceback maps every covered source char."""
    n,m=len(expected),len(actual)
    directions=bytearray((n+1)*(m+1))
    previous=array('H',range(m+1))
    for j in range(1,m+1): directions[j]=2
    for i,a in enumerate(expected,1):
        current=array('H',[i]+[0]*m);directions[i*(m+1)]=1
        for j,b in enumerate(actual,1):
            diag=previous[j-1]+(a!=b);delete=previous[j]+1;insert=current[j-1]+1
            if diag<=delete and diag<=insert: cost,op=diag,0
            elif delete<=insert: cost,op=delete,1
            else: cost,op=insert,2
            current[j]=cost;directions[i*(m+1)+j]=op
        previous=current
    mapping=[None]*n;matches=[False]*n;ops=[];i=n;j=m
    while i or j:
        op=directions[i*(m+1)+j]
        if i and j and op==0:
            mapping[i-1]=j-1;matches[i-1]=expected[i-1]==actual[j-1]
            if not matches[i-1]: ops.append({'kind':'substitution','expected_index':i-1,'actual_index':j-1,'expected':expected[i-1],'actual':actual[j-1]})
            i-=1;j-=1
        elif i and (not j or op==1):
            ops.append({'kind':'deletion','expected_index':i-1,'actual_index':j,'expected':expected[i-1]});i-=1
        else:
            ops.append({'kind':'insertion','expected_index':i,'actual_index':j-1,'actual':actual[j-1]});j-=1
    return mapping,matches,list(reversed(ops)),int(previous[m])

def whisper_words(j):
    words=j.get('words') or [w for s in j.get('segments',[]) for w in s.get('words',[])]
    if not words: raise AssertionError('ASR has no word timestamps; sentence-only timing is insufficient.')
    result=[]
    for w in words:
        result.append({'word':w.get('word',w.get('text','')),'start':float(w['start']),'end':float(w['end']),'probability':w.get('probability')})
    assert all(w['start']<=w['end'] for w in result),'Negative ASR word duration.'
    assert all(result[i]['start']<=result[i+1]['start'] for i in range(len(result)-1)),'ASR words are out of order.'
    return result

def quiet_regions(pcm, rate, width):
    import numpy as np
    dtype={2:'<i2',4:'<i4'}.get(width)
    assert dtype,'Only integer 16/32-bit PCM is supported.'
    samples=np.frombuffer(pcm,dtype=dtype).astype(np.float64)/(2**(width*8-1))
    window=int(rate*.01)
    rms=np.sqrt(np.mean(samples[:len(samples)//window*window].reshape(-1,window)**2,axis=1))
    quiet=rms<10**(-35/20)
    regions=[];start=None
    for i,v in enumerate(list(quiet)+[False]):
        if v and start is None: start=i
        if not v and start is not None:
            if i-start>=3: regions.append((start*.01,i*.01))
            start=None
    return regions

def safe_boundary(left,right,quiet,words,target=None):
    assert left<=right+1e-7,f'No word-safe gap: {left:.3f} > {right:.3f}'
    target=(left+right)/2 if target is None else min(right,max(left,target))
    candidates=[]
    for a,b in quiet:
        lo=max(a,left,target-.4);hi=min(b,right,target+.4)
        if hi-lo>=.08: candidates.append((lo+hi)/2)
    point=min(candidates,key=lambda x:abs(x-target)) if candidates else target
    inside=[w for w in words if w['start']+1e-5<point<w['end']-1e-5]
    assert not inside,f'Cut would enter an ASR word at {point}: {inside}'
    return point,{'basis':'waveform silence inside verified word gap' if candidates else 'verified inter-word gap; no qualifying waveform silence','left_word_end':left,'right_word_start':right,'point':point,'silence_preferred':bool(candidates)}

def reviewed_ending_pause(root,words,left_cut,right_cut,quiet,pcm,rate,width):
    """Resolve Whisper's leading-pause attribution at the ending sentence break.

    This exception is limited to a source-region ASR review that identifies the
    complete preceding sentence and the next approved line, plus an independently
    measured long waveform pause. A tiny low-energy interval cannot qualify.
    Original ASR words are retained; interval corrections are explicit evidence.
    """
    review_dir=root/'narration/transcription/reviews'
    review_path=review_dir/'ending_cut3_to_cut5.json';region_path=review_dir/'source-regions.json';log_path=root/'narration/silence.log'
    if not all(p.exists() for p in (review_path,region_path,log_path)):return None
    local=whisper_words(json.loads(review_path.read_text()))
    offset=json.loads(region_path.read_text())['regions']['ending_cut3_to_cut5']['source_start']
    pair=None
    for a,b in zip(local,local[1:]):
        if '환경까지' in a['word'] and re.search(r'(12|열두|십이).*개',b['word']):pair=(a,b);break
    assert pair,'Isolated ending ASR does not confirm the complete sentence/next-line boundary.'
    intervals=[];start=None
    for line in log_path.read_text().splitlines():
        m=re.search(r'silence_start:\s*([\d.]+)',line)
        if m:start=float(m[1])
        m=re.search(r'silence_end:\s*([\d.]+)',line)
        if m and start is not None:intervals.append((start,float(m[1])));start=None
    anchor=(left_cut['word_end']+right_cut['word_start'])/2
    candidates=[(a,b) for a,b in intervals if b-a>=.20 and abs((a+b)/2-anchor)<=.4 and any(q0<=a and q1>=b-.015 for q0,q1 in quiet)]
    assert candidates,'No independent long quiet interval near reviewed ending boundary.'
    a,b=min(candidates,key=lambda pair:abs(sum(pair)/2-anchor));point=(a+b)/2
    # The full ASR assigned the preceding inter-sentence silence to "12개의".
    # Narrow only that leading-pause span, leaving its spoken ending unchanged.
    protected=[dict(w) for w in words];li=left_cut['last_word_index'];ri=right_cut['first_word_index']
    assert li+1==ri and abs(pair[0]['end']+offset-anchor)<.1,'Unexpected ending words; manual review needed.'
    protected[li]['end']=a;protected[ri]['start']=b
    point,info=safe_boundary(a,b,quiet,protected,point)
    import numpy as np
    dtype='<i2' if width==2 else '<i4'
    raw=np.frombuffer(pcm,dtype=dtype).astype(np.float64)/(2**(width*8-1))
    around=raw[round((point-.04)*rate):round((point+.04)*rate)]
    rms=float(np.sqrt(np.mean(around**2)));db=20*math.log10(max(rms,1e-12))
    assert db<-35,'Reviewed insertion point has audible energy; do not split.'
    info.update({'basis':'isolated ASR sentence review + independent ffmpeg silence + RMS verification; leading-pause ASR interval corrected','source_review':str(review_path),'source_review_sha256':digest(review_path.read_bytes()),'isolated_asr_previous_word':pair[0],'isolated_asr_next_word':pair[1],'source_review_offset':offset,'original_asr_previous_word':words[li],'original_asr_next_word':words[ri],'corrected_previous_word_end':a,'corrected_next_word_start':b,'rms_dbfs_80ms':db,'explicit_timestamp_correction':True})
    return point,info

def build(args):
    config=json.loads(args.config.read_text());spec=json.loads(args.spec.read_text());asr=json.loads(args.asr.read_text())
    blocks=config['blocks'];words=whisper_words(asr);pronunciation=config.get('pronunciation_map',{})
    assert len(blocks)==12,'Expected twelve revised task narration blocks.'
    with wave.open(str(args.master),'rb') as master:
        params=master.getparams();pcm=master.readframes(params.nframes)
    assert params.nchannels==1 and params.framerate==48000,'Master must be 48000 Hz mono PCM.'
    duration=params.nframes/params.framerate;quiet=quiet_regions(pcm,params.framerate,params.sampwidth)
    cuts=[];expected=''
    for block in blocks:
        for cut in block['cuts']:
            norm,_=normalize(cut.get('spoken_text',cut['text']),pronunciation)
            cuts.append({**cut,'section_id':block['section_id'],'char_start':len(expected),'char_end':len(expected)+len(norm),'normalized':norm})
            expected+=norm
    raw='';owners=[]
    for wi,w in enumerate(words): raw+=w['word'];owners.extend([wi]*len(w['word']))
    actual,char_word=normalize(raw,pronunciation,owners)
    mapping,matches,edits,distance=edit_align(expected,actual)
    report={'status':'IN_PROGRESS','master':str(args.master),'asr':str(args.asr),'master_sha256':digest(args.master.read_bytes()),'asr_sha256':digest(args.asr.read_bytes()),'master_duration':duration,'normalization':'NFKC, punctuation/spacing removal, saved pronunciation map and documented ASR notation aliases. Original transcript retained.','expected_chars':len(expected),'asr_chars':len(actual),'edit_distance':distance,'exact_character_coverage':sum(matches)/len(expected),'cuts':[],'edit_count':len(edits),'edits':edits,'waveform_silence_regions':quiet,'boundaries':[]}
    save(args.out/'alignment-report.json',report)
    assert report['exact_character_coverage']>=args.coverage_min,f"Global ASR coverage too low: {report['exact_character_coverage']:.3f}"
    for cut in cuts:
        a,b=cut['char_start'],cut['char_end'];mapped=[mapping[k] for k in range(a,b) if mapping[k] is not None]
        assert mapped,f"No ASR anchor for {cut['id']}"
        first,last=min(char_word[k] for k in mapped),max(char_word[k] for k in mapped)
        coverage=sum(matches[a:b])/max(1,b-a)
        row={'id':cut['id'],'section_id':cut['section_id'],'expected':cut['text'],'spoken_text':cut['spoken_text'],'normalized':cut['normalized'],'asr_text':' '.join(w['word'].strip() for w in words[first:last+1]),'character_coverage':coverage,'first_word_index':first,'last_word_index':last,'word_start':words[first]['start'],'word_end':words[last]['end'],'review_required':coverage<.98}
        cut.update(row);report['cuts'].append(row)
    save(args.out/'alignment-report.json',report)
    assert all(c['character_coverage']>=args.cut_coverage_min for c in cuts),'At least one narration cut lacks sufficient transcript coverage; inspect report.'
    assert all(cuts[i]['last_word_index']<cuts[i+1]['first_word_index'] for i in range(len(cuts)-1)),'A source word is shared across adjacent narration cuts; exact word-safe alignment unresolved.'
    sections={};manifest={'master':{'path':str(args.master),'sha256':report['master_sha256'],'sample_rate':params.framerate,'channels':1,'sample_width':params.sampwidth,'sample_count':params.nframes,'duration':duration},'config':config,'generation_mode':config['generation_mode'],'cuts':[],'note':'vo1..vo12 are unmodified, exact PCM slices of master. Tempo belongs only to processed output, never these source cuts.'}
    for bi,block in enumerate(blocks):
        members=[c for c in cuts if c['section_id']==block['section_id']];first=members[0]['first_word_index'];last=members[-1]['last_word_index']
        previous_end=words[first-1]['end'] if first else 0
        next_start=words[last+1]['start'] if last+1<len(words) else duration
        start,start_info=safe_boundary(previous_end,words[first]['start'],quiet,words)
        end,end_info=safe_boundary(words[last]['end'],next_start,quiet,words)
        # ASR may place the final timestamp before the audible Korean ending.
        # Preserve the actual file ends, and split task gaps near their middle.
        if first==0:start=0;start_info.update(point=0,basis='complete master head preserved')
        if last==len(words)-1:end=duration;end_info.update(point=duration,basis='complete master tail preserved beyond ASR final timestamp')
        bounds=[start]
        for left,right in zip(members,members[1:]):
            reviewed=reviewed_ending_pause(ROOT,words,left,right,quiet,pcm,params.framerate,params.sampwidth) if block['section_id']=='ending' and left['id']=='ending_cut3' and right['id']=='ending_cut5' else None
            point,info=reviewed if reviewed else safe_boundary(left['word_end'],right['word_start'],quiet,words)
            bounds.append(point);report['boundaries'].append({'section_id':block['section_id'],'after_cut':left['id'],**info})
        bounds.append(end)
        s0=int(round(start*params.framerate));s1=int(round(end*params.framerate));source=pcm[s0*params.sampwidth:s1*params.sampwidth]
        path=args.out/f'vo{bi+1}.wav'
        with wave.open(str(path),'wb') as out:
            out.setnchannels(1);out.setsampwidth(params.sampwidth);out.setframerate(params.framerate);out.writeframes(source)
        with wave.open(str(path),'rb') as check: assert check.readframes(check.getnframes())==source,'Exact master PCM comparison failed.'
        portable_path=path.resolve().relative_to(ROOT.resolve()).as_posix()
        record={'index':bi+1,'section_id':block['section_id'],'file':portable_path,'sha256':digest(path.read_bytes()),'pcm_sha256':digest(source),'source_start_sample':s0,'source_end_sample':s1,'source_start':s0/params.framerate,'source_end':s1/params.framerate,'duration_samples':s1-s0,'duration':(s1-s0)/params.framerate,'prompt':block['spoken_text'],'caption_script':block['text'],'start_boundary':start_info,'end_boundary':end_info}
        manifest['cuts'].append(record);sections[block['section_id']]={'members':members,'bounds':bounds,'source':record}
    fps=spec['output']['fps'];fixed=12*args.title_seconds+4*args.summary_seconds+args.ending_transition_seconds+args.ending_card_seconds
    available=args.target_seconds-fixed;voice=sum(s['source']['duration'] for s in sections.values())
    tempo=max(1,voice/available)
    # Round each continuous section once. Internal visual boundaries use
    # cumulative frame rounding, avoiding artificial silence at every cut.
    tempo=max(1,voice/(available-len(blocks)/fps))
    assert tempo<=args.tempo_max,f'Required pitch-preserving tempo {tempo:.4f} exceeds allowed {args.tempo_max}. No words were discarded.'
    entries=[];cursor=0
    def add(section_id,kind,seconds,frames_override=None,**extra):
        nonlocal cursor
        frames=max(1,frames_override if frames_override is not None else int(math.ceil(seconds*fps-1e-8)))
        entry={'section_id':section_id,'kind':kind,'start_frame':cursor,'end_frame':cursor+frames,'start':cursor/fps,'end':(cursor+frames)/fps,**extra};entries.append(entry);cursor+=frames
        return entry
    audio=[];clip_rows=[]
    for section in spec['sections']:
        sid=section['id']
        if section['type']=='summary': add(sid,'summary',args.summary_seconds,cut_index=0,caption='');continue
        if section['type']=='task': add(sid,'title',args.title_seconds,cut_index=None,caption='')
        info=sections[sid];start=cursor/fps;voice_frames_previous=0;insertions=[]
        for ci,cut in enumerate(section['cuts']):
            if not cut['narration']:
                seconds=args.ending_transition_seconds if ci==3 else args.ending_card_seconds
                silent_entry=add(sid,'silent',seconds,cut_index=ci,caption='')
                if ci==3:
                    insertions.append({'at_source_local_seconds':info['bounds'][3]-info['source']['source_start'],'at_source_local_sample':round((info['bounds'][3]-info['source']['source_start'])*params.framerate),'seconds':seconds,'timeline_start_seconds':silent_entry['start']})
                continue
            member=next(c for c in info['members'] if c['id']==cut['id']);mi=info['members'].index(member)
            a,b=info['bounds'][mi:mi+2];seconds=(b-a)/tempo
            assert seconds>=args.min_cut_seconds-1/fps,f"{cut['id']} needs {seconds:.3f}s, below minimum {args.min_cut_seconds}; word deletion is forbidden."
            voice_frames_end=int(math.ceil(info['source']['duration']/tempo*fps)) if mi==len(info['members'])-1 else round((b-info['source']['source_start'])/tempo*fps)
            frames=voice_frames_end-voice_frames_previous;voice_frames_previous=voice_frames_end
            entry=add(sid,'cut',seconds,frames_override=frames,cut_index=ci,cut_id=cut['id'],caption=cut['caption'],source_start=a,source_end=b,source_start_sample=round(a*params.framerate),source_end_sample=round(b*params.framerate),tempo=tempo)
            # Cut-level audio instructions make intentional silent ending scene 4
            # and frame rounding explicit, preserving each complete source word.
            audio.append({'section_id':sid,'cut_id':cut['id'],'file':info['source']['file'],'timeline_start':entry['start'],'timeline_end':entry['end'],'source_master_start':a,'source_master_end':b,'source_master_start_sample':round(a*params.framerate),'source_master_end_sample':round(b*params.framerate),'source_local_start':a-info['source']['source_start'],'source_local_end':b-info['source']['source_start'],'tempo':tempo,'processed_seconds':seconds})
        info['timeline_start']=start;info['timeline_end']=cursor/fps
        source=info['source'];last_voice_entry=next(e for e in reversed(entries) if e['section_id']==sid and e['kind']=='cut')
        clip_rows.append({'section_id':sid,'file':source['file'],'source_start_sample':source['source_start_sample'],'source_end_sample':source['source_end_sample'],'source_duration_seconds':source['duration'],'timeline_trim_start_sample':0,'timeline_trim_end_sample':round(source['duration']/tempo*params.framerate),'timeline_trim_coordinate_system':'post-tempo 48000 Hz section samples, before any intentional silence insertion; no second source trim','tempo_ratio':tempo,'timeline_start_seconds':start,'timeline_end_seconds':last_voice_entry['end'],'timeline_silence_insertions':insertions,'sha256':source['sha256'],'pcm_sha256':source['pcm_sha256'],'prompt':source['prompt']})
    total=cursor/fps
    assert total<=args.max_seconds,f'Timeline {total:.3f}s exceeds maximum {args.max_seconds}s.'
    report.update({'status':'PASS_WITH_ASR_VARIANTS' if any(c['review_required'] for c in report['cuts']) else 'PASS','script_blocks_covered':len(blocks),'script_cuts_covered':len(cuts),'all_source_cut_pcm_matches':True,'required_output_tempo':tempo,'final_timeline_seconds':total,'short_visual_cuts':[{'cut_id':e['cut_id'],'duration':e['end']-e['start'],'caption':e['caption']} for e in entries if e['kind']=='cut' and e['end']-e['start']<1.5],'minimum_visual_cut_seconds':args.min_cut_seconds,'low_coverage_cuts':[c for c in report['cuts'] if c['character_coverage']<.92],'notes':['Character coverage is transcript evidence, not a substitute for listening to ASR variants.','Every section and every ending line is anchored to timestamped words. No word or sentence was deleted to meet duration.','Tempo must be pitch preserving in audio mix; source master and exact section cuts remain unmodified.']})
    manifest.update({'alignment_report':str(args.out/'alignment-report.json'),'required_output_tempo':tempo,'timeline_seconds':total,'clips':clip_rows})
    timeline={'fps':fps,'duration':total,'duration_seconds':total,'frames':cursor,'max_seconds':args.max_seconds,'target_seconds':args.target_seconds,'tempo':tempo,'fixed_silent_seconds':fixed,'source_voice_seconds':voice,'entries':entries,'audio_segments':audio,'sections':[{'section_id':sid,'start':s['timeline_start'],'end':s['timeline_end'],'source':s['source']} for sid,s in sections.items()]}
    save(args.out/'manifest.json',manifest);save(args.out/'alignment-report.json',report);save(args.timeline,timeline)
    print(json.dumps({'status':report['status'],'coverage':report['exact_character_coverage'],'blocks':len(blocks),'spoken_cuts':len(cuts),'tempo':tempo,'duration':total,'timeline':str(args.timeline)},ensure_ascii=False))

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--config',type=Path,default=ROOT/'narration/ko.json');p.add_argument('--spec',type=Path,default=ROOT/'spec.json')
    p.add_argument('--asr',type=Path,default=ROOT/'narration/transcription/take.json');p.add_argument('--master',type=Path,default=ROOT/'narration/take.wav')
    p.add_argument('--out',type=Path,default=ROOT/'narration');p.add_argument('--timeline',type=Path,default=ROOT/'timeline.json')
    p.add_argument('--target-seconds',type=float,default=299);p.add_argument('--max-seconds',type=float,default=300);p.add_argument('--tempo-max',type=float,default=1.25)
    p.add_argument('--coverage-min',type=float,default=.88);p.add_argument('--cut-coverage-min',type=float,default=.75);p.add_argument('--min-cut-seconds',type=float,default=1.2)
    p.add_argument('--title-seconds',type=float,default=2);p.add_argument('--summary-seconds',type=float,default=6);p.add_argument('--ending-transition-seconds',type=float,default=1);p.add_argument('--ending-card-seconds',type=float,default=4)
    args=p.parse_args()
    try: build(args)
    except Exception as exc:
        path=args.out/'alignment-report.json'
        report=json.loads(path.read_text()) if path.exists() else {}
        report.update({'status':'FAIL','error':f'{type(exc).__name__}: {exc}'})
        save(path,report)
        raise

if __name__=='__main__': main()
