#!/usr/bin/env python3
"""Preserve the approved voice/outer PCM, repair only the body music bed."""
from pathlib import Path
import hashlib, importlib.util, json, math, shutil, wave
import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT.parent / 'out/showcase-v5'
SR = 48000
BODY_START = 39.0
BODY_END = 288.1
BPM = 113
LOOP_START = 39.0
PERIOD_BEATS = 128
OVERLAP_BEATS = 4
OUTER_BLEND_SECONDS = 1.2
BODY_MUSIC_GAIN = .125


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def save_wave(path, values):
    values = np.clip(np.rint(values), -32768, 32767).astype('<i2')
    with wave.open(str(path), 'wb') as f:
        f.setnchannels(values.shape[1]); f.setsampwidth(2); f.setframerate(SR)
        f.writeframes(values.tobytes())


def main():
    spec = importlib.util.spec_from_file_location('v5_music_audit', ROOT / 'audit-bgm-v5.py')
    audit = importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)
    paths = audit.ensure_stems()
    old_proof = json.loads(paths['proof'].read_text())
    assert old_proof['reproduced_mix_matches_approved_file'], 'Original stem graph differs from approved v4 audio'
    approved, params, _ = audit.read_wave(paths['approved'])
    voice, voice_params, _ = audit.read_wave(paths['voice'])
    original, _, _ = audit.read_wave(paths['original'])
    old_loop, _, _ = audit.read_wave(paths['loop'])
    old_ducked, _, _ = audit.read_wave(paths['ducked'])
    total = len(approved); duration = total / SR
    start, end = round(BODY_START * SR), round(BODY_END * SR)
    period = round(PERIOD_BEATS * 60 / BPM * SR)
    overlap = round(OVERLAP_BEATS * 60 / BPM * SR)
    source_start = round(LOOP_START * SR)
    core = original[source_start:source_start + period + overlap].astype(np.float64)
    assert len(core) == period + overlap
    body_count = end-start
    music_body = np.zeros((body_count, 2), dtype=np.float64)
    crossfades = []
    for position in range(0, body_count, period):
        count = min(len(core), body_count-position)
        if position == 0:
            music_body[:count] = core[:count]
            continue
        cross = min(overlap, count)
        phase = np.linspace(0, math.pi/2, cross, endpoint=True)
        music_body[position:position+cross] = (music_body[position:position+cross] * np.cos(phase)[:,None]
                                                + core[:cross] * np.sin(phase)[:,None])
        if count > cross:
            music_body[position+cross:position+count] = core[cross:count]
        crossfades.append({'start': BODY_START+position/SR, 'end': BODY_START+(position+cross)/SR})
    final_loop = old_loop.copy()
    final_loop[start:end] = np.clip(np.rint(music_body), -32768, 32767).astype('<i2')
    loop_path = OUT/'bgm-loop.wav'; save_wave(loop_path, final_loop)
    copied_voice = OUT/'narration.wav'; shutil.copyfile(paths['voice'], copied_voice)
    assert sha(copied_voice) == sha(paths['voice'])
    # Reconstruct the unchanged saved raw voice using the included exact PCM map.
    manifest = json.loads((ROOT/'narration/revision-manifest-v4.json').read_text())
    processed, _, _ = audit.read_wave(ROOT/manifest['processed_master']['path'])
    raw = np.zeros((total, 1), dtype='<i2'); recovered = []
    for placement in manifest['placements']:
        a,b,d,n = (placement[k] for k in ['source_start_sample','source_end_sample','timeline_start_sample','sample_count'])
        assert b-a == n
        raw[d:d+n] = processed[a:b]; recovered.append(processed[a:b])
    assert np.array_equal(np.concatenate(recovered), processed)
    save_wave(OUT/'narration-raw.wav', raw)
    candidate = paths['folder']/'music-repaired-full-mix.wav'
    new_duck_path = paths['folder']/'music-repaired-ducked.wav'
    new_base_path = paths['folder']/'music-repaired-base.wav'
    prelimit_path = paths['folder']/'music-repaired-prelimiter.wav'
    voice_carrier_path = paths['folder']/'narration-stereo-carrier.wav'
    # A 40% dry floor prevents attenuation below -7.96 dB. Slower envelope
    # timing reduces word-by-word pumping while retaining the original voice.
    graph = (f'[0:a]apad=pad_dur=1,asplit=3[side][speech][voiceplain];'
             f'[voiceplain]alimiter=limit=0.841395:level=false,atrim=duration={duration}[voiceout];'
             f'[1:a]apad=pad_dur=1,volume={BODY_MUSIC_GAIN},afade=t=in:st=0:d=1,afade=t=out:st={duration-1.5}:d=1.5,asplit=2[base][music];'
             f'[base]atrim=duration={duration}[baseout];'
             '[music][side]sidechaincompress=threshold=0.018:ratio=4:attack=45:release=650:makeup=1:mix=0.60,asplit=2[duck][mixmusic];'
             f'[duck]atrim=duration={duration}[duckout];'
             '[speech][mixmusic]amix=inputs=2:normalize=0:dropout_transition=0,asplit=2[premix][post];'
             f'[premix]atrim=duration={duration}[premixout];'
             f'[post]alimiter=limit=0.841395:level=false,atrim=duration={duration}[mix]')
    command = ['ffmpeg','-y','-v','error','-i',str(copied_voice),'-i',str(loop_path),'-filter_complex',graph,
               '-map','[baseout]','-ar','48000','-ac','2','-c:a','pcm_s16le',str(new_base_path),
               '-map','[duckout]','-ar','48000','-ac','2','-c:a','pcm_s16le',str(new_duck_path),
               '-map','[premixout]','-ar','48000','-ac','2','-c:a','pcm_s16le',str(prelimit_path),
               '-map','[voiceout]','-ar','48000','-ac','2','-c:a','pcm_s16le',str(voice_carrier_path),
               '-map','[mix]','-ar','48000','-ac','2','-c:a','pcm_s16le',str(candidate)]
    audit.run(command)
    candidate_pcm, _, _ = audit.read_wave(candidate)
    new_duck, _, _ = audit.read_wave(new_duck_path)
    new_base, _, _ = audit.read_wave(new_base_path)
    prelimiter, _, _ = audit.read_wave(prelimit_path)
    voice_carrier, _, _ = audit.read_wave(voice_carrier_path)
    assert len(candidate_pcm) == len(new_duck) == len(new_base) == total
    weight = np.ones(body_count, dtype=np.float64)
    ramp = min(round(OUTER_BLEND_SECONDS*SR), body_count//2)
    curve = .5-.5*np.cos(np.linspace(0, math.pi, ramp, endpoint=True))
    weight[:ramp] = curve; weight[-ramp:] = curve[::-1]
    output = approved.copy()
    output[start:end] = np.rint(approved[start:end].astype(np.float64)*(1-weight[:,None])
                                + candidate_pcm[start:end].astype(np.float64)*weight[:,None]).astype('<i2')
    final_music = old_ducked.copy()
    final_music[start:end] = np.rint(old_ducked[start:end].astype(np.float64)*(1-weight[:,None])
                                     + new_duck[start:end].astype(np.float64)*weight[:,None]).astype('<i2')
    final = OUT/'audio.wav'; save_wave(final, output)
    save_wave(paths['folder']/'music-repaired-final-stem.wav', final_music)
    assert np.array_equal(output[:start], approved[:start]) and np.array_equal(output[end:], approved[end:])
    core_start, core_end = start+ramp, end-ramp
    old_rms, old_peak = audit.windows(old_ducked)
    new_rms, new_peak = audit.windows(final_music)
    loop_rms, _ = audit.windows(final_loop)
    new_base_rms, _ = audit.windows(new_base)
    new_duck_rms, _ = audit.windows(new_duck)
    time = np.arange(len(new_rms))*.1
    body = (time>=BODY_START)&(time<BODY_END)
    interior = (time>=BODY_START+OUTER_BLEND_SECONDS)&(time<BODY_END-OUTER_BLEND_SECONDS)
    old_db, new_db = audit.db(old_rms), audit.db(new_rms)
    ratios = np.divide(new_duck_rms,new_base_rms,out=np.ones_like(new_duck_rms),where=new_base_rms>1e-6)
    ratio_db = audit.db(ratios)
    before_low = audit.spans(body&(old_db < -54), minimum=.5)
    after_low = audit.spans(body&(new_db < -54), minimum=.5)
    after_low_all = audit.spans(body&(new_db < -54), minimum=.1)
    near_silence_max = max((x['duration'] for x in after_low_all), default=0)
    normalized_peak = float(np.max(np.abs(output.astype(np.float64)))/32768)
    prelimit_peak = float(np.max(np.abs(prelimiter.astype(np.float64)))/32768)
    limiter_eligible_frames = int(np.count_nonzero(np.max(np.abs(prelimiter.astype(np.float64)),axis=1)/32768 >= .841395))
    speech_rms, _ = audit.windows(voice_carrier)
    speech_db = audit.db(speech_rms)
    voice_active = body & (speech_db > -32)
    speech_music_gap = speech_db-new_db
    checks = {
        'same_48000_stereo_frame_count': params.nchannels==2 and params.framerate==SR and len(output)==14742400,
        'opening_pcm_exactly_preserved': np.array_equal(output[:start],approved[:start]),
        'ending_pcm_exactly_preserved': np.array_equal(output[end:],approved[end:]),
        'normalized_narration_file_byte_identical': sha(copied_voice)==sha(paths['voice']),
        'raw_narration_all_processed_samples_preserved_once': np.array_equal(np.concatenate(recovered), processed),
        'raw_narration_matches_approved_revision4_hash': sha(OUT/'narration-raw.wav')=='5e50fc591b0bd2fee5cb8dab1f619ef283453222112f27ea5a7fe81af999ce1c',
        'music_gain_change_confined_to_body': np.array_equal(output[:start],approved[:start]) and np.array_equal(output[end:],approved[end:]),
        'no_100ms_music_dropout_in_body': not np.any(body&(new_peak==0)),
        'no_body_music_near_silence_longer_than_half_second': near_silence_max <= .5,
        'new_music_duck_floor_at_least_minus_8_1_db': float(np.min(ratio_db[interior])) >= -8.1,
        'mix_peak_below_original_limiter_ceiling': normalized_peak < .841395,
        'music_repair_does_not_trigger_shared_limiter': limiter_eligible_frames == 0 and prelimit_peak < .841395,
        'narration_has_six_db_headroom_in_95_percent_of_active_speech_windows': float(np.percentile(speech_music_gap[voice_active],5)) >= 6,
    }
    checks = {key: bool(value) for key, value in checks.items()}
    original_envelope, _ = audit.windows(original, seconds=.01)
    envelope_start = round(LOOP_START/.01)
    envelope_end = round((LOOP_START+period/SR)/.01)
    envelope_count = round((overlap/SR)/.01)
    envelope_correlation = float(np.corrcoef(original_envelope[envelope_start:envelope_start+envelope_count],
                                             original_envelope[envelope_end:envelope_end+envelope_count])[0,1])
    core_rms, _ = audit.windows(core.astype('<i2'))
    loop_meta = {'track':'Comprehension / Frank Jonsson','source_sha256':sha(paths['bgm']),
                 'source_start_seconds':LOOP_START,'source_end_seconds':(source_start+period+overlap)/SR,
                 'source_start_sample':source_start,'period_samples':period,'overlap_samples':overlap,
                 'metadata_bpm':BPM,'period_beats':PERIOD_BEATS,'crossfade_beats':OVERLAP_BEATS,
                 'phrase_basis':'128 beats at source metadata113BPM, a32 four-beat-group cycle; one four-beat equal-power overlap. Corresponding overlap RMS envelopes are measured from the original waveform.',
                 'waveform_overlap_envelope_correlation':envelope_correlation,
                 'source_core_rms_dbfs_p05_median_p95':list(map(float,np.percentile(audit.db(core_rms),[5,50,95]))),
                 'source_core_pcm_sha256':hashlib.sha256(core.astype('<i2').tobytes()).hexdigest(),
                 'crossfades':crossfades,'avoided_original_fade_tail_windows':[[127.6,136.8],[263.1,272.2]],
                 'source_music_speed_changed':False,'crossfade_curve':'equal power, cosine/sine'}
    trace=[]
    for i,t in enumerate(time):
        trace.append({'time':round(float(t),3),'before_music_rms_dbfs':round(float(old_db[i]),3),
                      'after_music_rms_dbfs':round(float(new_db[i]),3),'after_raw_loop_rms_dbfs':round(float(audit.db(loop_rms[i])),3),
                      'new_unblended_duck_gain_db':round(float(ratio_db[i]),3)})
    audit_report = {'status':'PASS' if all(checks.values()) else 'REVIEW','checks':checks,
                    'diagnosis':'No missing music PCM, but excessive ducking plus repeated original fade-out tails made the bed nearly disappear.',
                    'decision':'Repair the body using the stable original phrase and bounded, smoother ducking. Keep original opening/ending PCM and complete narration.',
                    'old_duck':{'threshold':.018,'ratio':4,'attack_ms':18,'release_ms':300,'wet_mix':1},
                    'new_duck':{'threshold':.018,'ratio':4,'attack_ms':45,'release_ms':650,'wet_mix':.60,'dry_floor':.40,'theoretical_floor_db':20*math.log10(.4)},
                    'body_music_base_gain':BODY_MUSIC_GAIN,
                    'base_gain_reason':'A conservative bed level is paired with bounded ducking, keeping music continuous without letting the newly restored steady phrase cover quieter narration tails.',
                    'loop':loop_meta,'protected_pcm_seconds':[[0,BODY_START],[BODY_END,duration]],
                    'body_boundary_crossfade_seconds':OUTER_BLEND_SECONDS,
                    'before_body_music_rms_percentiles_dbfs':list(map(float,np.percentile(old_db[body],[5,50,95]))),
                    'after_body_music_rms_percentiles_dbfs':list(map(float,np.percentile(new_db[body],[5,50,95]))),
                    'new_unblended_duck_gain_min_db':float(np.min(ratio_db[interior])),
                    'before_music_below_minus_48_seconds':float(np.count_nonzero(body&(old_db < -48))*.1),
                    'after_music_below_minus_48_seconds':float(np.count_nonzero(body&(new_db < -48))*.1),
                    'before_music_below_minus_54_seconds':float(np.count_nonzero(body&(old_db < -54))*.1),
                    'after_music_below_minus_54_seconds':float(np.count_nonzero(body&(new_db < -54))*.1),
                    'before_near_silence_regions':before_low,'after_near_silence_regions':after_low,
                    'all_after_100ms_near_silence_spans':after_low_all,
                    'maximum_after_near_silence_seconds':near_silence_max,
                    'mix_sample_peak_dbfs':float(audit.db(normalized_peak)),
                    'prelimiter_peak_dbfs':float(audit.db(prelimit_peak)),
                    'limiter_peak_trigger_eligible_frames':limiter_eligible_frames,
                    'limiter_peak_trigger_eligible_frame_percent':limiter_eligible_frames/total*100,
                    'shared_limiter_note':'The complete pre-limiter mix remains below its ceiling, so music does not cause shared gain reduction of narration. Fixed original limiter lookahead is retained.',
                    'speech_music_gap_measurement':'100ms RMS of the stereo narration carrier versus the prepared final stereo music stem, only while narration exceeds -32dBFS.',
                    'speech_minus_music_db_p05_median_p95':list(map(float,np.percentile(speech_music_gap[voice_active],[5,50,95]))),
                    'body_music_louder_than_active_speech_100ms_seconds':float(np.count_nonzero(voice_active&(speech_music_gap<0))*.1),
                    'complete_100ms_trace':trace,'inputs_sha256':old_proof['inputs'],
                    'scope':'Music-only body change; no speech generation, re-timing or voice processing. Objective measurements do not assert subjective listening acceptance.'}
    (OUT/'bgm-audit.json').write_text(json.dumps(audit_report,ensure_ascii=False,indent=2)+'\n')
    config=json.loads((ROOT/'narration/ko.json').read_text())
    validation={'status':'PASS' if all(checks.values()) else 'REVIEW','revision':5,'duration':duration,
                'sample_rate':SR,'channels':2,'samples':total,'audio_sha256':sha(final),
                'voice':config['voice_name'],'voice_id':config['voice_id'],'model_id':config['model_id'],
                'tempo_ratio':manifest['tempo_ratio'],'additional_speed_changes':0,'new_tts':False,
                'narration_sha256':sha(copied_voice),'narration_raw_sha256':sha(OUT/'narration-raw.wav'),
                'approved_revision4_mix_sha256':sha(paths['approved']),'bgm_source_sha256':sha(paths['bgm']),
                'bgm_loop_sha256':sha(loop_path),'bgm_gain':BODY_MUSIC_GAIN,'opening_ending_pcm_exact':True,
                'protected_pcm_ranges_samples':[[0,start],[end,total]],'checks':checks,
                'bgm_audit_sha256':sha(OUT/'bgm-audit.json'),'loop':loop_meta,
                'notes':['Same normalized narration WAV and exact raw voice placement; no atempo or TTS.',
                         'Only the task-body music loop/ducking changes; protected outer audio samples come directly from the approved v4 PCM.',
                         'Both filter inputs have one second zero EOF guard; final duration stays unchanged.']}
    (OUT/'audio-validation.json').write_text(json.dumps(validation,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':validation['status'],'checks':checks,'before_low48_seconds':audit_report['before_music_below_minus_48_seconds'],
                      'after_low48_seconds':audit_report['after_music_below_minus_48_seconds'],'before_low54_seconds':audit_report['before_music_below_minus_54_seconds'],
                      'after_low54_seconds':audit_report['after_music_below_minus_54_seconds'],'new_duck_min_db':audit_report['new_unblended_duck_gain_min_db'],
                      'peak_dbfs':audit_report['mix_sample_peak_dbfs'],'audio':str(final)},ensure_ascii=False,indent=2))
    if not all(checks.values()):
        raise SystemExit(2)


if __name__=='__main__':
    main()
