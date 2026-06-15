-- int_station_land_price_features: 駅別の地価特徴量（粒度: 駅）
-- 入力: stg_station_master（駅代表点）× stg_land_price（大阪市 公示価格 574地点）
-- 各駅に最も近い公示地点を ST_DISTANCE で最近傍結合する。公示価格は単年(2025)のためFold依存なし。
-- 分析対象（取引のある大阪市の駅）に限定する。N02は全国の駅を含むため、限定しないと
-- 大阪市外の駅に対し遠方の公示地点が最近傍となり距離が無意味になるため。
-- 注意: 地価特徴量は予測モデルに入れず、地価・エリア補足スコアで使う（CLAUDE.md / PART 14-3）。

WITH analyzed_stations AS (
    -- int_station_market_features に出る駅 = 大阪市スコープ内に取引がある駅
    SELECT DISTINCT station_name
    FROM {{ ref('int_station_market_features') }}
),

stations AS (
    -- 大阪府周辺に限定済みの代表座標（int_station_geo）を分析対象駅に絞る
    SELECT
        g.station_name,
        g.station_lon AS lon,
        g.station_lat AS lat
    FROM {{ ref('int_station_geo') }} g
    JOIN analyzed_stations a USING (station_name)
),

land AS (
    SELECT
        land_price_per_sqm,
        yoy_change_pct,
        lon,
        lat
    FROM {{ ref('stg_land_price') }}
    WHERE lon IS NOT NULL AND lat IS NOT NULL
      AND land_price_per_sqm IS NOT NULL
),

paired AS (
    SELECT
        s.station_name,
        l.land_price_per_sqm,
        l.yoy_change_pct,
        ST_DISTANCE(ST_GEOGPOINT(s.lon, s.lat), ST_GEOGPOINT(l.lon, l.lat)) AS dist_m,
        ROW_NUMBER() OVER (
            PARTITION BY s.station_name
            ORDER BY ST_DISTANCE(ST_GEOGPOINT(s.lon, s.lat), ST_GEOGPOINT(l.lon, l.lat))
        ) AS rn
    FROM stations s
    CROSS JOIN land l
)

SELECT
    station_name,
    land_price_per_sqm AS nearest_land_price,
    yoy_change_pct     AS land_price_change_rate,
    dist_m             AS land_price_distance_m
FROM paired
WHERE rn = 1
