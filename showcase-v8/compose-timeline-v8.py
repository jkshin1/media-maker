#!/usr/bin/env python3
"""Combine verified new task timings with the unchanged approved outer scenes."""
from pathlib import Path
import copy,hashlib,json
ROOT=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text())
def main():
 old=load(ROOT/'baseline-v6/timeline.json');body=load(ROOT/'timeline-tasks.json')
 spec=load(ROOT/'spec.json');report=load(ROOT/'narration/elevenlabs/alignment-report.json')
 assert report['script_blocks_covered']==12 and report['script_cuts_covered']==60
 assert report['status'] in ['PASS','PASS_WITH_ASR_VARIANTS'] and body['tempo']==1
 assert report['master_sha256']==hashlib.sha256((ROOT/'narration/elevenlabs/take.wav').read_bytes()).hexdigest()
 assert [s['section_id']for s in body['sections']]==spec['revision8']['task_order']
 opening=[e for e in old['entries']if e['section_id']=='opening'];ending=[e for e in old['entries']if e['section_id']=='ending']
 prefix=opening[-1]['end_frame'];tail_start=ending[0]['start_frame'];body_frames=body['frames']
 def shifted(e,frames):
  row=copy.deepcopy(e)
  for key in ['start_frame','end_frame']:row[key]+=frames
  row['start']=row['start_frame']/30;row['end']=row['end_frame']/30
  return row
 entries=[*copy.deepcopy(opening),*[shifted(e,prefix)for e in body['entries']],*[shifted(e,prefix+body_frames-tail_start)for e in ending]]
 assert len(entries)==87
 assert all(a['end_frame']==b['start_frame']for a,b in zip(entries,entries[1:]))
 audio=copy.deepcopy(body['audio_segments'])
 for a in audio:a['timeline_start']+=prefix/30;a['timeline_end']+=prefix/30
 sections=copy.deepcopy(body['sections'])
 for section in sections:section['start']+=prefix/30;section['end']+=prefix/30
 frames=entries[-1]['end_frame']
 out={**copy.deepcopy(body),'entries':entries,'audio_segments':audio,'sections':sections,'frames':frames,'duration':frames/30,'duration_seconds':frames/30,'allow_over_five_minutes':True,'preview_only':False,'revision':8,'timing_basis':'New single-take Kyung word timestamps and waveform gaps, unmodified source PCM; approved Revision6 opening and ending lengths preserved.','outer_audio':{'approved_file':'narration/revision5-approved-audio.m4a','opening_samples':[0,prefix*1600],'ending_source_samples':[tail_start*1600,old['frames']*1600],'ending_destination_sample':(prefix+body_frames)*1600},'alignment_report_sha256':hashlib.sha256((ROOT/'narration/elevenlabs/alignment-report.json').read_bytes()).hexdigest()}
 (ROOT/'timeline.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'duration':frames/30,'frames':frames,'entries':len(entries),'opening_seconds':prefix/30,'body_seconds':body_frames/30,'ending_seconds':(old['frames']-tail_start)/30}))
if __name__=='__main__':main()
