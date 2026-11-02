# transcripts — 데발링보(Devalingvo): 우리만의 언어

유튜브 자막 원문이 공개 저장소에서 **평문으로 보이지 않게**, 우리만의 언어 **데발링보**로 써서 `<영상ID>.txt.dvl` 로 올립니다.
이 저장소를 받은 사람은 누구나 번역기(`tools/transcripts.sh`)가 **자동으로 풀어서** 평문처럼 씁니다. 키·설정·추가 설치가 필요 없습니다.

```
DEVALINGVO-1
cŭlèbó bababa bababi bolèfé fapabi derohó láfímè hédèpì húsivi jéhùtè tètùlù sísògè
pónine kirépe bàjŭcè pípìhù fótívá tufúbà jŭvégù behejŭ sècépì jòsìna vajége rímènú
```

> **적용 범위**: 유튜브 자막처럼 외부에서 가져온 원문(스킬·자료를 만들 때 쓰는 재료)만 데발링보로 둡니다.
> 기존 md 문서·소스·스킬 파일은 평문 그대로입니다. 번역기는 `transcripts/` 폴더만 다룹니다.
>
> **가림막이지 보안 장치가 아닙니다.** 화면·검색에 평문이 드러나지 않게 할 뿐, 저장소를 받은 누구나 원문을 얻을 수 있습니다.
> 저작권 면에서는 원문을 공개하는 것과 같으므로, 분석에 필요한 자막만 두고 다 쓴 자막은 지웁니다.

## 데발링보 문법

| 항목 | 규칙 |
|---|---|
| 글자 | 자음 16개 `b c d f g h j k l m n p r s t v` × 모음 16개 `a e i o u á é í ó ú à è ì ò ù ŭ` |
| 음절 | 자음 + 모음 = 1바이트(자음이 앞 4비트, 모음이 뒤 4비트). 음절은 256개 |
| 단어·줄 | 3음절이 한 단어, 12단어가 한 줄 |
| 먼저 압축 | gzip(-n)으로 압축한 뒤 쓴다. 원문 글자 빈도가 드러나지 않고, 긴 자막은 원문보다 짧아진다 |
| 첫 줄 | `DEVALINGVO-1` (문법이 바뀌면 숫자를 올린다) |

같은 내용은 항상 같은 글이 됩니다. 시작이 늘 `cŭlèbó bababa …` 인 것은 압축 파일의 고정 머리말 때문입니다(데발링보의 인사말).

| 위치 | 내용 | git |
|---|---|---|
| `transcripts/plain/<영상ID>.txt` | 평문 자막(작업용) | **항상 제외** |
| `transcripts/<영상ID>.txt.dvl` | 데발링보로 쓴 자막 | 커밋 |

## 처음 한 번 (클론마다)

```bash
tools/transcripts.sh setup     # 자동 변환·풀기 훅을 켜고, 지금 있는 데발링보 글을 plain/ 에 푼다
```

필요한 것은 `git`, `bash`, `gzip`, `perl` 뿐입니다(Windows 는 Git Bash 에 모두 포함, 맥·리눅스는 기본 포함).

## 평소 사용

```bash
cp 받은자막.txt transcripts/plain/v-lYvViXXWA.txt   # 파일 이름 = <영상ID 11자>.txt
git commit -m "자막 추가"                           # 커밋 전 훅이 데발링보로 옮겨 .dvl 만 함께 커밋
git push
# 다른 곳에서 git pull 하면 훅이 자동으로 plain/ 에 풀어 준다
```

- 받은 쪽에서 `plain/` 의 파일을 고쳤고 그쪽이 더 새 파일이면 덮어쓰지 않는다.
- 수동 명령: `tools/transcripts.sh encode <자막.txt> <영상ID>`, `decode <영상ID> [출력 파일]`, `sync-enc`, `sync-dec`, `check`.

## 지켜야 할 것

- 평문은 `.gitignore`(plain/ 제외)와 커밋 전 검사 두 겹으로 막혀 있다. `git add -f` 로 억지로 넣어도 검사가 막는다.
- 공개 저장소의 기록은 지워도 남는다. 평문이 한 번 올라가면 되돌릴 수 없다.
