# R&D 공정 AI Fast Track — Revision 7

과제 12개의 첫 사진 컷에 기존 사진의 손·팔·문서 영역을 조금씩 움직이는 2.5D 애니메이션을 추가했습니다. 기존 사진만 사용하는 연속 메시 변형이며 AI 이미지/영상 생성, 생성형 콘텐츠 합성, 인물 교체, 장식 오버레이는 없습니다. 나레이션·BGM·타이밍·제목·기능 설명 화면·오프닝·엔딩을 유지합니다.

- 1920×1080 / 30 fps / 9,214 frames / 307.1333333333 seconds
- 첫 사진 12컷에서만 동작합니다. 다음 컷으로 넘어가는 기존 0.45초 디졸브에도 반영됩니다.
- 사진 원본은 수정하지 않습니다. 원래 자세에서 시작해 작은 업무 동작을 하고 원래 자세로 복귀합니다.
- 실제 손가락 타이핑·표정·새 시점 등을 생성하지 않습니다.
- 전체 승인 AAC의 패킷과 디코딩 PCM을 그대로 복사해 보존합니다.

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

출력은 소스 옆 `out/showcase-v7/`입니다. `narration/revision5-approved-audio.m4a`는 나레이션과 BGM을 포함한 승인된 전체 AAC입니다. 타임라인을 재계산하거나 과거 버전의 TTS/믹스 스크립트를 실행하지 않습니다.

`photo-motion-*.json`은 1254×1254 원본 사진의 정규화된 좌표, 이동량, 보호 영역입니다. `photo-motion.js`는 촬영된 픽셀을 시간에 따라 연속 변형합니다. `assets.freezeTaskBackground`로 카메라 확대를 멈춰도 손·팔의 움직임은 유지됩니다. `assets.photoMotion=false`로 새 움직임만 끌 수 있습니다.

`baseline-v6/`와 `revision6-baseline-provenance.json`에 직전 버전의 렌더 코드와 파일 해시가 보존됩니다. 별도 범위 검수 `node review-photo-motion-v7.mjs`는 인접 `showcase-v6/`가 있는 원래 작업 환경에서 수행합니다. 위의 렌더·오디오 재현 명령은 해당 폴더 없이도 실행됩니다.

재생 검수는 음소거 1배속 연속 재생입니다. 오디오는 AAC 패킷 및 디코딩 PCM의 정확한 동일성으로 별도 검증합니다.
