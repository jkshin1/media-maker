# R&D 공정 AI Fast Track 오프닝 v2

첨부한 공통 제작 규칙과 오프닝 명세서를 기준으로 제작한 독립 오프닝입니다. 1920×1080, 16:9, 30fps, H.264/AAC MP4이며 9개 장면으로 구성됩니다.

이번 수정은 R&D 발화 3곳을 **알앤디**로 통일하고, 사용자 원시안의 9개 장면 구도·골드빛·입체감을 직접 참조한 배경 9개로 교체했습니다. 화면에 표시하는 R&D와 승인 문구는 그대로 유지합니다.

완성 길이는 **46초**입니다. 1–8번 장면은 명세의 시간을 유지하고, 9번 장면만 42–45초에서 **42–46초**로 늘렸습니다. 마지막 승인 문장을 원래 속도로 끝까지 읽기 위한 조정이며, CUT05에만 피치를 유지하는 약 1.082787배 조정을 적용했고, 나머지 8개 문장은 원래 속도입니다.

## 실행

Node.js 22.12 이상, Python 3.10 이상, FFmpeg(`ffmpeg`, `ffprobe`), Chrome 또는 Chromium이 필요합니다. FFmpeg와 Python 실행 파일을 PATH에 등록합니다. 포함된 음성·이미지로 재제작하므로 API 키나 원격 생성은 필요하지 않습니다.

프로젝트에서 실행하거나 ZIP의 `opening-v2` 폴더로 이동해 아래 명령을 실행합니다.

```sh
cd opening-v2
npm ci
npm run build
```

출력은 기본적으로 `opening-v2`의 상위 폴더에 있는 `out/opening-v2/rd-ai-fast-track-opening-v2.mp4`입니다. `npm run build`는 21개 장면·전환 샘플의 글자 여백 검사, 전체 프레임 렌더링, 오디오 재믹스, MP4 결합과 디코딩 검증을 실행합니다. 이미 설치된 프로젝트의 루트 `node_modules`가 있다면 이를 사용할 수 있습니다.

Windows에서 Python 명령이 `python`일 경우 PowerShell에서 다음과 같이 지정합니다. Chrome은 기본 설치 위치를 자동 확인합니다.

```powershell
$env:PYTHON = "python"
npm run build
```

자동으로 찾을 수 없는 브라우저는 `CHROME_PATH`에 실행 파일의 전체 경로를 지정합니다. 출력 폴더는 `OPENING_OUT`으로 지정할 수 있습니다.

```sh
CHROME_PATH="/path/to/chrome" OPENING_OUT="/path/to/output" npm run build
```

## 미리보기와 검증

```sh
npm run stills
node render.mjs --serve
```

`--serve`가 출력한 로컬 주소를 브라우저에서 열면 재생·일시정지와 타임라인 이동을 사용할 수 있습니다. HTML은 1920×1080 기준으로 자동 축소되며, 한글은 포함된 폰트로 코드에서 렌더링합니다.

최종 MP4의 실제 연속 재생 검사를 실행하려면 다음 명령을 사용합니다.

```sh
node playback-check.mjs
npm run verify
```

`playback-check.mjs`는 MP4를 처음부터 끝까지 중간 탐색 없이 재생하고, 9개 장면의 재생 중 스크린샷과 오류·종료 이벤트를 저장합니다. 이는 브라우저 디코딩·재생 검증이며 청감 선호도 평가와 구분됩니다.

## 구성과 수정

| 파일/폴더 | 역할 |
| --- | --- |
| `index.html` | 한글·영문 타이틀, 설명, 자막, 글꼴·팔레트 |
| `scenes.js` | 9개 장면과 명시적 시간 기반 카메라·라인·프레임·입자 모션 |
| `spec-checklist.json` | 승인 문구, 장면 시간, 팔레트, 검수 기준 |
| `render.mjs` | Chromium 프레임 렌더와 FFmpeg 영상 인코딩 |
| `audio.py` | 단일 테이크 원본 컷 배치, BGM ducking, 믹스 |
| `build.mjs` | 전체 재실행과 H.264 영상 복사/AAC 결합 |
| `verify.py` | 해상도·프레임·길이·코덱·전체 디코딩·영상 스트림 동일성 검사 |
| `playback-check.mjs` | 완성 MP4의 실제 연속 재생 검사 |
| `assets/` | 시안 참조 배경 9개와 생성 프롬프트·SHA-256 |
| `fonts/` | 포함된 폰트와 공식 라이선스 |
| `narration/` | 생성 원음, 48kHz mono 마스터, 원본 PCM 컷, 전사·검증·출처 |
| `inputs/` | 사용자 첨부 원문 2개와 스토리보드 참고 이미지 |
| `validation/` | 납품 시점의 렌더·오디오·재생·최종 검사 기록 |

