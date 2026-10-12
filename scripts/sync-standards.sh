#!/usr/bin/env bash
# Refresh the vendored standards from a source repository's aidocs/ directory.
# Usage: ./scripts/sync-standards.sh /path/to/repo-with-aidocs
set -euo pipefail

SRC="${1:-}"
if [ -z "$SRC" ] || [ ! -d "$SRC/aidocs" ]; then
  echo "usage: $0 /path/to/repo-containing-aidocs" >&2
  exit 2
fi

DEST="$(cd "$(dirname "$0")/.." && pwd)/standards"
FILES=(
  python_code_style.ai.md
  django_standards.ai.md
  implementation_standards.ai.md
  technical_standards.ai.md
)

changed=0
for f in "${FILES[@]}"; do
  if [ ! -f "$SRC/aidocs/$f" ]; then
    echo "MISSING in source: $f" >&2
    continue
  fi
  if cmp -s "$SRC/aidocs/$f" "$DEST/$f"; then
    echo "  unchanged  $f"
  else
    diff -u "$DEST/$f" "$SRC/aidocs/$f" | head -40 || true
    cp "$SRC/aidocs/$f" "$DEST/$f"
    echo "  UPDATED    $f"
    changed=$((changed + 1))
  fi
done

echo "done. $changed file(s) updated."
