-- int_station_market_features: 駅別の市場特徴量（粒度: 駅 × Fold）
-- 入力: stg_transactions（scope_flag=TRUE・駅名あり）
-- D-009 リーク対策: 中央値・IQR 等は各 Fold の訓練期間のみから算出する。
--   Fold A（本番）訓練 = 2021-2024  / Fold B（検証）訓練 = 2021-2023
-- これらを各 Fold の train/test 両方の行へ適用することでテスト期間の情報混入を防ぐ。

WITH tx AS (
    SELECT
        station_name,
        price_per_sqm,
        walk_minutes,
        renovation_done_flag,
        trade_year
    FROM {{ ref('stg_transactions') }}
    WHERE scope_flag = TRUE
      AND station_name IS NOT NULL
      AND station_name != ''
),

-- 各 Fold の訓練期間の行だけを展開
fold_rows AS (
    SELECT *, 'A' AS fold FROM tx WHERE trade_year BETWEEN 2021 AND 2024
    UNION ALL
    SELECT *, 'B' AS fold FROM tx WHERE trade_year BETWEEN 2021 AND 2023
)

SELECT
    station_name,
    fold,
    COUNT(*) AS station_transaction_count,
    -- 中央値・四分位（GROUP BY 可能な APPROX_QUANTILES を使用）
    APPROX_QUANTILES(price_per_sqm, 100)[OFFSET(50)] AS station_median_price_per_sqm,
    APPROX_QUANTILES(price_per_sqm, 100)[OFFSET(75)]
        - APPROX_QUANTILES(price_per_sqm, 100)[OFFSET(25)] AS station_price_iqr,
    AVG(walk_minutes) AS station_avg_walk_minutes,
    AVG(renovation_done_flag) AS station_renovation_rate
FROM fold_rows
GROUP BY station_name, fold
