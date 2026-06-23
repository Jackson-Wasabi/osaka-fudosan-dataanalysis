-- Step 10 フェーズ1: 予測㎡単価モデルの作成（BQML）
-- 目的変数: log_price_per_sqm / 学習: model_eligible AND split='train'（Fold毎）
-- 線形は軽いL2(0.01)。BQMLは数値特徴量を自動標準化（係数比較の公平性）。data_split=NO_SPLIT（分割は自前のsplitで管理）。
-- 時点トレンドはリーク防止のため Model F（時点インデックス=trade_year-2021）で訓練から学習し2025へ外挿。
-- Baseline（駅中央値をそのまま予測値に）はモデル不要のため evaluate 側でSQL計算する。
-- 区切りは見出しコメント行。対象表: `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`

-- ==== model_a ====
CREATE OR REPLACE MODEL `osaka-fudosan-dataanalysis.osaka_real_estate.model_a`
OPTIONS(model_type='LINEAR_REG', input_label_cols=['log_price_per_sqm'],
        data_split_method='NO_SPLIT', l2_reg=0.01) AS
SELECT log_price_per_sqm, area_sqm, building_age_years, walk_minutes
FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
WHERE fold='A' AND split='train' AND model_eligible;

-- ==== model_b ====
CREATE OR REPLACE MODEL `osaka-fudosan-dataanalysis.osaka_real_estate.model_b`
OPTIONS(model_type='LINEAR_REG', input_label_cols=['log_price_per_sqm'],
        data_split_method='NO_SPLIT', l2_reg=0.01) AS
SELECT log_price_per_sqm, area_sqm, building_age_years, walk_minutes,
       renovation_done_flag, seismic_new
FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
WHERE fold='A' AND split='train' AND model_eligible;

-- ==== model_c ====
CREATE OR REPLACE MODEL `osaka-fudosan-dataanalysis.osaka_real_estate.model_c`
OPTIONS(model_type='LINEAR_REG', input_label_cols=['log_price_per_sqm'],
        data_split_method='NO_SPLIT', l2_reg=0.01) AS
SELECT log_price_per_sqm, area_sqm, building_age_years, walk_minutes,
       renovation_done_flag, seismic_new, station_median_price_per_sqm
FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
WHERE fold='A' AND split='train' AND model_eligible;

-- ==== model_d ====
CREATE OR REPLACE MODEL `osaka-fudosan-dataanalysis.osaka_real_estate.model_d`
OPTIONS(model_type='LINEAR_REG', input_label_cols=['log_price_per_sqm'],
        data_split_method='NO_SPLIT', l2_reg=0.01) AS
SELECT log_price_per_sqm, area_sqm, building_age_years, walk_minutes,
       renovation_done_flag, seismic_new, station_median_price_per_sqm,
       nearest_land_price
FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
WHERE fold='A' AND split='train' AND model_eligible;

-- ==== model_e_tree ====
CREATE OR REPLACE MODEL `osaka-fudosan-dataanalysis.osaka_real_estate.model_e_tree`
OPTIONS(model_type='BOOSTED_TREE_REGRESSOR', input_label_cols=['log_price_per_sqm'],
        data_split_method='NO_SPLIT', max_iterations=30, learn_rate=0.1, subsample=0.85) AS
SELECT log_price_per_sqm, area_sqm, building_age_years, walk_minutes,
       renovation_done_flag, seismic_new, station_median_price_per_sqm
FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
WHERE fold='A' AND split='train' AND model_eligible;

-- ==== model_f_time ====
CREATE OR REPLACE MODEL `osaka-fudosan-dataanalysis.osaka_real_estate.model_f_time`
OPTIONS(model_type='LINEAR_REG', input_label_cols=['log_price_per_sqm'],
        data_split_method='NO_SPLIT', l2_reg=0.01) AS
SELECT log_price_per_sqm, area_sqm, building_age_years, walk_minutes,
       renovation_done_flag, seismic_new, station_median_price_per_sqm,
       (trade_year - 2021) AS time_index
FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
WHERE fold='A' AND split='train' AND model_eligible;

-- ==== model_c_foldb ====
CREATE OR REPLACE MODEL `osaka-fudosan-dataanalysis.osaka_real_estate.model_c_foldb`
OPTIONS(model_type='LINEAR_REG', input_label_cols=['log_price_per_sqm'],
        data_split_method='NO_SPLIT', l2_reg=0.01) AS
SELECT log_price_per_sqm, area_sqm, building_age_years, walk_minutes,
       renovation_done_flag, seismic_new, station_median_price_per_sqm
FROM `osaka-fudosan-dataanalysis.osaka_real_estate_marts.mart_condo_price`
WHERE fold='B' AND split='train' AND model_eligible;
