DELETE FROM
    hive.stock_mart.stock_index_indicator_day
WHERE
    year = year(cast('${target_date}' as date))
    and month = month(cast('${target_date}' as date))
