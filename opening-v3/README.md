# R&D 공정 AI Fast Track 오프닝 v3

독립 오프닝 9개 컷, **46초 · 1920×1080 · 16:9 · 30fps · H.264/AAC MP4**입니다. 블랙·골드·앰버와 원시안의 배경 구도를 유지하면서, 컷마다 실제로 진행하는 금빛 라인·화살표·스캔·패널 점등을 추가했습니다.

사용자의 최신 수정 요청을 우선 적용했습니다.

- 첫 나레이션: **“알앤디 업무에 AI를 더합니다.”**
- R&D 발음 3곳 모두 **알앤디** 유지.
- **나레이션 자막과 하단 띠 제거.** 장면 타이틀과 승인된 보조 문구는 유지.
- 웨이퍼를 감싸는 금빛 라인이 **아래에서 출발해 위로 그려지는 동작**을 CUT04·07에 적용. CUT08에서는 대형 화살촉이 곡선을 따라 실제로 이동.

## 실행

Node.js 22.12 이상, Python 3.10 이상, FFmpeg(`ffmpeg`, `ffprobe`), Chrome 또는 Chromium이 필요합니다. FFmpeg와 Python을 PATH에 등록합니다. 이미지·음성·BGM·폰트를 포함했으므로 재렌더링에는 API 키나 원격 생성이 필요하지 않습니다.

```sh
cd opening-v3
npm ci
npm run build
```

기본 출력은 `../out/opening-v3/rd-ai-fast-track-opening-v3.mp4`입니다. 명령은 9개 컷 모션·자막 제거 검사, 스틸·글자 여백 검사, 모든 프레임 렌더, 오디오 믹싱, MP4 결합, 전체 디코딩 검증을 실행합니다.

Windows의 Python 명령이 `python`인 경우:

```powershell
$env:PYTHON = "python"
npm run build
```

Chrome을 자동으로 찾지 못하면 `CHROME_PATH`에 실행 파일 경로를 지정합니다. `OPENING_OUT`으로 출력 폴더를 바꿀 수 있습니다.

```sh
CHROME_PATH="/path/to/chrome" OPENING_OUT="/path/to/output" npm run build
```

## 미리보기·검사

```sh
npm run stills
node render.mjs --serve
node motion-check.mjs
node playback-check.mjs
npm run verify
```

`--serve`가 출력하는 로컬 주소에서 재생·일시정지·구간 이동을 사용할 수 있습니다. 모션은 `window.__seek(seconds)`로 계산하며, 같은 시점은 같은 프레임으로 재현됩니다.

`motion-check.mjs`는 사진의 카메라 이동을 고정한 상태에서도 9개 컷의 실제 효과가 변하는지 검사합니다. 자막 요소가 없는지도 검사합니다. `playback-check.mjs`는 완성 MP4를 처음부터 끝까지 중간 탐색 없이 재생하고 장면별 화면과 미디어 오류·종료 이벤트를 저장합니다. 자동 재생·전사 검사는 사람의 청감 평가와 구분됩니다.

## 컷별 모션

| 컷 · 구간 | 움직임 |
| --- | --- |
| 01 · 0–3초 | 지구 위 금빛 연결선이 순서대로 진행, 빛의 점 이동, 일출 광원과 카메라 후퇴 |
| 02 · 3–7초 | 웨이퍼 위 스캔 빛 이동, 곡면을 도는 금빛 궤적과 광점 |
| 03 · 7–12초 | 아래에서 위로 이어지는 연결선, 전달되는 빛과 파동 |
| 04 · 12–17초 | 아래에서 출발한 굵은 S자 금빛 라인이 웨이퍼를 감싸며 패널 쪽으로 전진 |
| 05 · 17–22초 | 양쪽에서 수렴하는 금빛 파동·입자, 순차 등장하는 타이틀과 반사광 |
| 06 · 22–28초 | 12개 패널이 아래 행부터 순차 점등, 위로 전진하는 연결선과 테두리 광점 |
| 07 · 28–35초 | 전경에서 출발해 위로 감기는 금빛 궤적·동반 선·입자, 패널 반사광 |
| 08 · 35–42초 | 실제로 상승하는 대형 금빛 화살촉과 누적 리본, 막대 표면의 순차 상승 빛 |
| 09 · 42–46초 | 웨이퍼 표면 스캔·회전 광점·입자 이동, 타이틀 등장과 빛 변화 |

