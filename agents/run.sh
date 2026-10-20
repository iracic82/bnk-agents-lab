#!/usr/bin/env bash
# Runs the agent team (NeMo Agent Toolkit) against the live factory, on the control node.
#   run.sh "<question>"            ask the team; a person approves any Run:ai change
#   run.sh                         the default question: is any tenant being refused at the BNK edge?
#   AGENTS_CONFIG=<file> run.sh    run a different team definition (challenge 9 edits a copy)
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
# Record the run, typed answers included, for the Topology tab's agent trace. script(1) keeps the
# real terminal, so the approval prompt still reads from the keyboard.
log_dir=/var/log/bnk-agents
mkdir -p "$log_dir"
printf '# question: %s\n' "$question" > "$log_dir/last-run.log"
# NAT asks about anonymous usage telemetry on first run. In a shared lab, keep it off and skip the question.
export NAT_TELEMETRY_ENABLED="${NAT_TELEMETRY_ENABLED:-false}"
# A healthy reply starts streaming within seconds. Give up on a silent one after 45 s, not 120 s, so the
# retry in factory-ops.yml kicks in sooner.
export LANGCHAIN_OPENAI_STREAM_CHUNK_TIMEOUT_S="${LANGCHAIN_OPENAI_STREAM_CHUNK_TIMEOUT_S:-45}"
# quiet_nat runs NAT's own CLI with tool-registration and import noise turned down.
cmd=$(printf '%q ' "$VENV/bin/python" -m bnk_agents.quiet_nat run --config_file "${AGENTS_CONFIG:-$HERE/configs/factory-ops.yml}" --input "$question")
exec script -q -a -e -c "$cmd" "$log_dir/last-run.log"
