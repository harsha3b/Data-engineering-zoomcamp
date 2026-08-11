# PySpark Setup on GCP VM

Steps taken to get PySpark + Jupyter running on the GCP data-engineering VM, in `batch_processing_spark/`.

## 1. Install Java (Spark requires a JVM)

Spark runs on the JVM, so a JDK has to be present before PySpark can start a `SparkSession` — without it, `pyspark` fails immediately with a "Java gateway process exited" error.

```bash
sudo apt update
sudo apt install default-jdk        # pulled in OpenJDK 11
sudo apt install openjdk-21-jdk     # installed a newer JDK alongside it
```

The VM ended up with both JDK 11 and JDK 21 installed. `update-alternatives` was used to pick which one `java`/`javac` resolve to:

```bash
sudo update-alternatives --config java
sudo update-alternatives --config javac
java -version
```

JDK 21 was selected.

## 2. Set JAVA_HOME

PySpark's launcher scripts (`pyspark`, `spark-submit`) look for `JAVA_HOME` to locate the JVM; without it they fall back to searching `PATH`, which is less reliable across shells and su/sudo contexts. `JAVA_HOME` was derived from wherever `java` currently resolves to (so it stays correct if `update-alternatives` is changed later) and prepended to `PATH`:

```bash
export JAVA_HOME=$(dirname $(dirname $(readlink -f $(which java))))
export PATH="${JAVA_HOME}/bin:${PATH}"
echo $JAVA_HOME
java --version
```

This was exported directly in the shell session and **not** yet persisted to `~/.bashrc`. To make it survive new shells/reboots, add the two `export` lines above to `~/.bashrc` (or `/etc/environment`) and `source ~/.bashrc`.

## 3. Install PySpark via uv

The project uses `uv` for dependency management (see `pyproject.toml`), so PySpark was added as a project dependency rather than pip-installed globally — this keeps the Spark version pinned and reproducible via `uv.lock`.

```bash
cd batch_processing_spark
uv init
uv add pyspark
```

Verify the install:

```bash
uv run pyspark --version
```

## 4. Install Jupyter

Jupyter (`jupyter` + `notebook`) was added the same way, so notebooks run inside the same `uv`-managed virtual environment as PySpark — this avoids kernel/version mismatches between the notebook and the `pyspark` package it imports:

```bash
uv add jupyter notebook
```

## 5. Jupyter password setup

The VM is remote, so Jupyter needs a password instead of relying on the one-time token printed to stdout (which isn't practical to copy every time the server restarts, and shouldn't be left token-less/open). A password hash was generated and stored in the server config instead:

```bash
uv run jupyter server password
```

This writes an Argon2 password hash to `~/.jupyter/jupyter_server_config.json` (`IdentityProvider.hashed_password`), so the plaintext password is never stored on disk.

## 6. Running Jupyter and accessing it from a local machine

Jupyter is started with its defaults, which bind to `127.0.0.1:8888` only:

```bash
uv run jupyter notebook
```

Because it's bound to localhost only (not `0.0.0.0`), the notebook server isn't reachable directly from outside the VM — this is intentional, so Jupyter is never exposed to the public internet. Access from a local machine is via an SSH tunnel:

```bash
gcloud compute ssh <vm-name> --zone <zone> -- -L 8888:localhost:8888
```

Then open `http://localhost:8888` in a local browser and log in with the password set in step 5.

## Verifying the setup

```python
import pyspark
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .master("local[*]") \
    .appName('test') \
    .getOrCreate()

print(f"Spark version: {spark.version}")

df = spark.range(10)
df.show()

spark.stop()
```

(see `test_script.py`) — ran cleanly, confirming Java, `JAVA_HOME`, and PySpark are wired up correctly.