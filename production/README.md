# R&D 공정 AI Fast Track 영상 제작

본 제작 파일은 `production/`과 `out/production/`에 별도로 저장합니다. 승인된 18초 데모의 화면, 원고, 음원과 결과 파일은 기존 위치에 유지합니다.

`production/storyboard.json`의 화면 구성과 `production/narration/ko.json`의 장면 시간을 기준으로 제작합니다. 영상은 1920×1080, 초당 30프레임이며 길이는 241초입니다.

가이드라인은 `concept/1791878315559.png`입니다. 사용자의 후속 편집 요청에 따라 오프닝 0–15초, 과제 소개 15–231초, 별도 엔딩 231–241초로 구성합니다. 12개 과제를 각각 18초씩 소개합니다. 과제 소개의 마지막 두 순서는 장민희 TL과 김지은 TL입니다. 사용자 정정에 따라 연구 Infra 담당자는 곽재오 TL, C&C Inline Data 담당자는 윤지욱 TL로 기록합니다.

각 과제는 제목 2초, BEFORE 4초, AFTER 연결 4초, AFTER 분석 4초, 전후 비교 4초의 다섯 컷으로 설명합니다. BEFORE의 불편과 AFTER의 변화가 서로 연결되도록 구성하며, 수치나 성과는 자료의 기대 효과를 확인된 실적으로 바꾸어 표현하지 않습니다. 과제별 원본 이미지의 내용을 화면과 원고의 근거로 사용합니다. BEFORE에는 과제별 수작업·탐색·대조·측정·검증 동작을 각기 다른 인물과 구도로 표현한 새 사진을 사용합니다. 반복되는 턱을 괴고 고민하는 남성 구도는 사용하지 않습니다. 사진과 생성 프롬프트는 `production/assets/before/`에 보관하며, 원본 concept 이미지는 수정하지 않습니다. AFTER 연결 컷에는 원본의 해당 사진 영역을 CSS로 잘라 사용하고, 이후 분석 컷은 각 과제의 추천·보고서·차트·맵·측정·검토 기능에 맞게 제작합니다. 마지막 컷은 두 열의 BEFORE/AFTER 비교를 유지합니다. 컷 사이는 0.25초 동안 부드럽게 연결합니다.

사용자 요청에 따라 과제 사이의 짧은 NEXT 화면은 표시하지 않습니다. 이전 과제의 본문을 구간 끝까지 보여준 뒤 다음 과제의 전체 제목으로 직접 이어집니다.

시네마틱 오프닝과 엔딩 배경은 built-in `image_gen`으로 생성한 `production/assets/hero.png`, `production/assets/ending.png`입니다. 사용한 전체 프롬프트와 파일 출처는 `production/assets/image-generation.json`에 저장했습니다.

## 나레이션

Salang - Calm, Clear and Warm과 저장된 ElevenLabs 모델, 밝고 자신감 있는 발표 톤, 안정성 75%를 사용합니다. 전체 원고를 하나의 요청으로 생성하고, 단어 경계와 파형의 쉼을 함께 확인한 뒤 나눕니다. 장면마다 별도로 생성하지 않고, 속도를 높이거나 단어를 잘라 시간에 맞추지 않습니다.

```sh
npm run production:prompts
```

반환된 최상위 `generated_prompt`를 ElevenLabs에 한 번 입력합니다. 원본을 48000 Hz 모노 `production/narration/elevenlabs/take.wav`로 보관하고, 원본과 동일한 샘플 구간을 `vo1.wav`부터 순서대로 저장합니다. `manifest.json`에 전체 원고, 모델과 음성 설정, SHA-256, 원본 샘플 경계를 기록합니다. 가져오기 도구는 원본과 잘린 파일의 샘플 일치 및 장면 길이를 검증합니다.

현재 50개 나레이션 블록과 엔딩, 49개 분할 경계의 확인 기록은 `out/production/voice-18s/alignment.json`입니다. 확인된 정렬 기록과 생성 영수증이 함께 준비되었을 때 아래 명령으로 연속 원본의 해당 샘플을 가져옵니다.

```sh
.venv/bin/python scripts/import-production-take.py --voice-dir out/production/voice-18s
```

## 화면과 합성

```sh
npm run production:stills -- --still 1.5,10.5,19,23,27,31,236 --layout-check
npm run production:render
npm run production:audio
```

스틸은 `out/production/stills/`, 무음 영상은 `out/production/video_silent.mp4`, 최종 영상은 `out/production/rd-process-ai-fast-track.mp4`에 생성합니다. 화면은 `production/src/index.html`의 `__ready`와 `__seek(time)`을 사용해 프레임마다 렌더링합니다. 로컬 JSON과 이미지는 실행 중에만 켜지는 127.0.0.1 전용 서버로 읽습니다. `--layout-check`는 선택한 시점에서 보이는 텍스트가 화면이나 부모 영역에서 잘리는지 측정하고 `out/production/layout-check.json`에 저장합니다. 스틸의 시각 검토도 함께 진행합니다.

음성은 전체 배치 후 한 번 음량을 정규화합니다. BGM은 `production/narration/ko.json`에 기록된 곡과 음량을 사용합니다. 현재 곡은 **Mountains / Andrew Ev (Mixkit)**이며 기본 음량 0.18, 엔딩 음량 0.30입니다. 출처와 이용 조건을 함께 기록하고, 기술 소개와 BEFORE/AFTER 변화에 어울리는 보컬 없는 곡을 선택합니다. 원곡보다 긴 영상에서는 기본 3초를 겹쳐 부드럽게 연결하며, `loop_overlap_seconds`로 조절할 수 있습니다. 음성 구간의 자동 음량 감소와 시작·끝 페이드를 적용합니다. 엔딩 음량은 `production/storyboard.json`의 `ending.start`부터 높이므로 편집 길이가 바뀌어도 위치가 맞습니다.

합성 시 화면 스트림을 그대로 복사합니다. 현재 구성의 최종 영상은 241초, 7,230프레임입니다. 최종 영상의 길이, 프레임 수, 오디오 디코딩, 48000 Hz 스테레오 오디오, 화면 스트림 해시를 확인하고 `out/production/audio-validation.json`에 결과를 저장합니다. 화면 구성과 원고 설정의 SHA-256도 기록합니다. 검증된 원본 음성과 단어 경계 기록이 준비되기 전에는 완성본으로 보고하지 않습니다.

화면만 수정할 때는 기존 최종 영상의 검증된 AAC 스트림을 그대로 복사하여 나레이션과 BGM이 바뀌지 않도록 할 수 있습니다. 이전 최종 영상과 `audio-validation.json`, `audio/mix.wav`를 같은 구조로 보존하고, 새 무음 영상 렌더링 후 실행합니다. 이 옵션은 원고 설정과 연속 원본 manifest가 이전과 동일한 경우에만 통과하며, AAC 스트림과 디코딩 PCM이 모두 같은지 확인합니다.

```sh
npm run production:audio -- --preserve-audio-from out/production/versions/241s-before-diversity-original/out/production/rd-process-ai-fast-track.mp4
```

사용자 가독성 편집: BEFORE 사진 자체의 하단 설명 문구를 표시하지 않습니다. 별도 나레이션 자막은 유지합니다. 각 과제 첫 2초 소개 컷은 과제명 84px, 소속·담당자 46px를 사용하고 긴 제목은 의미 단위로 줄바꿈합니다.
