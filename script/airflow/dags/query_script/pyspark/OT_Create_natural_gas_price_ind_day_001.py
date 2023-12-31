import sys, os
from pyspark.sql import SparkSession
from pyspark.sql.functions import col
from pyspark.sql.types import *
from datetime import datetime
from stock_indicators import Quote
from stock_indicators import indicators
import pandas as pd
import pytz


jst = pytz.timezone("Asia/Tokyo")
ts_now = datetime.now(jst).strftime("%Y-%m-%d %H:%M:%S")

SPARK_MASTER_HOST = sys.argv[1]
SPARK_MASTER_PORT = sys.argv[2]
HIVE_METASTORE_HOST = sys.argv[3]
HIVE_METASTORE_PORT = sys.argv[4]

#############################################
# Create a SparkSession with Hive connection
#############################################
spark = (
    SparkSession.builder.appName("{} PySpark Hive Session for {}".format(ts_now, os.path.basename(__file__)))
    .config(
        "spark.master",
        "spark://{}:{}".format(SPARK_MASTER_HOST, SPARK_MASTER_PORT),
    )
    .config(
        "spark.hadoop.hive.metastore.uris",
        "thrift://{}:{}".format(HIVE_METASTORE_HOST, HIVE_METASTORE_PORT),
    )
    .config("spark.executor.memory", "10g")
    .config("spark.executor.cores", "2")
    .config("spark.debug.maxToStringFields", "100")
    .enableHiveSupport()
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")


#############################################
# Load historical data from Hive table
#############################################
target_schema = "gas_raw"
target_table = "natural_gas_price_day"
query = f"select id, cast(dt_create_utc as string) as dt, open, high, low, close, volume, \
    year, month, day from {target_schema}.{target_table}"
natural_gas_price_raw_df = spark.sql(query)

# Select distinct symbols.
natural_gas_price_symbol_df = spark.sql(f"select distinct id from {target_schema}.{target_table}")


#############################################
# Calculate indicators
#############################################
# Calculate the indicator for each symbol.
final_results = None
for row in natural_gas_price_symbol_df.select(natural_gas_price_symbol_df.id).collect():
    print("Target Natural Gas Symbol:", row.id)
    sp_natural_gas_price_history_df = natural_gas_price_raw_df.filter(natural_gas_price_raw_df.id == row.id)
    pd_natural_gas_price_history_df = sp_natural_gas_price_history_df.toPandas()

    # Create quotes
    N_mul = 1.0
    quotes = [
        Quote(
            datetime.strptime(d, "%Y-%m-%d"),
            o * N_mul,
            h * N_mul,
            l * N_mul,
            c * N_mul,
            v,
        )
        for d, o, h, l, c, v in zip(
            pd_natural_gas_price_history_df["dt"],
            pd_natural_gas_price_history_df["open"],
            pd_natural_gas_price_history_df["high"],
            pd_natural_gas_price_history_df["low"],
            pd_natural_gas_price_history_df["close"],
            pd_natural_gas_price_history_df["volume"],
        )
    ]

    indicator_values = {}

    #######################
    # Calcuration main
    #######################
    # MACD(12,26,9)
    macd_results = indicators.get_macd(quotes, fast_periods=12, slow_periods=26, signal_periods=9)
    indicator_values["macd"] = macd_results

    # Relative Strength Index (14)
    rsi_results = indicators.get_rsi(quotes, lookback_periods=14)
    indicator_values["rsi"] = rsi_results

    # Bollinger Bands(20, 2)
    bollinger_bands_results = indicators.get_bollinger_bands(quotes, lookback_periods=20, standard_deviations=2)
    indicator_values["bollinger_bands"] = bollinger_bands_results

    # On-Balance Volume
    obv_results = indicators.get_obv(quotes)
    indicator_values["obv"] = obv_results

    # Ichimoku Cloud (9,26,52)
    ichimoku_results = indicators.get_ichimoku(quotes, tenkan_periods=9, kijun_periods=26, senkou_b_periods=52)
    indicator_values["ichimoku"] = ichimoku_results

    # Stochastic Oscillator %K(14),%D(3) (slow)
    stoch_results = indicators.get_stoch(quotes, lookback_periods=14, signal_periods=3, smooth_periods=3)
    indicator_values["stoch"] = stoch_results

    # Aroon
    aroon_results = indicators.get_aroon(quotes, lookback_periods=25)
    indicator_values["aroon"] = aroon_results

    # Simple Moving Average 5 days
    sma5_results = indicators.get_sma(quotes, lookback_periods=5)
    indicator_values["sma5"] = sma5_results

    # Simple Moving Average 10 days
    sma10_results = indicators.get_sma(quotes, lookback_periods=10)
    indicator_values["sma10"] = sma10_results

    # Simple Moving Average 30 days
    sma30_results = indicators.get_sma(quotes, lookback_periods=30)
    indicator_values["sma30"] = sma30_results

    # Exponential Moving Average 5 days
    ema5_results = indicators.get_ema(quotes, lookback_periods=5)
    indicator_values["ema5"] = ema5_results

    # Exponential Moving Average 10 days
    ema10_results = indicators.get_ema(quotes, lookback_periods=10)
    indicator_values["ema10"] = ema10_results

    # Exponential Moving Average 30 days
    ema30_results = indicators.get_ema(quotes, lookback_periods=30)
    indicator_values["ema30"] = ema30_results

    ##########################
    # Merge all indicator values
    ##########################
    all_indicaters = {}
    for data in zip(
        indicator_values["macd"],
        indicator_values["rsi"],
        indicator_values["bollinger_bands"],
        indicator_values["obv"],
        indicator_values["ichimoku"],
        indicator_values["stoch"],
        indicator_values["aroon"],
        indicator_values["sma5"],
        indicator_values["sma10"],
        indicator_values["sma30"],
        indicator_values["ema5"],
        indicator_values["ema10"],
        indicator_values["ema30"],
    ):
        all_indicaters[data[0].date.strftime("%Y-%m-%d")] = [
            data[0].date,
            float(data[0].macd) if data[0].macd else None,
            float(data[0].signal) if data[0].signal else None,
            float(data[1].rsi) if data[1].rsi else None,
            float(data[2].sma) if data[2].sma else None,
            float(data[2].lower_band) if data[2].lower_band else None,
            float(data[2].upper_band) if data[2].upper_band else None,
            float(data[3].obv) if data[3].obv else None,
            float(data[3].obv_sma) if data[3].obv_sma else None,
            float(data[4].chikou_span) if data[4].chikou_span else None,
            float(data[4].kijun_sen) if data[4].kijun_sen else None,
            float(data[4].tenkan_sen) if data[4].tenkan_sen else None,
            float(data[4].senkou_span_a) if data[4].senkou_span_a else None,
            float(data[4].senkou_span_b) if data[4].senkou_span_b else None,
            float(data[5].d) if data[5].d else None,
            float(data[5].k) if data[5].k else None,
            float(data[5].j) if data[5].j else None,
            float(data[6].aroon_up) if data[6].aroon_up else None,
            float(data[6].aroon_down) if data[6].aroon_down else None,
            float(data[6].oscillator) if data[6].oscillator else None,
            float(data[7].sma) if data[7].sma else None,
            float(data[8].sma) if data[8].sma else None,
            float(data[9].sma) if data[9].sma else None,
            float(data[10].ema) if data[10].ema else None,
            float(data[11].ema) if data[11].ema else None,
            float(data[12].ema) if data[12].ema else None,
            N_mul,
        ]

    columns = [
        "dt_",
        "macd",
        "macd_single",
        "rsi",
        "bollinger_bands_sma",
        "bollinger_bands_lower_band",
        "bollinger_bands_upper_band",
        "obv",
        "obv_sma",
        "ichimoku_chikou_span",
        "ichimoku_kijun_sen",
        "ichimoku_tenkan_sen",
        "ichimoku_senkou_span_a",
        "ichimoku_senkou_span_b",
        "stoch_oscillator",
        "stoch_signal",
        "stoch_percent_j",
        "aroon_up",
        "aroon_down",
        "aroon_oscillator",
        "sma5",
        "sma10",
        "sma30",
        "ema5",
        "ema10",
        "ema30",
        "N_multiple",
    ]

    # Define a schema of spark dataframe for the indicators
    schema = StructType(
        [
            StructField("dt_", DateType(), False),
            StructField("macd", FloatType(), True),
            StructField("macd_single", FloatType(), True),
            StructField("rsi", FloatType(), True),
            StructField("bollinger_bands_sma", FloatType(), True),
            StructField("bollinger_bands_lower_band", FloatType(), True),
            StructField("bollinger_bands_upper_band", FloatType(), True),
            StructField("obv", FloatType(), True),
            StructField("obv_sma", FloatType(), True),
            StructField("ichimoku_chikou_span", FloatType(), True),
            StructField("ichimoku_kijun_sen", FloatType(), True),
            StructField("ichimoku_tenkan_sen", FloatType(), True),
            StructField("ichimoku_senkou_span_a", FloatType(), True),
            StructField("ichimoku_senkou_span_b", FloatType(), True),
            StructField("stoch_oscillator", FloatType(), True),
            StructField("stoch_signal", FloatType(), True),
            StructField("stoch_percent_j", FloatType(), True),
            StructField("aroon_up", FloatType(), True),
            StructField("aroon_down", FloatType(), True),
            StructField("aroon_oscillator", FloatType(), True),
            StructField("sma5", FloatType(), True),
            StructField("sma10", FloatType(), True),
            StructField("sma30", FloatType(), True),
            StructField("ema5", FloatType(), True),
            StructField("ema10", FloatType(), True),
            StructField("ema30", FloatType(), True),
            StructField("N_multiple", FloatType(), True),
        ]
    )

    # Create pandas dataframe from python dict object that contains the indicators.
    pd_all_indicaters_df = pd.DataFrame.from_dict(all_indicaters, orient="index", columns=columns)

    # Create spark dataframe from pandas dataframe
    sp_all_indicaters_df = spark.createDataFrame(pd_all_indicaters_df, schema=schema)

    # Join the two spark dataframes of historical data and indicator data.
    sp_history_with_indicators_df = sp_natural_gas_price_history_df.join(
        sp_all_indicaters_df,
        sp_natural_gas_price_history_df.dt == sp_all_indicaters_df.dt_,
        "outer",
    )

    # Union spark dataframe
    if final_results:
        final_results = final_results.unionAll(sp_history_with_indicators_df)
    else:
        final_results = sp_history_with_indicators_df


#############################################
# Insert the calculated indicator values to the hive mart WRK table
#############################################
insert_data = final_results.select(
    col("id"),
    col("dt_"),
    col("low"),
    col("high"),
    col("open"),
    col("close"),
    col("volume"),
    col("macd"),
    col("macd_single"),
    col("rsi"),
    col("bollinger_bands_sma"),
    col("bollinger_bands_lower_band"),
    col("bollinger_bands_upper_band"),
    col("obv"),
    col("obv_sma"),
    col("ichimoku_chikou_span"),
    col("ichimoku_kijun_sen"),
    col("ichimoku_tenkan_sen"),
    col("ichimoku_senkou_span_a"),
    col("ichimoku_senkou_span_b"),
    col("stoch_oscillator"),
    col("stoch_signal"),
    col("stoch_percent_j"),
    col("aroon_up"),
    col("aroon_down"),
    col("aroon_oscillator"),
    col("sma5"),
    col("sma10"),
    col("sma30"),
    col("ema5"),
    col("ema10"),
    col("ema30"),
    col("N_multiple"),
    col("year"),
    col("month"),
    col("day"),
)

# Insert the calculated indicator values
target_schema = "gas_mart"
target_table = "natural_gas_indicator_day"
insert_data.write.insertInto(f"{target_schema}.{target_table}", overwrite=True)
