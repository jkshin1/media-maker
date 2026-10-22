Revision3의 화면 구도를 유지하면서 요청한 나레이션·과제 표시·서머리 삭제만 반영한 Revision4 소스입니다. 기존 showcase-v3/와 Revision3 영상은 보존합니다.

서머리 네 장면(각6초, 합24초)을 삭제하고 그 시간을 나레이션에 배분합니다. 원본 Kyung 단일 음성을 직접 한 번 처리해 기존보다 약9% 여유 있는 속도로 말하며, 원문과 목소리·피치를 유지합니다. 12과제는 기존 순서대로 이어지고 오른쪽 위에 해당 과제명과 담당자가 표시됩니다. Cubic공정Lab 전용 App&Agent 화면의 (Before)/(After) 보조 표시는 제거합니다.

오프닝·엔딩의 기존 문구, 사진, 색상, 연출과 전체화면 구도는 유지합니다. 발화 컷의 길이만 감속 음성에 맞춰 조정하며, 과제 제목 카드2초·엔딩 전환1초·마지막 우수과제 카드4초를 유지합니다. 전체 목표 길이는 Revision3와 같은307.133333초(30fps,9214프레임)입니다. BGM 원곡과 루프·볼륨·페이드 설정도 유지합니다.

Node.js, Python3와 NumPy/Pillow, FFmpeg/FFprobe가 필요합니다. 전체 재생 검수에는 Chrome 또는 Chromium과 puppeteer-core가 필요합니다. 설치된 브라우저 경로는 CHROME_PATH로 지정할 수 있습니다. 압축을 푼 폴더에서 실행합니다.

```sh
cd showcase-v4
npm install
python3 build-v4-timeline.py
python3 audio.py
python3 validate-final-speech-v4.py
node render.mjs --stills
python3 make-contact-sheets-v4.py
node render.mjs
python3 finish.py
python3 validate-revision4.py
node playback-check.mjs
```

출력은 ../out/showcase-v4/이며 최종 영상은 RD_Process_AI_Fast_Track_Showcase_Revision4.mp4입니다. 저장된 새 연속 음성 및 말끝 근거를 사용하므로 영상 재현에 새 음성 생성이나 외부 전송은 필요하지 않습니다. 원본 음성을 다시 처리하고 단어 경계를 새로 분석하려면 narration-retime-v4.py와 설치된 로컬 Whisper가 필요합니다. 과거 제작·검수 도구는 변경 이력으로 보존하며 위 실행 순서에서는 호출하지 않습니다.

baseline-v3/와 revision3-baseline-provenance.json은 직전 소스의 설정·화면 코드와 원본 해시를 보존합니다. 소스 압축파일에서는 과거 생성 기록의 임시 URL 필드만 제거하며, 지정된 원본/배포본 해시와 제거 필드는 packaged_json_redactions에 기록합니다. 실제 음성·음악·이미지 원본은 보존합니다. 검수 보고서는 음성 내용·말끝·속도, 타임라인, 화면 표기·구도, 완성 영상 재생을 구분해 기록합니다.
