# dbt Student Notes — Sessions 1–4

Project: `taxi_analytics` (inside `Data-engineering-zoomcamp` repo)
GCP project: `kestra-sandbox-499212` · Raw dataset: `zoomcamp_hw_dataset` (location `europe-west2`) · dbt output dataset: `dbt_harsha`

---

## 1. The core idea of dbt

dbt is only the **T** in ELT. It does not extract or load data — your data has to already be sitting in the warehouse (in your case, loaded via your Kestra pipeline). dbt's entire job is: take raw tables, transform them using nothing but `SELECT` statements (plus a bit of templating), and dbt handles turning those into actual `CREATE TABLE` / `CREATE VIEW` statements in the right order.

Everything in dbt is really just SQL + a dependency graph on top of it.

---

## 2. Two key config files

| File | Purpose | Committed to git? |
|---|---|---|
| `~/.dbt/profiles.yml` | *How* to connect — credentials, GCP project, dataset, location | **No** — lives outside the project on purpose |
| `dbt_project.yml` | *What* the project is — name, folder structure, materialization defaults | **Yes** |

**Why `profiles.yml` lives in `~/.dbt/` and not the project folder:** so credentials can never accidentally get committed to GitHub.

---

## 3. Environment setup (what we did)

```bash
uv init dbt-taxi-project --python 3.11
cd dbt-taxi-project
uv add dbt-core dbt-bigquery
uv run dbt init taxi_analytics
```

- Chose **oauth** as the BigQuery auth method — uses the Application Default Credentials (ADC) already set up in the Codespace, no service account JSON needed.
- `location` in `profiles.yml` **must match** the location of the dataset you're querying. BigQuery datasets have a fixed location set at creation and it **cannot be changed later** — if you get it wrong, you either fix the profile to match, or delete-and-recreate the dbt-owned dataset (never the raw one).

**Key lesson learned:** `dbt debug` / `dbt run` must always be executed from the folder that directly contains `dbt_project.yml` (the project root), not a parent folder.

**Separate virtual environments per component (e.g. one for your pipeline code, one for `taxi_analytics`) is good practice**, not a mistake — different tools often need conflicting dependency versions, so isolating them avoids resolver fights later.

---

## 4. `.gitignore` — one root file covers the whole repo

Since `taxi_analytics/` lives inside the bigger `Data-engineering-zoomcamp` repo, one `.gitignore` at the **repo root** is enough — git checks it against everything underneath, no matter how deeply nested.

```gitignore
# Python
.venv/
__pycache__/
*.pyc
.python-version

# dbt
target/
dbt_packages/
logs/

# credentials — never commit
.dbt/
.env
```

- `target/` = compiled SQL + run artifacts, fully regenerated every run
- `dbt_packages/` = installed dbt package dependencies (like `node_modules`)
- No leading slash on a pattern (e.g. `logs/`) means it matches that folder name **anywhere** in the repo tree — handy since dbt scaffolds a `logs/` folder in more than one place.

---

## 5. Core dbt vocabulary

**`source()`**
A raw table dbt did **not** create — e.g. your `green_tripdata` table loaded via Kestra. Declared in a `sources.yml` file so dbt knows about it and can track it in the dependency graph.

```yaml
sources:
  - name: zoomcamp_raw
    database: kestra-sandbox-499212   # = GCP project
    schema: zoomcamp_hw_dataset       # = BigQuery dataset
    tables:
      - name: green_tripdata
```
Referenced in SQL as: `{{ source('zoomcamp_raw', 'green_tripdata') }}`

> Note the naming mismatch: dbt uses Postgres-style **database → schema → table**, which maps to BigQuery's **project → dataset → table**.

**`ref()`**
A table/view dbt **did** create — either a model or a seed. Referenced as `{{ ref('model_name') }}`. This is what lets dbt build the dependency graph (the DAG) and always run things in the correct order.

**Seed**
A small, static CSV committed into the project (`seeds/` folder) and loaded into the warehouse with `dbt seed`. Good for reference/lookup data that rarely changes and isn't worth building a whole ingestion pipeline for (our example: the taxi zone lookup table). Once seeded, it's referenced with `ref()`, not `source()` — because dbt created it.

