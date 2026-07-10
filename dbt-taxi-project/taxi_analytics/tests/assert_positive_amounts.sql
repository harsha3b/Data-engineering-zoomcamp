-- fails if any trip in fct_trips has a negative fare or total amount
-- (should be impossible after our staging filters, this is a safety net)

select
    unique_row_id,
    fare_amount,
    total_amount
from {{ ref('fct_trips') }}
where fare_amount < 0
   or total_amount < 0