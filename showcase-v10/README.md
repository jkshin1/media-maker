# R&D 공정 AI Fast Track — Revision10 소스

이 문서는 로컬 재현 절차와 출처 구분을 설명합니다. 제작 완료 여부는 함께 제공되는 `out/showcase-v10/SOURCE_STATUS.json`과 `final-validation.json`으로 확인합니다. 무음 화면 검수의 PASS만으로 최종 음성이나 완성본을 승인하지 않습니다. `package-source.py`는 최종 영상·음성·전체 재생 검수가 통과하기 전에는 최종 ZIP을 만들지 않습니다.

## 원래 화면 디자인과 승인된 실제 타이밍·음성은 별도 기록입니다

`spec.json`은 Revision9에서 바이트 그대로 보존한 **화면 디자인 스냅샷**입니다. 화면·사진·카메라·모션·과제 순서·오프닝·엔딩 디자인은 유지하고, 업무 변화 화면 8개 컷에서 `자료 기준`만 제거했습니다. 단독행은 빈 슬롯을 남겨 다음 행을 움직이지 않았고, 접두어에 붙은 가운뎃점만 함께 제거했습니다. `단일 층 검증`, 담당자 검토, 검증 중, 확정 실적과 후보의 구분, 향후 계획은 유지합니다.

원래 314.5초·9,435프레임으로 만든 문구 삭제 무음본은 별도 기준본으로 보존합니다. 이후 사용자가 새 두 부분 음성의 발화 속도를 유지하면서 컷 시각을 조정하고 +315cents 보정 톤을 적용하는 예외를 승인했습니다. 적용되는 `timeline.json`은 **Revision10의 실제 화면 타이밍**으로, 1920×1080, 30fps, 315초, 9,450프레임·69개 화면이며 마지막 카드 4초를 유지합니다. 승인된 제안의 시각과 정확히 같아야 렌더러가 실행됩니다. 과거 시각과 이동량은 `narration/retime/approved-plan.json`에 남아 있습니다.

기초 자료나 과거 스냅샷 안의 `spoken_text`, `audio_segments`, 원래 Revision9의 원음·엔딩 재사용 참조와 샘플 좌표를 **Revision10의 실제 음성 출처로 해석하면 안 됩니다**. 새 음성의 실제 출처와 샘플 배치는 아래 전용 기록이 기준입니다.

- `narration/ko.json`: `Lot`의 ‘랏’ 발음과 통일된 전달 톤을 반영한 실제 발음 원고입니다. 승인된 68문장과 14개 블록의 내용·순서는 유지합니다.
- `narration/two-parts/authorization.json`: 이번 수정에 한해 사용자가 승인한 두 부분 생성 예외입니다. 일반 기본값인 전체 한 번 생성 규칙을 바꾸는 문서가 아닙니다.
- `narration/retime-tone-authorization.json`: 315초 시각 조정, 승인된 내부 무음 10곳 조정, 발화 속도1 및 +315cents 보정 톤에 대한 별도 사용자 승인입니다. 승인 전 제안서의 해시를 지정합니다.
- `narration/retime/approved-plan.json`과 `independent-review.json`: 새 컷 시각과 원음의 유지 조각을 샘플 단위로 연결한 제안서 및 독립 실행 가능성 검토입니다. 제안서의 원래 `application_authorized:false`는 제안 당시 상태로 보존하며, 실제 적용 권한은 위 별도 승인 문서로 확인합니다.
- `narration/two-part-sources.json`: 33문장·35문장을 각각 연속 생성한 두 원음, 각 전사, 정확한 프롬프트와 가져오기 출처를 지정합니다. 원음은 각 `part*/take.wav`에 보존합니다.
- `narration/placement-manifest.json`: 실제 채택된 두 원음의 로컬 샘플 범위와 고정된 화면 슬롯의 목적지 샘플 범위를 연결합니다. `source_identity_sha256`는 두 원음·전사·프롬프트 출처·승인 기록을 함께 묶습니다.
- `out/showcase-v10/audio-validation.json`과 음성 완결 검수: 실제 믹스에 사용된 상대경로 입력, 68문장의 존재, 단어·파형 경계, 슬롯 적합성과 PCM 보존을 확인합니다.

이전 불완전한 전체 생성본과 시도 기록은 증거로 보존할 수 있으나, 새 두 부분 manifest에 없는 원음을 최종 오디오 입력으로 사용하지 않습니다. 두 파일을 하나의 생성 원음이라고 표시하지 않습니다. 문장별로 새로 생성하거나 음성을 가속하지 않습니다. 낮은 신호만으로 한국어 단어의 끝이라고 판단하지 않습니다. 승인된 내부 무음 10곳은 전사 단어 사이의 낮은 신호 구간이며 총 127,679샘플, 약2.659979초입니다. 엔딩 첫 두 구절과 그 사이380ms는 한 연속 원음으로 유지하고, 그 사이의 화면만 원래 무음 중앙 부근에서 전환합니다. 첫 원음의 끝과 둘째 원음의 시작0·마지막EOF도 보수적으로 보존합니다.

`narration-raw.wav`는 승인된 원음 조각을 PCM 그대로 실제 타이밍에 배치한 결과입니다. `narration.wav`의 +315cents 음높이 보정과 전체 공통 음량 조절은 원본 보존과 별도 처리 단계이며, 원음과 처리된 음성이 PCM 동일하다고 주장하지 않습니다. 처리 설정·출처·정렬은 실제 오디오 처리 manifest와 검수 기록에 보존합니다. 발화 속도는1입니다.

