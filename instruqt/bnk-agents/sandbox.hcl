resource "network" "lab" {
  subnet = "10.1.1.0/24"
}

# Simulated BlueField DPU: BNK's data plane runs here in the full lab.
resource "vm" "dpu" {
  image {
    name = "ubuntu:24.04"
  }

  resources {
    cpu    = 8
    memory = 32768
  }

  network {
    id         = resource.network.lab.meta.id
    ip_address = "10.1.1.20"
    aliases    = ["dpu"]
  }
}

# Largest node in the full lab (the Run:ai control plane needs 32 vCPU), so the spike asks for that size.
resource "vm" "gpu" {
  image {
    name = "ubuntu:24.04"
  }

  resources {
    cpu    = 32
    memory = 65536
  }

  network {
    id         = resource.network.lab.meta.id
    ip_address = "10.1.1.21"
    aliases    = ["gpu"]
  }
}

resource "terminal" "dpu" {
  target = resource.vm.dpu
  shell  = "/bin/bash"
}

resource "terminal" "gpu" {
  target = resource.vm.gpu
  shell  = "/bin/bash"
}
