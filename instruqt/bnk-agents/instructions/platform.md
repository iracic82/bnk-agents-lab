# Platform spike

This page checks that a Labs 2.0 sandbox can host the lab before any lab content is written. It runs four
checks on the `gpu` VM:

1. The VM is the size the Run:ai control plane needs.
2. BNK's data plane can reserve its hugepages.
3. Kubernetes' container runtime and kernel modules install.
4. A gretap link between `dpu` and `gpu` passes traffic, the way the lab simulates the PCIe link to the DPU.

<instruqt-task id="platform"></instruqt-task>
