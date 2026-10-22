#!/usr/bin/env python3
"""Read-only codec/container/timestamp and unchanged-AAC validation.

No Windows execution or visual-quality claim. Does not modify either MP4.
"""
from pathlib import Path
from fractions import Fraction
from collections import Counter
import datetime, hashlib, json, struct, subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / 'out/showcase-v12'
TARGET = OUT / 'windows10'
SOURCE = OUT / 'RD_Process_AI_Fast_Track_Showcase_Revision12.mp4'
VIDEO = TARGET / 'RD_Process_AI_Fast_Track_Revision12_Windows10_Compatible.mp4'
REPORT = TARGET / 'mp4-validation.json'
SOURCE_SHA = '8554cff5a71b81be36734c18a763f2aa94db36b3198d29984ac815325ffb972b'
TARGET_SHA = '3269304f99f68d5e8b7c3fdbd7544921556e2753cac196e586f971cd3bd02906'
report = {'revision': 12, 'status': 'IN_PROGRESS', 'scope': 'Read-only compatibility derivative technical validation; no Windows10 device or subjective visual/listening validation.', 'checks': {}, 'windows_runtime_tested': False, 'windows_runtime': 'NOT_TESTED_ON_USER_WINDOWS10_PC'}

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''): h.update(b)
    return h.hexdigest()

def run_json(args):
    return json.loads(subprocess.check_output(args, text=True))

def probe(path):
    return run_json(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)])

def packets(path, selector, with_hash=False):
    args = ['ffprobe', '-v', 'error', '-select_streams', selector, '-show_packets', '-show_entries', 'packet=pts,dts,duration,size,pos,flags,data_hash']
    if with_hash: args += ['-show_data_hash', 'sha256']
    return run_json(args + ['-of', 'json', str(path)])['packets']

def check(name, value, detail):
    report['checks'][name] = {'pass': bool(value), 'details': detail}
    if not value: raise AssertionError(name)

