#!/usr/bin/env bash
# Same setting the full lab applies on every node (platform/cluster/node-prep.sh).
sysctl -w vm.nr_hugepages=2048 >/dev/null
total=$(awk '/HugePages_Total/ {print $2}' /proc/meminfo)
size=$(awk '/Hugepagesize/ {print $2}' /proc/meminfo)
echo "HugePages_Total=${total} Hugepagesize=${size} kB"
[ "$total" -ge 2048 ] && [ "$size" = 2048 ]
