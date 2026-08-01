-- int_account_transaction_activity.sql
-- One row per account: transaction volume, spend, and recency signals.
-- Feeds the dormancy risk logic in the mart.


with transactions as (
    select * from {{ ref('stg_card_transactions')}}
    where account_id is not null --drop orphaned FK rows flagged by staging tests
),

aggregated as (
    select
        account_id,
        count(*)  as txn_count_12m,
        sum(case when is_approved then amount else 0 end) as total_spend_12m,
        max(txn_datetime)  as last_txn_date,
        datediff('day', max(txn_datetime), current_date) as days_since_last_txn
    from transactions
    group by account_id
)

select * from aggregated