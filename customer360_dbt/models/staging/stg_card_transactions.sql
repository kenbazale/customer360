-- stg_card_transactions.sql

with source as (

    select * from {{ source('raw', 'card_transactions') }}

),

cleaned as (

    select
        txn_id,
        account_id,
        txn_datetime,
        upper(trim(channel))            as channel,
        amount,
        lower(trim(merchant_category))  as merchant_category,
        response_code,
        case when response_code = '00' then true else false end as is_approved

    from source

)

select * from cleaned