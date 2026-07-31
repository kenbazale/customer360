-- int_customer_digital_activity.sql
-- One row per customer: digital channel engagement signals.
-- Feeds the engagement score in the mart.

with events as (

    select * from {{ ref('stg_digital_events') }}
    where customer_id is not null

),

aggregated as (

    select
        customer_id,
        count(*)                                                  as event_count_12m,
        count(case when event_type = 'login' then 1 end)          as login_count_12m,
        count(case when event_type = 'transfer' then 1 end)       as transfer_count_12m,
        count(case when event_type = 'bill_pay' then 1 end)       as bill_pay_count_12m,
        max(event_datetime)                                       as last_digital_event_date,
        datediff('day', max(event_datetime), current_date())      as days_since_last_digital_event

    from events
    group by customer_id

)

select * from aggregated