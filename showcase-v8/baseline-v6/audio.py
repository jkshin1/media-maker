#!/usr/bin/env python3
"""Verify the complete approved Revision5 AAC; do not rebuild or mix audio."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parent
OUT=ROOT.parent/'out/showcase-v6'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def audio_hash(p,decode=False):
 args=['ffmpeg','-v','error','-i',str(p),'-map','0:a:0']
 args+=['-ar','48000','-ac','2','-c:a','pcm_s16le'] if decode else ['-c:a','copy']
 return subprocess.check_output(args+['-f','hash','-hash','sha256','-'],text=True).strip()
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 provenance=json.loads((ROOT/'narration/revision5-approved-audio-provenance.json').read_text())
 file=ROOT/provenance['approved_aac_file'];tl=json.loads((ROOT/'timeline.json').read_text())
 meta=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(file)]))
 a=meta['streams'][0]
 checks={'approved_aac_file_hash_matches':sha(file)==provenance['approved_aac_file_sha256'],
  'exact_approved_aac_packets':audio_hash(file)==provenance['aac_packet_payload_hash'],
  'exact_approved_decoded_pcm':audio_hash(file,True)==provenance['decoded_48000_stereo_s16le_hash'],
  'aac_48000_stereo':a['codec_name']=='aac' and a['sample_rate']=='48000' and a['channels']==2,
  'locked_audio_duration':abs(float(meta['format']['duration'])-tl['duration'])<2/30}
 report={'status':'PASS' if all(checks.values()) else 'FAIL','revision':6,'checks':checks,'method':'Copy the complete approved Revision5 AAC without re-encoding.','new_tts':False,'mix_changed':False,'voice_speed_changed':False,'narration_changed':False,'bgm_changed':False,'duration':tl['duration'],'source_audio_file':provenance['approved_aac_file'],'approved_aac_file_sha256':sha(file),'aac_packet_payload_hash':provenance['aac_packet_payload_hash'],'decoded_48000_stereo_s16le_hash':provenance['decoded_48000_stereo_s16le_hash'],'baseline_audio_validation':'validation/baseline-v5/audio-validation.json','baseline_speech_validation':'validation/baseline-v5/final-speech-review.json'}
 (OUT/'audio-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'status':report['status'],'checks':checks}))
 assert all(checks.values())
if __name__=='__main__':main()
