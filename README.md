# newspeak

A Claude Code skill that finds and removes AI writing tells in Korean and English text.
It can also write new text without them.

[한국어 설명](README.ko.md)

## Why the name

In Orwell's *Nineteen Eighty-Four*, Newspeak is a language built to shrink vocabulary and force every thought into a fixed set of phrases.
Text from language models drifts the same way: the same frames, the same stock phrases, the same rhythm.
This skill looks for those patterns and takes them out.

## What it does

The skill has three modes.

| Mode | What it does | Done when |
|---|---|---|
| review | Reports AI tells and why they read as AI | lint results plus a short list for a human to check |
| rewrite | Edits an existing text, only where a pattern was found | `gate.py` passes |
| write | Writes a new text from a brief and checks it | lint shows no S1 or S2 findings and `gate.py --mode write` passes |

Two scripts do the mechanical part.
Both use only the Python standard library.

- `scripts/lint.py` finds patterns: 108 regex rules and 13 structural checks across Korean and English, with three severity levels.
  `--style ste` adds ASD-STE100 limits for reports.
  It also lists lines that hold more than one sentence ([FMT]).
- `scripts/gate.py` compares the original with the rewrite.
  It flags lost or invented numbers and URLs, a changed hedge or obligation ("may" turned into "is"), dropped attributions, a writer's role made larger or smaller, new AI patterns added by the rewrite, and over-editing.
  On the command line it also checks that every sentence sits on its own line.
- `scripts/linebreak.py` puts each sentence on its own line.
  It leaves decimals, list numbers, ellipses, abbreviations, quotes, code, headings and table cells alone.

Every output puts one sentence on each line: a line break goes after each sentence-ending period, question mark and exclamation mark.
Reports and documents follow the core ideas of ASD-STE100 (Simplified Technical English): one piece of information per sentence, sentence and paragraph limits, one word for one meaning, conditions and warnings before the action, and vertical lists for complex content.

The rules keep what people actually write.
Passive voice, adverbs, a single list of three and an occasional dash are not treated as AI tells on their own.
The studies listed in `references/evidence.md` found them to be weak signals.

## Install

Claude Code reads user skills from `~/.claude/skills/<name>/`.

With git:

```bash
git clone https://github.com/PoisonJelly/newspeak ~/.claude/skills/newspeak
```

From a downloaded copy (zip or clone in another folder):

```powershell
# Windows (PowerShell)
.\install.ps1
```

```bash
# macOS / Linux
./install.sh
```

Both scripts copy the files to `~/.claude/skills/newspeak`, move any older copy to `~/.claude/skill-backups/`, and run the unit tests.

Requirements: Python 3.9 or later (tested on 3.12).
No packages to install.

Check the install:

```bash
python ~/.claude/skills/newspeak/scripts/selftest.py
```

## Use

Ask Claude in plain words, for example "make this sound human", "remove the AI tells from this email", "AI 티 빼줘", "윤문해줘", or type `/newspeak`.

The scripts also work on their own:

```bash
python scripts/lint.py draft.txt                      # find patterns
python scripts/lint.py post.txt --genre sns           # social posts: section emoji and one CTA line are normal
python scripts/gate.py before.txt after.txt           # check a rewrite
python scripts/gate.py brief.txt draft.txt --mode write
python scripts/linebreak.py draft.txt out.txt         # one sentence per line (--target markdown | html)
python scripts/lint.py report.txt --style ste         # reports: ASD-STE100 sentence and paragraph limits
```

Exit codes: `lint.py` returns 0 (no S1), 1 (S1 found) or 3 (error).
`gate.py` returns 0 (pass), 1 (warn), 2 (reject) or 3 (error).

## How it was tested

The skill went through 46 test rounds in 8 batches.
In each round one agent applied the skill to a text, and a second agent judged the result against a research summary without reading the skill.
Inputs covered blog posts, notices, op-eds, news stories, press releases, cover letters, Korean job applications, customer replies, product pages, YouTube descriptions, LinkedIn posts, messenger replies, technical docs and three human-written control texts.
The last batch, which included texts the skill had never seen, had no major findings and no script errors.
The full log (in Korean) is in [tests/selftest-log.md](tests/selftest-log.md).

Known limits:

- The reviewers were also language models, not human editors.
- `lint.py` uses regular expressions.
  It misses reworded patterns, so the skill also asks for a human read.
- Most rule documents are in Korean.
  The English pattern list (`references/en-patterns.md`) is in English.

## Changes

- 1.1.1: STE-2 no longer counts a numbered list with indented continuation lines as one paragraph.
- 1.1.0: one sentence per line (`linebreak.py`, gate check `linebreak`); ASD-STE100 report format (`--style ste`, SKILL.md 6-1); structural checks for a two-sentence punchline title, a labelled three-line summary and runs of very short sentences (KO-S1, KO-S2, KO-E4, EN-S1, EN-S2, EN-L5).
  44 unit tests.
- 1.0.0: first release.

## Files

| Path | Contents |
|---|---|
| `SKILL.md` | Workflow, core rules, the ASD-STE100 report format and the 67 judgment rules that came out of testing |
| `references/ko-patterns.md` | Korean patterns, each with its severity and fix |
| `references/en-patterns.md` | English patterns and human signals to keep |
| `references/recipes.md` | Before/after examples |
| `references/evidence.md` | Research findings and sources |
| `references/LICENSES.md` | Upstream licenses and what was changed |
| `scripts/` | `lint.py`, `gate.py`, `linebreak.py`, `selftest.py` |
| `tests/selftest-log.md` | Test log |

## Credits and license

MIT License.
See [LICENSE](LICENSE).

This skill adapts rules from two MIT-licensed projects.
Their copyright notices and the list of changes are in [references/LICENSES.md](references/LICENSES.md).

- [stop-slop](https://github.com/hardikpandya/stop-slop) by Hardik Pandya: English phrase and structure lists
- [im-not-ai](https://github.com/epoko77-ai/im-not-ai) by epoko77-ai: Korean pattern taxonomy and measurements

Wikipedia's "Signs of AI writing" and the papers listed in `references/evidence.md` were used as sources of findings.
No text was copied from them beyond short pattern phrases.
