# R&D 공정 AI Fast Track — Revision12 소스

사용자가 선택한 Kyung 회사 행사 발표 톤4번과 음높이를 유지하는1.15배 속도를 적용하는 제작 소스입니다. 12개 과제의 큰 제목·팀·담당자 화면을 이전처럼 각2초의 독립 화면으로 복원하고, 첫 사진 위에서 큰 제목이 빠르게 사라지는 중복 오버레이는 비활성화했습니다. 기존 사진·본문 구성·색상·화면 문구·과제 순서·상단 과제 정보·오프닝과 엔딩 디자인은 유지합니다.

실제 타임라인은324.133333초(5분24.1초), 30fps/9,724프레임이며, 설명68컷·제목12컷·마지막4초 카드의 총81개 화면입니다. 최종 제작 완료와 납품 검수 상태는 소스 폴더 옆 `out/showcase-v12/final-validation.json`, `delivery-validation.json` 및 `SHOWCASE_STATUS.json`이 기준입니다. 소스 파일의 존재나 음성 서비스의 completed 표시는 최종 제작·사람의 청감 수용을 뜻하지 않습니다.

## 음성 출처와 승인

`authorization.json`은 미리듣기4번·약1.15배·최대330초·과제 제목 복원 요청입니다. `narration/two-parts/authorization.json`은 전체 생성이 후반에서 끊긴 뒤 사용자가 이번 수정에 한해33문장+35문장을 각각1회 생성하도록 승인한 기록입니다. 기본 정책 single_take와 이번 예외를 구분합니다.

실제 채택한 원음은 `narration/two-parts/part1/take.wav`(167.68초)와 `part2/take.wav`(170.88초)입니다. 두 파일을 정확한 PCM으로 연결한 `narration/elevenlabs/complete-original.wav`는338.56초의 합성 마스터이며, 한 번에 생성된 단일 원음이라고 주장하지 않습니다. 각 원음의 생성ID·목소리·모델·정확한 프롬프트·원본MP3 및 WAV SHA는 해당 폴더의 import-provenance와 generation-settings에 기록돼 있습니다. 모델은 eleven_v4, 목소리는 Kyung이며 발성 지시는 선택한4번과 같습니다. 연결 도구에서 노출하지 않는 stability 등의 설정을 적용했다고 주장하지 않습니다.

완전한 연속 마스터에 `atempo=1.15`를 한 번 적용한 `complete-tempo1.15.wav`는294.396792초입니다. 이후 음높이 보정·추가 속도 변경·EQ·음성 압축은 적용하지 않습니다. 1.15배 시간 압축 자체는 PCM을 변환하므로 처리 전 원음과 PCM이 같다는 주장은 하지 않습니다.

`narration/two-part-sources.json`은 두 원음과 연속 처리 마스터의 출처를 묶습니다. `narration/placement-manifest.json`은 처리된 마스터14,131,046샘플을 순서대로 한 번씩 전부 보존하는25개 배치를 기록합니다. 단어·휴지 삭제, 누락·중복은0입니다. 과제 안의 음성은 시각 컷마다 재시작하지 않습니다. 제목12개와 마지막 카드는 나레이션0 PCM이며, 필요한 프레임 패딩과 오프닝·엔딩의 기존 최소 노출시간만 추가합니다.

## 문구와 경계 검수

`narration/ko.json`의68개 text/spoken_text는 승인된 원고를 유지합니다. 원속도와1.15배 전체 마스터를 각각 로컬 Whisper로 전사해68문장과 엔딩, 핵심 수치를 확인했습니다. `narration/completeness-review.json`은 이 독립 검토입니다. 기술 용어의 ASR 표기 변형은 원고에 덮어쓰지 않습니다. Lot의 원고 발음은9곳 모두 랏이며, ASR은 LAT/라트 등으로 기록합니다. 사람의 완벽한 발음·음색 수용을 확인했다고 주장하지 않습니다.

`narration/alignment.json`은 현재 처리 마스터의67개 경계를 단어와 파형 양쪽으로 확인합니다. ASR이 다음 단어에 앞의 휴지를 잘못 포함한3곳은 `alignment-reviews/`의 정확한 PCM 지역 파일과 무힌트 재전사로 확인했고, root의 `independent-boundary-review.json`에 별도 재계산 근거를 남겼습니다. 단어 안의 저신호만으로 자르지 않습니다.

