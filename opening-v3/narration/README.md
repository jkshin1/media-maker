# 오프닝 v3 오디오 소스 및 검증

첫 문장을 **알앤디 업무에 AI를 더합니다.**로 수정한 최종 오디오입니다. 다른 8문장, R&D의 한글 발음 입력 **알앤디**, Salang 목소리, BGM, 46초 장면 구간은 유지했습니다. 기존 `opening/`, `opening-v2/` 및 해당 출력은 보존했습니다.

## 재실행

Python 3.9 이상과 FFmpeg가 PATH에 있으면 추가 Python 패키지나 API 키 없이 재실행할 수 있습니다.

```sh
# 프로젝트 루트에서
python3 opening-v3/audio.py

# opening-v3 폴더만 별도로 옮긴 경우
python3 audio.py --output ./output
```

출력은 `audio.wav`, `narration.wav`, `narration-raw.wav`, `audio-validation.json`입니다. 미리보기용 `narration/mix.wav`도 동일한 최종 PCM으로 갱신됩니다. 이 스크립트는 원격 음성 생성이나 업로드를 하지 않습니다.

저장된 전사·파형 근거로 원본 PCM 컷과 manifest를 다시 검증하려면 다음 명령을 실행합니다.

```sh
python3 opening-v3/narration/align.py
```

## 최종 단일 테이크

- 서비스: ElevenLabs Creative Studio
- 목소리: Salang - Calm, Clear and Warm, `mYk0rAapHek2oTw18z8x`
- 모델: `eleven_v4`
- 최종 generation ID: `oMWZdjpos5wtbdkjYn8B`
- 원본: `source.mp3`, **40.32초**
- 편집 기준 마스터: `take.wav`, 48000 Hz mono PCM16
- 원본 컷: `vo1.wav`–`vo9.wav`; 이 한 개 최종 마스터의 기록된 샘플 범위와 PCM이 정확히 일치
- 최종 테이크 소모: 424 credits
- 생성·설정·스크립트: `receipt.json`, `ko.json`
- SHA-256·샘플 경계·검증: `manifest.json`

`text`에는 화면 자막 원문을, `spoken_text`에는 R&D를 알앤디로 바꾼 발화 문구를 저장했습니다. 첫 문장의 현업만 업무로 수정했으며 다른 8개 승인 문구는 변경하지 않았습니다. delivery tag는 전체 프롬프트 앞에 한 번만 넣었습니다. 기존의 밝고 자신감 있는 전달에 `clear Korean diction, precise consonants`를 추가해 재녹음했습니다.

Creative Studio 커넥터는 저장된 stability와 similarity_boost를 노출하지 않습니다. 동일 목소리·모델·언어와 delivery tag를 사용했지만 두 수치의 실제 기본값은 독립적으로 확인할 수 없다는 제약을 receipt에 기록했습니다.

## 음성 검증

설치된 로컬 OpenAI Whisper small로 새 최종 마스터를 정답 프롬프트 없이 전사했습니다.

- 첫 문장에 **업무**가 확인되고 현업은 없습니다.
- CUT02가 **더 나은 R&D 공정을 위한 변화가 시작됩니다.**로 전사되었습니다.
- 9문장 전체와 마지막 **소개합니다**를 확인했습니다.
- 8개 경계를 단어·문장 타임스탬프와 파형 휴지 구간으로 검증했습니다.
- 6–7번 경계의 근사 타임스탬프는 정확한 컷 샘플에서 시작하는 별도 전사로 7번 첫 단어와 문장 전체 보존을 확인했습니다.
- 9개 원본 컷은 마스터 샘플과 정확히 일치합니다.

기본 전사는 알앤디를 R&D로 정규화하고 업무에를 업무의로 표기하는 등 ASR 표기 차이가 있으므로 글자 단위로 완벽한 ASR이라고 주장하지 않습니다. 승인된 화면·발화 문구는 별도로 정확히 보존했습니다.

## 최종 배치

장면 구간은 0–3, 3–7, 7–12, 12–17, 17–22, 22–28, 28–35, 35–42, 42–46초입니다. **모든 문장을 원래의 1.0배 속도**로 배치했습니다.

| CUT | 실제 발화 배치 (초) |
| --- | --- |
| 01 | 0.120–2.542 |
| 02 | 3.180–6.587 |
| 03 | 7.250–11.483 |
| 04 | 12.300–15.514 |
| 05 | 17.040–21.741 |
| 06 | 22.250–27.252 |
| 07 | 28.450–33.271 |
| 08 | 35.400–40.538 |
| 09 | 42.150–45.903 |

최종 믹스는 **46.000초, 48000 Hz stereo PCM16**, **−17.14 LUFS / −4.95 dBTP**입니다. FFmpeg 전체 디코딩을 통과했습니다. SHA-256은 `5ce54014634a39106481c91af22fff427f4a700bebb90c598774b86d188b4054`입니다. 최종 MP4의 AAC·영상 복사·전체 재생 검증은 영상 보고서에서 확인합니다.

## BGM

v2와 동일한 Andrew Ev의 **Mountains** 0–46초 구간, 동일 볼륨·ducking·페이드를 유지했습니다. 자료는 `bgm/music.mp3`, `bgm/provenance.json`, `bgm/license.html`에 있습니다.

출처: https://mixkit.co/free-stock-music/tag/corporate/?page=2

라이선스: https://mixkit.co/license/modal/musicFree/

음원 단독 재배포·소유권 주장·권리 관리 서비스 등록은 허용되지 않습니다. 이 리소스는 나레이션을 포함한 영상 결합 사용을 위해 보존했습니다.

## 채택하지 않은 테이크

첫 v3 테이크 `kJnbaRK4s7QWPI5t1ZBq`는 CUT02 두 단어를 로컬 ASR로 확인할 수 없어 채택하지 않았습니다. 동일 조건의 v2 대조 음원은 정상적으로 전사되었습니다. 이 테이크의 원본 MP3·receipt·전사·거부 이유를 `rejected-take/`에 보존했습니다.

기존 TTS 노드에 연결한 Scribe 결과는 실제로 발화되지 않은 delivery tag와 불가능한 단어 시간을 포함했으므로 독립 음성 근거로 사용하지 않았습니다. 해당 부정적 근거도 rejected-take에 있습니다. 최종 9개 컷에는 채택하지 않은 테이크의 음성을 섞지 않았습니다.
