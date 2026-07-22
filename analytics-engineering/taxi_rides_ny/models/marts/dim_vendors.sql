with vendors as (
    select distinct vendor_id
    from {{ ref('int_trips_2019_unioned') }}
)

select
    vendor_id,
    {{get_vendor_names('vendor_id')}} as vendor_name --macro for case statement
from vendors