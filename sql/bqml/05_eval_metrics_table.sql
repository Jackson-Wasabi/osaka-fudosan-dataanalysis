-- 画面4(Tableau)用: モデル評価指標テーブル（実モデルから再現可能に算出）
-- 出典: フェーズ2 02_evaluate.sql ブロック1と同一ロジックを CREATE TABLE で materialize。
--   手打ちでなく ML.PREDICT の実測から計算するため再現性・監査性がある。
-- 母集団: Fold A・split='test'(2025)・model_eligible。smearing補正で円/㎡へ逆変換。
-- 主指標 hit10=±10%以内的中率。signed_bias=符号付相対誤差平均（負=過小予測）。
CREATE OR REPLACE TABLE `osaka-fudosan-dataanalysis.osaka_real_estate.model_eval_metrics` AS
WITH
p_a AS (SELECT split, price_per_sqm, predicted_log_price_per_sqm AS plog
  FROM ML.PREDICT(MODEL `osaka-fudosan-dataanalysis.osaka_real_estate.model_a`,
    (SELECT * FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price` WHERE fold='A' AND model_eligible))),
p_b AS (SELECT split, price_per_sqm, predicted_log_price_per_sqm AS plog
  FROM ML.PREDICT(MODEL `osaka-fudosan-dataanalysis.osaka_real_estate.model_b`,
    (SELECT * FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price` WHERE fold='A' AND model_eligible))),
p_c AS (SELECT split, price_per_sqm, predicted_log_price_per_sqm AS plog
  FROM ML.PREDICT(MODEL `osaka-fudosan-dataanalysis.osaka_real_estate.model_c`,
    (SELECT * FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price` WHERE fold='A' AND model_eligible))),
p_d AS (SELECT split, price_per_sqm, predicted_log_price_per_sqm AS plog
  FROM ML.PREDICT(MODEL `osaka-fudosan-dataanalysis.osaka_real_estate.model_d`,
    (SELECT * FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price` WHERE fold='A' AND model_eligible))),
p_e AS (SELECT split, price_per_sqm, predicted_log_price_per_sqm AS plog
  FROM ML.PREDICT(MODEL `osaka-fudosan-dataanalysis.osaka_real_estate.model_e_tree`,
    (SELECT * FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price` WHERE fold='A' AND model_eligible))),
p_f AS (SELECT split, price_per_sqm, predicted_log_price_per_sqm AS plog
  FROM ML.PREDICT(MODEL `osaka-fudosan-dataanalysis.osaka_real_estate.model_f_time`,
    (SELECT *, (trade_year-2021) AS time_index FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price` WHERE fold='A' AND model_eligible))),
sm AS (
  SELECT 'A' m, AVG(EXP(LN(price_per_sqm)-plog)) s FROM p_a WHERE split='train'
  UNION ALL SELECT 'B', AVG(EXP(LN(price_per_sqm)-plog)) FROM p_b WHERE split='train'
  UNION ALL SELECT 'C', AVG(EXP(LN(price_per_sqm)-plog)) FROM p_c WHERE split='train'
  UNION ALL SELECT 'D', AVG(EXP(LN(price_per_sqm)-plog)) FROM p_d WHERE split='train'
  UNION ALL SELECT 'E', AVG(EXP(LN(price_per_sqm)-plog)) FROM p_e WHERE split='train'
  UNION ALL SELECT 'F', AVG(EXP(LN(price_per_sqm)-plog)) FROM p_f WHERE split='train'
),
preds AS (
  SELECT 1 ord, 'Model A(面積+築年+徒歩)' model_label, price_per_sqm actual, EXP(plog)*(SELECT s FROM sm WHERE m='A') pred FROM p_a WHERE split='test'
  UNION ALL SELECT 2, 'Model B(A+改装+新耐震)', price_per_sqm, EXP(plog)*(SELECT s FROM sm WHERE m='B') FROM p_b WHERE split='test'
  UNION ALL SELECT 3, 'Model C(B+駅中央値)', price_per_sqm, EXP(plog)*(SELECT s FROM sm WHERE m='C') FROM p_c WHERE split='test'
  UNION ALL SELECT 4, 'Model D(C+公示価格)', price_per_sqm, EXP(plog)*(SELECT s FROM sm WHERE m='D') FROM p_d WHERE split='test'
  UNION ALL SELECT 5, 'Model E_tree(木)', price_per_sqm, EXP(plog)*(SELECT s FROM sm WHERE m='E') FROM p_e WHERE split='test'
  UNION ALL SELECT 6, 'Model F_time(C+時点)', price_per_sqm, EXP(plog)*(SELECT s FROM sm WHERE m='F') FROM p_f WHERE split='test'
  UNION ALL SELECT 0, 'Baseline(駅中央値)', price_per_sqm, station_median_price_per_sqm
    FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
    WHERE fold='A' AND split='test' AND model_eligible AND station_median_price_per_sqm IS NOT NULL
)
SELECT
  ord,
  model_label,
  (model_label LIKE 'Model C%') AS adopted,
  COUNT(*) AS n_test,
  ROUND(AVG(IF(ABS(pred-actual)/actual<=0.10,1,0)),4) AS hit10,
  ROUND(AVG(IF(ABS(pred-actual)/actual<=0.20,1,0)),4) AS hit20,
  ROUND(APPROX_QUANTILES(ABS(pred-actual)/actual,100)[OFFSET(50)],4) AS mdape,
  ROUND(AVG(ABS(pred-actual)),0) AS mae,
  ROUND(SQRT(AVG(POW(pred-actual,2))),0) AS rmse,
  ROUND(AVG((pred-actual)/actual),4) AS signed_bias
FROM preds
GROUP BY ord, model_label
ORDER BY ord;
