-- stg_land_price: 公示価格の型変換・大阪市絞り込み
-- 入力: raw_land_price_2025（L01-2025）
-- L01_008=公示価格（円/m²）, L01_009=対前年変動率（%）

WITH raw AS (
    SELECT *
    FROM {{ source('osaka_real_estate', 'raw_land_price_2025') }}
    WHERE STARTS_WITH(L01_006, '大阪市')
),

casted AS (
    SELECT
        L01_001                             AS point_id,
        L01_006                             AS city_name,
        SAFE_CAST(L01_008 AS INT64)         AS land_price_per_sqm,
        SAFE_CAST(L01_009 AS FLOAT64)       AS yoy_change_pct,
        SAFE_CAST(lon AS FLOAT64)           AS lon,
        SAFE_CAST(lat AS FLOAT64)           AS lat
    FROM raw
)

SELECT * FROM casted
