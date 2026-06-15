-- stg_transactions: 成約価格情報の型変換・フラグ付与・スコープ判定
-- 入力: raw_transactions（全列STRING・大阪府47,386行）
-- 出力: 大阪市スコープ（24,613行）に絞り、D-002〜D-011の処理を適用

WITH raw AS (
    SELECT * FROM {{ source('osaka_real_estate', 'raw_transactions') }}
    WHERE STARTS_WITH(city_name, '大阪市')
),

casted AS (
    SELECT
        -- 識別・場所
        city_name,
        district_name,
        nearest_station_name                                        AS station_name_raw,
        SAFE_CAST(nearest_station_distance_min AS INT64)            AS walk_minutes,

        -- 価格・面積
        SAFE_CAST(trade_price_total AS INT64)                       AS price,
        SAFE_CAST(area_sqm AS FLOAT64)                              AS area_sqm,
        SAFE_DIVIDE(
            SAFE_CAST(trade_price_total AS INT64),
            SAFE_CAST(area_sqm AS FLOAT64)
        )                                                           AS price_per_sqm,

        -- 築年数（成約年 - 建築年）
        SAFE_CAST(SUBSTR(trade_period, 1, 4) AS INT64)
            - SAFE_CAST(REGEXP_EXTRACT(built_year, r'^([0-9]{4})年$') AS INT64)
                                                                    AS building_age_raw,
        built_year,

        -- 物件属性
        layout,
        building_structure,
        renovation,

        -- 取引情報
        trade_period,
        SAFE_CAST(SUBSTR(trade_period, 1, 4) AS INT64)              AS trade_year,
        SAFE_CAST(REGEXP_EXTRACT(trade_period, r'第([1-4])') AS INT64) AS trade_quarter,
        trade_circumstances
    FROM raw
),

flagged AS (
    SELECT
        *,

        -- D-008: 築年数マイナス補正
        CASE WHEN building_age_raw < 0 THEN 0 ELSE building_age_raw END
            AS building_age_years,
        CASE WHEN building_age_raw < 0 THEN 1 ELSE 0 END
            AS is_negative_age,

        -- D-007: 改装空欄フラグ
        CASE WHEN renovation = '' OR renovation IS NULL THEN 1 ELSE 0 END
            AS renovation_unknown_flag,
        CASE WHEN renovation = '改装済み' THEN 1 ELSE 0 END
            AS renovation_done_flag,

        -- D-002: ㎡単価5万円/m²未満フラグ（物理的ミス候補）
        CASE WHEN price_per_sqm < 50000 THEN 1 ELSE 0 END
            AS outlier_pps_flag,

        -- D-009: 時系列分割ラベル
        -- Fold A（本番）: 訓練=2021-2024, テスト=2025
        CASE
            WHEN SAFE_CAST(SUBSTR(trade_period, 1, 4) AS INT64) <= 2024 THEN 'train'
            WHEN SAFE_CAST(SUBSTR(trade_period, 1, 4) AS INT64) = 2025  THEN 'test'
        END AS fold_a_split,
        -- Fold B（検証）: 訓練=2021-2023, テスト=2024
        CASE
            WHEN SAFE_CAST(SUBSTR(trade_period, 1, 4) AS INT64) <= 2023 THEN 'train'
            WHEN SAFE_CAST(SUBSTR(trade_period, 1, 4) AS INT64) = 2024  THEN 'test'
            WHEN SAFE_CAST(SUBSTR(trade_period, 1, 4) AS INT64) = 2025  THEN 'exclude'
        END AS fold_b_split,

        -- 旧耐震基準フラグ（1981年以前竣工 = 築45年以上相当）
        CASE
            WHEN SAFE_CAST(REGEXP_EXTRACT(built_year, r'^([0-9]{4})年$') AS INT64) <= 1981
            THEN 1 ELSE 0
        END AS seismic_old_flag

    FROM casted
),

scoped AS (
    SELECT
        *,

        -- スコープ判定（D-003/D-011/D-018）。徒歩・築年が「欠損」の行は除外せず対象に
        -- 含め、intermediate で訓練期間中央値により補完する。範囲外（徒歩>20分・築<5/>60年）は除外。
        -- NULLセーフのため COALESCE(..., FALSE)。complete-case は scope_flag かつ
        -- walk_minutes/building_age_years が非NULL の行で復元できる。
        -- 駅名は本分析の核（駅中央値・地価・駅ランキングの基盤）のため必須。
        -- 駅名欠損は補完せず除外（手順書 PART 7: 最寄駅名欠損は基本除外）。
        -- 徒歩・築年の「欠損」は駅があれば intermediate で補完するため対象に含める。
        COALESCE(
            area_sqm BETWEEN 20 AND 60
            AND price >= 5000000
            AND price_per_sqm >= 50000
            AND station_name_raw IS NOT NULL AND station_name_raw != ''
            AND (walk_minutes IS NULL OR walk_minutes <= 20)
            AND (building_age_years IS NULL OR building_age_years BETWEEN 5 AND 60),
            FALSE
        ) AS scope_flag,

        -- 除外理由（最初に該当する1つ。欠損(NULL)の徒歩・築年は補完対象なので除外理由にしない）
        CASE
            WHEN area_sqm IS NULL OR area_sqm NOT BETWEEN 20 AND 60
                THEN 'area_out_of_scope'
            WHEN price IS NULL OR price < 5000000
                THEN 'price_out_of_scope'
            WHEN price_per_sqm IS NULL OR price_per_sqm < 50000
                THEN 'pps_too_low'
            WHEN station_name_raw IS NULL OR station_name_raw = ''
                THEN 'station_missing'
            WHEN walk_minutes > 20
                THEN 'walk_out_of_scope'
            WHEN building_age_years < 5 OR building_age_years > 60
                THEN 'age_out_of_scope'
            ELSE NULL
        END AS excluded_reason

    FROM flagged
),

named AS (
    -- D-006: 取引側の駅名も staging で正規化し、駅結合キー station_name を作る
    -- （stg_station_master と同一の normalize_station_name マクロ + mapping）
    SELECT
        s.*,
        COALESCE(m.canonical_name, {{ normalize_station_name('s.station_name_raw') }})
            AS station_name
    FROM scoped s
    LEFT JOIN {{ ref('station_name_mapping') }} m
        ON {{ normalize_station_name('s.station_name_raw') }} = m.raw_name
)

SELECT * FROM named
