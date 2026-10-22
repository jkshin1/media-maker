#!/usr/bin/env python3
"""Mix one complete, unaccelerated narration master and the selected music.

The original narration PCM is placed once at sample zero. Only global frame
padding and the final card add silence; no old opening/ending mix is imported.
"""
from pathlib import Path
import argparse,hashlib,json,math,re,subprocess,wave
import numpy as np

ROOT=Path(__file__).resolve().parent
SR=48000

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def pcmsha(a):return hashlib.sha256(a.astype('<i2',copy=False).tobytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text())
def save(path,value):Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def portable(path):
    path=Path(path).resolve()
    try:return path.relative_to(ROOT).as_posix()
    except ValueError:return str(path)
def run(args):return subprocess.run(args,check=True,capture_output=True,text=True)
def read(path):
    with wave.open(str(path))as w:
        assert w.getframerate()==SR and w.getsampwidth()==2,'Expected 48 kHz 16-bit PCM.'
        return np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').reshape(-1,w.getnchannels()).copy()
def write(path,a):
    a=np.clip(np.rint(a),-32768,32767).astype('<i2')
    with wave.open(str(path),'wb')as w:w.setnchannels(a.shape[1]);w.setsampwidth(2);w.setframerate(SR);w.writeframes(a.tobytes())
