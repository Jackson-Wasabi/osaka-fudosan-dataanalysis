-- Step 10 フェーズ0: 価格モデル前の診断（読み取り専用・SELECTのみ）
-- 母集団の原則: 年次比較は fold='A'（2021-2025を各物件1回）。
--   特徴量×目的変数・分布・相関は train(2021-2024)・model_eligible（モデルが学ぶ土俵）。
--   分布シフト(7)と報告ラグ(1)のみ test を覗くが、評価窓の判断にのみ用い、モデル調整には使わない。
-- 実行: scripts 経由で Python BigQuery クライアント（gcloud回避策）。各クエリは見出しコメント行で区切る。
-- 対象: `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`

-- ==== 1_report_lag_quarterly ====
-- 対策⑦: 2025の四半期別件数（後半の報告ラグ確認）
SELECT trade_year, trade_quarter, COUNT(*) AS n
FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
WHERE fold = 'A'
GROUP BY trade_year, trade_quarter
ORDER BY trade_year, trade_quarter;

-- ==== 2a_year_median_pps_raw ====
-- 対策①: 生の年次㎡単価中央値（参考。構成変化と混同しうる）
SELECT trade_year,
  APPROX_QUANTILES(price_per_sqm, 2)[OFFSET(1)] AS median_pps,
  COUNT(*) AS n
FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
WHERE fold = 'A'
GROUP BY trade_year ORDER BY trade_year;

-- ==== 2b_year_median_pps_by_areaband ====
-- 対策E: 面積帯を固定して値上がりを見る（サイズ構成の交絡を除去）
SELECT
  CASE WHEN area_sqm < 30 THEN '20-30' WHEN area_sqm < 40 THEN '30-40'
       WHEN area_sqm < 50 THEN '40-50' ELSE '50-60' END AS area_band,
  trade_year,
  APPROX_QUANTILES(price_per_sqm, 2)[OFFSET(1)] AS median_pps
FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
WHERE fold = 'A'
GROUP BY area_band, trade_year ORDER BY area_band, trade_year;

-- ==== 2c_year_median_pps_major_stations ====
-- 対策E: 全5年で各年20件以上ある「主要駅」に固定して値上がりを見る（立地構成の交絡を除去）
WITH yr AS (
  SELECT station_name, trade_year, COUNT(*) AS c
  FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
  WHERE fold = 'A' GROUP BY station_name, trade_year
),
maj AS (
  SELECT station_name FROM yr WHERE c >= 20
  GROUP BY station_name HAVING COUNT(DISTINCT trade_year) = 5
)
SELECT trade_year,
  APPROX_QUANTILES(price_per_sqm, 2)[OFFSET(1)] AS median_pps,
  COUNT(DISTINCT station_name) AS stations, COUNT(*) AS n
FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
WHERE fold = 'A' AND station_name IN (SELECT station_name FROM maj)
GROUP BY trade_year ORDER BY trade_year;

-- ==== 2d_staleness_gap ====
-- 対策①: 訓練(2021-2024)の駅中央値水準 vs 2025実績中央値のギャップ
SELECT
  (SELECT APPROX_QUANTILES(station_median_price_per_sqm, 2)[OFFSET(1)]
   FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
   WHERE fold='A' AND split='train' AND model_eligible) AS train_station_median_level,
  (SELECT APPROX_QUANTILES(price_per_sqm, 2)[OFFSET(1)]
   FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
   WHERE fold='A' AND split='test') AS actual_2025_median;

-- ==== 3_area_band_counts_iqr ====
-- 対策③: 面積帯別の件数と㎡単価のばらつき（小型の構成比・粒度由来の分散）
SELECT
  CASE WHEN area_sqm < 30 THEN '20-30' WHEN area_sqm < 40 THEN '30-40'
       WHEN area_sqm < 50 THEN '40-50' ELSE '50-60' END AS area_band,
  COUNT(*) AS n,
  APPROX_QUANTILES(price_per_sqm, 4)[OFFSET(1)] AS p25,
  APPROX_QUANTILES(price_per_sqm, 4)[OFFSET(2)] AS p50,
  APPROX_QUANTILES(price_per_sqm, 4)[OFFSET(3)] AS p75
FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
WHERE fold = 'A'
GROUP BY area_band ORDER BY area_band;

-- ==== 4a_target_percentiles ====
-- 対策A: 目的変数の分位（pps と log版）。log で歪みが減るか
WITH s AS (
  SELECT price_per_sqm AS x, LN(price_per_sqm) AS lx
  FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
  WHERE fold='A' AND split='train' AND model_eligible
)
SELECT 'price_per_sqm' AS var,
  ROUND(AVG(x)) AS mean, APPROX_QUANTILES(x,100)[OFFSET(1)] AS p1,
  APPROX_QUANTILES(x,100)[OFFSET(50)] AS p50, APPROX_QUANTILES(x,100)[OFFSET(99)] AS p99 FROM s
UNION ALL
SELECT 'log_price_per_sqm', ROUND(AVG(lx),3), ROUND(APPROX_QUANTILES(lx,100)[OFFSET(1)],3),
  ROUND(APPROX_QUANTILES(lx,100)[OFFSET(50)],3), ROUND(APPROX_QUANTILES(lx,100)[OFFSET(99)],3) FROM s;

