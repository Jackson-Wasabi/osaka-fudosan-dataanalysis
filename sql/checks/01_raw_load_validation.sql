-- raw_transactions: 列と値の対応検証（カラムシフト検出）
-- 読み取り専用のSELECTのみ。データの変更は行わない。
-- 各列が期待する値域・形式に合致しない行数を数える。全列0なら位置ズレなし。
SELECT
  COUNT(*)                                                                  AS total_rows,
  COUNTIF(kind != '中古マンション等')                                       AS bad_kind,
  COUNTIF(price_category != '成約価格情報')                                 AS bad_price_category,
  COUNTIF(NOT REGEXP_CONTAINS(city_code, r'^27[0-9]{3}$'))                  AS bad_city_code,
  COUNTIF(prefecture_name != '大阪府')                                      AS bad_prefecture,
  COUNTIF(city_name != '' AND NOT STARTS_WITH(city_name, '大阪')
          AND NOT REGEXP_CONTAINS(city_name, r'(市|町|村|区)'))             AS bad_city_name,
  COUNTIF(nearest_station_distance_min != ''
          AND SAFE_CAST(nearest_station_distance_min AS INT64) IS NULL
          AND NOT REGEXP_CONTAINS(nearest_station_distance_min, r'分|H'))   AS bad_walk,
  COUNTIF(trade_price_total = ''
          OR SAFE_CAST(trade_price_total AS INT64) IS NULL)                 AS bad_price,
  COUNTIF(area_sqm = '' OR SAFE_CAST(area_sqm AS FLOAT64) IS NULL)          AS bad_area,
  COUNTIF(built_year != ''
          AND NOT REGEXP_CONTAINS(built_year, r'^[0-9]{4}年$')
          AND built_year != '戦前')                                         AS bad_built_year,
  COUNTIF(building_structure != ''
          AND NOT REGEXP_CONTAINS(building_structure,
              r'(ＲＣ|ＳＲＣ|鉄骨造|木造|ブロック造|軽量鉄骨造)'))          AS bad_structure,
  COUNTIF(NOT REGEXP_CONTAINS(trade_period, r'^202[1-5]年第[1-4]四半期$'))  AS bad_trade_period,
  -- 実データの値域: '改装済み' と空欄のみ（'未改装' は存在しない。2026-06-12確認）
  COUNTIF(renovation NOT IN ('', '改装済み'))                               AS bad_renovation
FROM `osaka_real_estate.raw_transactions`;
