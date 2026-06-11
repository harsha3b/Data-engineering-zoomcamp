# Static External IP Address
resource "google_compute_address" "de_static_ip" {
  name         = "${var.vm_name}-static-ip"
  address_type = "EXTERNAL"
  region       = var.region
  address      = null  # Let GCP assign an available static IP
}

# Data Engineering VM on GCP
resource "google_compute_instance" "de_sandbox" {
  name         = var.vm_name
  machine_type = var.machine_type
  zone         = var.project_zone

  # configure the operating system (ubuntu 22.04 lts)
  boot_disk {
    initialize_params {
      image = var.boot_disk_image
      size  = var.boot_disk_size
      type  = var.boot_disk_type
    }
  }

  # connect the machine to the default gcp network so it has internet access
  network_interface {
    network = var.network
    access_config {
      nat_ip = google_compute_address.de_static_ip.address
    }
  }

  # metadata tag to allow ssh access
  metadata = {
    block-project-ssh-keys = false
  }

  # Add startup script (optional)
  metadata_startup_script = var.startup_script

  tags = var.network_tags
}