**Staging models**
Live in `models/staging/`. One staging model per source table, roughly 1:1. Job: light cleanup only — renaming columns to a consistent convention (snake_case), casting types safely, maybe adding a readable label for a coded field. **No filtering, no business logic, no joins.** Keeps this layer reusable for anything built on top of it later.

**Marts**
Live in `models/marts/`. This is where the real business logic happens — joins, filters, aggregations. The output here is meant to be queried directly by analysts/dashboards, so it should be denormalized (readable) rather than requiring further joins.

- **Fact table** — one row per event/transaction (our `fct_trips`, one row per taxi trip)
- **Dimension table** — descriptive lookup info (our `dim`-style `stg_zones`, boroughs/zones)

**Role-playing dimension**
When the same dimension table is joined into a query more than once for different purposes — our `stg_zones` joined twice as `pickup_zone` and `dropoff_zone`. Each join gets its own alias.

**Materialization**
Controls *how* dbt physically builds a model in the warehouse:
- `view` — recomputed every time it's queried. Cheap to build, no storage cost, always fresh. Good for staging.
- `table` — precomputed and stored. Faster to query repeatedly, costs storage, only as fresh as the last `dbt run`. Good for marts that get queried a lot.
- (Later: `incremental` — only processes new/changed rows instead of rebuilding everything. Coming in Session 5.)

Set per-folder in `dbt_project.yml`:
```yaml
models:
  taxi_analytics:
    staging:
      +materialized: view
    marts:
      +materialized: table
```

---

## 6. Commands used so far

| Command | What it does |
|---|---|
| `uv run dbt debug` | Tests the connection defined in `profiles.yml` |
| `uv run dbt run` | Builds all models |
| `uv run dbt run --select model_name` | Builds just one model (fast iteration) |
| `uv run dbt seed` | Loads CSVs from `seeds/` into the warehouse |
| `uv run dbt list --resource-type source` | Lists all declared sources — good sanity check |
| `uv run dbt docs generate` + `uv run dbt docs serve` | Builds and opens an interactive docs site with the full DAG (lineage graph) |

---

## 7. What we actually built (the pipeline so far)

```
zoomcamp_hw_dataset.green_tripdata (raw source)
        │
        ▼
stg_green_tripdata.sql   (view — renamed columns, safe_cast, payment label)
        │
        ├──────────────┐
        │              │
taxi_zone_lookup.csv    │
   (seed)               │
        │                │
        ▼                │
   stg_zones.sql          │
   (view — renamed)       │
        │                │
        └───────┬────────┘
                ▼
          fct_trips.sql
    (table — joined twice for pickup/dropoff zone,
     filtered: trip_distance > 0, fare_amount > 0)
```

---

## 8. Debugging patterns worth remembering

- **"project path not found"** → you're not sitting in the folder with `dbt_project.yml`. `cd` there first.
- **"Dataset X was not found in location Y"** → location mismatch between your dbt profile and the actual BigQuery dataset. Check the real location with `bq show --format=prettyjson project:dataset | grep location`, then fix `profiles.yml` to match — never try to change an existing dataset's location (not possible in BigQuery).
- **Relative path commands failing** (e.g. `head` says "no such file") → almost always means you ran it from the wrong working directory. Run `pwd` to confirm where you are.

---

## 9. Session 4 — Testing and documentation

### Why tests matter
Up to this point, dbt would happily build broken output — nothing was checking whether the *data* itself was correct, only whether the SQL ran without error. Tests close that gap: they run after (or alongside) a build and fail loudly if the data doesn't meet the rules you define.

### Generic (built-in) tests
Defined as YAML config in a `schema.yml` file — no SQL to write. Four used so far:

| Test | Checks | Example use |
|---|---|---|
| `unique` | No duplicate values in a column | `unique_row_id` |
| `not_null` | No NULLs in a column | `location_id`, `pickup_borough` |
| `relationships` | Referential integrity — every value in this column exists in another table's column | every `pickup_location_id` exists in `stg_zones.location_id` |
| `accepted_values` | Column only contains values from a defined list | `payment_type` must be in `[1,2,3,4,5,6]` |

Newer dbt syntax nests test arguments under `arguments:`:
```yaml
- name: pickup_location_id
  tests:
    - relationships:
        arguments:
          to: ref('stg_zones')
          field: location_id
```

