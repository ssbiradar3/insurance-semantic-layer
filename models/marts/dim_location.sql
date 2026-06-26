-- Exposure dimension enriched with the third-party flood feed.
-- Left join keeps every location even if the vendor feed misses one,
-- and the relationships test downstream proves the join did not drop rows.
with loc as (
    select * from {{ ref('stg_locations') }}
),
flood as (
    select * from {{ ref('stg_vendor_flood') }}
)
select
    loc.location_id,
    loc.address,
    loc.city,
    loc.state,
    loc.zip,
    loc.latitude,
    loc.longitude,
    coalesce(flood.flood_zone, 'UNKNOWN') as flood_zone,
    flood.flood_risk_score,
    flood.vendor_source
from loc
left join flood on loc.location_id = flood.location_id