def stats(a,step=.1):
    n=round(SR*step);a=a[:len(a)//n*n].astype(np.float64)/32768
    return np.sqrt(np.mean(a.reshape(-1,n,a.shape[1])**2,axis=(1,2)))
def db(a):return 20*np.log10(np.maximum(a,1e-12))
def loudnorm_measure(stderr):
    found=re.search(r'\{\s*"input_i".*?\}',stderr,re.S)
    assert found,'FFmpeg did not return loudness measurements.'
    return json.loads(found.group())

def build_music(original,total,fade_in_seconds,fade_out_seconds):
    """Preserve the song intro, then loop a phrase before its original fadeout."""
    intro=39*SR;period=round(128*60/113*SR);overlap=round(4*60/113*SR)
    assert len(original)>=intro+period+overlap,'Selected track is too short for the approved stable loop.'
    loop=np.zeros((total,2),dtype=np.float64)
    n=min(total,intro);loop[:n]=original[:n]
    core=original[intro:intro+period+overlap].astype(np.float64);crossfades=[]
    # The first stable phrase follows the original intro without a splice.
    for offset in range(intro,total,period):
        n=min(len(core),total-offset)
        if offset==intro:loop[offset:offset+n]=core[:n];continue
        nf=min(overlap,n);phase=np.linspace(0,math.pi/2,nf)
        loop[offset:offset+nf]=loop[offset:offset+nf]*np.cos(phase)[:,None]+core[:nf]*np.sin(phase)[:,None]
        if n>nf:loop[offset+nf:offset+n]=core[nf:n]
        crossfades.append({'start_sample':offset,'end_sample':offset+nf,'start':offset/SR,'end':(offset+nf)/SR})
    fadein=min(total,round(fade_in_seconds*SR));fadeout=min(total,round(fade_out_seconds*SR))
    if fadein:loop[:fadein]*=(.5-.5*np.cos(np.linspace(0,math.pi,fadein)))[:,None]
    if fadeout:loop[-fadeout:]*=(.5+.5*np.cos(np.linspace(0,math.pi,fadeout)))[:,None]
    return loop,{'bpm':113,'intro_seconds':39,'loop_source_samples':[intro,intro+period+overlap],'period_beats':128,'overlap_beats':4,'crossfades':crossfades,'fade_in_seconds':fade_in_seconds,'fade_out_seconds':fade_out_seconds,'source_speed_changed':False}

def build(args):
    out=args.output_dir;out.mkdir(parents=True,exist_ok=True);audit=out/'audio-audit';audit.mkdir(exist_ok=True)
    tl=load(args.timeline);manifest=load(args.manifest);alignmentpath=ROOT/manifest['alignment_report'];alignment=load(alignmentpath)
    assert tl['revision']==9 and not tl.get('preview_only')and tl['tempo']==1
    assert len(tl['audio_segments'])==68 and len(manifest['cuts'])==14 and manifest['required_output_tempo']==1
    assert alignment['status']in ['PASS','PASS_WITH_ASR_VARIANTS']
    assert not alignment.get('analysis_only')and not manifest.get('analysis_only'),'Analysis-only raw evidence is not a production mix approval.'
    assert sha(alignmentpath)==tl['alignment_report_sha256']
    masterpath=ROOT/manifest['master']['path'];original=read(masterpath)
    assert original.shape[1]==1 and sha(masterpath)==manifest['master']['sha256']==alignment['master_sha256']
    assert pcmsha(original)==manifest['master']['pcm_sha256']
    assert tl['fps']==30;total=tl['frames']*1600
    placements=[];chunks=[];previous=0
    for clip in manifest['cuts']:
        pcm=read(ROOT/clip['file']);a,b=clip['source_start_sample'],clip['source_end_sample']
        assert a==previous and np.array_equal(pcm,original[a:b])and sha(ROOT/clip['file'])==clip['sha256']
        assert pcmsha(pcm)==clip['pcm_sha256'];chunks.append(pcm);previous=b
        placements.append({'section_id':clip['section_id'],'source_start_sample':a,'source_end_sample':b,'start_sample':a,'end_sample':b,'exact_master_pcm':True,'audio_restart':False,'file_sha256':clip['sha256'],'pcm_sha256':clip['pcm_sha256']})
    assert previous==len(original)and np.array_equal(np.concatenate(chunks),original),'14 raw blocks must preserve the original recovered PCM.'
    master=original;workingpath=masterpath;editmap=None;extra_bindings=[]
    if manifest.get('working_master'):
        working=manifest['working_master'];workingpath=ROOT/working['path'];master=read(workingpath);editpath=ROOT/working['edit_map'];editmap=load(editpath)
        assert sha(workingpath)==working['sha256']and pcmsha(master)==working['pcm_sha256']and len(master)==working['sample_count']
        assert sha(editpath)==working['edit_map_sha256']and editmap['status']=='APPLIED_EXACT_QUIET_ONLY'
        assert sha(ROOT/editmap['approved_plan'])==editmap['approved_plan_sha256']
        retained=[original[p['raw_start_sample']:p['raw_end_sample']]for p in editmap['retained_pieces']]
        assert np.array_equal(np.concatenate(retained),master),'Retained original sample ranges must exactly reconstruct working audio.'
        for piece in editmap['retained_pieces']:assert pcmsha(original[piece['raw_start_sample']:piece['raw_end_sample']])==piece['pcm_sha256']
        assert len(original)-len(master)==editmap['removed_samples']==editmap['non_speech_samples_removed']and editmap['spoken_samples_removed']==0
        assert len(editmap['protected_phrase_pcm_proofs'])==68
        for proof in editmap['protected_phrase_pcm_proofs']:
            assert np.array_equal(original[proof['raw_start_sample']:proof['raw_end_sample']],master[proof['working_start_sample']:proof['working_end_sample']])
        def output_sample(sample):return sample-sum(max(0,min(sample,e['raw_remove_end_sample'])-e['raw_remove_start_sample'])for e in editmap['edits']if sample>e['raw_remove_start_sample'])
        for placement in placements:
            a,b=placement['source_start_sample'],placement['source_end_sample']
            placement.update(raw_source_start_sample=a,raw_source_end_sample=b,start_sample=output_sample(a),end_sample=output_sample(b),source_clock='original_recovered_composite',timeline_clock='pause_edited_working_master',raw_clip_is_audit_only=True,exact_master_pcm_meaning='Source raw clip equals its original composite range; the whole working master is played once, not restarted by raw clip.')
        extra_bindings.extend([workingpath,editpath,ROOT/editmap['approved_plan']])
    assembly=manifest.get('source_assembly')
    if assembly:
        assert manifest['generation_mode']=='single_take_with_authorized_original_ending_reuse'and manifest['ending_reuse_exception_authorized']
        assert sha(ROOT/assembly['authorization'])==assembly['authorization_sha256']
        for span in assembly['source_spans']:
            path=ROOT/span['file'];assert sha(path)==span['file_sha256'];part=read(path)[span['source_start_sample']:span['source_end_sample']]
            assert np.array_equal(part,original[span['composite_start_sample']:span['composite_end_sample']])and pcmsha(part)==span['pcm_sha256'];extra_bindings.append(path)
        extra_bindings.extend([ROOT/assembly['authorization'],ROOT/assembly['ending_review'],ROOT/assembly['prefix_review'],ROOT/'narration/recovery/recovery-map.json'])
    assert len(master)==tl['source_voice_samples']and total>=len(master)and tl['duration']<=tl['max_seconds']+1e-8
    segments=tl['audio_segments'];assert segments[0]['source_master_start_sample']==0 and segments[-1]['source_master_end_sample']==len(original)
    assert all(a['source_master_end_sample']==b['source_master_start_sample']for a,b in zip(segments,segments[1:]))
    if editmap:assert all(s['timeline_start_sample']==s['working_master_start_sample']and s['timeline_end_sample']==s['working_master_end_sample']and not s['audio_restart']for s in segments)
    else:assert all(s['timeline_start_sample']==s['source_master_start_sample']and s['timeline_end_sample']==s['source_master_end_sample']and not s['audio_restart']for s in segments)
    assert all(a['timeline_end_sample']==b['timeline_start_sample']for a,b in zip(segments,segments[1:]))and segments[-1]['timeline_end_sample']==len(master)
    raw=np.zeros((total,1),dtype='<i2');raw[:len(master)]=master;rawfile=out/'narration-raw.wav';write(rawfile,raw)
    measured=loudnorm_measure(run([args.ffmpeg,'-v','info','-i',str(rawfile),'-af','loudnorm=I=-18.5:TP=-3.5:LRA=9:print_format=json','-f','null','-']).stderr)
    filt='loudnorm=I=-18.5:TP=-3.5:LRA=9:linear=true:print_format=json:'+':'.join(f'{k}={measured[v]}'for k,v in [('measured_I','input_i'),('measured_TP','input_tp'),('measured_LRA','input_lra'),('measured_thresh','input_thresh'),('offset','target_offset')])
    normalized=out/'narration.wav';second=run([args.ffmpeg,'-y','-v','info','-i',str(rawfile),'-af',filt,'-ar',str(SR),'-ac','1','-c:a','pcm_s16le',str(normalized)])
    voice=read(normalized);assert len(voice)==total,'Loudness processing must retain the exact sample clock.'
    cfg=load(args.config);source=ROOT/cfg['bgm'];sourcewav=audit/'bgm-original.wav'
    run([args.ffmpeg,'-y','-v','error','-i',str(source),'-ar',str(SR),'-ac','2','-c:a','pcm_s16le',str(sourcewav)])
    loop,musicplan=build_music(read(sourcewav),total,args.fade_in_seconds,args.fade_out_seconds);loopfile=out/'bgm-loop.wav';write(loopfile,loop)
    basefile=audit/'music-base.wav';musicfile=audit/'music-final.wav'
    # Padding completes all FFmpeg compressor buffers outside the delivered
    # timeline, avoiding EOF-dependent last-block flush differences.
    graph=f'[0:a]apad=pad_len={SR}[side];[1:a]apad=pad_len={SR},volume=0.125,asplit=2[basepre][music];[basepre]atrim=end_sample={total}[base];[music][side]sidechaincompress=threshold=0.018:ratio=4:attack=45:release=650:makeup=1:mix=0.60,atrim=end_sample={total}[duck]'
    run([args.ffmpeg,'-y','-v','error','-filter_complex_threads','1','-i',str(normalized),'-i',str(loopfile),'-filter_complex',graph,'-map','[base]','-c:a','pcm_s16le',str(basefile),'-map','[duck]','-c:a','pcm_s16le',str(musicfile)])
    base=read(basefile);music=read(musicfile);assert len(music)==total and len(base)==total
    mixed=voice.astype(np.int32)+music.astype(np.int32)
    peak=int(np.max(np.abs(mixed)));assert peak<32767,'New music sum clips; do not conceal this by limiting all narration again.'
    final=out/'audio.wav';write(final,mixed)
    base_rms=stats(base);music_rms=stats(music);voice_db=db(stats(voice));music_db=db(music_rms);time=np.arange(len(music_db))*.1
    core=(time>=args.fade_in_seconds+.1)&(time<total/SR-args.fade_out_seconds-.1);active=core&(voice_db>-32)
    assert np.any(core)and np.any(active),'Audio is too short/quiet to evaluate the music policy.'
    ratio=np.divide(music_rms,base_rms,out=np.ones_like(base_rms),where=base_rms>1e-8);gap=voice_db-music_db
    checks={'fourteen_exact_original_pcm_slices':len(placements)==14,'raw_clips_reconstruct_original_source':np.array_equal(np.concatenate(chunks),original),'retained_original_pcm_exact_in_working':True,'spoken_samples_removed_zero':not editmap or editmap['spoken_samples_removed']==0,'whole_working_master_single_continuous_placement':np.array_equal(raw[:len(master)],master)and not np.any(raw[len(master):]),'all_sixty_eight_audio_segments_contiguous':len(segments)==68,'tempo_unchanged':tl['tempo']==1,'authorized_original_ending_assembly_exact':bool(assembly),'exact_frame_locked_sample_count':len(mixed)==total,'duration_within_hard_maximum':total/SR<=tl['max_seconds']+1e-8,'no_100ms_music_zero_outside_end_fades':not np.any(music_rms[core]==0),'duck_floor_above_minus_8_1_db':float(np.min(db(ratio)[core]))>=-8.1,'no_mix_clipping':peak<32767,'speech_six_db_above_music_95_percent':float(np.percentile(gap[active],5))>=6,'no_additional_mix_limiter':True}
    checks={k:bool(v)for k,v in checks.items()}
    report={'status':'PASS'if all(checks.values())else'REVIEW','revision':9,'checks':checks,'duration':total/SR,'sample_rate':SR,'channels':2,'samples':total,'audio_file':'audio.wav','audio_sha256':sha(final),'voice':cfg['voice_name'],'model_id':cfg['model_id'],'generation_mode':'single_take','new_full_narration':True,'tempo':1,'opening_and_ending_reused':False,'source_master_sha256':sha(masterpath),'source_master_pcm_sha256':pcmsha(master),'source_master_samples':len(master),'source_samples_removed':0,'source_samples_duplicated':0,'continuous_source_placement_count':1,'audio_restarts_at_visual_boundaries':0,'global_silent_tail_samples':total-len(master),'final_frame_padding_samples':tl['final_frame_padding_samples'],'final_card_seconds':tl['final_card_seconds'],'normalization':{'target_integrated_lufs':-18.5,'true_peak_db':-3.5,'first_pass':measured,'second_pass':loudnorm_measure(second.stderr),'changes_tempo':False},'bgm':{**musicplan,'source':portable(source),'source_sha256':sha(source),'source_track':'Comprehension / Frank Jonsson','base_gain':.125,'duck_wet_mix':.6,'duck_dry_floor':.4,'attack_ms':45,'release_ms':650,'minimum_duck_db':float(np.min(db(ratio)[core])),'music_rms_dbfs_p05_median_p95':list(map(float,np.percentile(music_db[core],[5,50,95]))),'speech_minus_music_db_p05_median_p95':list(map(float,np.percentile(gap[active],[5,50,95])))},'mix_peak_integer':peak,'mix_peak_dbfs':20*math.log10(max(peak,1)/32768),'additional_mix_limiter_samples':0,'additional_mix_limiter_ratio':0,'placements':placements,'scope':'Exact raw PCM preservation, original sample-clock timing and objective audio envelope checks. Fresh normalized voice ASR, subjective pronunciation/BGM listening, and final encoded playback are separate.','ffmpeg_version':run([args.ffmpeg,'-version']).stdout.splitlines()[0]}
    report.update(generation_mode=manifest['generation_mode'],ending_reuse_exception_authorized=bool(assembly),fresh_body_narration=bool(assembly),new_full_narration=False if assembly else True,speech_tempo=1,ending_reused=bool(assembly),opening_reused=False,source_master_pcm_sha256=pcmsha(original),source_master_samples=len(original),working_master_file=portable(workingpath),working_master_sha256=sha(workingpath),working_master_pcm_sha256=pcmsha(master),working_master_samples=len(master),source_samples_removed=len(original)-len(master),non_speech_samples_removed=len(original)-len(master),spoken_samples_removed=0,original_sources_preserved=True)
    report['actual_master_placements']=[{'file':portable(workingpath),'source_start_sample':0,'source_end_sample':len(master),'timeline_start_sample':0,'timeline_end_sample':len(master),'pcm_sha256':pcmsha(master),'continuous':True}]
    report['placements_are_original_clip_audit_ranges']=True
    if editmap:report.update(pause_edit_map=manifest['working_master']['edit_map'],pause_edit_map_sha256=manifest['working_master']['edit_map_sha256'],approved_pause_plan_sha256=editmap['approved_plan_sha256'],protected_speech_pcm_exact_count=68)
    bound=list(dict.fromkeys([args.timeline,args.manifest,alignmentpath,args.config,masterpath,source,Path(__file__),*extra_bindings]))
    report['input_bindings']=[{'file':portable(p),'sha256':sha(p)}for p in bound]
    report['artifacts']={p.name:{'sha256':sha(p),'sample_count':len(read(p)),'pcm_sha256':pcmsha(read(p))}for p in [final,normalized,rawfile,loopfile]}
    save(out/'audio-validation.json',report);save(args.manifest.parent/'mix-provenance.json',report)
    print(json.dumps({'status':report['status'],'duration':total/SR,'checks':checks,'audio':str(final)},ensure_ascii=False))
    assert all(checks.values()),'Audio review required; see audio-validation.json.'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--timeline',type=Path,default=ROOT/'timeline.json');p.add_argument('--manifest',type=Path,default=ROOT/'narration/elevenlabs/manifest.json');p.add_argument('--config',type=Path,default=ROOT/'narration/ko.json')
    p.add_argument('--output-dir',type=Path,default=ROOT.parent/'out/showcase-v9');p.add_argument('--ffmpeg',default='ffmpeg');p.add_argument('--fade-in-seconds',type=float,default=2);p.add_argument('--fade-out-seconds',type=float,default=4)
    args=p.parse_args();assert args.fade_in_seconds>=0 and args.fade_out_seconds>=0;build(args)

if __name__=='__main__':main()
