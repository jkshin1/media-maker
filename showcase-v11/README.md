# R&D 공정 AI Fast Track — Revision11 소스

Revision11은 Kyung 원음의 음높이를 유지하는 오디오 수정본입니다. 사용자의 이번 요청에 따라 음높이 보정만 제거하며, 나레이션 문구·읽기 속도·68문장의 순서·315초·9,450프레임·69개 화면·마지막 카드4초·BGM은 유지합니다. 제작 완료 여부는 함께 제공되는 `out/showcase-v11/SOURCE_STATUS.json`과 `final-validation.json`이 기준입니다. 기술 검수는 사람의 음색·발음 수용 여부와 별도입니다.

## 실제 실행 입력과 보존한 과거 소스

`visual-source-v10/`은 Revision10의 실행 소스172개를 보존한 스냅샷입니다. 사진·디자인·원고·타이밍·두 원음과 샘플 배치 기록을 포함합니다. 이 안의 이전 오디오 빌드·음높이 처리 코드와 +315cents 처리 기록은 **과거 자료**이며, Revision11 오디오를 만들 때 실행하지 않습니다. Revision10의 원본 폴더와 완성 영상도 수정하지 않습니다.

Revision11은 이 폴더의 **상위 `audio.py`와 `finish.py`**를 실행합니다. `authorization.json`은 자연스러운 원래 음높이·속도1·전체 공통 정적 음량 조절만 허용한 직접 요청입니다. `baseline-provenance.json`은 스냅샷172개, 고정된 영상과 원음 배치·BGM·타이밍의 해시를 기록합니다. 현재 오디오 manifest와 검수 기록은 실제 사용한 상대경로 입력 및 SHA를 별도로 지정합니다.

`assets/video/locked-silent.mp4`는 검수된 Revision10의 무음 영상입니다. Revision11은 이 파일의 영상 스트림을 그대로 복사해 사용합니다. 기존 화면 코드를 다시 렌더하거나 69개 PNG를 생성할 필요가 없습니다. 화면 디자인·카메라·모션·전환·컷 시각은 이 고정 스트림에 보존됩니다.

## 오디오 보존 범위

새 원음을 생성하거나 음성 서비스를 호출하지 않습니다. 승인된 두 Kyung 원음의77개 조각을 기존 샘플 좌표에 조립한 `narration-raw.wav`는 이전 원음 배치와 PCM·파일 바이트가 같습니다. 두 생성 원음33문장·35문장과 내부 무음 조정·연속 엔딩 구절의 출처는 보존된 배치 기록으로 확인합니다.

`narration.wav`에는 음높이·시간 변환·EQ·압축을 적용하지 않습니다. 전체315초에 하나의 공통 정적 gain만 적용합니다. 원래 원음과 최종 음량 조절 결과는 별도 파일이며 두 PCM이 동일하다고 주장하지 않습니다. `bgm-loop.wav`는 기존315초 BGM과 동일한 PCM을 유지하는 스템 이름입니다. 마지막4초 카드의 원음 나레이션은0 PCM입니다.

## 로컬 재현

Python3·NumPy와 FFmpeg/FFprobe가 필요합니다. 이 오디오 수정본은 Node.js·캔버스·Swift·AVAudioUnit 없이 재현합니다. ZIP을 풀고 **상위 `showcase-v11/` 폴더**에서 실행합니다.

```sh
python3 audio.py
python3 finish.py
```

첫 명령은 저장된 원음·샘플 배치를 읽어 `narration-raw.wav`, `narration.wav`, `bgm-loop.wav`, `audio.wav`를 만듭니다. 두 번째 명령은 고정 영상 스트림을 복사하고 최종 오디오를 AAC로 인코딩합니다. 출력은 소스 폴더 옆 `out/showcase-v11/`입니다. 외부 생성·전사, 네트워크·마이크·스피커는 이 재현 절차에 포함하지 않습니다. 원래 `showcase-v10/` 폴더나 Downloads 경로가 없어도 저장된 입력으로 실행해야 합니다.

## 소스 ZIP 검증

최종 검수와 실행 소스 동결 후에만 최종 패키지를 만듭니다. 기본 호출은 준비 상태만 확인합니다.

```sh
python3 package-source.py
python3 package-source.py --final
python3 verify-source-package.py
# 재현 보고서만 추가한 재포장 후:
python3 verify-source-package.py --package-only
```

검증기는 ZIP 전체 inventory·SHA·크기·CRC·안전한 경로·서명 URL 잔존 여부, 고정 영상과 실제 오디오 입력의 상대경로·SHA를 확인합니다. 새 `/private/tmp/` 폴더에서 상위 `audio.py`를 실행하고 4개 WAV의 파일·PCM 해시를 기존 결과와 비교합니다. 고정 영상 전체 해시와 영상 packet 해시를 확인하며, 전체 영상 재렌더·새69PNG·전체 재생·주관적 청취를 반복했다고 주장하지 않습니다.

과거 생성 기록의 서명된 미디어 URL은 ZIP 사본에서만 제거합니다. 보존한 workspace 원본은 수정하지 않으며, 정확한 원래 해시→내보낸 해시와 삭제 필드 기록으로만 스냅샷 검증 예외를 허용합니다. 실제 오디오 입력이나 영상은 내보내기 과정에서 바뀌면 실패합니다.

`immutable_source_identity`는 내보낸 실행 소스와 저장 입력을 묶습니다. 최초 ZIP의 새 폴더 재현과 보고서만 추가한 최종 ZIP은 이 값이 같아야 합니다. 자기참조를 피하기 위해 최종 ZIP 자체 해시를 포함하는 패키지 검사·납품 보고서는 ZIP 밖에 둡니다. `AUDIO_PYTHON` 환경변수로 NumPy를 설치한 Python을 지정할 수 있습니다.
