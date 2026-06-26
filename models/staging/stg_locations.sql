with source as (
    select * from {{ ref('raw_locations') }}
)
select
    location_id,
    address,
    city,
    state,
    zip,
    cast(latitude as double)  as latitude,
    cast(longitude as double) as longitude
from source
