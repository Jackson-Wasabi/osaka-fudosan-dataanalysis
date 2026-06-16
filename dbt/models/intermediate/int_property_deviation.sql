-- int_property_deviation: 物件ごとの「駅相対乖離」を二段の加法補正で算出（粒度: 物件・2025年）
-- 入力: source predictions_model_c（Model C の予測㎡単価・2025候補）
-- 方針（D-026）: 駅相対乖離 = 乖離率 −（市全体の面積帯中央値）−（駅内中央値）
--   - 乖離率 = 実勢㎡単価 / 予測㎡単価 − 1（マイナス＝予測より安い＝割安候補）
--   - 面積帯の系統差は「市全体」で補正（各帯数百件で安定）
--   - 立地差は「駅内」で補正（駅×面積帯は件数が薄すぎるため層別せず加法分離）
--   - 中央値は PERCENTILE_CONT の分析関数（GROUP不要・全行に同値を付与）
-- 補正後の駅相対乖離が負に大きいほど「その駅・その面積帯の相場に対して安い」。
-- 注意: 安い物件はデータに写らない瑕疵（逆選択）で安いことが多い（D-024/D-025）。額面で買い判断しない。

WITH base AS (
    SELECT
        *,
        -- 乖離率（マイナス＝予測より安い）
        SAFE_DIVIDE(actual_price_per_sqm, predicted_price_per_sqm) - 1 AS raw_deviation,
        -- 面積帯（D-026: 〜30 / 30〜45 / 45〜60㎡）
        CASE
            WHEN area_sqm < 30 THEN '1:〜30'
            WHEN area_sqm < 45 THEN '2:30〜45'
            ELSE '3:45〜60'
        END AS area_band
    FROM {{ source('osaka_real_estate', 'predictions_model_c') }}
),

-- ① 市全体の面積帯中央値を引く（セグメント混在＝㎡単価構造の帯差を除去）
band_adj AS (
    SELECT
        *,
        PERCENTILE_CONT(raw_deviation, 0.5) OVER (PARTITION BY area_band) AS city_band_median_deviation
    FROM base
),

with_band AS (
    SELECT
        *,
        raw_deviation - city_band_median_deviation AS band_adjusted_deviation
    FROM band_adj
),

-- ② 駅内中央値を引く（立地＝駅固定の時点・空間バイアスを除去）
station_adj AS (
    SELECT
        *,
        PERCENTILE_CONT(band_adjusted_deviation, 0.5) OVER (PARTITION BY station_name) AS station_median_adjusted_deviation
    FROM with_band
)

SELECT
    -- キー / 属性
    trade_quarter,
    ward,
    district,
    station_name,
    line_name,
    station_lat,
    station_lon,
    area_sqm,
    area_band,
    building_age_years,
    walk_minutes,

    -- スコア用（予測には入れない・v9）
    renovation_done_flag,
    seismic_new,
    seismic_old_flag,
    station_median_price_per_sqm,
    station_transaction_count,
    station_price_iqr,
    nearest_land_price,
    land_price_change_rate,
    land_price_distance_m,
    renovation_unknown_flag,

    -- リスク減点・品質フラグ
    is_imputed_building_age,
    is_imputed_walk_minutes,
    is_imputed_land_price,
    is_negative_age,
    potential_dup_flag,
    outlier_pps_flag,

    -- 実勢・予測・乖離
    actual_price_per_sqm,
    predicted_price_per_sqm,
    raw_deviation,
    city_band_median_deviation,
    band_adjusted_deviation,
    station_median_adjusted_deviation,
    -- 最終: 駅相対乖離（負に大きいほど割安）
    band_adjusted_deviation - station_median_adjusted_deviation AS station_relative_deviation
FROM station_adj
