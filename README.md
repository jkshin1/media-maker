# Media Maker

## Git 업로드용 미디어 정리 (2026-10-22)

사용자 요청으로 완성본·중간 렌더 영상 72개와 생성·편집·검토용 작업 이미지 4,682개를 로컬에서 삭제했습니다. 승인본 Revision6, 최신 Revision12 및 Windows 호환 영상도 삭제 대상에 포함됩니다. 아래의 기존 영상 경로와 검증 결과는 정리 전 제작 이력입니다.

코드·대본·설정·프롬프트·검증 기록, 원본 `concept/`·`reference/`·`inputs/` 이미지, 음성·BGM 및 기존 `out/`의 ZIP 소스 묶음은 보존했습니다. `.gitignore`는 영상·이미지·음성·압축파일을 제외합니다. Git으로 받은 사본에는 이 미디어가 없으므로 렌더링 전에 별도 보관한 소스 묶음이나 원본에서 필요한 자산을 복원해야 합니다.

로컬 삭제 목록과 보존 파일 검증 결과는 `out/cleanup-20261022/`에 있습니다. 이 정리 기록은 Git 초기화 전 상태를 기준으로 합니다. 서명된 다운로드 URL이 포함된 서비스 원본 응답과 `*.private.json` 기록도 로컬에만 보존하며 Git에서 제외합니다.

## 현재 R&D 쇼케이스 기준

현재 작업 기준은 **Revision6**입니다. [영상](out/showcase-v6/RD_Process_AI_Fast_Track_Showcase_Revision6.mp4)과 [소스](showcase-v6/README.md)를 사용합니다. 다음 수정에서도 이 버전을 기준으로 하며, 채택 여부와 제외 사항은 [SHOWCASE_STATUS.json](SHOWCASE_STATUS.json)을 확인합니다.

현재 본편은 `production/`에서 R&D 공정 AI Fast Track의 12개 과제를 소개하는 130초 영상으로 제작합니다.
[본편 제작 안내](production/README.md)에 화면 구성, 원고, 단일 테이크 나레이션과 렌더 명령을 정리했습니다.
승인된 18초 소개 샘플은 기존 `src/`와 `assets/narration/`에서 별도로 유지합니다.

## 기본 음성: ElevenLabs Salang

기본 엔진은 **ElevenLabs**, 목소리는 **Salang - Calm, Clear and Warm**,
모델은 **Eleven v4**입니다. 청중에게 발표하는 밝고 자신감 있는 톤을 기본으로 저장했습니다.
원고 앞에 `[bright, confident voice, slightly higher pitch, projecting to an audience]`를 붙이고,
Stability `0.75`, Similarity `0.75`를 사용합니다.
기본 생성 방식은 **`single_take`**입니다. 전체 네 문장을 하나의 요청으로 생성하고,
문장 사이 쉼에서 나눈 음성을 각 장면에 배치합니다. 장면마다 따로 생성할 때 생기는
억양·목소리 높이의 편차를 줄이고 한 발표 흐름을 유지합니다.
이후 음성 생성에도 `assets/narration/ko.json`의 저장된 모델·목소리·발화 설정을 사용합니다.
연결된 Codex 플러그인 또는 같은 계정의 ElevenLabs 웹 TTS로 음성을 생성하고,
WAV와 출처 기록을 프로젝트에 가져옵니다.
`npm run audio`는 가져온 음성을 검증한 뒤 기존 화면에 합성합니다.
터미널 명령이 ElevenLabs를 자동 호출하거나 새 원고를 자동으로 합성하지는 않습니다.

이전 Jeong-Ah 발표 영상과 음성 출처 기록은 `out/versions/jeong-ah-presentation`에 보관합니다.
Jeong-Ah 발표 영상은 `out/smart-process-architecture-ai-agent-presentation.mp4`로도 확인할 수 있습니다.
발표 톤의 v4 음성은 저장된 설정으로 생성하고, 가져온 파일의 원고·모델·목소리·발화 지시를
검증한 뒤 합성합니다. `npm run tts:sample`로 4번 문장을 미리 들을 수 있습니다.
최신 완성 상태와 검증 기록은 `out/local-tts-validation.json`에 남깁니다.

```bash
# 최초 설치: 음성 처리 의존성 설치, 모델 다운로드 없음
npm run tts:setup

# 기존 화면에 준비된 나레이션/BGM을 합성
npm run audio

# 화면까지 새로 렌더링하고 준비된 음성을 합성
npm run build

# 현재 선택한 목소리의 4번 문장 미리 듣기
npm run tts:sample

# 현재 저장된 목소리·모델·설정과 전체 원고의 단일 생성 입력 확인
npm run tts:prompts
```