-- ==== 4b_skewness ====
-- 対策A: 歪度（0に近いほど対称）。pps は右に歪み、log で改善するはず
WITH s AS (
  SELECT price_per_sqm AS x, LN(price_per_sqm) AS lx
  FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
  WHERE fold='A' AND split='train' AND model_eligible
),
m AS (SELECT AVG(x) mx, STDDEV_POP(x) sx, AVG(lx) mlx, STDDEV_POP(lx) slx FROM s)
SELECT ROUND(AVG(POW((x-mx)/sx,3)),3) AS skew_pps,
       ROUND(AVG(POW((lx-mlx)/slx,3)),3) AS skew_logpps
FROM s CROSS JOIN m;

-- ==== 4c_logpps_histogram ====
-- 対策A: log㎡単価の簡易ヒストグラム（0.25幅）。対称性を目視
SELECT ROUND(FLOOR(LN(price_per_sqm)/0.25)*0.25, 2) AS log_bin, COUNT(*) AS n
FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
WHERE fold='A' AND split='train' AND model_eligible
GROUP BY log_bin ORDER BY log_bin;

-- ==== 5a_feature_target_corr ====
-- 対策B: log㎡単価と各特徴量の相関（符号の事前確認）
SELECT
  ROUND(CORR(LN(price_per_sqm), area_sqm),3) AS corr_area,
  ROUND(CORR(LN(price_per_sqm), building_age_years),3) AS corr_age,
  ROUND(CORR(LN(price_per_sqm), walk_minutes),3) AS corr_walk,
  ROUND(CORR(LN(price_per_sqm), station_median_price_per_sqm),3) AS corr_station_median
FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
WHERE fold='A' AND split='train' AND model_eligible;

-- ==== 5b_age_nonlinearity ====
-- 対策B/⑥: 築年帯別の中央値㎡単価（非線形＝減価カーブを確認）
SELECT CAST(FLOOR(building_age_years/10)*10 AS INT64) AS age_band_start,
  APPROX_QUANTILES(price_per_sqm,2)[OFFSET(1)] AS median_pps, COUNT(*) AS n
FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
WHERE fold='A' AND split='train' AND model_eligible
GROUP BY age_band_start ORDER BY age_band_start;

-- ==== 5c_flag_effect ====
-- 対策B: 新耐震・改装済みの効果の向き（群別中央値）
SELECT seismic_new, renovation_done_flag,
  APPROX_QUANTILES(price_per_sqm,2)[OFFSET(1)] AS median_pps, COUNT(*) AS n
FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
WHERE fold='A' AND split='train' AND model_eligible
GROUP BY seismic_new, renovation_done_flag ORDER BY seismic_new, renovation_done_flag;

-- ==== 6_collinearity ====
-- 対策C: 駅中央値×公示価格の相関（Model D が効かない事前根拠）＋主要特徴量間の相関
SELECT
  ROUND(CORR(station_median_price_per_sqm, nearest_land_price),3) AS corr_stationmed_land,
  ROUND(CORR(station_median_price_per_sqm, area_sqm),3) AS corr_stationmed_area,
  ROUND(CORR(building_age_years, walk_minutes),3) AS corr_age_walk,
  ROUND(CORR(area_sqm, building_age_years),3) AS corr_area_age
FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
WHERE fold='A' AND split='train' AND model_eligible;

-- ==== 7_covariate_shift ====
-- 対策D: 訓練(2021-2024) vs テスト(2025) の特徴量分布シフト
SELECT split, COUNT(*) AS n,
  ROUND(AVG(area_sqm),1) AS avg_area,
  APPROX_QUANTILES(building_age_years,2)[OFFSET(1)] AS med_age,
  APPROX_QUANTILES(walk_minutes,2)[OFFSET(1)] AS med_walk,
  APPROX_QUANTILES(station_median_price_per_sqm,2)[OFFSET(1)] AS med_station_median
FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
WHERE fold='A' AND model_eligible
GROUP BY split ORDER BY split;

-- ==== 7b_areaband_shift ====
-- 対策D: 面積帯構成の train/test シフト（割合）
SELECT split,
  CASE WHEN area_sqm < 30 THEN '20-30' WHEN area_sqm < 40 THEN '30-40'
       WHEN area_sqm < 50 THEN '40-50' ELSE '50-60' END AS area_band,
  COUNT(*) AS n,
  ROUND(COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY split) * 100, 1) AS pct_in_split
FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
WHERE fold='A' AND model_eligible
GROUP BY split, area_band ORDER BY area_band, split;

-- ==== 8a_outlier_count ====
-- 対策F: 学習データ中の外れ値pps行（学習に含めるか判断）
SELECT COUNTIF(outlier_pps_flag = 1) AS outliers, COUNT(*) AS n,
  ROUND(COUNTIF(outlier_pps_flag = 1)/COUNT(*)*100, 2) AS pct
FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
WHERE fold='A' AND split='train' AND model_eligible;

-- ==== 8b_station_train_size_dist ====
-- 対策F/④: 駅別の訓練件数分布（少件数駅で駅中央値が不安定）
WITH s AS (
  SELECT station_name, COUNT(*) AS c
  FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
  WHERE fold='A' AND split='train' AND model_eligible GROUP BY station_name
)
SELECT COUNTIF(c < 20) AS stations_lt20, COUNTIF(c BETWEEN 20 AND 49) AS stations_20_49,
  COUNTIF(c >= 50) AS stations_ge50, COUNT(*) AS stations_total FROM s;
