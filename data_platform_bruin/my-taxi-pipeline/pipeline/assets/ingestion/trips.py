"""@bruin

name: ingestion.trips
type: python
image: python:3.11
connection: duckdb-default

materialization:
  type: table
  strategy: append

columns:
  - name: taxi_type
    type: string
    description: Taxi type this row was ingested from (yellow or green).
  - name: pickup_datetime
    type: timestamp
    description: Trip start time (tpep_pickup_datetime for yellow, lpep_pickup_datetime for green).
  - name: dropoff_datetime
    type: timestamp
    description: Trip end time (tpep_dropoff_datetime for yellow, lpep_dropoff_datetime for green).
  - name: passenger_count
    type: integer
    description: Number of passengers reported by the driver.
  - name: trip_distance
    type: float
    description: Trip distance in miles, as reported by the taxi meter.
  - name: fare_amount
    type: float
    description: Time-and-distance fare calculated by the meter.
  - name: total_amount
    type: float
    description: Total amount charged to passengers (excludes cash tips).
  - name: extracted_at
    type: timestamp
    description: Timestamp when this row was extracted by the ingestion asset.

@bruin"""

import json
import os
from datetime import datetime, timezone
from io import BytesIO

import pandas as pd
import requests
from dateutil.relativedelta import relativedelta

BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"

PICKUP_COLUMNS = {
    "yellow": "tpep_pickup_datetime",
    "green": "lpep_pickup_datetime",
}
DROPOFF_COLUMNS = {
    "yellow": "tpep_dropoff_datetime",
    "green": "lpep_dropoff_datetime",
}


def _months_in_range(start_date: str, end_date: str) -> list[str]:
    """Monthly file suffixes (YYYY-MM) covering [start_date, end_date)."""
    current = datetime.strptime(start_date, "%Y-%m-%d").replace(day=1)
    end = datetime.strptime(end_date, "%Y-%m-%d")

    months = []
    while current < end:
        months.append(current.strftime("%Y-%m"))
        current += relativedelta(months=1)
    return months


def _fetch_month(taxi_type: str, year_month: str) -> pd.DataFrame:
    url = f"{BASE_URL}/{taxi_type}_tripdata_{year_month}.parquet"
    response = requests.get(url, timeout=60)
    response.raise_for_status()

    df = pd.read_parquet(BytesIO(response.content))
    df = df.rename(
        columns={
            PICKUP_COLUMNS[taxi_type]: "pickup_datetime",
            DROPOFF_COLUMNS[taxi_type]: "dropoff_datetime",
        }
    )
    df["taxi_type"] = taxi_type
    return df


def materialize():
    start_date = os.environ["BRUIN_START_DATE"]
    end_date = os.environ["BRUIN_END_DATE"]
    taxi_types = json.loads(os.environ["BRUIN_VARS"])["taxi_types"]

    frames = [
        _fetch_month(taxi_type, year_month)
        for taxi_type in taxi_types
        for year_month in _months_in_range(start_date, end_date)
    ]

    final_dataframe = pd.concat(frames, ignore_index=True)
    final_dataframe["extracted_at"] = datetime.now(timezone.utc)
    return final_dataframe
