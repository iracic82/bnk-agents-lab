#!/usr/bin/env bash
cpus=$(nproc)
mem_mb=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)
echo "gpu: ${cpus} vCPU, ${mem_mb} MB RAM, kernel $(uname -r)"
grep -m1 'model name' /proc/cpuinfo
# The guest sees slightly less than the configured memory, so allow 5% headroom.
[ "$cpus" -ge 32 ] && [ "$mem_mb" -ge $((65536 * 95 / 100)) ]
