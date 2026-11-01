# 008_youtube_analyzer — 유튜브 영상 통째로 분석하기

Claude는 영상을 직접 재생하지 못합니다. 이 도구는 유튜브 영상을 **대본(자막) + 장면 캡처(이미지) + Markdown 보고서**로 바꿔서,
Claude가 영상 내용을 처음부터 끝까지 읽고 요약·분석·코드 재현을 할 수 있게 합니다.

## 동작 흐름

```
유튜브 URL ──yt-dlp──▶ 영상 정보(info.json) + 자막(.vtt) + 영상(.mp4, 720p 이하)
                           │                    │
                           ▼                    ▼
                  자막 파싱·중복 제거      ffmpeg로 N초마다 장면 캡처
                           │                    │
                           └────────┬───────────┘
                                    ▼
             report.md (시간대별 대본 + 같은 시간대 장면 이미지)
                                    ▼
                   Claude에게 "output/report.md 읽고 분석해줘"
```

- **자막**: 수동 자막을 먼저 찾고, 없으면 자동 생성 자막을 씁니다. 언어 우선순위는 `--lang`으로 정합니다(기본 `ko,en`).
- **중복 제거**: 유튜브 자동 자막은 같은 문장이 여러 번 반복되고 단어별 타이밍 태그가 섞여 있습니다. 이를 정리해 한 번씩만 남깁니다.
- **장면 캡처**: 화면에 나온 코드, 슬라이드, UI를 놓치지 않도록 `--interval`초(기본 10초)마다 PNG로 저장합니다.
- **보고서**: `--section`초(기본 60초) 구간마다 "그 시간에 한 말"과 "그 시간의 화면"을 나란히 배치합니다.

## 기술 스택

- Python 3.13
- [yt-dlp](https://github.com/yt-dlp/yt-dlp): 영상 정보·자막·영상 내려받기
- ffmpeg / ffprobe: 장면 캡처, 영상 길이 확인 (시스템에 설치 필요)
- pytest

## 폴더 구조

```
008_youtube_analyzer/
├── youtube_analyzer/
│   ├── __main__.py     # python -m youtube_analyzer 진입점
│   ├── cli.py          # 명령행 인자 처리, 전체 흐름
│   ├── downloader.py   # yt-dlp 연동 (테스트를 위해 YoutubeDL 클래스 주입 가능)
│   ├── subtitles.py    # VTT/SRT 파싱, 자동 자막 중복 제거
│   ├── frames.py       # ffmpeg 장면 캡처
│   └── report.py       # Markdown 보고서, 대본 텍스트 생성
├── tests/              # pytest (네트워크 없이 실행)
├── requirements.txt
└── pytest.ini
```

## 설치

```bash
cd 000_sample_project/008_youtube_analyzer
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
ffmpeg -version   # 없으면: sudo apt install ffmpeg / brew install ffmpeg
```

## 사용법

```bash
# 유튜브 영상 분석 (결과: output/)
.venv/bin/python -m youtube_analyzer "https://youtu.be/VIDEO_ID"

# 자막만 빠르게 (영상 내려받기·장면 캡처 생략)
.venv/bin/python -m youtube_analyzer "https://youtu.be/VIDEO_ID" --no-frames

# 코드가 빠르게 바뀌는 강의: 5초 간격 캡처, 30초 구간, 영어 자막 우선
.venv/bin/python -m youtube_analyzer "https://youtu.be/VIDEO_ID" --interval 5 --section 30 --lang en,ko

# 로컬 영상·자막 파일 분석 (유튜브 접속이 막힌 환경에서도 사용 가능)
.venv/bin/python -m youtube_analyzer --video lecture.mp4 --subtitle lecture.ko.vtt --title "강의 제목"
```

| 옵션 | 기본값 | 설명 |
|---|---|---|
| `url` | | 유튜브 영상 URL |
| `--video`, `--subtitle` | | URL 대신 로컬 영상/자막 파일 |
| `--title` | 파일 이름 | 로컬 파일 분석 시 보고서 제목 |
| `-o`, `--out` | `output` | 결과 폴더 |
| `--lang` | `ko,en` | 자막 언어 우선순위 |
| `--interval` | `10` | 장면 캡처 간격(초) |
| `--section` | `60` | 보고서 구간 길이(초) |
| `--max-height` | `720` | 내려받을 영상 최대 세로 해상도 |
| `--no-frames` | | 장면 캡처 생략 |

### 결과물

```
output/
├── report.md        # Claude에게 읽힐 보고서 (대본 + 장면 이미지 링크)
├── transcript.txt   # [00:01:23] 형식의 순수 대본
├── info.json        # 제목, 채널, 길이, 설명, 챕터
├── frames/          # frame_0001.png ...
└── source/          # 내려받은 원본 자막·영상
```

### Claude에게 분석시키기

Claude Code에서 다음처럼 요청하면 됩니다. Claude는 이미지(장면 캡처)도 읽을 수 있습니다.

```
output/report.md 와 frames/ 이미지를 읽고
1) 영상 전체 요약 2) 시간대별 핵심 내용 3) 화면에 나온 코드를 정리해줘
```

## 테스트

```bash
.venv/bin/pytest -q
```

- 네트워크 없이 실행됩니다. yt-dlp는 가짜 클래스로 대체합니다.
- ffmpeg가 있으면 짧은 테스트 영상을 직접 만들어 실제로 장면을 캡처합니다. ffmpeg가 없으면 해당 테스트는 건너뜁니다.

## 클라우드 환경에서 쓸 때

Claude Code 클라우드 세션은 네트워크 정책 때문에 유튜브 접속이 막혀 있을 수 있습니다(`403 Forbidden`).
환경 설정 → **Network access** → **Allowed domains**에 다음을 추가하세요.

- `www.youtube.com`: 영상 정보·자막
- `*.googlevideo.com`: 영상 파일

## 주의

- 내려받은 영상·자막·캡처는 저작물입니다. 개인 학습·분석 용도로만 쓰고 다시 배포하지 마세요. `.gitignore`에서 `output/`과 영상 파일을 제외해 두었습니다.
- 유튜브 이용약관을 지키세요. 비공개·연령 제한 영상은 로그인 정보가 필요해서 이 도구로는 받을 수 없습니다.
- 자막이 없는 영상은 대본 없이 장면 캡처만 만들어집니다. 음성을 직접 텍스트로 바꾸려면 Whisper 같은 음성 인식을 추가해야 합니다(이 샘플에는 포함하지 않음).
