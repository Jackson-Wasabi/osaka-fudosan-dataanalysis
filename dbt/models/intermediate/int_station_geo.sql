-- int_station_geo: 駅名ごとの代表座標・代表路線（粒度: 駅）
-- 入力: stg_station_master（全国の駅）
-- 目的: 駅名だけで結合すると「本町」等の全国同名駅の座標まで平均され代表点が大阪から
--   ずれる問題を防ぐため、大阪府周辺のバウンディングボックスに限定してから集約する。
--   地価最近傍結合（int_station_land_price_features）と物件結合（地図表示用座標）の
--   両方がこの1テーブルを参照する（座標ロジックの一元化）。
-- 大阪府の範囲: 概ね lat 34.2-35.1 / lon 135.0-135.8（decision_log のGIS座標域に基づく）

SELECT
    station_name,
    ANY_VALUE(line_name) AS line_name,
    AVG(lon) AS station_lon,
    AVG(lat) AS station_lat
FROM {{ ref('stg_station_master') }}
WHERE station_name IS NOT NULL AND station_name != ''
  AND lat BETWEEN 34.2 AND 35.1
  AND lon BETWEEN 135.0 AND 135.8
GROUP BY station_name
