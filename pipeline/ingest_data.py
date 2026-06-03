#!/usr/bin/env python
import pandas as pd
from sqlalchemy import create_engine
from tqdm.auto import tqdm
import time

def get_database_engine():
    """
    Step 1: Define connection parameters and create a SQLAlchemy engine
    to interface with the PostgreSQL database.
    """
    pg_user = "root"
    pg_password = "root"
    pg_host = "localhost"
    pg_port = 5432
    pg_db = "ny_taxi"
    connection_string = f'postgresql+psycopg://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}'
    return create_engine(connection_string)

def get_data_iterator(url, chunk_size):
    """
    Step 2: Configure data types and datetime parsing.
    Initialize a Pandas CSV iterator to stream the file in chunks,
    preventing memory exhaustion for large datasets.
    """
    dtype = {
        "VendorID": "Int64",
        "passenger_count": "Int64",
        "trip_distance": "float64",
        "RatecodeID": "Int64",
        "store_and_fwd_flag": "string",
        "PULocationID": "Int64",
        "DOLocationID": "Int64",
        "payment_type": "Int64",
        "fare_amount": "float64",
        "extra": "float64",
        "mta_tax": "float64",
        "tip_amount": "float64",
        "tolls_amount": "float64",
        "improvement_surcharge": "float64",
        "total_amount": "float64",
        "congestion_surcharge": "float64"
    }
    parse_dates = ["tpep_pickup_datetime", "tpep_dropoff_datetime"]

    return pd.read_csv(
        url,
        dtype=dtype,
        parse_dates=parse_dates,
        iterator=True,
        chunksize=chunk_size
    )

def run_ingestion_pipeline():
    """
    Step 3: Orchestrate the flow.
    - Set the source URL and target table name.
    - Create the table schema by overriding any existing table.
    - Iterate through the dataset, appending each chunk to the database.
    """
    # Configuration
    year, month = 2021, 1
    url = f'https://github.com/DataTalksClub/nyc-tlc-data/releases/download/yellow/yellow_tripdata_{year}-{month:02d}.csv.gz'
    target_table = "yellow_taxi_data"
    chunk_size = 100000

    # Resource Initialization
    engine = get_database_engine()
    df_iter = get_data_iterator(url, chunk_size)

    print(f"Flow Started: Ingesting data from {url} into table '{target_table}'")

    for i, df_chunk in enumerate(df_iter):
        start_time = time.time()
        if i == 0:
            # Step 4a: Create/Reset the table structure using the first chunk's header
            df_chunk.head(0).to_sql(name=target_table, con=engine, if_exists="replace")
            print(f"Flow Update: Table '{target_table}' schema initialized.")

        # Step 4b: Append the data chunk to the database
        df_chunk.to_sql(name=target_table, con=engine, if_exists="append")

        end_time = time.time()
        print(f"Flow Update: Inserted chunk {i+1} ({len(df_chunk)} rows) in {end_time - start_time:.2f} seconds")

    print("Flow Completed: All data successfully migrated to PostgreSQL.")


if __name__ == "__main__":
    run_ingestion_pipeline()

