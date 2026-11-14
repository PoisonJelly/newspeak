# 근거 요약

- 바탕: 2026-11-08에 한 조사(한국어 자료, 영어 위키·실무 가이드, 학술·실증 연구). 핵심 수치와 출처를 아래 표에 옮겼다.
- 표시:
  - [2차]: 원문을 못 열고 보도로 확인한 것
  - [자체]: 업체·오픈소스의 자체 측정

## 1. 가장 단단한 근거

| 사실 | 수치 | 출처 |
|---|---|---|
| 한국어 쉼표 과다 | 쉼표 든 문장 비율: 사람 26%, LLM 61%(에세이). 연결어미 뒤 쉼표: 4%, 20% | KatFishNet, ACL 2025 |
| 한국어 'A가 아니라 B' | 1,000자당 AI 5.8회, 사람 0.6회(9.2배) | im-not-ai [자체] |
| 한국어 장문 결핍 | 100자 넘는 문장: 1,000어절당 사람 91.3, AI 8.1 | im-not-ai [자체] |
| 영어 분사절·명사화 | 분사절 2~5배(GPT-4o 5.3배), 명사화 1.5~2배 | Reinhart 외, PNAS 2025 |
| 영어 행위자 없는 수동태 | GPT-4o가 사람의 약 0.5배 | Reinhart 외, PNAS 2025 |
| 어휘 급증 | 2024년 PubMed 초록의 최소 13.5%가 LLM을 거침. 초과 단어의 66%가 동사 | Kobak 외, Science Advances 2025 |
| 어휘 유행 | delve 등은 2024년 4월부터 감소. 회피 프롬프트는 줄일 뿐 없애지 못함 | Geng & Trotta, ACL Findings 2025 |
| 모델 지문 | 5개 모델 97.1% 구분. 단어를 섞어도 88.9%, 번역 뒤 91.8% | Sun 외, ICML 2025 |
| 아첨의 원인 | 엄지 피드백 보상이 아첨 억제 신호를 약하게 만들었다고 OpenAI가 인정(2025-04-29, 05-02) | OpenAI 공식 |
| 선호 학습의 쏠림 | 평가자가 동조하는 답, 긴 답, 확신하는 답, 익숙한 답을 선호 | Sharma 2024, Singhal 2024, Zhou 2024, Zhang 2025 |
| 사후 학습이 원인 | base 모델은 사람에 가깝고 instruct 모델에서 차이가 커짐 | Reinhart 2025, Sun 2025, Padmakumar 2024 |
| 구문 틀은 사전학습에서 | 모델 템플릿의 76%가 사전학습 데이터에 있음 | Shaib 외, EMNLP 2024 |

## 2. 통념과 실제

| 통념 | 실제 | 이 스킬의 처리 |
|---|---|---|
| em dash = AI | 모델마다 0~10.6/1,000단어로 다르고 사람도 0.3~17.1로 넓다. 2026년 ChatGPT·Gemini는 사람보다 적게 쓴다[2차] | 300단어당 1회 이하로 줄이고 대체 부호를 섞는다 |
| AI는 과잉 헤징 | 측정 연구는 헤지·인식 표지가 더 적다고 본다. 사람들이 느끼는 헤징은 면책·훈계 문구다 | 정당한 헤지는 두고 면책 상투구만 지운다 |
| AI는 수동태 남용 | 영어 GPT-4o는 덜 쓴다. 한국어는 번역투 피동이 지목되지만 정량 측정이 없다 | 영어는 행위자를 숨기는 수동태만 고친다. 한국어는 이중 피동·'~에 의해'만 고친다 |
| '~를 통해'는 AI 표현 | im 실측에서 사람 글에 더 많았다 | 몰릴 때만 고친다 |
| 금지어만 피하면 된다 | 단어를 섞어도 모델을 맞힌다 | 구조를 먼저 본다 |
| 탐지기는 믿을 만하다 | 비원어민 에세이의 61%를 AI로 오판했다(Liang 2023) | 이 스킬은 탐지 판정을 하지 않는다. 고칠 곳만 찾는다 |
| 사람은 쉽게 알아본다 | 일반인 50~52%, 언어학자 38.9%. LLM을 자주 쓰는 사람만 예외다(Russell 2025: 5명 다수결 299/300) | 패턴 목록과 스크립트로 보완한다 |