A test can be scoped to a subset of rows with `config: where:` — used this to let `accepted_values` ignore legitimate NULLs instead of failing on them:
```yaml
- accepted_values:
    arguments:
      values: [1, 2, 3, 4, 5, 6]
      quote: false          # needed because payment_type is INT64, not STRING —
                             # without this dbt wraps values in quotes and BigQuery
                             # rejects comparing INT64 to STRING
    config:
      where: "payment_type is not null"
```

### Custom (singular) tests
Plain `.sql` files in a `tests/` folder for logic too specific for a generic test. **Rule: the query should return zero rows if the data is healthy** — any returned row is a failure.

`tests/assert_positive_amounts.sql`:
```sql
select unique_row_id, fare_amount, total_amount
from {{ ref('fct_trips') }}
where fare_amount < 0
   or total_amount < 0
```

Run all tests: `uv run dbt test`

### Real data issues found and fixed this session
This is the most valuable part of the session — real debugging, not just following steps:

1. **Duplicate rows in the source data.** `unique` test failed on `unique_row_id` with 53,551 duplicates. Investigated with `GROUP BY` + `HAVING COUNT(*) > 1`, then checked row counts per `filename` to rule out a pipeline double-load (row counts per month looked normal — a realistic COVID-era decline through 2020). Concluded it was genuine duplicate rows scattered across several source CSVs, a known quirk of NYC TLC data.

   **Fix — dedup pattern using `ROW_NUMBER()`**, added in `stg_green_tripdata.sql`:
   ```sql
   row_number() over (
       partition by unique_row_id
       order by filename
   ) as rn
   ...
   where rn = 1
   ```
   This numbers duplicate rows within each `unique_row_id` group and keeps only the first. This is a standard, reusable SQL dedup pattern.

