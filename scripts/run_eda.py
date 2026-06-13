# -*- coding: utf-8 -*-
"""Step 5 EDA 統合スクリプト（読み取り専用）
- QUERIES の SQL を sql/checks/*.sql へ書き出し（このスクリプトが単一の真実 = SQLとグラフの連携保証）
- BigQuery で実行し outputs/tables/*.csv へ保存
- グラフ（結論タイトル + 出典キャプション付き）を outputs/figures/*.png へ生成
- docs/eda_report.md（決定事項サマリー + SQL + グラフ + 所見）を自動生成
データの変更は一切行わない。
"""
import csv
import io
import os
import subprocess
from datetime import date

PROJECT = "osaka-fudosan-dataanalysis"
ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
SQL_DIR = os.path.join(ROOT, "sql", "checks")
TBL_DIR = os.path.join(ROOT, "outputs", "tables")
FIG_DIR = os.path.join(ROOT, "outputs", "figures")
DOC = os.path.join(ROOT, "docs", "eda_report.md")
TODAY = date.today().isoformat()
SNAPSHOT = ("データ取得日: 2026-06-12 / 対象スコープ: 大阪市・中古マンション等・成約価格情報 "
            "2021Q1-2025Q4（24,613行）。raw全体は大阪府47,386行で、形式チェックは府全体で実施済み（D-010）")

_BASE_SELECT = """WITH base AS (
  SELECT
    SAFE_CAST(trade_price_total AS INT64) AS price,
    SAFE_CAST(area_sqm AS FLOAT64) AS area,
    SAFE_DIVIDE(SAFE_CAST(trade_price_total AS INT64), SAFE_CAST(area_sqm AS FLOAT64)) AS pps,
    SAFE_CAST(SUBSTR(trade_period, 1, 4) AS INT64)
      - SAFE_CAST(REGEXP_EXTRACT(built_year, r'^([0-9]{4})年$') AS INT64) AS age,
    SAFE_CAST(nearest_station_distance_min AS INT64) AS walk,
    nearest_station_name AS st_name,
    built_year, trade_period, city_name, district_name, layout, renovation
  FROM `osaka_real_estate.raw_transactions`"""

# 分布・外れ値の確認は分析対象スコープ（大阪市）で行う（D-010）
BASE_CTE = _BASE_SELECT + "\n  WHERE STARTS_WITH(city_name, '大阪市')\n)"
# Step6試算（検査10）だけは府全体から絞り込みの過程を見るため無フィルター
BASE_ALL = _BASE_SELECT + "\n)"

Q = {}  # id -> (filename, sql)

Q["02"] = ("02_eda_numeric_profile.sql", BASE_CTE + """
, m AS (
  SELECT 'price' AS metric, price AS v FROM base
  UNION ALL SELECT 'area', area FROM base
  UNION ALL SELECT 'pps', pps FROM base
  UNION ALL SELECT 'age', CAST(age AS FLOAT64) FROM base
  UNION ALL SELECT 'walk', CAST(walk AS FLOAT64) FROM base
)
SELECT metric, COUNT(v) AS n_valid,
  ROUND(MIN(v), 1) AS min_v,
  ROUND(APPROX_QUANTILES(v, 100)[OFFSET(1)], 1) AS p01,
  ROUND(APPROX_QUANTILES(v, 100)[OFFSET(25)], 1) AS p25,
  ROUND(APPROX_QUANTILES(v, 100)[OFFSET(50)], 1) AS p50,
  ROUND(APPROX_QUANTILES(v, 100)[OFFSET(75)], 1) AS p75,
  ROUND(APPROX_QUANTILES(v, 100)[OFFSET(99)], 1) AS p99,
  ROUND(MAX(v), 1) AS max_v
FROM m GROUP BY metric ORDER BY metric""")

