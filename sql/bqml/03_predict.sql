-- Step 10 フェーズ3: 採用モデル(Model C)で予測㎡単価を生成（候補=2025年）
-- 出力: 新規テーブル `osaka_real_estate.predictions_model_c`（既存raw/martは触らない）
-- 用途: この物件単位予測を土台に、Step 11 で【駅・エリア単位の割安傾向】(本命・D-024)へ集約する。
-- 方針:
--   - 採用モデル D-022 = model_c（線形・面積/築年/徒歩/改装/新耐震/駅中央値㎡単価）
--   - log学習のため Duan smearing 係数で円/㎡へ逆変換（Jensen下振れ補正）
--   - smearing 係数は Model C の【訓練残差】から固定算出（2025テストからは作らない＝リーク防止 D-023）
--   - 候補は 2025年（fold='A' AND split='test' AND model_eligible）
--   - 下流（駅相対乖離・スコア・駅集約）が使う列を一緒に持たせて1テーブルで完結させる
-- 実行: Python BQクライアント（gcloud回避策）。実行後に件数・NULL・min/max・全体バイアスを検証する。

CREATE OR REPLACE TABLE `osaka-fudosan-dataanalysis.osaka_real_estate.predictions_model_c` AS
WITH
-- Fold A 全行(train+test)を1回 ML.PREDICT。passthrough で元の列も保持。
pred_all AS (
  SELECT *
  FROM ML.PREDICT(MODEL `osaka-fudosan-dataanalysis.osaka_real_estate.model_c`,
    (SELECT * FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
     WHERE fold='A' AND model_eligible))
),
-- smearing 係数 = 訓練残差(2021-2024)の EXP 平均。テスト(2025)からは作らない。
sm AS (
  SELECT AVG(EXP(LN(price_per_sqm) - predicted_log_price_per_sqm)) AS smearing
  FROM pred_all
  WHERE split='train'
)
SELECT
  -- キー / 属性
  trade_year,
  trade_quarter,
  ward,
  district,
  station_name,
  line_name,
  station_lat,
  station_lon,

  -- 予測に使った特徴量（参照用）
  area_sqm,
  building_age_years,
  walk_minutes,
  renovation_done_flag,
  seismic_new,
  station_median_price_per_sqm,

  -- スコア用に下流で使う項目（v9: 予測には入れない）
  nearest_land_price,
  land_price_change_rate,
  land_price_distance_m,
  station_transaction_count,
  station_price_iqr,
  renovation_unknown_flag,
  seismic_old_flag,

  -- リスク減点・品質フラグ
  is_imputed_building_age,
  is_imputed_walk_minutes,
  is_imputed_land_price,
  is_negative_age,
  potential_dup_flag,
  outlier_pps_flag,

  -- 実勢 と 予測
  trade_price,
  price_per_sqm                                                       AS actual_price_per_sqm,
  ROUND(EXP(predicted_log_price_per_sqm) * (SELECT smearing FROM sm)) AS predicted_price_per_sqm,
  -- 参考: 補正前後を追えるよう smearing も記録
  ROUND((SELECT smearing FROM sm), 4)                                 AS smearing_factor
FROM pred_all
WHERE split='test';   -- 2025年のみ（候補）
