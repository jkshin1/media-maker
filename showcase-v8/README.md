# R&D 공정 AI Fast Track — Revision 8

현재 상태: 최종 영상 제작·검수 완료. 전체 406.833333초를 정상 속도로 연속 재생했으며 12,205프레임 모두 디코딩됐습니다. 화면·원고·전체 한 번 생성 음성·문장 경계·BGM·최종 AAC 검수 기록을 포함합니다. 소스 압축파일의 독립 재현 범위와 결과는 별도 source-package/source-reproduction 검수 기록에 있습니다.

Revision6을 기준으로 12개 과제의 Before·After·효과와 소개 순서를 사용자의 최신 내용에 맞춰 수정했습니다. 인물·손을 변형한 미채택 Revision7 모션은 사용하지 않습니다.

- 소개 순서: 장민희 → 김도훈 → 권혜선 → 김성후 → 서우석 → 윤지욱 → 김태민 → 오승재 → 박재오 → 이태관 → 정현준 → 김지은
- 김지은 TL 과제 장비명은 사용자 최종 확인에 따라 DD-SEM입니다. 나레이션에서는 계측 데이터로 읽습니다.
- 12개 첫 사진은 승인된 사진 원본을 유지하고 완만한 이동·확대·축소를 적용했습니다. 충분히 긴 일부 컷에서는 같은 사진의 관련 부분 구도를 연결합니다. 사람·손·물건을 휘거나 변형하지 않습니다.
- 기능과 효과 수치는 해당 설명 컷에 표시합니다. 자료 기준, 단일 층 검증, 검증 중, 향후 계획 등 조건을 유지합니다.
- 화면 상단에 과제명·팀·담당자를 표시하며 별도 나레이션 자막과 4개 서머리는 삽입하지 않습니다.
- 기존 오프닝 39초·엔딩 19.033333초의 장면과 노출 시간을 유지합니다. 실제 전체 길이는 406.833333초(12,205프레임, 1920×1080/30fps)이며 사용자가 허용한 5분 초과 조건을 적용했습니다.
- Kyung - Warm, Calm and Clear / eleven_v4 / 한국어 ko로 12개 과제 전체를 한 번에 생성했습니다. 과제별 추가 생성·교체는 적용하지 않았습니다. 문구는 유지하고 한 구절의 쉼표만 보완했습니다.
- 원본 음성은 속도를 바꾸지 않고 정확한 PCM 분할과 문장 경계로 배치했습니다. 마지막 원본 EOF도 보존합니다. ASR의 일부 약어·철자 차이는 실제 원문 변경으로 간주하지 않고 원자료와 검수 기록에 남깁니다.
- BGM은 Comprehension / Frank Jonsson입니다. 기존 보완 방식의 안정적인 반복 구간과 완만한 음량 조절을 유지해 새 본문 길이에 맞췄습니다. 오프닝·엔딩 승인 PCM은 새 AAC 인코딩 직전까지 정확히 보존합니다. 최종 AAC는 새로 인코딩하므로 예전 AAC 패킷과 동일하다고 주장하지 않습니다.

## 원고와 음성 근거

`reference/user-revision8-brief.json`은 최신 사용자 내용이며 `revision8-content.json`은 60개 설명 컷의 원고입니다. `spec.json`, `narration/ko.json`, `narration/tasks-ko.json`은 이를 반영한 제작 설정입니다. 실제 유료 생성 원고는 `narration/tasks-prompt-korean-v8.txt`, 적용 설정은 `narration/generation-korean-settings-v8.json`에 있습니다. 도구에서 노출하지 않는 stability·similarity 값은 적용됐다고 주장하지 않습니다.

`narration/elevenlabs/take.wav`는 하나의 연속 take를 48kHz mono로 가져온 master이며, `vo1.wav`부터 `vo12.wav`는 속도 변경 없는 정확한 샘플 분할본입니다. `manifest.json`에 원본 샘플 경계·해시·원고가 기록됩니다. `narration/transcription-v8-korean/`에 로컬 Whisper 전체 전사와 독립 구간 검수 근거를 보존합니다. 생성 결과의 완료 상태만으로 음성 완전성을 인정하지 않았습니다.

초기 두 take의 누락은 `attempt1-incomplete/`, `attempt2-incomplete/`와 전사 검수 기록에 보존하며 최종 오디오에 사용하지 않습니다. `unused-preparation/`의 과제별 교체 준비안은 사용자가 선택하지 않아 실행하지 않았습니다.

`timeline.json`이 실제 단어·문장 끝과 파형 공백을 대조한 최종 시간표입니다. `timeline-preview.json`과 이름에 `Visual_Review_Silent`가 붙은 MP4는 이전 화면 검토용 추정 타이밍이며 최종 음성 싱크 근거가 아닙니다.

## 재현

Node.js, Python 3와 NumPy, FFmpeg/FFprobe가 필요합니다. 연락시트에는 Pillow가, 전체 재생 검수에는 Chrome과 puppeteer-core가 필요합니다.

```sh
npm install
node render.mjs --stills
node review-content-v8.mjs
node review-camera-v8.mjs --timeline timeline.json
python3 audio.py
node render.mjs
python3 finish.py
node playback-check.mjs
```

출력은 소스 폴더 옆 `out/showcase-v8/`입니다. 포함된 음성·타임라인으로 재현하며 새 유료 음성을 생성하지 않습니다. `finish.py`는 현재 입력의 해시와 검수 상태를 확인한 뒤 영상 스트림을 복사하고 PCM 음성을 AAC로 한 번 인코딩합니다.

새 take의 정렬을 다시 만들 때만 로컬 Whisper 단어 시점 생성 뒤 `align-tasks-v8.py`, `compose-timeline-v8.py`를 사용합니다. 음성을 임의로 자르거나 속도를 올리지 않습니다. 과거 버전 믹스·생성 스크립트는 이력 보존용이므로 실행하지 않습니다.

화면 검수, 음성 완전성·샘플 보존·BGM 검수, 최종 인코딩과 연속 재생, 소스 재현은 각 기록에 검증 범위를 구분합니다. 소리 없는 브라우저 연속 재생은 화면 디코딩 확인이며, 주관적인 청감 승인을 대신하지 않습니다.
