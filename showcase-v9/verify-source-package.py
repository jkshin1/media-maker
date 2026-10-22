#!/usr/bin/env python3
"""Audit a final Revision9 ZIP and reproduce its 69 PNGs and four PCM WAVs.

Run only after the final archive is ready. No remote voice generation, complete
video encode, mux, listening review or browser playback is performed. Original
workspace sources/media are read only; execution occurs in a fresh private tmp.
"""
from pathlib import Path, PurePosixPath
import argparse, hashlib, io, json, os, re, stat, subprocess, sys, tempfile
import unicodedata, urllib.parse, wave, zipfile

ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'out/showcase-v9'
ARCHIVE_NAME='RD_Process_AI_Fast_Track_Showcase_Revision9_Source.zip'
VIDEO_NAME='RD_Process_AI_Fast_Track_Showcase_Revision9.mp4'
ORDER=['opening','task11','task13','task7','task17','task5','task9','task4','task12','task3','task8','task14','task16','ending']
TASK_COUNTS={'task11':5,'task13':5,'task7':5,'task17':4,'task5':5,'task9':5,'task4':5,'task12':3,'task3':4,'task8':4,'task14':5,'task16':5}
TEXT_EXT={'.json','.txt','.md','.py','.js','.mjs','.cjs','.html','.css','.toml','.yaml','.yml','.csv','.srt','.vtt'}
SIGNED_KEYS={'x-amz-signature','x-amz-credential','x-amz-security-token','x-goog-signature','x-goog-credential','signature','sig','token','access_token','authorization','jwt','key-pair-id','policy'}
BUNDLED_PYTHON=Path('/Users/jk/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3')

def sha(data):return hashlib.sha256(data).hexdigest()
def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb')as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def relative(value):
    if not isinstance(value,str)or not value or '\\'in value or '\0'in value:return False
    p=PurePosixPath(value)
    return not p.is_absolute()and '..'not in p.parts and not re.match(r'^[A-Za-z]:',value)
def cleaned(value):
    if isinstance(value,dict):return{k:cleaned(v)for k,v in value.items()if k!='url'and not k.endswith('_url')}
    if isinstance(value,list):return[cleaned(v)for v in value]
    return value
