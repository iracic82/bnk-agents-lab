# Each sandbox gets its own GCP project. Terraform creates the lab's VMs in it as ordinary Compute Engine
# machines, so their size is not limited by the sandbox host.
resource "google_project" "factory" {
  regions  = ["europe-west1"]
  services = ["compute.googleapis.com"]

  # The learner's Google Cloud console login, read-only: the lab is driven from the terminals.
  user "learner" {
    roles = ["roles/viewer"]
  }

  service_account "lab" {
    roles = ["roles/compute.admin", "roles/iam.serviceAccountUser"]
  }
}

resource "template" "gcp_key" {
  source      = resource.google_project.factory.service_account.0.key
  destination = "${data("google")}/key.json"
}

resource "terraform" "nodes" {
  source = "files/terraform"

  volume {
    source      = resource.template.gcp_key.destination
    destination = "/tmp/key.json"
  }

  variables = {
    zone = "europe-west1-b"
  }

  environment = {
    GOOGLE_APPLICATION_CREDENTIALS = "/tmp/key.json"
    GOOGLE_PROJECT                 = resource.google_project.factory.project_id
    GOOGLE_REGION                  = resource.google_project.factory.regions.0
  }
}

# The learner's shell, and where task checks run: reaches the lab's GCP VMs over ssh.
resource "container" "console" {
  image {
    name = "gcr.io/google.com/cloudsdktool/google-cloud-cli:alpine"
  }

  environment = {
    SSH_PRIVATE_KEY = resource.terraform.nodes.output.ssh_private_key
    DPU_IP          = resource.terraform.nodes.output.dpu_ip
    GPU_IP          = resource.terraform.nodes.output.gpu_ip
    DPU_INTERNAL_IP = resource.terraform.nodes.output.dpu_internal_ip
    GPU_INTERNAL_IP = resource.terraform.nodes.output.gpu_internal_ip
  }

  resources {
    cpu    = 1000
    memory = 1024
  }
}

resource "terminal" "console" {
  target = resource.container.console
  shell  = "/bin/bash"
}
