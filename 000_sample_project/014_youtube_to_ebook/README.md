# 014_youtube_to_ebook — 유튜브 영상 한 편으로 삽화 전자책 만들기

유튜브 URL 하나만 넣으면 **자막 대본**과 **핵심 장면 캡처(스틸컷)** 를 자동으로 뽑아,
본문 중간중간 삽화가 쏙쏙 박힌 전자책(단독 HTML 뷰어 + EPUB)을 한 번에 만드는 파이프라인이다.

- [008_youtube_analyzer](../008_youtube_analyzer/) 가 하던 「영상 → 대본 + 장면 캡처」 에서 한 발 더 나아가,
- [013_ai_ebook_builder](../013_ai_ebook_builder/) 의 「대본 → 전자책 4종 조판」 과 **직렬로 결합**했다.

## 동작 흐름

```
유튜브 URL
   │  yt-dlp: 영상 정보(제목·채널·공식 챕터) + 자막(수동 → 자동) 1개만
   ▼
자막 파싱·중복 제거(008 의 subtitles 로직)         ffmpeg 로 10초마다 스틸컷 PNG
   ▼                                              ▼
챕터화 (유튜브 공식 챕터가 있으면 그 경계, 없으면 60초 간격)
   ▼
스틸컷 ↔ 챕터 시간대 매칭 (컷이 나온 시점으로 어느 챕터에 들어갈지 정한다)
   ▼
ebook: 삽화 포함 단독 HTML 뷰어(이미지를 데이터 URI 로 박음) + EPUB 3(이미지 번들링)
   ▼
output/ebook.html · output/ebook.epub
```

- **자막 우선순위**: 수동 자막을 먼저 찾고, 없으면 자동 생성 자막(기계 번역본 제외)을 씁니다.
  여러 언어를 한꺼번에 받으면 유튜브 요청 과다(429)에 걸리기 쉬워 **하나만** 받습니다.
- **챕터 나눔**: 영상에 공식 챕터(챕터 표시)가 있으면 그 경계를 따르고, 없으면 60초 간격으로 묶습니다.
- **삽화 배치**: 스틸컷이 캡처된 시점으로 어느 챕터 구간에 속하는지 정하고, 캡션에 그 시각(00:01:23 장면)을 달아 줍니다. 지워졌거나 깨진 PNG 는 삽화에서만 빼고 본문은 살립니다.
- **EPUB 규격**: `META-INF/container.xml`·`urn:uuid:` 고유번호를 넣고, 값이 빈 저자·설명 항목은 쓰지 않습니다. 시험의 가짜 입력으로 만든 EPUB 이 EPUBCheck 5.2.1 에서 「No errors or warnings detected」 로 통과합니다.
- **폴백**: 자막이 아예 없는 영상은 `faster-whisper` 로컬 받아쓰기로 자막을 만들 수 있습니다(`local_transcribe`, 선택 설치).

## 기술 스택

- Python 3.12+ (표준 라이브러리만으로 조판 — 외부 패키지는 yt-dlp 뿐)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp): 영상 정보·자막·영상 내려받기
- ffmpeg / ffprobe: 스틸컷 캡처 (시스템에 설치 필요)
- unittest (pytest 에서도 돌아간다)

## 폴더 구조

```
014_youtube_to_ebook/
├── youtube_to_ebook/
│   ├── __main__.py     # python -m youtube_to_ebook 진입점
│   ├── cli.py          # 한 줄 배치 러너(명령행 인자)
│   ├── extractor.py    # 자막 추출·중복 제거 + ffmpeg 스틸컷 캡처 (008 연계)
│   ├── pipeline.py     # 챕터화 + 스틸컷 매칭 + 전체 오케스트레이션
│   └── ebook.py        # 삽화 포함 HTML 뷰어·EPUB 생성 (013 연계)
├── tests/              # unittest 53개 (네트워크·ffmpeg 없이 실행)
├── requirements.txt
├── pytest.ini
└── .gitignore          # output/·영상·전자책 결과물은 커밋하지 않는다
```

## 설치

```bash
cd 000_sample_project/014_youtube_to_ebook
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
ffmpeg -version   # 없으면: sudo apt install ffmpeg / brew install ffmpeg
```

## 사용법

```bash
# 원클릭 — URL 하나로 삽화 전자책 완성
python -m youtube_to_ebook https://youtu.be/VIDEO_ID

# 결과 폴더·출력 형식 지정
python -m youtube_to_ebook https://youtu.be/VIDEO_ID -o output --format html,epub

# 세부 조정: 챕터 간격 30초, 스틸컷 15초 간격, 제목·저자 직접 지정
python -m youtube_to_ebook https://youtu.be/VIDEO_ID \
    --subtitle-interval 30 --interval 15 \
    --title "내 책 제목" --author "데브얼라이브"
```

결과물:

| 파일 | 용도 |
|---|---|
| `output/ebook.html` | 파일 하나로 끝나는 뷰어(이미지 포함). 오프라인에서 열리고 그대로 공유 가능 |
| `output/ebook.epub` | 리디북스·애플 북스 등 전자책 리더용 (EPUB 3, 이미지 번들링) |

HTML 을 브라우저에서 열고 인쇄 → PDF 저장을 하면 PDF 도 된다.

## 테스트

```bash
python3 -m unittest discover -s tests -t .        # 53개
# 또는
.venv/bin/python -m pytest -q                     # pytest 로도 같은 53개
```

테스트는 yt-dlp·ffmpeg·네트워크 없이 돈다. 외부 연결(정보 조회·자막·영상·캡처)은
전부 함수 주입 지점이 있어 가짜로 검증한다.

## 주의

- **저작권**: 남의 영상을 전자책으로 만들어 올리는 것은 저작권 침해가 될 수 있다.
  내 채널 영상이나 허락받은 영상에 쓴다. 자막·캡처 결과물(`output/`)은 커밋하지 않는다.
- 유튜브는 클라우드 서버 IP 의 영상 다운로드를 막는 경우가 있다(HTTP 403). 그때는
  스틸컷 없이 글만 조판하므로 전자책 자체는 나온다. 영상은 내 PC 에서 받는 것이 안전하다.
- 요청을 연달아 많이 보내면 유튜브가 차단(429)한다. 한 번에 하나씩, 쉬엄쉬엄 쓴다.

---

Copyright (c) 2026 devalive · [MIT 라이선스](../LICENSE-MIT)
