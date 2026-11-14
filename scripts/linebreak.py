#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""newspeak / linebreak.py: put each sentence on its own line.

A line break goes after every sentence-ending period, question mark and exclamation mark
that still has text after it on the same line. Decimals (8.5), numbered-list markers (1.),
ellipses (..., …), initials (J.), common English abbreviations (e.g., Dr., U.S.), code,
URLs, headings, table rows and double-quoted spans are left alone (same detector as lint FMT-LB).

  python linebreak.py IN [OUT]                 # plain text: "\\n"
  python linebreak.py IN OUT --target markdown # rendered Markdown: two trailing spaces + "\\n"
  python linebreak.py IN OUT --target html     # HTML: "<br>\\n"

List items keep their indent: "- A. B." becomes "- A." and "  B.".
Exit codes: 0 done | 3 error
"""
from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lint  # noqa: E402

BREAKS = {"text": "\n", "markdown": "  \n", "html": "<br>\n"}
_MARK = re.compile(r"^(\s*(?:[-*•>]|\d+[.)])\s+)")


def break_lines(text: str, target: str = "text") -> str:
    text = lint.normalize(text)
    hits = lint.inline_sentence_ends(text)
    if not hits:
        return text
    br = BREAKS[target]
    by_line = {}
    for li, col in hits:
        by_line.setdefault(li, []).append(col)
    lines = text.split("\n")
    out = []
    for li, line in enumerate(lines):
        cols = by_line.get(li)
        if not cols:
            out.append(line)
            continue
        m = _MARK.match(line)
        indent = " " * len(m.group(1)) if m else re.match(r"\s*", line).group(0)
        pieces, start = [], 0
        for col in sorted(cols):
            pieces.append(line[start:col + 1].rstrip())
            start = col + 1
            while start < len(line) and line[start] in " \t":
                start += 1
        pieces.append(line[start:])
        out.append((br + indent).join(pieces))
    return "\n".join(out)


def main(argv=None) -> int:
    lint._configure_stdout()
    ap = argparse.ArgumentParser(description="Put each sentence on its own line.")
    ap.add_argument("infile", help="text file, or - for stdin")
    ap.add_argument("outfile", nargs="?", help="output file (default: stdout)")
    ap.add_argument("--target", choices=sorted(BREAKS), default="text")
    try:
        a = ap.parse_args(argv)
        res = break_lines(lint.read_text(a.infile), a.target)
        if a.outfile:
            with open(a.outfile, "w", encoding="utf-8", newline="\n") as f:
                f.write(res)
        else:
            sys.stdout.write(res)
    except SystemExit as e:
        return 3 if e.code not in (0, None) else 0
    except Exception as e:  # never crash with a traceback
        print(f"linebreak error: {type(e).__name__}: {e}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
