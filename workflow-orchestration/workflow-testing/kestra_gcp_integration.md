# Kestra + GCP Integration — Session Notes

> **Goal:** Securely authenticate Kestra OSS with GCP and send API data to Google Cloud Storage (GCS) using a service account JSON key.

---

## What Was Attempted & Outcome

| Item | Status | Notes |
|---|---|---|
| Use Kestra Secret Store for JSON key | ❌ Failed | Enterprise-only feature, not available in OSS |
| Base64 encode the JSON key | ✅ Worked | Used `base64 -w 0` to avoid line breaks |
| Store encoded key in `.env` file | ✅ Worked | Clean single-line value, no escaping issues |
| Load `.env` into Docker via `env_file` | ✅ Worked | Added `env_file: - .env` in docker-compose.yml |
| Reference `secret()` in Kestra flow | ✅ Worked | Unexpectedly supported in this OSS setup |
| Print key in Kestra logs to verify | ✅ Worked | Confirmed key was loaded and intact |

---

## What Failed & Why

### Kestra Secret Store
- The Secret Store UI in Kestra prompted for an **Enterprise license**
- `secret()` is not officially supported in OSS through the UI Secret Store
- This is a **feature restriction**, not a configuration issue

### Raw JSON as Env Variable
- Multi-line JSON causes **shell escaping issues** inside Docker env vars
- Special characters like `"` and `:` break `.env` file parsing
- **Fix:** Base64 encoding eliminated all formatting issues

---

## What Worked — Step by Step

### Step 1: Base64 Encode the JSON Key

```bash
base64 -w 0 your-keyfile.json
```

> `-w 0` prevents line wrapping — a multi-line base64 string will fail to decode correctly.

---

### Step 2: Create the `.env` File

```bash
# .env
GCP_SERVICE_ACCOUNT=eyJ0eXBlIjoic2VydmljZV9hY2NvdW50...
```

Rules:
- No quotes around the value
- Single line only — no line breaks
- Variable name must match what the Kestra flow references

---

### Step 3: Reference `.env` in `docker-compose.yml`

```yaml
services:
  kestra:
    image: kestra/kestra:latest
    env_file:
      - .env
```

---

### Step 4: Verify Key is Accessible in Kestra

Diagnostic flow used to confirm the key was loaded:

```yaml
id: print_gcp_key
namespace: zoomcamp

tasks:
  - id: print_encoded_key
    type: io.kestra.plugin.scripts.shell.Commands
    env:
      GCP_SA_KEY: "{{ secret('GCP_SERVICE_ACCOUNT') }}"
    commands:
      - echo "Encoded GCP Service Account Key:"
      - echo "${GCP_SA_KEY:0:30}..."    # print first 30 chars only
```

This confirmed:
- `.env` was loaded correctly into the Docker container
- `secret()` templating was accessible in this OSS setup
- Base64 encoded key was intact with no corruption

---

## How It All Connects

```
your-keyfile.json
  └── base64 -w 0 → encoded string
        │
        ▼
.env file
  └── GCP_SERVICE_ACCOUNT=eyJ0eXBlI...
        │
        ▼
docker-compose.yml
  └── env_file: - .env  (loads it into the Kestra container)
        │
        ▼
Kestra Flow
  └── {{ secret('GCP_SERVICE_ACCOUNT') }}  (reads the value)
        │
        ▼
Kestra Logs
  └── Printed successfully ✅
```

---

## Full Flow — API → GCS (Next Step)

```yaml
id: api_to_gcs
namespace: zoomcamp

tasks:

  # Step 1: Decode base64 key to a temp file
  - id: decode_key
    type: io.kestra.plugin.scripts.shell.Commands
    env:
      GCP_SA_KEY: "{{ secret('GCP_SERVICE_ACCOUNT') }}"
    commands:
      - echo $GCP_SA_KEY | base64 -d > /tmp/gcp-key.json

  # Step 2: Fetch data from API
  - id: fetch_api_data
    type: io.kestra.plugin.core.http.Request
    uri: https://your-api-endpoint.com/data
    method: GET

  # Step 3: Write API response to a file
  - id: write_to_file
    type: io.kestra.plugin.core.storage.LocalFiles
    inputs:
      data.json: "{{ outputs.fetch_api_data.body }}"

  # Step 4: Upload to GCS
  - id: upload_to_gcs
    type: io.kestra.plugin.gcp.gcs.Upload
    serviceAccount: /tmp/gcp-key.json
    projectId: your-gcp-project-id
    from: "{{ outputs.write_to_file.uris['data.json'] }}"
    to: gs://your-bucket-name/{{ now() | date('yyyy-MM-dd') }}/data_{{ execution.id }}.json
```

---

## Security Checklist

- [ ] `.env` added to `.gitignore`
- [ ] Raw JSON key file not committed to the repo
- [ ] Service account granted minimal IAM role: `roles/storage.objectCreator`
- [ ] Never print the full key in production logs — use `${GCP_SA_KEY:0:30}...`
- [ ] `/tmp/gcp-key.json` is ephemeral — auto-cleared after flow run

### `.gitignore` entries to add

```
.env
*.json
```

---

## Key Learnings

- `base64 -w 0` is critical — without it the encoded string has line breaks and decoding fails
- The `.env` + `env_file` pattern in Docker Compose is a clean and valid approach for OSS Kestra
- `secret()` templating worked in this OSS setup despite not being officially listed as an OSS feature
- `/tmp` is the right place to write the decoded key — it is ephemeral and not persisted
- Never store the raw JSON key in the project folder or commit it to git

---

## Next Steps

- [ ] Run the full `api_to_gcs` flow above
- [ ] Add dynamic GCS paths using `{{ now() | date('yyyy-MM-dd') }}`
- [ ] Add retry logic for transient API failures
- [ ] Add error alerting (email or Slack notification on failure)
- [ ] Schedule with a cron trigger for automated ingestion

```yaml
# Example cron trigger — runs every day at 6am
triggers:
  - id: daily_schedule
    type: io.kestra.plugin.core.trigger.Schedule
    cron: "0 6 * * *"
```
