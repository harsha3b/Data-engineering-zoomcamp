# Provider and Backend Configuration
terraform {
  required_version = ">= 1.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }

  # Uncomment when ready to use GCS backend
  # backend "gcs" {
  #   bucket = "your-terraform-state-bucket"
  #   prefix = "prod"
  # }
}
provider "google" {
  project = var.project
  region  = var.region
  # Terraform will automatically use gcloud CLI credentials (ADC)
  # No credentials file needed!
}

# provider "google" {
#   project     = var.project
#   region      = var.region
#   credentials = file(var.credentials)
# }

# GCS Storage Bucket
resource "google_storage_bucket" "demo-bucket" {
  count         = var.gcs_bucket_name != null ? 1 : 0
  name          = var.gcs_bucket_name
  storage_class = var.gcs_storage_class
  location      = var.location
  force_destroy = false

  uniform_bucket_level_access = true

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 1
    }
    action {
      type = "AbortIncompleteMultipartUpload"
    }
  }
}

# BigQuery Dataset
resource "google_bigquery_dataset" "demo_dataset" {
  count      = var.bq_dataset_name != null ? 1 : 0
  dataset_id = var.bq_dataset_name
  location   = var.location
  delete_contents_on_destroy = true
}