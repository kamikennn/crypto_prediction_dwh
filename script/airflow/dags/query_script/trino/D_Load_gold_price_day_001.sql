INSERT INTO
    hive.gold_raw.gold_price_day (
        id,
        low,
        high,
        open,
        close,
        volume,
        adjclose,
        currency,
        dt_unix,
        dt,
        tz_gmtoffset,
        ts_insert_utc,
        year,
        month,
        day
    )
SELECT
    id,
    low,
    high,
    open,
    close,
    volume,
    adjclose,
    currency,
    dt_unix,
    dt,
    tz_gmtoffset,
    ts_insert_utc,
    year (from_unixtime (dt_unix)),
    month (from_unixtime (dt_unix)),
    day (from_unixtime (dt_unix))
FROM
    cassandra.gold.gold_price_day
WHERE
    dt > (
        SELECT
            COALESCE(MAX(dt), CAST('1111-01-01' AS date))
        FROM
            hive.gold_raw.gold_price_day
    )