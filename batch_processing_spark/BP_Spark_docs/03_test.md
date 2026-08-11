# 03_test.ipynb — Walkthrough

What this notebook does, step by step, and why each command is there. Mirrors the markdown cells added directly in the notebook, kept here as a standalone reference.

## 1. Check the PySpark install

```python
import pyspark
```
Imports the `pyspark` package so its APIs (and `SparkSession` later on) are available in the notebook.

```python
pyspark.__version__
```
Prints the installed PySpark version (`4.2.0`) — a quick sanity check that the `uv`-managed virtual environment has the expected version.

```python
pyspark.__file__
```
Prints the on-disk path of the installed package (`.venv/lib/python3.13/site-packages/pyspark/__init__.py`) — confirms the notebook kernel is actually using the project's `.venv`, not some other Python/PySpark install.

## 2. Start a local Spark session

```python
from pyspark.sql import SparkSession
```
Imports `SparkSession`, the entry point for creating and configuring a Spark application. Nothing else in Spark's DataFrame/SQL API works without one.

```python
spark = SparkSession.builder \
    .master("local[*]") \
    .appName('test') \
    .getOrCreate()
```
Creates (or reuses) a Spark session running **locally**, with `local[*]` telling Spark to use all available CPU cores as its "cluster" — no real Spark cluster is involved, this is for local experimentation only. `getOrCreate()` returns an existing session if one is already running instead of starting a duplicate.

Output includes the standard Spark startup log noise (log4j defaults, native-hadoop library warning) — expected on a single-node local setup and safe to ignore.

## 3. Get a real dataset onto disk

```bash
!wget https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv
```
Downloads the NYC TLC taxi zone lookup CSV (LocationID → Borough/Zone/service_zone mapping) so there's an actual file to read into Spark in the next steps.

```bash
!head taxi_zone_lookup.csv
```
Previews the first few raw lines of the CSV to check its structure (headers, delimiters, quoting) before letting Spark parse it.

## 4. Load the CSV into a Spark DataFrame

```python
df = spark.read \
    .option("header", "true") \
    .csv('taxi_zone_lookup.csv')
```
Reads the CSV into a Spark DataFrame. `.option("header", "true")` tells Spark the first row is column names, not data — otherwise columns would default to generic names like `_c0`, `_c1`.

```python
df.show()
```
Triggers Spark's lazy evaluation (Spark doesn't actually read/process data until an action like `.show()` is called) and prints the first 20 rows — used here purely to visually confirm the CSV loaded with the right columns and values.

## 5. Write the data out as Parquet

```python
df.write.parquet('zones')
```
Writes the DataFrame to disk in Parquet format, Spark's standard columnar output format — more compact and much faster to read back than CSV, and the typical hand-off format between Spark stages/jobs. Creates a `zones/` directory containing the output part-files.

```bash
!ls -lh
```
Lists the working directory to confirm the `zones/` Parquet output actually landed on disk.

## 6. Note on the Spark UI

```python
# open port 4040 to look at spark jobs which have been completed
```
Reminder note (not executed code): while a `SparkSession` is active, Spark exposes a web UI at `http://localhost:4040` for inspecting jobs, stages, and tasks — useful for debugging performance or understanding how a job was executed under the hood. On this VM it would need an SSH tunnel to view locally, same as the Jupyter setup (see `SPARK_SETUP.md`).

## Takeaway

This notebook is a minimal end-to-end smoke test for the local PySpark setup: import → start a session → read a real CSV → inspect it → write it back out as Parquet. It doesn't do any real transformation/analysis — it exists to prove Java, `JAVA_HOME`, and PySpark are correctly wired together before building anything more substantial on top.
