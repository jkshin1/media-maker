#!/usr/bin/env python3
"""Reconstruct the locked narration clock; apply constant level only, no DSP."""
from pathlib import Path
import hashlib,json,math,re,subprocess,sys,wave
import numpy as np

ROOT=Path(__file__).resolve().parent;BASE=ROOT/'visual-source-v10';OUT=ROOT.parent/'out/showcase-v11'
RATE=48000;SAMPLES=15120000
RAW_SHA='6ffd0cedda626853c222e5c960ac8df862e764cf7e62845075fdc7c6f1663620'
RAW_PCM_SHA='8194f0e68353a3b5a3e8a51a9b743bfd9cb9d7a5247ae2d68a52128b75167ae1'
MUSIC_SHA='f51dc5750fc27dabb13f73e9c96945fee270e13f3bbb4106555b07c021941bfb'
TIMELINE_SHA='8beda6d4a6871df3542f86a1aacf7d4d6912caed99923a90b3725796f6958318'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pcmsha(a):return hashlib.sha256(a.astype('<i2').tobytes()).hexdigest()
def load(p):return json.loads(p.read_text())
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2,default=lambda v:v.item()if isinstance(v,np.generic)else str(v))+'\n')
def read(p,channels):
    with wave.open(str(p))as w:
        assert(w.getframerate(),w.getsampwidth(),w.getnchannels())==(RATE,2,channels)
        return np.frombuffer(w.readframes(w.getnframes()),dtype='<i2').copy().reshape(-1,channels)
def write(p,a):
    with wave.open(str(p),'wb')as w:w.setframerate(RATE);w.setsampwidth(2);w.setnchannels(a.shape[1]);w.writeframes(a.astype('<i2').tobytes())
def measure(p):
    r=subprocess.run(['ffmpeg','-hide_banner','-nostats','-i',str(p),'-af','loudnorm=I=-19.3:TP=-1:LRA=7:print_format=json','-f','null','-'],check=True,capture_output=True,text=True)
    d=json.loads(re.findall(r'\{\s*"input_i".*?\}',r.stderr,re.S)[-1])
    return{k:float(d[k])for k in ['input_i','input_tp','input_lra','input_thresh']}
