#!/usr/bin/env bash
# Runs the agent team (NeMo Agent Toolkit) against the live factory, on the control node.
#   run.sh "<question>"            ask the team; a person approves any Run:ai change
#   run.sh                         the default question: is any tenant being refused at the BNK edge?
# Every run gets a fresh Run:ai token (it's short-lived) and the bnk-tenancy-mcp token from its Secret.
set -euo pipefail
LAB_ROOT="${LAB_ROOT:-/root/lab}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="${AGENTS_VENV:-/opt/bnk-agents}"
export KUBECONFIG="${KUBECONFIG:-/etc/kubernetes/admin.conf}"
die() { echo "ERROR: $*" >&2; exit 1; }

[ -x "$VENV/bin/nat" ] || die "the agent team isn't installed; run $HERE/install.sh"

# The LLM: Nemotron on build.nvidia.com by default, any OpenAI-compatible endpoint by override.
if [ -z "${LLM_API_KEY:-}" ] && [ -r /root/.config/lab/llm.env ]; then
  # shellcheck disable=SC1091
  . /root/.config/lab/llm.env
fi
[ -n "${LLM_API_KEY:-}" ] || die "no LLM_API_KEY (Instruqt secret, written to /root/.config/lab/llm.env at setup)"
export LLM_API_KEY
export LLM_BASE_URL="${LLM_BASE_URL:-https://integrate.api.nvidia.com/v1}"
export LLM_MODEL="${LLM_MODEL:-nvidia/nemotron-3.5-super-vl-120b-a12b}"

# Run:ai token for the Run:ai MCP server (it forwards the caller's token to the Run:ai API).
CA="${RUNAI_CA_FILE:-/etc/runai/ca.crt}"
RUNAI_URL="${RUNAI_URL:-https://runai.lab}"
body="$(jq -nc --arg u "${RUNAI_ADMIN_EMAIL:-admin@acme.lab}" --arg p "${RUNAI_ADMIN_PASSWORD:-Lab-Admin-1!}" \
  '{grantType:"password",username:$u,password:$p}')"
RUNAI_TOKEN="$(curl -s --cacert "$CA" -m 20 -X POST "$RUNAI_URL/api/v1/token" -H 'Content-Type: application/json' -d "$body" \
  | jq -r '.accessToken // .access_token // empty')"
[ -n "$RUNAI_TOKEN" ] || die "Run:ai login failed at $RUNAI_URL"
export RUNAI_TOKEN

BNK_MCP_TOKEN="$(kubectl -n bnk-runai-tenancy get secret bnk-tenancy-mcp-token -o jsonpath='{.data.token}' | base64 -d)"
[ -n "$BNK_MCP_TOKEN" ] || die "no bnk-tenancy-mcp token (secret bnk-runai-tenancy/bnk-tenancy-mcp-token)"
export BNK_MCP_TOKEN

svc() { kubectl -n "$1" get svc "$2" -o jsonpath='{.spec.clusterIP}'; }
export RUNAI_MCP_URL="http://$(svc runai-mcp runai-mcp-server):8080/mcp"
export BNK_MCP_URL="http://$(svc bnk-runai-tenancy bnk-tenancy-mcp):8090/mcp"

question="${1:-Is any tenant being refused at the BNK edge? If so, propose the GPU quota that would stop it.}"
exec "$VENV/bin/nat" run --config_file "$HERE/configs/factory-ops.yml" --input "$question"
