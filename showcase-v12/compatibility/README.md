# Revision12 — Windows 10 재생 호환본

사내 Windows 10의 **Windows Media Player에서 소리만 나오고 화면이 표시되지 않는다**는 사용자 보고에 따라 만든 인코딩 파생본입니다. 원본 Revision12와 기존 소스 ZIP은 보존합니다. 과제 순서, 문구, 화면 구성, 나레이션, BGM, 재생 속도 또는 컷 타이밍을 편집하는 작업이 아닙니다.

## 원본 확인

원본은 `out/showcase-v12/RD_Process_AI_Fast_Track_Showcase_Revision12.mp4`이며 SHA-256은 `8554cff5a71b81be36734c18a763f2aa94db36b3198d29984ac815325ffb972b`입니다.

| 항목 | 원본 |
|---|---|
| 컨테이너 | MP4, avc1 영상 + mp4a 음성, moov 선행 |
| 영상 | H.264 High, Level 4.0, 8비트 yuv420p, 1920×1080 순차주사 |
| 시간 | 30fps, 9,724프레임, 324.133333초 |
| 음성 | AAC-LC, 48kHz, 스테레오 |

SPS/PPS, 영상 패킷 위치, 전체 표시 시각, 첫 키프레임 및 파일 구조에서 원인으로 지목할 오류를 찾지 못했습니다. 초기 음수 DTS는 B프레임의 재정렬과 대응합니다. High 프로파일이라는 사실만으로 Windows 10 미지원 코덱이라고 판단할 수 없습니다.

Microsoft 공식 문서의 [H.264 디코더](https://learn.microsoft.com/en-us/windows/win32/medfound/h-264-video-decoder)는 Baseline/Main/High와 Level 5.1 이하, 4:2:0을 지원하며, [AAC 디코더](https://learn.microsoft.com/en-us/windows/win32/medfound/aac-decoder)는 AAC-LC를 지원합니다. 사내 PC의 실제 디코더·GPU·Media Player 구성 및 PC로 옮겨진 파일의 동일성은 이 작업 환경에서 확인할 수 없습니다.

## 제공 파일

출력은 모두 `out/showcase-v12/windows10/`에 있습니다.

| 파일 | 영상 | 음성 | 용도 |
|---|---|---|---|
| `RD_Process_AI_Fast_Track_Revision12_Windows10_Compatible.mp4` | H.264 Constrained Baseline, L4.0 | 원본 AAC-LC 패킷 복사 | 압축 옵션을 단순하게 한 MP4 |
| `RD_Process_AI_Fast_Track_Revision12_Windows10_Fallback.wmv` | WMV2 / Windows Media Video 8 | WMA2, 192kbps, 48kHz 스테레오 | H.264/AAC와 다른 디코더 경로를 사용하는 Windows Media Player 대체본 |

MP4는 1920×1080/30fps/9,724프레임과 표시 시각을 유지하고 B프레임, CABAC, 8×8 변환, weighted P를 끕니다. 참조 프레임은 하나이며, 2초 간격의 닫힌 GOP를 사용합니다. 기존 AAC는 다시 압축하지 않으며, 실제 AAC 패킷·시각과 디코딩 PCM이 원본과 완전히 같은지 검사합니다. 첫 AAC 프라이밍 처리를 위해 정상적인 MP4 edit list를 유지합니다.

WMV는 별도의 영상·음성 코덱으로 변환하므로 압축된 바이트가 원본과 같지는 않습니다. 원본 믹스 PCM에서 음성을 변환하고 속도·음높이·음량을 변경하지 않습니다. ASF 프리롤 및 WMA 인코더 지연에 따른 컨테이너 시각과 실제 영상·음성의 정렬은 별도 검수 기록으로 구분합니다.

## 검수와 범위

`mp4-validation.json`은 실제 비트스트림·모든 프레임 시각·AAC 패킷과 PCM·전체 AV 디코딩을 검수합니다. `visual-validation.json`과 `direct-visual-review.json`은 원본과 정확히 같은 36개 프레임을 비교합니다. WMV의 인코딩 명령, 지연과 정렬, 전체 디코딩·프레임 수는 해당 WMV 전용 검수 기록이 기준입니다. `compatibility-validation.json`은 두 완성 파일의 SHA와 검수 기록을 묶습니다.

최종 상태 `PASS_WITH_WINDOWS_RUNTIME_CAVEAT`는 파일의 로컬 기술 검수가 통과했으며, **사내 Windows 10 PC의 실제 Windows Media Player 재생은 아직 확인하지 못했다**는 뜻입니다. 이 파일만으로 회사 PC의 원인이 확정되거나 실제 재생 성공이 확인됐다고 주장하지 않습니다.

두 파일 중 하나를 PC에 완전히 저장한 뒤 Windows Media Player에서 여십시오. 필요하면 같은 폴더의 `SHA256SUMS.txt`와 Windows의 `Get-FileHash -Algorithm SHA256`으로 전송된 파일을 비교할 수 있습니다.

MP4 재현 명령은 `python3 showcase-v12/compatibility/build-windows-mp4.py`입니다. FFmpeg/FFprobe와 libx264가 필요하며, 새 음성 생성이나 외부 유료 서비스 호출을 하지 않습니다. 이 폴더의 스크립트와 별도의 WMV 빌드 스크립트는 기존 원본을 읽어 새 호환본을 생성합니다.

WMV 재현 도구는 `wmv-fallback.py`입니다. 기본 실행으로 새 partial 파일을 변환·기술검수하며, 별도 화면 검수 기록을 확인한 뒤 `--finalize`로 완성 파일을 확정합니다. 기존 완성 파일을 임의로 덮어쓰지 않습니다.
