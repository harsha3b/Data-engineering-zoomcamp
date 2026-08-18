# GCP Dataproc — Reference Notes

*(Dataproc is now branded "Managed Service for Apache Spark" — same `gcloud dataproc` commands, no syntax changes.)*

---

## 1. What is Dataproc

Dataproc is GCP's managed service for running **Apache Spark, Hadoop, Hive, Flink, and Presto** workloads. It spins up a cluster of VMs (master + workers), pre-installed with the Spark/Hadoop stack, and tears down on command. You don't manage the underlying infra — no manual installs, no cluster software patching.

Key building blocks:
- **Cluster** — the set of VMs (1 master, 0+ workers) that run your Spark jobs
- **Job** — a single Spark/PySpark/Hive script submitted to run on a cluster
- **Region/Zone** — where the VMs physically live (pick close to you or your data to avoid latency/egress cost)
- **Staging bucket** — auto-created GCS bucket Dataproc uses for job metadata/logs

---

## 2. Creating a Cluster — CLI

### One-time setup
```bash
gcloud config set project YOUR_PROJECT_ID

gcloud services enable \
  dataproc.googleapis.com \
  compute.googleapis.com \
  storage.googleapis.com \
  cloudresourcemanager.googleapis.com
```

### Sample / testing cluster (cheap, single-node)
Good for tutorials, learning, small datasets (one month of taxi data, etc.)
```bash
gcloud dataproc clusters create nyc-taxi-cluster \
  --region=europe-west3 \
  --zone=europe-west3-a \
  --single-node \
  --master-machine-type=n2-standard-4 \
  --master-boot-disk-size=50 \
  --image-version=2.2-debian12 \
  --optional-components=JUPYTER \
  --enable-component-gateway \
  --max-idle=30m
```

### Production-level cluster (multi-node, resilient)
```bash
gcloud dataproc clusters create prod-spark-cluster \
  --region=europe-west3 \
  --zone=europe-west3-a \
  --master-machine-type=n2-standard-4 \
  --worker-machine-type=n2-standard-8 \
  --num-workers=3 \
  --master-boot-disk-size=100 \
  --worker-boot-disk-size=200 \
  --num-worker-local-ssds=1 \
  --image-version=2.2-debian12 \
  --optional-components=JUPYTER \
  --enable-component-gateway \
  --autoscaling-policy=YOUR_POLICY_NAME \
  --labels=env=production
```
Differences from testing cluster: multiple workers (no single point of failure), bigger machines, larger/SSD-backed disks, autoscaling policy, no `--max-idle` (production clusters usually stay up or are managed by a scheduler), labels for cost tracking.

---

## 3. Notes on Memory Selection

| Machine type | vCPU | RAM | Use case |
|---|---|---|---|
| n2-standard-2 | 2 | 8 GB | Too small — risk of driver OOM (SIGTERM/143) even for moderate parquet reads |
| n2-standard-4 | 4 | 16 GB | Solid minimum for single-node tutorials |
| n2-standard-8 | 8 | 32 GB | Good worker size for real workloads |

**Rules of thumb:**
- On `--single-node`, the driver, YARN, and all executors share **one** machine's RAM — undersizing here fails fast. Prefer 16GB+ (n2-standard-4) even for tutorials.
- **SIGTERM / exit code 143** = OOM kill. Fix by: bigger machine, tuning `spark.driver.memory` / `spark.executor.memory`, or reading less data at once (filter to one month/file instead of `*.parquet`).
- For production, split driver and executor memory explicitly via job properties rather than relying on defaults:
  ```
  --properties=spark.driver.memory=4g,spark.executor.memory=6g,spark.executor.memoryOverhead=1g
  ```
- PD-Standard disks under 1TB have weaker I/O — fine for tutorials, but production jobs with heavy shuffle benefit from local SSDs (`--num-worker-local-ssds`).

---

## 4. Job Submission — Console UI

