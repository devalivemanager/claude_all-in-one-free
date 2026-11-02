# transcripts — 우리만의 공용 번역 도구(자막 자동 암호화)

유튜브 자막 원문은 저작물입니다. 공개 저장소에 **평문으로 보이지 않게** age 로 잠근 암호문(`<영상ID>.txt.age`)만 올립니다.
비밀키(사전)를 가진 우리 환경에서는 커밋할 때 **자동으로 잠그고**, 받을 때 **자동으로 풀어서** 평문처럼 씁니다.
비밀키가 없는 곳에서는 암호문만 보입니다.

| 위치 | 내용 | git |
|---|---|---|
| `transcripts/plain/<영상ID>.txt` | 평문 자막(작업용) | **항상 제외** |
| `transcripts/<영상ID>.txt.age` | 암호문 | 커밋 |
| `transcripts/recipients.txt` | age 공개키(잠그기 전용) | 커밋(공개돼도 됨) |
| 비밀키 `AGE-SECRET-KEY-1...` | 사전(여는 키) | **저장소·채팅·파일에 두지 않음** |

## 처음 한 번

```bash
# 1) 키 만들기(한 사람이 한 번). 비밀키 파일은 저장소 밖에 둔다
age-keygen -o ~/.config/devalive/transcript-key.txt
#    출력된 "Public key: age1..." 를 transcripts/recipients.txt 에 한 줄 추가해 커밋

# 2) 클론마다 한 번: 자동 잠금·풀기 훅 켜기
tools/transcripts.sh setup
```

비밀키를 찾는 순서: 환경변수 `TRANSCRIPT_AGE_KEY`(키 문자열) → `TRANSCRIPT_AGE_KEY_FILE`(키 파일 경로) → `~/.config/devalive/transcript-key.txt`.
클라우드 작업 환경에는 환경 설정의 비밀값(환경변수) `TRANSCRIPT_AGE_KEY` 로 넣는다. 새 세션부터 적용된다.

## 평소 사용

```bash
cp 받은자막.txt transcripts/plain/v-lYvViXXWA.txt   # 파일 이름 = <영상ID 11자>.txt
git commit -m "자막 추가"                           # 커밋 전 훅이 자동으로 잠가 .age 만 함께 커밋
git push
# 다른 환경에서 git pull 하면 훅이 자동으로 plain/ 에 풀어 준다
```

- 내용이 그대로인 자막은 다시 잠그지 않는다(잠글 때마다 결과가 달라 불필요한 변경이 생기므로).
- 받은 쪽에서 `plain/` 의 파일을 고쳤고 그쪽이 더 새 파일이면 덮어쓰지 않는다.
- 수동 명령: `tools/transcripts.sh encrypt <자막.txt> <영상ID>`, `decrypt <영상ID> [출력 파일]`, `sync-enc`, `sync-dec`, `check`.

## 지켜야 할 것

- 평문은 `.gitignore`(plain/ 제외)와 커밋 전 검사 두 겹으로 막혀 있다. `git add -f` 로 억지로 넣지 않는다(검사가 막는다).
- 공개 저장소의 기록은 지워도 남는다. 평문이 한 번 올라가면 되돌릴 수 없다.
- 비밀키가 새면 그동안 올린 암호문을 모두 열 수 있다. 새면 키를 바꾸고 새 공개키로 다시 잠근다.
- 파일 이름(영상 ID)·크기·올린 시각은 암호화되지 않는다.
