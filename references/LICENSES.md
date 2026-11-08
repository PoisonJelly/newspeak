# 가져온 자료와 라이선스

This skill adapts material from two MIT-licensed projects. Rules were rewritten, merged, renumbered and changed where research disagreed (see SKILL.md section 7). No code was copied; lint.py and gate.py are new implementations.

## stop-slop

- Source: Hardik Pandya, https://github.com/hardikpandya/stop-slop (https://hvpandya.com), version 2026-01-13
- Used: phrase lists (throat-clearing, emphasis crutches, business jargon, meta-commentary), structure lists (binary contrasts, negative listing, dramatic fragmentation, false agency, narrator-from-a-distance), scoring idea.
- Changed: "no passive voice", "kill all adverbs", "no em dashes at all", "three-item lists -> two", "no Wh- starters", "no lazy extremes" became conditional or were dropped, based on Reinhart 2025 (PNAS), Wikipedia "Signs of AI writing" (human signals), and 2026 em-dash measurements.

```
MIT License

Copyright (c) 2025 Hardik Pandya

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## im-not-ai (humanize-korean)

- Source: epoko77-ai, https://github.com/epoko77-ai/im-not-ai (read 2026-11-08, v2.3.x)
- Used: Korean pattern taxonomy A-J (IDs and many prescriptions, reworded), severity scheme S1-S3, prime directives (fidelity, mood preservation, locality, removal-only, over-polish alarm at 30%/50%), Do-NOT list, empirical findings (9.2x contrast frame, connective commas, long-sentence deficit, weak or reversed signals).
- Changed: contrast frame 'A가 아니라 B' is S1 on first occurrence (the strongest Korean structural signal, 9.2x in im-not-ai's own measurement); added K (chatbot residue, sycophancy) and L (model-specific vocabulary) from the 2026-11 study; gates reimplemented with a smaller, deterministic check set.

```
MIT License

Copyright (c) 2026 epoko77-ai

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Other sources

Wikipedia "Signs of AI writing" (CC BY-SA 4.0) and the research papers listed in `evidence.md` were used as facts and findings only; no text was copied beyond short pattern phrases.
