-- int_customer_account_summary.sql
-- One row per customer: account counts, total balances, and the most
-- recent transaction activity across ALL of their accounts. This is the
-- customer-grain rollup that the mart's dormancy logic depends on.

with accounts as (

    select * from {{ ref('stg_accounts') }}
    where customer_id is not null

),

txn_activity as (

    select * from {{ ref('int_account_transaction_activity') }}

),

accounts_with_activity as (

    select
        a.customer_id,
        a.account_id,
        a.account_type,
        a.status,
        a.balance,
        t.days_since_last_txn

    from accounts a
    left join txn_activity t
        on a.account_id = t.account_id

),

aggregated as (

    select
        customer_id,
        count(distinct account_id)                         as total_accounts,
        count(distinct case when status = 'active' then account_id end)  as active_accounts,
        sum(balance)                                        as total_balance,
        min(days_since_last_txn)                            as days_since_most_recent_txn  -- most recent across all accounts

    from accounts_with_activity
    group by customer_id

)

select * from aggregated