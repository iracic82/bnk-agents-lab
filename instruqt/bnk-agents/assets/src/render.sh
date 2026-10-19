#!/usr/bin/env bash
# Renders the challenge diagrams and notes slides from these HTML sources into ../*.png.
# Needs Google Chrome (headless). Run after editing diagrams.py, notes.py or style.css.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHROME="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
cd "$HERE"
python3 -I diagrams.py
python3 -I notes.py
shot() { "$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=1 \
  --window-size="$2" --virtual-time-budget=2000 --screenshot="$3" "file://$HERE/$1" 2>/dev/null; }
for f in [0-9][0-9]-*.html; do
  # Measure the page, then shoot at exactly that height so there is no empty space below.
  h=$("$CHROME" --headless=new --disable-gpu --window-size=1400,2000 --virtual-time-budget=2000 \
    --run-all-compositor-stages-before-draw --dump-dom "file://$HERE/$f" 2>/dev/null \
    | sed -n 's/.*data-h="\([0-9]*\)".*/\1/p' | head -1)
  shot "$f" "1400,${h:-700}" "../${f%.html}.png"
  echo "  ${f%.html}.png  1400x${h:-700}"
done
for f in notes-*.html; do shot "$f" 1600,900 "../${f%.html}.png"; echo "  ${f%.html}.png"; done
