# transcripts — 암호화된 유튜브 자막

유튜브 자막 원문은 저작물입니다. 이 공개 저장소에는 **age 로 암호화한 파일(`<영상ID>.txt.age`)만** 둡니다.
비밀키를 가진 사람(저작권자의 PC, 클라우드 작업 환경)만 열 수 있습니다.

| 파일 | 내용 | 공개 여부 |
|---|---|---|
| `recipients.txt` | age 공개키(잠그기 전용) | 공개돼도 됨 |
| `<영상ID>.txt.age` | 암호화된 자막 | 암호문만 공개 |
| 비밀키 `AGE-SECRET-KEY-1...` | 여는 키 | **저장소·채팅·파일에 두지 않음.** PC 보관 + 클라우드 환경 설정의 비밀값 `TRANSCRIPT_AGE_KEY` |

## 처음 한 번 (로컬)

```bash
age-keygen -o ~/.config/devalive/transcript-key.txt   # 비밀키 파일. 저장소 밖에 둔다
# 출력된 "Public key: age1..." 를 transcripts/recipients.txt 에 한 줄 추가해 커밋
git config core.hooksPath .githooks                     # 평문 커밋을 막는 검사 켜기
```

클라우드: 환경 설정의 비밀값(환경변수)에 `TRANSCRIPT_AGE_KEY` = 비밀키 파일의 `AGE-SECRET-KEY-1...` 줄을 넣는다. 새 세션부터 적용된다.

## 자막 올리기 (로컬)

```bash
tools/transcripts.sh encrypt 받은자막.txt v-lYvViXXWA   # → transcripts/v-lYvViXXWA.txt.age
git add transcripts/v-lYvViXXWA.txt.age && git commit -m "자막 추가: v-lYvViXXWA" && git push
```

## 자막 열기 (비밀키가 있는 곳)

```bash
tools/transcripts.sh decrypt v-lYvViXXWA /tmp/v-lYvViXXWA.txt   # 평문은 저장소 밖에만 푼다
```

## 지켜야 할 것

- 평문 자막은 `.gitignore` 와 커밋 전 검사(`.githooks/pre-commit`) 두 겹으로 막혀 있다. `git add -f` 로 억지로 넣지 않는다.
- 공개 저장소의 기록은 지워도 남는다. 평문이 한 번 올라가면 되돌릴 수 없다.
- 비밀키가 새면 지금까지 올린 암호문 전체가 열린다. 새면 키를 바꾸고(새 공개키로 다시 잠금) 사용자에게 알린다.
- 파일 이름(영상 ID)·크기·올린 시각은 암호화되지 않는다.