Q["03"] = ("03_eda_histogram.sql", BASE_CTE + """
SELECT 'pps_10man' AS metric, CAST(FLOOR(LEAST(pps, 3000000) / 100000) AS INT64) AS bin_v, COUNT(*) AS cnt
FROM base WHERE pps IS NOT NULL GROUP BY 2
UNION ALL
SELECT 'price_500man', CAST(FLOOR(LEAST(price, 200000000) / 5000000) AS INT64), COUNT(*)
FROM base WHERE price IS NOT NULL GROUP BY 2
UNION ALL
SELECT 'area_5sqm', CAST(FLOOR(LEAST(area, 200) / 5) * 5 AS INT64), COUNT(*)
FROM base WHERE area IS NOT NULL GROUP BY 2
UNION ALL
SELECT 'age_5y', CAST(FLOOR(LEAST(age, 80) / 5) * 5 AS INT64), COUNT(*)
FROM base WHERE age IS NOT NULL AND age >= 0 GROUP BY 2
UNION ALL
SELECT 'walk_1min', CAST(LEAST(walk, 40) AS INT64), COUNT(*)
FROM base WHERE walk IS NOT NULL GROUP BY 2
ORDER BY metric, bin_v""")

Q["04"] = ("04_eda_iqr_outliers.sql", BASE_CTE + """
, banded AS (
  SELECT pps,
    CASE WHEN age IS NULL THEN '不明'
         WHEN age <= 10 THEN '築0-10年' WHEN age <= 20 THEN '築11-20年'
         WHEN age <= 30 THEN '築21-30年' WHEN age <= 40 THEN '築31-40年'
         ELSE '築41年以上' END AS band
  FROM base WHERE pps IS NOT NULL
),
stats AS (
  SELECT band,
    APPROX_QUANTILES(pps, 4)[OFFSET(1)] AS q1,
    APPROX_QUANTILES(pps, 4)[OFFSET(2)] AS q2,
    APPROX_QUANTILES(pps, 4)[OFFSET(3)] AS q3,
    COUNT(*) AS n
  FROM banded GROUP BY band
)
SELECT s.band, s.n, ROUND(s.q1) AS q1, ROUND(s.q2) AS med, ROUND(s.q3) AS q3,
  ROUND(s.q3 - s.q1) AS iqr,
  ROUND(s.q1 - 1.5 * (s.q3 - s.q1)) AS lower_fence,
  ROUND(s.q3 + 1.5 * (s.q3 - s.q1)) AS upper_fence,
  COUNTIF(b.pps < s.q1 - 1.5 * (s.q3 - s.q1)) AS n_below,
  COUNTIF(b.pps > s.q3 + 1.5 * (s.q3 - s.q1)) AS n_above
FROM stats s JOIN banded b ON b.band = s.band
GROUP BY s.band, s.n, s.q1, s.q2, s.q3 ORDER BY s.band""")

Q["05"] = ("05_eda_station_join.sql", """WITH tx AS (
  SELECT nearest_station_name AS nm, COUNT(*) AS c
  FROM `osaka_real_estate.raw_transactions`
  WHERE nearest_station_name != '' AND STARTS_WITH(city_name, '大阪市') GROUP BY 1
),
norm AS (
  SELECT nm, c,
    REGEXP_REPLACE(REGEXP_REPLACE(nm, r'\\([^)]*\\)|（[^）]*）', ''), r'駅$', '') AS nm_norm
  FROM tx
),
st AS (SELECT DISTINCT n02_005 AS s FROM `osaka_real_estate.raw_station_master_2025`)
SELECT 'A_summary' AS section,
  CAST(COUNTIF(s1.s IS NOT NULL) AS STRING) AS names_matched_raw,
  CAST(COUNTIF(s2.s IS NOT NULL) AS STRING) AS names_matched_norm,
  CAST(COUNT(*) AS STRING) AS names_total,
  CAST(SUM(IF(s2.s IS NOT NULL, n.c, 0)) AS STRING) AS rows_matched_norm,
  CAST(SUM(n.c) AS STRING) AS rows_total
FROM norm n
LEFT JOIN st s1 ON n.nm = s1.s
LEFT JOIN st s2 ON n.nm_norm = s2.s
UNION ALL
SELECT 'B_unmatched_top', n.nm, n.nm_norm, CAST(n.c AS STRING), '', ''
FROM norm n LEFT JOIN st s2 ON n.nm_norm = s2.s
WHERE s2.s IS NULL
ORDER BY section, CAST(names_total AS INT64) DESC
LIMIT 30""")

