# -*- coding: utf-8 -*-
"""サマリーのファネル数値（2,097件 / 151駅 / 66駅）を mart_condo_price から確認（読み取り専用）。
2025年 = fold A の test split。スコープ（中古マンション・20〜60㎡）は上流で適用済み。
実行: python -u scripts/confirm_funnel.py
"""
import os
from google.cloud import bigquery

PROJ = "osaka-fudosan-dataanalysis"
MART = f"{PROJ}.osaka_real_estate_marts.mart_condo_price"
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
        print("  " + " | ".join(str(r[c]).ljust(w[c]) for c in cols))


# 1. 2025年(fold A test)の母数：件数・駅数・適格駅数
run("2025年(fold A test) 母数", f"""
SELECT
  COUNT(*)                                   AS n_transactions,
  COUNT(DISTINCT station_name)               AS n_stations_all,
  COUNT(DISTINCT IF(model_eligible, station_name, NULL)) AS n_stations_eligible
FROM `{MART}`
WHERE fold = 'A' AND split = 'test' AND trade_year = 2025
""")

# 2. 10件以上の駅数（全体 / 適格のみ）= ランク対象66駅の確認
run("駅あたり件数で10件以上の駅数", f"""
WITH per_station AS (
  SELECT station_name,
         COUNT(*) AS n,
         LOGICAL_OR(model_eligible) AS eligible
  FROM `{MART}`
  WHERE fold = 'A' AND split = 'test' AND trade_year = 2025
  GROUP BY station_name
)
SELECT
  COUNTIF(n >= 10)                  AS stations_ge10_all,
  COUNTIF(n >= 10 AND eligible)     AS stations_ge10_eligible
FROM per_station
""")

# 3. 念のため：trade_year と fold/split の分布（2025の所在確認）
run("trade_year × split 件数（fold A）", f"""
SELECT trade_year, split, COUNT(*) AS n
FROM `{MART}`
WHERE fold = 'A'
GROUP BY trade_year, split
ORDER BY trade_year, split
""")

print("\n確認完了")
