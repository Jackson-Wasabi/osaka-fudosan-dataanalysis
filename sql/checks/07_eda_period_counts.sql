-- 07_eda_period_counts.sql
-- 生成元: scripts/run_eda.py（編集はスクリプト側で行うこと）
-- 読み取り専用 / 入力: raw_* / データ取得日: 2026-06-12 / 対象スコープ: 大阪市・中古マンション等・成約価格情報 2021Q1-2025Q4（24,613行）。raw全体は大阪府47,386行で、形式チェックは府全体で実施済み（D-010）
SELECT
  SUBSTR(trade_period, 1, 4) AS yr,
  REGEXP_EXTRACT(trade_period, r'第([1-4])') AS qtr,
  COUNT(*) AS cnt
FROM `osaka_real_estate.raw_transactions`
WHERE STARTS_WITH(city_name, '大阪市')
GROUP BY 1, 2 ORDER BY 1, 2
