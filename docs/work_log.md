# 作業ログ (work_log)

## 2026-06-12 — data/samples: 公開用サンプル追加

- `data/samples/osaka_condo_seiyaku_sample.csv`: 2025年成約CSVの先頭10行（UTF-8変換）
- `data/samples/README.md`: 出典・取得条件・21カラムの説明・GISサンプルの追加予定を記載
- 判断: raw全体はコミットしない（成約価格情報の再配布規約が不明確なため）。構造理解用の少量抜粋＋出典明記＋スクリプトによる再現性で代替（decision_log 参照）

## 2026-06-12 — git リポジトリ初期化・初回コミット

- `git init -b main`（ローカルのみ。GitHub への push は Step 13 で実施）
- 取得スクリプト4件を `scripts/` へ移動して追跡対象に追加（extract_pdf.py / download_transactions.py / download_transactions_2025.py / verify_downloads.py）
- 空ディレクトリ14箇所に .gitkeep を追加。data/raw・data/gis/raw は中身を除外しつつ .gitkeep のみ追跡するよう .gitignore を調整
- ステージ内容を検証し、raw データ・認証情報が含まれないことを確認してからコミット
- 注意: scripts/download_transactions*.py に含まれる Ocp-Apim-Subscription-Key は、reinfolib サイトが全ブラウザ訪問者に配布しているフロントエンド公開キーであり、個人の認証情報ではない（GitHub 公開時に README でも明記予定）

## 2026-06-12 — クリーンアップ: 使い捨て調査ファイルの削除

- 削除（データ分析直下）: test_reinfo_api.py / test_reinfo_matrix.py / test_reinfo_browser.py / test_reinfo_browser2.py / test_reinfo_ui.py（reinfolib API調査用ワンショット。成果は download_transactions*.py と errors_and_fixes.md に反映済み）
- 削除（%TEMP%）: JSチャンク・検証レスポンス・スクショ等 26 件
- 保持: extract_pdf.py、manual_v9_extracted.txt、download_transactions.py、download_transactions_2025.py、verify_downloads.py（再取得・再現性の証跡）
- raw データ・旧プロジェクト・docs ログには未接触

## 2026-06-12 — Step 2: データ取得（ダウンロード）

### 実行した内容
- 国土数値情報（nlftp.mlit.go.jp）から直URLでGISデータ4ファイルを `data/gis/raw/` へ取得
- 不動産情報ライブラリ（reinfolib.mlit.go.jp）のWebサイト内部CSVダウンロードAPI（ブラウザのダウンロードボタンと同一の経路・同一の公開キー）で、成約価格CSVを年単位で `data/raw/` へ取得
  - 条件: 大阪府 / 中古マンション等 / 成約価格情報のみ / 各年第1〜第4四半期（旧作業と同一条件）
  - 統合せず年ごとに別ファイルのまま保存
- 取得スクリプト: `scripts/download_transactions.py`、`scripts/download_transactions_2025.py`、検証: `scripts/verify_downloads.py`（2026-06-12 git管理化に伴い scripts/ へ移動）

### 取得結果と検証（件数・内容・整合性）
| ファイル | データ行数 | 検証結果 |
|---|---|---|
| raw/osaka_condo_seiyaku_2020/Osaka Prefecture_20201_20204.csv | 0（ヘッダーのみ） | 成約価格情報の提供が2021年開始のため空。ファイルは証跡として保持 |
| raw/osaka_condo_seiyaku_2021/Osaka Prefecture_20211_20214.csv | 8,505 | 旧ファイルとMD5一致 |
| raw/osaka_condo_seiyaku_2022/Osaka Prefecture_20221_20224.csv | 9,107 | 旧ファイルと行集合完全一致（並び順のみ相違、MD5不一致は順序差） |
| raw/osaka_condo_seiyaku_2023/Osaka Prefecture_20231_20234.csv | 8,975 | 旧ファイルとMD5一致 |
| raw/osaka_condo_seiyaku_2024/Osaka Prefecture_20241_20244.csv | 9,705 | 旧ファイルとMD5一致 |
| raw/osaka_condo_seiyaku_2025/Osaka Prefecture_20251_20254.csv | 11,094 | 新規（2025Q1〜Q4、大容量のためサーバ返却URL経由で取得） |
| gis/raw/N02-24_GML.zip | 22エントリ | ZIP整合性OK・旧ファイルとMD5一致 |
| gis/raw/N02-25_GML.zip | 24エントリ | ZIP整合性OK（新規） |
| gis/raw/L01-24_27_GML.zip | 8エントリ | ZIP整合性OK・旧ファイルとMD5一致 |
| gis/raw/L01-25_27_GML.zip | 8エントリ | ZIP整合性OK（新規） |

