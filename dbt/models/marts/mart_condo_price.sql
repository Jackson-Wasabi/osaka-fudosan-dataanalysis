-- mart_condo_price: 物件単位の分析完成テーブル（Tableau / BQML が読む）
-- 入力: int_transactions_with_station_features（物件 × Fold）
-- 方針:
--   - 予測モデル用の特徴量は補完済みの値を「誰が見ても分かる正規の列名」で公開（生のNULL列は出さない）
--   - 予測に入れない項目（公示価格・駅件数/IQR・renovation_unknown）はスコア用として別に保持（v9核心）
--   - 両 Fold を保持し fold 列で区別（Tableau は fold='A' でフィルタ。PART17のFold横断比較に対応）
--   - 新規出現駅（駅中央値が訓練に無くNULL）は station_history_missing でフラグ、model_eligible=FALSE
--     としてモデル学習・予測・候補ランキングから除外する（D-017）
-- 予測㎡単価・乖離率・調査優先度スコアは Step 10-11 で付与する。

SELECT
    -- キー / 属性
    trade_year,
    trade_quarter,
    fold,
    split,
    city_name        AS ward,            -- 大阪市○○区
    district_name    AS district,
    station_name,
    line_name,
    station_lat,
    station_lon,

    -- 目的変数
    price AS trade_price,
    price_per_sqm,
    LN(price_per_sqm) AS log_price_per_sqm,   -- BQML の目的変数

    -- 予測モデル用 特徴量（補完済みの値を正規名で公開）
    area_sqm,
    imputed_building_age      AS building_age_years,
    imputed_walk_minutes      AS walk_minutes,
    renovation_done_flag,
    seismic_new,
    station_median_price_per_sqm,

    -- スコア用（予測には入れない・v9核心）
    imputed_nearest_land_price AS nearest_land_price,
    land_price_change_rate,
    land_price_distance_m,
    station_transaction_count,
    station_price_iqr,
    renovation_unknown_flag,
    station_joined,
    seismic_old_flag,

    -- データ品質フラグ
    is_imputed_building_age,
    is_imputed_walk_minutes,
    is_imputed_land_price,
    is_negative_age,
    potential_dup_flag,
    outlier_pps_flag,

    -- D-017: 新規出現駅（駅相場が無く予測・採点不能）の識別と適格フラグ
    (station_median_price_per_sqm IS NULL) AS station_history_missing,
    (station_median_price_per_sqm IS NOT NULL) AS model_eligible,

    -- 参考（元データ）
    layout,
    renovation,
    built_year

FROM {{ ref('int_transactions_with_station_features') }}
