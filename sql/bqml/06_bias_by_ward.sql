-- 画面4補強(Tableau)用: 区別の予測ズレ Model C vs Model F
-- 目的: 「Fは集計精度最良だが、周縁の区を構造的に過大予測（=偽の割安を量産）」を可視化し却下理由を証明。
-- 母集団: Fold A・split='test'(2025)・model_eligible。signed_bias=AVG((pred-actual)/actual)。
--   負=過小予測 / 正=過大予測（実勢が予測より安く見える=偽の割安）。
-- 出典: フェーズ4の残差診断ロジックを CREATE TABLE で再現（実測materialize）。
CREATE OR REPLACE TABLE `osaka-fudosan-dataanalysis.osaka_real_estate.model_bias_by_ward` AS
WITH
pc AS (SELECT ward, split, price_per_sqm, predicted_log_price_per_sqm AS plog
  FROM ML.PREDICT(MODEL `osaka-fudosan-dataanalysis.osaka_real_estate.model_c`,
    (SELECT * FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price` WHERE fold='A' AND model_eligible))),
pf AS (SELECT ward, split, price_per_sqm, predicted_log_price_per_sqm AS plog
  FROM ML.PREDICT(MODEL `osaka-fudosan-dataanalysis.osaka_real_estate.model_f_time`,
    (SELECT *, (trade_year-2021) AS time_index FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price` WHERE fold='A' AND model_eligible))),
smc AS (SELECT AVG(EXP(LN(price_per_sqm)-plog)) s FROM pc WHERE split='train'),
smf AS (SELECT AVG(EXP(LN(price_per_sqm)-plog)) s FROM pf WHERE split='train'),
bias_c AS (
  SELECT ward, 'Model C' AS model, COUNT(*) AS n,
    ROUND(AVG((EXP(plog)*(SELECT s FROM smc) - price_per_sqm)/price_per_sqm),4) AS signed_bias
  FROM pc WHERE split='test' GROUP BY ward),
bias_f AS (
  SELECT ward, 'Model F(時点項)' AS model, COUNT(*) AS n,
    ROUND(AVG((EXP(plog)*(SELECT s FROM smf) - price_per_sqm)/price_per_sqm),4) AS signed_bias
  FROM pf WHERE split='test' GROUP BY ward)
SELECT * FROM bias_c WHERE n >= 20
UNION ALL
SELECT * FROM bias_f WHERE n >= 20
ORDER BY ward, model;