`uv`, Python 3.11, Node.js와 FFmpeg가 필요합니다.
화면 렌더링에는 Google Chrome도 필요합니다.
공통 음성 처리 의존성과 선택용 Supertonic 실행 의존성은 `requirements-tts.lock`에 고정했습니다.
의존성은 `.venv`, 선택 설치한 로컬 모델은 `.models`, 다운로드 캐시는 `.cache`에 저장됩니다.
기본 엔진은 `assets/narration/ko.json`의 `default_engine`에서 읽으며,
`TTS_ENGINE` 환경 변수 또는 Python 명령의 `--engine`으로 일회성 변경할 수 있습니다.

## ElevenLabs 플러그인 연결

이 Codex 채팅에 연결한 **ElevenLabs 플러그인**으로 한국어 음성을 생성할 수 있습니다.
플러그인 로그인은 이 채팅에서 사용하므로 프로젝트에 API 키를 저장할 필요가 없습니다.
선택한 Salang의 실제 음성 ID는 `mYk0rAapHek2oTw18z8x`입니다.
음성·모델 정보는 `models/elevenlabs.json`에 고정하며 원고 설정과 일치하는지 확인합니다.
Codex에서 새 음성을 생성할 때는 `npm run tts:prompts`가 출력하는 값을 사용합니다.
`generation_mode: single_take`에서는 최상위 `generated_prompt` 전체를 한 번에 사용합니다.
발화 태그는 첫 줄에 한 번만 들어가며, `clips`에는 장면별 원문과 배치 시간을 보관합니다.
원문과 생성용 태그를 구분해 보관하므로 화면 자막에 발화 지시가 들어가지 않습니다.

