with fct_table as (
    select
        {{ dbt_utils.generate_surrogate_key([
            'vendor_id',
            'pickup_datetime',
            'dropoff_datetime',
            'pickup_location_id',
            'dropoff_location_id'
        ]) }} as trip_id,
        *
    from {{ ref('int_trips_2019_unioned') }}
    qualify row_number() over (
        partition by vendor_id, pickup_datetime, dropoff_datetime, pickup_location_id, dropoff_location_id
        order by pickup_datetime
    ) = 1
),
payment_type_lookup as (
    select * from {{ ref('payment_type_lookup') }}
)

select
    f.*,
    p.description as payment_type_description
from fct_table f
left join payment_type_lookup p
    on f.payment_type = p.payment_type
