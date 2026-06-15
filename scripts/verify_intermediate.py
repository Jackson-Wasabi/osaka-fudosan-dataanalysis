# -*- coding: utf-8 -*-
"""Step 8 intermediate モデルの検証クエリ（読み取り専用）。
gcloud サブプロセスのハングを回避するため、ADC コピーを明示指定して接続する。
実行: GOOGLE_APPLICATION_CREDENTIALS と GOOGLE_CLOUD_PROJECT を設定して python で実行。
"""
import os
from google.cloud import bigquery

PROJ = "osaka-fudosan-dataanalysis"
STG = f"{PROJ}.osaka_real_estate_staging"
INT = f"{PROJ}.osaka_real_estate_intermediate"
client = bigquery.Client(project=PROJ)


def q(label, sql):
    print(f"\n=== {label} ===")
    for row in client.query(sql).result():
        print(dict(row))


# 1. stg_transactions: スコープ整合（D-011: 大阪市24,613 / scope内7,796想定）
q("stg_transactions 件数・スコープ", f"""
SELECT
  COUNT(*) AS total_osaka_city,
  COUNTIF(scope_flag) AS scope_true,
  COUNTIF(NOT scope_flag) AS scope_false,
  ROUND(AVG(CAST(station_name IS NULL OR station_name = '' AS INT64)) * 100, 2) AS station_blank_pct,
  COUNTIF(price IS NULL) AS price_null,
  COUNTIF(area_sqm IS NULL) AS area_null
FROM `{STG}.stg_transactions`
""")

# 2. scope内の駅別10件以上（D-011: 134駅想定）
q("scope内 駅別10件以上の駅数", f"""
SELECT COUNT(*) AS stations_ge10 FROM (
  SELECT station_name FROM `{STG}.stg_transactions`
  WHERE scope_flag AND station_name != ''
  GROUP BY station_name HAVING COUNT(*) >= 10)
""")

# 3. int_station_market_features: Fold別の駅数・中央値レンジ
q("int_station_market_features Fold別", f"""
SELECT fold,
  COUNT(*) AS station_rows,
  COUNTIF(station_transaction_count >= 10) AS stations_ge10,
  ROUND(MIN(station_median_price_per_sqm)) AS min_median_pps,
  ROUND(MAX(station_median_price_per_sqm)) AS max_median_pps,
  COUNTIF(station_median_price_per_sqm IS NULL) AS median_null
FROM `{INT}.int_station_market_features`
GROUP BY fold ORDER BY fold
""")

# 4. int_station_land_price_features: 距離分布
q("int_station_land_price_features 距離", f"""
SELECT
  COUNT(*) AS station_rows,
  ROUND(MIN(land_price_distance_m)) AS min_dist_m,
  ROUND(APPROX_QUANTILES(land_price_distance_m, 2)[OFFSET(1)]) AS median_dist_m,
  ROUND(MAX(land_price_distance_m)) AS max_dist_m,
  COUNTIF(land_price_distance_m > 1000) AS over_1000m,
  COUNTIF(nearest_land_price IS NULL) AS price_null
FROM `{INT}.int_station_land_price_features`
""")

# 5. int_transactions_with_station_features: Fold/split分布・結合率・特徴量NULL率
q("int_transactions_with_station_features Fold/split・結合率", f"""
SELECT fold, split,
  COUNT(*) AS n_rows,
  COUNTIF(station_joined) AS joined,
  ROUND(AVG(CAST(station_joined AS INT64)) * 100, 1) AS joined_pct,
  COUNTIF(station_median_price_per_sqm IS NULL) AS median_feat_null,
  COUNTIF(nearest_land_price IS NULL) AS land_null
FROM `{INT}.int_transactions_with_station_features`
GROUP BY fold, split ORDER BY fold, split
""")

print("\n検証完了")
