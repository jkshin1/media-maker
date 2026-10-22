현재 최종 영상 Revision2의 구도만 수정한 Revision3 소스입니다. 기존 showcase-v2/와 Revision2 영상은 보존합니다.

오프닝·서머리·엔딩에서 자막용으로 남겨 두었던 하단 215px를 본문 화면에 돌려주었습니다. 사진과 배경은 1920×1080 전체를 채우고, 글자·패널·카드는 기존 크기와 비율을 유지하며 세로 중심을 조정합니다. 과제의 AFTER 모니터는 기울기를 포함한 테두리의 중심이 제목 아래 공간 중앙에 오도록 재배치했습니다. BEFORE는 사진 속 실제 모니터에 맞춘 위치를 유지합니다.

문구, 사진 원본, 디자인·색상, 과제 순서, 모든 장면 시작·종료 시점과 전환은 Revision2와 같습니다. 전체 길이는 307.133333초, 30fps, 9214프레임입니다. Kyung 나레이션과 Comprehension BGM은 승인된 Revision2 영상에서 AAC 스트림을 그대로 복사해 narration/approved-mix.m4a에 보관하며, 최종 영상에도 재인코딩 없이 복사합니다. 음성 생성, 속도 조정, 음성 재분할은 하지 않습니다.

Node.js, Python 3와 Pillow, FFmpeg/FFprobe가 필요합니다. 전체 재생 검수에는 설치된 Chrome 또는 Chromium이 필요합니다(다른 설치 경로는 CHROME_PATH로 지정). 압축을 푼 폴더에서 아래 순서로 재현합니다.

```sh
cd showcase-v3
npm install
node render.mjs --stills
python3 make-contact-sheets.py
node render.mjs
python3 finish.py
python3 validate-layout.py
node playback-check.mjs
```

출력은 ../out/showcase-v3/이며, 최종 영상은 RD_Process_AI_Fast_Track_Showcase_Revision3.mp4입니다. 원본 타임라인과 spec을 다시 생성하지 않습니다. audio.py는 승인된 AAC를 검수용 WAV로 디코딩할 때만 사용하며, 최종 영상은 approved-mix.m4a를 직접 사용합니다.

layout-baseline-provenance.json은 변경 전 Revision2 소스 전체 해시, baseline-v2/는 최소 원본 설정과 화면 코드입니다. 기존 baseline/ 및 이전 음성 생성·분할 기록은 과거 근거로 포함했습니다. 이들 과거 제작 도구는 이번 구도 수정의 실행 과정에 사용하지 않습니다. 검증 보고서는 구도, 입력 보존, 오디오 스트림 보존, 프레임·타이밍, 전체 재생을 나누어 기록합니다. 이전 음성의 인식 표기 차이는 이번 수정 범위에서 그대로 유지합니다.

소스 압축파일에서는 과거 생성 기록의 임시 URL 필드만 제거합니다. 원본·배포본 해시와 제거 필드 경로는 layout-baseline-provenance.json의 packaged_json_redactions에 기록하며, 실제 음성·음악·이미지 파일은 보존합니다.