Q["06"] = ("06_eda_station_stats.sql", BASE_CTE + """
SELECT st_name, COUNT(*) AS cnt,
  ROUND(APPROX_QUANTILES(pps, 100)[OFFSET(50)]) AS median_pps
FROM base WHERE st_name != '' AND pps IS NOT NULL
GROUP BY st_name ORDER BY cnt DESC""")

Q["07"] = ("07_eda_period_counts.sql", """SELECT
  SUBSTR(trade_period, 1, 4) AS yr,
  REGEXP_EXTRACT(trade_period, r'第([1-4])') AS qtr,
  COUNT(*) AS cnt
FROM `osaka_real_estate.raw_transactions`
WHERE STARTS_WITH(city_name, '大阪市')
GROUP BY 1, 2 ORDER BY 1, 2""")

Q["08"] = ("08_eda_missing_special.sql", """WITH t AS (
  SELECT * FROM `osaka_real_estate.raw_transactions` WHERE STARTS_WITH(city_name, '大阪市'))
SELECT 'empty' AS section, 'nearest_station_name' AS item, CAST(COUNTIF(nearest_station_name = '') AS INT64) AS cnt FROM t
UNION ALL SELECT 'empty', 'nearest_station_distance_min', COUNTIF(nearest_station_distance_min = '') FROM t
UNION ALL SELECT 'empty', 'built_year', COUNTIF(built_year = '') FROM t
UNION ALL SELECT 'empty', 'renovation', COUNTIF(renovation = '') FROM t
UNION ALL SELECT 'empty', 'layout', COUNTIF(layout = '') FROM t
UNION ALL SELECT 'empty', 'use_type', COUNTIF(use_type = '') FROM t
UNION ALL SELECT 'empty', 'city_planning', COUNTIF(city_planning = '') FROM t
UNION ALL SELECT 'walk_range', nearest_station_distance_min, COUNT(*) FROM t
  WHERE nearest_station_distance_min != '' AND SAFE_CAST(nearest_station_distance_min AS INT64) IS NULL
  GROUP BY 2
UNION ALL SELECT 'built_special', built_year, COUNT(*) FROM t
  WHERE built_year != '' AND NOT REGEXP_CONTAINS(built_year, r'^[0-9]{4}年$') GROUP BY 2
UNION ALL SELECT 'renovation_value', renovation, COUNT(*) FROM t WHERE renovation != '' GROUP BY 2
UNION ALL
SELECT 'dup_rows', 'excess_total', SUM(c - 1) FROM (
  SELECT COUNT(*) AS c FROM t
  GROUP BY kind, price_category, city_code, prefecture_name, city_name, district_name,
    nearest_station_name, nearest_station_distance_min, trade_price_total, layout, area_sqm,
    built_year, building_structure, use_type, future_use_purpose, city_planning,
    building_coverage_ratio, floor_area_ratio, trade_period, renovation, trade_circumstances
  HAVING c > 1)
ORDER BY section, cnt DESC""")

Q["09"] = ("09_eda_outlier_examples.sql", BASE_CTE + """
SELECT * FROM (
  SELECT 'price_top5' AS section, city_name, district_name, st_name, walk,
    area, ROUND(price / 10000) AS price_man, ROUND(pps / 10000, 1) AS pps_man,
    built_year, layout, trade_period
  FROM base WHERE price IS NOT NULL ORDER BY price DESC LIMIT 5)
UNION ALL
SELECT * FROM (
  SELECT 'pps_top5', city_name, district_name, st_name, walk, area,
    ROUND(price / 10000), ROUND(pps / 10000, 1), built_year, layout, trade_period
  FROM base WHERE pps IS NOT NULL ORDER BY pps DESC LIMIT 5)
UNION ALL
SELECT * FROM (
  SELECT 'pps_bottom5', city_name, district_name, st_name, walk, area,
    ROUND(price / 10000), ROUND(pps / 10000, 1), built_year, layout, trade_period
  FROM base WHERE pps IS NOT NULL ORDER BY pps ASC LIMIT 5)
ORDER BY section, pps_man DESC""")