CUT04·07·08은 원래 사진의 고정된 금빛 궤적을 제거한 배경 위에 코드로 움직이는 빛을 그립니다. 원본 사진과 편집본을 모두 보존했습니다. 패널 수는 승인된 12개 과제에 해당하며, 축·단위·성능 수치·실제 과제 UI는 추가하지 않았습니다.

## 소스 구성

| 파일/폴더 | 역할 |
| --- | --- |
| `index.html` | 코드로 렌더하는 한글·영문 타이틀, 보조 문구, 폰트·색상 |
| `scenes.js` | 9개 컷의 시간·카메라·광선·입자·점등·타이틀 모션 |
| `hero-effects.js` | CUT08의 이동 화살촉·금속 리본·막대 반사광 |
| `spec-checklist.json` | 승인 문구와 사용자 수정, 타이밍, 검수 기준 |
| `render.mjs` | Chromium 프레임 캡처·FFmpeg 인코딩 |
| `audio.py`, `build.mjs`, `verify.py` | 오디오 배치·믹스, 영상 결합, 검증 |
| `motion-check.mjs`, `playback-check.mjs` | 물체/효과 모션 및 완성 MP4 연속 재생 검사 |
| `assets/` | 원시안 기반 배경, 움직이는 라인용 편집 배경, 프롬프트·출처·SHA-256 |
| `fonts/` | 한글 Noto Sans CJK KR / 영문 Source Serif 4와 라이선스 |
| `narration/` | 단일 테이크 원음, PCM 마스터·원본 컷, 대본·전사·검증·출처 |
| `inputs/` | 사용자 첨부 명세·참고 시안 |
| `validation/` | 납품 시점 검증 결과와 대표 화면 |

## 음성·리소스

Salang 목소리와 `eleven_v4`의 밝고 자신 있는 발표 톤으로 9개 문장을 한 번에 생성했습니다. 첫 문장의 ‘현업’을 ‘업무’로 바꾸고, 발화용 R&D는 ‘알앤디’로 표기했습니다. 원음에서 자른 컷의 정확한 샘플 경계·SHA-256과 타임라인 속도 조정은 `narration/manifest.json`에 기록했습니다. 로컬 Whisper로 문장 포함 여부를 확인하고 파형의 휴지 구간과 함께 경계를 검토했습니다. 전사상의 표기 차이와 지원되지 않는 서비스 설정의 한계는 `narration/README.md`와 `receipt.json`에 기록했습니다.

길이는 이전 수정본과 같은 46초입니다. CUT01–08은 첨부 명세의 시간을 유지하고, CUT09만 42–46초입니다. BGM은 Andrew Ev의 *Mountains* 도입부이며 발화 중 볼륨을 낮춥니다. 음원은 영상 제작에 결합하는 용도입니다. [Mixkit 음악 라이선스](https://mixkit.co/license/modal/musicFree/)와 [이용약관](https://mixkit.co/terms/) 사본·출처를 `narration/bgm/`에 포함했습니다.

배경은 개념 이미지이며 실제 현장·제품 화면을 증명하는 자료가 아닙니다. 생성·편집 프롬프트와 입력/출력 해시는 `assets/`의 JSON에 있습니다. 모든 한글 문구는 이미지 생성 없이 코드로 구현했습니다. 폰트의 [Noto 공식 라이선스](https://github.com/notofonts/noto-cjk/blob/main/Sans/LICENSE)와 [Source Serif 공식 라이선스](https://github.com/adobe-fonts/source-serif/blob/release/LICENSE.md) 사본을 포함했습니다.

기존 본편·샘플과 v2는 별도 보존했습니다. 이 패키지는 오프닝만 제작합니다.
