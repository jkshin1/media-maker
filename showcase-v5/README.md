# R&D 공정 AI Fast Track — Revision 5

과제별 핵심 기능과 동작을 드러내는 화면 구성으로 수정한 버전입니다. 제공된 개별 MD와 이미지 시안, 기존 확정 문구를 기준으로 합니다.

## 유지 범위

- 확정된 `spec.json`, `timeline.json`, 과제 순서, 과제명·담당자명, 오프닝·엔딩 구성
- 1920×1080, 30 fps, 9,214 frames, 307.1333333333 seconds
- Kyung 음성, 나레이션 문구·속도·배치와 문장 끝 보존
- 기존 검정·차콜·골드·앰버 색상, 사진 원본, 제목과 담당자 헤더
- 서머리 4개와 나레이션 중복 자막은 계속 제외

## 변경 범위

`task-visuals-early.js`, `task-visuals-late.js`에 12개 과제의 60개 본문 컷별 구도와 시간 기반 동작을 정의했습니다. 공통 기울어진 모니터 대신 데이터 연계, 문서 탐색, 웨이퍼 비교, 계측, 보고서·메일 등의 과제별 대상을 중심으로 구성합니다. 원본 이미지의 예시 수치를 검증된 성과로 새로 사용하지 않습니다.

음악은 동일한 Comprehension / Frank Jonsson 원곡을 사용합니다. `audit-bgm-v5.py`로 기존 반복 연결과 덕킹을 분리 점검하고, `mix-v5-audio.py`로 본문 음악만 수정합니다. 오프닝·엔딩의 기존 오디오와 나레이션은 보존용 PCM에서 재사용합니다. 상세 측정은 출력 폴더의 오디오 검수 기록을 확인하십시오.

## 재현

Node.js, Python 3, FFmpeg/FFprobe가 필요합니다. 분석 스크립트에는 NumPy, 접촉 시트에는 Pillow가 필요합니다. 음성 생성 서비스 호출은 없습니다.

```sh
npm install
node render.mjs --stills
python3 make-contact-sheets-v4.py
node render.mjs
python3 audio.py
python3 finish.py
```

결과는 이 소스 폴더 옆 `out/showcase-v5/`에 저장됩니다. 기존 타임라인을 다시 계산하거나 TTS를 재생성하지 마십시오.

## 검수

```sh
node review-visuals-v5.mjs
python3 validate-final-speech-v4.py
node playback-check.mjs
```

첫 검수는 보존한 Revision4 렌더링 함수와 원본 해시를 비교하고, 텍스트 범위와 고정 배경에서의 모션 프레임을 기록합니다. 자동 프레임 차이는 미적 판단을 대신하지 않으므로 전체 컷과 최종 영상 검수가 별도로 필요합니다. 마지막 검수는 음소거 상태의 실시간 연속 재생이며 오디오 분석과 분리합니다.

`baseline-v4/`는 비교용 기존 화면 함수입니다. `narration/revision4-approved-audio.wav`와 `revision4-narration.wav`는 정확한 오디오 보존과 독립적인 재현을 위한 원본입니다. 제공된 MD는 제작 근거이며 이후 사용자가 확정한 수정사항(서머리 제거, 담당자 정정, 팀명, 자막 제거, 길이 허용 등)을 되돌리는 지시로 사용하지 않습니다.
