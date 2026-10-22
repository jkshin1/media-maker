기존 최종 영상과 소스를 기준으로 만든 2026-10-15 수정본입니다. 원본 showcase/와 기존 최종 영상은 보존합니다. 과제 순서, 확정 MD, 이미지, 색상, 본문·핵심 문구와 Kyung 나레이션 원문 및 BGM을 유지합니다.

이번 변경은 오프닝 4.5초 연장, 완전한 문장 끝을 기준으로 한 음성·화면 경계 수정, Cubic 첫 제목의 (Before) 삭제, 우수과제 팀명 추가, 중복 나레이션 자막 제거입니다. 사용자가 노출 시간을 우선해 5분 초과를 허용했습니다.

음성은 기존 single-take 원본 take.wav를 사용합니다. 기존에 적용했던 FFmpeg atempo=1.244678251425를 한 번 적용하며, 추가적인 재생 속도 변경이나 새 TTS 요청을 하지 않습니다. 완전한 연속 음성에서 14개 문단을 다시 구분해 빠졌거나 다음 과제에 붙었던 마지막 음절을 복원합니다. 이 과정의 PCM은 모두 한 번씩 순서대로 보존하고, 노출 시간과 장면 분리를 위한 무음만 삽입합니다. 과제 내부의 컷 경계에서는 오디오를 다시 시작하지 않습니다.

Node.js, Python 3와 NumPy, FFmpeg/FFprobe가 필요합니다. Node 의존성은 npm install로 설치합니다. 저장된 processed-continuous.wav와 speech-edit-map.json을 사용하면 음성을 다시 처리하거나 인식할 필요 없이 렌더할 수 있습니다.

```sh
npm install
python3 build-revision-timeline.py
python3 audio.py
node render.mjs --stills
node render.mjs
python3 finish.py
python3 validate-final-speech.py
python3 validate-revision.py
node playback-check.mjs
```

출력은 ../out/showcase-v2/에 저장되며 최종 영상 이름은 RD_Process_AI_Fast_Track_Showcase_Revision2.mp4입니다. MP4에는 자막 트랙을 넣지 않으며, SRT/VTT를 새로 내보내지 않습니다. 스토리보드에서 지정한 과제명, 담당자·팀명, 핵심 키워드 및 UI 텍스트는 유지합니다.

활성 배치 기록은 narration/revision-manifest.json, 연속 음성 및 실제 말끝 근거는 narration/speech-edit-map.json입니다. 기존 narration/manifest.json과 vo1.wav~vo14.wav는 과거 분할 증거로 보존하며 수정본의 활성 오디오 배치에는 사용하지 않습니다. baseline/에는 변경 전의 관련 설정과 코드가 있고 baseline-provenance.json에 모든 원본 입력 해시가 있습니다.

원본에서 음성 인식과 경계 분석을 다시 실행하려면 retime-narration.py를 사용합니다. 로컬 Whisper small가 설치된 환경에서만 가능하며, 새 음성을 생성하거나 외부 서비스에 오디오를 보내지 않습니다. 입력·배치·렌더·재생 검증은 별개의 근거이며, 최종 검증 보고서와 실제 화면을 함께 확인해야 합니다.
