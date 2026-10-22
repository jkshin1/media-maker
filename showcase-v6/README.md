# R&D 공정 AI Fast Track — Revision 6

12개 과제의 타이틀 다음 첫 사진 컷에서 설명과 연결되지 않는 작은 링·십자선·포인터·가이드 선을 제거했습니다. 사진, 제목·담당자, 나레이션, BGM, 컷 순서와 길이는 Revision5 그대로입니다. 이후 기능 설명의 검색·그래프·데이터 연결·계측 동작은 유지합니다.

- 1920×1080 / 30 fps / 9,214 frames / 307.1333333333 seconds
- 오프닝·엔딩, 사진 원본과 기존 사진의 카메라 이동 유지
- Kyung 나레이션과 보완 완료된 BGM을 포함한 전체 AAC를 복사하며 음성을 재생성·재인코딩·재믹싱하지 않음
- 과제 첫 사진 12컷만 변경. 해당 컷에서 다음 컷으로 넘어가는 기존 0.45초 디졸브에도 제거가 반영됨

## 재현

Node.js, Python 3, FFmpeg/FFprobe가 필요합니다. 검수 연락시트 생성에는 Pillow가 필요합니다.

```sh
npm install
python3 audio.py
node render.mjs --stills
node render.mjs
python3 finish.py
node playback-check.mjs
```

출력은 소스 옆 `out/showcase-v6/`입니다. `narration/revision5-approved-audio.m4a`가 승인된 전체 나레이션·BGM이며 `audio.py`는 이를 검증합니다. 타임라인을 다시 계산하거나 기존의 과거 버전 믹스·TTS 스크립트를 실행하지 않습니다.

`baseline-v5/`의 기존 렌더링 함수로 수정 범위를 비교합니다. `revision5-baseline-provenance.json`과 `validation/baseline-v5/`에는 기존 자료의 해시와 음성·BGM 검수 근거가 보존되어 있습니다. 재생 검수는 음소거 1배속 연속 재생이며, 전체 오디오는 별도로 AAC 및 디코딩 PCM이 기존과 정확하게 같은지 검증합니다.

별도 비교 검수: 기존 `showcase-v5/` 원본 폴더가 소스 옆에 보존된 현재 작업 환경에서는 `node review-overlays-v6.mjs`로 원본 파일 보존과 변경 범위를 확인할 수 있습니다. 배포한 소스만 있는 환경의 렌더·오디오 검증은 위 재현 명령으로 실행합니다.
