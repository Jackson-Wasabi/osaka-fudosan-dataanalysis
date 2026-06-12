# Project Rules for Claude Code

プロジェクト: osaka-fudosan-dataanalysis（手順書 v9 準拠）
目的: 大阪市の中古マンション成約価格に駅情報と公示価格を組み合わせ、相場より割安に見える「追加調査候補」を抽出する一次スクリーニング。「買うべき物件」とは断定しない。公開データの限界を必ず明示する。

## 基本方針

- ユーザーが「実行して」と明示するまで、shell command / bq / dbt / git 操作は実行しない。
- まず必ず実行計画を出す。
- BigQuery 操作では、入力テーブル・出力テーブル・変更内容を説明する。
- raw テーブル、data/raw、data/gis/raw は上書き・削除しない。
- SELECT * を使う場合は必ず LIMIT 10 を付ける。
- 実行後は必ず件数確認、NULL率確認、最小値・最大値確認を行う。
- エラーが出たら、原因候補、確認コマンド、修正案、安全な再実行手順を出す。
- 作業結果は docs/work_log.md に日付付きで記録する。
- 判断理由は docs/decision_log.md に残す。
- エラーと修正内容は docs/errors_and_fixes.md に記録する。
- セクション（Step）ごとに 1 つずつ進め、一気に複数 Step を実行しない。

## dbt 方針

- staging: 型変換・表記ゆれ補正まで。
- intermediate: 結合・駅特徴量・地価特徴量を作る。
- marts: Tableau / BQML が読む完成テーブル。
- mart は「誰が見ても意味がわかる列名」にする。

## モデル/スコア設計（v9 の核心ルール）

- 予測㎡単価モデルに入れる特徴量: area_sqm, building_age_years, walk_minutes, renovation_done_flag, seismic_new (built_year >= 1982), station_median_price_per_sqm
- 予測モデルに入れない（スコア側で使う）:
  - 公示価格 (nearest_land_price 等) → 地価・エリア補足スコア（15点）
  - station_transaction_count, station_price_iqr → 市場信頼性スコア（25点）
  - renovation_unknown_flag → データ品質スコア（15点）・リスク減点
- 調査優先度スコア = 割安度45 + 市場信頼性25 + 地価補足15 + データ品質15 − リスク減点(最大20)、0〜100にクリップ。
- 改装済み = 耐震補強済みとは見なさない。旧耐震×改装状態の組み合わせはリスク減点。

## GitHub 公開ルール

- .env、認証情報、APIキー、data/raw、data/gis/raw、profiles.yml は絶対にコミットしない。
- 公開するのは SQL、dbt モデル、README、docs、公開可能なサンプル（data/samples）のみ。

## 参照

- 手順書: ../osaka_fudosan_dataanalysis_manual_v9.pdf（抽出テキスト: ../manual_v9_extracted.txt）
- 旧実装（参照のみ・変更禁止）: ../osaka-condo-station-opportunity-analysis/