모션은 `window.__seek(seconds)`로 계산하므로 같은 시간의 프레임을 다시 렌더링할 수 있습니다. 시안 JPG의 장면 번호와 제작 안내는 참고에만 사용했습니다. 승인 문구는 Markdown을 따릅니다.

## 사용 리소스

배경은 사용자가 다시 첨부한 9개 장면 시안을 직접 참조해 built-in image_gen으로 만든 **개념 이미지 9개**입니다. 각 장면은 지구·일출, 웨이퍼·정밀 장비, 클린룸 연구원, 골드빛 프레임·웨이퍼, 중앙 골드 파동, 12개 패널과 연구원, 동적인 패널·웨이퍼, 입체 상승 그래픽, 웨이퍼·골드 보케로 구성됩니다. 이미지에는 글자·수치·실제 과제 UI를 생성하지 않았습니다.

정확한 프롬프트, 참조 이미지와 출력 이미지 SHA-256은 `assets/prompts-revision-a.json`, `assets/prompts-revision-b.json`에 있습니다. CUT06은 4열×3행의 12개 추상 패널이며, CUT07은 별도 구도입니다. CUT08의 막대·상승 선에는 축·단위·수치가 없으며 실제 데이터나 검증된 성과를 표현하지 않습니다. 사진의 카메라 이동, 빛의 이동과 수렴, 타이틀·자막은 코드로 시간에 맞춰 렌더링합니다.

나레이션은 기존 기본 목소리 Salang과 `eleven_v4`로 R&D 발화 3곳만 알앤디로 바꾼 9개 문장을 한 번에 생성했습니다. 화면 원문 `text`와 발화용 `spoken_text`를 별도로 보존합니다. 로컬 Whisper 전사와 파형 휴지 구간을 함께 확인해 문장별로 나눴습니다. 커넥터가 `stability`와 `similarity_boost` 입력을 지원하지 않아 두 세부 설정은 서비스 기본값으로 생성됐고 정확한 값은 확인되지 않았습니다. 원문·설정·생성 ID·샘플 경계와 제약은 `narration/receipt.json`, `narration/manifest.json`, `narration/README.md`에 기록했습니다.

BGM은 Andrew Ev의 *Mountains* 도입부를 낮은 볼륨으로 사용했고, 발화 중에는 자동으로 음악을 낮춥니다. 출처와 확보한 라이선스 문서는 `narration/bgm/`에 있습니다. 음악은 이 영상 제작에 결합하는 용도이며, 단독 음원으로 재배포하지 마세요. [Mixkit 음악 라이선스](https://mixkit.co/license/modal/musicFree/)와 [이용약관](https://mixkit.co/terms/)을 함께 확인할 수 있습니다.

한글 발음은 `pronunciation_map={"R&D":"알앤디"}`로 기록했습니다. 기본 ASR은 약어를 R&D로 정규화하므로, 추가 한글 표기 전사와 이전 음원 비교 방법·제약을 `narration/README.md`에 공개했습니다.

한글은 Noto Sans CJK KR, 영문 메인 타이틀은 Source Serif 4를 사용합니다. [Noto 공식 라이선스](https://github.com/notofonts/noto-cjk/blob/main/Sans/LICENSE), [Source Serif 공식 라이선스](https://github.com/adobe-fonts/source-serif/blob/release/LICENSE.md) 사본을 포함했습니다.

과제별 본편과 별도 엔딩은 이 패키지의 제작 범위에 포함하지 않았습니다.
