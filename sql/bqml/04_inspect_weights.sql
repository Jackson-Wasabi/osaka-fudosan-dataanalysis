-- Step 10 補遺: 採用モデル(Model C)の係数確認（PART 15-6・読み取りのみ）
-- 目的: 「徒歩分が増えると下がる」等の符号と、標準化した影響度を実係数で説明できるようにする。
-- 注意: log_price_per_sqm を目的変数に学習しているため、係数は log スケールへの寄与。
--   重要なのは符号と相対的な大きさ（standardized）であり、円/㎡への直訳ではない。

-- 1) 生の係数（符号と大きさ）。BQMLは数値特徴を内部標準化するため weight は標準化寄与に近い。
SELECT
  processed_input AS feature,
  ROUND(weight, 5) AS weight
FROM ML.WEIGHTS(MODEL `osaka-fudosan-dataanalysis.osaka_real_estate.model_c`, STRUCT(true AS standardize))
ORDER BY ABS(weight) DESC;
