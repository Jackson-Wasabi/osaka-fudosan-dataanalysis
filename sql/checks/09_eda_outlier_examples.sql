-- 09_eda_outlier_examples.sql
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
ORDER BY section, pps_man DESC
