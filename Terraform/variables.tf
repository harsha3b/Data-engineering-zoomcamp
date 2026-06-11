
# variable "credentials" {
#   description = "Path to Service Account JSON file"
#   type        = string
#   sensitive   = true
#   # ex: ./keys/my-creds.json
# }

variable "project" {
  description = "GCP Project ID"
  type        = string
}

variable "project_zone" {
  description = "Project Zone"
  type        = string
  default     = "us-central1-a"
}

variable "region" {
  description = "Region"
  type        = string
  default     = "us-central1"
}

variable "location" {
  description = "Project Location"
  type        = string
  default     = "US"
}

# VM Configuration Variables
variable "vm_name" {
  description = "Name of the VM instance"
  type        = string
  default     = "data-engineering-vm"
}

variable "machine_type" {
  description = "GCP machine type (e.g., e2-medium, e2-highmem-4)"
  type        = string
  default     = "e2-highmem-4" # 4 vCPUs, 32GB RAM
}

variable "boot_disk_image" {
  description = "Boot disk image"
  type        = string
  default     = "ubuntu-os-cloud/ubuntu-2204-lts"
}

variable "boot_disk_size" {
  description = "Boot disk size in GB"
  type        = number
  default     = 50
}

variable "boot_disk_type" {
  description = "Boot disk type (pd-standard or pd-ssd)"
  type        = string
  default     = "pd-standard"
}

variable "network" {
  description = "VPC network name"
  type        = string
  default     = "default"
}

variable "network_tags" {
  description = "Network tags for firewall rules"
  type        = list(string)
  default     = ["http-server", "https-server"]
}

variable "startup_script" {
  description = "Startup script to run on VM boot"
  type        = string
  default     = ""
}

# BigQuery and GCS Variables
variable "bq_dataset_name" {
  description = "BigQuery Dataset Name"
  type        = string
  default     = null
}

variable "gcs_bucket_name" {
  description = "GCS Storage Bucket Name"
  type        = string
  default     = null
}


variable "gcs_storage_class" {
  description = "Bucket Storage Class"
  type        = string
  default     = "STANDARD"
}

variable "log_bucket_name" {
  description = "GCS bucket for storing access logs"
  type        = string
  sensitive   = true
  default     = null
}