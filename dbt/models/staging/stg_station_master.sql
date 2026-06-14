-- stg_station_master: 駅マスタの正規化（D-006）
-- 入力: raw_station_master_2025（N02-2025）
-- 処理: (1)括弧除去 (2)「駅」除去 (3)mapping CSV適用

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

normalized AS (
    SELECT
        *,
        -- Step1: 括弧除去（全角・半角）
        REGEXP_REPLACE(
            REGEXP_REPLACE(station_name_raw, r'\([^)]*\)', ''),
            r'（[^）]*）', ''
        ) AS name_step1,
        -- Step2: 末尾の「駅」除去
        REGEXP_REPLACE(
            REGEXP_REPLACE(
                REGEXP_REPLACE(station_name_raw, r'\([^)]*\)', ''),
                r'（[^）]*）', ''
            ),
            r'駅$', ''
        ) AS name_step2
    FROM raw
),

mapped AS (
    SELECT
        n.line_name,
        n.company_name,
        n.station_name_raw,
        n.lon,
        n.lat,
        -- Step3: mapping CSV適用。一致しない場合は Step2 の正規化済み名をそのまま使う
        COALESCE(m.canonical_name, n.name_step2) AS station_name
    FROM normalized n
    LEFT JOIN {{ ref('station_name_mapping') }} m
        ON n.name_step2 = m.raw_name
)

SELECT * FROM mapped
