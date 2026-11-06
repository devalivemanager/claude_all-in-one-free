# 013_ai_ebook_builder — AI 전자책 빌더(Folio 파이프라인)

원본 텍스트·마크다운(대본, 기획서, 소설 원고)을 넣으면 **목차 분할 → 표지 생성 → 4종 출력(단독 HTML 뷰어·EPUB·인쇄용 HTML·웹북 ZIP)** 까지 한 번에 끝내는 파이썬 패키지다.
웹 앱 Folio(https://youtu.be/GvtjzW8UZCM 에서 소개)의 흐름을 데브얼라이브 클로드 코드 환경으로 옮긴 것으로, **브라우저 복붙 없이 CLI 한 줄**로 돈다.

> 원본 자료 : GPT PARK의 AI팩트 「전자책 만들기, 이제 5분이면 됩니다」 https://youtu.be/GvtjzW8UZCM
> 이 샘플이 바꿔서 만든 것 :
> - **목차 분할을 모델 없이 규칙으로 한다.** 마크다운 제목·「제N장」·「N.」 번호만으로 챕터를 찾으므로 결과가 늘 같고 비용이 0원이다. 주제 단위 재분할이 꼭 필요할 때만 클로드 코드에게 맡긴다.
> - **표지는 코드(SVG)로 그린다.** 생성 이미지 AI를 쓰지 않으므로 한글 글자가 뭉개지지 않고, 같은 입력은 언제나 같은 표지가 나온다.
> - **본문 다시 쓰기(요약·문장 정리)는 여기서 하지 않는다.** 그것은 클로드 코드의 일이다. 이 패키지는 읽고 묶는 일만 하고, 챕터별 청크(`Chapter.chunks`)를 재생성 단위로 남긴다.
> - **API 키가 어디에도 필요 없다.** HTML 산출물에 비밀값이 들어갈 자리 자체가 없다.

## 기술 스택

- Python 3.10 이상, **표준 라이브러리만**(설치할 패키지 없음)
- 테스트: `unittest`(원하는 경우 `pytest` 로도 돈다)

## 폴더 구조

```
013_ai_ebook_builder/
├── ebook_builder/
│   ├── cli.py              # 한 줄 배치 러너(python -m ebook_builder.cli build …)
│   ├── toc_generator.py    # 목차 분할·챕터 감지·청크 분할
│   ├── builder.py          # HTML 뷰어·EPUB·인쇄용 HTML·웹북 ZIP 조판, 10종 스타일 프리셋
│   └── cover_generator.py  # SVG 표지 자동 생성(결정론적)
├── tests/                  # 시험(외부 도구·네트워크 없이 돈다)
└── (실행하면 생김, 커밋하지 않음) output/
```

## 실행 방법

```bash
cd 000_sample_project/013_ai_ebook_builder

# 스타일 프리셋 10종 보기
python -m ebook_builder.cli presets

# 대본 파일들을 전자책으로 (산출물 4종 + 표지 + 목차 보고서)
python -m ebook_builder.cli build data/*.txt \
    --title "밤지기 옛이야기 대본집" --author "데브얼라이브" \
    --preset novel --outdir output
```

산출물:

| 파일 | 용도 |
|---|---|
| `output/viewer.html` | 단독 뷰어. 검색·야간 모드·인쇄 버튼 포함, 오프라인에서 열린다. 공유용 |
| `output/book.epub` | 리디북스·애플 북스 등 전자책 리더용 |
| `output/print.html` | 인쇄용. 브라우저에서 열어 인쇄(→PDF 저장)하면 챕터마다 페이지가 나뉜다 |
| `output/webbook.zip` | 버셀 드롭(https://vercel.com/drop) 에 끌어다 놓으면 그대로 웹북 URL 이 된다 |
| `output/cover.svg` · `output/toc.md` | 표지 원본과 챕터·청크 목록(클로드 코드 검토용) |

## 시험 방법

```bash
python3 -m unittest discover -s tests -t .. -v   # 폴더 안에서
# 또는
python3 -m unittest discover -s 000_sample_project/013_ai_ebook_builder/tests \
    -t 000_sample_project/013_ai_ebook_builder
```

시험은 챕터 분할(마크다운 제목·「제N장」·「N.」), 껍데기 제목 병합, 청크 분할, SVG 표지 결정론성·XML 유효성·이스케이프, EPUB mimetype 무압축 규격, 웹북 manifest, CLI 한 줄 빌드까지 본다.

## 10대 운영 수칙 중 이 패키지가 직접 지키는 것

1. **원본은 읽기만 한다.** 입력 파일은 절대 고치지 않고, 산출물은 `--outdir` 로만 나온다.
2. **비밀값 없음.** Gemini API 키를 쓰는 Folio 와 달리 키가 필요 없고, 산출물 HTML 에 키가 들어갈 자리가 없다.
3. **교보 POD 판형과 분리.** 이 파이프라인의 출력은 화면 읽기용(EPUB·웹북)이다. 종이책 판형(152×225mm 등) 조판은 `013` 에서 하지 않고 POD 문서 규격을 따른다.
4. **토큰 보호.** 챕터마다 청크를 나눠 두어, 마음에 안 드는 챕터 하나만 클로드 코드에게 다시 쓰게 할 수 있다(전체 재생성 금지).

## 클로드 코드와 이어 붙이기

1. (선택) 본문 다듬기 — 챕터 청크를 클로드 코드에 넣어 「같은 사실, 같은 인물명」을 지키며 다듬고 `data/refined/` 에 저장.
2. `python -m ebook_builder.cli build data/refined/*.txt --title … --outdir output`
3. `output/webbook.zip` 을 버셀 드롭에 올려 링크로 배포하거나, `book.epub` 을 리더에서 열어 확인.
