# GCP Setup with Kestra — Instructions & Notes

This document covers how to connect a GCP Service Account to Kestra running in Docker, and use it to provision a GCS bucket and BigQuery dataset. It also records the issues encountered so future setup is smoother.

---

## Overview of Files

| File | Purpose |
|---|---|
| `print_gcp_key.yaml` | Verifies the GCP service account secret is accessible inside Kestra |
| `gcp_kv.yaml` | Creates the Kestra KV store entries (project ID, bucket name, dataset, location) |
| `gcp_setup.yaml` | Uses the credentials + KV values to create the GCS bucket and BigQuery dataset |

---

## Step 1 — Create a GCP Service Account and Download the JSON Key

1. Go to **GCP Console → IAM & Admin → Service Accounts**
2. Create a new service account and assign the following roles:

   | Role | Why it's needed |
   |---|---|
   | `Storage Admin` | Create and manage GCS buckets |
   | `BigQuery Admin` | Create datasets and tables |
   | `BigQuery Data Editor` | Read/write data in BigQuery |
   | `Viewer` | Basic read access across the project |

3. Download the key as a JSON file (e.g. `kestra-sandbox-xxxx.json`)

> **Important:** Use the **Project ID** (e.g. `my-project-123`), not the Project Name. They are different. You can find the Project ID on the GCP Console home page.

---

## Step 2 — Encode the JSON Key as Base64

The key needs to be base64-encoded before it can be passed as an environment variable.

Run this command from the directory containing your JSON key file:

```bash
echo "SECRET_GCP_SERVICE_ACCOUNT=`cat kestra-sandbox-*.json | base64 -w 0`" > .env
```

This creates a `.env` file with the encoded key stored under the variable name `SECRET_GCP_SERVICE_ACCOUNT`.

> **Note:** The `SECRET_` prefix is required — Kestra automatically picks up environment variables with this prefix and makes them available as secrets inside flows.

---

## Step 3 — Add the `.env` File to Docker Compose

In your `docker-compose.yml`, tell the Kestra service to load the `.env` file:

```yaml
services:
  kestra:
    env_file:
      - .env
```

Restart Kestra after making this change:

```bash
docker compose down && docker compose up -d
```

---

## Step 4 — Verify the Secret is Accessible in Kestra

Run the `print_gcp_key.yaml` flow in Kestra. It should print the base64-encoded key in the task logs. If it prints nothing or errors, the secret is not being picked up — double-check the `.env` file and docker compose config.

---

## Step 5 — Populate the KV Store

Run the `gcp_kv.yaml` flow to create the following key-value pairs in Kestra:

| Key | Example Value |
|---|---|
| `GCP_PROJECT_ID` | `my-project-123` |
| `GCP_BUCKET_NAME` | `my-kestra-bucket` (must be globally unique) |
| `GCP_DATASET` | `zoomcamp_dataset` |
| `GCP_LOCATION` | `US` |

---

## Step 6 — Run the GCP Setup Flow

Run the `gcp_setup.yaml` flow. It will:

1. Print the encoded key (sanity check)
2. Create the GCS bucket (skips if it already exists)
3. Create the BigQuery dataset (skips if it already exists)

---

## Gitignore — Files That Must NOT Be Committed

Add the following to your `.gitignore` to prevent secrets from being pushed to GitHub:

```
*.json
.env
.env_encoded
```

---

## Issues Faced

### Key Issue — Passing the GCP Credential into Kestra

Getting the service account JSON into Kestra via Docker was the trickiest part. The solution:

1. Encode the JSON as base64 (a single-line string that's safe to store as an env var)
2. Write it to a `.env` file with the `SECRET_` prefix
3. Load the `.env` file in docker compose
4. Access it inside Kestra flows as `{{ secret('GCP_SERVICE_ACCOUNT') }}`

### Common Mistake — Project ID vs Project Name

GCP has both a **Project Name** (human-readable) and a **Project ID** (unique identifier). The KV value and all Kestra flows must use the **Project ID**, not the name. Using the wrong one will cause authentication errors.