1. Go to **Dataproc → Jobs → Submit Job**
2. Fill in:
   - **Cluster** — select from dropdown
   - **Job type** — PySpark / Spark / Hive / etc.
   - **Main python file** — GCS path to your script, e.g. `gs://bucket/code/06_spark_sql.py`
   - **Arguments** — any CLI args your script expects (one per line)
   - **Jar files / Python files** — optional extra dependencies
   - **Properties** — optional Spark config overrides (key=value)
3. Click **Submit** — job appears under Dataproc → Jobs with live status and logs link

---

## 5. Job Submission — CLI

```bash
gcloud dataproc jobs submit pyspark \
    --cluster=nyc-taxi-cluster \
    --region=europe-west6 \
    gs://bucket/code/06_spark_sql.py \
    -- \
        --input_green=gs://bucket/pq/green/2020/*/ \
        --input_yellow=gs://bucket/pq/yellow/2020/*/ \
        --output=gs://bucket/report-2020
```
Notes:
- Everything **after the bare `--`** is passed as arguments to your script (accessible via `sys.argv` or `argparse`)
- Everything **before** the bare `--` is Dataproc/Spark configuration

---

## 5a. Job Submission — Writing Output to BigQuery

When the job writes its result via the Spark BigQuery connector (`df.write.format('bigquery')...`), the submit command is simpler than you'd expect — **don't pass `--jars`**:

```bash
gcloud dataproc jobs submit pyspark \
    --cluster=nyc-taxi-cluster \
    --region=europe-west3 \
    gs://spark-tutorial-pq/code/06_spark_sql_bigquerry.py \
    -- \
        --input_green=gs://spark-tutorial-pq/pq/green/2020/01/ \
        --input_yellow=gs://spark-tutorial-pq/pq/yellow/2020/01/ \
        --output=kestra-sandbox-499212.spark_sql_BQ.report-2020-01
```

**Why we removed `--jars=gs://spark-lib/bigquery/spark-bigquery-latest_2.12.jar`:**
We initially submitted with that flag (the connector jar is commonly recommended in older tutorials). The job failed immediately on `spark.read.parquet(...)` with:
```
java.util.ServiceConfigurationError: org.apache.spark.sql.sources.DataSourceRegister:
com.google.cloud.spark.bigquery.BigQueryRelationProvider not a subtype
```
Dataproc image `2.3.34-debian12` already bundles the connector at `/usr/lib/spark/jars/spark-3.5-bigquery-0.42.3.jar`. Adding `--jars` pulled in a *second* copy of the same class, loaded by a different classloader — Spark's `ServiceLoader` found two incompatible versions of `BigQueryRelationProvider` and errored before the job could even read the input parquet files. Dropping `--jars` (letting the cluster use its pre-installed connector) fixed it — no code change needed.

**Second issue after that fix — IAM, not code/jars:**
With `--jars` removed, parquet reads and the Spark SQL transform ran fine, but the BigQuery *write* failed with:
```
403 Permission Denied — bigquery.tables.get denied on table PROJECT:dataset.table (or it may not exist)
```
Cause: the cluster runs as the **default Compute Engine service account** (`PROJECT_NUMBER-compute@developer.gserviceaccount.com`), and newer GCP projects no longer auto-grant it `roles/editor`. It had `roles/dataproc.worker` + `roles/iam.serviceAccountUser` only — no BigQuery access at all. Fixed by granting it BigQuery roles at the project level:
```bash
SA="PROJECT_NUMBER-compute@developer.gserviceaccount.com"
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:${SA}" --role="roles/bigquery.dataEditor" --condition=None

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:${SA}" --role="roles/bigquery.jobUser" --condition=None
```
`bigquery.dataEditor` lets it create/write tables; `bigquery.jobUser` lets it run the load/query jobs the connector issues under the hood. After both fixes, the job wrote successfully.

---

