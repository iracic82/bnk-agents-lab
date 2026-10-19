#!/usr/bin/env bash
# Runs the probe below on the gpu VM over ssh (probe source: probes/kubernetes.sh).
set -uo pipefail
key=$(mktemp); trap 'rm -f "$key"' EXIT
printf '%s\n' "$SSH_PRIVATE_KEY" > "$key"; chmod 600 "$key"
command -v ssh >/dev/null || apk add -q openssh-client
ssh -i "$key" -o StrictHostKeyChecking=no -o BatchMode=yes -o ConnectTimeout=20 "root@$GPU_IP" bash -s <<'PROBE'
# The node prerequisites from platform/cluster/node-prep.sh, minus the cluster join.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
for m in overlay br_netfilter ip_gre; do
  modprobe "$m" && echo "module $m: loaded"
done
apt-get update -qq
apt-get install -y -qq containerd curl gpg >/dev/null
echo "containerd: $(containerd --version)"
K8S_MINOR=1.30
install -d /etc/apt/keyrings
curl -fsSL "https://pkgs.k8s.io/core:/stable:/v${K8S_MINOR}/deb/Release.key" \
  | gpg --dearmor --yes -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
echo "deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v${K8S_MINOR}/deb/ /" \
  > /etc/apt/sources.list.d/kubernetes.list
apt-get update -qq
apt-get install -y -qq kubelet kubeadm kubectl >/dev/null
echo "kubeadm: $(kubeadm version -o short)"
PROBE
