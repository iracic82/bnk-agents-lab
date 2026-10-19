#!/usr/bin/env bash
# Installs the agent team (NeMo Agent Toolkit + the bnk_agents plugin) into its own venv on the control
# node, and puts `labctl agents` on the path through run.sh. Run by track setup.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${AGENTS_VENV:-/opt/bnk-agents}"
export DEBIAN_FRONTEND=noninteractive

# NeMo Agent Toolkit 1.9.0 needs Python 3.11 to 3.13; uv fetches a pinned one so the OS Python doesn't matter.
if ! command -v uv >/dev/null; then
  curl -LsSf https://astral.sh/uv/0.12.21/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh >/dev/null
fi
uv venv -q --python 3.12 "$VENV"
uv pip install -q --python "$VENV/bin/python" "$HERE"
"$VENV/bin/nat" --version
chmod +x "$HERE/run.sh"
echo "  agent team installed in $VENV; run: bash $HERE/run.sh"
