with source as (

    select * from {{ source('zoomcamp_raw', 'green_tripdata') }}

),

deduped as (

    select
        *,
        row_number() over (
            partition by unique_row_id
            order by filename
        ) as rn

    from source

),

renamed as (

    select
        unique_row_id,
        filename,

        safe_cast(VendorID as int64)      as vendor_id,
        safe_cast(RatecodeID as int64)    as rate_code_id,
        safe_cast(PULocationID as int64)  as pickup_location_id,
        safe_cast(DOLocationID as int64)  as dropoff_location_id,

        lpep_pickup_datetime  as pickup_datetime,
        lpep_dropoff_datetime as dropoff_datetime,

        store_and_fwd_flag,
        trip_type,
        passenger_count,
        trip_distance,

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
        case payment_type
            when 1 then 'Credit card'
            when 2 then 'Cash'
            when 3 then 'No charge'
            when 4 then 'Dispute'
            when 5 then 'Unknown'
            when 6 then 'Voided trip'
            else 'Unknown'
        end as payment_type_description

    from deduped
    where rn = 1

)

select * from renamed