Q["10"] = ("10_eda_scope_preview.sql", BASE_ALL + """
, scoped AS (
  SELECT *, STARTS_WITH(city_name, '大阪市') AS in_osaka_city,
    (area BETWEEN 20 AND 55) AS ok_area, (walk <= 20) AS ok_walk,
    (age BETWEEN 5 AND 50) AS ok_age,
    (price BETWEEN 5000000 AND 80000000) AS ok_price
  FROM base
)
SELECT 'A_funnel' AS section, '0_全件(大阪府)' AS step, CAST(COUNT(*) AS INT64) AS cnt FROM scoped
UNION ALL SELECT 'A_funnel', '1_大阪市内', COUNTIF(in_osaka_city) FROM scoped
UNION ALL SELECT 'A_funnel', '2_+面積20-55', COUNTIF(in_osaka_city AND ok_area) FROM scoped
UNION ALL SELECT 'A_funnel', '3_+徒歩20分以内', COUNTIF(in_osaka_city AND ok_area AND ok_walk) FROM scoped
UNION ALL SELECT 'A_funnel', '4_+築5-50年', COUNTIF(in_osaka_city AND ok_area AND ok_walk AND ok_age) FROM scoped
UNION ALL SELECT 'A_funnel', '5_+価格500-8000万', COUNTIF(in_osaka_city AND ok_area AND ok_walk AND ok_age AND ok_price) FROM scoped
UNION ALL
SELECT 'B_station', '駅数(条件後10件以上)', COUNT(*) FROM (
  SELECT st_name FROM scoped
  WHERE in_osaka_city AND ok_area AND ok_walk AND ok_age AND ok_price AND st_name != ''
  GROUP BY st_name HAVING COUNT(*) >= 10)
UNION ALL
SELECT 'B_station', '駅数(条件後1件以上)', COUNT(*) FROM (
  SELECT st_name FROM scoped
  WHERE in_osaka_city AND ok_area AND ok_walk AND ok_age AND ok_price AND st_name != ''
  GROUP BY st_name)
ORDER BY section, step""")


def run_query(sql):
    flat = " ".join(l for l in sql.splitlines() if not l.strip().startswith("--"))
    flat = " ".join(flat.split())
    env = dict(os.environ, PYTHONUTF8="1")
    r = subprocess.run(
        ["bq", f"--project_id={PROJECT}", "query", "--use_legacy_sql=false",
         "--format=csv", "--max_rows=10000", flat],
        capture_output=True, text=True, encoding="utf-8", env=env, shell=True)
    if r.returncode != 0:
        raise RuntimeError(r.stderr[:500])
    return list(csv.reader(io.StringIO(r.stdout)))


def main():
    results = {}
    for qid, (fname, sql) in sorted(Q.items()):
        with open(os.path.join(SQL_DIR, fname), "w", encoding="utf-8", newline="\n") as f:
            f.write(f"-- {fname}\n-- 生成元: scripts/run_eda.py（編集はスクリプト側で行うこと）\n"
                    f"-- 読み取り専用 / 入力: raw_* / {SNAPSHOT}\n" + sql.strip() + "\n")
        rows = run_query(sql)
        results[qid] = rows
        out = os.path.join(TBL_DIR, fname.replace(".sql", ".csv"))
        with open(out, "w", encoding="utf-8-sig", newline="") as f:
            csv.writer(f).writerows(rows)
        print(f"{qid}: {fname} -> {len(rows)-1} rows")
    charts(results)
    report(results)
    print("DONE")


def caption(ax, qid):
    # 図の最下部余白に描画（軸ラベルと重ならないよう、tight_layout の rect で余白を確保）
    ax.figure.text(0.995, 0.006, f"source: sql/checks/{Q[qid][0]} | raw_transactions | {TODAY}",
                   ha="right", va="bottom", fontsize=7, color="gray")


