#!/usr/bin/env python3
"""Align all Revision9 narration at its original sample clock.

No speech generation, resampling, time stretching, inter-cut audio restart,
intentional inter-task silence, or legacy outer audio is used.
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
import shutil
import copy

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

def portable(path):
    path=Path(path).resolve()
    try:return path.relative_to(ROOT).as_posix()
    except ValueError:return str(path)

def assemble_recovery(args):
    """Join the approved prefix and original-speed ending as exact PCM."""
    directory=ROOT/'narration/recovery';directory.mkdir(parents=True,exist_ok=True)
    authorization=directory/'authorization.json';auth=json.loads(authorization.read_text())
    assert auth['authorization_source']=='direct_user_reply_in_current_chat'and auth['voice_speed_ratio']==1
    ending=directory/'approved-ending-original.wav';review=directory/'ending-reuse-review.json';prefix=directory/'prefix64-narration-analysis.json'
    for target,source,expected in [(ending,Path(auth['ending_source']),auth['ending_source_sha256']),(review,Path(auth['ending_review']),auth['ending_review_sha256'])]:
        if not target.exists():assert digest(source.read_bytes())==expected;shutil.copyfile(source,target)
        assert digest(target.read_bytes())==expected
    if not prefix.exists():shutil.copyfile(ROOT.parent/'out/showcase-v9/prefix64-narration-analysis.json',prefix)
    evidence=json.loads(prefix.read_text());boundary=evidence['body_end_candidate']['source_boundary_sample']
    source=ROOT/'narration/elevenlabs/take.wav';raw_sha=digest(source.read_bytes())
    assert raw_sha==evidence['source_hashes']['showcase-v9/narration/elevenlabs/take.wav']
    def read_audio(path):
        with wave.open(str(path),'rb')as w:
            assert (w.getframerate(),w.getnchannels(),w.getsampwidth())==(48000,1,2)
            return w.readframes(w.getnframes())
    raw=read_audio(source);tail=read_audio(ending);head=raw[:boundary*2];combined=head+tail
    assert digest(head)==evidence['body_end_candidate']['source_prefix_pcm_sha256']
    output=directory/'composite-original.wav'
    if output.exists():assert read_audio(output)==combined,'Never overwrite a different recovered source.'
    else:
        with wave.open(str(output),'wb')as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(48000);w.writeframes(combined)
    assert read_audio(output)==combined and digest(source.read_bytes())==raw_sha
    result={'status':'EXACT_PCM_COMPOSITE_ASSEMBLED_PENDING_FULL_ASR','generation_mode':'single_take_with_authorized_original_ending_reuse','ending_reuse_exception_authorized':True,'fresh_body_narration':True,'new_full_narration':False,'tempo':1,'speech_tempo':1,'authorization':portable(authorization),'authorization_sha256':digest(authorization.read_bytes()),'ending_review':portable(review),'ending_review_sha256':digest(review.read_bytes()),'prefix_review':portable(prefix),'prefix_review_sha256':digest(prefix.read_bytes()),'original_incomplete_take_preserved':True,'original_incomplete_take':portable(source),'original_incomplete_take_sha256':raw_sha,'composite':portable(output),'composite_sha256':digest(output.read_bytes()),'composite_pcm_sha256':digest(combined),'samples':len(combined)//2,'duration':len(combined)/96000,'sample_rate':48000,'channels':1,'sample_width':2,'source_spans':[{'role':'fresh_opening_and_55_task_lines','file':portable(source),'file_sha256':raw_sha,'source_start_sample':0,'source_end_sample':boundary,'composite_start_sample':0,'composite_end_sample':boundary,'pcm_sha256':digest(head)},{'role':'authorized_identical_original_speed_ending','file':portable(ending),'file_sha256':digest(ending.read_bytes()),'source_start_sample':0,'source_end_sample':len(tail)//2,'composite_start_sample':boundary,'composite_end_sample':len(combined)//2,'pcm_sha256':digest(tail)}],'words_or_samples_synthesized':0,'speech_speed_changed':False,'crossfade_samples':0,'actual_pause_edit_applied':False,'scope':'Exact authorized source assembly only; full 68-line completeness and pause-edit approval remain separate gates.'}
    save(directory/'recovery-map.json',result);print(json.dumps(result,ensure_ascii=False))
    return result

def quiet_regions(pcm,rate,width,threshold=-42):
    import numpy as np
    assert width==2,'Use the unmodified 16-bit master; do not implicitly convert it.'
    samples=np.frombuffer(pcm,dtype='<i2').astype(np.float64)/32768
    window=round(rate*.01)
    rms=np.sqrt(np.mean(samples[:len(samples)//window*window].reshape(-1,window)**2,axis=1))
    db=20*np.log10(np.maximum(rms,1e-12));regions=[];start=None
    for i,value in enumerate(list(db<threshold)+[False]):
        if value and start is None:start=i
        if not value and start is not None:
            if i-start>=8:regions.append({'start_sample':start*window,'end_sample':i*window,'start':start*.01,'end':i*.01,'duration':(i-start)*.01,'peak_rms_dbfs':float(np.max(db[start:i]))})
            start=None
    return regions

def reviewed_boundary(reviews,left,right,pcm,rate,quiet,fps):
    """Only current-master/current-ASR reviews can replace inaccurate ASR times."""
    rows=reviews.get('boundaries',[])
    if isinstance(rows,dict):rows=[dict(v,after_cut=k)for k,v in rows.items()]
    row=next((r for r in rows if r.get('after_cut')==left['id']),None)
    if row is None:return None
    assert row.get('evidence'),'Boundary review must identify its local ASR/waveform evidence.'
    end=float(row['actual_speech_end_seconds']);onset=float(row['actual_next_speech_start_seconds'])
    point=float(row['source_boundary_seconds']);frame=round(point*fps);point=frame/fps
    assert end<=point<=onset,'Reviewed frame must follow the complete preceding phrase.'
    info={'frame':frame,'sample':round(point*rate),'point':point,'basis':row.get('kind','REVIEWED_CURRENT_MASTER_BOUNDARY'),'left_word_end':left['word_end'],'right_word_start':right['word_start'],'reviewed_previous_speech_end':end,'reviewed_next_speech_start':onset,'evidence':row['evidence'],'review':row,'reviewed':True}
    regions=[q for q in quiet if q['start']<=point<=q['end']]
    if regions:info['quiet']=max(regions,key=lambda q:q['duration'])
    return info

def safe_boundary(left,right,quiet,rate,fps,reviews,pcm,words,prefer_quiet_midpoint=False):
    reviewed=reviewed_boundary(reviews,left,right,pcm,rate,quiet,fps)
    if reviewed:return reviewed
    lo=left['word_end'];hi=right['word_start'];target=(lo+hi)/2;candidates=[]
    if hi>=lo:
        for region in quiet:
            a=max(region['start'],lo);b=min(region['end'],hi)
            # A sustained quiet interval is considered only inside the lexical
            # phrase gap. Low energy inside a Korean word cannot qualify.
            if b-a<.08:continue
            f0=math.ceil((a+.02)*fps-1e-8);f1=math.floor((b-.02)*fps+1e-8)
            if f0>f1:continue
            desired=(a+b)/2 if prefer_quiet_midpoint else target
            frame=min(f1,max(f0,round(desired*fps)));point=frame/fps
            if any(w['start']+1e-7<point<w['end']-1e-7 for w in words):continue
            candidates.append((abs(point-target),frame,point,region))
    assert candidates, f"No reviewed word/waveform-safe boundary after {left['id']} ({lo:.3f}..{hi:.3f}); review the current master region, never insert a pause or reuse old ASR exceptions."
    _,frame,point,region=min(candidates,key=lambda c:c[0])
    return {'frame':frame,'sample':round(point*rate),'point':point,'basis':'sustained waveform quiet inside ordered lexical phrase gap, quantized to the global frame clock','left_word_end':lo,'right_word_start':hi,'quiet':region,'quiet_before_frame_seconds':point-region['start'],'quiet_after_frame_seconds':region['end']-point,'reviewed':False}

def propose_pause_edit(args,report,pcm,words,rate):
    """Write evidence and a virtual edit plan; never create/alter audio here."""
    import numpy as np
    target=round(args.target_working_seconds*rate);original=len(pcm)//2;needed=original-target
    assert needed>0,'A pause-removal plan is unnecessary for this source length.'
    strict_quiet=quiet_regions(pcm,rate,2,-48);byid={c['id']:c for c in report['cuts']};rows=[]
    for boundary in report['boundaries']:
        left=byid[boundary['after_cut']];right=byid[boundary['before_cut']]
        intervals=[q for q in strict_quiet if q['start']<=boundary['point']<=q['end']]
        if not intervals:continue
        q=max(intervals,key=lambda q:q['duration']);paragraph=left['section_id']!=right['section_id']
        minimum=args.paragraph_pause_seconds if paragraph else args.phrase_pause_seconds
        # The waveform silence must also be outside all timestamped words.
        lo=max(q['start_sample']+round(.08*rate),math.ceil(left['word_end']*rate)+1)
        hi=min(q['end_sample']-round(.08*rate),math.floor(right['word_start']*rate)-1)
        lexical_gap_samples=math.floor(right['word_start']*rate)-math.ceil(left['word_end']*rate)
        capacity=min(max(0,hi-lo),max(0,q['end_sample']-q['start_sample']-round(minimum*rate)),max(0,lexical_gap_samples-round(minimum*rate)))
        for word in words:
            if word['start']*rate<hi and word['end']*rate>lo:
                capacity=0;break
        rows.append({'after_cut':left['id'],'before_cut':right['id'],'paragraph_boundary':paragraph,'quiet':q,'original_lexical_gap_samples':lexical_gap_samples,'minimum_retained_quiet_seconds':minimum,'energy_guard_each_side_seconds':.08,'safe_remove_window_samples':[lo,hi],'capacity_samples':capacity})
    capacity=sum(r['capacity_samples']for r in rows)
    assert capacity>=needed,f'Only {capacity/rate:.3f}s verified pause capacity, below required {needed/rate:.3f}s; do not shorten words or speed speech.'
    allocations=[needed*r['capacity_samples']//capacity for r in rows];remainder=needed-sum(allocations)
    order=sorted(range(len(rows)),key=lambda i:(needed*rows[i]['capacity_samples'])%capacity,reverse=True)
    for i in order[:remainder]:allocations[i]+=1
    raw=np.frombuffer(pcm,dtype='<i2');edits=[]
    for row,length in zip(rows,allocations):
        if not length:continue
        lo,hi=row['safe_remove_window_samples'];center=(lo+hi-length)//2
        # Choose a quiet join with minimum integer-PCM discontinuity, without
        # crossfading, synthesizing, or changing any retained sample value.
        choices=range(max(lo,center-144),min(hi-length,center+144)+1)
        start=min(choices,key=lambda s:abs(int(raw[s-1])-int(raw[s+length]))+.1*(abs(int(raw[s-1]))+abs(int(raw[s+length]))))
        end=start+length;q=row['quiet'];assert start>=lo and end<=hi
        edits.append({**row,'raw_remove_start_sample':start,'raw_remove_end_sample':end,'removed_samples':length,'removed_seconds':length/rate,'retained_quiet_seconds':q['duration']-length/rate,'retained_lexical_gap_seconds':(row['original_lexical_gap_samples']-length)/rate,'quiet_join_jump_integer':abs(int(raw[start-1])-int(raw[end])),'crossfade_samples':0,'removed_pcm_sha256':digest(pcm[start*2:end*2])})
    edits.sort(key=lambda e:e['raw_remove_start_sample']);pieces=[];cursor=0;dest=0;virtual=[]
    for edit in edits+[{'raw_remove_start_sample':original,'raw_remove_end_sample':original}]:
        end=edit['raw_remove_start_sample'];content=pcm[cursor*2:end*2]
        if end>cursor:
            pieces.append({'raw_start_sample':cursor,'raw_end_sample':end,'working_start_sample':dest,'working_end_sample':dest+end-cursor,'pcm_sha256':digest(content)});virtual.append(content);dest+=end-cursor
        cursor=edit['raw_remove_end_sample']
    working=b''.join(virtual);assert dest==target and len(working)//2==target
    def mapped(point):return point-sum(max(0,min(point,e['raw_remove_end_sample'])-e['raw_remove_start_sample'])for e in edits if point>e['raw_remove_start_sample'])
    proofs=[]
    for index,cut in enumerate(report['cuts']):
        before=next((b for b in report['boundaries']if b['before_cut']==cut['id']),None);after=next((b for b in report['boundaries']if b['after_cut']==cut['id']),None)
        start=0 if index==0 else math.floor(min(cut['word_start'],before.get('quiet',{}).get('end',cut['word_start']))*rate)
        end=original if index==len(report['cuts'])-1 else math.ceil(max(cut['word_end'],after.get('quiet',{}).get('start',cut['word_end']))*rate)
        assert not any(start<e['raw_remove_end_sample']and end>e['raw_remove_start_sample']for e in edits),f"Protected phrase span overlaps a deletion: {cut['id']}"
        a,b=mapped(start),mapped(end);assert working[a*2:b*2]==pcm[start*2:end*2]
        proofs.append({'cut_id':cut['id'],'raw_start_sample':start,'raw_end_sample':end,'working_start_sample':a,'working_end_sample':b,'pcm_sha256':digest(pcm[start*2:end*2]),'retained_pcm_exact':True})
    plan={'status':'PROPOSED_NOT_APPLIED','approval_required':True,'audio_file_written':False,'master_sha256':report['master_sha256'],'asr_sha256':report['asr_sha256'],'alignment_report_sha256':digest((args.out/'alignment-report.json').read_bytes()),'sample_rate':rate,'original_samples':original,'original_seconds':original/rate,'target_samples':target,'target_seconds':target/rate,'removed_samples':needed,'removed_seconds':needed/rate,'verified_capacity_samples':capacity,'verified_capacity_seconds':capacity/rate,'spoken_samples_removed':0,'tempo':1,'waveform_threshold_dbfs':-48,'rms_window_seconds':.01,'phrase_minimum_quiet_seconds':args.phrase_pause_seconds,'paragraph_minimum_quiet_seconds':args.paragraph_pause_seconds,'energy_guards_each_side_seconds':.08,'crossfade_samples':0,'edits':edits,'retained_pieces':pieces,'protected_phrase_pcm_proofs':proofs,'expected_working_pcm_sha256':digest(working),'proposed_total_seconds_with_card':math.ceil(target*30/rate)/30+args.ending_card_seconds,'notes':['Analysis-only virtual edit proposal; no original/working audio has been written or changed.','Only central current-ASR inter-sentence sustained quiet can be removed; every retained PCM sample is unchanged.','All 68 protected phrase spans include ASR words and the waveform tail beyond approximate ASR endpoints.','Root/independent verification must approve this exact plan before application.']}
    save(args.out/'pause-edit-proposal.json',plan)
    return plan

def apply_approved_pause_plan(args):
    """Apply an exact independently approved plan, retaining all speech PCM."""
    assert args.approved_plan_sha256,'Explicit SHA approval of the exact plan is required.'
    assert digest(args.apply_pause_plan.read_bytes())==args.approved_plan_sha256
    plan=json.loads(args.apply_pause_plan.read_text());assert plan['status']=='PROPOSED_NOT_APPLIED'
    manifest=json.loads((args.out/'manifest-original.json').read_text());original_report=json.loads((args.out/'alignment-report-original.json').read_text());original_timeline=json.loads((args.out/'timeline-analysis.json').read_text())
    master=ROOT/manifest['master']['path'];assert digest(master.read_bytes())==plan['master_sha256']==manifest['master']['sha256']
    assert original_report['asr_sha256']==plan['asr_sha256']and digest((ROOT/original_report['asr']).read_bytes())==plan['asr_sha256']
    assert digest((args.out/'alignment-report-original.json').read_bytes())==plan['alignment_report_sha256']
    with wave.open(str(master))as w:raw=w.readframes(w.getnframes())
    pieces=plan['retained_pieces'];working=b''.join(raw[p['raw_start_sample']*2:p['raw_end_sample']*2]for p in pieces)
    assert digest(working)==plan['expected_working_pcm_sha256']and len(working)//2==plan['target_samples']
    for p in pieces:assert digest(raw[p['raw_start_sample']*2:p['raw_end_sample']*2])==p['pcm_sha256']
    for proof in plan['protected_phrase_pcm_proofs']:
        a,b=proof['raw_start_sample'],proof['raw_end_sample'];x,y=proof['working_start_sample'],proof['working_end_sample']
        assert raw[a*2:b*2]==working[x*2:y*2]and digest(raw[a*2:b*2])==proof['pcm_sha256']
    assert len(plan['protected_phrase_pcm_proofs'])==68 and plan['spoken_samples_removed']==0 and plan['tempo']==1
    directory=ROOT/'narration/recovery';directory.mkdir(parents=True,exist_ok=True);output=directory/'pause-edited.wav'
    if output.exists():
        with wave.open(str(output))as w:assert w.readframes(w.getnframes())==working,'Never overwrite a different working master.'
    else:
        with wave.open(str(output),'wb')as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(48000);w.writeframes(working)
    def mapped(sample):return sample-sum(max(0,min(sample,e['raw_remove_end_sample'])-e['raw_remove_start_sample'])for e in plan['edits']if sample>e['raw_remove_start_sample'])
    def mapped_time(time):return mapped(round(time*48000))/48000
    asr=json.loads((ROOT/original_report['asr']).read_text());words=whisper_words(asr)
    adjusted_words=[{**w,'start':mapped_time(w['start']),'end':mapped_time(w['end'])}for w in words]
    sourcecuts=original_report['cuts'];cuts=[{**c,'word_start':mapped_time(c['word_start']),'word_end':mapped_time(c['word_end'])}for c in sourcecuts]
    reviews={'boundaries':[]}
    for boundary in original_report['boundaries']:
        if boundary.get('reviewed'):
            reviews['boundaries'].append({'after_cut':boundary['after_cut'],'actual_speech_end_seconds':mapped_time(boundary['reviewed_previous_speech_end']),'actual_next_speech_start_seconds':mapped_time(boundary['reviewed_next_speech_start']),'source_boundary_seconds':mapped_time(boundary['point']),'kind':'MAPPED_CURRENT_SOURCE_REGION_REVIEW_AFTER_APPROVED_QUIET_EDIT','evidence':{'original_review':boundary,'approved_pause_plan_sha256':args.approved_plan_sha256}})
    quiet=quiet_regions(working,48000,2,args.quiet_dbfs);boundaries=[]
    for left,right,original_boundary in zip(cuts,cuts[1:],original_report['boundaries']):
        item=safe_boundary(left,right,quiet,48000,30,reviews,working,adjusted_words,prefer_quiet_midpoint=True)
        item.update(after_cut=left['id'],before_cut=right['id'],section_id=left['section_id'],kind=original_boundary['kind'],clock='pause_edited_working_master',original_source_boundary=original_boundary)
        boundaries.append(item)
    points=[0]+[b['sample']for b in boundaries]+[len(working)//2];frames=[0]+[b['frame']for b in boundaries]+[math.ceil(len(working)/2/1600)]
    assert all(a<b for a,b in zip(points,points[1:]))and all(a<b for a,b in zip(frames,frames[1:]))
    entries=[];segments=[];oldspoken=[e for e in original_timeline['entries']if e['kind']=='cut']
    for i,(old,segment)in enumerate(zip(oldspoken,original_timeline['audio_segments'])):
        a,b=points[i:i+2];f0,f1=frames[i:i+2]
        entry={**old,'start_frame':f0,'end_frame':f1,'start':f0/30,'end':f1/30,'source_clock':'original_recovered_composite','working_source_start_sample':a,'working_source_end_sample':b,'working_source_start':a/48000,'working_source_end':b/48000};entries.append(entry)
        segments.append({**segment,'file':portable(output),'timeline_start':a/48000,'timeline_end':b/48000,'timeline_start_sample':a,'timeline_end_sample':b,'working_master_start_sample':a,'working_master_end_sample':b,'working_master_start':a/48000,'working_master_end':b/48000,'source_clock':'original_recovered_composite','timeline_source_clock':'pause_edited_working_master','source_local_start':a/48000,'source_local_end':b/48000,'processed_seconds':(b-a)/48000,'visual_start':f0/30,'visual_end':f1/30})
    card_frames=round(args.ending_card_seconds*30);total_frames=frames[-1]+card_frames
    assert total_frames/30<=original_timeline['max_seconds']+1e-8,'Approved silence plan still exceeds hard cap.'
    if card_frames:
        card=copy.deepcopy(original_timeline['entries'][-1]);assert card['kind']=='silent';card.update(start_frame=frames[-1],end_frame=total_frames,start=frames[-1]/30,end=total_frames/30);entries.append(card)
    sections=[]
    for source in original_timeline['sections']:
        group=[e for e in entries if e['section_id']==source['section_id']];first=next(s for s in segments if s['section_id']==source['section_id']);last=next(s for s in reversed(segments)if s['section_id']==source['section_id'])
        sections.append({**source,'start':group[0]['start'],'end':group[-1]['end'],'speech_start':first['timeline_start'],'speech_end':last['timeline_end'],'working_start_sample':first['timeline_start_sample'],'working_end_sample':last['timeline_end_sample'],'source_clock':'original_recovered_composite'})
    editmap={**plan,'status':'APPLIED_EXACT_QUIET_ONLY','approval_required':False,'approved_plan_sha256':args.approved_plan_sha256,'approved_plan':portable(args.apply_pause_plan),'audio_file_written':True,'working_master':portable(output),'working_master_sha256':digest(output.read_bytes()),'working_pcm_sha256':digest(working),'all_retained_samples_pcm_exact':True,'protected_phrase_pcm_exact_count':68,'spoken_samples_removed':0,'source_samples_removed':plan['removed_samples'],'non_speech_samples_removed':plan['removed_samples'],'speech_tempo':1,'generation_mode':manifest['generation_mode'],'ending_reuse_exception_authorized':manifest.get('ending_reuse_exception_authorized',False),'notes':['The exact approved central-quiet plan was applied with no sample-value changes or crossfade.','Source raw clips still reconstruct the entire recovered original; output working audio retains only the mapped raw ranges.']}
    editpath=directory/'pause-edit-map.json';save(editpath,editmap)
    record={'path':portable(output),'sha256':digest(output.read_bytes()),'pcm_sha256':digest(working),'sample_rate':48000,'channels':1,'sample_width':2,'sample_count':len(working)//2,'duration':len(working)/96000,'edit_map':portable(editpath),'edit_map_sha256':digest(editpath.read_bytes())}
    report=copy.deepcopy(original_report);report.update(analysis_only=False,timeline_committed=True,duration_within_hard_limit=True,working_master=record,original_boundaries=original_report['boundaries'],boundaries=boundaries,working_waveform_silence_regions=quiet,final_timeline_seconds=total_frames/30,final_frame_padding_samples=frames[-1]*1600-len(working)//2,final_card_seconds=args.ending_card_seconds,all_source_pcm_in_order_once=False,raw_source_clips_cover_original_once=True,all_retained_samples_pcm_exact=True,source_samples_removed=plan['removed_samples'],non_speech_samples_removed=plan['removed_samples'],spoken_samples_removed=0,speech_tempo=1)
    for source,adjusted in zip(report['cuts'],cuts):source.update(working_word_start=adjusted['word_start'],working_word_end=adjusted['word_end'],word_timing_clock='original_recovered_composite',working_word_timing_clock='pause_edited_working_master')
    report['notes']=['68 approved lines retain exact protected speech PCM. Only explicitly approved central inter-sentence quiet was removed.','Original words/ASR coordinates remain original-source times; working_word fields and working boundaries have a separate clock.','Raw 14 clips join to the full recovered original, not to the shorter working master. All retained raw ranges map exactly to working audio.','Fresh body plus authorized identical original-speed Kyung ending; this is not one fresh68-line generation.']
    manifest.update(analysis_only=False,working_master=record,timeline_seconds=total_frames/30,continuous_master_placement={'file':portable(output),'source_start_sample':0,'source_end_sample':len(working)//2,'timeline_start_sample':0,'timeline_end_sample':len(working)//2,'audio_restarts':0},source_samples_removed=plan['removed_samples'],non_speech_samples_removed=plan['removed_samples'],spoken_samples_removed=0)
    manifest['original_clip_proof']=manifest.pop('proof');manifest['proof']={'raw_clips_reconstruct_original_recovered_source':True,'retained_raw_ranges_reconstruct_working_exactly':True,'protected_phrase_pcm_exact_count':68,'spoken_samples_removed':0,'non_speech_samples_removed':plan['removed_samples']}
    save(args.out/'alignment-report.json',report);save(args.out/'manifest.json',manifest)
    timeline=copy.deepcopy(original_timeline);timeline.update(preview_only=False,analysis_only=False,duration=total_frames/30,duration_seconds=total_frames/30,frames=total_frames,entries=entries,audio_segments=segments,sections=sections,source_voice_seconds=len(working)/96000,source_voice_samples=len(working)//2,original_source_voice_seconds=len(raw)/96000,original_source_voice_samples=len(raw)//2,source_speech_frames=frames[-1],final_frame_padding_samples=frames[-1]*1600-len(working)//2,final_card_seconds=args.ending_card_seconds,fixed_silent_seconds=args.ending_card_seconds,working_master=record,source_samples_removed=plan['removed_samples'],non_speech_samples_removed=plan['removed_samples'],spoken_samples_removed=0,alignment_report_sha256=digest((args.out/'alignment-report.json').read_bytes()),timing_basis='Authorized original-speed body/ending assembly with independently approved central-quiet removal only. Raw and working source clocks are explicit; all protected speech PCM is retained unchanged.')
    assert len(entries)==69 and len(segments)==68 and len(sections)==14
    save(args.timeline,timeline);print(json.dumps({'status':report['status'],'working_seconds':record['duration'],'film_seconds':timeline['duration'],'entries':69,'sentences':68,'source_samples_removed':plan['removed_samples'],'spoken_samples_removed':0,'tempo':1},ensure_ascii=False))

def build(args):
    config=json.loads(args.config.read_text());spec=json.loads(args.spec.read_text());asr=json.loads(args.asr.read_text())
    blocks=config['blocks'];flat=[(b,c)for b in blocks for c in b['cuts']]
    expected_counts=[9,5,5,5,4,5,5,5,3,4,4,5,5,4]
    assert [len(b['cuts'])for b in blocks]==expected_counts,'Expected the approved 14 blocks / 68 lines.'
    assert len(flat)==68 and len(blocks)==14
    assert config['generation_mode']=='single_take' and config.get('language_code')=='ko'
    assert [b['section_id']for b in blocks]==[s['id']for s in spec['sections']]
    spec_index={c['id']:(s,i,c)for s in spec['sections']for i,c in enumerate(s['cuts'])}
    assert len(spec_index)==sum(len(s['cuts'])for s in spec['sections']),'Duplicate spec cut ID.'
    brief=json.loads(args.brief.read_text())
    assert [[c['text']for c in b['cuts']]for b in blocks]==[[c['text']for c in b['lines']]for b in brief['blocks']],'Every user line must remain exact.'
    assert all(c['text']==spec_index[c['id']][2]['narration']for _,c in flat),'Spec narration and exact user text differ.'
    assert flat[0][1]['text']=='R&D 업무에 AI를 더합니다.'
    with wave.open(str(args.master),'rb')as w:params=w.getparams();pcm=w.readframes(w.getnframes())
    rate=params.framerate;duration=params.nframes/rate
    assert params.nchannels==1 and rate==48000 and params.sampwidth==2,'Master must be the unmodified 48000 Hz mono 16-bit PCM.'
    fps=spec['output']['fps'];assert fps==30,'The production frame/sample contract is 30 fps / 48000 Hz.'
    assert args.ending_card_seconds>=0 and abs(args.ending_card_seconds*fps-round(args.ending_card_seconds*fps))<1e-7
    master_sha=digest(args.master.read_bytes());asr_sha=digest(args.asr.read_bytes());words=whisper_words(asr)
    recovery=None
    if args.recovery_map.exists():
        candidate=json.loads(args.recovery_map.read_text())
        if args.master.resolve()==(ROOT/candidate['composite']).resolve():
            assert master_sha==candidate['composite_sha256']
            assert candidate['ending_reuse_exception_authorized']and candidate['tempo']==1
            assert digest((ROOT/candidate['authorization']).read_bytes())==candidate['authorization_sha256']
            recovery=candidate
    reviews={}
    if args.review_file and args.review_file.exists():
        reviews=json.loads(args.review_file.read_text())
        assert reviews.get('master_sha256')==master_sha and reviews.get('asr_sha256')==asr_sha,'Review belongs to another take/ASR.'
    pronunciation=config.get('pronunciation_map',{});expected='';cuts=[]
    for block,cut in flat:
        normalized,_=normalize(cut['spoken_text'],pronunciation)
        assert normalized
        cuts.append({**cut,'section_id':block['section_id'],'char_start':len(expected),'char_end':len(expected)+len(normalized),'normalized':normalized})
        expected+=normalized
    raw='';owners=[]
    for wi,word in enumerate(words):raw+=word['word'];owners.extend([wi]*len(word['word']))
    actual,char_word=normalize(raw,pronunciation,owners);mapping,matches,edits,distance=edit_align(expected,actual)
    quiet=quiet_regions(pcm,rate,params.sampwidth,args.quiet_dbfs)
    report={'revision':9,'status':'IN_PROGRESS','master':portable(args.master),'master_sha256':master_sha,'asr':portable(args.asr),'asr_sha256':asr_sha,'master_duration':duration,'master_samples':params.nframes,'config_sha256':digest(args.config.read_bytes()),'spec_sha256':digest(args.spec.read_bytes()),'brief_sha256':digest(args.brief.read_bytes()),'normalization':'Saved pronunciation/number aliases and spacing/punctuation only; raw ASR and every discrepancy are retained.','expected_chars':len(expected),'asr_chars':len(actual),'exact_character_coverage':sum(matches)/len(expected),'edit_distance':distance,'edit_count':len(edits),'edits':edits,'cuts':[],'boundaries':[],'waveform_silence_regions':quiet,'waveform_rms_window_seconds':.01,'quiet_threshold_dbfs':args.quiet_dbfs,'required_output_tempo':1,'new_tts_by_this_script':False}
    if asr.get('source_mapping_proof'):
        assert asr['source_mapping_proof']['current_composite_sha256']==master_sha
        report['source_mapping_proof']=asr['source_mapping_proof']
    save(args.out/'alignment-report.json',report)
    for cut in cuts:
        a,b=cut['char_start'],cut['char_end'];mapped=[mapping[k]for k in range(a,b)if mapping[k]is not None]
        assert mapped,f"Missing entire approved line: {cut['id']}"
        first=min(char_word[k]for k in mapped);last=max(char_word[k]for k in mapped);coverage=sum(matches[a:b])/(b-a)
        row={'id':cut['id'],'section_id':cut['section_id'],'expected':cut['text'],'spoken_text':cut['spoken_text'],'normalized':cut['normalized'],'asr_text':' '.join(w['word'].strip()for w in words[first:last+1]),'character_coverage':coverage,'first_word_index':first,'last_word_index':last,'word_start':words[first]['start'],'word_end':words[last]['end'],'review_required':coverage<.98}
        cut.update(row);report['cuts'].append(row)
    save(args.out/'alignment-report.json',report)
    assert report['exact_character_coverage']>=args.coverage_min,'Whole-script ASR coverage below review gate.'
    assert all(c['character_coverage']>=args.cut_coverage_min for c in cuts),'At least one approved line lacks sufficient lexical evidence.'
    assert all(a['last_word_index']<b['first_word_index']for a,b in zip(cuts,cuts[1:])),'Adjacent approved lines share an ASR word; independently review this region.'
    boundaries=[]
    for left,right in zip(cuts,cuts[1:]):
        info=safe_boundary(left,right,quiet,rate,fps,reviews,pcm,words)
        info.update(after_cut=left['id'],before_cut=right['id'],section_id=left['section_id'],kind='visual_only_within_continuous_block'if left['section_id']==right['section_id']else'between_contiguous_source_blocks')
        boundaries.append(info);report['boundaries']=boundaries;save(args.out/'alignment-report.json',report)
    speech_frames=math.ceil(params.nframes*fps/rate);card_frames=round(args.ending_card_seconds*fps);total_frames=speech_frames+card_frames
    limits=[315,spec['output'].get('max_seconds',315),config.get('max_video_seconds',315),brief.get('max_seconds',315)]
    if args.max_seconds is not None:limits.append(args.max_seconds)
    maximum=min(limits)
    report.update(proposed_duration_seconds=total_frames/fps,source_speech_frames=speech_frames,final_card_frames=card_frames,maximum_seconds=maximum)
    save(args.out/'alignment-report.json',report)
    if not args.analysis_only:
        assert total_frames/fps<=maximum+1e-8,f'Unmodified take + final card is {total_frames/fps:.3f}s, above hard maximum {maximum}s. No speedup or spoken trimming was performed; ask root to review the explicit final-card option.'
    points=[0]+[b['sample']for b in boundaries]+[params.nframes];frames=[0]+[b['frame']for b in boundaries]+[speech_frames]
    assert all(a<b for a,b in zip(points,points[1:])) and all(a<b for a,b in zip(frames,frames[1:])), 'A visual/source line span became empty.'
    entries=[];audio=[]
    for i,cut in enumerate(cuts):
        section,ci,sourcecut=spec_index[cut['id']];a,b=points[i:i+2];f0,f1=frames[i:i+2]
        entries.append({'section_id':cut['section_id'],'kind':'cut','start_frame':f0,'end_frame':f1,'start':f0/fps,'end':f1/fps,'cut_index':ci,'cut_id':cut['id'],'caption':cut['text'],'source_start':a/rate,'source_end':b/rate,'source_start_sample':a,'source_end_sample':b,'tempo':1})
        audio.append({'section_id':cut['section_id'],'cut_id':cut['id'],'file':portable(args.master),'timeline_start':a/rate,'timeline_end':b/rate,'timeline_start_sample':a,'timeline_end_sample':b,'source_master_start':a/rate,'source_master_end':b/rate,'source_master_start_sample':a,'source_master_end_sample':b,'source_local_start':a/rate,'source_local_end':b/rate,'tempo':1,'processed_seconds':(b-a)/rate,'audio_restart':False,'visual_start':f0/fps,'visual_end':f1/fps})
    ending=next(s for s in spec['sections']if s['id']=='ending');assert len(ending['cuts'])==6 and not ending['cuts'][5]['narration']
    assert [e['cut_index']for e in entries if e['section_id']=='ending']==[0,1,2,4],'Retain physical ending indices and omit index3 without inserting silence.'
    if card_frames:entries.append({'section_id':'ending','kind':'silent','start_frame':speech_frames,'end_frame':total_frames,'start':speech_frames/fps,'end':total_frames/fps,'cut_index':5,'cut_id':ending['cuts'][5]['id'],'caption':'','tempo':1})
    clips=[];sections=[];joined=b''
    for bi,block in enumerate(blocks):
        indices=[i for i,c in enumerate(cuts)if c['section_id']==block['section_id']];a=points[indices[0]];b=points[indices[-1]+1];content=pcm[a*params.sampwidth:b*params.sampwidth];path=args.out/f'vo{bi+1}.wav'
        if not path.exists():
            with wave.open(str(path),'wb')as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(rate);w.writeframes(content)
        with wave.open(str(path),'rb')as w:assert w.readframes(w.getnframes())==content
        joined+=content;record={'index':bi+1,'section_id':block['section_id'],'file':portable(path),'sha256':digest(path.read_bytes()),'pcm_sha256':digest(content),'source_start_sample':a,'source_end_sample':b,'source_start':a/rate,'source_end':b/rate,'duration_samples':b-a,'duration':(b-a)/rate,'prompt':block['spoken_text'],'caption_script':block['text'],'source_is_exact_master_slice':True,'timeline_start_sample':a,'timeline_end_sample':b,'timeline_start_seconds':a/rate,'timeline_end_seconds':b/rate,'tempo_ratio':1,'audio_restart':False}
        clips.append(record);sid=block['section_id'];group=[e for e in entries if e['section_id']==sid]
        sections.append({'section_id':sid,'start':group[0]['start'],'end':group[-1]['end'],'source':record,'speech_start':a/rate,'speech_end':b/rate,'source_start_sample':a,'source_end_sample':b,'continuous_audio':True})
    assert joined==pcm and clips[0]['source_start_sample']==0 and clips[-1]['source_end_sample']==params.nframes,'Source sample conservation failed.'
    assert all(a['source_end_sample']==b['source_start_sample']for a,b in zip(clips,clips[1:]))
    assert len(entries)==(69 if card_frames else 68)and all(a['end_frame']==b['start_frame']for a,b in zip(entries,entries[1:]))
    report.update(status='PASS_WITH_ASR_VARIANTS'if any(c['review_required']for c in report['cuts'])else'PASS',script_blocks_covered=14,script_cuts_covered=68,all_source_cut_pcm_matches=True,all_source_pcm_in_order_once=True,source_pcm_sha256=digest(pcm),joined_clip_pcm_sha256=digest(joined),final_timeline_seconds=total_frames/fps,source_head_and_eof_preserved=True,audio_restarts_at_visual_boundaries=False,inserted_inter_block_or_inter_cut_silence_samples=0,final_frame_padding_samples=speech_frames*1600-params.nframes,final_card_seconds=args.ending_card_seconds,notes=['No tempo change, narration generation, wording change, or old outer audio reuse.','The master is played once continuously; 14 exact WAV slices are provenance, not separately restarted audio.','All 67 lexical boundaries are quantized inside sustained waveform quiet or explicitly current-master reviewed.','ASR variants remain evidence differences; source/PCM validation does not prove pronunciation or subjective listening acceptance.'])
    manifest={'revision':9,'master':{'path':portable(args.master),'sha256':master_sha,'pcm_sha256':digest(pcm),'sample_rate':rate,'channels':1,'sample_width':2,'sample_count':params.nframes,'duration':duration},'config':config,'config_sha256':digest(args.config.read_bytes()),'generated_prompt_sha256':digest(config['generated_prompt'].encode()),'brief_sha256':digest(args.brief.read_bytes()),'generation_mode':'single_take','required_output_tempo':1,'cuts':clips,'clips':clips,'alignment_report':portable(args.out/'alignment-report.json'),'timeline_seconds':total_frames/fps,'continuous_master_placement':{'file':portable(args.master),'source_start_sample':0,'source_end_sample':params.nframes,'timeline_start_sample':0,'timeline_end_sample':params.nframes,'audio_restarts':0},'proof':{'ordered_source_pcm_once':True,'source_pcm_sha256':digest(pcm),'joined_clip_pcm_sha256':digest(joined),'source_samples_removed':0,'source_samples_duplicated':0},'note':'Every source sample is retained in order. 14 block WAVs are exact slices; narration mix uses the whole original master once.'}
    report.update(analysis_only=args.analysis_only,duration_within_hard_limit=total_frames/fps<=maximum+1e-8,timeline_committed=not args.analysis_only)
    manifest.update(analysis_only=args.analysis_only)
    if recovery:
        mode={'generation_mode':'single_take_with_authorized_original_ending_reuse','ending_reuse_exception_authorized':True,'fresh_body_narration':True,'new_full_narration':False,'speech_tempo':1,'source_assembly':recovery,'source_assembly_sha256':digest(args.recovery_map.read_bytes())}
        report.update(mode);manifest.update(mode)
    save(args.out/'alignment-report.json',report);save(args.out/'manifest.json',manifest)
    timeline={'revision':9,'preview_only':False,'allow_over_five_minutes':True,'fps':fps,'duration':total_frames/fps,'duration_seconds':total_frames/fps,'frames':total_frames,'max_seconds':maximum,'target_seconds':brief.get('goal_seconds',300),'tempo':1,'source_voice_seconds':duration,'source_voice_samples':params.nframes,'source_speech_frames':speech_frames,'final_frame_padding_samples':speech_frames*1600-params.nframes,'final_card_seconds':args.ending_card_seconds,'fixed_silent_seconds':args.ending_card_seconds,'inserted_inter_block_silence_seconds':0,'continuous_master_audio':True,'entries':entries,'audio_segments':audio,'sections':sections,'alignment_report_sha256':digest((args.out/'alignment-report.json').read_bytes()),'timing_basis':'All 68 fresh single-take sentences on the original master sample clock. No title/gap insertion, voice speed change, or old outer audio. Only final frame padding and explicit final card are added.'}
    if recovery:timeline.update(mode,timing_basis='Authorized recovered original-speed source: new opening/tasks plus identical old Kyung ending. Current-source ASR and waveform boundaries; no speed change or inserted intermediate silence.')
    if args.analysis_only:
        timeline.update(preview_only=True,analysis_only=True)
        save(args.out/'timeline-analysis.json',timeline);save(args.out/'manifest-original.json',manifest);save(args.out/'alignment-report-original.json',report)
        if args.propose_pause_edit:
            plan=propose_pause_edit(args,report,pcm,words,rate)
            print(json.dumps({'pause_plan':'PROPOSED_NOT_APPLIED','verified_capacity_seconds':plan['verified_capacity_seconds'],'remove_seconds':plan['removed_seconds'],'working_seconds':plan['target_seconds'],'film_seconds':plan['proposed_total_seconds_with_card']},ensure_ascii=False))
    else:save(args.timeline,timeline)
    print(json.dumps({'status':report['status'],'analysis_only':args.analysis_only,'production_timeline_committed':not args.analysis_only,'duration_within_hard_limit':total_frames/fps<=maximum+1e-8,'blocks':14,'sentences':68,'boundaries':67,'entries':len(entries),'tempo':1,'duration':total_frames/fps,'master_duration':duration,'maximum':maximum,'timeline':str(args.out/'timeline-analysis.json'if args.analysis_only else args.timeline)},ensure_ascii=False))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,default=ROOT/'narration/ko.json');p.add_argument('--spec',type=Path,default=ROOT/'spec.json');p.add_argument('--brief',type=Path,default=ROOT/'reference/user-revision9-brief.json')
    p.add_argument('--master',type=Path,default=ROOT/'narration/elevenlabs/take.wav');p.add_argument('--asr',type=Path,default=ROOT/'narration/transcription/take.json')
    p.add_argument('--out',type=Path,default=ROOT/'narration/elevenlabs');p.add_argument('--timeline',type=Path,default=ROOT/'timeline.json')
    p.add_argument('--review-file',type=Path,default=ROOT/'narration/transcription/reviews/boundary-reviews.json')
    p.add_argument('--coverage-min',type=float,default=.92);p.add_argument('--cut-coverage-min',type=float,default=.80);p.add_argument('--quiet-dbfs',type=float,default=-42)
    p.add_argument('--ending-card-seconds',type=float,default=4);p.add_argument('--max-seconds',type=float)
    p.add_argument('--analysis-only',action='store_true',help='Create original exact block clips and evidence even when raw duration exceeds the cap; never commit a production timeline.')
    p.add_argument('--propose-pause-edit',action='store_true',help='With --analysis-only, write a current-ASR/quiet-only virtual plan, without writing edited audio.')
    p.add_argument('--target-working-seconds',type=float,default=310.5);p.add_argument('--phrase-pause-seconds',type=float,default=.3);p.add_argument('--paragraph-pause-seconds',type=float,default=.4)
    p.add_argument('--assemble-recovery-only',action='store_true',help='Assemble the explicitly authorized original-speed ending; do not align, pause-edit or commit a production timeline.')
    p.add_argument('--recovery-map',type=Path,default=ROOT/'narration/recovery/recovery-map.json')
    p.add_argument('--apply-pause-plan',type=Path,help='Apply only an exact independently approved proposal; no automatic approval.')
    p.add_argument('--approved-plan-sha256',help='SHA-256 explicitly approved by root after independent review.')
    args=p.parse_args()
    if args.assemble_recovery_only:assemble_recovery(args);return
    if args.apply_pause_plan:apply_approved_pause_plan(args);return
    assert not args.propose_pause_edit or args.analysis_only,'Pause proposals require analysis-only mode.'
    try:build(args)
    except Exception as exc:
        path=args.out/'alignment-report.json';report=json.loads(path.read_text())if path.exists()else{}
        report.update(status='FAIL',error=f'{type(exc).__name__}: {exc}')
        save(path,report);raise

if __name__=='__main__':main()

