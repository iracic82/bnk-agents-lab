#!/usr/bin/env bash
# Runs the probe below on the gpu VM over ssh (probe source: probes/size.sh).
set -uo pipefail
key=$(mktemp); trap 'rm -f "$key"' EXIT
printf '%s\n' "$SSH_PRIVATE_KEY" > "$key"; chmod 600 "$key"
command -v ssh >/dev/null || apk add -q openssh-client
ssh -i "$key" -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=20 "root@$GPU_IP" bash -s <<'PROBE'
cpus=$(nproc)
mem_mb=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)
echo "gpu: ${cpus} vCPU, ${mem_mb} MB RAM, kernel $(uname -r)"
grep -m1 'model name' /proc/cpuinfo
# The guest sees slightly less than the configured memory, so allow 5% headroom.
[ "$cpus" -ge 32 ] && [ "$mem_mb" -ge $((131072 * 95 / 100)) ]
PROBE
