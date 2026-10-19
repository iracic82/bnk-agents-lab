# Lab nodes as Compute Engine VMs in the sandbox's own GCP project. Spike: dpu and gpu only.
terraform {
  required_providers {
    google = { source = "hashicorp/google", version = "~> 6.0" }
    tls    = { source = "hashicorp/tls", version = "~> 4.0" }
  }
}

variable "zone" {
  type = string
}

provider "google" {
  zone = var.zone
}

resource "tls_private_key" "lab" {
  algorithm = "ED25519"
}

resource "google_compute_network" "lab" {
  name                    = "lab"
  auto_create_subnetworks = false
}

resource "google_compute_subnetwork" "lab" {
  name          = "lab"
  network       = google_compute_network.lab.id
  ip_cidr_range = "10.1.1.0/24"
}

# All traffic between lab nodes, GRE (IP protocol 47) included: the simulated PCIe link is a gretap tunnel.
resource "google_compute_firewall" "internal" {
  name          = "lab-internal"
  network       = google_compute_network.lab.id
  source_ranges = ["10.1.1.0/24"]
  allow { protocol = "all" }
}

resource "google_compute_firewall" "ssh" {
  name          = "lab-ssh"
  network       = google_compute_network.lab.id
  source_ranges = ["0.0.0.0/0"]
  allow {
    protocol = "tcp"
    ports    = ["22"]
  }
}

locals {
  nodes = {
    dpu = { machine_type = "n2-standard-8", ip = "10.1.1.20" }
    gpu = { machine_type = "n2-standard-32", ip = "10.1.1.21" }
  }
}

resource "google_compute_instance" "node" {
  for_each     = local.nodes
  name         = each.key
  machine_type = each.value.machine_type

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2404-lts-amd64"
      size  = 100
    }
  }

  network_interface {
    subnetwork = google_compute_subnetwork.lab.id
    network_ip = each.value.ip
    access_config {}
  }

  metadata = {
    ssh-keys = "root:${tls_private_key.lab.public_key_openssh}"
  }

  # Root ssh with the lab key, from the console and between nodes (as in the classic track).
  metadata_startup_script = <<-EOF
    #!/bin/bash
    sed -i 's/^#\?PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
    systemctl restart ssh
    install -d -m 700 /root/.ssh
    printf '%s' '${tls_private_key.lab.private_key_openssh}' > /root/.ssh/id_ed25519
    chmod 600 /root/.ssh/id_ed25519
    printf '10.1.1.20 dpu\n10.1.1.21 gpu\n' >> /etc/hosts
  EOF
}

output "ssh_private_key" {
  value     = tls_private_key.lab.private_key_openssh
  sensitive = true
}

output "dpu_ip" {
  value = google_compute_instance.node["dpu"].network_interface[0].access_config[0].nat_ip
}

output "gpu_ip" {
  value = google_compute_instance.node["gpu"].network_interface[0].access_config[0].nat_ip
}

output "dpu_internal_ip" {
  value = google_compute_instance.node["dpu"].network_interface[0].network_ip
}

output "gpu_internal_ip" {
  value = google_compute_instance.node["gpu"].network_interface[0].network_ip
}