최종 BGM은 `assets/bgm/revision9-approved-music.wav`의 기존314.5초 PCM을 그대로 유지하고 끝에0.5초의 0 PCM만 추가해315초에 맞춥니다. 새 루프·덕킹·페이드를 적용하지 않습니다. 출력명 `bgm-loop.wav`는 이 보존된 최종 음악 스템을 뜻합니다. 최종 카드의 4초는 원음 배치 기준으로 0 PCM입니다. 최종 처리 음성에는 카드 시작 후 약37.33ms의 아주 작은 처리 잔향이 남고 50ms 이후에는 0 PCM이며, 말끝과 잔향을 자르거나 페이드하지 않았습니다.

## 로컬 재현

Node.js, Python3와 NumPy, FFmpeg/FFprobe가 필요합니다. macOS의 저장된 음높이 처리 구현을 다시 실행하는 경우에는 해당 Swift/AVFoundation 환경도 필요합니다. 캔버스 의존성은 `@napi-rs/canvas` 0.1.100이며 글꼴·참고 MD·원본 참고 이미지·사진·BGM·원음·전사·승인된 샘플 매핑과 실제 채택된 처리 입력은 ZIP 안에 포함합니다. 이전 `showcase-v9/` 폴더나 원래 Downloads 경로는 필요하지 않습니다. 새 음성 생성이나 외부 전사는 이 재현 절차에 포함하지 않습니다.

ZIP을 풀고 `showcase-v10/` 안에서 실행합니다.

```sh
npm install
node render.mjs --stills
python3 audio.py
node render.mjs
python3 finish.py
```

`audio.py`는 `mix-v10-audio.py`를 통해 승인된 배치의 원음 PCM을 재현한 다음, `pitch-narration.swift`의 오프라인 AVAudioUnitTimePitch(rate1, +315cents), 전체 공통 정적 gain, 원래 음악 PCM과의 정수 합산 순서로 4개 WAV를 만듭니다. 이 macOS 컴포넌트가 격리된 실행 환경에서 생성되지 않으면 로컬 실행 권한이 필요합니다. 마이크·스피커나 네트워크를 사용하지 않습니다. 필요한 현재 원음의 독립 완결·경계 검수와 승인 계획의 실제 적용이 확인되어야 최종 WAV를 생성합니다. 패키지에 보존된 실제 입력을 사용하며 외부 음성 서비스를 호출하거나 과금하지 않습니다. `finish.py`는 최종 오디오 검수 후 무음 영상의 비디오 스트림을 복사해 합성합니다. 출력은 소스 폴더 옆 `out/showcase-v10/`입니다.

`spec.json`의 과거 metadata는 디자인 스냅샷으로 보존하고, `timeline.json`은 승인된 실제 Revision10 화면 타이밍을 기록합니다. 새 음성의 원본 파일·내부 무음 조정·연속 엔딩 조각·음높이 처리의 출처는 별도 음성 manifest로 확인합니다. `render.mjs`의 출력 대상은 `out/showcase-v10/`입니다.

검수된 음성 입력·출력의 상대경로와 SHA를 확인한 뒤 전체 재생과 최종 검수를 따로 진행합니다. 네이티브 PNG 비교, 전체 디코딩, 음성 내용 확인, 실제 1배속 전체 재생, 사람의 톤·발음 수용 여부는 서로 다른 증거입니다.

## 최종 소스 ZIP과 재현 검증

최종 검수 전에는 아래 첫 명령이 준비 상태만 확인합니다. `--final`은 최종 통과 후 패키징을 명시적으로 실행할 때 사용합니다.

```sh
python3 package-source.py
python3 package-source.py --final
python3 verify-source-package.py
# 재현 보고서만 추가한 재포장 후, 같은 실행 소스임을 다시 확인합니다.
python3 verify-source-package.py --package-only
```

검증기는 `SOURCE_MANIFEST.json`의 전체 파일 SHA·크기·CRC·안전한 경로·서명 URL 잔존 여부를 확인합니다. 새 `/private/tmp/` 폴더에 풀어 이전 프로젝트 폴더 없이 실제 69개 PNG와 `audio.wav`, `narration.wav`, `narration-raw.wav`, `bgm-loop.wav`를 재현하고 파일·PCM SHA를 비교합니다. 전체 동영상 재인코딩이나 전체 재생을 반복했다고 주장하지 않습니다. 같은 호환 캔버스·글꼴·FFmpeg·Python 환경에서의 바이트 재현이며, 실제 런타임 버전은 검수 기록에 남깁니다.

필요하면 `NODE_BINARY`와 `AUDIO_PYTHON` 환경변수로 설치된 실행 파일을 지정할 수 있습니다. 최종 ZIP은 원래 생성 기록의 서명된 미디어 URL을 제거한 사본을 포함하며 원본 파일은 수정하지 않습니다. 음성 빌드가 사용하는 해시 결합 입력은 내보내기 과정에서 바뀌면 실패합니다.

최초 ZIP을 재현한 뒤 검수 보고서만 추가하여 재포장할 수 있습니다. 실행 소스 전체의 안정적인 `immutable_source_identity`가 같아야 이전 재현 결과와 묶습니다. `source-package-validation.json`과 ZIP 자체 해시를 포함하는 납품 보고서는 자기참조를 막기 위해 ZIP에 넣지 않습니다.
