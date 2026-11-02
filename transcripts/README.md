# transcripts — 우리만의 공용 번역기(자막 「에스페란토」 변환)

유튜브 자막 원문이 공개 저장소에서 **평문으로 보이지 않게** 고정 변환(gzip 압축 + base64)한 `<영상ID>.txt.eo` 만 올립니다.
이 저장소를 받은 사람은 누구나 같은 방식으로 **자동으로 풀어서** 평문처럼 씁니다. 키·설정·추가 설치가 필요 없습니다.

> **가림막이지 보안 장치가 아닙니다.** 화면·검색에 평문이 드러나지 않게 할 뿐, 저장소를 받은 누구나 원문을 얻을 수 있습니다.
> 저작권 면에서는 원문을 공개하는 것과 같으므로, 분석에 필요한 자막만 두고 다 쓴 자막은 지웁니다.

| 위치 | 내용 | git |
|---|---|---|
| `transcripts/plain/<영상ID>.txt` | 평문 자막(작업용) | **항상 제외** |
| `transcripts/<영상ID>.txt.eo` | 변환본(첫 줄 `DEVALIVE-EO1`) | 커밋 |

## 처음 한 번 (클론마다)

```bash
tools/transcripts.sh setup     # 자동 변환·풀기 훅을 켜고, 지금 있는 변환본을 plain/ 에 푼다
```

필요한 것은 `git`, `bash`, `gzip`, `base64` 뿐입니다(Windows 는 Git Bash, 맥·리눅스는 기본 포함).

## 평소 사용

```bash
cp 받은자막.txt transcripts/plain/v-lYvViXXWA.txt   # 파일 이름 = <영상ID 11자>.txt
git commit -m "자막 추가"                           # 커밋 전 훅이 자동으로 변환해 .eo 만 함께 커밋
git push
# 다른 곳에서 git pull 하면 훅이 자동으로 plain/ 에 풀어 준다
```

- 같은 내용은 항상 같은 변환본이 나와서, 다시 커밋해도 불필요한 변경이 생기지 않는다.
- 받은 쪽에서 `plain/` 의 파일을 고쳤고 그쪽이 더 새 파일이면 덮어쓰지 않는다.
- 수동 명령: `tools/transcripts.sh encode <자막.txt> <영상ID>`, `decode <영상ID> [출력 파일]`, `sync-enc`, `sync-dec`, `check`.

## 지켜야 할 것

- 평문은 `.gitignore`(plain/ 제외)와 커밋 전 검사 두 겹으로 막혀 있다. `git add -f` 로 억지로 넣어도 검사가 막는다.
- 공개 저장소의 기록은 지워도 남는다. 평문이 한 번 올라가면 되돌릴 수 없다.
