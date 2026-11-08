#!/usr/bin/env bash
# Install the newspeak skill into the Claude Code user skills folder.
# Usage:  ./install.sh            (installs to ~/.claude/skills/newspeak)
#         ./install.sh /some/other/path/newspeak
set -euo pipefail

src="$(cd "$(dirname "$0")" && pwd)"
dest="${1:-$HOME/.claude/skills/newspeak}"

if [ "$src" = "$(cd "$(dirname "$dest")" 2>/dev/null && pwd)/$(basename "$dest")" ]; then
  echo "Already in place: $dest"
else
  if [ -e "$dest" ]; then
    # keep the backup outside the skills folder, or Claude Code would load it as a second skill
    mkdir -p "$HOME/.claude/skill-backups"
    backup="$HOME/.claude/skill-backups/newspeak-$(date +%Y%m%d-%H%M%S)"
    mv "$dest" "$backup"
    echo "Moved the previous copy to $backup"
  fi
  mkdir -p "$dest"
  (cd "$src" && tar --exclude=.git --exclude=__pycache__ -cf - .) | (cd "$dest" && tar -xf -)
  echo "Installed to $dest"
fi

py=""
for c in python3 python; do
  # skip launcher stubs that exist but do not run (e.g. the Windows Store alias)
  if command -v "$c" >/dev/null 2>&1 && "$c" -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >/dev/null 2>&1; then
    py="$c"; break
  fi
done
if [ -z "$py" ]; then
  echo "Python was not found. Install Python 3.9+ to use lint.py and gate.py." >&2
  exit 0
fi
PYTHONIOENCODING=utf-8 "$py" "$dest/scripts/selftest.py" | tail -n 1
echo "Done. Restart Claude Code, then type /newspeak or ask Claude to remove the AI tells from a text."
