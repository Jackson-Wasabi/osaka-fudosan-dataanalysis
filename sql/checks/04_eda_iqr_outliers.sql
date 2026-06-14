-- 04_eda_iqr_outliers.sql
-- 生成元: scripts/run_eda.py（編集はスクリプト側で行うこと）
-- 読み取り専用 / 入力: raw_* / データ取得日: 2026-06-12 / 対象スコープ: 大阪市・中古マンション等・成約価格情報 2021Q1-2025Q4（24,613行）。raw全体は大阪府47,386行で、形式チェックは府全体で実施済み（D-010）
WITH base AS (
  SELECT
    SAFE_CAST(trade_price_total AS INT64) AS price,
    SAFE_CAST(area_sqm AS FLOAT64) AS area,
    SAFE_DIVIDE(SAFE_CAST(trade_price_total AS INT64), SAFE_CAST(area_sqm AS FLOAT64)) AS pps,
    SAFE_CAST(SUBSTR(trade_period, 1, 4) AS INT64)
      - SAFE_CAST(REGEXP_EXTRACT(built_year, r'^([0-9]{4})年$') AS INT64) AS age,
    SAFE_CAST(nearest_station_distance_min AS INT64) AS walk,
    nearest_station_name AS st_name,
    built_year, trade_period, city_name, district_name, layout, renovation
  FROM `osaka_real_estate.raw_transactions`
  WHERE STARTS_WITH(city_name, '大阪市')
)
, banded AS (
  SELECT pps,
    CASE WHEN age IS NULL THEN '不明'
         WHEN age <= 10 THEN '築0-10年' WHEN age <= 20 THEN '築11-20年'
         WHEN age <= 30 THEN '築21-30年' WHEN age <= 40 THEN '築31-40年'
         WHEN age <= 50 THEN '築41-50年' WHEN age <= 60 THEN '築51-60年'
         ELSE '築61年以上' END AS band
  FROM base WHERE pps IS NOT NULL
),
stats AS (
  SELECT band,
    APPROX_QUANTILES(pps, 4)[OFFSET(1)] AS q1,
    APPROX_QUANTILES(pps, 4)[OFFSET(2)] AS q2,
    APPROX_QUANTILES(pps, 4)[OFFSET(3)] AS q3,
    COUNT(*) AS n
  FROM banded GROUP BY band
)
SELECT s.band, s.n, ROUND(s.q1) AS q1, ROUND(s.q2) AS med, ROUND(s.q3) AS q3,
  ROUND(s.q3 - s.q1) AS iqr,
  ROUND(s.q1 - 1.5 * (s.q3 - s.q1)) AS lower_fence,
  ROUND(s.q3 + 1.5 * (s.q3 - s.q1)) AS upper_fence,
  COUNTIF(b.pps < s.q1 - 1.5 * (s.q3 - s.q1)) AS n_below,
  COUNTIF(b.pps > s.q3 + 1.5 * (s.q3 - s.q1)) AS n_above
FROM stats s JOIN banded b ON b.band = s.band
GROUP BY s.band, s.n, s.q1, s.q2, s.q3 ORDER BY s.band
