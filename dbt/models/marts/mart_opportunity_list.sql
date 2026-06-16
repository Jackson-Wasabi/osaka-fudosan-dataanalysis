-- mart_opportunity_list: 駅単位の調査優先度ランキング（本命の成果物・D-024）
-- 入力: int_property_deviation（物件・2025年候補）/ 粒度: 駅（2025年10件以上・D-025）
-- スコア（D-027/D-028・全要素パーセンタイル/比率ベース）:
--   調査優先度 = 割安度45 + 市場信頼性25(件数15+IQR10) + 地価補足15 + データ品質15 − リスク減点20、0-100クリップ
-- PART 17-3 感度分析: バランス型(45/25/15/15/-20)・割安重視型(60/15/10/15/-20)・リスク重視型(35/30/15/20/-30)の
--   3配点でスコア化し、3パターン中2回以上Top20の駅を stable_flag=安定候補とする（D-032）。
--   主スコア priority_score はバランス型（従来と同値）。
-- C案(D-031b改/PART15-A): 旧耐震は減点でなく理由として可視化（old_seismic_share / high_risk_share）。物件別は int の building_risk_label。
-- 用途: 仕入れが優先調査すべきエリアの一次スクリーニング。買い判断でなく逆選択(D-024)のため必ず人が現物確認。

WITH per_station AS (
    SELECT
        station_name,
        APPROX_TOP_COUNT(ward, 1)[OFFSET(0)].value AS ward,
        ANY_VALUE(line_name) AS line_name,
        ANY_VALUE(station_lat) AS station_lat,
        ANY_VALUE(station_lon) AS station_lon,
        COUNT(*) AS n_transactions_2025,

        ANY_VALUE(station_median_adjusted_deviation) AS under_level,         -- ①駅水準（負ほど割安）
        AVG(IF(station_relative_deviation <= -0.15, 1, 0)) AS bargain_share,  -- ②駅内バーゲン比率（補助）

        ANY_VALUE(station_transaction_count) AS station_transaction_count,
        SAFE_DIVIDE(ANY_VALUE(station_price_iqr), ANY_VALUE(station_median_price_per_sqm)) AS iqr_ratio,
        AVG(nearest_land_price) AS avg_land_price,

        -- 品質（D-029: 改装不明は除外し補完フラグのみ）
        AVG(IF(is_imputed_building_age OR is_imputed_walk_minutes OR is_imputed_land_price, 1, 0)) AS quality_issue_share,
        -- リスク減点の素（D-031: outlier除外。旧耐震は減点せずC案で可視化）
        AVG(IF((seismic_old_flag = 1 AND renovation_done_flag = 1)
               OR is_negative_age = 1 OR potential_dup_flag, 1, 0)) AS risk_share,

        -- C案: 建物リスクの理由（減点でなく表示・PART 15-A）
        AVG(seismic_old_flag) AS old_seismic_share,                                            -- 旧耐震率
        AVG(IF(seismic_old_flag = 1 AND renovation_unknown_flag = 1, 1, 0)) AS high_risk_share, -- 旧耐震×改装不明=リスク高

        APPROX_QUANTILES(actual_price_per_sqm, 2)[OFFSET(1)] AS actual_median_price_per_sqm
    FROM {{ ref('int_property_deviation') }}
    GROUP BY station_name
    HAVING COUNT(*) >= 10
),

-- 各要素をパーセンタイル(0-1)に。配点を変えるだけで3パターンを作れるよう素の比率で保持。
pct AS (
    SELECT
        *,
        PERCENT_RANK() OVER (ORDER BY under_level DESC)                AS pct_value,  -- 安いほど1
        PERCENT_RANK() OVER (ORDER BY station_transaction_count ASC)   AS pct_count,  -- 多いほど1
        PERCENT_RANK() OVER (ORDER BY iqr_ratio DESC)                  AS pct_iqr,    -- 締まるほど1
        PERCENT_RANK() OVER (ORDER BY avg_land_price ASC)              AS pct_land,   -- 高いほど1
        (1 - quality_issue_share)                                     AS pct_quality
    FROM per_station
),

scored AS (
    SELECT
        *,
        -- 3配点のスコア（信頼性は件数:IQR=0.6:0.4で内分）
        GREATEST(0, LEAST(100, 45*pct_value + 25*(0.6*pct_count+0.4*pct_iqr) + 15*pct_land + 15*pct_quality - 20*risk_share)) AS score_balance,
        GREATEST(0, LEAST(100, 60*pct_value + 15*(0.6*pct_count+0.4*pct_iqr) + 10*pct_land + 15*pct_quality - 20*risk_share)) AS score_discount,
        GREATEST(0, LEAST(100, 35*pct_value + 30*(0.6*pct_count+0.4*pct_iqr) + 15*pct_land + 20*pct_quality - 30*risk_share)) AS score_risk
    FROM pct
),

ranked AS (
    SELECT
        *,
        RANK() OVER (ORDER BY score_balance  DESC) AS rank_balance,
        RANK() OVER (ORDER BY score_discount DESC) AS rank_discount,
        RANK() OVER (ORDER BY score_risk     DESC) AS rank_risk
    FROM scored
)

SELECT
    station_name,
    ward,
    line_name,
    station_lat,
    station_lon,
    n_transactions_2025,
    actual_median_price_per_sqm,

    ROUND(under_level, 3) AS under_level,
    ROUND(bargain_share, 3) AS bargain_share,

    -- バランス型のスコア内訳（透明性）
    ROUND(45*pct_value, 1) AS sc_value,
    ROUND(25*(0.6*pct_count+0.4*pct_iqr), 1) AS sc_reliability,
    ROUND(15*pct_land, 1) AS sc_land,
    ROUND(15*pct_quality, 1) AS sc_quality,
    ROUND(-20*risk_share, 1) AS risk_penalty,

    -- 主スコア＝バランス型
    ROUND(score_balance, 1) AS priority_score,
    rank_balance AS priority_rank,

    -- PART 17-3 感度分析：3配点のスコア・順位・安定候補
    ROUND(score_discount, 1) AS score_discount,
    rank_discount,
    ROUND(score_risk, 1) AS score_risk,
    rank_risk,
    ((CASE WHEN rank_balance <= 20 THEN 1 ELSE 0 END)
   + (CASE WHEN rank_discount <= 20 THEN 1 ELSE 0 END)
   + (CASE WHEN rank_risk <= 20 THEN 1 ELSE 0 END)) >= 2 AS stable_flag,  -- 3中2回以上Top20

    -- C案：建物リスクの理由（減点でなく可視化・PART 15-A）
    ROUND(old_seismic_share, 3) AS old_seismic_share,
    ROUND(high_risk_share, 3) AS high_risk_share,

    -- 透明性のための素データ
    ROUND(iqr_ratio, 3) AS iqr_ratio,
    ROUND(avg_land_price) AS avg_land_price,
    ROUND(quality_issue_share, 3) AS quality_issue_share,
    ROUND(risk_share, 3) AS risk_share,
    station_transaction_count
FROM ranked
ORDER BY priority_score DESC
