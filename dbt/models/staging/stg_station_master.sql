-- stg_station_master: 駅マスタの正規化（D-006）
-- 入力: raw_station_master_2025（N02-2025）
-- 処理: (1)括弧除去 (2)「駅」除去 → normalize_station_name マクロで共通化
--       (3)mapping CSV適用（LEFT JOIN + COALESCE）

WITH raw AS (
    SELECT DISTINCT
        n02_003 AS line_name,
        n02_004 AS company_name,
        n02_005 AS station_name_raw,
        SAFE_CAST(lon AS FLOAT64) AS lon,
        SAFE_CAST(lat AS FLOAT64) AS lat
    FROM {{ source('osaka_real_estate', 'raw_station_master_2025') }}
    WHERE n02_005 IS NOT NULL AND n02_005 != ''
),

mapped AS (
    SELECT
        r.line_name,
        r.company_name,
        r.station_name_raw,
        r.lon,
        r.lat,
        -- Step3: mapping 一致時は正規名、非一致時は Step1+Step2 正規化名
        COALESCE(m.canonical_name, {{ normalize_station_name('r.station_name_raw') }})
            AS station_name
    FROM raw r
    LEFT JOIN {{ ref('station_name_mapping') }} m
        ON {{ normalize_station_name('r.station_name_raw') }} = m.raw_name
)

SELECT * FROM mapped
