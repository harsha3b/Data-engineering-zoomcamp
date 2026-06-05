#!/usr/bin/env python
# coding: utf-8

import pandas as pd
from sqlalchemy import create_engine

# Load green taxi data
gt_data = 'green_tripdata_2025-11.parquet'
df = pd.read_parquet(gt_data)
print(f"Loaded taxi data: {len(df)} rows")
print(df.head())
print(df.info())

# Clean up - ehail_fee has all NaNs and isn't in the description
df = df.drop(columns=['ehail_fee'])

# Load zone lookup data
zone_data = 'taxi_zone_lookup.csv'
df2 = pd.read_csv(zone_data)
print(f"\nLoaded zone data: {len(df2)} rows")
print(df2.info())
print(df2.head())

# Handle missing values in zone data
null_columns = df2.columns[df2.isnull().any()]
print(f"\nColumns with nulls: {list(null_columns)}")

rows_with_nulls = df2[df2.isnull().any(axis=1)]
print(rows_with_nulls)

# Fill missing Zone and service_zone with 'Unknown'
df2['Zone'] = df2['Zone'].fillna('Unknown')
df2['service_zone'] = df2['service_zone'].fillna('Unknown')
print("\nCorrected rows:")
print(df2.loc[[263, 264]])

# Fix data types for database
df['PULocationID'] = df['PULocationID'].astype('Int64')
df['DOLocationID'] = df['DOLocationID'].astype('Int64')

# Reset index to start at 1
df.index = df.index + 1
df2.index = df2.index + 1

# Connect to DB
engine = create_engine('postgresql+psycopg://root:root@localhost:5432/ny_taxi')

# Create and insert green taxi data
print("\nCreating green_taxi_data table...")
print(pd.io.sql.get_schema(df, name='green_taxi_data', con=engine))

df.head(n=0).to_sql(name='green_taxi_data', con=engine, if_exists='replace', index=True)
print("Inserting data...")
df.to_sql(name='green_taxi_data', con=engine, if_exists='append', index=True, chunksize=10000)
print(f"Inserted {len(df)} rows into green_taxi_data")

# Create and insert zone data
print("\nCreating taxi_zone_data table...")
df2.head(n=0).to_sql(name='taxi_zone_data', con=engine, if_exists='replace', index=True)
df2.to_sql(name='taxi_zone_data', con=engine, if_exists='append', index=True)
print(f"Inserted {len(df2)} rows into taxi_zone_data")

print("\nDone!")




