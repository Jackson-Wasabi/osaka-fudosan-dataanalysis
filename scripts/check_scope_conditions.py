import os
from google.cloud import bigquery

client = bigquery.Client(project=os.environ.get("GOOGLE_CLOUD_PROJECT", "osaka-fudosan-dataanalysis"))

sql = """
WITH base AS (
  SELECT
    SAFE_CAST(trade_price_total AS INT64) AS price,
    SAFE_CAST(area_sqm AS FLOAT64) AS area,
    SAFE_CAST(nearest_station_distance_min AS INT64) AS walk,
    SAFE_CAST(SUBSTR(trade_period,1,4) AS INT64)
      - SAFE_CAST(REGEXP_EXTRACT(built_year, r'^([0-9]{4})年$') AS INT64) AS age,
    nearest_station_name AS st
  FROM `osaka_real_estate.raw_transactions`
  WHERE STARTS_WITH(city_name, '大阪市')
),
scoped AS (
  SELECT *,
    (area BETWEEN 20 AND 55)  AS a55,
    (area BETWEEN 20 AND 70)  AS a70,
    (area BETWEEN 20 AND 80)  AS a80,
    (walk <= 20)              AS w20,
    (price BETWEEN 5000000 AND 80000000) AS p_ok,
    (age >= 5 OR age IS NULL) AS age_min5
  FROM base
),
station_counts AS (
  SELECT cond, st, COUNT(*) AS cnt FROM (
    SELECT '1_area55_age50' AS cond, st FROM scoped WHERE a55 AND w20 AND p_ok AND age BETWEEN 5 AND 50 AND st != ''
    UNION ALL
    SELECT '2_area70_age50', st FROM scoped WHERE a70 AND w20 AND p_ok AND age BETWEEN 5 AND 50 AND st != ''
    UNION ALL
    SELECT '3_area80_age50', st FROM scoped WHERE a80 AND w20 AND p_ok AND age BETWEEN 5 AND 50 AND st != ''
    UNION ALL
    SELECT '4_area70_age_free', st FROM scoped WHERE a70 AND w20 AND p_ok AND age_min5 AND st != ''
    UNION ALL
    SELECT '5_area80_age_free', st FROM scoped WHERE a80 AND w20 AND p_ok AND age_min5 AND st != ''
  )
  GROUP BY cond, st
)
SELECT
  cond,
  SUM(cnt)           AS total_rows,
  COUNT(*)           AS all_stations,
  COUNTIF(cnt >= 10) AS st_10plus,
  COUNTIF(cnt >= 15) AS st_15plus,
  COUNTIF(cnt >= 20) AS st_20plus,
  COUNTIF(cnt >= 25) AS st_25plus,
  COUNTIF(cnt >= 30) AS st_30plus
FROM station_counts
GROUP BY cond
ORDER BY cond
"""

rows = client.query(sql).result()

label = {
    "1_area55_age50":   "①面積55・築50",
    "2_area70_age50":   "②面積70・築50",
    "3_area80_age50":   "③面積80・築50",
    "4_area70_age_free":"④面積70・築制限なし",
    "5_area80_age_free":"⑤面積80・築制限なし",
}

print(f"{'条件':<18} {'総件数':>7} {'全駅':>5} {'10件+':>6} {'15件+':>6} {'20件+':>6} {'25件+':>6} {'30件+':>6}")
print("-" * 70)
for row in rows:
    name = label.get(row.cond, row.cond)
    print(f"{name:<18} {row.total_rows:>7,} {row.all_stations:>5} {row.st_10plus:>6} {row.st_15plus:>6} {row.st_20plus:>6} {row.st_25plus:>6} {row.st_30plus:>6}")
