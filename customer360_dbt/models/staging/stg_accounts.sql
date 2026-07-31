with source as (
    select * from {{ source('raw', 'accounts') }}
),

cleaned as (
    select
        account_id,
        customer_id,
        lower(trim(account_type)) as account_type,
        product_code,
        open_date,
        balance,
        lower(trim(status)) as status,
        loan_days_past_due,
    from source

)

select * from cleaned
