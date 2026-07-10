# dbt Student Notes — Sessions 1–6

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

## 10. Session 5 — Incremental models + partitioning/clustering

### The problem being solved
Before this session, `fct_trips` was a plain `table` — every `dbt run` fully dropped and rebuilt it from scratch, rescanning *all* historical data even though only new rows actually needed processing. Harmless at small scale, but at real-world scale (years of data, daily new batches) this means re-scanning and re-paying for data that hasn't changed since yesterday. BigQuery bills primarily by bytes scanned, so this is a direct cost problem, not just a speed one — same cost-awareness as the `SELECT *` / `COUNT(*)` lessons from earlier BigQuery exercises, now applied to *how tables get built* rather than just how they're queried.

### The core mechanism

**`is_incremental()`** — a Jinja macro that returns:
- `false` on the very first run (table doesn't exist yet) or during `--full-refresh`
- `true` on every normal run after that

Used to wrap a `WHERE` filter so only new rows get processed on subsequent runs:
```sql
{% if is_incremental() %}
where pickup_datetime > (select max(pickup_datetime) from {{ this }})
{% endif %}
```
**`{{ this }}`** = a special dbt variable meaning "the table this model builds" — lets the model look at its own current contents to figure out what's already there before deciding what's new.

**Incremental key** — the column used to detect "new" (here, `pickup_datetime`). Should reliably increase as new data arrives; a timestamp/date is the natural choice for event-style data.

### Why partitioning/clustering reappear here
The `WHERE pickup_datetime > (select max(...) from {{ this }})` filter is only cheap if the table is actually **partitioned** on that same column — otherwise finding the max still requires scanning the whole table, defeating the purpose. This is the same BigQuery partitioning concept from earlier standalone exercises, now configured directly in the dbt model:

```sql
{{
    config(
        materialized='incremental',
        unique_key='unique_row_id',
        incremental_strategy='merge',
        partition_by={
            "field": "pickup_datetime",
            "data_type": "timestamp",
            "granularity": "day"
        },
        cluster_by=["pickup_borough"]
    )
}}
```
- `partition_by` — splits the table physically by day
- `cluster_by` — sorts rows within each partition by borough, since "trips in a specific borough over a date range" is a realistic query pattern

### Incremental strategy: `merge`
Two rows-handling options: `append` (just adds new rows, risk of duplicates on reprocessing) vs `merge` (checks a `unique_key` — updates if it exists, inserts if not). Chose `merge` with `unique_key='unique_row_id'` given the duplicate-row issue already found and fixed in Session 4 — protects against reprocessing overlap.

### Commands
| Command | What it does |
|---|---|
| `uv run dbt run --select fct_trips --full-refresh` | Forces a complete drop-and-rebuild — required once to apply new partitioning to an existing table, and anytime the partition/cluster config changes later |
| `uv run dbt run --select fct_trips` | Normal run — uses the incremental filter once the table already exists |

### Debugging story worth remembering
Hit a cryptic error: `Syntax error: Expected keyword DEPTH but got identifier "trips"`. Initially assumed it was a scripting/partitioning quirk (dbt-bigquery's `_dbt_max_partition` auto-variable). **The real cause, found by reading the actual compiled SQL rather than guessing from the error message:** the model file had gotten a whole duplicate copy of the CTE chain pasted into it during editing — the config block landed on the same line as the old file's closing `)`, and two full copies of `with trips as (...) ... select * from final` ended up back to back in one file. BigQuery's parser error was a downstream symptom of genuinely malformed SQL (a `WITH` block appearing where a `SELECT` was expected), not a real syntax rule violation.

**Lesson:** when a database error doesn't make sense next to your source file, check the actual **compiled** SQL (`target/run/.../model.sql` for the final run version, `target/compiled/...` for the pre-run version) before assuming it's a deep syntax/config issue. The error is always about what got sent to the database, not necessarily what you think you wrote.

Also learned along the way: `_dbt_max_partition` is a BigQuery scripting variable dbt only auto-declares for the `insert_overwrite` strategy's full-control partition mode — not for `merge`. Using it with `merge` throws `Unrecognized name`. For `merge`, the manual `(select max(col) from {{ this }})` subquery is the correct, standard pattern.

### End-of-session state
`fct_trips` is now incremental, partitioned by day on `pickup_datetime`, clustered by `pickup_borough`, using `merge` strategy. Verified real incremental behavior by comparing bytes-processed between a `--full-refresh` run and a subsequent normal run in BigQuery's Job History.

---

## 12. Session 6 — Orchestration + Git Workflow

### Why orchestration
Every previous session was triggered by hand — typing `dbt run`/`dbt build` and watching it. A real pipeline needs to run unattended. Session 6's goal: chain dbt to the existing `gcp_setup_hw` Kestra flow, so the moment raw data is ready, transformation + testing happens automatically with no manual step.

### `dbt build` vs `dbt run` + `dbt test`
- `dbt run` — builds models only, no checking.
- `dbt test` — checks already-built data only, changes nothing.
- `dbt build` — does both together, model by model, in dependency order. If a model's tests fail, dbt stops before building anything downstream of it on bad data. This fail-fast behavior matters far more in an unattended context than when watching the terminal yourself.

### How Kestra runs dbt
Kestra doesn't have special dbt "understanding" — it runs dbt inside a Docker container via the `io.kestra.plugin.dbt.cli.DbtCLI` task, the same way you'd run it in a terminal, just automated. Auth switches from the local `oauth` method (interactive personal login, fine for a human at a terminal) to `service-account` (a JSON keyfile, required since there's no human to interactively log in during an automated run).

### The final working flow (`dbt_build`, namespace `zoomcamp`)

```yaml
id: dbt_build
namespace: zoomcamp

triggers:
  - id: after_gcp_setup
    type: io.kestra.plugin.core.trigger.Flow
    conditions:
      - type: io.kestra.plugin.core.condition.ExecutionStatus
        in:
          - SUCCESS
      - type: io.kestra.plugin.core.condition.ExecutionFlow
        namespace: zoomcamp
        flowId: gcp_setup_hw

tasks:
  - id: dbt_pipeline
    type: io.kestra.plugin.core.flow.WorkingDirectory
    tasks:

      - id: clone_repository
        type: io.kestra.plugin.git.Clone
        url: https://github.com/harsha3b/Data-engineering-zoomcamp
        branch: main

      - id: write_gcp_keyfile
        type: io.kestra.plugin.scripts.shell.Commands
        taskRunner:
          type: io.kestra.plugin.scripts.runner.docker.Docker
        commands:
          - echo '{{ secret('GCP_SERVICE_ACCOUNT') }}' > dbt-taxi-project/taxi_analytics/gcp-key.json

      - id: dbt_build
        type: io.kestra.plugin.dbt.cli.DbtCLI
        projectDir: dbt-taxi-project/taxi_analytics
        taskRunner:
          type: io.kestra.plugin.scripts.runner.docker.Docker
        containerImage: python:3.11-slim
        beforeCommands:
          - pip install --quiet uv
          - uv venv --quiet
          - . .venv/bin/activate --quiet
          - uv pip install --quiet dbt-core dbt-bigquery
        commands:
          - dbt build --profiles-dir .
        profiles: |
          taxi_analytics:
            target: prod
            outputs:
              prod:
                type: bigquery
                method: service-account
                keyfile: "gcp-key.json"
                project: "{{ kv('GCP_PROJECT_ID') }}"
                dataset: dbt_harsha
                location: "{{ kv('GCP_LOCATION') }}"
                threads: 4
                job_timeout_seconds: 300
```

Key pieces explained:
- **`triggers:` block** — fires automatically whenever the flow `gcp_setup_hw` (in namespace `zoomcamp`) completes with `SUCCESS`. `flowId` must match the real flow ID exactly — a mismatch here is the single most common reason a trigger silently never fires.
- **`WorkingDirectory`** — wraps all sub-tasks in one shared folder, so files written by one task (the keyfile) are visible to a later task (`dbt_build`) — necessary because each Docker-backed task otherwise runs in its own fully isolated container filesystem.
- **`write_gcp_keyfile`** — decodes/retrieves the same `GCP_SERVICE_ACCOUNT` secret used in `gcp_setup_hw`, writing it as a plain JSON file. `secret()` already returns the decoded value — no manual `base64 -d` needed (a mistake repeated from the original `gcp_setup` setup, caught again here).
- **`profiles:` defined inline** in the task itself, not relying on any `~/.dbt/profiles.yml` existing on a machine — keeps the flow fully self-contained and reproducible from Git alone. `project` and `location` pull from the same `kv()` store used by `gcp_setup_hw`, so they never drift out of sync.
- **`dbt build --profiles-dir .`** — the fail-fast build+test combo, run against the `prod` target defined inline.

### Debugging story: container isolation, path resolution, and secret handling
This was the hardest debugging round of the whole curriculum, and the lessons generalize well beyond dbt. Five distinct bugs, layered on top of each other — each only became visible after fixing the previous one.

**1. `Path 'taxi_analytics' does not exist`**
`projectDir` was set to `taxi_analytics`, but the repo clones with the dbt project one level deeper.
**Fix:** `projectDir: dbt-taxi-project/taxi_analytics` (the real path, confirmed via `find . -name dbt_project.yml`).

**2. `No such file or directory: 'gcp-key.json'` (or `'../../gcp-key.json'`)**
Even after fixing `projectDir`, dbt couldn't find the keyfile. The key insight: although `write_gcp_keyfile` and `dbt_build` share the same `WorkingDirectory`, the `dbt build` process actually runs from the **root** of that shared folder — not from inside `projectDir`, despite `projectDir` telling dbt where the *project* lives. So any relative `keyfile` path (bare filename, or guessed `../..`) was resolving from the wrong starting point.
**Fix:** write the keyfile to, and reference it from, the **exact same relative path from the shared root** in both tasks — `dbt-taxi-project/taxi_analytics/gcp-key.json`, written out in full in both places rather than a shortened relative reference. Consistency beats cleverness here.

**3. `Unable to find 'workingDir' used in the expression`**
Tried Kestra's built-in `{{ workingDir }}` variable for a "safe" absolute path instead. Works fine inside `commands:`, but the `DbtCLI` task's `profiles:` block renders in a different context that doesn't expose `workingDir` at all.
**Fix:** don't rely on `{{ workingDir }}` inside `profiles:` — plain relative paths (from fix #2) are more portable across task types.

**4. `Database Error: Invalid control character at: line 5 column 46`**
Once the keyfile was finally *found*, its contents were invalid JSON.
**Fix (partial, led to bug #5):** `secret('GCP_SERVICE_ACCOUNT')` already returns the fully decoded plaintext the moment it's referenced in a template — Kestra's secret backend decodes it automatically. No manual decode step should be applied at all.

**5. `base64: invalid input`, then a still-corrupted key file after removing the redundant decode**
First tried piping through `base64 -d` — failed immediately, since the secret was already plaintext JSON (bug #4), so decoding it again is like base64-decoding a plain sentence. Removed that step, but the file was *still* broken: the private key's escaped `\n` sequences (the two literal characters `\` and `n`) were coming out as real line breaks — invalid inside a JSON string.
**Root cause:** `echo` in this container's shell (`/bin/sh` → `dash` on Debian-based images) silently expands `\n`-style escapes even without an explicit `-e` flag.
**Fix:** write the file with `printf '%s' '{{ secret(...) }}' > ...` instead of `echo`. `printf`'s `%s` never interprets escape sequences in its argument, so the JSON's `\n` stays literal text, exactly as needed.

### Working flow (final, confirmed)
```yaml
id: dbt_build
namespace: zoomcamp

triggers:
  - id: after_gcp_setup
    type: io.kestra.plugin.core.trigger.Flow
    conditions:
      - type: io.kestra.plugin.core.condition.ExecutionStatus
        in:
          - SUCCESS
      - type: io.kestra.plugin.core.condition.ExecutionFlow
        namespace: zoomcamp
        flowId: gcp_setup_hw

tasks:
  - id: dbt_pipeline
    type: io.kestra.plugin.core.flow.WorkingDirectory
    tasks:

      - id: clone_repository
        type: io.kestra.plugin.git.Clone
        url: https://github.com/harsha3b/Data-engineering-zoomcamp
        branch: main

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
        beforeCommands:
          - pip install --quiet uv
          - uv venv --quiet
          - . .venv/bin/activate --quiet
          - uv pip install --quiet dbt-core dbt-bigquery
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
- A `WorkingDirectory` task genuinely does share files across sibling Docker containers — if something "isn't found," suspect a **path mismatch** before suspecting the sharing mechanism itself.
- Inside a `WorkingDirectory`, don't assume a task's `projectDir`-style config changes its actual *running* folder — check where the process really executes from, and make every path relative to that same point, consistently.
- Not every Pebble variable (like `workingDir`) is available in every field of every task type — plain relative paths are more portable when in doubt.
- Secrets backed by `type: env` are already decoded by the time `secret()` returns them — never decode them again.
- `echo` is not a safe way to write secret/credential content to a file in an unfamiliar shell — its escape-handling behavior varies by shell (`dash` vs `bash`). `printf '%s'` is the safer default for writing credential content verbatim.

### End-of-session verification
Manually executed `gcp_setup_hw` → watched `dbt_build` fire automatically in the Executions view, with no manual trigger — confirming the full automated chain: **ingest → transform → test**, unattended, exactly as intended.

### Git workflow
Already an established practice going into this session (branch → commit → PR review on GitHub → merge → delete branch) — no new ground needed here, just applied as usual to this session's flow changes.

### Not covered (optional, for later)
GitHub Actions CI — automatically running `dbt build` on every PR so a broken model can't merge silently. A natural next step if/when this project moves toward a more team-like workflow.

---

## Curriculum complete
All six sessions done: dbt installed and connected to BigQuery, a full staging → seed → mart pipeline built and tested on real NYC taxi data, incremental models with partitioning/clustering, and the whole thing running unattended via Kestra orchestration — with a real trail of debugging real, not simulated, problems along the way (duplicate source rows, NULL handling, dbt/BigQuery syntax quirks, and container filesystem isolation). This is a genuinely complete, working analytics engineering pipeline, not just a tutorial exercise.