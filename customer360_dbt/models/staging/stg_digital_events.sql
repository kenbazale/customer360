-- stg_digital_events.sql

with source as (

    select * from {{ source('raw', 'digital_events') }}

),

cleaned as (

    select
        event_id,
        customer_id,
        event_datetime,
        lower(trim(channel))     as channel,
        lower(trim(event_type))  as event_type

    from source

)

select * from cleaned