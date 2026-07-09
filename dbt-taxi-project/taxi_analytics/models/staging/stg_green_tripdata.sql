with source as (

    select * from {{ source('zoomcamp_raw', 'green_tripdata') }}

),

renamed as (

    select
        unique_row_id,
        filename,

        -- ids
        safe_cast(VendorID as int64)      as vendor_id,
        safe_cast(RatecodeID as int64)    as rate_code_id,
        safe_cast(PULocationID as int64)  as pickup_location_id,
        safe_cast(DOLocationID as int64)  as dropoff_location_id,

        -- timestamps
        lpep_pickup_datetime  as pickup_datetime,
        lpep_dropoff_datetime as dropoff_datetime,

        store_and_fwd_flag,
        trip_type,
        passenger_count,
        trip_distance,

        -- money
        fare_amount,
        extra,
        mta_tax,
        tip_amount,
        tolls_amount,
        ehail_fee,
        improvement_surcharge,
        congestion_surcharge,
        total_amount,

        payment_type,
        -- human-readable payment type, since the raw column is just an int code
        case payment_type
            when 1 then 'Credit card'
            when 2 then 'Cash'
            when 3 then 'No charge'
            when 4 then 'Dispute'
            when 5 then 'Unknown'
            when 6 then 'Voided trip'
            else 'Unknown'
        end as payment_type_description

    from source

)

select * from renamed