-- 05_eda_station_join.sql
-- 生成元: scripts/run_eda.py（編集はスクリプト側で行うこと）
-- 読み取り専用 / 入力: raw_* / データ取得日: 2026-06-12 / 対象スコープ: 大阪市・中古マンション等・成約価格情報 2021Q1-2025Q4（24,613行）。raw全体は大阪府47,386行で、形式チェックは府全体で実施済み（D-010）
WITH tx AS (
  SELECT nearest_station_name AS nm, COUNT(*) AS c
  FROM `osaka_real_estate.raw_transactions`
  WHERE nearest_station_name != '' AND STARTS_WITH(city_name, '大阪市') GROUP BY 1
),
norm AS (
  SELECT nm, c,
    REGEXP_REPLACE(REGEXP_REPLACE(nm, r'\([^)]*\)|（[^）]*）', ''), r'駅$', '') AS nm_norm
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
LIMIT 30