def charts(res):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams["font.family"] = "Meiryo"

    prof = {r[0]: r for r in res["02"][1:]}  # metric -> row
    p99 = {m: float(prof[m][7]) for m in prof}
    hist = {}
    for m, b, c in res["03"][1:]:
        hist.setdefault(m, []).append((int(b), int(c)))

    def bar(qid, key, xs, ys, title, fname, xlabel, vline=None, vlabel=""):
        fig, ax = plt.subplots(figsize=(9, 4.5))
        ax.bar(xs, ys, width=(xs[1] - xs[0]) * 0.9 if len(xs) > 1 else 0.9,
               color="#4C78A8", align="edge")
        if vline is not None:
            ax.axvline(vline, color="crimson", ls="--", lw=1.2)
            ax.text(vline, max(ys) * 0.92, f" {vlabel}", color="crimson", fontsize=9)
        ax.set_title(title, fontsize=11)
        ax.set_xlabel(xlabel)
        ax.set_ylabel("件数")
        caption(ax, qid)
        fig.tight_layout(rect=(0, 0.035, 1, 1))
        fig.savefig(os.path.join(FIG_DIR, fname), dpi=120)
        plt.close(fig)

    # ㎡単価
    d = sorted(hist["pps_10man"])
    n_over = sum(c for b, c in d if b * 100000 >= p99["pps"])
    bar("03", "pps", [b * 10 for b, c in d], [c for b, c in d],
        f"㎡単価(大阪市): P99={p99['pps']/1e4:.0f}万円/m2 超は約{n_over}件 = 要確認フラグ候補 (D-002)",
        "03_hist_pps.png", "㎡単価（万円/m2）※300万で打ち切り",
        vline=p99["pps"] / 1e4, vlabel=f"P99 {p99['pps']/1e4:.0f}万")
    # 価格
    d = sorted(hist["price_500man"])
    bar("03", "price", [b * 500 for b, c in d], [c for b, c in d],
        f"価格(大阪市): P99={p99['price']/1e4:,.0f}万円 / 最大{float(prof['price'][8])/1e8:.1f}億円 (D-002)",
        "03_hist_price.png", "価格（万円）※2億で打ち切り",
        vline=p99["price"] / 1e4, vlabel=f"P99 {p99['price']/1e4:,.0f}万")
    # 面積
    d = sorted(hist["area_5sqm"])
    n100 = sum(c for b, c in d if b >= 100)
    bar("03", "area", [b for b, c in d], [c for b, c in d],
        f"面積(大阪市): 100m2以上は{n100}件 = 分析対象外候補 (D-003)",
        "03_hist_area.png", "面積（m2）※200で打ち切り", vline=100, vlabel="100m2")
    # 築年数
    d = sorted(hist["age_5y"])
    n50 = sum(c for b, c in d if b >= 50)
    bar("03", "age", [b for b, c in d], [c for b, c in d],
        f"築年数(大阪市): 50年以上は{n50}件 / 「戦前」表記は別途 (D-004)",
        "03_hist_age.png", "築年数（年）※80で打ち切り", vline=50, vlabel="50年")
    # 徒歩分
    d = sorted(hist["walk_1min"])
    n20 = sum(c for b, c in d if b > 20)
    bar("03", "walk", [b for b, c in d], [c for b, c in d],
        f"徒歩分(大阪市): 20分超は{n20}件 / 範囲表記は数値化対象外 (D-001)",
        "03_hist_walk.png", "徒歩分（分）※40で打ち切り", vline=20, vlabel="20分")

    # 04 箱ひげ（築年帯別）
    fig, ax = plt.subplots(figsize=(9, 4.5))
    rows = [r for r in res["04"][1:] if r[0] != "不明"]
    boxes = [dict(label=f"{r[0]}\n(n={int(r[1]):,})", med=float(r[3]) / 1e4,
                  q1=float(r[2]) / 1e4, q3=float(r[4]) / 1e4,
                  whislo=max(0.0, float(r[6])) / 1e4, whishi=float(r[7]) / 1e4,
                  fliers=[]) for r in rows]
    n_out = sum(int(r[8]) + int(r[9]) for r in rows)
    ax.bxp(boxes, showfliers=False)
    ax.set_title(f"築年帯別㎡単価のIQR(大阪市): フェンス外は計{n_out:,}件 = 即除外せず要確認 (D-002)", fontsize=11)
    ax.set_ylabel("㎡単価（万円/m2）")
    caption(ax, "04")
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(os.path.join(FIG_DIR, "04_box_pps_by_age.png"), dpi=120)
    plt.close(fig)

    # 06 駅別サンプル数 top20
    st = [(r[0], int(r[1])) for r in res["06"][1:]]
    n_ge10 = sum(1 for _, c in st if c >= 10)
    top = st[:20][::-1]
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh([s for s, _ in top], [c for _, c in top], color="#4C78A8")
    ax.set_title(f"駅別サンプル数Top20(大阪市): 10件以上は{n_ge10}駅（全{len(st)}駅）= ランキング対象の母数", fontsize=11)
    ax.set_xlabel("取引件数（2021-2025・大阪市・駅名未正規化）")
    caption(ax, "06")
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(os.path.join(FIG_DIR, "06_station_top20.png"), dpi=120)
    plt.close(fig)

    # 07 期間別件数
    pr = [(f"{r[0]}Q{r[1]}", int(r[2])) for r in res["07"][1:]]
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar([p for p, _ in pr], [c for _, c in pr], color="#4C78A8")
    ax.set_title("年・四半期別件数(大阪市): 期間の欠落有無と件数トレンドの確認", fontsize=11)
    ax.set_ylabel("件数")
    plt.setp(ax.get_xticklabels(), rotation=60, ha="right", fontsize=8)
    caption(ax, "07")
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(os.path.join(FIG_DIR, "07_period_counts.png"), dpi=120)
    plt.close(fig)

    # 08 欠損率（対象スコープの総行数は 07 の期間別件数から動的に算出）
    total = sum(int(r[2]) for r in res["07"][1:])
    em = [(r[1], int(r[2])) for r in res["08"][1:] if r[0] == "empty"]
    em.sort(key=lambda x: x[1])
    rate = {k: c / total * 100 for k, c in em}
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.barh([i for i, _ in em], [c / total * 100 for _, c in em], color="#E45756")
    ax.set_title(
        f"空欄率(大阪市): 改装{rate.get('renovation', 0):.1f}%・"
        f"徒歩分{rate.get('nearest_station_distance_min', 0):.1f}%・"
        f"建築年{rate.get('built_year', 0):.1f}% = 補完/フラグ設計の対象 (D-004, D-007)", fontsize=11)
    ax.set_xlabel("空欄率（%）")
    caption(ax, "08")
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    fig.savefig(os.path.join(FIG_DIR, "08_missing_rates.png"), dpi=120)
    plt.close(fig)
    print("charts: 9 PNGs saved")


