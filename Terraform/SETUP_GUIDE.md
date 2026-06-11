# GCP VM Setup Guide

This Terraform configuration provisions a data engineering VM on Google Cloud Platform.

## Prerequisites

1. **GCP Account & Project**
   - Create a GCP project at https://console.cloud.google.com
   - Note your Project ID 

2. **Service Account**
   - Go to IAM & Admin → Service Accounts
   - Create a new service account with "Compute Admin" and "Editor" roles
   - Create a JSON key and save it to `./keys/my-service-account.json`

3. **Terraform Installed**
   ```bash
   # Check if installed
   terraform version
   # If not, download from https://www.terraform.io/downloads.html
   ```

4. **Enable Required APIs**
   In GCP Console, enable:
   - Compute Engine API
   - Cloud Resource Manager API
   - Cloud Storage API (if using GCS)
   - BigQuery API (if using BigQuery)

## Setup Steps

### 1. Configure Variables
```bash
# Copy the example file
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars with your values
```

**Required values to update:**
- `credentials` - Path to your service account JSON file if doing using keys
- `project` - Your GCP project ID (credible-torus-499011-g5)

### 2. Initialize Terraform
```bash
terraform init
```

### 3. Plan the Deployment
```bash
terraform plan
```
Review the resources that will be created.

### 4. Apply Configuration
```bash
terraform apply
```
Confirm by typing `yes` when prompted.

### 5. Get VM Details
After deployment completes, Terraform outputs:
- **vm_public_ip** - SSH into your VM at this IP
- **vm_instance_name** - Name of your instance
- **vm_internal_ip** - Internal IP for GCP networking

## Access Your VM

'''VS code

# SSH into your VM (from VS code)
press f1 or ctrl+shift+p to open the command palette.
# you can see the projectid and details of the gcp vm here and connect to it
type and select remote-ssh: connect to host

# to close connection to VM from vscode
press f1 or ctrl+shift+p (cmd+shift+p on mac).
type remote-ssh: close remote connection and press
'''

```bash
# SSH into your VM (from gcloud CLI or web console)
gcloud compute ssh data-engineering-vm --zone=us-central1-a

# if the above failed try this in terminal
gcloud compute config-ssh

# Or use the public IP directly if your key is set up
ssh -i ~/.ssh/google_compute_engine ubuntu@<PUBLIC_IP>
```

## Common Operations

### Scale VM (Change Machine Type)
Edit `terraform.tfvars`:
```hcl
machine_type = "e2-highmem-8"  # Change to desired size
```
Then:
```bash
terraform plan
terraform apply
```

### Add More Storage
Edit `terraform.tfvars`:
```hcl
boot_disk_size = 100  # Increase size
```

### Destroy VM
```bash
terraform destroy
```
Confirm by typing `yes`.

## VM Machine Types Reference

| Type | vCPUs | Memory | Cost |
|------|-------|--------|------|
| e2-medium | 1 | 4GB | Low |
| e2-standard-4 | 4 | 16GB | Medium |
| e2-highmem-4 | 4 | 32GB | Medium-High |
| e2-highmem-8 | 8 | 64GB | High |

## Troubleshooting

**\"credentials file not found\"**
- Ensure service account JSON is at `./keys/my-service-account.json`

**\"Permission denied\"**
- Verify service account has \"Compute Admin\" role in IAM

**\"Quota exceeded\"**
- Check GCP quotas for your region
- Try a different zone or request quota increase

## Cost Optimization Tips

- Use `e2-medium` for development/testing
- Delete VM when not needed with `terraform destroy`
- Use preemptible VMs for cost savings (add to main.tf if needed)
