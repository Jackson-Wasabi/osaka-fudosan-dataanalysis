-- stg_land_price: 公示価格の型変換・大阪市絞り込み
-- 入力: raw_land_price_2025（L01-2025・大阪府）
-- L01_001=行政区域コード（大阪市=271xx）, L01_008=公示価格（円/m²）, L01_009=対前年変動率（%）
-- 注意（修正）: 旧実装は L01_006 で市を絞っていたが L01_006 は「前年連番」(例 001) で誤り。
--   大阪市は行政区域コード L01_001 が '271' 始まり（574地点）。市区名は住所 L01_025 から抽出する。

WITH raw AS (
    SELECT *
    FROM {{ source('osaka_real_estate', 'raw_land_price_2025') }}
    WHERE STARTS_WITH(L01_001, '271')   -- 大阪市24区の行政区域コード
),

casted AS (
    SELECT
        -- 標準地番号（行政区域コード/用途区分/連番）= 地点の一意キー
        CONCAT(L01_001, '_', L01_002, '_', L01_003)   AS point_id,
        -- 住所（例: 大阪府　大阪市東成区…）から「大阪市○○区」を抽出
        REGEXP_EXTRACT(L01_025, r'(大阪市.+?区)')      AS city_name,
        SAFE_CAST(L01_008 AS INT64)                    AS land_price_per_sqm,
        SAFE_CAST(L01_009 AS FLOAT64)                  AS yoy_change_pct,
        SAFE_CAST(lon AS FLOAT64)                      AS lon,
        SAFE_CAST(lat AS FLOAT64)                      AS lat
    FROM raw
)

SELECT * FROM casted
