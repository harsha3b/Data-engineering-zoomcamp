with source as (
    select * from {{ source('staging', 'fhv_tripdata_external') }}
),

renamed as (
    select
        -- identifiers
        dispatching_base_num,
        affiliated_base_number          as affiliated_base_num,

        -- locations (renamed from mixed-case CSV originals)
        PUlocationID                    as pickup_location_id,
        DOlocationID                    as dropoff_location_id,

        -- timestamps (dropOff_datetime renamed to match project convention)
        pickup_datetime,
        dropOff_datetime                as dropoff_datetime,

        -- flags
        SR_Flag                         as sr_flag

    from source
    where dispatching_base_num is not null
)

select * from renamed