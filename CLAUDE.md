# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository purpose

This is a personal coursework repo for the [DataTalksClub Data Engineering Zoomcamp](https://github.com/DataTalksClub/data-engineering-zoomcamp). It is **not a single application** — it's a collection of independent, module-by-module exercises (ingestion, orchestration, data warehousing, analytics engineering, and data-platform tooling). Each top-level directory is its own self-contained project with its own dependency management; there is no repo-wide build, lint, or test command.

## Directory map

| Directory | Module / topic | Stack |
|---|---|---|
| `pipeline/` | Module 1 (Docker + Postgres ingestion homework) | uv, Docker — **currently reset to empty placeholder files**, not runnable as-is |
| `Terraform/` | GCP VM provisioning | Terraform |
| `workflow-orchestration/` | Orchestration homework | Kestra (YAML flows) |
| `analytics-engineering/taxi_rides_ny/` | Analytics engineering module | dbt (BigQuery) |
| `dbt-taxi-project/` | dbt project run via Kestra, deployed to BigQuery | dbt-core, dbt-bigquery, uv |
| `my-dlt-pipeline/` | dlt ("data load tool") pipelines into DuckDB, plus marimo/altair dashboards | dlt, uv |
| `data_platform_bruin/` | Bruin CLI data-platform tutorial (chess + NYC taxi pipelines) | Bruin CLI, ingestr, DuckDB/BigQuery, uv |
| `Module_3/` | Data Warehousing / BigQuery homework (standalone script + Q&A notes) | google-cloud-storage |
| `test/` | Scratch files only — not a real test suite | — |

When making a change, first check whether the target subdirectory has its own `pyproject.toml`/`uv.lock`, `dbt_project.yml`, `.bruin.yml`, or Kestra flow — dependencies and run context are scoped per-directory, not shared.

## Commands

### uv-managed Python projects (`my-dlt-pipeline/`, `data_platform_bruin/`, `dbt-taxi-project/`)
Each has its own `pyproject.toml` + `uv.lock`. From inside the subdirectory:
```bash
uv sync                    # install deps into subproject's venv
uv run <script>.py         # run a script, e.g. uv run taxi_pipeline.py
```

### dlt pipelines (`my-dlt-pipeline/`)
Each script is a standalone dlt pipeline that loads into local DuckDB (`dataset_name` set per pipeline):
```bash
uv run taxi_pipeline.py          # NYC taxi data from the zoomcamp demo REST API
uv run football_data.py          # football-data.org API — requires an API key in dlt secrets (X-Auth-Token)
uv run open_library_pipeline.py
uv run rest_api_pipeline.py
```
`football_dashboard.py` / `taxi_pipeline_dashboard.py` are marimo/altair dashboards over the resulting DuckDB tables.

### Bruin data platform (`data_platform_bruin/`)
Requires the Bruin CLI (`curl -LsSf https://getbruin.com/install/cli | sh`) and a `.bruin.yml` (gitignored — holds connection credentials, not committed).
```bash
bruin validate <path>                        # fast static check (syntax, deps, schema) — no execution
bruin run <path>                             # run a pipeline or a single asset
bruin run <path> --downstream                # run an asset plus everything depending on it
bruin run <path> --full-refresh              # truncate + rebuild from scratch
bruin lineage <path>                         # show upstream/downstream dependencies
bruin query --connection <conn> --query "…"  # ad-hoc SQL against a configured connection
```
Two sub-pipelines:
- `chess/` — ingestr-based ingestion of chess.com data into DuckDB (`pipeline.yml` at the directory root).
- `my-taxi-pipeline/` — layered NYC taxi ELT pipeline (`pipeline/assets/{ingestion,staging,reports}/`). **This is a learning skeleton with unfinished TODOs** in `trips.py`, `trips.sql`, and `trips_report.sql` — don't assume it runs end-to-end without checking those files first. Designed to run first against local DuckDB, then be repointed at BigQuery (swap `duckdb.sql`/`duckdb.seed` asset types for `bq.sql`/`bq.seed`, and `default_connections.duckdb` for `default_connections.bigquery`).

### dbt projects (`analytics-engineering/taxi_rides_ny/`, `dbt-taxi-project/taxi_analytics/`)
```bash
dbt deps                    # install packages (packages.yml)
dbt build                   # run models + tests + seeds + snapshots
dbt run --select <model>    # build a single model
dbt test                    # run tests only
```
Both target BigQuery (`dbt-bigquery`) — a `profiles.yml`/credentials must be available locally (not committed; `.dbt/` and `.env` are gitignored). `dbt-taxi-project/taxi_analytics` is normally built remotely by the Kestra flow `dbt-taxi-project/dbt_build.yml`, which clones the repo, materializes a GCP service-account key from a Kestra secret, and runs `dbt build --profiles-dir .` against BigQuery project `kestra-sandbox-499212`, dataset `dbt_harsha`, region `europe-west2` — that flow is triggered automatically after the `gcp_setup_hw` flow succeeds.

### Kestra orchestration (`workflow-orchestration/`)
Flows are plain YAML under `Module_2_working_flows/` (homework) and `workflow-testing/` (scratch/examples). Kestra itself runs via Docker Compose (`docker-compose.yml`); flows are uploaded/run through the Kestra UI or CLI, not executed directly as scripts.

### Terraform (`Terraform/`)
Provisions a single GCP data-engineering VM (`main.tf`, `VM_setup.tf`, `variables.tf`, `outputs.tf`). See `Terraform/SETUP_GUIDE.md` for the full setup walkthrough.
```bash
cp terraform.tfvars.example terraform.tfvars   # then edit project/credentials
terraform init
terraform plan
terraform apply
terraform destroy
```

## Architecture notes

- **No shared codebase**: modules don't import from each other. Similar-looking files (e.g. multiple `stg_green_tripdata.sql`, multiple taxi ingestion scripts) are intentionally duplicated across modules that each demonstrate a different tool (dlt vs. Bruin vs. dbt vs. raw Kestra) against the same NYC taxi dataset — don't try to unify them.
- **Credentials are always external to the repo**: GCP service-account JSON, `.bruin.yml`, `.env`, and `.dbt/` are all gitignored. Any pipeline that talks to BigQuery or an external API expects credentials to be supplied at runtime (ADC, a secrets file, or a Kestra secret), never committed.
- **DuckDB is the default local destination** across dlt and Bruin pipelines; BigQuery is the production/cloud target once a local pipeline is validated. Expect a `duckdb: duckdb-default` connection locally and a `bigquery: gcp-default` (or Kestra-injected) connection in cloud runs.
- **`pipeline/` is currently a set of empty placeholder files** (0 bytes, including `pyproject.toml`, `main.py`, `Dockerfile`, etc.) — treat it as scaffolding to be filled in, not working code, unless you've just verified otherwise.
- **NYC TLC taxi trip data** (parquet, `https://d37ci6vzurychx.cloudfront.net/trip-data/<type>_tripdata_<year>-<month>.parquet`) is the dataset reused across `my-dlt-pipeline`, `data_platform_bruin/my-taxi-pipeline`, `analytics-engineering`, `dbt-taxi-project`, and `Module_3`. TLC data is not available past November 2025, so date ranges in examples stay before Dec 2025.