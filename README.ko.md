# newspeak

한국어와 영어 글에서 AI 말투를 찾아 지우는 Claude Code 스킬입니다.
새 글을 처음부터 AI 티 없이 쓸 때도 씁니다.

[English](README.md)

## 이름

조지 오웰 『1984』의 신어(Newspeak)는 낱말을 줄이고 정해진 틀로만 말하게 해 생각을 좁히는 언어입니다.
AI 글도 같은 틀, 같은 상투구, 같은 리듬으로 흘러갑니다.
이 스킬은 그 틀을 찾아 걷어 냅니다.

## 하는 일

| 모드 | 하는 일 | 끝나는 조건 |
|---|---|---|
| review | AI 말투와 그 이유를 보고합니다 | lint 결과와 사람이 볼 목록 |
| rewrite | 있는 글을 고칩니다. 패턴이 나온 곳만 고칩니다 | `gate.py` 통과 |
| write | 지시서로 새 글을 쓰고 검사합니다 | lint S1·S2 0건, `gate.py --mode write` 통과 |

- `scripts/lint.py`는 탐지기입니다.
  한국어·영어 정규식 규칙 108개와 구조 검사 13개가 들어 있습니다.
  심각도는 세 단계로 나눕니다.
  보고서에는 `--style ste`로 ASD-STE100 문장·문단 상한을 더 검사합니다.
  한 줄에 문장이 둘 이상인 줄도 따로 알려 줍니다([FMT]).
- `scripts/gate.py`는 원문과 고친 글을 비교합니다.
  다음을 잡습니다.
  - 수치·링크가 사라지거나 새로 생긴 것
  - 추측·당위 표지가 바뀐 것('~일 수 있다'를 '~이다'로)
  - 출처 표시가 빠진 것
  - 필자의 역할을 부풀리거나 줄인 것
  - 고치면서 새로 생긴 AI 패턴
  - 지나치게 고친 것
  - 한 줄에 문장이 둘 이상인 것(명령줄 기본)
- `scripts/linebreak.py`는 문장마다 줄을 바꿉니다.
  소수점, 목록 번호, 말줄임표, 약어, 인용, 코드, 제목, 표 칸은 건드리지 않습니다.

결과 글은 한 줄에 한 문장으로 씁니다.
문장을 끝내는 마침표·물음표·느낌표 뒤에서 줄을 바꿉니다.
보고서·문서는 ASD-STE100(Simplified Technical English)의 핵심 원칙을 따릅니다.
한 문장에 정보 하나, 문장·문단 길이 상한, 낱말 하나에 뜻 하나, 조건·경고는 동작 앞에, 복잡한 내용은 세로 목록이 그것입니다.

연구에서 신호가 약하다고 나온 것(피동, 부사, 3개 나열 한 번, 대시 한두 개)은 그것만으로 고치지 않습니다.

## 설치

Claude Code는 `~/.claude/skills/<이름>/`에서 사용자 스킬을 읽습니다.

git으로 받을 때:

```bash
git clone https://github.com/PoisonJelly/newspeak ~/.claude/skills/newspeak
```

zip으로 받았거나 다른 폴더에 받았을 때:

```powershell
# Windows (PowerShell)
.\install.ps1
```

```bash
# macOS / Linux
./install.sh
```

두 스크립트 모두 `~/.claude/skills/newspeak`로 파일을 복사합니다.
예전 판이 있으면 `~/.claude/skill-backups/`로 옮겨 두고 끝에 단위 테스트를 돌립니다.

Python 3.9 이상이 필요합니다(3.12에서 시험).
따로 설치할 패키지는 없습니다.

## 쓰는 법

Claude에게 "AI 티 빼줘", "윤문해줘", "이 메일 사람이 쓴 것처럼 고쳐줘"라고 하거나 `/newspeak`를 입력합니다.

스크립트만 따로 쓸 수도 있습니다.

```bash
python scripts/lint.py draft.txt
python scripts/lint.py post.txt --genre sns
python scripts/gate.py before.txt after.txt
python scripts/gate.py brief.txt draft.txt --mode write
python scripts/linebreak.py draft.txt out.txt   # 한 줄에 한 문장(--target markdown | html)
python scripts/lint.py report.txt --style ste   # 보고서: ASD-STE100 상한
```

## 시험

8묶음 46회 셀프테스트를 거쳤습니다.
회차마다 한 에이전트가 스킬로 글을 고치거나 썼습니다.
스킬 파일을 보지 않는 다른 에이전트가 조사 자료를 기준으로 그 결과를 판정했습니다.
사람이 쓴 대조군 글 3개도 넣었습니다.
처음 보는 입력이 들어간 마지막 묶음에서는 중대 문제와 스크립트 오류가 나오지 않았습니다.
기록은 [tests/selftest-log.md](tests/selftest-log.md)에 있습니다.

한계:
- 판정자도 언어 모델입니다.
  사람 편집자가 본 것은 아닙니다.
- lint는 정규식이라 말을 바꿔 쓴 패턴을 놓칠 수 있습니다.
  그래서 스킬이 사람 눈으로도 읽게 합니다.

## 바뀐 점

- 1.1.1: 이어지는 줄을 들여쓴 번호 목록을 STE-2가 문단 하나로 세던 문제를 고쳤습니다.
- 1.1.0: 한 줄에 한 문장(`linebreak.py`, gate `linebreak` 검사), ASD-STE100 보고서 형식(`--style ste`, SKILL.md 6-1절), 구조 패턴 검사 추가(경구식 두 문장 제목, 라벨 세 줄 요약, 아주 짧은 문장 연속: KO-S1·S2·E4, EN-S1·S2·L5).
  단위 시험 44개.
- 1.0.0: 첫 공개.

## 출처와 라이선스

MIT 라이선스입니다([LICENSE](LICENSE)).

MIT 라이선스로 공개된 두 프로젝트의 규칙을 가져와 고쳤습니다.
저작권 고지와 바꾼 내용은 [references/LICENSES.md](references/LICENSES.md)에 있습니다.

- [stop-slop](https://github.com/hardikpandya/stop-slop) (Hardik Pandya): 영어 문구·구조 목록
- [im-not-ai](https://github.com/epoko77-ai/im-not-ai) (epoko77-ai): 한국어 패턴 분류, 심각도 체계, 실측 결과

위키백과 「Signs of AI writing」과 `references/evidence.md`의 논문들은 사실과 결과만 참고했습니다.
짧은 패턴 문구 말고는 글을 옮기지 않았습니다.
