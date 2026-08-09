/* @bruin

# Docs:
# - Materialization: https://getbruin.com/docs/bruin/assets/materialization
# - Quality checks (built-ins): https://getbruin.com/docs/bruin/quality/available_checks
# - Custom checks: https://getbruin.com/docs/bruin/quality/custom

# TODO: Set the asset name (recommended: staging.trips).
name: staging.trips
# TODO: Set platform type.
# Docs: https://getbruin.com/docs/bruin/assets/sql
# suggested type: duckdb.sql
type: duckdb.sql

# TODO: Declare dependencies so `bruin run ... --downstream` and lineage work.
# Examples:
# depends:
#   - ingestion.trips
#   - ingestion.payment_lookup
depends:
  - ingestion.trips

# TODO: Choose time-based incremental processing if the dataset is naturally time-windowed.
# - This module expects you to use `time_interval` to reprocess only the requested window.
materialization:
  # What is materialization?
  # Materialization tells Bruin how to turn your SELECT query into a persisted dataset.
  # Docs: https://getbruin.com/docs/bruin/assets/materialization
  #
  # Materialization "type":
  # - table: persisted table
  # - view: persisted view (if the platform supports it)
  type: table
  # TODO: set a materialization strategy.
  # Docs: https://getbruin.com/docs/bruin/assets/materialization
  # suggested strategy: time_interval
  #
  # Incremental strategies (what does "incremental" mean?):
  # Incremental means you update only part of the destination instead of rebuilding everything every run.
  # In Bruin, this is controlled by `strategy` plus keys like `incremental_key` and `time_granularity`.
  #
  # Common strategies you can choose from (see docs for full list):
  # - create+replace (full rebuild)
  # - truncate+insert (full refresh without drop/create)
  # - append (insert new rows only)
  # - delete+insert (refresh partitions based on incremental_key values)
  # - merge (upsert based on primary key)
  # - time_interval (refresh rows within a time window)
  strategy: time_interval
  # TODO: set incremental_key to your event time column (DATE or TIMESTAMP).
  incremental_key: pickup_datetime
  # TODO: choose `date` vs `timestamp` based on the incremental_key type.
  time_granularity: timestamp

# TODO: Define output columns, mark primary keys, and add a few checks.
columns:
  - name: trip_id
    type: VARCHAR
    description: Deterministic hash of trip attributes; used as the staging primary key since ingestion.trips has no natural id.
    primary_key: true
    nullable: false
    checks:
      - name: not_null
      - name: unique
  - name: taxi_type
    type: VARCHAR
    description: Taxi type this row was ingested from (yellow or green).
    checks:
      - name: not_null
  - name: pickup_datetime
    type: TIMESTAMP
    description: Trip start time.
    checks:
      - name: not_null
  - name: dropoff_datetime
    type: TIMESTAMP
    description: Trip end time.
    checks:
      - name: not_null
  - name: passenger_count
    type: INTEGER
    description: Number of passengers reported by the driver.
  - name: trip_distance
    type: FLOAT
    description: Trip distance in miles, as reported by the taxi meter.
    checks:
      - name: non_negative
  - name: fare_amount
    type: FLOAT
    description: Time-and-distance fare calculated by the meter.
    checks:
      - name: non_negative
  - name: total_amount
    type: FLOAT
    description: Total amount charged to passengers (excludes cash tips).
    checks:
      - name: non_negative

# TODO: Add one custom check that validates a staging invariant (uniqueness, ranges, etc.)
# Docs: https://getbruin.com/docs/bruin/quality/custom
custom_checks:
  - name: no_negative_trip_duration
    description: Every trip's dropoff_datetime must be at or after its pickup_datetime.
    query: |
      SELECT COUNT(*)
      FROM staging.trips
      WHERE dropoff_datetime < pickup_datetime
    value: 0

@bruin */

-- TODO: Write the staging SELECT query.
--
-- Purpose of staging:
-- - Clean and normalize schema from ingestion
-- - Deduplicate records (important if ingestion uses append strategy)
-- - Enrich with lookup tables (JOINs)
-- - Filter invalid rows (null PKs, negative values, etc.)
--
-- Why filter by {{ start_datetime }} / {{ end_datetime }}?
-- When using `time_interval` strategy, Bruin:
--   1. DELETES rows where `incremental_key` falls within the run's time window
--   2. INSERTS the result of your query
-- Therefore, your query MUST filter to the same time window so only that subset is inserted.
-- If you don't filter, you'll insert ALL data but only delete the window's data = duplicates.

WITH windowed AS (
    SELECT *
    FROM ingestion.trips
    WHERE pickup_datetime >= '{{ start_datetime }}'
      AND pickup_datetime < '{{ end_datetime }}'
),

deduped AS (
    -- ingestion.trips uses an `append` strategy, so re-running an ingestion
    -- window can produce duplicate rows. Keep only the most recently
    -- extracted copy of each trip.
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY taxi_type, pickup_datetime, dropoff_datetime, trip_distance, fare_amount
            ORDER BY extracted_at DESC
        ) AS row_num
    FROM windowed
)

SELECT
    md5(
        CAST(taxi_type AS VARCHAR)
        || CAST(pickup_datetime AS VARCHAR)
        || CAST(dropoff_datetime AS VARCHAR)
        || CAST(trip_distance AS VARCHAR)
        || CAST(fare_amount AS VARCHAR)
    ) AS trip_id,
    taxi_type,
    pickup_datetime,
    dropoff_datetime,
    passenger_count,
    trip_distance,
    fare_amount,
    total_amount
FROM deduped
WHERE row_num = 1
  AND pickup_datetime IS NOT NULL
  AND dropoff_datetime IS NOT NULL
  AND dropoff_datetime >= pickup_datetime
  AND trip_distance >= 0
  AND fare_amount >= 0
  AND total_amount >= 0
