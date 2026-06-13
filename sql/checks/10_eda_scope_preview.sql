-- 10_eda_scope_preview.sql
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
)
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
ORDER BY section, step
