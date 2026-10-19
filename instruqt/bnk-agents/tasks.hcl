resource "task" "platform" {
  description     = "The sandbox can host BNK 2.4 and open-source Run:ai"
  success_message = "Every platform property the full lab depends on holds."

  config {
    target  = resource.vm.gpu
    user    = "root"
    timeout = "10m"
  }

  condition "size" {
    description = "The gpu VM has 32 vCPU and 64 GB"

    check {
      script          = "scripts/spike/check-size.sh"
      failure_message = "The gpu VM is smaller than 32 vCPU / 64 GB."
    }
  }

  condition "hugepages" {
    description = "2048 hugepages of 2 MiB can be reserved (BNK TMM needs 4 GiB)"

    check {
      script          = "scripts/spike/check-hugepages.sh"
      failure_message = "Could not reserve 2048 hugepages."
    }
  }

  condition "kubernetes" {
    description = "containerd and kubeadm install, with the kernel modules Kubernetes needs"

    check {
      script          = "scripts/spike/check-kubernetes.sh"
      failure_message = "containerd, kubeadm or a kernel module failed; see the task log."

      config {
        timeout = "15m"
      }
    }
  }

  condition "gretap" {
    description = "A gretap link between dpu and gpu passes traffic (the simulated PCIe link)"

    check {
      script          = "scripts/spike/check-gretap.sh"
      failure_message = "The gretap link between dpu and gpu did not pass traffic."
    }
  }
}
