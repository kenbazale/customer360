-- stg_customers.sql
-- Light cleaning only: standardize casing, trim whitespace, keep everything
-- else as-is. No filtering or deduplication here — that happens downstream
-- once quality checks have flagged what's dirty.

with source as (
    select * from {{ source('raw', 'customers') }}
),

cleaned as (
    select 
        customer_id,
        trim(full_name) as full_name,
        dob,
        national_id_masked,
        upper(trim(branch_code)) as branch_code,
        lower(trim(kyc_status)) as kyc_status,
        customer_since_date,
        lower(trim(segment)) as segment
    from source
)

select * from cleaned