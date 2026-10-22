# R&D 공정 AI Fast Track — Revision 9

확정 타임라인: 05:14.5 / 9,435프레임 / 1920×1080, 30fps. 제작·검수의 최종 상태는 함께 제공되는 `out/showcase-v9/SOURCE_STATUS.json`과 `final-validation.json`을 기준으로 확인합니다.

사용자가 지정한 Revision8을 편집 입력으로 삼았습니다. 이전 승인본 Revision6과 Revision8 원본은 보존하며, 미채택 Revision7의 인물·손·물건 부분 변형 모션은 사용하지 않습니다.

- 원문: `reference/user-revision9-narration.md`; 최종 시각의 나레이션 목록: `reference/final-narration-timeline.md`
- 구성: 오프닝 9개, 과제 55개, 엔딩 4개로 총 68개 발화입니다.
- 목표: 약 5분, 사용자 확인 상한은 315초입니다. 실제 음성 길이에 맞추며 추가 문구 삭제·축약·음성 가속을 하지 않습니다.
- 음성: Kyung - Warm, Calm and Clear / eleven_v4 / 한국어 ko. 새 전체 생성 1회를 실행했습니다. 생성본 엔딩 절단 후 사용자가 이번 수정에 한해 기존 동일 원문 엔딩 재사용 예외를 승인했습니다. 추가 유료 생성은 하지 않았습니다.
- 생성 프롬프트: `narration/generated-prompt.txt`, 서버 확인 설정: `narration/generation-settings-v9.json`. 영문·숫자를 기존 한국어 발음으로 바꾸고 필요한 조사와 쉼표만 발음용으로 정리했습니다. 사용자 원문 68줄은 그대로입니다.
- 첫 문장은 ‘R&D 업무에 AI를 더합니다.’입니다. 소개 순서와 담당자는 최신 사용자 지정을 유지합니다. 박재오 TL, DD-SEM 표기를 적용합니다.
- 과제 타이틀을 첫 사진 컷 안에 함께 보여 별도 무음 타이틀 시간을 추가하지 않습니다. 과제명·팀·담당자는 상단에 계속 표시합니다.
- TCAD·Infra·Monitoring은 4개, 경비는 3개, 다른 과제는 5개 발화에 맞춰 화면을 구성합니다. 각 기능·분석·성과 화면이 해당 문장과 맞도록 연결하며, 자료 기준·검증 중·최종 검증·추가 개발 계획 조건을 유지합니다.
- 완전한 원음이 확보된 뒤 단어와 파형에 근거해 문장 사이의 긴 무음만 조정할 수 있습니다. 발화 속도·발화 샘플은 유지하며 원본과 편집 매핑을 별도로 보존합니다. 현재 불완전 원음에는 편집을 적용하지 않았습니다. 마지막 우수과제 카드에는 별도 노출 시간을 둡니다.
- BGM은 Comprehension / Frank Jonsson을 유지합니다. 원곡 도입부와 안정적인 박자 구간을 연결하고, 완만한 음량 조절과 처음·끝 페이드를 적용합니다.

## 현재 생성 상태

첫 요청의 크레딧 부족은 사용자 보완으로 해소됐고, 허가된 전체 생성 1회를 진행했습니다. 새 원음은 326.08초이나 엔딩 두 번째 문장 중간에서 종료됐으며 마지막 두 문장은 없습니다. 원고는 서버에 끝까지 전달됐음을 확인했습니다. 원본·전체 전사·끝부분 별도 전사와 파형 증거는 `../out/showcase-v9/incomplete-narration-review.json`에 보존했습니다. 완료 상태인 생성 기록만으로 전체 문장의 발화를 승인하지 않습니다.

추가 유료 생성이나 과제별 생성은 실행하지 않았습니다. 무료 재생성은 UI에서 확인되지 않았습니다. 사용자가 기존 동일 문구·Kyung 엔딩을 원래 속도로 재사용하는 예외를 명시적으로 승인했으며, 승인 기록은 `narration/recovery/authorization.json`에 있습니다. 원래 불완전한 새 take는 보존합니다.

`narration/recovery/composite-original.wav`는 새 take의 완결된 오프닝·본문 321.500초와, 가속 전 기존 엔딩 15.620초를 원본 PCM 그대로 연결한 337.120초 원음입니다. 기존 엔딩의 원본·추출 경계·설정·전사는 `narration/recovery/`에 보존했습니다. `recovery-map.json`이 두 출처를 샘플 단위로 연결합니다.

편집 계획은 `narration/elevenlabs/pause-edit-proposal.json`입니다. 실제 단어 경계와 −48dBFS 이하의 긴 무음 중앙만 대상으로 26.620초를 덜어내며, 68문장 보호 구간의 PCM을 그대로 유지합니다. 원래 두 원음 전체를 무조건 보존했다고 주장하지 않습니다. 승인된 잘린 엔딩 교체와 무음만 조정하는 편집은 서로 다른 기록입니다. 독립 승인된 계획을 적용한 working master는 310.500초이고, 마지막 카드 4초를 더한 최종 타임라인은 314.500초입니다. 원음과 68문장 보호 구간은 별도 샘플 매핑으로 검증했습니다.

`timeline-preview.json`과 `visual_preview_silent.mp4`는 사용자가 제시한 예상 시각으로 만든 화면 검토용입니다. 실제 새 음성 싱크나 최종 길이의 근거가 아닙니다. 미검증 음성을 최종본에 사용하지 않습니다.

## 재현 절차

Node.js, Python 3와 NumPy, FFmpeg/FFprobe가 필요합니다. Node 의존성은 `npm install`로 설치합니다. 내장 캔버스와 한국어 글꼴을 사용하며, 전체 재생 확인에는 CUA로 제어하는 Chrome과 로컬 검수 플레이어를 사용합니다.

새 음성은 연결된 ElevenLabs 서비스에서 생성합니다. 로컬 가져오기 도구는 음성을 생성하거나 과금하지 않습니다. 완료된 결과 기록이 저장된 뒤 실행합니다.

```sh
# 보존된 최종 타임라인·검수된 working master로 재현합니다.
node render.mjs --stills
python3 audio.py
node render.mjs
python3 finish.py
python3 check-encoded-audio.py
node playback-cua-check.mjs
# 출력한 localhost 주소를 CUA 브라우저로 열고 처음부터 1배속 검수 재생 버튼을 누릅니다.
python3 validate-final.py
python3 export-narration-timeline.py
python3 package-source.py
```

모든 68문장의 발화와 67개 경계를 승인된 복합 원음·전사·원본 매핑에 대조한 독립 검수 기록이 있어야 `finish.py`가 최종 합성을 허용합니다. 최종 출력은 소스 폴더 옆 `out/showcase-v9/`입니다. 315초를 넘는 경우 자동 가속·원고 축약 대신 실패 상태와 실제 필요한 길이를 기록합니다.

원고·원본 보존, 합성 fixture, 예상 시간 화면 검수는 각각 범위가 다릅니다. 실제 음성·최종 인코딩·전체 재생을 통과하기 전에는 완료된 최종 영상으로 표시하지 않습니다.
