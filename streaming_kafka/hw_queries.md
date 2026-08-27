3) How many trips have trip_distance > 5?
select count(*) from gt_processed_events where trip_distance > 5;

4) Which PULocationID had the most trips in a single 5-minute window?
SELECT PULocationID, num_trips
FROM gt_trip_counts_5min
ORDER BY num_trips DESC
LIMIT 3;

5) How many trips were in the longest session?
SELECT
    pulocationid,
    window_start,
    window_end,
    num_trips,
    (window_end - window_start) AS session_duration
FROM gt_trip_sessions
ORDER BY session_duration DESC
LIMIT 1;

6) Tumbling window - largest tip
Which hour had the highest total tip amount?

SELECT
    window_start,
    total_tips
FROM gt_hourly_tips
ORDER BY total_tips DESC
LIMIT 1;



