I’ve structured this Kestra workflow to handle the ingestion of NYC Taxi CSV data into a PostgreSQL database. It follows a standard **Extract, Load, Transform (ELT)** pattern with a focus on idempotency and performance.

Here is a technical breakdown of how the pipeline is built:

### 1. Parameterization & Variables
The workflow starts with **Inputs** that allow me to select the taxi type (yellow or green), year, and month. 

In the **Variables** section, I use Jinja templating to dynamically build filenames and table paths. A key part here is the `data` variable, which maps the internal storage URI from the extraction task so I can reference it easily in the database load step.

### 2. Data Retrieval (Extract)
I’m using a `shell.Commands` task to fetch the raw data.
*   It downloads the `.csv.gz` file directly from the GitHub source using `wget`.
*   It pipes the stream through `gunzip` to decompress it before saving.
*   By defining `outputFiles`, I ensure Kestra moves the local file into its internal storage, making it accessible to the rest of the execution even if the runner terminates.

### 3. Schema-Aware Routing
Because the schema for "Yellow" and "Green" taxis differs (specifically the pickup/dropoff column names), I implemented **Conditional Branching** using `If` tasks. This allows the flow to switch between two sets of logic while maintaining the same high-level structure.

### 4. Database Strategy (The Staging Pattern)
To ensure the process is reliable and fast, I use a **Staging-to-Production** approach within each branch:
*   **DDL Management**: It first ensures that both the target table and a staging table exist.
*   **Bulk Loading**: I use the `CopyIn` task. This is significantly faster than standard `INSERT` statements because it streams the CSV directly into the Postgres staging table.
*   **Data Enrichment**: Since the source CSVs lack a unique primary key, I run an `UPDATE` in the staging table to generate a `unique_row_id` using an MD5 hash of several columns. I also tag the rows with the source `filename` for lineage.
*   **Idempotent Merge**: Finally, I use a `MERGE` (upsert) statement. This ensures that if the workflow is re-run for the same month, it won't create duplicate records; it only inserts data that doesn't already exist based on the unique ID.

### 5. Cleanup and Configuration
*   **Maintenance**: At the end of the run, the `PurgeCurrentExecutionFiles` task wipes the temporary CSVs from Kestra’s storage to keep the system clean.
*   **DRY Credentials**: I used `pluginDefaults` at the bottom to define the PostgreSQL connection details once. This prevents me from having to repeat the database URL and credentials in every single SQL task.

### Summary of the Pipeline Logic:
1.  **Select** the dataset via user inputs.
2.  **Pull** and decompress the CSV to internal storage.
3.  **Branch** logic based on the specific taxi schema.
4.  **Stream** the data into a staging table for performance.
5.  **Generate** unique IDs and metadata.
6.  **Upsert** the staging data into the final production table.
7.  **Purge** temporary files.