def main():
    OUT.mkdir(parents=True,exist_ok=True)
    auth=load(ROOT/'authorization.json');baseline=load(ROOT/'baseline-provenance.json');placement=load(BASE/'narration/placement-manifest.json')
    assert auth['authorization_source']=='direct_user_request_in_current_chat'and auth['pitch_shift_cents']==0 and auth['speech_tempo']==1 and auth['pitch_or_time_processor_allowed']is False
    assert sha(ROOT/'timeline.json')==sha(BASE/'timeline.json')==TIMELINE_SHA
    assert placement['piece_count']==77 and placement['spoken_cut_count']==68 and placement['spoken_samples_removed']==0
    inputs=['audio.py','authorization.json','baseline-provenance.json','timeline.json','visual-source-v10/narration/placement-manifest.json','visual-source-v10/narration/two-part-sources.json']
    buffers={}
    for p in placement['source_parts']:
        path=BASE/p['master'];assert sha(path)==p['master_sha256'];buffers[p['part_id']]=read(path,1)
        assert len(buffers[p['part_id']])==p['samples']and pcmsha(buffers[p['part_id']])==p['master_pcm_sha256']
        inputs.append('visual-source-v10/'+p['master'])
    raw=np.zeros((SAMPLES,1),dtype='<i2');last=0
    for p in placement['pieces']:
        a,b=p['source_local_start_sample'],p['source_local_end_sample'];c,d=p['destination_start_sample'],p['destination_end_sample']
        chunk=buffers[p['source_part_id']][a:b];assert last<=c<d<=SAMPLES and len(chunk)==d-c and pcmsha(chunk)==p['pcm_sha256']
        raw[c:d]=chunk;last=d
    assert pcmsha(raw)==RAW_PCM_SHA and not np.any(raw[311*RATE:])
    write(OUT/'narration-raw.wav',raw);assert sha(OUT/'narration-raw.wav')==RAW_SHA==baseline['baseline_raw_sha256']
    musicpath=BASE/'assets/bgm/revision9-approved-music.wav';original_music=read(musicpath,2);assert len(original_music)==15096000
    music=np.zeros((SAMPLES,2),dtype='<i2');music[:len(original_music)]=original_music
    write(OUT/'bgm-loop.wav',music);assert sha(OUT/'bgm-loop.wav')==MUSIC_SHA==baseline['baseline_music_sha256']
    inputs.append('visual-source-v10/assets/bgm/revision9-approved-music.wav')
    original_level=measure(OUT/'narration-raw.wav');target=baseline['baseline_voice_integrated_LUFS'];gain_db=target-original_level['input_i']
    def combine(g):
        voice=np.rint(raw.astype(np.float64)*(10**(g/20))).astype(np.int64)
        return voice,voice+music.astype(np.int64)
    voice,mixed=combine(gain_db);limit=32768*10**(-1/20)
    while max(float(np.max(np.abs(voice))),float(np.max(np.abs(mixed))))>limit:
        gain_db-=.1;voice,mixed=combine(gain_db)
    assert np.max(np.abs(mixed))<32767 and np.max(np.abs(voice))<32767
    voice=voice.astype('<i2');mixed=mixed.astype('<i2')
    write(OUT/'narration.wav',voice);write(OUT/'audio.wav',mixed)
    level=measure(OUT/'narration.wav');mix_level=measure(OUT/'audio.wav')
    assert abs(level['input_i']-target)<=.25 and level['input_tp']<0 and mix_level['input_tp']<0
    assert np.array_equal(mixed.astype(np.int32)-voice.astype(np.int32),music.astype(np.int32))
    assert np.array_equal(voice,np.rint(raw.astype(np.float64)*(10**(gain_db/20))).astype('<i2'))
    assert not np.any(voice[311*RATE:])
    files={n:{'sha256':sha(OUT/n),'pcm_sha256':pcmsha(a),'samples':SAMPLES,'sample_rate':RATE,'channels':a.shape[1]}for n,a in [('narration-raw.wav',raw),('narration.wav',voice),('bgm-loop.wav',music),('audio.wav',mixed)]}
    bindings={n:sha(ROOT/n)for n in inputs}
    report={'revision':11,'status':'PASS','pitch_cents':0,'speech_tempo':1,'tempo':1,'duration_seconds':315,'frames':9450,'sample_rate':RATE,'samples':SAMPLES,
        'no_pitch_processor':True,'no_time_processor':True,'no_filter_or_EQ_or_compressor':True,'no_new_speech_generation':True,
        'source_identity_sha256':placement['source_identity_sha256'],'timeline_sha256':TIMELINE_SHA,'placement_manifest_sha256':sha(BASE/'narration/placement-manifest.json'),
        'constant_voice_gain_db':gain_db,'gain_factor':10**(gain_db/20),'quantization':"np.rint(raw16.astype(float64) * 10**(gain_db/20)).astype('<i2')",
        'target_voice_integrated_LUFS':target,'original_voice_measurement':original_level,'voice_measurement':level,'mix_measurement':mix_level,
        'audio_sha256':sha(OUT/'audio.wav'),'files':files,'input_bindings':bindings,
        'checks':{'77_original_PCM_pieces_exact':True,'raw315s_byte_identical_to_Revision10':True,'same68_source_utterances':True,'same_timeline_bytes':True,
            'no_pitch_time_or_timbre_DSP':True,'voice_exact_raw_times_single_gain':True,'music315s_byte_identical':True,'mix_exact_voice_plus_music':True,
            'no_clipping':True,'voice_level_matches_previous_within_quarter_LU':abs(level['input_i']-target)<=.25,'true_peak_below_zero':mix_level['input_tp']<0,'last4s_voice_literal_zero':True}}
    save(OUT/'audio-validation.json',report)
    save(ROOT/'audio-processing-manifest.json',{k:report[k]for k in ['revision','pitch_cents','speech_tempo','no_pitch_processor','no_time_processor','no_filter_or_EQ_or_compressor','no_new_speech_generation','source_identity_sha256','timeline_sha256','placement_manifest_sha256','constant_voice_gain_db','gain_factor','quantization','files','input_bindings']})
    print(json.dumps({'status':'PASS','pitch_cents':0,'duration':315,'gain_db':gain_db,'voice_LUFS':level['input_i'],'mix_TP':mix_level['input_tp'],'voice_sha256':sha(OUT/'narration.wav')}))
if __name__=='__main__':main()
