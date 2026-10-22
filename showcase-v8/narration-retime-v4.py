#!/usr/bin/env python3
"""Slow the approved complete take to use the 24 seconds released by summaries.

This creates one continuous atempo render and partitions it only at genuine
paragraph pauses. The 73 internal landmarks are visual metadata, not audio
restarts. No TTS, script edit, original asset overwrite, or cascading speed processing occurs. The sole tempo change is user approved.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, math, subprocess, sys, wave, tempfile
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parent
SR=48000

def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()

def digest(b):return hashlib.sha256(b).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def save(p,x):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def wav(p):
    with wave.open(str(p),'rb') as f:
        if (f.getframerate(),f.getnchannels(),f.getsampwidth())!=(SR,1,2):raise ValueError('Expected 48k mono s16 PCM')
        return f.readframes(f.getnframes())
def writewav(p,b):
    Path(p).parent.mkdir(parents=True,exist_ok=True)
    with wave.open(str(p),'wb') as f:
        f.setframerate(SR);f.setnchannels(1);f.setsampwidth(2);f.writeframes(b)
def run(args):
    r=subprocess.run(args,capture_output=True,text=True)
    if r.returncode:raise RuntimeError('Command failed: '+str(args)+'\n'+r.stderr[-4000:])
    return r

def quiet_regions(pcm,threshold=-45.,minimum=.10):
    v=np.frombuffer(pcm,dtype='<i2').astype(np.float64)/32768
    window=480;hop=48
    n=np.arange(0,len(v)-window+1,hop)
    cumulative=np.r_[0.,np.cumsum(v*v)]
    energy=(cumulative[n+window]-cumulative[n])/window
    db=10*np.log10(np.maximum(energy,1e-12))
    low=db<threshold
    transitions=np.diff(np.r_[False,low,False].astype(np.int8))
    starts=np.where(transitions==1)[0];ends=np.where(transitions==-1)[0]
    regions=[]
    for a,b in zip(starts,ends):
        start=int(n[a]);end=int(n[b-1]+window)
        if (end-start)/SR>=minimum:
            regions.append({'start_sample':start,'end_sample':end,'start':start/SR,'end':end/SR,'duration':(end-start)/SR,'peak_rms_dbfs':float(np.max(db[a:b]))})
    return regions

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--master',type=Path,default=ROOT/'narration/take.wav')
    ap.add_argument('--config',type=Path,default=ROOT/'narration/ko.json')
    ap.add_argument('--legacy-timeline',type=Path,default=ROOT/'baseline/timeline.json')
    ap.add_argument('--legacy-alignment',type=Path,default=ROOT/'baseline/narration/alignment-report.json')
    ap.add_argument('--whisper',default='/opt/homebrew/bin/whisper')
    ap.add_argument('--asr',type=Path)
    ap.add_argument('--reuse-processed',action='store_true')
    ap.add_argument('--prepare-only',action='store_true')
    args=ap.parse_args()
    config=read(args.config);old=read(args.legacy_timeline);legacy=read(args.legacy_alignment)
    source_hash=sha(args.master);config_hash=sha(args.config);source_pcm=wav(args.master)
    processed=ROOT/'narration/processed-continuous-v4.wav'
    provenance=ROOT/'narration/processed-continuous-v4-provenance.json'
    baseline_map=read(ROOT/'baseline-v3/narration/speech-edit-map.json')
    old_tempo=float(baseline_map['tempo_ratio'])
    old_count=baseline_map['processed_continuous']['sample_count']
    target_count=old_count+24*SR
    nominal_tempo=old_tempo*old_count/target_count
    if args.reuse_processed:
        proof=read(provenance)
        assert proof['source_master_sha256']==source_hash and sha(processed)==proof['processed_sha256']
        assert proof['target_samples']==target_count
    else:
        # Each duration-search candidate starts directly at the unchanged source;
        # the selected audio has one WSOLA pass, never a chain of speed changes.
        temp=Path(tempfile.mkdtemp(prefix='media-maker-v4-tempo-solve-',dir='/tmp'))
        trials=[]
        def candidate(factor):
            factor=float(f'{factor:.13f}')
            file=temp/f'{len(trials):02d}.wav'
            run(['ffmpeg','-y','-v','error','-i',str(args.master),'-af',f'atempo={factor:.13f}','-ar',str(SR),'-ac','1','-c:a','pcm_s16le',str(file)])
            data=wav(file);n=len(data)//2
            row={'factor':factor,'samples':n,'target_delta_samples':n-target_count,'path':str(file)}
            trials.append(row);return row
        low=nominal_tempo-.0005;high=nominal_tempo+.0005
        left=candidate(low);right=candidate(high)
        assert left['samples']>=target_count>=right['samples']
        for _ in range(18):
            mid=candidate((low+high)/2)
            if mid['samples']>target_count:low=mid['factor']
            else:high=mid['factor']
        selected=min((r for r in trials if r['samples']<=target_count),key=lambda r:target_count-r['samples'])
        rendered=wav(selected['path']);pad=target_count-selected['samples']
        assert 0<=pad<=240,('Only <=5ms verified tail silence may be added',pad)
        # Appending zeros retains every sample of the selected WSOLA result.
        writewav(processed,rendered+b'\0\0'*pad)
        proof={'source_master':'narration/take.wav','source_master_sha256':source_hash,'source_pcm_sha256':digest(source_pcm),'previous_tempo_ratio':old_tempo,'nominal_requested_tempo':nominal_tempo,'tempo_ratio':selected['factor'],'effective_ffmpeg_tempo':selected['factor'],'atempo_filter':f"atempo={selected['factor']:.13f}",'previous_processed_samples':old_count,'target_samples':target_count,'target_voice_extension_seconds':24,'selected_rendered_samples':selected['samples'],'tail_zero_padding_samples':pad,'no_processed_samples_removed':True,'selected_audio_continuous_processing_passes':1,'duration_search_candidates_all_direct_from_original_source':trials,'processed':'narration/processed-continuous-v4.wav','processed_sha256':sha(processed),'processing':'one whole continuous original take at the approved slower factor, with only <=5ms zero tail padding for exact duration','new_tts':False,'pitch_preserving_filter':'ffmpeg atempo / WSOLA','speed_ratio_vs_previous':selected['factor']/old_tempo}
        save(provenance,proof)
    tempo=proof['tempo_ratio'];filter_value=f'{tempo:.13f}'
    if args.prepare_only:
        print(json.dumps({'status':'PREPARED','tempo':tempo,'previous_tempo':old_tempo,'target_samples':target_count,'processed':str(processed),'tail_zero_padding_samples':proof['tail_zero_padding_samples']},ensure_ascii=False),flush=True)
        return 0
    pcm=wav(processed);count=len(pcm)//2
    asr_dir=ROOT/'narration/retimed-asr-v4';asr_dir.mkdir(parents=True,exist_ok=True)
    asr=args.asr or asr_dir/'processed-continuous-v4.json'
    if not args.asr:
        print('Local Whisper small/CPU word timestamps for complete processed master',flush=True)
        run([args.whisper,str(processed),'--language','ko','--task','transcribe','--word_timestamps','True','--output_format','json','--output_dir',str(asr_dir),'--verbose','False'])
    modspec=importlib.util.spec_from_file_location('read_only_alignment_helpers',ROOT/'align.py');helpers=importlib.util.module_from_spec(modspec);modspec.loader.exec_module(helpers)
    words=helpers.whisper_words(read(asr));pronunciation=config.get('pronunciation_map',{})
    cut_rows=[];expected=''
    for block in config['blocks']:
        for cut in block['cuts']:
            norm,_=helpers.normalize(cut.get('spoken_text',cut['text']),pronunciation)
            cut_rows.append({'cut_id':cut['id'],'section_id':block['section_id'],'caption':cut['text'],'spoken_text':cut['spoken_text'],'normalized':norm,'char_start':len(expected),'char_end':len(expected)+len(norm)})
            expected+=norm
    raw='';owners=[]
    for i,w in enumerate(words):raw+=w['word'];owners.extend([i]*len(w['word']))
    actual,char_word=helpers.normalize(raw,pronunciation,owners)
    mapping,matches,edits,distance=helpers.edit_align(expected,actual)
    old_cuts={c['id']:c for c in legacy['cuts']}
    for cut in cut_rows:
        indices=[mapping[i] for i in range(cut['char_start'],cut['char_end']) if mapping[i] is not None]
        if not indices:raise AssertionError('No timestamped words for '+cut['cut_id'])
        first,last=char_word[min(indices)],char_word[max(indices)]
        cut.update({'first_word_index':first,'last_word_index':last,'word_timing':{'first':words[first],'last':words[last]},'asr_word_start':words[first]['start'],'asr_word_end':words[last]['end'],'asr_text':' '.join(w['word'].strip() for w in words[first:last+1]),'character_coverage':sum(matches[cut['char_start']:cut['char_end']])/len(cut['normalized']),'legacy_nominal_word_end':old_cuts[cut['cut_id']]['word_end']/tempo})
    quiet=quiet_regions(pcm);short_quiet=quiet_regions(pcm,minimum=.012);boundaries=[];unresolved=[]
    reviewed_continuous={'task3_cut1','task4_cut1','task9_cut4'}
    for i,cut in enumerate(cut_rows[:-1]):
        nxt=cut_rows[i+1];paragraph=cut['section_id']!=nxt['section_id'];anchor=cut['legacy_nominal_word_end']
        # Word timestamps are only lexical anchors. Never use a zero-width
        # ASR gap or a short Korean consonant gap as a valid cut by itself.
        lower=anchor-.18;upper=anchor+.62
        next_last=words[nxt['first_word_index']]['end']
        candidates=[q for q in quiet if q['duration']>=(.14 if paragraph else .10) and lower<=q['start']<=upper and q['end']<=next_last+.06]
        if not candidates:
            if not paragraph and cut['cut_id'] in reviewed_continuous:
                # Reviewed lexical end + a waveform valley *after* that word,
                # not a fabricated long pause. Audio remains uninterrupted.
                lexical_end=max(anchor,cut['asr_word_end'])
                short=[q for q in short_quiet if lexical_end<=q['start']<=lexical_end+.24 and q['end']<=next_last+.04]
                if short:
                    q=min(short,key=lambda q:q['start'])
                    point=(q['start_sample']+q['end_sample'])//2
                    row={'after_cut':cut['cut_id'],'before_cut':nxt['cut_id'],'paragraph':False,'anchor':anchor,'asr_end':cut['asr_word_end'],'safe_boundary_sample':int(point),'safe_boundary_seconds':point/SR,'actual_speech_end_sample':q['start_sample'],'next_actual_speech_start_sample':min(q['end_sample'],round(nxt['asr_word_start']*SR)),'waveform_next_onset_sample':q['end_sample'],'quiet_boundary':q,'post_speech_guard_seconds':(point-q['start_sample'])/SR,'confidence':'REVIEWED_CONTINUOUS_SPEECH_VISUAL_ONLY','audio_split':False,'inserted_pause':False,'next_lexical_asr_start':nxt['asr_word_start'],'asr_start_overlap_seconds':max(0,point/SR-nxt['asr_word_start']),'evidence':'Fresh processed-master lexical end and the first subsequent short waveform valley; internal visual change only. Next ASR word may include the preceding phonetic transition, so its earliest timestamp is retained conservatively.','asr_boundary_disagreement_seconds':q['start']-cut['asr_word_end']}
                    boundaries.append(row);continue
            row={'after_cut':cut['cut_id'],'before_cut':nxt['cut_id'],'paragraph':paragraph,'confidence':'UNRESOLVED_NO_TRUE_PAUSE','anchor':anchor,'asr_end':cut['asr_word_end'],'next_asr_start':nxt['asr_word_start'],'safe_boundary_sample':None}
            unresolved.append(row);boundaries.append(row);continue
        q=min(candidates,key=lambda q:abs((q['start']+min(.08,q['duration']/2))-anchor))
        point=q['start_sample']+min(round(.08*SR),(q['end_sample']-q['start_sample'])//2)
        row={'after_cut':cut['cut_id'],'before_cut':nxt['cut_id'],'paragraph':paragraph,'anchor':anchor,'asr_end':cut['asr_word_end'],'safe_boundary_sample':int(point),'safe_boundary_seconds':point/SR,'actual_speech_end_sample':q['start_sample'],'next_actual_speech_start_sample':q['end_sample'],'quiet_boundary':q,'post_speech_guard_seconds':(point-q['start_sample'])/SR,'confidence':'GENUINE_PARAGRAPH_PAUSE' if paragraph else 'GENUINE_PHRASE_PAUSE','asr_boundary_disagreement_seconds':q['start']-cut['asr_word_end']}
        boundaries.append(row)
    if unresolved:
        save(ROOT/'narration/speech-edit-map-v4.json',{'status':'BLOCKED_UNRESOLVED_BOUNDARIES','source_master_sha256':source_hash,'tempo_ratio':tempo,'processed_continuous':{'path':str(processed),'sha256':sha(processed),'pcm_sha256':digest(pcm),'sample_count':count},'asr':str(asr),'asr_sha256':sha(asr),'exact_character_coverage':sum(matches)/len(expected),'cuts':cut_rows,'boundaries':boundaries,'unresolved':unresolved})
        print(json.dumps({'status':'BLOCKED_UNRESOLVED_BOUNDARIES','count':len(unresolved),'ids':[r['after_cut'] for r in unresolved]},ensure_ascii=False),flush=True)
        return 2
    points=[0]+[b['safe_boundary_sample'] for b in boundaries]+[count]
    if any(a>=b for a,b in zip(points,points[1:])):raise AssertionError('Safe boundaries are not strictly increasing')
    first_speech=quiet[0]['end_sample'] if quiet and quiet[0]['start_sample']==0 else 0
    last_anchor=cut_rows[-1]['legacy_nominal_word_end']
    last_quiet=[q for q in quiet if last_anchor-.18<=q['start']<=last_anchor+.5 and q['end_sample']>=count-1000]
    last_speech_end=last_quiet[0]['start_sample'] if last_quiet else count
    for i,cut in enumerate(cut_rows):
        a,b=points[i],points[i+1]
        speech_start=first_speech if i==0 else boundaries[i-1]['next_actual_speech_start_sample']
        speech_end=last_speech_end if i==len(cut_rows)-1 else boundaries[i]['actual_speech_end_sample']
        cut.update({'processed_start_sample':a,'processed_end_sample':b,'actual_speech_start_sample':speech_start,'actual_speech_end_sample':speech_end,'safe_boundary_sample':b,'safe_boundary_seconds':b/SR,'source_start_sample_estimate':min(len(source_pcm)//2,round(a*tempo)),'source_end_sample_estimate':min(len(source_pcm)//2,round(b*tempo)),'source_sample_mapping_basis':'nominal fixed-tempo coordinate estimate; exact retained PCM coordinates are processed samples','quiet_boundary':boundaries[i]['quiet_boundary'] if i<len(boundaries) else (last_quiet[0] if last_quiet else None),'confidence':boundaries[i]['confidence'] if i<len(boundaries) else 'FINAL_TAKE_TAIL','pcm_span_sha256':digest(pcm[a*2:b*2]),'speech_start_seconds':speech_start/SR,'speech_end_seconds':speech_end/SR,'safe_end_guard_seconds':(b-speech_end)/SR})
        cut['continuous_start_overlap']=i>0 and boundaries[i-1]['confidence']=='REVIEWED_CONTINUOUS_SPEECH_VISUAL_ONLY'
        cut['speech_start_method']='conservative fresh-ASR lexical start; short waveform next onset recorded at prior boundary' if cut['continuous_start_overlap'] else 'sustained quiet endpoint / following phonetic onset'
    sections=[];recombined=bytearray()
    for i,block in enumerate(config['blocks'],1):
        rows=[c for c in cut_rows if c['section_id']==block['section_id']];a=rows[0]['processed_start_sample'];b=rows[-1]['processed_end_sample'];chunk=pcm[a*2:b*2]
        file=ROOT/'narration/retimed-sections-v4'/f'{i:02d}-{block["section_id"]}.wav';writewav(file,chunk);recombined.extend(wav(file))
        sections.append({'section_id':block['section_id'],'pcm_file':str(file),'start_sample':a,'end_sample':b,'duration_seconds':(b-a)/SR,'actual_speech_start_sample':rows[0]['actual_speech_start_sample'],'actual_speech_end_sample':rows[-1]['actual_speech_end_sample'],'pcm_sha256':digest(chunk),'file_sha256':sha(file),'cut_ids':[r['cut_id'] for r in rows],'paragraph_head_quiet_seconds':(rows[0]['actual_speech_start_sample']-a)/SR,'paragraph_tail_quiet_seconds':(b-rows[-1]['actual_speech_end_sample'])/SR})
    if bytes(recombined)!=pcm:raise AssertionError('Section PCM reassembly differs from complete processed master')
    if sha(args.master)!=source_hash or sha(args.config)!=config_hash:raise AssertionError('Source take or narration config changed during retiming')
    report={'status':'PASS_WITH_ASR_VARIANTS' if sum(matches)/len(expected)<1 else 'PASS','sample_rate':SR,'channels':1,'sample_width':2,'tempo_ratio':tempo,'effective_ffmpeg_tempo':float(filter_value),'source_master':{'path':str(args.master),'sha256':source_hash,'pcm_sha256':digest(source_pcm),'unchanged':True},'source_config_sha256':config_hash,'new_tts':False,'voice_id':config['voice_id'],'voice_name':config['voice_name'],'model_id':config['model_id'],'script_unchanged':True,'processed_continuous':{'path':str(processed),'sha256':sha(processed),'pcm_sha256':digest(pcm),'sample_count':count,'duration_seconds':count/SR,'continuous_processing_passes':1},'asr':{'path':str(asr),'sha256':sha(asr),'model':'local Whisper small CPU','exact_character_coverage':sum(matches)/len(expected),'edit_distance':distance,'edits':edits},'cuts':cut_rows,'sections':sections,'boundaries':boundaries,'verification':{'spoken_cut_count':len(cut_rows),'continuous_section_count':len(sections),'all_73_words_anchored':len(cut_rows)==73,'all_14_sections_complete':len(sections)==14,'all_paragraph_points_in_genuine_pauses':all(b['quiet_boundary']['duration']>=.14 for b in boundaries if b['paragraph']),'continuous_visual_only_exception_count':sum(b['confidence']=='REVIEWED_CONTINUOUS_SPEECH_VISUAL_ONLY' for b in boundaries),'all_internal_points_genuine_pause_or_reviewed_visual_only':all(b['quiet_boundary']['duration']>=.10 or b['confidence']=='REVIEWED_CONTINUOUS_SPEECH_VISUAL_ONLY' for b in boundaries if not b['paragraph']),'all_visual_boundaries_after_actual_speech_end':all(c['safe_boundary_sample']>=c['actual_speech_end_sample'] for c in cut_rows),'section_pcm_reassembly_matches_continuous_master':True,'reassembly_pcm_sha256':digest(recombined),'no_processed_samples_removed':True,'no_audio_restarts_at_internal_visual_cuts':True,'source_voice_script_preserved_and_approved_tempo_applied':True},'notes':['All samples of the continuous processed take are retained exactly once across fourteen paragraph WAVs.','Internal narration cut points are visual landmarks only. Do not restart the audio or add pauses at task-internal boundaries.','The original single take restores final syllables previously discarded by section clipping or assigned to the next section.','Waveform endpoints are conservative sustained-quiet estimates anchored to lexical word order; ASR notation variants remain separate from content presence.','Previously reviewed continuous-speech candidates use a short post-word waveform valley only when no sustained pause exists; no audio split/pause is introduced and conservative next-word onset overlap is disclosed.','The four removed summaries supply exactly 24 seconds for slower speech. Other exposure padding is timeline silence; no TTS is generated.']}
    save(ROOT/'narration/speech-edit-map-v4.json',report)
    print(json.dumps({'status':report['status'],'processed_seconds':count/SR,'cuts':len(cut_rows),'sections':len(sections),'asr_coverage':report['asr']['exact_character_coverage'],'source_hash':source_hash,'output':str(ROOT/'narration/speech-edit-map-v4.json')},ensure_ascii=False),flush=True)
    return 0
if __name__=='__main__':sys.exit(main())
