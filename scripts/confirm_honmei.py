# -*- coding: utf-8 -*-
"""本命10駅・上位5駅・要確認(平野)を mart_opportunity_list から確認（読み取り専用）。
本命の定義: stable_flag = TRUE AND high_risk_share < 0.10（D-033系・10駅想定）。
実行: python -u scripts/confirm_honmei.py
"""
import os
from google.cloud import bigquery

PROJ = os.environ.get("GOOGLE_CLOUD_PROJECT", "osaka-fudosan-dataanalysis")
MART = f"{PROJ}.osaka_real_estate_marts.mart_opportunity_list"
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


# 1. 全体駅数と本命駅数（本命 = stable_flag AND high_risk_share < 0.10）
run("駅数と本命駅数", f"""
SELECT
  COUNT(*)                                                    AS n_stations,
  COUNTIF(stable_flag)                                        AS n_stable,
  COUNTIF(stable_flag AND high_risk_share < 0.10)             AS n_honmei
FROM `{MART}`
""")

# 2. priority_score 上位8駅（本命判定つき）
run("priority_score 上位8駅", f"""
SELECT
  priority_rank,
  station_name,
  ward,
  ROUND(priority_score,1)              AS priority_score,
  ROUND(actual_median_price_per_sqm)   AS median_pps,
  stable_flag,
  ROUND(high_risk_share,3)             AS high_risk_share,
  (stable_flag AND high_risk_share < 0.10) AS is_honmei
FROM `{MART}`
ORDER BY priority_score DESC
LIMIT 8
""")

# 3. 本命10駅の一覧
run("本命10駅（stable_flag AND high_risk_share<0.10）", f"""
SELECT
  priority_rank, station_name, ward,
  ROUND(priority_score,1) AS priority_score,
  ROUND(actual_median_price_per_sqm) AS median_pps,
  ROUND(high_risk_share,3) AS high_risk_share
FROM `{MART}`
WHERE stable_flag AND high_risk_share < 0.10
ORDER BY priority_score DESC
""")

# 4. 平野の位置づけ（要確認の代表）
run("平野の状態", f"""
SELECT station_name, ward, priority_rank,
  ROUND(priority_score,1) AS priority_score,
  rank_risk,
  stable_flag,
  ROUND(old_seismic_share,3) AS old_seismic_share,
  ROUND(high_risk_share,3) AS high_risk_share
FROM `{MART}`
WHERE station_name = '平野'
""")

print("\n確認完了")