## 3. 시기와 모델별 차이

| 시기·모델 | 두드러진 말투 |
|---|---|
| 2022~23 GPT-3.5/4 | "As an AI language model", 지식 기준일 문구, 'In conclusion', delve·tapestry. 한국어: '~하는 것이 중요합니다', '저는 인공지능이기 때문에' |
| 2024~25 GPT-4o | 이모지 글머리, em dash 폭증, 'not just X but Y', 아첨(2025-04 롤백). 한국어: '핵심을 찔렀어' |
| 2025-08~ GPT-5 계열 | 건조함, 후속 제안('원하시면~'), 훈계('다만', '하나만 짚고 가자'), 억지 반박('반은 맞고 반은 틀려'), 비유 오용('선명하다', '층위') |
| 2026 GPT-5.6·GPT-6 | 'should be treated as X rather than Y', 'not simply', 'matters because', 'dependable' |
| Claude | 영어: 'rather than merely', 'less like X and more like Y', 현행 모델 중 em dash 최다[2차]. 한국어: 쉼표·비유 과다, '함께 봅니다'(나무위키) |
| Gemini | 'furthermore', 'absolutely essential', 'incredibly', 이탤릭. 한국어: '단순한 A가 아니라 B' 남용(나무위키) |

## 4. 출처

- 나무위키 「와... 너 정말, **핵심을 찔렀어.**」(2026-11-05판), ChatGPT·GPT-5·Claude 문서
- Wikipedia:Signs of AI writing (revid 1384336333, 2026-11-07), /Style, /Markup, WP:G15
- im-not-ai(humanize-korean) https://github.com/epoko77-ai/im-not-ai: ai-tell-taxonomy.md, quick-rules.md, rewriting-playbook.md, empirical-validation.md
- stop-slop(Hardik Pandya): SKILL.md, references/phrases.md, structures.md
- KatFishNet https://arxiv.org/abs/2503.00032
- Reinhart 외 https://arxiv.org/abs/2410.16107
- Sun 외 https://arxiv.org/abs/2502.12150
- Kobak 외 https://arxiv.org/abs/2406.07016
- Geng & Trotta https://aclanthology.org/2025.findings-acl.657
- Juzek & Ward https://aclanthology.org/2025.coling-main.426
- Shaib 외 https://arxiv.org/abs/2407.00211
- Sharma 외 https://arxiv.org/abs/2310.13548
- Russell 외 https://aclanthology.org/2025.acl-long.267
- Liang 외 2023 https://arxiv.org/abs/2304.02819
- Freeburg 2026 https://arxiv.org/abs/2603.27006
- Graphite "AI Tells" https://graphite.io/five-percent/research/ai-tells
- OpenAI https://openai.com/index/expanding-on-sycophancy/
- ASD-STE100 Simplified Technical English, Issue 9 (2025-01, 규칙 53개): 지시문 20단어·설명문 25단어 이하, 문단 6문장 이하·주제 하나, 한 문장에 지시 하나, 능동태, 명사 덩어리 3단어 이하, 낱말 하나에 뜻 하나, 복잡한 내용은 세로 목록. 공식 문서는 https://asd-ste100.org 에서 무료로 받는다. 요약: https://en.wikipedia.org/wiki/Simplified_Technical_English , https://www.tcworld.info/news/asd-ste100-issue-9-setting-a-standard-for-technical-documentation
- v1.1 구조 패턴(KO-S1·S2, KO-E4)은 연구가 아니라 실제 사용 보고에서 나왔다: lint 0건인 주간 보고서를 받는 사람이 '전형적인 AI 말투'로 읽었다(2026-11). 지난 셀프테스트 결과물 46개에 돌려 S2 오탐 0건을 확인했다.
