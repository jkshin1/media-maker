#!/usr/bin/env python3
"""Place reviewed new narration into the immutable Revision9 cut slots.

The default action is analysis only. --render is gated by 68 lexical anchors,
67 word/waveform-safe boundaries and exact protected PCM placement. Neither
the master nor the timeline is changed. BGM is an approved final PCM stem,
not a source track to loop, duck, normalize or fade again.
"""
from __future__ import annotations
import argparse
from array import array
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import unicodedata
import wave

ROOT = Path(__file__).resolve().parent
RATE = 48000
SLOT_GEOMETRY_SHA256 = '884046c0cdb38f5b08334237a9d33a137d236ec9bd9badf8e51a1d336a42df38'
MUSIC_FILE_SHA256 = '12d9b6b71aa83859bad9c53becaa74c4b962113a66b6206a0bec57e8057d1af0'
MUSIC_PCM_SHA256 = 'c8be57c5a5718090679297fe1ca09c4a6733c02c01d33141e41df82c63be0644'
AUTHORIZED_RETIME_PLAN_SHA256 = 'ff38348f4f94a046381dfc29d357e8a6ebfb14224d4ab011e1706725cbda7abf'

def digest(data): return hashlib.sha256(data).hexdigest()

def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def relative(path):
    try: return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError: return str(Path(path).resolve())

def read_wav(path, channels=None):
    with wave.open(str(path), 'rb') as f:
        p = f.getparams(); pcm = f.readframes(p.nframes)
    assert p.framerate == RATE and p.sampwidth == 2 and p.comptype == 'NONE'
    if channels is not None: assert p.nchannels == channels
    return p, pcm

def write_wav(path, pcm, channels):
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), 'wb') as f:
        f.setnchannels(channels); f.setsampwidth(2); f.setframerate(RATE)
        f.writeframes(pcm)

def normalize(text, pronunciation, owners=None):
    """Typography/approved pronunciation aliases; never equate 로트 and 랏."""
    chars=[]; ids=[]
    for i,c in enumerate(text):
        for out in unicodedata.normalize('NFKC',c).lower():
            if not out.isspace(): chars.append(out); ids.append(owners[i] if owners is not None else i)
    value=''.join(chars)
    aliases=dict(pronunciation)
    aliases.update({'CNC':'씨앤씨','씨엔씨':'씨앤씨','SW':'에스더블유','MA':'엠에이','아이전트':'에이전트','써머리':'서머리','12개':'열두개','십이개':'열두개','1건':'한건','2시간':'두시간','40분':'사십분','20분':'이십분','PM':'피엠','K-파라미터':'케이파라미터','1일':'일일','5개':'다섯개'})
    # 로트 is a rejected spoken form; it cannot be hidden by an alias.
    aliases={s:t for s,t in aliases.items() if '로트' not in s}
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
            ids=ids[:pos]+mapped+ids[pos+len(source):]; offset=pos+len(target)
    keep=[i for i,c in enumerate(value) if c.isalnum()]
    return ''.join(value[i] for i in keep),[ids[i] for i in keep]

def edit_align(expected,actual):
    n,m=len(expected),len(actual); directions=bytearray((n+1)*(m+1)); previous=array('H',range(m+1))
    for j in range(1,m+1): directions[j]=2
    for i,a in enumerate(expected,1):
        current=array('H',[i]+[0]*m); directions[i*(m+1)]=1
        for j,b in enumerate(actual,1):
            choices=(previous[j-1]+(a!=b),previous[j]+1,current[j-1]+1)
            cost=min(choices); op=choices.index(cost); current[j]=cost; directions[i*(m+1)+j]=op
        previous=current
    mapping=[None]*n; matches=[False]*n; edits=[]; i=n; j=m
    while i or j:
        op=directions[i*(m+1)+j]
        if i and j and op==0:
            mapping[i-1]=j-1; matches[i-1]=expected[i-1]==actual[j-1]
            if not matches[i-1]: edits.append({'kind':'substitution','expected_index':i-1,'actual_index':j-1,'expected':expected[i-1],'actual':actual[j-1]})
            i-=1; j-=1
        elif i and (not j or op==1):
            edits.append({'kind':'deletion','expected_index':i-1,'actual_index':j,'expected':expected[i-1]}); i-=1
        else:
            edits.append({'kind':'insertion','expected_index':i,'actual_index':j-1,'actual':actual[j-1]}); j-=1
    return mapping,matches,list(reversed(edits)),int(previous[m])

def words_from(j):
    words=j.get('words') or [w for s in j.get('segments',[]) for w in s.get('words',[])]
    assert words, 'Word timestamps are required.'
    result=[{'word':w.get('word',w.get('text','')),'start':float(w['start']),'end':float(w['end']),'probability':w.get('probability')} for w in words]
    assert all(w['start']<=w['end'] for w in result)
    assert all(a['start']<=b['start'] for a,b in zip(result,result[1:]))
    return result

