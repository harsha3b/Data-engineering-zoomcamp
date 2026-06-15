# Kestra GCP Setup — Troubleshooting Report

**Flow:** `gcp_setup` | **Namespace:** `zoomcamp` | **Date:** June 15, 2026

---

## Summary

| Metric | Count |
|---|---|
| Total Issues Encountered | 5 |
| Issues Resolved | 5 |
| Root Cause Categories | 3 (Kestra Config, GCP Permissions, GCP Billing) |

---

## Issue Log

### Issue 1 — `IllegalVariableEvaluationException`

**Error:**
```
Unable to find `SECRET_GCP_SERVICE_ACCOUNT` used in the expression `{{ envs.SECRET_GCP_SERVICE_ACCOUNT | base64decode }}`
```

**Root Cause:**
Kestra automatically prepends `SECRET_` when resolving `envs.*` variables. Writing `{{ envs.GCP_SERVICE_ACCOUNT }}` in the flow makes Kestra look for `SECRET_GCP_SERVICE_ACCOUNT` in the environment. The variable in `.env` was not named with the `SECRET_` prefix, so the lookup failed.

**Resolution:**
Renamed the variable in the `.env` file to `SECRET_GCP_SERVICE_ACCOUNT`. Alternatively, use `{{ secret('GCP_SERVICE_ACCOUNT') }}` in the flow which handles the prefix automatically.

---

### Issue 2 — `PebbleException` on `base64decode`

**Error:**
```
Please provide a correctly Base64 encoded string containing a UTF-8 string
({{ secret('GCP_SERVICE_ACCOUNT') | base64decode }}:1)
```

**Root Cause:**
Kestra's `secret()` function automatically decodes base64 secrets internally before returning the value. Applying `| base64decode` on top tried to decode an already-decoded JSON string, which broke the filter.

**Resolution:**
Removed `| base64decode` from `pluginDefaults`. The correct reference is:
```yaml
serviceAccount: "{{ secret('GCP_SERVICE_ACCOUNT') }}"
```
Kestra handles decoding internally so the GCP plugin receives clean JSON directly.

---

### Issue 3 — `403 Forbidden` — Missing IAM Permissions

**Error:**
```
403 harsha-kestra-zoomcamp@kestra-sandbox-499212.iam.gserviceaccount.com does not have
storage.buckets.create access to the Google Cloud project.
```

**Root Cause:**
The service account was authenticated correctly but had no IAM roles assigned in the GCP project — it had zero permissions to create any resources.

**Resolution:**
Assigned the following roles to the service account in **GCP Console → IAM & Admin → IAM**:

| Role | Purpose |
|---|---|
| `Storage Admin` | Create and manage GCS buckets |
| `BigQuery Data Editor` | Create and manage BigQuery datasets |
| `BigQuery Job User` | Run BigQuery jobs |
| `Owner` | Full project access |

---

### Issue 4 — `403 Forbidden` — Bucket Name Typo

**Error:**
```
Permission 'storage.buckets.create' denied on resource
'//storage.googleapis.com/projects/_/buckets/kestra-sandox-harsha-314'
```

**Root Cause:**
Typo in the KV Store value for `GCP_BUCKET_NAME` — `sandox` instead of `sandbox`. GCP could not resolve the malformed bucket name.

**Resolution:**
Corrected the bucket name in **Kestra UI → Namespaces → zoomcamp → KV Store**:

| | Value |
|---|---|
| ❌ Before | `kestra-sandox-harsha-314` |
| ✅ After | `kestra-sandbox-harsha-314` |

---

### Issue 5 — `403 Forbidden` — Wrong Project ID + Billing Disabled

**Error:**
```
403 The billing account for the owning project is disabled in state absent
POST https://storage.googleapis.com/storage/v1/b?project=kestra-sandbox
```

**Root Cause:**
Two problems combined:
1. `GCP_PROJECT_ID` in the KV Store was set to `kestra-sandbox` instead of the full project ID `kestra-sandbox-499212`. Requests were going to the wrong project.
2. That wrong project had no billing account linked, so GCP blocked all resource creation.

**Resolution:**
1. Corrected `GCP_PROJECT_ID` in KV Store to `kestra-sandbox-499212`
2. Linked an active billing account in **GCP Console → Billing → Link a billing account**

---

## Reference — Kestra Variable Resolution

| Where Key is Stored | Correct Kestra Reference | Notes |
|---|---|---|
| Docker `.env` as `SECRET_XYZ` | `{{ secret('XYZ') }}` | Kestra prepends `SECRET_` automatically — do not include it in the flow |
| Docker `.env` as `SECRET_XYZ` | `{{ envs.XYZ }}` | Same rule — `envs.XYZ` looks for `SECRET_XYZ` in the environment |
| Kestra KV Store | `{{ kv('KEY_NAME') }}` | Used for non-secret config like project ID, bucket name, location |
| Kestra Secrets UI | `{{ secret('KEY_NAME') }}` | Managed secrets via the Kestra UI secrets manager |

---

## Final Working KV Store Values

| KV Key | Correct Format | Example |
|---|---|---|
| `GCP_PROJECT_ID` | Full project ID including numeric suffix | `kestra-sandbox-499212` |
| `GCP_BUCKET_NAME` | Globally unique, no typos | `kestra-sandbox-harsha-314` |
| `GCP_DATASET` | BigQuery dataset name | `zoomcamp_dataset` |
| `GCP_LOCATION` | GCP region or multi-region | `US` or `europe-west1` |

---

## Final Working Flow

```yaml
id: gcp_setup
namespace: zoomcamp

tasks:
  - id: print_encoded_key
    type: io.kestra.plugin.scripts.shell.Commands
    env:
      GCP_SA_KEY: "{{ secret('GCP_SERVICE_ACCOUNT') }}"
    commands:
      - echo "Verifying GCP key..."
      - echo "$GCP_SA_KEY" | python3 -c "import sys, json; d=json.load(sys.stdin); print('Auth OK - project:', d['project_id'], '| client:', d['client_email'])"

  - id: create_gcs_bucket
    type: io.kestra.plugin.gcp.gcs.CreateBucket
    ifExists: SKIP
    storageClass: REGIONAL
    name: "{{ kv('GCP_BUCKET_NAME') }}"

  - id: create_bq_dataset
    type: io.kestra.plugin.gcp.bigquery.CreateDataset
    name: "{{ kv('GCP_DATASET') }}"
    ifExists: SKIP

pluginDefaults:
  - type: io.kestra.plugin.gcp
    values:
      serviceAccount: "{{ secret('GCP_SERVICE_ACCOUNT') }}"
      projectId: "{{ kv('GCP_PROJECT_ID') }}"
      location: "{{ kv('GCP_LOCATION') }}"
      bucket: "{{ kv('GCP_BUCKET_NAME') }}"
```