def identity(rows):
    values=[{k:r[k]for k in ('file','sha256','bytes')}for r in rows if r['file'].startswith('showcase-v9/')]
    data=json.dumps(sorted(values,key=lambda r:r['file']),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    return{'file_count':len(values),'manifest_sha256':sha(data)}
def signed_hits(name,data):
    """Report filenames, JSON key paths and query-key names, never URL values."""
    try:text=data.decode('utf-8')
    except UnicodeDecodeError:return[]
    strings=[]
    def walk(v,key='$'):
        if isinstance(v,dict):
            for k,x in v.items():walk(x,key+'.'+str(k))
        elif isinstance(v,list):
            for i,x in enumerate(v):walk(x,f'{key}[{i}]')
        elif isinstance(v,str):strings.append((key,v))
    try:walk(json.loads(text))
    except(ValueError,TypeError):strings=[('$text',text)]
    result=[]
    for key,value in strings:
        value=value.replace('\\/','/').replace('&amp;','&')
        for _ in range(2):
            decoded=urllib.parse.unquote(value)
            if decoded==value:break
            value=decoded
        for url in re.findall(r'https?://[^\s\"\'<>]+',value,re.I):
            query=urllib.parse.parse_qsl(urllib.parse.urlsplit(url.rstrip('),.;]')).query,keep_blank_values=True)
            keys=sorted({k for k,_ in query if k.lower()in SIGNED_KEYS or k.lower().startswith(('x-amz-','x-goog-'))})
            if keys:result.append({'file':name,'key_path':key,'parameter_keys':keys})
        if re.search(r'X-(?:Amz|Goog)-Signature\s*(?:=|%3D)',value,re.I)and not any(r['key_path']==key for r in result):
            result.append({'file':name,'key_path':key,'parameter_keys':['signature-marker']})
    return result
def wav_bytes(data):
    with wave.open(io.BytesIO(data),'rb')as w:
        info={'sample_rate':w.getframerate(),'channels':w.getnchannels(),'sample_width':w.getsampwidth(),'sample_count':w.getnframes()}
        pcm=w.readframes(w.getnframes())
    return info,pcm
def wav_identity(path):
    h=hashlib.sha256()
    with wave.open(str(path),'rb')as w:
        info={'sample_rate':w.getframerate(),'channels':w.getnchannels(),'sample_width':w.getsampwidth(),'sample_count':w.getnframes()}
        for data in iter(lambda:w.readframes(48000),b''):h.update(data)
    return{**info,'sha256':file_sha(path),'pcm_sha256':h.hexdigest()}
def passing(report):
    if report.get('status')not in {'PASS','PASS_WITH_ASR_VARIANTS'}:return False
    checks=report.get('checks')
    if checks is None:return True
    if isinstance(checks,dict):return bool(checks)and all(v is True or isinstance(v,dict)and(v.get('pass')is True or v.get('status')=='PASS')for v in checks.values())
    if isinstance(checks,list):return bool(checks)and all(v.get('pass')is True or v.get('status')=='PASS'for v in checks)
    return False
def report_video_hash(report):return report.get('final_sha256',report.get('video_sha256',report.get('sha256')))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive',nargs='?',type=Path,default=OUT/ARCHIVE_NAME)
    parser.add_argument('--package-only',action='store_true',help='Validate a receipt-only repack without repeating PNG/audio execution.')
    args=parser.parse_args();archive=args.archive.resolve()
    if not archive.exists():
        print(json.dumps({'status':'WAITING_FOR_FINAL_ARCHIVE','validation_performed':False,'reproduction_performed':False}));return 0
    OUT.mkdir(parents=True,exist_ok=True)
    package={'status':'IN_PROGRESS','revision':9,'scope':'Exact final ZIP inventory, CRC, privacy and active relative-input bindings.','checks':{},'tested_archive':{'file':str(archive),'bytes':archive.stat().st_size,'sha256':file_sha(archive)}}
    repro={'status':'NOT_RUN','revision':9,'preview_only':False,'checks':{},'scope':'Fresh extracted actual-timeline native PNG and local four-WAV reproduction.','new_tts':False,'whole_video_encode_repeated':False,'mux_or_browser_playback_repeated':False}
    active=package
    def check(report,name,ok,detail):
        report['checks'][name]={'pass':bool(ok),'details':detail}
        if not ok:raise AssertionError(name)
    try:
        with zipfile.ZipFile(archive)as z:
            infos=z.infolist();names=[i.filename for i in infos if not i.is_dir()];invalid=[];collisions=[];seen={}
            for info in infos:
                name=info.filename;key=unicodedata.normalize('NFC',name.rstrip('/')).casefold()
                if not relative(name)or stat.S_ISLNK(info.external_attr>>16):invalid.append(name)
                if key in seen and seen[key]!=name:collisions.append([seen[key],name])
                seen[key]=name
            check(package,'safe_relative_paths_no_symlinks_or_collisions',not invalid and not collisions,{'invalid':invalid,'normalized_collisions':collisions})
            check(package,'unique_archive_members',len(names)==len(set(names)),{'file_members':len(names)})
            manifest_data=z.read('SOURCE_MANIFEST.json');manifest=json.loads(manifest_data);rows=manifest['files'];listed=[r['file']for r in rows]
            check(package,'exact_source_manifest_inventory',len(listed)==len(set(listed))and set(names)==set(listed)|{'SOURCE_MANIFEST.json'},{'manifest_files':len(rows),'missing':sorted(set(listed)-set(names)),'unlisted':sorted(set(names)-set(listed)-{'SOURCE_MANIFEST.json'})})
            mismatch=[];secrets=[];source_mismatch=[];redactions=[];workspace_before={}
            for row in rows:
                h=hashlib.sha256();count=0;text=bytearray();window=b'';istext=Path(row['file']).suffix.lower()in TEXT_EXT
                with z.open(row['file'])as f:
                    for block in iter(lambda:f.read(1024*1024),b''):
                        h.update(block);count+=len(block)
                        if istext:text.extend(block)
                        else:
                            for match in re.findall(rb'https?://[^\s\"\'<>\x00-\x20]{1,16384}',window+block):secrets.extend(signed_hits(row['file'],match))
                            window=block[-16384:]
                if h.hexdigest()!=row['sha256']or count!=row['bytes']:mismatch.append(row['file'])
                if istext:secrets.extend(signed_hits(row['file'],bytes(text)))
                if row['file'].startswith('showcase-v9/'):
                    rel=row['file'].split('/',1)[1];original=ROOT/rel
                    if not original.exists():source_mismatch.append({'file':rel,'reason':'missing_workspace_source'});continue
                    workspace_before[row['file']]=file_sha(original)
                    if workspace_before[row['file']]!=row['sha256']:
                        allowed=rel.startswith('narration/')and original.suffix=='.json'and any(k in original.name for k in ['receipt','generation'])
                        cleaned_data=(json.dumps(cleaned(json.loads(original.read_text())),ensure_ascii=False,indent=2)+'\n').encode()if allowed else b''
                        if allowed and sha(cleaned_data)==row['sha256']:redactions.append({'file':rel,'original_sha256':workspace_before[row['file']],'packaged_sha256':row['sha256'],'kind':'generation_URL_field_redaction_only'})
                        else:source_mismatch.append({'file':rel,'reason':'unexpected_source_difference'})
            secrets.extend(signed_hits('SOURCE_MANIFEST.json',manifest_data))
            check(package,'all_member_sha256_and_sizes_match',not mismatch,{'verified_files':len(rows),'mismatch_files':mismatch})
            check(package,'all_zip_members_crc_verified',True,{'members_read_completely':len(rows)+1,'method':'ZipExtFile CRC is checked while every member, including the manifest, is read to EOF.'})
            check(package,'signed_generation_url_residue_zero',not secrets,{'hit_count':len(secrets),'hits':secrets,'URL_values_printed':False})
            check(package,'workspace_source_matches_except_exact_URL_redactions',not source_mismatch,{'source_files':len(workspace_before),'allowed_redactions':redactions,'unexpected_differences':source_mismatch})
            def load(name):return json.loads(z.read(name))
            def source_json(name):return load('showcase-v9/'+name)
            tl=source_json('timeline.json');spec=source_json('spec.json');config=source_json('narration/ko.json');voice=source_json('narration/elevenlabs/manifest.json')
            check(package,'final_delivery_and_authorized_ending_exception',manifest.get('production_complete')is True and manifest.get('delivery_status')=='FINAL'and manifest.get('revision')==9 and manifest.get('ending_reuse_exception_authorized')is True and manifest.get('speech_tempo')==1 and manifest.get('max_seconds')==315,{'delivery_status':manifest.get('delivery_status'),'ending_reuse_exception_authorized':manifest.get('ending_reuse_exception_authorized'),'generation_mode':manifest.get('generation_mode'),'speech_tempo':manifest.get('speech_tempo')})
            task_sections=[s for s in spec['sections']if s['type']=='task'];entries=tl['entries'];ending_indices=[e['cut_index']for e in entries if e['section_id']=='ending'];entry_sections=list(dict.fromkeys(e['section_id']for e in entries))
            check(package,'actual_69_entry_timeline_and_exact_script_shape',tl.get('revision')==9 and tl.get('preview_only')is False and not tl.get('analysis_only')and tl['fps']==30 and tl['tempo']==1 and tl['duration']<=315 and abs(tl['frames']/30-tl['duration'])<1e-8 and len(entries)==69 and all(e['kind']!='title'for e in entries)and entry_sections==ORDER and ending_indices==[0,1,2,4,5]and{s['id']:len(s['cuts'])for s in task_sections}==TASK_COUNTS and len(tl['audio_segments'])==68 and len(config['blocks'])==14 and sum(len(b['cuts'])for b in config['blocks'])==68,{'duration_seconds':tl['duration'],'frames':tl['frames'],'entries':len(entries),'audio_segments':len(tl['audio_segments']),'section_order':entry_sections,'ending_physical_indices':ending_indices})
            required=['render.mjs','stage.mjs','task-scenes.js','hero-scenes.js','task-visuals-early.js','task-visuals-late.js','photo-camera.js','photo-camera-profiles.json','audio.py','mix-v9-audio.py','verify-source-package.py','fonts/NotoSansCJKkr-Regular.otf','fonts/NotoSansCJKkr-Bold.otf','narration/elevenlabs/take.wav']
            missing=[f for f in required if 'showcase-v9/'+f not in names]
            check(package,'required_portable_runtime_and_original_take_present',not missing,{'required_files':len(required),'missing':missing})
            render=load('out/showcase-v9/render-validation.json');audio=load('out/showcase-v9/audio-validation.json');final=load('out/showcase-v9/final-validation.json');mux=load('out/showcase-v9/mux-validation.json')
            current_video=OUT/VIDEO_NAME;current_hash=file_sha(current_video)if current_video.exists()else None
            check(package,'final_receipts_bound_to_actual_video_and_mix',all(passing(r)for r in [render,audio,final,mux])and render.get('preview_only')is False and render.get('timeline_file')=='timeline.json'and current_hash is not None and report_video_hash(final)==report_video_hash(mux)==current_hash and audio['audio_sha256']==file_sha(OUT/'audio.wav'),{'video_sha256':current_hash,'render_status':render.get('status'),'audio_status':audio.get('status'),'final_status':final.get('status'),'mux_status':mux.get('status'),'audio_sha256':audio.get('audio_sha256')})
            bound=render.get('inputs',[])+audio.get('input_bindings',[]);binding_bad=[]
            for item in bound:
                name=item.get('file')
                if not relative(name)or'showcase-v9/'+name not in names or sha(z.read('showcase-v9/'+name))!=item.get('sha256'):binding_bad.append(name)
            working=voice.get('working_master',{})
            active_paths=[voice['master']['path'],voice['alignment_report'],config['bgm'],working.get('path'),working.get('edit_map')]+[c['file']for c in voice['cuts']]+[s['file']for s in tl['audio_segments']]
            assembly_paths=[];assembly_detail={'present':False}
            if voice.get('source_assembly'):
                # The manifest embeds the recovery-map JSON, not its filename.
                # The mixer binds this relative file; both representations must
                # agree exactly, in addition to the archived byte-hash binding.
                assembly=voice['source_assembly']
                assembly_file=voice.get('source_assembly_file','narration/recovery/recovery-map.json')
                assembly_paths.append(assembly_file);active_paths.append(assembly_file)
                assembly_present=relative(assembly_file)and'showcase-v9/'+assembly_file in names
                assembly_bytes=z.read('showcase-v9/'+assembly_file)if assembly_present else b''
                assembly_equal=assembly_present and isinstance(assembly,dict)and json.loads(assembly_bytes)==assembly
                assembly_hash_ok=assembly_present and sha(assembly_bytes)==voice.get('source_assembly_sha256')
                if not assembly_hash_ok or not assembly_equal:binding_bad.append('source_assembly')
                assembly_detail={'present':True,'file':assembly_file,'archived_sha256_matches':assembly_hash_ok,'embedded_json_matches_archived_file':assembly_equal}
            bad_paths=[p for p in active_paths if not relative(p)or'showcase-v9/'+p not in names]
            alignment=source_json(voice['alignment_report']);audio_bound={r['file']for r in audio.get('input_bindings',[])}
            critical_bound={voice['master']['path'],working.get('path'),working.get('edit_map'),'timeline.json','narration/ko.json','narration/elevenlabs/manifest.json',*assembly_paths}
            alignment_master_bound=alignment['master_sha256']in {voice['master']['sha256'],working.get('sha256')}
            check(package,'active_render_audio_inputs_are_relative_archived_and_hash_bound',bool(render.get('inputs'))and bool(audio.get('input_bindings'))and not binding_bad and not bad_paths and critical_bound<=audio_bound and sha(z.read('showcase-v9/'+voice['alignment_report']))==tl['alignment_report_sha256']and alignment_master_bound,{'render_inputs':len(render.get('inputs',[])),'audio_input_bindings':len(audio.get('input_bindings',[])),'active_relative_paths':len(active_paths),'binding_mismatches':binding_bad,'invalid_or_missing_active_paths':bad_paths,'critical_audio_inputs_missing_bindings':sorted(str(x)for x in critical_bound-audio_bound),'source_assembly':assembly_detail})
            master_data=z.read('showcase-v9/'+voice['master']['path']);params,master_pcm=wav_bytes(master_data);parts=[];previous=0;pcm_rows=[]
            for cut in voice['cuts']:
                data=z.read('showcase-v9/'+cut['file']);info,pcm=wav_bytes(data);a,b=cut['source_start_sample'],cut['source_end_sample']
                ok=a==previous and b>a and info=={**params,'sample_count':b-a}and sha(data)==cut['sha256']and sha(pcm)==cut['pcm_sha256']and pcm==master_pcm[a*2:b*2]
                pcm_rows.append({'section_id':cut['section_id'],'file':cut['file'],'start_sample':a,'end_sample':b,'exact_active_master_pcm':ok});parts.append(pcm);previous=b
            working_data=z.read('showcase-v9/'+working['path']);working_params,working_pcm=wav_bytes(working_data)
            edit_data=z.read('showcase-v9/'+working['edit_map']);edit=json.loads(edit_data);pieces=edit['retained_pieces'];protected=edit['protected_phrase_pcm_proofs'];retained=[];previous_raw=previous_work=0;piece_failures=[]
            for i,piece in enumerate(pieces):
                a,b=piece['raw_start_sample'],piece['raw_end_sample'];c,d=piece['working_start_sample'],piece['working_end_sample'];raw_pcm=master_pcm[a*2:b*2];work_pcm=working_pcm[c*2:d*2]
                if not(a>=previous_raw and c==previous_work and b>a and d-c==b-a and raw_pcm==work_pcm and sha(raw_pcm)==piece['pcm_sha256']):piece_failures.append(i)
                retained.append(raw_pcm);previous_raw=b;previous_work=d
            protected_failures=[]
            for proof in protected:
                a,b=proof['raw_start_sample'],proof['raw_end_sample'];c,d=proof['working_start_sample'],proof['working_end_sample'];raw_pcm=master_pcm[a*2:b*2];work_pcm=working_pcm[c*2:d*2]
                if not(proof.get('retained_pcm_exact')is True and b>a and d-c==b-a and raw_pcm==work_pcm and sha(raw_pcm)==proof['pcm_sha256']):protected_failures.append(proof['cut_id'])
            expected_ids={c['id']for block in config['blocks']for c in block['cuts']}
            working_ok=sha(working_data)==working['sha256']and sha(working_pcm)==working['pcm_sha256']and sha(edit_data)==working['edit_map_sha256']and not piece_failures and bool(pieces)and b''.join(retained)==working_pcm and previous_work==working_params['sample_count']and working_params=={**params,'sample_count':working['sample_count']}and len(protected)==68 and{p['cut_id']for p in protected}==expected_ids and not protected_failures and edit.get('spoken_samples_removed')==0
            check(package,'fourteen_raw_clips_and_working_retained_speech_pcm_exact',not voice.get('analysis_only')and len(voice['cuts'])==14 and[c['section_id']for c in voice['cuts']]==ORDER and all(r['exact_active_master_pcm']for r in pcm_rows)and b''.join(parts)==master_pcm and previous==params['sample_count']and params['sample_rate']==48000 and params['channels']==1 and params['sample_width']==2 and sha(master_data)==voice['master']['sha256']and sha(master_pcm)==voice['master']['pcm_sha256']and voice.get('required_output_tempo')==1 and working_ok,{'master_path':voice['master']['path'],'master_pcm_sha256':sha(master_pcm),'master_parameters':params,'clips':pcm_rows,'working_path':working['path'],'working_parameters':working_params,'edit_map':working['edit_map'],'retained_pieces':len(pieces),'protected_phrase_proofs':len(protected),'piece_failures':piece_failures,'protected_phrase_failures':protected_failures,'removed_non_speech_samples':params['sample_count']-working_params['sample_count'],'scope':'Original composite/14 raw cuts and retained working PCM are checked directly; lexical/acoustic completeness remains an independent archived coverage review.'})
            runtime={s['reference_image']for s in spec['sections']if s.get('reference_image')}
            runtime.update(p for s in spec['sections']for p in s.get('backgrounds',[])if p);runtime.update(spec.get('microscopy',{}).values());runtime.update(f'assets/opening/cut{i:02d}.png'for i in range(1,10))
            missing=[p for p in runtime if not relative(p)or'showcase-v9/'+p not in names]
            check(package,'all_declared_native_assets_in_archive',not missing,{'assets':len(runtime),'missing':missing})
            assert len(package['checks'])==14
            package.update(status='PASS',source_manifest_sha256=sha(manifest_data),immutable_source_identity=identity(rows),archive_file_count=len(names))
            package['scope_limits']=['No new complete-video encoding, AAC mux, human listening or browser playback is performed.','Exact file/PCM reproduction requires the same compatible native canvas/font/FFmpeg/Python runtime; actual versions are recorded.']
            prior_repro=OUT/'source-reproduction-validation.json'
            if args.package_only and prior_repro.exists():
                prior=json.loads(prior_repro.read_text())
                if prior.get('status')=='SOURCE_PASS':
                    assert prior['immutable_source_identity']==package['immutable_source_identity'],'receipt-only repack changed executable source identity'
                    package['same_immutable_source_as_fresh_reproduction']=True
            save(OUT/'source-package-validation.json',package)
            if args.package_only:
                print(json.dumps({'package_status':'PASS','checks':14,'archive_sha256':package['tested_archive']['sha256'],'immutable_source_identity':package['immutable_source_identity']}));return 0
            temp=Path(tempfile.mkdtemp(prefix='media-maker-v9-source-smoke-',dir='/private/tmp'));z.extractall(temp)
        active=repro;extracted=temp/'showcase-v9';tempout=temp/'out/showcase-v9';source_rows=[r for r in rows if r['file'].startswith('showcase-v9/')]
        repro.update(tested_archive=package['tested_archive'],source_manifest_sha256=package['source_manifest_sha256'],immutable_source_identity=package['immutable_source_identity'],extraction_directory=str(temp))
        before={r['file']:file_sha(temp/r['file'])for r in source_rows}
        check(repro,'isolated_fresh_extraction_without_adjacent_baselines',not any((temp/f'showcase-v{i}').exists()for i in range(1,9)),{'directory':str(temp)})
        check(repro,'extracted_source_files_match_zip',all(before[r['file']]==r['sha256']for r in source_rows),{'files':len(source_rows)})
        expected_png={p.name:file_sha(p)for p in sorted((OUT/'stills').glob('*.png'))};wav_names=['audio.wav','narration.wav','narration-raw.wav','bgm-loop.wav'];expected_wav={n:wav_identity(OUT/n)for n in wav_names}
        check(repro,'canonical_actual_outputs_match_active_timeline',len(expected_png)==69 and expected_wav['audio.wav']['sha256']==audio['audio_sha256']and all(w['sample_rate']==48000 and w['sample_count']==tl['frames']*1600 for w in expected_wav.values()),{'native_png_count':len(expected_png),'wav_files':expected_wav})
        env=os.environ.copy();env['TIMELINE_FILE']='timeline.json'
        for name in ['RENDER_FILE','RENDER_REPORT','SHOWCASE_OUT','SHOWCASE_VIDEO']:env.pop(name,None)
        node=os.environ.get('NODE_BINARY','node');node_version=subprocess.check_output([node,'--version'],text=True).strip();log=OUT/'source-reproduction-render.log'
        with log.open('w')as f:result=subprocess.run([node,'render.mjs','--stills'],cwd=extracted,env=env,stdout=f,stderr=subprocess.STDOUT)
        check(repro,'portable_actual_native_render_succeeded',result.returncode==0,{'return_code':result.returncode,'node_version':node_version,'command':'TIMELINE_FILE=timeline.json node render.mjs --stills','log':str(log),'whole_video_encode':False})
        actual_png={p.name:file_sha(p)for p in sorted((tempout/'stills').glob('*.png'))};unequal=[n for n in sorted(set(expected_png)|set(actual_png))if expected_png.get(n)!=actual_png.get(n)]
        check(repro,'all_69_native_png_files_byte_identical',len(actual_png)==69 and not unequal,{'expected':len(expected_png),'actual':len(actual_png),'mismatch_files':unequal})
        visual=json.loads((tempout/'visual-validation.json').read_text());motion=visual.get('motion',[])
        check(repro,'actual_timeline_69_motion_probes_and_no_captions',visual.get('preview_only')is False and visual.get('timeline_file')=='timeline.json'and len(visual.get('records',[]))==69 and len(motion)==69 and all(x['moving']for x in motion)and all(not x.get('caption')for x in visual['records']),{'records':len(visual.get('records',[])),'motion_probes':len(motion),'moving':sum(x['moving']for x in motion),'scope':'Time-separated native RGBA differences, not a repeated encoded playback judgment.'})
        interpreter=os.environ.get('AUDIO_PYTHON',str(BUNDLED_PYTHON)if BUNDLED_PYTHON.exists()else sys.executable);audio_log=OUT/'source-reproduction-audio.log'
        with audio_log.open('w')as f:result=subprocess.run([interpreter,'audio.py'],cwd=extracted,env=env,stdout=f,stderr=subprocess.STDOUT)
        check(repro,'portable_local_saved_audio_mix_succeeded',result.returncode==0,{'return_code':result.returncode,'interpreter':interpreter,'command':'python3 audio.py','log':str(audio_log),'remote_generation_invoked':False,'ffmpeg_version':subprocess.check_output(['ffmpeg','-version'],text=True).splitlines()[0]})
        actual_wav={n:wav_identity(tempout/n)for n in wav_names}
        check(repro,'four_wav_files_and_pcm_exact',expected_wav==actual_wav,{'expected':expected_wav,'reproduced':actual_wav,'file_matches':sum(expected_wav[n]['sha256']==actual_wav[n]['sha256']for n in wav_names),'pcm_matches':sum(expected_wav[n]['pcm_sha256']==actual_wav[n]['pcm_sha256']for n in wav_names)})
        rebuilt=json.loads((tempout/'audio-validation.json').read_text())
        check(repro,'rebuilt_audio_checks_pass_and_relative_inputs_preserved',passing(rebuilt)and rebuilt['audio_sha256']==expected_wav['audio.wav']['sha256']and all(relative(r['file'])and file_sha(extracted/r['file'])==r['sha256']for r in rebuilt['input_bindings']),{'status':rebuilt.get('status'),'input_bindings':len(rebuilt.get('input_bindings',[]))})
        changed=[r['file']for r in source_rows if file_sha(temp/r['file'])!=before[r['file']]]
        check(repro,'extracted_archived_sources_unchanged',not changed,{'source_files':len(source_rows),'changed_files':changed})
        changed=[name for name,h in workspace_before.items()if file_sha(ROOT/name.split('/',1)[1])!=h]
        check(repro,'original_workspace_sources_and_reference_outputs_unchanged',not changed and expected_png=={p.name:file_sha(p)for p in(OUT/'stills').glob('*.png')}and expected_wav=={n:wav_identity(OUT/n)for n in wav_names},{'source_files':len(workspace_before),'changed_files':changed,'native_pngs':69,'wav_files':4})
        repro.update(status='SOURCE_PASS',native_png_hashes=actual_png,audio_outputs=actual_wav)
        repro['scope_limits']=['69 PNGs, 69 native motion probes and four WAV/decoded-PCM outputs reproduced from the exact archived active inputs only.','No remote generation, complete MP4 rerender, mux, browser playback or subjective listening performed.','Authorized ending reuse and pause edits remain separate from fresh voice generation and are bound to archived assembly/coverage evidence.'];save(OUT/'source-reproduction-validation.json',repro)
        print(json.dumps({'package_status':'PASS','package_checks':14,'reproduction_status':'SOURCE_PASS','reproduction_checks':len(repro['checks']),'png_matches':69,'wav_file_matches':4,'pcm_matches':4,'signed_URL_residue':0,'archive_sha256':package['tested_archive']['sha256'],'immutable_source_identity':package['immutable_source_identity'],'extraction_directory':str(temp)}));return 0
    except Exception as error:
        active['status']='FAIL';active['error']={'type':type(error).__name__,'check':str(error)};save(OUT/'source-package-validation.json',package)
        if active is repro:save(OUT/'source-reproduction-validation.json',repro)
        print(json.dumps({'status':'FAIL','type':type(error).__name__,'check':str(error)}));return 1

if __name__=='__main__':sys.exit(main())