def quiet_regions(pcm, threshold):
    import numpy as np
    raw=np.frombuffer(pcm,dtype='<i2').astype(np.float64)/32768
    window=480; rms=np.sqrt(np.mean(raw[:len(raw)//window*window].reshape(-1,window)**2,axis=1))
    db=20*np.log10(np.maximum(rms,1e-12)); rows=[]; start=None
    for i,is_quiet in enumerate(list(db<threshold)+[False]):
        if is_quiet and start is None: start=i
        if not is_quiet and start is not None:
            if i-start>=8: rows.append({'start_sample':start*window,'end_sample':i*window,'start':start*.01,'end':i*.01,'duration':(i-start)*.01,'peak_10ms_rms_dbfs':float(max(db[start:i]))})
            start=None
    return rows

def geometry(timeline):
    sig=[{k:e.get(k) for k in ['section_id','kind','cut_id','cut_index','start_frame','end_frame']} for e in timeline['entries']]
    return digest(json.dumps(sig,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())

def rooted(value):
    path=Path(value)
    return path if path.is_absolute() else ROOT/path

def bound_file(value):
    """Resolve an explicitly SHA-bound portable input, without modifying it."""
    path=rooted(value['path'])
    assert digest(path.read_bytes())==value['sha256'], f'Input SHA mismatch: {path}'
    return path

def load_inputs(args,config):
    """Read either the historical diagnostic take or the approved new pair.

    The concatenated PCM and word clock exist only in memory for analysis.
    Every final placement still names one untouched source file and its local
    sample range. No synthetic intermediate WAV is presented as a single take.
    """
    flat=[dict(c,section_id=b['section_id']) for b in config['blocks'] for c in b['cuts']]
    assert len(flat)==68 and len(config['blocks'])==14
    inputs=[]; parts=[]; combined=[]; all_words=[]; offset=0
    if args.sources:
        assert not args.prefix_lines, 'The earlier prefix analysis cannot be reused for the two new sources.'
        descriptor=json.loads(args.sources.read_text())
        assert descriptor['generation_mode']=='two_part_with_user_authorization'
        assert descriptor['speech_tempo']==1
        authorization_binding=descriptor['authorization'] if isinstance(descriptor['authorization'],dict) else {'path':descriptor['authorization'],'sha256':descriptor['authorization_sha256']}
        authorization=bound_file(authorization_binding); inputs.extend([args.sources,authorization])
        auth=json.loads(authorization.read_text())
        assert auth['authorization_source']=='direct_user_reply_in_current_chat' and auth['generation_mode']==descriptor['generation_mode'] and auth['speech_speed_ratio']==1
        assert len(descriptor['parts'])==2
        rows=descriptor['parts']; assert [len(p['cut_ids']) for p in rows]==[33,35]
        assert [c for p in rows for c in p['cut_ids']]==[c['id'] for c in flat], 'Two sources must cover all 68 approved cuts in exact order.'
        mode='two_part_with_user_authorization'
    else:
        rows=[{'part_id':'diagnostic_single_take','master':relative(args.master),'master_sha256':digest(args.master.read_bytes()),'asr':relative(args.asr),'asr_sha256':digest(args.asr.read_bytes()),'cut_ids':[c['id'] for c in flat]}]
        descriptor={}; mode='single_take'
    for row in rows:
        master=rooted(row['master']); asr_path=rooted(row['asr'])
        provenance=[]; imported=None
        provenance_bindings=row.get('provenance',[])
        if isinstance(provenance_bindings,str): provenance_bindings=[{'path':provenance_bindings,'sha256':row['provenance_sha256']}]
        for binding in provenance_bindings:
            path=bound_file(binding); inputs.append(path); provenance.append({'path':relative(path),'sha256':binding['sha256']})
            data=json.loads(path.read_text())
            if 'master_sha256' in data:
                imported=data
                assert rooted(data['master_file']).resolve()==master.resolve()
                assert data['speech_tempo']==1 and data['generation_mode']==mode
                assert (data['voice_id'],data['model_id'],data['language_code'])==(descriptor['voice_id'],descriptor['model_id'],descriptor['language_code'])
                assert data['authorization_sha256']==authorization_binding['sha256']
                prompt=bound_file({'path':data['prompt_file'],'sha256':data['prompt_sha256']}); inputs.append(prompt)
        if args.sources: assert imported is not None, 'Each generated part requires URL-free import provenance bound to its original master and exact prompt.'
        master_sha=row.get('master_sha256',(imported or {}).get('master_sha256'))
        asr_sha=digest(asr_path.read_bytes())
        assert digest(master.read_bytes())==master_sha
        if row.get('asr_sha256'): assert asr_sha==row['asr_sha256']
        params,pcm=read_wav(master,1); local_words=words_from(json.loads(asr_path.read_text()))
        assert all(w['end']<=params.nframes/RATE+.02 for w in local_words), 'ASR extends beyond its own source.'
        inputs.extend([master,asr_path])
        part={'part_id':row['part_id'],'master':relative(master),'master_sha256':master_sha,'master_pcm_sha256':digest(pcm),'asr':relative(asr_path),'asr_sha256':asr_sha,'cut_ids':row['cut_ids'],'samples':params.nframes,'seconds':params.nframes/RATE,'sample_rate':RATE,'channels':1,'sample_width':2,'virtual_start_sample':offset,'virtual_end_sample':offset+params.nframes,'first_word_index':len(all_words),'provenance':provenance}
        for w in local_words:
            all_words.append({**w,'start':w['start']+offset/RATE,'end':w['end']+offset/RATE,'source_part_id':row['part_id'],'source_local_start':w['start'],'source_local_end':w['end']})
        part['last_word_index']=len(all_words)-1; parts.append(part); combined.append(pcm); offset+=params.nframes
    identity_payload={'generation_mode':mode,'authorization_sha256':authorization_binding['sha256'] if args.sources else None,'parts':[{k:p[k] for k in ['part_id','master_sha256','asr_sha256','cut_ids','provenance']} for p in parts]}
    identity=digest(json.dumps(identity_payload,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
    metadata={'generation_mode':mode,'source_identity_sha256':identity,'source_identity_payload':identity_payload,'source_parts':parts,'source_manifest':relative(args.sources) if args.sources else None,'source_manifest_sha256':digest(args.sources.read_bytes()) if args.sources else None,'two_part_exception_authorized':bool(args.sources),'authorization':authorization_binding if args.sources else None,'source_file_count':len(parts),'ordered_source_pcm_sha256':digest(b''.join(combined)),'virtual_clock_note':'Internal ordered-source sample clock only; this is not a generated single-take file. Final cut maps explicitly identify source-local samples.'}
    args.source_input_paths=list(dict.fromkeys(inputs))
    return flat,parts,b''.join(combined),all_words,metadata

def align_parts(flat,parts,words,pronunciation,prefix_lines=None):
    """Align each new ASR only to the approved sentences for its own part."""
    byid={c['id']:c for c in flat}; cuts=[]; all_matches=[]; edits=[]; distance=0; expected=''
    for part in parts:
        approved=[byid[c] for c in part['cut_ids']]
        if prefix_lines: approved=approved[:prefix_lines]
        text=''; local=[]
        for c in approved:
            normalized,_=normalize(c['spoken_text'],pronunciation)
            local.append(dict(c,char_start=len(text),char_end=len(text)+len(normalized),normalized=normalized,source_part_id=part['part_id'])); text+=normalized
        raw=''; owners=[]
        for wi in range(part['first_word_index'],part['last_word_index']+1):
            raw+=words[wi]['word']; owners.extend([wi]*len(words[wi]['word']))
        actual,word_owner=normalize(raw,pronunciation,owners)
        mapping,matches,part_edits,part_distance=edit_align(text,actual)
        for c in local:
            a,b=c['char_start'],c['char_end']; mapped=[mapping[i] for i in range(a,b) if mapping[i] is not None]
            if mapped:
                first=min(word_owner[i] for i in mapped); last=max(word_owner[i] for i in mapped)
                c.update(first_word_index=first,last_word_index=last,word_start=words[first]['start'],word_end=words[last]['end'],asr_text=' '.join(w['word'].strip() for w in words[first:last+1]))
            c['character_coverage']=sum(matches[a:b])/(b-a)
            c['char_start']+=len(expected); c['char_end']+=len(expected)
        cuts.extend(local); all_matches.extend(matches); expected+=text; distance+=part_distance
        edits.extend([dict(e,source_part_id=part['part_id']) for e in part_edits])
    return cuts,all_matches,edits,distance,expected

def find_boundary(left,right,words,quiet,reviews):
    review=next((x for x in reviews.get('boundaries',[]) if x['after_cut']==left['id'] and x['before_cut']==right['id']),None)
    lo=left['word_end']; hi=right['word_start']; center=(lo+hi)/2
    common={'after_cut':left['id'],'before_cut':right['id'],'left_word_end':lo,'right_word_start':hi,'lexical_gap_seconds':hi-lo,'between_source_parts':left['source_part_id']!=right['source_part_id']}
    if review:
        q=review['quiet']; a=q['start_sample']; b=q['end_sample']; point=review['source_boundary_sample']
        assert a<point<b and review.get('evidence')
        assert review['actual_previous_speech_end_sample']<=a and review['actual_next_speech_start_sample']>=b
        common.update(status='REVIEWED_CURRENT_TAKE',quiet=q,source_boundary_sample=point,review=review)
        return common
    valid=[]; candidates=[]
    for q in quiet:
        a=max(lo,q['start']); b=min(hi,q['end'])
        if b-a>=.08:
            valid.append((abs((a+b)/2-center),q,round((a+b)/2*RATE)))
        # Leading pauses can be wrongly assigned to a timestamped word. This
        # relaxed proposal is evidence for independent review, never a pass.
        left_word=words[left['last_word_index']]; right_word=words[right['first_word_index']]
        if q['start']>left_word['start']+.04 and q['end']<right_word['end']-.02 and abs((q['start']+q['end'])/2-center)<2:
            candidates.append((abs((q['start']+q['end'])/2-center),q,round((q['start']+q['end'])/2*RATE)))
    if valid:
        _,q,point=min(valid,key=lambda x:x[0]); common.update(status='WORD_WAVE_SAFE',quiet=q,source_boundary_sample=point)
    elif candidates:
        _,q,point=min(candidates,key=lambda x:x[0]); common.update(status='REVIEW_REQUIRED_ASR_PAUSE_ATTRIBUTION',candidate_quiet=q,candidate_source_boundary_sample=point)
    else: common.update(status='REVIEW_REQUIRED_NO_SUSTAINED_LEXICAL_GAP')
    return common

def analyze(args):
    config=json.loads(args.config.read_text()); timeline=json.loads(args.timeline.read_text())
    assert geometry(timeline)==SLOT_GEOMETRY_SHA256, 'Fixed approved slot geometry changed.'
    assert (timeline['fps'],timeline['frames'],timeline['duration'])==(30,9435,314.5)
    flat,parts,pcm,words,source_metadata=load_inputs(args,config)
    total_samples=len(pcm)//2
    source_sha=parts[0]['master_sha256'] if len(parts)==1 else None
    asr_sha=parts[0]['asr_sha256'] if len(parts)==1 else None
    reviews={}
    if args.reviews.exists():
        reviews=json.loads(args.reviews.read_text())
        if args.sources:
            assert reviews['source_identity_sha256']==source_metadata['source_identity_sha256'], 'Boundary review belongs to different source pair/ASRs.'
        else:
            assert reviews['master_sha256']==source_sha and reviews['asr_sha256']==asr_sha, 'Review belongs to different audio/ASR.'
        args.source_input_paths.append(args.reviews)
    cuts,matches,edits,distance,expected=align_parts(flat,parts,words,config['pronunciation_map'],args.prefix_lines)
    quiet=quiet_regions(pcm,args.quiet_dbfs)
    boundaries=[find_boundary(a,b,words,quiet,reviews) if 'word_end' in a and 'word_start' in b else {'after_cut':a['id'],'before_cut':b['id'],'status':'MISSING_LEXICAL_ANCHOR'} for a,b in zip(cuts,cuts[1:])]
    slots={e['cut_id']:e for e in timeline['entries'] if e['kind']=='cut'}
    for i,c in enumerate(cuts):
        part=next(p for p in parts if p['part_id']==c['source_part_id'])
        slot=slots[c['id']]; c.update(slot_start_sample=slot['start_frame']*1600,slot_end_sample=slot['end_frame']*1600,slot_seconds=(slot['end_frame']-slot['start_frame'])/30)
        if c['character_coverage']<.80 or 'word_start' not in c:
            c.update(source_start_sample=None,source_end_sample=None,boundary_review_complete=False,retained_source_seconds=None,slot_shortage_seconds=None,protected_speech_shortage_seconds=None,fit_status='UNAVAILABLE_MISSING_LEXICAL_EVIDENCE',raw_asr_lot_variant_words=[])
            continue
        before=boundaries[i-1] if i else None; after=boundaries[i] if i<len(cuts)-1 else None
        bq=(before or {}).get('quiet',(before or {}).get('candidate_quiet'))
        aq=(after or {}).get('quiet',(after or {}).get('candidate_quiet'))
        complete_before=i==0 or (before and before['status'] in ['WORD_WAVE_SAFE','REVIEWED_CURRENT_TAKE'])
        complete_after=i==len(cuts)-1 or (after and after['status'] in ['WORD_WAVE_SAFE','REVIEWED_CURRENT_TAKE'])
        # Include waveform tails beyond approximate ASR word ends, and 80ms
        # quiet guards. Shared source partitions prevent duplicated samples.
        start=0 if i==0 else max((before or {}).get('source_boundary_sample',(before or {}).get('candidate_source_boundary_sample',0)), (bq['end_sample']-3840) if bq else math.floor(c.get('word_start',0)*RATE)-3840)
        end=total_samples if i==len(cuts)-1 and not args.prefix_lines else min((after or {}).get('source_boundary_sample',(after or {}).get('candidate_source_boundary_sample',total_samples)), (aq['start_sample']+3840) if aq else math.ceil(c.get('word_end',total_samples/RATE)*RATE)+3840)
        if args.prefix_lines and i==len(cuts)-1:
            terminal=[q for q in quiet if q['start']>=c.get('word_end',total_samples/RATE) and q['start']<c.get('word_end',0)+1.5]
            if terminal:
                aq=min(terminal,key=lambda q:q['start']); end=aq['start_sample']+3840
            complete_after=False
        leading=next((q for q in quiet if q['start_sample']==0),None)
        protected_start=bq['end_sample'] if bq else (leading['end_sample'] if i==0 and leading else 0)
        protected_end=aq['start_sample'] if aq else (total_samples if i==len(cuts)-1 and not args.prefix_lines else min(total_samples,math.ceil(c['word_end']*RATE)))
        c.update(protected_speech_start_sample=protected_start,protected_speech_end_sample=protected_end,protected_speech_seconds=(protected_end-protected_start)/RATE,protected_speech_shortage_seconds=max(0,(protected_end-protected_start)/RATE-c['slot_seconds']),available_total_quiet_guard_seconds=c['slot_seconds']-(protected_end-protected_start)/RATE,protected_span_basis='All signal between adjacent verified inter-sentence quiet regions; ASR timestamps can include quiet and end before phoneme tails. Terminal prefix boundary is a review candidate only.')
        c.update(source_start_sample=max(part['virtual_start_sample'],start),source_end_sample=min(part['virtual_end_sample'],end),boundary_review_complete=bool(complete_before and complete_after))
        c.update(source_file=part['master'],source_file_sha256=part['master_sha256'],source_local_start_sample=c['source_start_sample']-part['virtual_start_sample'],source_local_end_sample=c['source_end_sample']-part['virtual_start_sample'],source_sample_clock='source_start/end_sample are ordered-source virtual coordinates; source_local_start/end_sample index the untouched named WAV.')
        c['retained_source_seconds']=(c['source_end_sample']-c['source_start_sample'])/RATE
        c['slot_shortage_seconds']=max(0,c['retained_source_seconds']-c['slot_seconds'])
        c['word_span_seconds']=c.get('word_end',0)-c.get('word_start',0)
        c['fit_status']='BLOCKED_SLOT_OVERFLOW' if c['slot_shortage_seconds']>0 else ('FIT_REVIEWED' if c['boundary_review_complete'] else 'CANDIDATE_FIT_REVIEW_REQUIRED')
        c['source_pcm_sha256']=digest(pcm[c['source_start_sample']*2:c['source_end_sample']*2])
        c['raw_asr_lot_variant_words']=[w for w in words[c.get('first_word_index',0):c.get('last_word_index',-1)+1] if any(x in w['word'] for x in ['로트','라트','락','LAT'])]
    coverage=sum(matches)/len(expected)
    lexical_pass=coverage>=.92 and all(c['character_coverage']>=.80 and 'word_start' in c for c in cuts)
    order_pass=all(a.get('last_word_index',10**9)<b.get('first_word_index',-1) for a,b in zip(cuts,cuts[1:]))
    boundary_pass=all(b['status'] in ['WORD_WAVE_SAFE','REVIEWED_CURRENT_TAKE'] for b in boundaries)
    fit_pass=all(c['slot_shortage_seconds']==0 for c in cuts)
    full=len(cuts)==68 and not args.prefix_lines
    ready=full and lexical_pass and order_pass and boundary_pass and fit_pass
    status='READY_FOR_REVIEWED_PCM_PLACEMENT' if ready else ('PARTIAL_PREFIX_ANALYSIS_ONLY' if args.prefix_lines else 'BLOCKED')
    report={'revision':10,'status':status,'analysis_only':True,'final_audio_written':False,'full_68_ready':ready,'scope':'Word timestamps are approximate. Waveform quiet inside a Korean word is not a sentence boundary. Candidates outside lexical gaps require explicit current-take review. No human-listening or pronunciation acceptance is claimed.','generation_mode':'single_take','new_take_received':True,'new_full_narration':ready,'ending_reuse_exception_authorized':False,'speech_tempo':1,'timeline_changed':False,'music_changed':False,'master':relative(args.master),'master_sha256':source_sha,'master_pcm_sha256':digest(pcm),'master_samples':total_samples,'master_seconds':total_samples/RATE,'asr':relative(args.asr),'asr_sha256':asr_sha,'config_sha256':digest(args.config.read_bytes()),'timeline_sha256':digest(args.timeline.read_bytes()),'fixed_slot_geometry_sha256':geometry(timeline),'sample_rate':RATE,'quiet_threshold_dbfs':args.quiet_dbfs,'rms_window_seconds':.01,'quiet_minimum_seconds':.08,'quiet_guards_seconds':.08,'expected_sentence_count':68,'analyzed_sentence_count':len(cuts),'lexically_anchored_sentence_count':sum(c['character_coverage']>=.80 for c in cuts),'boundary_count':len(boundaries),'exact_character_coverage':coverage,'edit_distance':distance,'edits':edits,'lexical_gate_pass':lexical_pass,'ordered_anchors_pass':order_pass,'all_boundaries_reviewed':boundary_pass,'all_slots_fit':fit_pass,'missing_or_low_coverage_cuts':[{'cut_id':c['id'],'coverage':c['character_coverage'],'asr_text':c.get('asr_text','')} for c in cuts if c['character_coverage']<.80],'cuts':cuts,'boundaries':boundaries,'quiet_regions':quiet,'words':words,'normalization':'Saved notation/number aliases, spacing and punctuation only. Rejected 로트 and raw 랏 variants remain distinct; ASR spelling is not pronunciation proof.'}
    report.update(source_metadata)
    if args.sources:
        report.update(master=None,master_sha256=None,master_pcm_sha256=None,asr=None,asr_sha256=None,new_full_narration=ready,source_input_bindings={relative(p):digest(p.read_bytes()) for p in args.source_input_paths})
    path=args.out/('fit-prefix%d.json'%args.prefix_lines if args.prefix_lines else 'fit-analysis.json'); save(path,report)
    return report,pcm,timeline,path

def loudness(path):
    result=subprocess.run(['ffmpeg','-hide_banner','-nostats','-i',str(path),'-af','loudnorm=I=-18.5:TP=-3.5:LRA=11:print_format=json','-f','null','-'],capture_output=True,text=True,check=True)
    match=re.findall(r'\{\s*"input_i".*?\}',result.stderr,re.S)
    assert match, 'FFmpeg loudness measurement was not returned.'
    return {k:float(v) for k,v in json.loads(match[-1]).items()}

def analyze_internal_pauses(args,report,pcm):
    """Capacity proposal only; never apply an intra-sentence audio edit.

    Executable candidates require both an ASR inter-word gap and the same
    source's sustained waveform quiet. A separate deliberately generous bound
    also counts quiet inside timestamped words: it is not an editing proposal,
    but can establish insufficiency even if ASR timing were later improved.
    """
    rate=RATE; guard=round(args.internal_guard_seconds*rate); minimum=round(args.internal_minimum_pause_seconds*rate)
    bypart={p['part_id']:p for p in report['source_parts']}; rows=[]
    for c in report['cuts']:
        need=math.ceil(max(0,c.get('protected_speech_shortage_seconds') or 0)*rate-1e-6)
        internal=[q for q in report['quiet_regions'] if q['start_sample']>=c['protected_speech_start_sample'] and q['end_sample']<=c['protected_speech_end_sample']]
        proposals={}
        for wi in range(c['first_word_index'],c['last_word_index']):
            left,right=report['words'][wi:wi+2]
            lexical_start=math.ceil(left['end']*rate); lexical_end=math.floor(right['start']*rate)
            for q in internal:
                a=max(q['start_sample']+guard,lexical_start)
                b=min(q['end_sample']-guard,lexical_end)
                capacity=max(0,min(b-a,q['end_sample']-q['start_sample']-minimum,lexical_end-lexical_start-minimum))
                if not capacity: continue
                key=(q['start_sample'],q['end_sample']); part=bypart[c['source_part_id']]
                candidate={'after_word_index':wi,'before_word_index':wi+1,'after_word':left,'before_word':right,'source_part_id':part['part_id'],'source_file':part['master'],'source_file_sha256':part['master_sha256'],'quiet':q,'source_local_quiet_start_sample':q['start_sample']-part['virtual_start_sample'],'source_local_quiet_end_sample':q['end_sample']-part['virtual_start_sample'],'safe_remove_virtual_window_samples':[a,b],'safe_remove_source_local_window_samples':[a-part['virtual_start_sample'],b-part['virtual_start_sample']],'lexical_gap_seconds':(lexical_end-lexical_start)/rate,'capacity_samples':capacity,'capacity_seconds':capacity/rate,'energy_guard_each_side_seconds':args.internal_guard_seconds,'minimum_retained_quiet_and_lexical_gap_seconds':args.internal_minimum_pause_seconds,'word_overlap_in_safe_remove_window':any(w['start']*rate<b and w['end']*rate>a for w in report['words']),'application_authorized':False}
                assert not candidate['word_overlap_in_safe_remove_window']
                if key not in proposals or capacity>proposals[key]['capacity_samples']: proposals[key]=candidate
        candidates=list(proposals.values()); strict=sum(p['capacity_samples'] for p in candidates)
        # This is an upper bound, not proof that a quiet region is outside a
        # Korean syllable. It intentionally ignores lexical restrictions.
        optimistic=sum(max(0,q['end_sample']-q['start_sample']-max(2*guard,round(.16*rate))) for q in internal)
        rows.append({'cut_id':c['id'],'source_part_id':c['source_part_id'],'source_file':c['source_file'],'source_file_sha256':c['source_file_sha256'],'fixed_slot_seconds':c['slot_seconds'],'protected_signal_span_seconds':c['protected_speech_seconds'],'signal_only_shortage_samples':need,'signal_only_shortage_seconds':need/rate,'preferred_80ms_guard_shortage_seconds':c['slot_shortage_seconds'],'strict_word_wave_capacity_samples':strict,'strict_word_wave_capacity_seconds':strict/rate,'strict_remaining_signal_shortage_seconds':max(0,need-strict)/rate,'strict_capacity_covers_signal_only_shortage':strict>=need,'strict_capacity_covers_preferred_guard_shortage':strict>=round(c['slot_shortage_seconds']*rate),'strict_candidates':candidates,'all_internal_wave_quiet_regions':internal,'optimistic_wave_only_capacity_with_160ms_pause_and_80ms_guards_seconds':optimistic/rate,'optimistic_remaining_signal_shortage_seconds':max(0,need-optimistic)/rate,'optimistic_bound_is_not_an_edit_plan':True})
    result={'revision':10,'status':'ANALYSIS_ONLY_NO_EDITS_APPLIED','source_identity_sha256':report['source_identity_sha256'],'source_parts':report['source_parts'],'alignment_report_sha256':digest((args.out/'fit-analysis.json').read_bytes()),'timeline_sha256':report['timeline_sha256'],'fixed_slot_geometry_sha256':report['fixed_slot_geometry_sha256'],'speech_tempo':1,'new_audio_written':False,'pause_edit_applied':False,'application_authorized':False,'waveform_threshold_dbfs':report['quiet_threshold_dbfs'],'waveform_rms_window_seconds':.01,'minimum_sustained_quiet_seconds':.08,'strict_energy_guard_each_side_seconds':args.internal_guard_seconds,'strict_minimum_retained_pause_seconds':args.internal_minimum_pause_seconds,'signal_overflow_cuts_analyzed':len(rows),'strict_candidate_count':sum(len(r['strict_candidates']) for r in rows),'strict_signal_fit_cuts':sum(r['strict_capacity_covers_signal_only_shortage'] for r in rows),'strict_nonfit_cut_ids':[r['cut_id'] for r in rows if not r['strict_capacity_covers_signal_only_shortage']],'optimistic_nonfit_cut_ids':[r['cut_id'] for r in rows if r['optimistic_remaining_signal_shortage_seconds']>0],'rows':rows,'limitations':['No ASR timestamp was overridden and no first-take timing was reused.','A low-energy interval inside a timestamped word is not an executable deletion candidate.','The generous wave-only bound is deliberately unsafe to execute; even it can show that quiet shortening cannot provide enough time under the stated pause/guard policy.','Signal span includes all original PCM between sentence-boundary quiet regions, including intentional in-sentence pauses. It is not a human phonetic label of every sample.','Root/independent review of any exact new edit map is required before application. No edit map or shortened WAV has been applied.']}
    save(args.out/'internal-pause-capacity.json',result)
    print(json.dumps({'internal_pause_analysis':'NOT_APPLIED','strict_candidate_count':result['strict_candidate_count'],'strict_signal_fit_cuts':result['strict_signal_fit_cuts'],'strict_nonfit_cut_ids':result['strict_nonfit_cut_ids'],'optimistic_nonfit_cut_ids':result['optimistic_nonfit_cut_ids']},ensure_ascii=False))
    return result

def verify_quiet_omissions(report,pcm):
    """Prove every omitted source sample lies in measured sentence quiet."""
    ranges=sorted((c['source_start_sample'],c['source_end_sample']) for c in report['cuts'])
    cursor=0; omitted=[]
    for a,b in ranges+[(len(pcm)//2,len(pcm)//2)]:
        assert cursor<=a<=b, 'Speech/source ranges overlap or are unordered.'
        if a>cursor:
            covering=[q for q in report['quiet_regions'] if q['start_sample']<=cursor and q['end_sample']>=a]
            assert covering, 'An omitted sample interval is not entirely inside verified quiet.'
            omitted.append({'virtual_start_sample':cursor,'virtual_end_sample':a,'samples':a-cursor,'pcm_sha256':digest(pcm[cursor*2:a*2]),'quiet':covering[0]})
        cursor=b
    return omitted

def raw_block_clips(report,pcm):
    """Keep 14 provenance WAVs whose ordered PCM exactly covers both sources."""
    records=[]; joined=b''
    sections=list(dict.fromkeys(c['section_id'] for c in report['cuts']))
    assert len(sections)==14
    for index,sid in enumerate(sections,1):
        cuts=[c for c in report['cuts'] if c['section_id']==sid]
        part=next(p for p in report['source_parts'] if p['part_id']==cuts[0]['source_part_id'])
        assert all(c['source_part_id']==part['part_id'] for c in cuts)
        before=next((b for b in report['boundaries'] if b['before_cut']==cuts[0]['id']),None)
        after=next((b for b in report['boundaries'] if b['after_cut']==cuts[-1]['id']),None)
        a=part['virtual_start_sample'] if before is None or before['between_source_parts'] else before['source_boundary_sample']
        b=part['virtual_end_sample'] if after is None or after['between_source_parts'] else after['source_boundary_sample']
        content=pcm[a*2:b*2]; path=ROOT/'narration/two-parts/raw-clips'/f'vo{index}.wav'
        if path.exists(): assert read_wav(path,1)[1]==content, 'Never overwrite different raw source clips.'
        else: write_wav(path,content,1)
        joined+=content
        records.append({'index':index,'section_id':sid,'source_part_id':part['part_id'],'source_file':part['master'],'source_file_sha256':part['master_sha256'],'source_local_start_sample':a-part['virtual_start_sample'],'source_local_end_sample':b-part['virtual_start_sample'],'path':relative(path),'sha256':digest(path.read_bytes()),'pcm_sha256':digest(content),'samples':b-a,'tempo':1,'raw_source_pcm_exact':True,'used_as_mix_restart':False})
    assert joined==pcm
    return records

def apply_authorized_retime(args):
    """Reconstruct only the approved pre-DSP PCM and visual timeline.

    This path reads the frozen analysis; it never recomputes or overwrites it.
    Pitch, gain, music padding and the final mix belong to the next stage.
    """
    import numpy as np
    assert args.raw_only, 'The approved-plan builder currently produces pre-DSP raw PCM only.'
    authorization=json.loads(args.retime_authorization.read_text())
    assert authorization['authorization_source']=='direct_user_reply_in_current_chat'
    assert authorization['approved_proposal_sha256']==AUTHORIZED_RETIME_PLAN_SHA256
    assert (authorization['duration_seconds'],authorization['frames'],authorization['fps'],authorization['final_silent_card_seconds'],authorization['speech_tempo'])==(315,9450,30,4,1)
    plan_path=rooted(authorization['approved_proposal']);review_path=rooted(authorization['independent_review'])
    assert digest(plan_path.read_bytes())==AUTHORIZED_RETIME_PLAN_SHA256
    plan=json.loads(plan_path.read_text());review=json.loads(review_path.read_text())
    assert review['status']=='PROPOSAL_INTERNALLY_FEASIBLE' and review['proposal_sha256']==AUTHORIZED_RETIME_PLAN_SHA256
    assert review['checks_passed']==11 and all(c['pass'] for c in review['checks'].values())
    config=json.loads(args.config.read_text());flat,parts,ordered_pcm,words,metadata=load_inputs(args,config)
    assert metadata['source_identity_sha256']==authorization['source_identity_sha256']==plan['source_identity_sha256']==review['source_identity_sha256']
    coverage=json.loads(args.coverage_review.read_text())
    assert coverage['status'].startswith('PASS') and coverage['sentences_complete']==68 and coverage['source_identity_sha256']==metadata['source_identity_sha256']
    expected_ids=[c['id'] for c in flat];spoken=[e for e in plan['entries'] if e['kind']=='cut']
    assert [e['cut_id'] for e in spoken]==expected_ids and len(plan['entries'])==69
    assert [e['caption'] for e in spoken]==[c['text'] for c in flat]
    assert (plan['duration'],plan['frames'],plan['fps'])==(315,9450,30)
    assert plan['entries'][-1]['kind']=='silent' and plan['entries'][-1]['end_frame']-plan['entries'][-1]['start_frame']==120
    baseline_hash=plan['input_bindings']['timeline.json']
    if args.baseline_timeline.exists():
        assert digest(args.baseline_timeline.read_bytes())==baseline_hash, 'Preserved Revision9 timeline changed.'
    else:
        assert digest(args.timeline.read_bytes())==baseline_hash, 'Cannot preserve a missing baseline from an already changed timeline.'
    for name,expected in plan['input_bindings'].items():
        if name!='timeline.json': assert digest(rooted(name).read_bytes())==expected, f'Approved-plan input changed: {name}'
    before={relative(rooted(p['master'])):p['master_sha256'] for p in parts}
    source={p['part_id']:read_wav(rooted(p['master']),1)[1] for p in parts};by_part={p['part_id']:p for p in parts}
    quiet_proofs=[]
    for edit in plan['internal_pause_edits']:
        part=by_part[edit['source_part_id']];a=edit['remove_source_local_start_sample'];b=edit['remove_source_local_end_sample'];q=edit['quiet'];offset=part['virtual_start_sample']
        assert b-a==edit['removed_samples'] and digest(source[part['part_id']][a*2:b*2])==edit['removed_pcm_sha256']
        assert a-(q['start_sample']-offset)>=3840 and q['end_sample']-offset-b>=3840
        assert q['end_sample']-q['start_sample']-(b-a)>=9600
        assert not any(w['source_part_id']==part['part_id'] and w['source_local_start']*RATE<b and w['source_local_end']*RATE>a for w in words)
        qa=q['start_sample']-offset;qb=q['end_sample']-offset
        samples=np.frombuffer(source[part['part_id']][qa*2:qb*2],dtype='<i2').astype(np.float64)/32768
        rms=np.sqrt(np.mean(samples[:len(samples)//480*480].reshape(-1,480)**2,axis=1));max_db=float(20*np.log10(max(1e-12,float(np.max(rms)))))
        assert max_db < -48
        quiet_proofs.append({'cut_id':edit['cut_id'],'source_part_id':part['part_id'],'source_local_start_sample':a,'source_local_end_sample':b,'removed_samples':b-a,'removed_pcm_sha256':edit['removed_pcm_sha256'],'maximum_10ms_rms_dbfs':max_db,'ASR_word_overlap':False,'guard_each_side_samples':3840,'retained_quiet_samples':q['end_sample']-q['start_sample']-(b-a)})
    assert len(quiet_proofs)==10 and sum(p['removed_samples'] for p in quiet_proofs)==127679
    pieces=[p for c in plan['placements'] for p in c['pieces']]+plan['audio_groups']
    pieces=sorted(pieces,key=lambda p:p['destination_start_sample']);assert len(pieces)==77
    raw=np.zeros(9450*1600,dtype='<i2');cursor=0;proofs=[]
    for piece in pieces:
        part=by_part[piece['source_part_id']]
        assert piece['source_file']==part['master'] and piece['source_file_sha256']==part['master_sha256']
        a,b=piece['source_local_start_sample'],piece['source_local_end_sample'];c,d=piece['destination_start_sample'],piece['destination_end_sample']
        assert 0<=a<b<=part['samples'] and cursor<=c<d<=311*RATE and b-a==d-c
        content=source[part['part_id']][a*2:b*2];assert digest(content)==piece['pcm_sha256']
        raw[c:d]=np.frombuffer(content,dtype='<i2');assert raw[c:d].tobytes()==content
        proofs.append({**piece,'retained_pcm_exact':True});cursor=d
    assert digest(raw.tobytes())==plan['proposed_raw_narration_pcm_sha256_not_written']
    assert not np.any(raw[311*RATE:])
    assert any(p['source_part_id']=='part1' and p['source_local_end_sample']==by_part['part1']['samples'] for p in pieces)
    assert any(p['source_part_id']=='part2' and p['source_local_start_sample']==0 for p in pieces)
    assert any(p['source_part_id']=='part2' and p['source_local_end_sample']==by_part['part2']['samples'] and p['destination_end_sample']==311*RATE for p in pieces)
    for index,placement in enumerate(plan['placements']):
        e=spoken[index]
        assert placement['cut_id']==e['cut_id']
        assert placement['speech_start_sample']-e['start_frame']*1600>=3840
        assert e['end_frame']*1600-placement['speech_end_sample']>=(0 if index==67 else 3840)
    for gap in plan['intersentence_pauses']: assert gap['proposed_seconds']+1e-8>=gap['minimum_seconds']
    group=plan['audio_groups'][0]
    assert group['cut_ids']==['ending_cut1','ending_cut2'] and group['audio_splices']==0 and group['internal_quiet_removed_samples']==0
    # Commit only after every original-source, authorization and virtual-PCM
    # assertion passes. The previous timeline is preserved byte for byte.
    if not args.baseline_timeline.exists():
        args.baseline_timeline.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(args.timeline,args.baseline_timeline)
    args.output.mkdir(parents=True,exist_ok=True);raw_path=args.output/'narration-raw.wav'
    write_wav(raw_path,raw.tobytes(),1)
    params,written=read_wav(raw_path,1);assert written==raw.tobytes() and params.nframes==15120000
    audio_segments=[{'file':p['source_file'],'source_part_id':p['source_part_id'],'source_local_start_sample':p['source_local_start_sample'],'source_local_end_sample':p['source_local_end_sample'],'source_local_start':p['source_local_start_sample']/RATE,'source_local_end':p['source_local_end_sample']/RATE,'timeline_start_sample':p['destination_start_sample'],'timeline_end_sample':p['destination_end_sample'],'timeline_start':p['destination_start_sample']/RATE,'timeline_end':p['destination_end_sample']/RATE,'pcm_sha256':p['pcm_sha256'],'tempo':1,'audio_group_id':p.get('audio_group_id')} for p in proofs]
    timeline={'revision':10,'preview_only':False,'allow_over_five_minutes':True,'fps':30,'frames':9450,'duration':315,'duration_seconds':315,'max_seconds':315,'tempo':1,'speech_tempo':1,'generation_mode':'two_part_with_user_authorization','two_part_exception_authorized':True,'retime_exception_authorized':True,'new_full_narration':True,'reused_ending':False,'source_identity_sha256':metadata['source_identity_sha256'],'source_parts':parts,'source_voice_seconds':len(ordered_pcm)/96000,'source_voice_samples':len(ordered_pcm)//2,'final_card_seconds':4,'fixed_silent_seconds':4,'additional_post_EOF_padding_seconds':0,'pitch_cents_authorized':authorization['pitch_cents'],'tone_processing_stage':'Downstream of exact pre-DSP source placement; no pitch DSP is applied by this builder.','retime_authorization':relative(args.retime_authorization),'retime_authorization_sha256':digest(args.retime_authorization.read_bytes()),'approved_plan':relative(plan_path),'approved_plan_sha256':AUTHORIZED_RETIME_PLAN_SHA256,'independent_retime_review':relative(review_path),'independent_retime_review_sha256':digest(review_path.read_bytes()),'baseline_timeline':relative(args.baseline_timeline),'baseline_timeline_sha256':baseline_hash,'entries':plan['entries'],'sections':plan['sections'],'audio_segments':audio_segments,'raw_narration':'../out/showcase-v10/narration-raw.wav','raw_placement_manifest':'narration/placement-manifest.json','timing_basis':'Exact user-approved 315-second plan: all68 new source phrases at tempo1, ten verified internal quiet removals, original continuous ending pair, complete source1 EOF/source2 head and EOF, with the final four-second silent narration card.'}
    save(args.timeline,timeline)
    assert geometry(timeline)==geometry({'entries':plan['entries']})
    assert before=={relative(rooted(p['master'])):digest(rooted(p['master']).read_bytes()) for p in parts}
    inputs=[*args.source_input_paths,args.config,args.timeline,args.baseline_timeline,args.retime_authorization,plan_path,review_path,args.coverage_review,Path(__file__).resolve()]
    inputs.extend(rooted(p) for p in plan['input_bindings'] if p!='timeline.json')
    bindings={relative(p):digest(p.read_bytes()) for p in dict.fromkeys(inputs)}
    report={'revision':10,'status':'PASS_RAW_PCM_PLACEMENT','scope':'Approved pre-DSP raw narration and actual visual timeline only. Pitch correction, common gain, music and final mix are pending a separate stage.','source_identity_sha256':metadata['source_identity_sha256'],'generation_mode':'two_part_with_user_authorization','two_part_exception_authorized':True,'retime_exception_authorized':True,'tone_correction_authorized':True,'pitch_cents_authorized':authorization['pitch_cents'],'pitch_processing_applied':False,'gain_processing_applied':False,'music_mixed':False,'final_mix_complete':False,'new_full_narration':True,'reused_ending':False,'speech_tempo':1,'spoken_samples_removed':0,'source_full_files_preserved':True,'all77_retained_pieces_PCM_exact':True,'source_parts':parts,'approved_plan':relative(plan_path),'approved_plan_sha256':AUTHORIZED_RETIME_PLAN_SHA256,'retime_authorization':relative(args.retime_authorization),'retime_authorization_sha256':digest(args.retime_authorization.read_bytes()),'independent_retime_review':relative(review_path),'independent_retime_review_sha256':digest(review_path.read_bytes()),'completeness_review':relative(args.coverage_review),'completeness_review_sha256':digest(args.coverage_review.read_bytes()),'baseline_timeline':relative(args.baseline_timeline),'baseline_timeline_sha256':baseline_hash,'timeline':relative(args.timeline),'timeline_sha256':digest(args.timeline.read_bytes()),'timeline_geometry_sha256':geometry(timeline),'duration':315,'duration_seconds':315,'sample_rate':RATE,'channels':1,'sample_width':2,'samples':15120000,'frames':9450,'spoken_cut_count':68,'visual_entry_count':69,'section_count':14,'final_silent_card_seconds':4,'final_card_narration_PCM_all_zero':True,'raw_output':{'path':'narration-raw.wav','path_basis':'selected_output_directory','sha256':digest(raw_path.read_bytes()),'pcm_sha256':digest(written)},'expected_raw_PCM_matches_approved_proposal':True,'piece_count':77,'pieces':proofs,'cuts':plan['placements'],'audio_groups':plan['audio_groups'],'internal_quiet_edits':quiet_proofs,'internal_quiet_removed_samples':127679,'internal_quiet_removed_seconds':127679/RATE,'all_source_PCM_once_in_mix_claimed':False,'note':'Source files remain unmodified. Excess sentence quiet is omitted and ten approved word-safe internal quiet intervals are removed; retained speech PCM is exact before downstream tone/gain processing. ASR spelling and subjective tone acceptance are separate from this sample proof.','input_bindings':bindings}
    save(ROOT/'narration/placement-manifest.json',report);save(args.output/'raw-placement-validation.json',report)
    print(json.dumps({'status':report['status'],'duration':315,'frames':9450,'pieces':77,'raw_pcm_sha256':digest(written),'raw_file_sha256':digest(raw_path.read_bytes()),'timeline_sha256':report['timeline_sha256'],'raw_output':str(raw_path),'final_mix_complete':False},ensure_ascii=False))

def render(args,report,pcm,timeline,analysis_path):
    import numpy as np
    assert report['full_68_ready'], 'Final audio blocked: incomplete lexical anchors, unresolved boundaries or a fixed-slot overflow. Review fit-analysis.json.'
    # Completeness and pronunciation are independent gates, not an inference
    # from a matching generation prompt or high average ASR coverage.
    assert args.coverage_review.exists(), 'Independent current-take 68-line review is required.'
    independent=json.loads(args.coverage_review.read_text())
    assert independent.get('status','').startswith('PASS')
    if args.sources:
        assert independent.get('source_identity_sha256')==report['source_identity_sha256']
    else:
        assert independent.get('master_sha256')==report['master_sha256'] and independent.get('asr_sha256')==report['asr_sha256']
    assert independent.get('sentences_complete')==68
    assert report['generation_mode']=='two_part_with_user_authorization', 'The rejected incomplete diagnostic take cannot be adopted.'
    omitted=verify_quiet_omissions(report,pcm)
    music_params,music_pcm=read_wav(args.music,2)
    assert digest(args.music.read_bytes())==MUSIC_FILE_SHA256 and digest(music_pcm)==MUSIC_PCM_SHA256
    total=timeline['frames']*1600; assert music_params.nframes==total
    placed=np.zeros(total,dtype='<i2'); source=np.frombuffer(pcm,dtype='<i2'); proofs=[]
    for c in report['cuts']:
        a,b=c['source_start_sample'],c['source_end_sample']; dest=c['slot_start_sample']; content=source[a:b]
        assert dest+len(content)<=c['slot_end_sample']
        placed[dest:dest+len(content)]=content
        assert placed[dest:dest+len(content)].tobytes()==pcm[a*2:b*2]
        source_file=rooted(c['source_file']); source_bytes=read_wav(source_file,1)[1]
        assert source_bytes[c['source_local_start_sample']*2:c['source_local_end_sample']*2]==content.tobytes()
        proofs.append({'cut_id':c['id'],'source_part_id':c['source_part_id'],'source_file':c['source_file'],'source_file_sha256':c['source_file_sha256'],'source_local_start_sample':c['source_local_start_sample'],'source_local_end_sample':c['source_local_end_sample'],'source_start_sample':a,'source_end_sample':b,'source_sample_clock':'source_start/end_sample are virtual ordered-source coordinates; source_local_start/end_sample address the named source WAV.','destination_start_sample':dest,'destination_end_sample':dest+b-a,'pcm_sha256':digest(content.tobytes()),'retained_pcm_exact':True,'slot_end_sample':c['slot_end_sample'],'trailing_slot_silence_samples':c['slot_end_sample']-dest-(b-a)})
    args.output.mkdir(parents=True,exist_ok=True)
    raw_path=args.output/'narration-raw.wav'; voice_path=args.output/'narration.wav'; music_path=args.output/'bgm-loop.wav'; mix_path=args.output/'audio.wav'
    write_wav(raw_path,placed.tobytes(),1)
    measured=loudness(raw_path)
    gain_db=min(args.voice_lufs-measured['input_i'],args.voice_true_peak-measured['input_tp'])
    scaled=np.rint(placed.astype(np.float64)*10**(gain_db/20))
    assert max(abs(scaled.min()),abs(scaled.max()))<32767, 'Global voice gain would clip; no limiter was silently applied.'
    voice=scaled.astype('<i2'); write_wav(voice_path,voice.tobytes(),1)
    shutil.copyfile(args.music,music_path)
    music=np.frombuffer(music_pcm,dtype='<i2').reshape(-1,2).astype(np.int32)
    mixed=music+voice.astype(np.int32)[:,None]
    clipped=int(np.sum((mixed>32767)|(mixed<-32768)))
    assert clipped==0, 'Fixed BGM + voice clips. Lower the one global voice gain explicitly; do not change music or limit the mix.'
    write_wav(mix_path,mixed.astype('<i2').tobytes(),2)
    raw_bytes=placed.tobytes(); speech_end=timeline['entries'][-1]['start_frame']*1600
    assert not np.any(placed[speech_end:]), 'Narration intrudes into the fixed final card.'
    assert all(digest(rooted(part['master']).read_bytes())==part['master_sha256'] for part in report['source_parts'])
    assert digest(args.timeline.read_bytes())==report['timeline_sha256']
    outputs={p.name:{'path':p.name,'path_basis':'relative_to_selected_output_directory','sha256':digest(p.read_bytes()),'pcm_sha256':digest(read_wav(p)[1]),'samples':read_wav(p)[0].nframes} for p in [raw_path,voice_path,music_path,mix_path]}
    report_out={'revision':10,'status':'PASS','sample_rate':RATE,'channels':2,'duration':total/RATE,'duration_seconds':total/RATE,'samples':total,'frames':timeline['frames'],'generation_mode':report['generation_mode'],'two_part_exception_authorized':True,'source_identity_sha256':report['source_identity_sha256'],'source_parts':report['source_parts'],'authorization':report['authorization'],'new_full_narration':True,'reused_ending':False,'speech_tempo':1,'word_or_syllable_samples_removed':0,'spoken_samples_removed':0,'non_speech_samples_removed':sum(r['samples'] for r in omitted),'omitted_quiet_intervals':omitted,'source_full_files_preserved':True,'all_retained_speech_pcm_exact':True,'timeline_changed':False,'fixed_slot_geometry_sha256':geometry(timeline),'fixed_music_file_sha256':MUSIC_FILE_SHA256,'fixed_music_pcm_sha256':MUSIC_PCM_SHA256,'music_pcm_byte_exact':True,'music_gain_fade_duck_or_loop_changed':False,'global_voice_gain_db':gain_db,'per_cut_voice_gain_applied':False,'per_part_voice_gain_applied':False,'voice_loudness_measurement_before_global_gain':measured,'voice_loudness_measurement_after_global_gain':loudness(voice_path),'mix_peak_dbfs':20*math.log10(max(1,np.max(np.abs(mixed)))/32768),'mix_clipped_samples':clipped,'mix_limiter_applied':False,'final_card_narration_silent':True,'input_bindings':{relative(p):digest(p.read_bytes()) for p in [*args.source_input_paths,args.config,args.timeline,args.music,args.coverage_review,analysis_path,Path(__file__).resolve(),ROOT/'audio.py']},'outputs':outputs,'cuts':proofs,'raw_block_clips':raw_block_clips(report,pcm),'source_phrase_placement':'Each reviewed speech span, including waveform tails and quiet guards, is copied at tempo1 from its untouched named source into its own immutable visual slot. Only verified inter-sentence quiet is omitted; slot remainder is zero PCM. Single-take or continuous-source playback is not claimed.'}
    save(args.output/'audio-validation.json',report_out)
    save(ROOT/'narration/placement-manifest.json',report_out)
    print(json.dumps({'status':'PASS','duration':total/RATE,'music_pcm_exact':True,'global_voice_gain_db':gain_db,'output':str(mix_path)},ensure_ascii=False))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,default=ROOT/'narration/ko.json'); p.add_argument('--timeline',type=Path,default=ROOT/'timeline.json')
    p.add_argument('--master',type=Path,default=ROOT/'narration/elevenlabs/take.wav'); p.add_argument('--asr',type=Path,default=ROOT/'narration/transcription/take.json')
    p.add_argument('--sources',type=Path,help='SHA-bound authorized two-part descriptor; automatically selected when narration/two-part-sources.json exists.')
    p.add_argument('--reviews',type=Path,default=ROOT/'narration/two-parts/boundary-reviews.json')
    p.add_argument('--coverage-review',type=Path,default=ROOT/'narration/two-parts/completeness-review.json')
    p.add_argument('--music',type=Path,default=ROOT/'assets/bgm/revision9-approved-music.wav')
    p.add_argument('--out',type=Path,default=ROOT/'narration/placement'); p.add_argument('--output',type=Path,default=ROOT.parent/'out/showcase-v10')
    p.add_argument('--quiet-dbfs',type=float,default=-48); p.add_argument('--prefix-lines',type=int,choices=[64])
    p.add_argument('--voice-lufs',type=float,default=-18.5); p.add_argument('--voice-true-peak',type=float,default=-3.5)
    p.add_argument('--analyze-internal-pauses',action='store_true',help='Write a word/waveform internal-pause capacity proposal only; never apply audio edits.')
    p.add_argument('--internal-guard-seconds',type=float,default=.08); p.add_argument('--internal-minimum-pause-seconds',type=float,default=.20)
    p.add_argument('--render',action='store_true',help='Write audio only after every full-68 lexical, boundary, fit and independent review gate passes.')
    p.add_argument('--apply-approved-plan',action='store_true',help='Apply only the exact independently reviewed and user-authorized315-second plan; never rerun frozen fixed-slot analysis.')
    p.add_argument('--raw-only',action='store_true',help='Produce only exact pre-DSP narration-raw.wav and the authorized timeline.')
    p.add_argument('--retime-authorization',type=Path,default=ROOT/'narration/retime-tone-authorization.json')
    p.add_argument('--baseline-timeline',type=Path,default=ROOT/'baseline/timeline-revision9.json')
    args=p.parse_args()
    assert args.internal_guard_seconds>=.08 and args.internal_minimum_pause_seconds>=.16, 'Internal-pause analysis must retain at least 80ms energy guards and 160ms pause.'
    if args.sources is None and not args.prefix_lines and (ROOT/'narration/two-part-sources.json').exists(): args.sources=ROOT/'narration/two-part-sources.json'
    if args.apply_approved_plan:
        assert not args.render and not args.analyze_internal_pauses and not args.prefix_lines
        apply_authorized_retime(args);return
    report,pcm,timeline,path=analyze(args)
    print(json.dumps({'status':report['status'],'analyzed_sentences':report['analyzed_sentence_count'],'coverage':report['exact_character_coverage'],'safe_boundaries':sum(b['status'] in ['WORD_WAVE_SAFE','REVIEWED_CURRENT_TAKE'] for b in report['boundaries']),'boundary_review_required':sum(b['status'] not in ['WORD_WAVE_SAFE','REVIEWED_CURRENT_TAKE'] for b in report['boundaries']),'slot_overflows':[{'cut_id':c['id'],'shortage_seconds':c['slot_shortage_seconds'],'protected_speech_shortage_seconds':c['protected_speech_shortage_seconds'],'available_quiet_guard_seconds':c['available_total_quiet_guard_seconds']} for c in report['cuts'] if (c['slot_shortage_seconds'] or 0)>0],'report':str(path)},ensure_ascii=False))
    if args.analyze_internal_pauses:
        assert not args.render, 'Internal-pause capacity is analysis only; this command cannot apply a proposal.'
        analyze_internal_pauses(args,report,pcm)
    if args.render:
        assert not args.prefix_lines, 'A partial-prefix analysis cannot produce final audio.'
        render(args,report,pcm,timeline,path)

if __name__=='__main__': main()
