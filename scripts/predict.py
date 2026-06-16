# -*- coding: utf-8 -*-
"""Step 10 フェーズ3: 03_predict.sql を実行し predictions_model_c を作成・検証（読み取り検証）。
gcloud ハング回避のため ADC コピーを明示指定。
実行: GOOGLE_APPLICATION_CREDENTIALS=/tmp/adc.json GOOGLE_CLOUD_PROJECT=osaka-fudosan-dataanalysis python -u scripts/predict.py
"""
import os
from google.cloud import bigquery

PROJ = "osaka-fudosan-dataanalysis"
TBL = f"{PROJ}.osaka_real_estate.predictions_model_c"
SQL_FILE = os.path.join(os.path.dirname(__file__), "..", "sql", "bqml", "03_predict.sql")
client = bigquery.Client(project=PROJ)


def run(label, sql):
    print(f"\n=== {label} ===")
    rows = [dict(r) for r in client.query(sql).result()]
    if not rows:
        print("  (0 rows)")
        return
    cols = list(rows[0].keys())
    w = {c: max(len(c), *(len(str(r[c])) for r in rows)) for c in cols}
    print("  " + " | ".join(c.ljust(w[c]) for c in cols))
    print("  " + "-+-".join("-" * w[c] for c in cols))
    for r in rows:
        print("  " + " | ".join(str(r[c]).ljust(w[c]) for c in r))


# 1. CREATE TABLE 実行
print("=== predictions_model_c を作成 ===")
with open(SQL_FILE, encoding="utf-8") as f:
    ddl = f.read()
client.query(ddl).result()
print("  作成完了")

# 2. 件数・NULL・min/max
run("件数・NULL・予測の範囲", f"""
SELECT
  COUNT(*) AS n_rows,
  COUNTIF(predicted_price_per_sqm IS NULL) AS pred_null,
  COUNTIF(actual_price_per_sqm IS NULL) AS actual_null,
  COUNT(DISTINCT station_name) AS n_stations,
  ROUND(MIN(predicted_price_per_sqm)) AS pred_min,
  ROUND(MAX(predicted_price_per_sqm)) AS pred_max,
  ANY_VALUE(smearing_factor) AS smearing_factor
FROM `{TBL}`
""")

# 3. 全体バイアス（予測 vs 実勢・2025）。フェーズ2のModel C符号付バイアス(-9〜13%)と整合するか
run("全体バイアス（中央値・平均）", f"""
SELECT
  ROUND(APPROX_QUANTILES(actual_price_per_sqm,2)[OFFSET(1)]) AS actual_median,
  ROUND(APPROX_QUANTILES(predicted_price_per_sqm,2)[OFFSET(1)]) AS pred_median,
  ROUND(AVG((predicted_price_per_sqm-actual_price_per_sqm)/actual_price_per_sqm),4) AS signed_bias_mean,
  ROUND(APPROX_QUANTILES((predicted_price_per_sqm-actual_price_per_sqm)/actual_price_per_sqm,2)[OFFSET(1)],4) AS signed_bias_median
FROM `{TBL}`
""")

# 4. サンプル（最も割安に見える物件＝逆選択の確認用・額面では信じない）
run("参考: 額面で最も割安な物件 上位5（逆選択リスクあり・要確認）", f"""
SELECT station_name, ward, area_sqm, building_age_years, walk_minutes,
  actual_price_per_sqm, predicted_price_per_sqm,
  ROUND(actual_price_per_sqm/predicted_price_per_sqm-1,3) AS raw_deviation
FROM `{TBL}`
ORDER BY raw_deviation ASC
LIMIT 5
""")

print("\nフェーズ3 完了")
