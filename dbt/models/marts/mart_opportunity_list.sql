-- mart_opportunity_list: 駅単位の調査優先度ランキング（本命の成果物・D-024）
-- 入力: int_property_deviation（物件・2025年候補）
-- 粒度: 駅（2025年取引10件以上に限定・D-025）
-- スコア（D-027/D-028・全要素パーセンタイル/比率ベース）:
--   調査優先度 = 割安度45 + 市場信頼性25(件数15+IQR10) + 地価補足15 + データ品質15 − リスク減点20、0-100クリップ
--   割安度は ①駅水準(station_median_adjusted_deviation) を主軸。②bargain_share は補助列で併記。
-- 用途: 仕入れが優先的に調べるべきエリアの一次スクリーニング。買い判断ではない。逆選択(D-024)のため必ず人が現物確認。

WITH per_station AS (
    SELECT
        station_name,
        APPROX_TOP_COUNT(ward, 1)[OFFSET(0)].value AS ward,   -- 代表区（駅が区境をまたぐ場合の最頻）
        ANY_VALUE(line_name) AS line_name,
        ANY_VALUE(station_lat) AS station_lat,
        ANY_VALUE(station_lon) AS station_lon,
        COUNT(*) AS n_transactions_2025,

        -- 割安シグナル
        ANY_VALUE(station_median_adjusted_deviation) AS under_level,            -- ①駅水準（負ほど割安）
        AVG(IF(station_relative_deviation <= -0.15, 1, 0)) AS bargain_share,     -- ②駅内バーゲン比率（補助）

        -- 信頼性・地価の素
        ANY_VALUE(station_transaction_count) AS station_transaction_count,       -- 訓練期間の取引件数（市場の厚み）
        SAFE_DIVIDE(ANY_VALUE(station_price_iqr), ANY_VALUE(station_median_price_per_sqm)) AS iqr_ratio,
        AVG(nearest_land_price) AS avg_land_price,

        -- 品質・リスクの素（物件割合）
        -- D-029: 改装不明(94%欠損)はデータ収集の癖で駅品質を測れず全スコアに偽の天井を作るため除外。
        --        補完フラグ（築年・徒歩・地価の補完）のみで品質を測る。
        AVG(IF(is_imputed_building_age
               OR is_imputed_walk_minutes OR is_imputed_land_price, 1, 0)) AS quality_issue_share,
        -- D-031: outlier_pps_flag は「㎡単価<5万」専用で価格下限500万(=60㎡で83,333/㎡)と冗長＝スコープ内で恒久0。
        --         飾りなので除外。残りは旧耐震×改装・築年補正・重複（重複はD-005で残すが murky=軽い不確実性として減点）。
        AVG(IF((seismic_old_flag = 1 AND renovation_done_flag = 1)
               OR is_negative_age = 1 OR potential_dup_flag, 1, 0)) AS risk_share,

        -- 参考
        APPROX_QUANTILES(actual_price_per_sqm, 2)[OFFSET(1)] AS actual_median_price_per_sqm
    FROM {{ ref('int_property_deviation') }}
    GROUP BY station_name
    HAVING COUNT(*) >= 10   -- D-025: 2025年10件以上の駅のみランキング対象
),

scored AS (
    SELECT
        *,
        -- 割安度45（駅水準が安い順）
        ROUND(45 * PERCENT_RANK() OVER (ORDER BY under_level DESC), 1) AS sc_value,
        -- 市場信頼性25 = 件数15 + IQR狭さ10
        ROUND(15 * PERCENT_RANK() OVER (ORDER BY station_transaction_count ASC), 1) AS sc_count,
        ROUND(10 * PERCENT_RANK() OVER (ORDER BY iqr_ratio DESC), 1) AS sc_iqr,
        -- 地価補足15（公示価格が高いほど＝エリア基礎体力）
        ROUND(15 * PERCENT_RANK() OVER (ORDER BY avg_land_price ASC), 1) AS sc_land,
        -- データ品質15（補完・改装不明が少ないほど）
        ROUND(15 * (1 - quality_issue_share), 1) AS sc_quality,
        -- リスク減点（最大-20）
        ROUND(-20 * risk_share, 1) AS risk_penalty
    FROM per_station
)

SELECT
    station_name,
    ward,
    line_name,
    station_lat,
    station_lon,
    n_transactions_2025,
    actual_median_price_per_sqm,

    -- 割安シグナル
    ROUND(under_level, 3) AS under_level,
    ROUND(bargain_share, 3) AS bargain_share,

    -- スコア内訳
    sc_value,
    ROUND(sc_count + sc_iqr, 1) AS sc_reliability,
    sc_count,
    sc_iqr,
    sc_land,
    sc_quality,
    risk_penalty,

    -- 総合（0-100クリップ）と順位
    GREATEST(0, LEAST(100,
        ROUND(sc_value + sc_count + sc_iqr + sc_land + sc_quality + risk_penalty, 1)
    )) AS priority_score,
    RANK() OVER (ORDER BY GREATEST(0, LEAST(100,
        sc_value + sc_count + sc_iqr + sc_land + sc_quality + risk_penalty)) DESC) AS priority_rank,

    -- 透明性のための素データ
    ROUND(iqr_ratio, 3) AS iqr_ratio,
    ROUND(avg_land_price) AS avg_land_price,
    ROUND(quality_issue_share, 3) AS quality_issue_share,
    ROUND(risk_share, 3) AS risk_share,
    station_transaction_count
FROM scored
ORDER BY priority_score DESC
