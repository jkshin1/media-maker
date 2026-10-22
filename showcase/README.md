R&D 공정 AI Fast Track 성과공유회 영상의 독립 제작 소스입니다. 기존 `production/` 및 샘플과 별도로 구성했습니다. 입력 자료, 사진 크롭, 폰트, BGM, 연속 나레이션 원본과 14개 원본 음성 컷을 포함합니다.

Node.js, Python 3, PATH에 등록된 FFmpeg·FFprobe가 필요합니다. Node 의존성은 `@napi-rs/canvas` 0.1.100입니다. 배포 ZIP을 같은 폴더 구조로 펼친 뒤 `showcase/`에서 실행합니다.

```sh
npm install
node render.mjs
python3 audio.py
python3 write-subtitles.py
python3 finish.py
python3 validate.py
```

`node render.mjs --stills`로 컷별 검토 이미지를 만들 수 있습니다. 결과 영상·음성·자막과 검증 기록은 `out/showcase/`에 저장됩니다. 최종 MP4의 재생·음성·전환·텍스트 품질은 출력 후 확인해야 합니다. 생성 기록이나 정렬 기록만으로 최종 MP4 검수가 완료된 것은 아닙니다.

현재 장면 렌더러는 빠른 금빛 세로 스윕을 제거하고 첫 화면 이후의 모든 컷 시작에 **0.45초 부드러운 크로스 디졸브**를 적용합니다. 직전 컷의 마지막 화면과 새 컷을 smoothstep 곡선으로 혼합하며, 컷 길이·발화·자막 시간은 유지합니다. 마지막 카드의 미확인 시안 Z-score는 디졸브 전에 가립니다. `finish.py`는 과거 렌더에 필요하면 같은 가림을 적용하고, 검증된 음성을 영상 스트림 복사로 결합합니다. `score-redaction.json`에 가림 범위와 시간이 기록되어 있습니다. Chrome이 설치된 환경에서는 `node playback-check.mjs`로 1배속 전체 재생을 검증합니다.

이미 만들어진 원본 MP4를 수정할 때에는 다음 명령으로 전환 구간만 다시 렌더할 수 있습니다. 이 경로는 원본 MP4가 있어야 하며, 오디오를 AAC 스트림 그대로 복사합니다. 소스 ZIP만으로 재생성할 때는 위의 전체 렌더 명령을 사용하면 됩니다.

```sh
node render-transition-patch.mjs
python3 apply-soft-transitions.py
python3 validate-transition.py
SHOWCASE_VIDEO=RD_Process_AI_Fast_Track_Showcase_Soft_Transitions.mp4 SHOWCASE_REPORT=playback-soft-validation.json SHOWCASE_EVIDENCE=playback-soft node playback-check.mjs
```

재생성에는 포함된 `spec.json`, `timeline.json`, `reference/`, `assets/`, `fonts/`, `narration/`을 사용합니다. Node 의존성을 설치한 뒤에는 새 음성 생성 요청이나 최초 Downloads 첨부 경로 없이 렌더할 수 있습니다. `import-reference.py`는 최초 첨부 반입용이며 기본 경로가 원래 업로드 환경을 가리킵니다. `prepare-assets.py`와 `align.py`는 입력·자산·타이밍을 다시 구성할 때 쓰는 도구입니다. `align.py` 재실행에는 NumPy가 추가로 필요합니다.

현재 타임라인은 1920×1080, 30fps, 8,962프레임, **298.733초**입니다. 과제 타이틀은 각 2초, 서머리는 각 6초이며 엔딩 마지막 카드는 4초 유지합니다. 나레이션은 Kyung의 하나의 연속 테이크에서 가져왔습니다. 원본 `take.wav`와 `vo1.wav`~`vo14.wav`의 PCM을 보존하고, 출력 음성에 피치를 유지하는 **1.244678배 tempo**를 적용해 5분 제한에 맞춥니다. 엔딩의 두 발화 사이에는 검토한 원본 무음 지점에서 1초를 추가합니다.

제작상 변경 및 근거는 다음 파일에 기록했습니다.

- `spec.json`의 `deviations`: MD가 별도 원자료 확인을 요구한 경비 80%, Cubic 90%, TCAD 측정 시간·정확도 수치만 정량 부분을 제외했습니다. 나머지 원고와 기능 범위는 유지했습니다.
- `narration/manifest.json`: 14개 음성 컷의 마스터 샘플 경계, SHA-256, 출력 tempo 및 엔딩 무음 삽입 위치를 기록했습니다. `timeline_trim_*`는 tempo 적용 후 48,000Hz 샘플 좌표이며 원본을 다시 자르는 지시가 아닙니다.
- `narration/alignment-report.json`: 발화 73컷·14블록의 ASR/단어/파형 정렬을 기록했습니다. 문자 coverage는 약 98.5%입니다. Thinfilm의 짧은 조회 컷은 실제 발화에 맞춰 1.4초입니다.
- `narration/transcription/reviews/`: 전문 용어와 일부 한국어 표현에서 ASR 철자 변형이 반복된 4구간의 별도 재인식 자료를 포함합니다. ASR 변형만으로 실제 발음 오류나 정확한 발음을 단정할 수 없어 청취 확인 항목으로 남겼습니다.

`subtitles.ko.srt`와 `subtitles.ko.vtt`는 영상에 표시되는 원문 표기 그대로 73개 발화 자막을 담습니다. 과제명 타이틀, 서머리와 엔딩 무음 장면에는 별도 자막 큐를 넣지 않습니다. 모든 시간은 고정된 영상 프레임 경계에서 내보냅니다.