def md_table(rows, limit=None):
    if not rows:
        return "(no rows)"
    head, body = rows[0], rows[1:limit + 1 if limit else None]
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(r) + " |" for r in body]
    return "\n".join(out)


def report(res):
    def sql_details(qid):
        return (f"<details><summary>実行SQL（sql/checks/{Q[qid][0]}）</summary>\n\n"
                f"```sql\n{Q[qid][1].strip()}\n```\n</details>")

    prof = {r[0]: r for r in res["02"][1:]}
    summary = res["10"][1:]
    funnel = {r[1]: int(r[2]) for r in summary if r[0] == "A_funnel"}
    stn = {r[1]: int(r[2]) for r in summary if r[0] == "B_station"}

    parts = [f"""# EDA レポート (Step 5)

**{SNAPSHOT}**
レポート生成: {TODAY} / 生成スクリプト: scripts/run_eda.py（全SQL・全グラフはこのスクリプトから再現可能）
注意: 成約価格情報は遡及改訂されるため、再取得時は件数が変わる可能性がある。

## 決定事項サマリー（すべて提案中 = Step 6/7 で承認を得て確定）

| ID | 提案 | 件数影響 | ステータス |
|---|---|---|---|
| D-001 | 徒歩分の範囲表記は下限値を採用して数値化（30分-60分=30） | 47件 | 提案中 |
| D-002 | ㎡単価・価格のP99超は即除外せず「要確認フラグ」で保持 | 約1%（-500件） | 提案中 |
| D-003 | 面積100m2超は分析対象外（scope_flag=FALSE, 単身-DINKS市場に集中） | 下記3章 | 提案中 |
| D-004 | 建築年「戦前」は1945年扱い + is_prewar フラグ（旧耐震確定） | 下記8章 | 提案中 |
| D-005 | 完全重複行は1件に集約し dup_count を保持 | 330行 | 提案中 |
| D-006 | 駅名は正規化（括弧・「駅」除去）+ mapping CSV で結合率改善 | 下記5章 | 提案中 |
| D-007 | 改装空欄は renovation_unknown_flag=1（未改装と断定しない） | 空欄全件（約95%） | 提案中 |
| D-008 | 築年数マイナス（建築年>取引年）は is_negative_age フラグ + scope除外候補 | 少数 | 提案中 |
| D-009 | 分位点系の閾値は訓練期間（2021-2024）のみで算出しテスト期間へ適用（リーク防止） | - | 提案中 |
| D-010 | 分布・外れ値のEDAは分析対象スコープ（大阪市）で実施 = 本レポート。形式チェックは府全体で実施済み | - | 採用済み |

---

## 02. 数値プロファイル（min/P01/P25/中央値/P75/P99/max）

{md_table(res["02"])}

**所見**: 価格は中央値{float(prof['price'][5])/1e4:,.0f}万円に対し最大{float(prof['price'][8])/1e8:.1f}億円、
㎡単価はP99={float(prof['pps'][7])/1e4:.0f}万円/m2。P01-P99の外側（両側約2%）が外れ値候補 = D-002。

{sql_details("02")}

## 03. 分布（ヒストグラム）

![㎡単価](../outputs/figures/03_hist_pps.png)
![価格](../outputs/figures/03_hist_price.png)
![面積](../outputs/figures/03_hist_area.png)
![築年数](../outputs/figures/03_hist_age.png)
![徒歩分](../outputs/figures/03_hist_walk.png)

{sql_details("03")}

## 04. 築年帯別IQR（箱ひげ）

![築年帯別](../outputs/figures/04_box_pps_by_age.png)

{md_table(res["04"])}

**所見**: 築年帯ごとにフェンスを引くことで「築古だから安い」を外れ値と誤判定しない（手順書No.7）。
フェンス外は D-002 の要確認フラグ対象。

{sql_details("04")}

## 05. 駅名結合率（raw駅名 × N02-2025駅マスタ）

{md_table(res["05"], limit=25)}

**所見**: A_summary行 = [生駅名の一致数, 正規化後の一致数, 駅名総数, 正規化後一致行数, 駅名あり行総数]。
B_unmatched_top = 正規化しても一致しない駅名（mapping CSV の対象 = D-006）。

{sql_details("05")}

## 06. 駅別サンプル数

![駅別Top20](../outputs/figures/06_station_top20.png)

**所見**: 10件以上の駅がランキング対象の母数（手順書の最低ライン）。詳細は outputs/tables/06_eda_station_stats.csv。

{sql_details("06")}

## 07. 年・四半期別件数

![期間別](../outputs/figures/07_period_counts.png)

{sql_details("07")}

## 08. 欠損・特殊値・重複

![空欄率](../outputs/figures/08_missing_rates.png)

{md_table(res["08"], limit=30)}

**所見**: 徒歩分の範囲表記（D-001）、「戦前」（D-004）、完全重複（D-005）、改装空欄（D-007）の根拠データ。

{sql_details("08")}

## 09. 外れ値の現物確認（統計値でなく実データで判断）

{md_table(res["09"])}

**所見**: price_top5 が立地・面積で説明できる実在の高級物件なら入力ミスではなく「分析対象外」に分類（D-003）。
pps_bottom5 は事故物件・特殊事情の可能性 = 要確認フラグ。

{sql_details("09")}

## 10. Step 6 への試算（手順書の推奨初期条件を適用した場合）

| 絞り込みステップ | 残件数 |
|---|---|
""" + "\n".join(f"| {k} | {v:,} |" for k, v in sorted(funnel.items())) + f"""

- 条件後の駅数: {stn.get('駅数(条件後1件以上)', 0)}駅 / うち10件以上: **{stn.get('駅数(条件後10件以上)', 0)}駅**

**所見**: 手順書の初期条件（大阪市24区・20-55m2・徒歩20分・築5-50年・500-8000万円）での残件数。
駅別10件以上が確保できているかを Step 6 の判断材料とする。

{sql_details("10")}
"""]
    with open(DOC, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(parts))
    print(f"report: {DOC}")


if __name__ == "__main__":
    main()
