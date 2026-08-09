-- Sanity check for the ny_taxi_pipeline.
-- Not a Bruin asset (no @bruin header) — run manually against duckdb-default, e.g.:
--   bruin query -c duckdb-default --asset checks/sanity_check.sql
-- or paste the query inline:
--   bruin query -c duckdb-default -q "$(cat checks/sanity_check.sql)"
--
-- Every row is a named check with an actual_value; each check_name states what
-- the expected value should be so a passing run is easy to eyeball.

WITH checks AS (
    SELECT 'ingestion.trips row count' AS check_name,
           (SELECT COUNT(*) FROM ingestion.trips) AS actual_value

    UNION ALL
    SELECT 'staging.trips row count',
           (SELECT COUNT(*) FROM staging.trips)

    UNION ALL
    SELECT 'staging.trips duplicate trip_id count (expect 0)',
           (SELECT COUNT(*) - COUNT(DISTINCT trip_id) FROM staging.trips)

    UNION ALL
    SELECT 'staging.trips null trip_id count (expect 0)',
           (SELECT COUNT(*) FROM staging.trips WHERE trip_id IS NULL)

    UNION ALL
    SELECT 'staging.trips null pickup/dropoff count (expect 0)',
           (SELECT COUNT(*) FROM staging.trips WHERE pickup_datetime IS NULL OR dropoff_datetime IS NULL)

    UNION ALL
    SELECT 'staging.trips dropoff before pickup count (expect 0)',
           (SELECT COUNT(*) FROM staging.trips WHERE dropoff_datetime < pickup_datetime)

    UNION ALL
    SELECT 'staging.trips negative trip_distance count (expect 0)',
           (SELECT COUNT(*) FROM staging.trips WHERE trip_distance < 0)

    UNION ALL
    SELECT 'staging.trips negative fare_amount count (expect 0)',
           (SELECT COUNT(*) FROM staging.trips WHERE fare_amount < 0)

    UNION ALL
    SELECT 'staging.trips negative total_amount count (expect 0)',
           (SELECT COUNT(*) FROM staging.trips WHERE total_amount < 0)

    UNION ALL
    SELECT 'staging.trips distinct taxi_type count',
           (SELECT COUNT(DISTINCT taxi_type) FROM staging.trips)

    UNION ALL
    SELECT 'reports.trips_report row count (days x taxi_type)',
           (SELECT COUNT(*) FROM reports.trips_report)

    UNION ALL
    SELECT 'reports.trips_report duplicate (taxi_type, pickup_date) count (expect 0)',
           (SELECT COUNT(*) FROM (
                SELECT taxi_type, pickup_date, COUNT(*) AS c
                FROM reports.trips_report
                GROUP BY taxi_type, pickup_date
                HAVING COUNT(*) > 1
            ))

    UNION ALL
    SELECT 'staging vs reports trip_count diff (expect 0)',
           (SELECT (SELECT COUNT(*) FROM staging.trips) - (SELECT COALESCE(SUM(trip_count), 0) FROM reports.trips_report))

    UNION ALL
    SELECT 'staging vs reports total_amount diff (expect ~0)',
           (SELECT ROUND(
                (SELECT COALESCE(SUM(total_amount), 0) FROM staging.trips)
                - (SELECT COALESCE(SUM(total_amount), 0) FROM reports.trips_report)
           , 2))
)

SELECT * FROM checks ORDER BY check_name;
