#!/usr/bin/env bash
# Builds the simulated PCIe link the full lab uses (platform/cluster/pcie-overlay.sh): a gretap tunnel
# between gpu and dpu, bridged, then pings across it. Runs on gpu and builds the dpu end over ssh.
set -uo pipefail
GPU=10.1.1.21 DPU=10.1.1.20

# One end of the link: gretap + bridge, with a MAC derived from the bridge address. Cloned VMs can
# share machine-id, which gives both bridges the same MAC and drops every frame (seen in the old lab).
hexip() { local IFS=.; set -- $1; printf '%02x:%02x:%02x:%02x' "$1" "$2" "$3" "$4"; }
link() { # local remote bridge-cidr
  local mac="02:00:$(hexip "${3%/*}")"
  cat <<EOF
set -e
modprobe ip_gre
ip link del pcie 2>/dev/null || true; ip link del br0 2>/dev/null || true
ip link add pcie type gretap local $1 remote $2 key 1
ip link set pcie mtu 1462 up
ip link add br0 type bridge
ip link set br0 address $mac
ip link set pcie master br0
ip addr add $3 dev br0
ip link set br0 up
EOF
}

bash -c "$(link $GPU $DPU 10.1.20.21/24)" || { echo "gpu end of the gretap link failed"; exit 1; }
echo "gpu end up: $(ip -br addr show br0)"

ssh_opts="-o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=10"
if ! ssh $ssh_opts root@dpu true 2>/tmp/ssh.err; then
  echo "cannot ssh from gpu to dpu, so the dpu end could not be built: $(cat /tmp/ssh.err)"
  exit 2
fi
ssh $ssh_opts root@dpu "$(link $DPU $GPU 10.1.20.20/24)" || { echo "dpu end of the gretap link failed"; exit 1; }
echo "dpu end up: $(ssh $ssh_opts root@dpu ip -br addr show br0)"

ping -c 3 -W 2 10.1.20.20
