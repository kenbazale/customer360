-- int_customer_loan_status.sql
-- One row per customer with a loan: worst-case days-past-due across all
-- their loan accounts. Feeds the delinquency signal in the mart.

with accounts as (

    select * from {{ ref('stg_accounts') }}
    where account_type = 'loan'
      and customer_id is not null

),

aggregated as (

    select
        customer_id,
        count(*)                          as loan_account_count,
        max(loan_days_past_due)           as max_days_past_due,
        sum(balance)                      as total_loan_balance

    from accounts
    group by customer_id

)

select * from aggregated