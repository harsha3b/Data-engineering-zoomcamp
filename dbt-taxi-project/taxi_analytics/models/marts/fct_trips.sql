with trips as (

    select * from {{ ref('stg_green_tripdata') }}

),

pickup_zone as (

    select * from {{ ref('stg_zones') }}

),

dropoff_zone as (

    select * from {{ ref('stg_zones') }}

),

final as (

    select
        trips.unique_row_id,
        trips.vendor_id,
        trips.pickup_datetime,
        trips.dropoff_datetime,
        trips.rate_code_id,
        trips.trip_type,

        -- pickup zone info
        trips.pickup_location_id,
        pickup_zone.borough as pickup_borough,
        pickup_zone.zone    as pickup_zone,

        -- dropoff zone info
        trips.dropoff_location_id,
        dropoff_zone.borough as dropoff_borough,
        dropoff_zone.zone    as dropoff_zone,

        trips.passenger_count,
        trips.trip_distance,
        trips.fare_amount,
        trips.extra,
        trips.mta_tax,
        trips.tip_amount,
        trips.tolls_amount,
        trips.improvement_surcharge,
        trips.congestion_surcharge,
        trips.total_amount,
        trips.payment_type,
        trips.payment_type_description

    from trips
    left join pickup_zone
        on trips.pickup_location_id = pickup_zone.location_id
    left join dropoff_zone
        on trips.dropoff_location_id = dropoff_zone.location_id

    -- basic quality filters: business logic belongs here, not in staging
    where trips.trip_distance > 0
      and trips.fare_amount > 0

)

select * from final