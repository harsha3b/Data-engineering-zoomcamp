import os
import tempfile
import requests
from google.cloud import storage, bigquery

# ── Config ────────────────────────────────────────────────
PROJECT    = "kestra-sandbox-499212"
BUCKET     = "kestra-sandbox-harsha-314_hw"
GCS_PREFIX = "fhv/raw"
DATASET    = "zoomcamp_hw_dataset"
TABLE      = "fhv_tripdata_external"
BASE_URL   = "https://github.com/DataTalksClub/nyc-tlc-data/releases/download/fhv/"
YEARS      = [2019]   # add 2020 here later if needed
# ─────────────────────────────────────────────────────────

def upload_to_gcs(bucket, filename):
    url = f"{BASE_URL}{filename}"
    blob = bucket.blob(f"{GCS_PREFIX}/{filename}")

    if blob.exists():
        print(f"  skip {filename} — already in GCS")
        return

    print(f"  downloading {filename}...")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv.gz") as tmp:
        with requests.get(url, stream=True) as r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
                tmp.write(chunk)
        tmp_path = tmp.name

    print(f"  uploading to gs://{bucket.name}/{GCS_PREFIX}/{filename}...")
    with open(tmp_path, "rb") as f:
        blob.upload_from_file(f, content_type="application/gzip")
    os.unlink(tmp_path)
    print(f"  ✓ done")


def create_external_table(bq_client, dataset_id):
    # Schema based on DTC FHV 2019 CSV structure
    schema = [
        bigquery.SchemaField("dispatching_base_num",  "STRING"),
        bigquery.SchemaField("pickup_datetime",        "TIMESTAMP"),
        bigquery.SchemaField("dropOff_datetime",       "TIMESTAMP"),
        bigquery.SchemaField("PUlocationID",           "FLOAT64"),   # nullable, hence FLOAT not INT
        bigquery.SchemaField("DOlocationID",           "FLOAT64"),
        bigquery.SchemaField("SR_Flag",                "STRING"),
        bigquery.SchemaField("Affiliated_base_number", "STRING"),
    ]

    external_config = bigquery.ExternalConfig("CSV")
    external_config.source_uris    = [f"gs://{BUCKET}/{GCS_PREFIX}/*.csv.gz"]
    external_config.compression    = "GZIP"
    external_config.schema         = schema
    external_config.options.skip_leading_rows = 1  # skip header row

    table_ref = bq_client.dataset(dataset_id).table(TABLE)
    table     = bigquery.Table(table_ref, schema=schema)
    table.external_data_configuration = external_config

    # Drop and recreate cleanly
    bq_client.delete_table(table_ref, not_found_ok=True)
    bq_client.create_table(table)
    print(f"\n✓ External table created: {PROJECT}.{dataset_id}.{TABLE}")


def main():
    gcs_client = storage.Client(project=PROJECT)
    bq_client  = bigquery.Client(project=PROJECT)
    bucket     = gcs_client.bucket(BUCKET)

    # Ensure BQ dataset exists
    dataset_ref = bigquery.Dataset(f"{PROJECT}.{DATASET}")
    dataset_ref.location = "US"
    bq_client.create_dataset(dataset_ref, exists_ok=True)

    # Download + upload files
    print("=== Uploading FHV files to GCS ===")
    for year in YEARS:
        for month in range(1, 13):
            filename = f"fhv_tripdata_{year}-{str(month).zfill(2)}.csv.gz"
            upload_to_gcs(bucket, filename)

    # Create external table
    print("\n=== Creating BigQuery external table ===")
    create_external_table(bq_client, DATASET)


if __name__ == "__main__":
    main()