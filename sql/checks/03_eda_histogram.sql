-- 03_eda_histogram.sql
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
SELECT 'pps_10man' AS metric, CAST(FLOOR(LEAST(pps, 3000000) / 100000) AS INT64) AS bin_v, COUNT(*) AS cnt
FROM base WHERE pps IS NOT NULL GROUP BY 2
UNION ALL
SELECT 'price_500man', CAST(FLOOR(LEAST(price, 200000000) / 5000000) AS INT64), COUNT(*)
FROM base WHERE price IS NOT NULL GROUP BY 2
UNION ALL
SELECT 'area_5sqm', CAST(FLOOR(LEAST(area, 200) / 5) * 5 AS INT64), COUNT(*)
FROM base WHERE area IS NOT NULL GROUP BY 2
UNION ALL
SELECT 'age_5y', CAST(FLOOR(LEAST(age, 70) / 5) * 5 AS INT64), COUNT(*)
FROM base WHERE age IS NOT NULL AND age >= 0 GROUP BY 2
UNION ALL
SELECT 'walk_1min', CAST(LEAST(walk, 40) AS INT64), COUNT(*)
FROM base WHERE walk IS NOT NULL GROUP BY 2
ORDER BY metric, bin_v
