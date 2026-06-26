-- Third-party vendor enrichment (FEMA-style flood zone feed).
-- Kept as its own staging model so the vendor join is explicit and testable.
with source as (
    select * from {{ ref('raw_vendor_flood') }}
)
select
    location_id,
    flood_zone,
    cast(flood_risk_score as integer) as flood_risk_score,
    vendor_source
from source
