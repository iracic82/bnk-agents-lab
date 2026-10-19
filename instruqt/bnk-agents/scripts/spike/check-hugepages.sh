#!/usr/bin/env bash
# Runs the probe below on the gpu VM over ssh (probe source: probes/hugepages.sh).
set -uo pipefail
key=$(mktemp); trap 'rm -f "$key"' EXIT
printf '%s\n' "$SSH_PRIVATE_KEY" > "$key"; chmod 600 "$key"
command -v ssh >/dev/null || apk add -q openssh-client
ssh -i "$key" -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=20 "root@$GPU_IP" bash -s <<'PROBE'
# Same setting the full lab applies on every node (platform/cluster/node-prep.sh).
sysctl -w vm.nr_hugepages=2048 >/dev/null
total=$(awk '/HugePages_Total/ {print $2}' /proc/meminfo)
size=$(awk '/Hugepagesize/ {print $2}' /proc/meminfo)
echo "HugePages_Total=${total} Hugepagesize=${size} kB"
[ "$total" -ge 2048 ] && [ "$size" = 2048 ]
PROBE