2. **NULL `payment_type` values.** `accepted_values` failed — investigation showed 882,830 NULLs. Concluded this reflects real-world data collection gaps (street-hail trips where payment method wasn't logged), not corrupt data, so the fix was to scope the test to exclude NULLs (`config: where:`) rather than force a fake value or treat it as an error.

3. **Two dbt/BigQuery quirks hit and resolved:**
   - Deprecation warning on old-style test arguments → fixed by nesting under `arguments:`
   - `No matching signature for operator IN for argument types INT64 and {STRING}` → fixed by adding `quote: false`, since `accepted_values` quotes its values as strings by default.

### Documentation
Added `description:` fields to models and columns in `schema.yml`. These power the auto-generated docs site:
```bash
uv run dbt docs generate
uv run dbt docs serve
```
Opens a browsable site (port-forwarded in Codespaces) showing column descriptions, and — most usefully — a **Lineage Graph** visualizing the full DAG: `green_tripdata` → `stg_green_tripdata` → `fct_trips`, with `taxi_zone_lookup` → `stg_zones` feeding in.

### End-of-session state
12/12 tests passing. Committed and pushed:
```bash
git add .
git commit -m "Session 4: add tests, dedup fix, and documentation"
git push
```

---

## 10. Session 6 — Orchestrating dbt from Kestra: errors & resolutions

Wired up `dbt_build.yml`, a Kestra flow that clones the repo, writes a GCP service-account key file, then runs `dbt build` against BigQuery — all inside separate Docker containers stitched together by a `WorkingDirectory` task. Getting this working end-to-end surfaced five distinct bugs, layered on top of each other. Each one only became visible after fixing the previous one, so they're listed in the order they actually appeared.

**Error 1 — `Invalid value for '--project-dir': Path 'taxi_analytics' does not exist`**
`projectDir` was set to `taxi_analytics`, but the repo clones with the dbt project one level deeper.
**Resolution:** set `projectDir: dbt-taxi-project/taxi_analytics` (the real path after cloning).

**Error 2 — `[Errno 2] No such file or directory: 'gcp-key.json'` (or `'../../gcp-key.json'`)**
Even after fixing `projectDir`, dbt couldn't find the key file. The key insight: although `write_gcp_keyfile` and `dbt_build` share the same `WorkingDirectory`, the `dbt build` process actually runs from the **root** of that shared folder — not from inside `projectDir`, despite `projectDir` telling dbt where the project lives. So any relative path in `keyfile` (bare filename, or `../..`-style guessing) was being resolved from the wrong starting point.
**Resolution:** write the key file to, and reference it from, the *exact same relative path from the shared root* in both tasks: `dbt-taxi-project/taxi_analytics/gcp-key.json`. Consistency matters more than cleverness here.

**Error 3 — `Unable to find 'workingDir' used in the expression`**
Tried the "safe" option instead — Kestra's built-in `{{ workingDir }}` variable, which gives the full absolute path with no guessing. Worked fine inside `commands:`, but the DbtCLI task's `profiles:` block is rendered in a different context that doesn't expose `workingDir` at all.
**Resolution:** don't rely on `{{ workingDir }}` inside `profiles:` — use the plain relative path from Error 2 instead.

**Error 4 — `Database Error: Invalid control character at: line 5 column 46`**
Once the key file was finally *found*, its contents were invalid JSON. Root cause: Kestra's secret backend (`type: env`) stores secrets base64-encoded at rest, but `secret('GCP_SERVICE_ACCOUNT')` **already returns the decoded plaintext** — the decoding happens automatically the moment you reference the secret in a template.
**Resolution (partial, led to Error 5):** stop assuming the secret needs decoding.

**Error 5 — `base64: invalid input`, then (after removing the redundant decode) still-corrupted key file**
First tried piping the secret through `base64 -d` — failed immediately, because the secret was already plaintext JSON (see Error 4), so decoding it a second time is like base64-decoding a sentence that was never encoded. Removed that step, but the file was still broken: the private key's escaped `\n` sequences (two literal characters, backslash + n) were coming out as *actual* line breaks, which is invalid inside a JSON string.
Cause: `echo` in this container's shell (`/bin/sh` → `dash` on Debian-based images) silently expands `\n`-style escapes even without an explicit `-e` flag.
**Resolution:** write the file with `printf '%s' '{{ secret(...) }}' > ...` instead of `echo`. `printf` never interprets escape sequences inside its `%s` argument, so the JSON's `\n` stays as literal text.

### Working flow (final)
```yaml
- id: write_gcp_keyfile
  type: io.kestra.plugin.scripts.shell.Commands
  taskRunner:
    type: io.kestra.plugin.scripts.runner.docker.Docker
  containerImage: python:3.11-slim
  commands:
    - printf '%s' '{{ secret("GCP_SERVICE_ACCOUNT") }}' > dbt-taxi-project/taxi_analytics/gcp-key.json

- id: dbt_build
  type: io.kestra.plugin.dbt.cli.DbtCLI
  projectDir: dbt-taxi-project/taxi_analytics
  taskRunner:
    type: io.kestra.plugin.scripts.runner.docker.Docker
  containerImage: python:3.11-slim
  commands:
    - dbt build --profiles-dir .
  profiles: |
    taxi_analytics:
      target: prod
      outputs:
        prod:
          type: bigquery
          method: service-account
          keyfile: "dbt-taxi-project/taxi_analytics/gcp-key.json"
          project: kestra-sandbox-499212
          dataset: dbt_harsha
          location: europe-west2
          threads: 4
          job_timeout_seconds: 300
```

### General lessons for next time
- A `WorkingDirectory` task genuinely does share files across sibling Docker containers — if something "isn't found," suspect a path mismatch before suspecting the sharing mechanism itself.
- Inside a `WorkingDirectory`, don't assume a task's `projectDir`-style config changes its actual running folder — check where the process really executes from, and make every path relative to that same point.
- Not every Pebble variable (like `workingDir`) is available in every field of every task type — plain relative paths are more portable when in doubt.
- Secrets backed by `type: env` are already decoded by the time `secret()` returns them — don't decode them again.
- `echo` is not a safe way to write secret/credential content to a file in an unfamiliar shell — its escape-handling behavior varies by shell (`dash` vs `bash`). `printf '%s'` is the safer default.

---

## 11. What's next (Session 5)

**Incremental models + partitioning/clustering:**
- Why incremental models exist (cost + speed on large tables — avoid rebuilding everything on every run)
- The `is_incremental()` macro
- `partition_by` / `cluster_by` config in dbt (ties into the BigQuery partitioning/clustering work already covered separately)
- Full-refresh vs incremental runs

After that: Session 6 — orchestrating dbt from Kestra, git branching workflow, optional GitHub Actions CI.