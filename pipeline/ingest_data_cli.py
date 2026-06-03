#!/usr/bin/env python
import pandas as pd
from sqlalchemy import create_engine
import time
import click

def get_database_engine(user, password, host, port, db):
    """
    Step 1: Define connection parameters and create a SQLAlchemy engine
    python ingest_data.py --user=root --password=root --host=localhost --port=5432 --db=ny_taxi --table=yellow_taxi_data --year=2021 --month=1
    """
    connection_string = f'postgresql+psycopg://{user}:{password}@{host}:{port}/{db}'
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

@click.command()
@click.option('--user', default='root', help='PostgreSQL user name')
@click.option('--password', default='root', help='PostgreSQL password')
@click.option('--host', default='localhost', help='PostgreSQL host')
@click.option('--port', default=5432, type=int, help='PostgreSQL port')
@click.option('--db', default='ny_taxi', help='PostgreSQL database name')
@click.option('--table', default='yellow_taxi_data', help='Target table name')
@click.option('--chunk_size', default=100000, type=int, help='Size of data chunks for ingestion')
@click.option('--year', default=2021, type=int, help='Year of taxi data')
@click.option('--month', default=1, type=int, help='Month of taxi data')
def run_ingestion_pipeline(user, password, host, port, db, table, chunk_size, year, month):
    """
    Step 3: Orchestrate the flow.
    - Set the source URL and target table name.
    - Create the table schema by overriding any existing table.
    - Iterate through the dataset, appending each chunk to the database.
    """
    url = f'https://github.com/DataTalksClub/nyc-tlc-data/releases/download/yellow/yellow_tripdata_{year}-{month:02d}.csv.gz'
    # Resource Initialization
    engine = get_database_engine(user, password, host, port, db)
    df_iter = get_data_iterator(url, chunk_size)

    print(f"Flow Started: Ingesting data from {url} into table '{table}'")

    for i, df_chunk in enumerate(df_iter):
        start_time = time.time()
        if i == 0:
            # Step 4a: Create/Reset the table structure using the first chunk's header
            df_chunk.head(0).to_sql(name=table, con=engine, if_exists="replace")
            print(f"Flow Update: Table '{table}' schema initialized.")

        # Step 4b: Append the data chunk to the database
        df_chunk.to_sql(name=table, con=engine, if_exists="append")

        end_time = time.time()
        print(f"Flow Update: Inserted chunk {i+1} ({len(df_chunk)} rows) in {end_time - start_time:.2f} seconds")

    print("Flow Completed: All data successfully migrated to PostgreSQL.")

if __name__ == "__main__":
    run_ingestion_pipeline()