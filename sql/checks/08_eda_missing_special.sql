-- 08_eda_missing_special.sql
-- 生成元: scripts/run_eda.py（編集はスクリプト側で行うこと）
-- 読み取り専用 / 入力: raw_* / データ取得日: 2026-06-12 / 対象スコープ: 大阪市・中古マンション等・成約価格情報 2021Q1-2025Q4（24,613行）。raw全体は大阪府47,386行で、形式チェックは府全体で実施済み（D-010）
WITH t AS (
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
ORDER BY section, cnt DESC