- 全CSVで 種類=中古マンション等のみ / 価格情報区分=成約価格情報のみ / 都道府県=大阪府のみ / 四半期4区分そろい を確認
- 2021〜2025 合計データ行数: 47,386行（参考: 大阪市内行 2021:4,124 / 2022:4,529 / 2023:4,724 / 2024:5,200 / 2025:6,036）

### BigQuery で作成・変更したテーブル
- なし（Step 2 はローカル取得のみ）

### 失敗と修正
- reinfolib CSV APIの `kind` パラメータ形式誤りで500エラーが続いた（詳細は errors_and_fixes.md）

### 次にやること
- Step 3: 投入前確認（文字コード・カラム名・行数・NULL候補の確認計画）→ Step 4: BigQuery raw 投入

## 2026-06-12 — Step 1: 接続確認（読み取り専用）

### 確認結果
| ツール | 状態 | 詳細 |
|---|---|---|
| gcloud 認証 | OK | アカウント: ononoomichi@gmail.com (ACTIVE) |
| gcloud プロジェクト | OK | osaka-condo-analysis |
| bq | OK | データセット2件: `osaka_real_estate`, `osaka_real_estate_osaka_real_estate`（後者は旧作業の誤作成分。削除候補だが今回は触らない） |
| dbt | OK | dbt-core 1.11.11 / dbt-bigquery 1.9.0（Python 3.12 の dbt.exe） |
| profiles.yml | 注意 | `~/.dbt/` には無し。旧プロジェクト `osaka-condo-station-opportunity-analysis/dbt/profiles.yml` に存在（dbt実行時はプロジェクト内 dbt/ ディレクトリ参照だった模様） |
| git | OK | 2.54.0.windows.1 |
| gh (GitHub CLI) | 未インストール | GitHub 公開 Step までに導入要否を判断 |
| Tableau | 未確認 | CLI確認不可。接続時に BigQuery コネクタの認証方式と mart 読み取り権限を確認する |

### BigQuery で作成・変更したテーブル
- なし（一覧表示のみ）

### 次にやること
- Step 2: データ配置。旧プロジェクトの data/raw を新プロジェクトへコピーするか、BigQuery 上の既存 raw テーブルを再利用するかを決める

## 2026-06-12 — Step 0: プロジェクト作成

### 実行した内容
- 手順書 `osaka_fudosan_dataanalysis_manual_v9.pdf`（全24ページ）を読み込み（pypdf 6.13.2 をPython 3.12 にインストールしてテキスト抽出 → `../manual_v9_extracted.txt`）
- v9 のディレクトリ構成（PART 2）どおりにフォルダ17個を作成
  - data/{raw, gis/raw, gis/processed, samples}
  - dbt/models/{staging, intermediate, marts}
  - sql/{checks, bqml, ad_hoc}
  - tableau/{data_sources, dashboard_wireframes, screenshots}
  - docs, outputs/{figures, tables, reports}

### 作成したファイル
- CLAUDE.md（PART 3 の作業ルール + v9 特徴量/スコア分離ルール）
- .gitignore（data/raw・data/gis/raw・profiles.yml・認証情報を除外）
- profiles.example.yml（公開用サンプル。実認証情報なし）
- docs/work_log.md・docs/decision_log.md・docs/errors_and_fixes.md（本ファイル群）

### BigQuery で作成・変更したテーブル
- なし（Step 0 は BigQuery 操作なし）

### 確認した件数・NULL率・外れ値
- なし（データ未投入）

### 失敗と修正
- PDF を Read ツールで直接読めず（pdftoppm 不在）→ pypdf によるテキスト抽出で解決（詳細は errors_and_fixes.md）

### 次にやること
- Step 1: BigQuery / dbt / GitHub の接続確認（実行前に確認計画を提示する）
