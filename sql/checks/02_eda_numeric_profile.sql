-- 02_eda_numeric_profile.sql
-- 生成元: scripts/run_eda.py（編集はスクリプト側で行うこと）
-- 読み取り専用 / 入力: raw_* / データ取得日: 2026-06-12 / 対象スコープ: 大阪市・中古マンション等・成約価格情報 2021Q1-2025Q4（24,613行）。raw全体は大阪府47,386行で、形式チェックは府全体で実施済み（D-010）
WITH base AS (
  SELECT
    SAFE_CAST(trade_price_total AS INT64) AS price,
    SAFE_CAST(area_sqm AS FLOAT64) AS area,
    SAFE_DIVIDE(SAFE_CAST(trade_price_total AS INT64), SAFE_CAST(area_sqm AS FLOAT64)) AS pps,
    SAFE_CAST(SUBSTR(trade_period, 1, 4) AS INT64)
      - SAFE_CAST(REGEXP_EXTRACT(built_year, r'^([0-9]{4})年$') AS INT64) AS age,
    SAFE_CAST(nearest_station_distance_min AS INT64) AS walk,
    nearest_station_name AS st_name,
    built_year, trade_period, city_name, district_name, layout, renovation
  FROM `osaka_real_estate.raw_transactions`
  WHERE STARTS_WITH(city_name, '大阪市')
)
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
FROM m GROUP BY metric ORDER BY metric