앞서 실패한 전체1회 생성은 최종에 채택하지 않았습니다. 그 음성과 만료되는 URL은 납품 소스 ZIP에서 제외하고, 작은 역사적 실패 검토와 별도로 보존한 거절 원음의 전사·SHA만 포함합니다. 기존의 잘린 음성이나 예전 엔딩을 임의로 섞지 않았습니다. Revision7 인물 부분 변형 모션과 Revision10의315cents 음높이 보정도 사용하지 않습니다.

## BGM과 음량

BGM은 기존 Comprehension / Frank Jonsson 원곡입니다. 원곡 속도·113BPM·39초 intro·128beat 루프·4beat 크로스페이드·총gain .125·wet .6 덕킹을 유지하고, 시작2초와 새 영상 끝4초에 페이드를 적용합니다. 이미 덕킹된 구315초 stem을 늘이거나 배속하지 않습니다. float 루프에 gain을 먼저 적용해 중간 정수 변환에서의 불필요한 클리핑을 피합니다.

나레이션은 처리된 마스터 전체에 하나의 정적 gain5.02dB를 적용해 약−19.5LUFS를 유지합니다. 음악과 나레이션의 PCM을 정확하게 더합니다. 기존 보조 목표인 음성 우세6dB의 하위5% 값은5.495dB로 약0.505dB 부족합니다. 사용자 요청의 BGM·음성 정책을 유지하면서 이를 PASS_WITH_BALANCE_CAVEAT와 advisory 항목으로 공개하며,6dB 목표를 통과했다고 주장하지 않습니다. 필수 PCM·클리핑·BGM 무음·덕킹 하한·샘플 배치 검수와 이 보조 지표는 구분합니다.

## 오프라인 재현

Python3/NumPy, FFmpeg/FFprobe, Node.js와 `@napi-rs/canvas`가 필요합니다. 원음·ASR·폰트·사진·설정이 소스에 들어 있어 재생성과 유료 서비스 호출 없이 재현합니다. 기본 출력은 소스 폴더 옆 `out/showcase-v12/`입니다.

```sh
# NumPy를 사용할 수 있는 Python으로 실행
python3 audio.py
npm install
node render.mjs
python3 review-audio.py
python3 finish.py
```

`audio.py`는 저장된 두 원음의 정확한 연결과 연속1.15배 처리의 재현을 감사하고, 확정 배치·정적 음량·원곡 BGM을 조립합니다. `render.mjs`는 실제81개 타임라인을 렌더합니다. `review-audio.py`는 별도 수식으로 PCM·음악 루프·덕킹·F0를 확인합니다. `finish.py`는 믹스를 AAC256k로 한 번 인코딩하고 새 무음 영상과 오디오 패킷을 복사해 최종 MP4를 만듭니다. 전체 AV의 엄격한 디코딩과 인코딩된 오디오·영상 검수는 각 out 보고서에 기록합니다.

원음 연결·타임라인을 다시 계산하려면 저장된 근거로 `prepare-narration.py`, `align.py`, `make-timeline.py`를 순서대로 실행할 수 있습니다. ASR을 새로 실행할 필요는 없습니다. 새 전사가 필요한 경우 설치된 로컬 Whisper를 사용하고, 기존 검토를 다른 원음에 재사용하지 않습니다.

```sh
python3 package-source.py --final
python3 verify-source-package.py
# 검수 보고서만 추가해 재포장한 경우
python3 verify-source-package.py --package-only
```

패키지 검증은 ZIP의 안전한 경로·중복·CRC·SHA·크기와 입력 누락, 비공개 서명 URL 제외를 확인합니다. 새 임시 폴더에서4개 WAV와81개 PNG를 재현해 파일·PCM 해시 및 소스 바이트 불변을 비교합니다. package-only는 같은 immutable source identity의 앞선 재현 결과와 연결하는 검사이며 재렌더·재청취를 뜻하지 않습니다. `AUDIO_PYTHON`과 `NODE_BINARY`로 해당 의존성을 사용할 수 있는 실행 파일을 지정할 수 있습니다. 음성 톤의 최종 수용은 사용자 검토와 별도입니다.
