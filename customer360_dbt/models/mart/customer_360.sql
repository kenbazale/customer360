-- depends_on: {{ ref('stg_customers') }}
-- customer_360.sql
-- One row per customer: the unified view combining account activity, loan
-- status, and digital engagement into business-ready risk and engagement
-- signals. This is the model a marketing, risk, or relationship team would
-- actually query.
--
-- Scoring logic below reflects patterns observed in real core banking
-- operations (dormancy monitoring, delinquency thresholds, KYC lifecycle
-- management) rather than arbitrary rounding.

with customers as (

    select * from {{ ref('stg_customers') }}
    where customer_id is not null  -- drop the null-PK faults; nothing to key a 360 view on
    -- Deduplicate: Session 1's generator intentionally injects a handful of
    -- duplicate customer_id values (simulating a bad batch reload / merge
    -- error). Keep one deterministic row per customer_id rather than
    -- silently fanning out joins downstream.
    qualify row_number() over (
        partition by customer_id
        order by customer_since_date asc, full_name asc
    ) = 1

),

account_summary as (

    select * from {{ ref('int_customer_account_summary') }}

),

loan_status as (

    select * from {{ ref('int_customer_loan_status') }}

),

digital_activity as (

    select * from {{ ref('int_customer_digital_activity') }}

),

joined as (

    select
        c.customer_id,
        c.full_name,
        c.branch_code,
        c.segment,
        c.kyc_status,
        c.customer_since_date,
        datediff('year', c.customer_since_date, current_date())  as tenure_years,

        coalesce(a.total_accounts, 0)              as total_accounts,
        coalesce(a.active_accounts, 0)              as active_accounts,
        coalesce(a.total_balance, 0)                as total_balance,
        a.days_since_most_recent_txn,

        coalesce(l.loan_account_count, 0)           as loan_account_count,
        l.max_days_past_due,
        coalesce(l.total_loan_balance, 0)           as total_loan_balance,

        coalesce(d.event_count_12m, 0)               as digital_event_count_12m,
        coalesce(d.login_count_12m, 0)                as digital_login_count_12m,
        d.days_since_last_digital_event

    from customers c
    left join account_summary a on c.customer_id = a.customer_id
    left join loan_status l      on c.customer_id = l.customer_id
    left join digital_activity d on c.customer_id = d.customer_id

),

scored as (

    select
        *,

        -- Dormancy risk: no transaction activity in 90+ days across any
        -- account, or no accounts/activity recorded at all.
        case
            when days_since_most_recent_txn is null then 'unknown'
            when days_since_most_recent_txn > 90     then 'high'
            when days_since_most_recent_txn > 60     then 'medium'
            else 'low'
        end as dormancy_risk,

        -- Delinquency signal: standard banking arrears buckets.
        case
            when loan_account_count = 0                     then 'no_loan'
            when max_days_past_due is null or max_days_past_due = 0 then 'current'
            when max_days_past_due <= 30                     then 'watch'          -- 1-30 DPD
            when max_days_past_due <= 90                     then 'arrears'        -- 31-90 DPD
            else 'default_risk'                               -- 90+ DPD
        end as delinquency_status,

        -- KYC completeness score: reflects real regulatory lifecycle risk,
        -- not just a flat category label.
        case
            when kyc_status = 'complete' then 100
            when kyc_status = 'pending'  then 50
            when kyc_status = 'expired'  then 0
            else null  -- unrecognized status, caught by staging tests already
        end as kyc_completeness_score,

        -- Engagement score: simple 0-100 blend of digital activity volume
        -- and recency. Weighted toward recency since a customer who logged
        -- in 40 times a year ago is less "engaged" than one who logs in
        -- weekly right now.
        case
            when days_since_last_digital_event is null then 0
            else greatest(0, least(100,
                (least(digital_event_count_12m, 50) * 1.0)          -- volume component, capped
                + (case
                    when days_since_last_digital_event <= 7  then 50
                    when days_since_last_digital_event <= 30 then 30
                    when days_since_last_digital_event <= 90 then 10
                    else 0
                   end)                                              -- recency component
            ))
        end as engagement_score

    from joined

)

select * from scored