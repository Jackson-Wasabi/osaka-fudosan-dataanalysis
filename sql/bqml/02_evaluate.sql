-- Step 10 フェーズ2: モデル評価・比較（読み取りのみ・BQ書き込みなし）
-- 主指標: ±10%以内の的中率（スクリーニング用途＝相対割安検出に最も整合）。MAE/RMSE/MdAPE/±20%は併記。
-- 評価母集団: Fold A・split='test'（2025通年）・model_eligible。学習: split='train'。
-- 逆変換: log学習のため Duan smearing 係数 s=AVG(EXP(残差_train)) を掛けて円/㎡へ戻す（対策2・Jensen下振れ補正）。
--   pred_pps = EXP(predicted_log) * s
-- 系統バイアス（対策1・最重要）: テストの符号付き相対誤差 (pred-actual)/actual を実測。
--   後段キャリブレーション(b)の係数 = AVG(actual / pred_pps)（テスト全体の平均倍率。1未満なら過大、1超なら過小予測）。
-- 各モデルは fold='A' AND model_eligible の全行(train+test)を1回 ML.PREDICT し、split で smearing(訓練)と指標(テスト)を出し分ける。
-- 対象表: `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
--
-- ※ブロックごとに独立クエリ。Python BQクライアントで順に実行する。


-- ============================================================================
-- ブロック1: 比較表（Baseline / A / B / C / D / E_tree / F_time）Fold A テスト2025
--   smearing 補正済。主指標 hit10 で並べ替え。bias/calib はキャリブレーション判断材料。
-- ============================================================================
WITH
-- 各モデルの予測（log）+ 実績・split を保持（Fold A 全行）
p_a AS (
  SELECT split, price_per_sqm, predicted_log_price_per_sqm AS plog
  FROM ML.PREDICT(MODEL `osaka-fudosan-dataanalysis.osaka_real_estate.model_a`,
    (SELECT * FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
     WHERE fold='A' AND model_eligible))
),
p_b AS (
  SELECT split, price_per_sqm, predicted_log_price_per_sqm AS plog
  FROM ML.PREDICT(MODEL `osaka-fudosan-dataanalysis.osaka_real_estate.model_b`,
    (SELECT * FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
     WHERE fold='A' AND model_eligible))
),
p_c AS (
  SELECT split, price_per_sqm, predicted_log_price_per_sqm AS plog
  FROM ML.PREDICT(MODEL `osaka-fudosan-dataanalysis.osaka_real_estate.model_c`,
    (SELECT * FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
     WHERE fold='A' AND model_eligible))
),
p_d AS (
  SELECT split, price_per_sqm, predicted_log_price_per_sqm AS plog
  FROM ML.PREDICT(MODEL `osaka-fudosan-dataanalysis.osaka_real_estate.model_d`,
    (SELECT * FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
     WHERE fold='A' AND model_eligible))
),
p_e AS (
  SELECT split, price_per_sqm, predicted_log_price_per_sqm AS plog
  FROM ML.PREDICT(MODEL `osaka-fudosan-dataanalysis.osaka_real_estate.model_e_tree`,
    (SELECT * FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
     WHERE fold='A' AND model_eligible))
),
p_f AS (
  SELECT split, price_per_sqm, predicted_log_price_per_sqm AS plog
  FROM ML.PREDICT(MODEL `osaka-fudosan-dataanalysis.osaka_real_estate.model_f_time`,
    (SELECT *, (trade_year - 2021) AS time_index
     FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
     WHERE fold='A' AND model_eligible))
),
-- 各モデルの smearing 係数（訓練残差）
sm AS (
  SELECT 'A' m, AVG(EXP(LN(price_per_sqm)-plog)) s FROM p_a WHERE split='train'
  UNION ALL SELECT 'B', AVG(EXP(LN(price_per_sqm)-plog)) FROM p_b WHERE split='train'
  UNION ALL SELECT 'C', AVG(EXP(LN(price_per_sqm)-plog)) FROM p_c WHERE split='train'
  UNION ALL SELECT 'D', AVG(EXP(LN(price_per_sqm)-plog)) FROM p_d WHERE split='train'
  UNION ALL SELECT 'E', AVG(EXP(LN(price_per_sqm)-plog)) FROM p_e WHERE split='train'
  UNION ALL SELECT 'F', AVG(EXP(LN(price_per_sqm)-plog)) FROM p_f WHERE split='train'
),
-- テスト行に smearing を掛けて pred_pps を作る（モデル別 UNION）
preds AS (
  SELECT 'Model A (面積+築年+徒歩)'              AS model_label, 1 AS ord, price_per_sqm AS actual, EXP(plog)*(SELECT s FROM sm WHERE m='A') AS pred FROM p_a WHERE split='test'
  UNION ALL SELECT 'Model B (A+改装+新耐震)',      2, price_per_sqm, EXP(plog)*(SELECT s FROM sm WHERE m='B') FROM p_b WHERE split='test'
  UNION ALL SELECT 'Model C (B+駅中央値)',         3, price_per_sqm, EXP(plog)*(SELECT s FROM sm WHERE m='C') FROM p_c WHERE split='test'
  UNION ALL SELECT 'Model D (C+公示価格)',         4, price_per_sqm, EXP(plog)*(SELECT s FROM sm WHERE m='D') FROM p_d WHERE split='test'
  UNION ALL SELECT 'Model E_tree (BOOSTED・C特徴)',5, price_per_sqm, EXP(plog)*(SELECT s FROM sm WHERE m='E') FROM p_e WHERE split='test'
  UNION ALL SELECT 'Model F_time (C+時点index)',   6, price_per_sqm, EXP(plog)*(SELECT s FROM sm WHERE m='F') FROM p_f WHERE split='test'
  -- Baseline: 駅中央値をそのまま予測値に（モデルなし・smearingなし）
  UNION ALL SELECT 'Baseline (駅中央値そのまま)',  0, price_per_sqm, station_median_price_per_sqm
    FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
    WHERE fold='A' AND split='test' AND model_eligible AND station_median_price_per_sqm IS NOT NULL
)
SELECT
  model_label,
  COUNT(*)                                                              AS n_test,
  ROUND(AVG(IF(ABS(pred-actual)/actual<=0.10,1,0)),4)                   AS hit10,   -- 主指標
  ROUND(AVG(IF(ABS(pred-actual)/actual<=0.20,1,0)),4)                   AS hit20,
  ROUND(APPROX_QUANTILES(ABS(pred-actual)/actual,100)[OFFSET(50)],4)    AS mdape,
  ROUND(AVG(ABS(pred-actual)),0)                                        AS mae_yen_per_sqm,
  ROUND(SQRT(AVG(POW(pred-actual,2))),0)                                AS rmse_yen_per_sqm,
  ROUND(AVG((pred-actual)/actual),4)                                    AS signed_bias_mean,   -- 負=過小予測（値上がり取りこぼし）
  ROUND(APPROX_QUANTILES((pred-actual)/actual,100)[OFFSET(50)],4)       AS signed_bias_median,
  -- (b)後段キャリブレーション倍率。平均バイアスを消す正しい係数は「平均の比」SUM/SUM。
  --   ※これは診断値。本番係数は 2025 から作らず Fold B / 訓練トレンドから決める（リーク防止）。
  ROUND(SUM(actual)/SUM(pred),4)                                        AS calib_sumratio,
  ROUND(APPROX_QUANTILES(actual/pred,100)[OFFSET(50)],4)                AS calib_medianratio
FROM preds
GROUP BY model_label, ord
ORDER BY ord;


-- ============================================================================
-- ブロック2: Fold A/B 安定性（採用候補 Model C）
--   同特徴量・同手法を Fold A(テスト2025) と Fold B(テスト2024) で比較。指標が大崩れしないか。
-- ============================================================================
WITH
p_ca AS (
  SELECT split, price_per_sqm, predicted_log_price_per_sqm AS plog
  FROM ML.PREDICT(MODEL `osaka-fudosan-dataanalysis.osaka_real_estate.model_c`,
    (SELECT * FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
     WHERE fold='A' AND model_eligible))
),
p_cb AS (
  SELECT split, price_per_sqm, predicted_log_price_per_sqm AS plog
  FROM ML.PREDICT(MODEL `osaka-fudosan-dataanalysis.osaka_real_estate.model_c_foldb`,
    (SELECT * FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
     WHERE fold='B' AND model_eligible))
),
preds AS (
  SELECT 'Fold A (訓練21-24/テスト2025)' AS fold_label, 1 AS ord, price_per_sqm AS actual,
         EXP(plog)*(SELECT AVG(EXP(LN(price_per_sqm)-plog)) FROM p_ca WHERE split='train') AS pred
  FROM p_ca WHERE split='test'
  UNION ALL
  SELECT 'Fold B (訓練21-23/テスト2024)', 2, price_per_sqm,
         EXP(plog)*(SELECT AVG(EXP(LN(price_per_sqm)-plog)) FROM p_cb WHERE split='train')
  FROM p_cb WHERE split='test'
)
SELECT
  fold_label,
  COUNT(*)                                                           AS n_test,
  ROUND(AVG(IF(ABS(pred-actual)/actual<=0.10,1,0)),4)               AS hit10,
  ROUND(AVG(IF(ABS(pred-actual)/actual<=0.20,1,0)),4)               AS hit20,
  ROUND(APPROX_QUANTILES(ABS(pred-actual)/actual,100)[OFFSET(50)],4) AS mdape,
  ROUND(AVG(ABS(pred-actual)),0)                                     AS mae_yen_per_sqm,
  ROUND(AVG((pred-actual)/actual),4)                                AS signed_bias_mean
FROM preds
GROUP BY fold_label, ord
ORDER BY ord;


-- ============================================================================
-- ブロック3: 残差診断（Model C・Fold A テスト2025）築年帯・徒歩帯・面積帯・区
--   系統パターンの有無（対策6=線形の取りこぼし、対策3=小型住戸の誤差床）を確認。
--   smearing は Model C 訓練残差から算出した固定係数を各帯に適用。
-- ============================================================================
WITH
p_c AS (
  SELECT split, price_per_sqm,
         building_age_years, walk_minutes, area_sqm, ward,
         predicted_log_price_per_sqm AS plog
  FROM ML.PREDICT(MODEL `osaka-fudosan-dataanalysis.osaka_real_estate.model_c`,
    (SELECT * FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
     WHERE fold='A' AND model_eligible))
),
sm AS (SELECT AVG(EXP(LN(price_per_sqm)-plog)) s FROM p_c WHERE split='train'),
test AS (
  SELECT price_per_sqm AS actual,
         EXP(plog)*(SELECT s FROM sm) AS pred,
         building_age_years, walk_minutes, area_sqm, ward
  FROM p_c WHERE split='test'
)
-- 3a) 面積帯別
SELECT '面積帯' AS dim,
  CASE WHEN area_sqm<30 THEN '20-30㎡' WHEN area_sqm<40 THEN '30-40㎡'
       WHEN area_sqm<50 THEN '40-50㎡' ELSE '50-60㎡' END AS bucket,
  COUNT(*) AS n,
  ROUND(AVG(IF(ABS(pred-actual)/actual<=0.10,1,0)),4) AS hit10,
  ROUND(APPROX_QUANTILES(ABS(pred-actual)/actual,100)[OFFSET(50)],4) AS mdape,
  ROUND(AVG((pred-actual)/actual),4) AS signed_bias_mean
FROM test GROUP BY bucket
UNION ALL
-- 3b) 築年帯別
SELECT '築年帯',
  CASE WHEN building_age_years<10 THEN '0-10年' WHEN building_age_years<20 THEN '10-20年'
       WHEN building_age_years<30 THEN '20-30年' WHEN building_age_years<40 THEN '30-40年'
       ELSE '40年以上' END,
  COUNT(*),
  ROUND(AVG(IF(ABS(pred-actual)/actual<=0.10,1,0)),4),
  ROUND(APPROX_QUANTILES(ABS(pred-actual)/actual,100)[OFFSET(50)],4),
  ROUND(AVG((pred-actual)/actual),4)
FROM test GROUP BY 2
UNION ALL
-- 3c) 徒歩帯別
SELECT '徒歩帯',
  CASE WHEN walk_minutes<=5 THEN '0-5分' WHEN walk_minutes<=10 THEN '6-10分'
       WHEN walk_minutes<=15 THEN '11-15分' ELSE '16-20分' END,
  COUNT(*),
  ROUND(AVG(IF(ABS(pred-actual)/actual<=0.10,1,0)),4),
  ROUND(APPROX_QUANTILES(ABS(pred-actual)/actual,100)[OFFSET(50)],4),
  ROUND(AVG((pred-actual)/actual),4)
FROM test GROUP BY 2
ORDER BY dim, bucket;


-- ============================================================================
-- ブロック4: 区別の残差（Model C・Fold A テスト2025）上位の系統ズレを確認
-- ============================================================================
WITH
p_c AS (
  SELECT split, price_per_sqm, ward, predicted_log_price_per_sqm AS plog
  FROM ML.PREDICT(MODEL `osaka-fudosan-dataanalysis.osaka_real_estate.model_c`,
    (SELECT * FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
     WHERE fold='A' AND model_eligible))
),
sm AS (SELECT AVG(EXP(LN(price_per_sqm)-plog)) s FROM p_c WHERE split='train'),
test AS (
  SELECT ward, price_per_sqm AS actual, EXP(plog)*(SELECT s FROM sm) AS pred
  FROM p_c WHERE split='test'
)
SELECT
  ward,
  COUNT(*) AS n,
  ROUND(AVG(IF(ABS(pred-actual)/actual<=0.10,1,0)),4) AS hit10,
  ROUND(AVG((pred-actual)/actual),4) AS signed_bias_mean   -- 区ごとの系統ズレ
FROM test
GROUP BY ward
HAVING n >= 20
ORDER BY signed_bias_mean;
