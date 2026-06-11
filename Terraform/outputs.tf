# VM Outputs
output "vm_instance_name" {
  description = "Name of the VM instance"
  value       = google_compute_instance.de_sandbox.name
}

output "vm_instance_id" {
  description = "Instance ID of the VM"
  value       = google_compute_instance.de_sandbox.id
}

output "vm_static_ip" {
  description = "Static external IP address of the VM"
  value       = google_compute_address.de_static_ip.address
}

output "vm_public_ip" {
  description = "Public IP address of the VM"
  value       = google_compute_instance.de_sandbox.network_interface[0].access_config[0].nat_ip
}

output "vm_internal_ip" {
  description = "Internal IP address of the VM"
  value       = google_compute_instance.de_sandbox.network_interface[0].network_ip
}

output "vm_zone" {
  description = "Zone where VM is deployed"
  value       = google_compute_instance.de_sandbox.zone
}

# GCS Bucket Output (if created)
output "gcs_bucket_name" {
  description = "Name of the created GCS bucket"
  value       = try(google_storage_bucket.demo-bucket[0].name, null)
}

# BigQuery Dataset Output (if created)
output "bigquery_dataset_id" {
  description = "ID of the created BigQuery dataset"
  value       = try(google_bigquery_dataset.demo_dataset[0].dataset_id, null)
}