class Bits:
    def __init__(self, raw):
        self.data = bytearray(); zeros = 0
        for v in raw:
            if zeros >= 2 and v == 3: zeros = 0; continue
            self.data.append(v); zeros = zeros + 1 if v == 0 else 0
        self.at = 0
    def bits(self, count):
        value = 0
        for _ in range(count):
            assert self.at < len(self.data)*8
            value = (value << 1) | ((self.data[self.at//8] >> (7-self.at%8)) & 1); self.at += 1
        return value
    def ue(self):
        n = 0
        while self.bits(1) == 0:
            n += 1; assert n < 33
        return (1 << n) - 1 + self.bits(n)
    def se(self):
        v = self.ue(); return (v+1)//2 if v & 1 else -(v//2)

def container(path):
    size = path.stat().st_size; top = []
    with path.open('rb') as f:
        offset = 0
        while offset < size:
            f.seek(offset); raw = f.read(8); assert len(raw) == 8
            length, typ = struct.unpack('>I4s', raw); header = 8
            if length == 1: length = struct.unpack('>Q', f.read(8))[0]; header = 16
            if length == 0: length = size-offset
            assert length >= header and offset+length <= size
            row = {'type': typ.decode('ascii'), 'offset': offset, 'size': length, 'header_bytes': header}; top.append(row)
            if typ == b'moov': f.seek(offset+header); moov = f.read(length-header)
            if typ == b'ftyp': f.seek(offset+header); brands = f.read(length-header)
            offset += length
        assert offset == size
    def boxes(raw, start=0, end=None):
        end = len(raw) if end is None else end; rows=[]; n=start
        while n<end:
            z,t=struct.unpack_from('>I4s',raw,n); h=8
            if z==1:z=struct.unpack_from('>Q',raw,n+8)[0];h=16
            if z==0:z=end-n
            assert z>=h and n+z<=end
            payload=raw[n+h:n+z]; name=t.decode('ascii'); row={'type':name,'payload':payload}
            if name in ['trak','mdia','minf','stbl','edts','dinf']: row['children']=boxes(payload)
            if name=='stsd':
                count=struct.unpack_from('>I',payload,4)[0]; row['entries']=boxes(payload,8);assert len(row['entries'])==count
            if name=='avc1': row['children']=boxes(payload,78)
            rows.append(row);n+=z
        assert n==end
        return rows
    tree=boxes(moov)
    def find(rows, name):
        answer=[]
        for r in rows:
            if r['type']==name:answer.append(r)
            answer+=find(r.get('children',[])+r.get('entries',[]),name)
        return answer
    avcc=find(tree,'avcC');assert len(avcc)==1; b=avcc[0]['payload']; assert b[0]==1
    i=6;sps=[];pps=[]
    for _ in range(b[5]&31):n=int.from_bytes(b[i:i+2],'big');i+=2;sps.append(b[i:i+n]);i+=n
    count=b[i];i+=1
    for _ in range(count):n=int.from_bytes(b[i:i+2],'big');i+=2;pps.append(b[i:i+n]);i+=n
    return {'top':top,'brands':brands,'tree':tree,'find':find,'avcc':b,'nal_length':(b[4]&3)+1,'sps':sps,'pps':pps,'avcc_trailing_bytes':len(b)-i}

def parse_sps(nal):
    assert nal[0]&31==7; b=Bits(nal[1:]);r={'profile_idc':b.bits(8),'constraints_byte':b.bits(8),'level_idc':b.bits(8),'sps_id':b.ue()}
    assert r['profile_idc']==66
    r['log2_max_frame_num_minus4']=b.ue();poc=b.ue();r['pic_order_cnt_type']=poc
    if poc==0:b.ue()
    elif poc==1:
        b.bits(1);b.se();b.se()
        for _ in range(b.ue()):b.se()
    r['max_num_ref_frames']=b.ue();r['gaps_in_frame_num_allowed_flag']=b.bits(1);w=b.ue()+1;h=b.ue()+1;frame=b.bits(1);r['frame_mbs_only_flag']=frame
    if not frame:b.bits(1)
    b.bits(1);crop=[0,0,0,0]
    if b.bits(1):crop=[b.ue()for _ in range(4)]
    r.update(coded_width=w*16,coded_height=h*16*(2-frame),crop_offsets=crop,display_width=w*16-2*(crop[0]+crop[1]),display_height=h*16*(2-frame)-2*(2-frame)*(crop[2]+crop[3]))
    return r

def parse_pps(nal):
    assert nal[0]&31==8;b=Bits(nal[1:]);return {'pps_id':b.ue(),'sps_id':b.ue(),'entropy_coding_mode_flag':b.bits(1)}

def pcm(path):
    command=['ffmpeg','-hide_banner','-v','error','-xerror','-err_detect','explode','-i',str(path),'-map','0:a:0','-vn','-sn','-dn','-c:a','pcm_f32le','-f','f32le','pipe:1']
    p=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE);h=hashlib.sha256();n=0
    for b in iter(lambda:p.stdout.read(1048576),b''):h.update(b);n+=len(b)
    errors=p.stderr.read().decode();code=p.wait();assert code==0,errors
    assert n%8==0
    return {'sha256':h.hexdigest(),'bytes':n,'samples_per_channel':n//8,'format':'IEEE754_float32le','sample_rate':48000,'channels':2,'decode_errors':errors}

def main():
    assert VIDEO.exists(),'Await completed derivative, not a partial file'
    original_sha=sha(SOURCE);final_sha=sha(VIDEO)
    report.update(source_file=str(SOURCE),source_sha256=original_sha,video_file=str(VIDEO),video_sha256=final_sha,validator_sha256=sha(Path(__file__)))
    check('exact_current_source_and_completed_derivative_bound',original_sha==SOURCE_SHA and final_sha==TARGET_SHA,{'source_expected':SOURCE_SHA,'derivative_expected':TARGET_SHA,'derivative_bytes':VIDEO.stat().st_size})
    old=probe(SOURCE);new=probe(VIDEO);v=next(x for x in new['streams']if x['codec_type']=='video');a=next(x for x in new['streams']if x['codec_type']=='audio');ov=next(x for x in old['streams']if x['codec_type']=='video')
    check('constrained_baseline_L40_8bit420_1080p30_avc1',v['codec_name']=='h264'and v['profile']=='Constrained Baseline'and v['level']==40 and v['pix_fmt']=='yuv420p'and v['bits_per_raw_sample']=='8'and (v['width'],v['height'])==(1920,1080)and v['r_frame_rate']==v['avg_frame_rate']=='30/1'and v['field_order']=='progressive'and v['has_b_frames']==0 and v['codec_tag_string']=='avc1'and int(v['nb_frames'])==9724,{'stream':v})
    check('only_video_and_original_AAC_LC_stereo',len(new['streams'])==2 and a['codec_name']=='aac'and a['profile']=='LC'and a['sample_rate']=='48000'and a['channels']==2 and a['codec_tag_string']=='mp4a',{'audio_stream':a})
    c=container(VIDEO);top=c['top'];mt=next(x for x in top if x['type']=='moov');md=next(x for x in top if x['type']=='mdat')
    check('ordinary_faststart_MP4_atom_bounds_SPS_PPS_present',mt['offset']<md['offset']and all(x['type']in ['ftyp','moov','free','mdat']for x in top)and len(c['sps'])==len(c['pps'])==1 and c['nal_length']==4 and c['avcc_trailing_bytes']==0 and c['brands'][:4]==b'mp42',{'top_level_atoms':top,'brands_hex':c['brands'].hex(),'avcC_version':c['avcc'][0],'SPS_count':len(c['sps']),'PPS_count':len(c['pps']),'NAL_length_bytes':c['nal_length']})
    sps=parse_sps(c['sps'][0]);pps=parse_pps(c['pps'][0]);check('SPS_main_compatible_baseline_one_reference_PPS_CABAC_disabled',sps['profile_idc']==66 and sps['constraints_byte']&64 and sps['level_idc']==40 and sps['max_num_ref_frames']==1 and sps['frame_mbs_only_flag']==1 and (sps['display_width'],sps['display_height'])==(1920,1080)and pps['entropy_coding_mode_flag']==0 and pps['sps_id']==sps['sps_id'],{'SPS':sps,'PPS':pps,'8x8_transform':'Unavailable in baseline profile'})
    vp=packets(VIDEO,'v:0');op=packets(SOURCE,'v:0');tb=Fraction(v['time_base']);otb=Fraction(ov['time_base']);expected=[Fraction(i,30)for i in range(9724)]
    pts=[int(x['pts'])*tb for x in vp];dts=[int(x['dts'])*tb for x in vp];oldpts=sorted(int(x['pts'])*otb for x in op)
    good=len(vp)==9724 and pts==dts==oldpts==expected and all(int(x['duration'])*tb==Fraction(1,30)for x in vp)and abs(float(v['duration'])-9724/30)<1e-6 and abs(float(new['format']['duration'])-9724/30)<1e-6
    check('all9724_frame_timestamps_exact_original_presentation_times_no_B_reorder',good,{'sample_count':len(vp),'time_base':str(tb),'first_PTS':str(pts[0]),'last_PTS':str(pts[-1]),'frame_duration':'1/30','first_DTS':str(dts[0]),'timestamp_sequence_sha256':hashlib.sha256('\n'.join(str(x)for x in pts).encode()).hexdigest()})
    types=Counter();idr=[];nal_types=Counter()
    with VIDEO.open('rb') as f:
        for index,p in enumerate(vp):
            pos=int(p['pos']);size=int(p['size']);assert md['offset']+md['header_bytes']<=pos and pos+size<=md['offset']+md['size'];f.seek(pos);raw=f.read(size);n=0;slices=[]
            while n<len(raw):
                length=int.from_bytes(raw[n:n+4],'big');n+=4;assert length>0 and n+length<=len(raw);nal=raw[n:n+length];n+=length;kind=nal[0]&31;nal_types[kind]+=1
                if kind in [1,5]:
                    b=Bits(nal[1:]);b.ue();kind_name={0:'P',1:'B',2:'I',3:'SP',4:'SI'}[b.ue()%5];slices.append(kind_name);types[kind_name]+=1
                    if kind==5:idr.append(index)
            assert n==len(raw)and slices
    check('all_access_units_no_B_slices_immediate_IDR_closed_two_second_GOP',types['B']==0 and set(types)<=set(['I','P'])and idr[0]==0 and sorted(set(idr))==list(range(0,9724,60)),{'slice_types':dict(types),'NAL_types':dict(nal_types),'IDR_count':len(set(idr)),'IDR_spacing_frames':60,'first_frame_IDR':True,'all_payload_positions_within_mdat':True})
    ap=packets(VIDEO,'a:0',True);oa=packets(SOURCE,'a:0',True)
    def signature(rows):return [(x['pts'],x['dts'],x['duration'],x['size'],x['data_hash'])for x in rows]
    sig=signature(ap);check('every_original_AAC_packet_payload_and_timing_exact',sig==signature(oa),{'AAC_packet_count':len(ap),'packet_signature_sha256':hashlib.sha256(json.dumps(sig,separators=(',',':')).encode()).hexdigest(),'packet_data_hashes':'ffprobe SHA256 per packet; original and derivative equal'})
    p1=pcm(SOURCE);p2=pcm(VIDEO);check('decoded_original_and_derivative_audio_PCM_byte_exact',p1==p2,{'source':p1,'derivative':p2})
    command=['ffmpeg','-hide_banner','-nostdin','-v','error','-xerror','-err_detect','explode','-nostats','-progress','pipe:1','-i',str(VIDEO),'-map','0:v:0','-map','0:a:0','-f','null','-'];r=subprocess.run(command,capture_output=True,text=True);counts=[int(x.split('=',1)[1])for x in r.stdout.splitlines()if x.startswith('frame=')]
    check('whole324seconds_AV_strict_decode_9724_frames',r.returncode==0 and counts and counts[-1]==9724 and 'progress=end'in r.stdout and not r.stderr.strip(),{'return_code':r.returncode,'decoded_video_frames':counts[-1]if counts else None,'strict_decode_stderr':r.stderr,'progress_end':'progress=end'in r.stdout,'audio_also_decoded':True})
    check('source_and_derivative_unchanged_after_read_only_validation',sha(SOURCE)==original_sha and sha(VIDEO)==final_sha,{'media_writes':0})
    report.update(status='PASS_WITH_WINDOWS_RUNTIME_CAVEAT',limitation='All local technical checks passed. Playback on the company Windows10 computer is untested; codec simplification is a compatibility workaround, not a confirmed diagnosis or device acceptance.',official_support_reference='https://learn.microsoft.com/en-us/windows/win32/medfound/h-264-video-decoder')

if __name__=='__main__':
    try:main()
    except Exception as e:report.update(status='FAIL',error={'type':type(e).__name__,'message':str(e)})
    finally:
        report['updated_at_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat();TARGET.mkdir(parents=True,exist_ok=True);REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':report['status'],'checks':len(report['checks']),'video_sha256':report.get('video_sha256'),'error':report.get('error')},ensure_ascii=False))
    if report['status']=='FAIL':raise SystemExit(1)
