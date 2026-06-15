-- int_transactions_with_station_features: 物件 × 駅特徴量 × 地価特徴量（粒度: 物件 × Fold）
-- 入力: stg_transactions(scope) + int_station_market_features + int_station_land_price_features + int_station_geo
-- mart_condo_price / BQML の元になる行レベルテーブル。
-- D-009: 各物件を Fold A/B に展開し、その Fold の訓練由来の駅市場特徴量を結合（リークなし）。
--   Fold A: 2021-2024=train / 2025=test　　Fold B: 2021-2023=train / 2024=test（2025は対象外）
-- D-018: 徒歩分・築年数の欠損を「その Fold の訓練期間の中央値」で補完（リーク防止）。
--   補完中央値は PERCENTILE_CONT(IF(split='train', 値, NULL)) で訓練行のみから算出。
--   築年数: 駅→区→全体 / 徒歩分: 駅→区 / 公示価格: 実計算で基本欠損なし、無い時のみ区中央値。

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
),

joined AS (
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
),

-- 補完用の中央値（その Fold の訓練期間=split='train' の行のみから算出。リーク防止）
medians AS (
    SELECT
        *,
        -- 築年数: 駅 → 区 → 全体
        PERCENTILE_CONT(IF(split = 'train', building_age_years, NULL), 0.5)
            OVER (PARTITION BY fold, station_name) AS age_med_station,
        PERCENTILE_CONT(IF(split = 'train', building_age_years, NULL), 0.5)
            OVER (PARTITION BY fold, city_name)    AS age_med_ward,
        PERCENTILE_CONT(IF(split = 'train', building_age_years, NULL), 0.5)
            OVER (PARTITION BY fold)               AS age_med_all,
        -- 徒歩分: 駅 → 区
        PERCENTILE_CONT(IF(split = 'train', walk_minutes, NULL), 0.5)
            OVER (PARTITION BY fold, station_name) AS walk_med_station,
        PERCENTILE_CONT(IF(split = 'train', walk_minutes, NULL), 0.5)
            OVER (PARTITION BY fold, city_name)    AS walk_med_ward,
        -- 公示価格: 区中央値（座標が無く実計算できない駅のフォールバック用）
        PERCENTILE_CONT(IF(split = 'train', nearest_land_price, NULL), 0.5)
            OVER (PARTITION BY fold, city_name)    AS land_med_ward
    FROM joined
)

SELECT
    * EXCEPT (age_med_station, age_med_ward, age_med_all, walk_med_station, walk_med_ward, land_med_ward),

    -- 築年数の補完（D-018）
    (building_age_years IS NULL) AS is_imputed_building_age,
    COALESCE(building_age_years, age_med_station, age_med_ward, age_med_all)
        AS imputed_building_age,

    -- 徒歩分の補完（D-018）
    (walk_minutes IS NULL) AS is_imputed_walk_minutes,
    COALESCE(walk_minutes, walk_med_station, walk_med_ward)
        AS imputed_walk_minutes,

    -- 公示価格の補完（基本は実計算で非NULL。無い時のみ区中央値）
    (nearest_land_price IS NULL) AS is_imputed_land_price,
    COALESCE(nearest_land_price, land_med_ward)
        AS imputed_nearest_land_price,

    -- 耐震区分（補完後の築年数から算出。new と old は相補的で「どちらでもない」状態は生じない・D-020）
    -- 取引年 - 補完後築年数 = 推定建築年。>=1982 を新耐震、<1982 を旧耐震とする。
    CASE
        WHEN (trade_year - COALESCE(building_age_years, age_med_station, age_med_ward, age_med_all)) >= 1982
        THEN 1 ELSE 0
    END AS seismic_new,
    CASE
        WHEN (trade_year - COALESCE(building_age_years, age_med_station, age_med_ward, age_med_all)) < 1982
        THEN 1 ELSE 0
    END AS seismic_old_flag
    -- 旧耐震判定が補完(推定)由来かは is_imputed_building_age で区別できる（リスク評価で過信を避ける）

FROM medians
