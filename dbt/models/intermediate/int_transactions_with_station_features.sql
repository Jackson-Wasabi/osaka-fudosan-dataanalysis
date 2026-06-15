-- int_transactions_with_station_features: 物件 × 駅特徴量 × 地価特徴量（粒度: 物件 × Fold）
-- 入力: stg_transactions(scope) + int_station_market_features + int_station_land_price_features + 駅マスタ代表点
-- mart_condo_price / BQML の元になる行レベルテーブル。
-- D-009: 各物件を Fold A/B に展開し、その Fold の訓練由来の駅市場特徴量を結合（リークなし）。
--   Fold A: 2021-2024=train / 2025=test
--   Fold B: 2021-2023=train / 2024=test（2025 は対象外）

WITH tx AS (
    SELECT * FROM {{ ref('stg_transactions') }}
    WHERE scope_flag = TRUE
),

-- 駅の代表座標・代表路線（大阪府周辺に限定済みの共通テーブル）
station_dim AS (
    SELECT station_name, line_name, station_lon, station_lat
    FROM {{ ref('int_station_geo') }}
),

-- 物件を Fold A/B に展開し split（train/test）を付与
tx_fold AS (
    SELECT *, 'A' AS fold, fold_a_split AS split
    FROM tx WHERE fold_a_split IS NOT NULL
    UNION ALL
    SELECT *, 'B' AS fold, fold_b_split AS split
    FROM tx WHERE fold_b_split IN ('train', 'test')
)

SELECT
    t.* EXCEPT (fold_a_split, fold_b_split),

    -- 駅マスタ結合の成否（データ品質スコア / リスク減点で使用）
    (sd.station_name IS NOT NULL) AS station_joined,
    sd.line_name,
    sd.station_lat,
    sd.station_lon,

    -- 駅市場特徴量（各 Fold 訓練由来）
    m.station_transaction_count,
    m.station_median_price_per_sqm,
    m.station_price_iqr,
    m.station_avg_walk_minutes,
    m.station_renovation_rate,

    -- 地価・エリア補足（予測モデルには入れない）
    l.nearest_land_price,
    l.land_price_change_rate,
    l.land_price_distance_m

FROM tx_fold t
LEFT JOIN station_dim sd
    ON t.station_name = sd.station_name
LEFT JOIN {{ ref('int_station_market_features') }} m
    ON t.station_name = m.station_name AND t.fold = m.fold
LEFT JOIN {{ ref('int_station_land_price_features') }} l
    ON t.station_name = l.station_name