## 6. Cluster Status / Delete — CLI

```bash
# List all clusters in a region
gcloud dataproc clusters list --region=europe-west3

# Describe one cluster (full config, status, staging bucket, etc.)
gcloud dataproc clusters describe nyc-taxi-cluster --region=europe-west3

# Delete a cluster
gcloud dataproc clusters delete nyc-taxi-cluster --region=europe-west3

# Skip confirmation prompt
gcloud dataproc clusters delete nyc-taxi-cluster --region=europe-west3 --quiet
```
**Note:** Dataproc clusters cannot be "stopped" and resumed like a GCE VM — only created or deleted. Recreating takes ~90 seconds to 2 minutes, so delete when done rather than leaving it idle.

---

## 7. Job Status / Cancel — CLI

```bash
# List jobs (optionally filter by cluster)
gcloud dataproc jobs list --region=europe-west3 --cluster=nyc-taxi-cluster

# Check status / details of one job
gcloud dataproc jobs describe JOB_ID --region=europe-west3

# Wait for a job to finish (streams status until done)
gcloud dataproc jobs wait JOB_ID --region=europe-west3

# Cancel a running job
gcloud dataproc jobs kill JOB_ID --region=europe-west3
```

---

## 8. End-to-End Command Sequence (Copy-Paste Flow)

```bash
# 1. Set project
gcloud config set project YOUR_PROJECT_ID

# 2. Enable APIs (one-time only)
gcloud services enable dataproc.googleapis.com compute.googleapis.com storage.googleapis.com cloudresourcemanager.googleapis.com

# 3. Create cluster (testing config)
gcloud dataproc clusters create nyc-taxi-cluster \
  --region=europe-west3 --zone=europe-west3-a \
  --single-node --master-machine-type=n2-standard-4 \
  --master-boot-disk-size=50 --image-version=2.2-debian12 \
  --optional-components=JUPYTER --enable-component-gateway \
  --max-idle=30m

# 4. Confirm it's running
gcloud dataproc clusters list --region=europe-west3

# 5. Upload script to GCS
gcloud storage cp 06_spark_sql.py gs://spark-tutorial-pq/code/06_spark_sql.py

# 6. Submit job
gcloud dataproc jobs submit pyspark \
  gs://spark-tutorial-pq/code/06_spark_sql.py \
  --cluster=nyc-taxi-cluster --region=europe-west3

# 7. Check job status (if run async with --async flag)
gcloud dataproc jobs list --region=europe-west3 --cluster=nyc-taxi-cluster

# 8. (Optional) Kill a stuck/long-running job
gcloud dataproc jobs kill JOB_ID --region=europe-west3

# 9. Delete cluster once done
gcloud dataproc clusters delete nyc-taxi-cluster --region=europe-west3 --quiet
```

---

## 9. Quick Gotchas Log (from actual setup)

- `--single-node` + small machine (n2-standard-2) → **SIGTERM/143 OOM** on parquet read across full year of data. Fixed by bumping to n2-standard-4 and/or reading fewer files.
- "Failed to validate permissions for default service account" warning → fixed by enabling **Cloud Resource Manager API**.
- Use `gcloud storage cp` (not `gsutil cp`) — current recommended CLI; drop `-m`/`-r` for single files.
- GCS buckets and staging buckets are **not deleted** when the cluster is deleted — only compute resources go away.
- Writing to BigQuery with the Spark connector: don't pass `--jars=gs://spark-lib/bigquery/...` — the cluster image already bundles the connector, and adding it again causes a classloader conflict (`ServiceConfigurationError: ... not a subtype`) that breaks even the input parquet read. See §5a.
- BigQuery write can also fail with `403 ... bigquery.tables.get denied` even after the jar fix — the default Compute Engine service account has no BigQuery roles on newer projects. Grant it `roles/bigquery.dataEditor` + `roles/bigquery.jobUser`. See §5a.