- [음성 생성 API 문서](https://elevenlabs.io/docs/api-reference/text-to-speech/convert)

플러그인은 원고를 ElevenLabs에 전송하며 음성 생성 시 계정 크레딧을 사용합니다.
터미널의 `npm run audio`는 플러그인을 직접 호출하지 않습니다.
Codex가 플러그인 또는 ElevenLabs 웹 TTS로 생성한 음성을 다음 파일명으로 가져온 뒤
기존 합성 과정을 재사용합니다.

```text
assets/narration/elevenlabs/take.wav
assets/narration/elevenlabs/vo1.wav
assets/narration/elevenlabs/vo2.wav
assets/narration/elevenlabs/vo3.wav
assets/narration/elevenlabs/vo4.wav
assets/narration/elevenlabs/manifest.json
```

```bash
# 4개 음성과 출처 기록이 모두 준비되면 기본 엔진으로 영상 합성
npm run audio

# 다른 디렉터리의 음성 가져오기
.venv/bin/python scripts/tts.py --engine elevenlabs \
  --import-audio-dir /absolute/path/to/voice-clips
```

설정은 `models/elevenlabs.json`, 원고·목소리·장면 타이밍은 `assets/narration/ko.json`에 있습니다.
가져올 음성은 해당 원고와 목소리 설정으로 생성해야 합니다.
음성 파일이 없거나 장면보다 길면 합성을 중단하고 수정할 파일을 알려줍니다.
`manifest.json`에는 `provider`, `model_id`, `voice_id`, `voice_name`과
`voice_settings`(현재 `stability: 0.75`, `similarity_boost: 0.75`),
`generation_mode: single_take`, `source_take`, `clips` 배열을 기록합니다.
`source_take`에는 48000 Hz 모노 마스터의 `file: take.wav`, `sha256`, 전체 `generated_prompt`를 저장합니다.
각 클립은 `id`, 원문 `text`, `delivery_tag`, 마스터와 같은 전체 `generated_prompt`,
`file`(예: `vo1.wav`), `sha256`, `source_take_sha256`,
`source_start_sample`, `source_end_sample`을 가집니다.
샘플 경계는 시작을 포함하고 끝을 제외하며, 클립끼리 겹치면 안 됩니다.
`source_start_ms`, `source_end_ms`를 추가하면 샘플 경계와 일치하는지도 검사합니다.
플러그인이 반환한 `generation_id`, `session_id`도 함께 보관할 수 있습니다.
합성 전 원고·목소리·모델·발화 설정·생성용 태그와 실제 WAV의 SHA-256을 모두 검사합니다.
각 클립의 원본 샘플이 마스터의 지정 구간과 일치하는지 확인하므로,
여러 독립 생성 결과를 하나의 테이크로 기록해 사용할 수 없습니다.
웹 TTS로 생성한 클립은 해당 생성 방식과 내려받은 파일의 출처도 기록합니다.
원고나 음성 설정을 바꾸면 해당 음성을 플러그인 또는 웹 TTS로 다시 생성하고
출처 기록도 갱신해야 합니다.
가져온 음성과 설정이 같으면 처리 결과를 재사용합니다.
일부 문장만 생성된 manifest로는 해당 문장의 미리 듣기는 가능하지만,
전체 영상 합성은 누락된 클립 번호를 안내하고 중단합니다.
이전 문장별 생성 자료는 `generation_mode: per_clip`으로 사용할 수 있으며,
필드를 생략한 이전 manifest도 문장별 방식으로 해석합니다.
현재 기본 설정과 다른 생성 방식은 설정과 출처 기록을 함께 일치시켜야 합니다.

미리 듣기는 기존 4번 클립을 사용하며 `out/comparison/elevenlabs/sample.wav`에 저장합니다.
다른 클립은 `.venv/bin/python scripts/tts.py --sample-clip 1`로 선택할 수 있습니다.

## 기본 BGM: 밝고 현대적인 기업 발표용

기본 BGM은 Lily J의 **Pop Track 03**으로 저장했습니다.
`assets/narration/ko.json`의 `bgm` 설정에 파일 경로·시작 위치·음량을 보관하므로
다음 `npm run audio`와 `npm run build`에도 같은 음악을 사용합니다.
음악 파일은 `assets/bgm/mixkit-pop-track-03-729.mp3`, 출처 기록은 같은 이름의 JSON에 있습니다.
나레이션이 나올 때 음악을 낮추고 마지막 화면에서 음량을 올립니다.

- [Mixkit 음악 출처](https://mixkit.co/free-stock-music/corporate-music/)
- [Mixkit Free Music 라이선스](https://mixkit.co/license/modal/musicFree/)

## 선택 가능한 로컬 음성: Supertonic 3

국내 수퍼톤의 **Supertonic 3 / F3**도 유지합니다.
Apple M4 Pro·메모리 64GB·Python 3.11에서 ONNX Runtime CPU 실행을 확인했습니다.
처음 모델을 받을 때 인터넷이 필요하며 이후 음성 생성은 로컬에서 진행됩니다.

```bash
# 로컬 모델이 아직 없을 때만 다운로드
npm run tts:setup -- supertonic

# Supertonic 음성으로 합성
TTS_ENGINE=supertonic npm run audio

# Supertonic 미리 듣기
TTS_ENGINE=supertonic npm run tts:sample
```

모델 리비전은 `models/supertonic.json`에 고정했습니다.
Supertonic 3는 [수퍼톤 공식 아카이브](https://github.com/supertone-oss-archive/supertonic)에서 받습니다.
2026-09-09에 개발·지원이 종료되었습니다. 코드에는 MIT, 모델에는 OpenRAIL-M 라이선스가 적용됩니다.

## 결과와 검증

- `out/smart-process-architecture-ai-agent-salang-consistent.mp4`: 전체 원고를 한 번에 생성해 장면 사이 톤 편차를 줄인 최신 Salang 영상
- `out/smart-process-architecture-ai-agent-salang.mp4`: Salang 발표 톤과 Pop Track 03 BGM을 적용한 영상
- `out/smart-process-architecture-ai-agent-elevenlabs.mp4`: 현재 기본 ElevenLabs 설정으로 합성한 결과
- `out/smart-process-architecture-ai-agent-presentation.mp4`: 이전 Jeong-Ah 발표 영상
- `out/versions/jeong-ah-presentation/`: 이전 Jeong-Ah 발표 음성과 출처 기록
- `out/smart-process-architecture-ai-agent-supertonic.mp4`: 선택 가능한 로컬 음성 결과
- `out/audio/<engine>/narration.wav`: BGM 없는 나레이션
- `out/audio/<engine>/generation.json`: 음성 설정, 원고, 발화 길이, 가져온 음성 출처 기록
- `out/audio/<engine>/raw/`: 경계 무음을 유지한 원본 음성
- `out/local-tts-validation.json`: 영상 검증 결과

나레이션은 각 장면의 시간 제한과 겹침 여부를 검사합니다.
길이가 넘치는 음성을 잘라내거나 가속하지 않으며, 원고 또는 장면 타이밍을 수정해야 합니다.
최종 화면은 18초·1920×1080·540프레임이며 원본 무음 영상의 화면 스트림을 그대로 복사합니다.
검증은 재생 가능성과 타이밍을 확인하며, 자연스러움은 실제 음성을 듣고 판단합니다.
