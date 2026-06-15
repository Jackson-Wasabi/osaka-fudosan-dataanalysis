# 作業ログ (work_log)

## 2026-06-15 — Step 10 事前レビュー（モデル設計の懸念点と対策を文書化）

- 実装前に、予測㎡単価モデル計画を実務レビュー。7つの懸念点（①市場値上がり未反映 ②ログ逆変換の下振れ ③面積5㎡丸め×小型 ④駅中央値の循環性 ⑤MAPE偏重 ⑥線形の取りこぼし ⑦2025報告ラグ）と各対策を `docs/step10_model_plan.md` に記録。
- 方針: 精度追求より「弱点を明示し相対ランキングの頑健性を主張」。測ってから設計を決める（フェーズ0診断→1作成→2評価→3予測）。
- 未実装（SQLはまだ作成していない）。次はフェーズ0（2025四半期件数・年次値上がり率・面積帯件数）から。

## 2026-06-15 — Step 9: mart_condo_price 構築（分析完成テーブル）

- mart_condo_price（materialized: table・13,718行=両Fold）作成。intermediate を整形し正規の列名で公開。
  - 予測特徴量は補完済みの値を正規名（building_age_years/walk_minutes）で公開、スコア用項目（公示価格・駅件数/IQR・renovation_unknown・seismic_old_flag）は分離（v9核心）
  - 両Fold保持＋fold/split列（Tableauはfold='A'。PART17のFold横断比較対応）
  - 目的変数 log_price_per_sqm を追加（BQML用）
- staging小修正: stg_transactions に potential_dup_flag を追加（D-005の実装漏れを補完。Fold A 182件）
- D-017反映: 新規出現駅（駅中央値NULL）は station_history_missing=TRUE / model_eligible=FALSE で識別し、モデル・予測・ランキングから除外（martには残す）。Fold A test 9件・Fold B test 8件
- 検証: **model_eligible行 13,701件で予測特徴量NULL=0**・log_price_per_sqm NULL=0・Fold/split件数整合（A:5,806+2,106 / B:4,201+1,605）
- 失敗と修正: mart で trade_price 列名誤り→ stg の列名 price に修正
- dbt run PASS=8 / dbt test 実行
- 次: Step 10 モデル（中央値ベースライン + BQML、PART17のBaseline〜Model D比較・Fold A本番/Fold B検証）

## 2026-06-15 — 整合性監査と耐震フラグの矛盾修正

- 目的（割安候補抽出＋スコアリング）に対しデータ補正が一貫しているか監査。最終テーブル46列を確認し、予測特徴量とスコア用項目の分離・リーク防止・層構造・限界明示が一貫していることを確認。
- 検出した唯一の論理矛盾: 耐震フラグの二重定義（補完で旧耐震化した9行が seismic_new=0 かつ seismic_old_flag=0）。
- 修正（D-020）: seismic_old_flag を staging から削除し、intermediate で seismic_new と相補的に補完後築年から算出。検証で矛盾0行（seismic_new+seismic_old_flag=1）、補完由来の旧耐震18行は is_imputed_building_age で区別可能。dbt run PASS=7 / dbt test PASS=21。
- 軽微: D-011 本文に実装後の数値（scope7,912/complete-case7,796/126駅）の注記を追加。
- 残課題（Step 9へ）: D-017 新規出現駅の駅中央値NULL（A:9/B:8）の扱い。モデルは imputed_* と seismic_new/seismic_old_flag を使う。

## 2026-06-15 — Step 8: 欠損値の補完（Fold対応・リーク防止・列ごとに理由のある方法）

- 方針（D-018/D-019）: 一律中央値でなく列ごとに最適な方法。補完中央値は当該Foldの訓練期間のみから算出（PERCENTILE_CONT(IF(split='train',...))）。
  - 築年数: 駅→区→全体の中央値 + is_imputed_building_age（欠損は全て真の不明＝戦前0件を確認）
  - 徒歩分: 駅→区の中央値 + is_imputed_walk_minutes（駅×面積帯は根拠薄で不採用）
  - 公示価格: int_station_land_price_features の対象を全取引駅に拡大し実計算（4駅の欠損解消）。補完は座標無し時のみ（実績0）
  - seismic_new を補完後築年数から再計算
- stg_transactions: scope を「徒歩・築年の欠損は駅があれば対象に含め補完／駅名欠損は除外（station_missing）」に変更
  - 不具合検出と修正: 当初 scope を欠損許容にしたら駅名空欄314行が混入し駅中央値・地価がNULLに → 駅名必須化で解消（D-019・errors_and_fixes）
- 検証（scripts/verify_intermediate.py + アドホック）:
  - scope_true=**7,912**（complete-case 7,796 + 補完対象116）・駅名空欄の混入0
  - 駅結合率 **100%**・補完後の築年/徒歩NULL=0・地価補完0（全て実値）
  - 補完値は範囲内（築5-58年・徒歩1-20分）・補完件数 築56/徒歩60
  - 駅中央値NULL（新規出現駅）Fold A test9/Fold B test8（D-017・要Step9対応）
- **dbt run PASS=7 / dbt test PASS=21**（補完列のnot_null 4件追加）
- 次: Step 9 mart。D-017（テスト期間の駅中央値NULL）の扱いを決める

## 2026-06-15 — Step 8: intermediate 構築（駅特徴量・地価特徴量・物件結合）

- 作成モデル（dbt/models/intermediate/・全 view）:
  - `int_station_geo`: 駅名→代表座標・代表路線。大阪府bbox限定で同名駅の全国平均ズレを防ぐ共通テーブル（D-016）
  - `int_station_market_features`（駅×Fold）: 取引件数・中央値㎡単価・IQR・平均徒歩・改装率を各Foldの訓練期間のみで算出（D-012=D-009の具体化）
  - `int_station_land_price_features`（駅）: 最寄り公示価格・対前年変動率・距離を ST_DISTANCE 最近傍結合
  - `int_transactions_with_station_features`（物件×Fold）: 上記を結合した mart/BQML 用の行レベルテーブル
- 前提整備（staging補修）: マクロ `normalize_station_name` 新設、stg_transactions に正規化駅名 `station_name` 追加、stg_station_master をマクロ化（D-013）
- **検出・修正したバグ**: ①scope_flag の NULL 誤判定（8,226→7,796 に是正・D-014）②stg_land_price の市フィルタ列違い（0件→574地点・D-015）③地価距離の同名駅平均ズレ（中央値328km→242m・D-016）。詳細は errors_and_fixes.md
- 検証結果（Python BigQuery クライアント / scripts/verify_intermediate.py）:
  - stg_transactions: 大阪市24,613行・scope_true **7,796**（D-011一致）・駅名空欄1.91%
  - 駅結合率 **100%**（scope内）・geo NULL 0
  - Fold A train5,725/test2,071=7,796、Fold B train4,142/test1,583
  - 地価: 175駅・距離 min32m/中央値242m/最大5.5km/1000m超4駅・NULL0
  - 新規出現駅でテスト期間の特徴量NULL 9件(0.4%)は既知の限界（D-017）
- **dbt test: PASS=17 / FAIL=0 / ERROR=0**
- 接続: gcloud ハングのため ADCコピー + GOOGLE_CLOUD_PROJECT 指定で実行（errors_and_fixes.md）
- 次にやること: Step 9 mart（mart_condo_price / mart_opportunity_list）。D-017のテスト期間特徴量NULLの扱いを決める

## 2026-06-12 — Step 7: dbt staging 構築（型変換・正規化・スコープ判定）

- 作成モデル: stg_transactions（大阪市24,613行・型変換・D-002/007/008フラグ・scope_flag/excluded_reason）、stg_station_master（D-006正規化）、stg_land_price（公示価格）。BigQuery にview作成・コミット済み（ce88573, 9758c14）
- 注: 当時 scope_flag のNULL扱いと stg_land_price の市フィルタにバグが残存（Step 8 検証で発見し D-014/D-015 で修正）

## 2026-06-12 — Step 6: 分析条件の確定（D-011）

- 10_eda_scope_preview.sql のファネルで件数を確認し、分析スコープを確定: **大阪市・面積20-60㎡・徒歩20分以内・築5-60年・価格500万円以上（上限なし）= 7,796件・駅別10件以上が134駅（生駅名ベース）**。判断根拠は decision_log D-011

## 2026-06-12 — Step 5 改訂: EDA を大阪市スコープで再実行（ユーザー指摘 D-010）

- 指摘: 「分析対象は大阪市なのに府全体で外れ値を見ても閾値の意思決定に使えない」→ 正しいので大阪市版を正式版として全面再実行
- run_eda.py に大阪市フィルターを実装（検査02-09 = 大阪市24,613行。検査10のみ府全体からの絞り込みファネル）
- グラフ9枚・レポートを大阪市版で再生成（タイトルに「大阪市」明記）。キャプション重なりも修正済み
- **府全体と大阪市の差が実証された**: ㎡単価P99は府全体158万 → 大阪市186万円/m2、中央値38.8万 → 50万円/m2。府全体の閾値を使っていたら大阪市の正常な高額物件を外れ値扱いするところだった
- 駅名結合（大阪市）: 208駅名中、正規化後201駅一致・行ベース96.6%。**不一致は7駅名のみ**（四天王寺前夕陽ケ丘287行・ＪＲ難波163・なんば119・あびこ113・鶴ケ丘56・ＪＲ淡路43・ＪＲ野江42）= mapping CSV は7行で済む見込み
- 府全体版の数値は本エントリより下の旧記録に残置（形式チェックの証跡として有効）

## 2026-06-12 — Step 5: EDA 実行（読み取り専用）

- scripts/run_eda.py で一括実行（SQL書き出し→BQ実行→CSV→グラフ→レポートの単一スクリプト = SQLとグラフの連携保証）
- 生成物: sql/checks/02〜10（9本）/ outputs/tables/*.csv（9個）/ outputs/figures/*.png（9枚・結論タイトル+出典キャプション付き）/ docs/eda_report.md（決定事項サマリー+SQL+グラフ+所見+現物5件）
- 主要結果:
  - ㎡単価: 中央値38.8万円/m2、P99=158万円/m2、最大965万円/m2
  - 価格: 中央値2,600万円、P99=1.3億円、最大8.2億円 / 面積: P99=115m2、最大1,960m2
  - 築年数に負値あり（min=-2、建築年>取引年）= D-008 新発見
  - 駅名結合率: 生名一致 362/443駅 → 正規化後 429/443駅、行ベース97.3%。不一致はケ/ヶ・全角ＪＲ・メトロひらがな駅名（D-006）
  - 期間欠落なし、2024年以降件数増
  - 手順書推奨条件適用後: 5,392件・107駅（10件以上）= Step 6 の判断材料
- 判断提案 D-001〜D-008 を decision_log に記録（すべて提案中、Step 6/7 で承認後に確定）
- BigQuery への書き込みなし

## 2026-06-12 — データ辞書作成・BQ列に日本語説明を設定

- `docs/data_dictionary.md` 作成: raw 3種のカラム日本語対応表（国土数値情報の公式属性定義ページ・実データ値と突合して作成。推測なし）
- 重要発見: L01_008=公示価格(円/㎡)、**L01_009=対前年変動率(%)** → land_price_change_rate が年次間結合なしで取得可能
- `scripts/add_column_descriptions.py`: BQ全5テーブルの列スキーマに日本語 description を設定（データ・型・列順は無変更）。raw_transactions 21/21列で反映確認済み

## 2026-06-12 — raw 再ロードと「列と値の対応」検証完了

### 経緯
- データセット `osaka_real_estate` が削除されていることを検知（プロジェクトは健在）→ ユーザー指示により再作成・再ロード
- sql/checks/01_raw_load_validation.sql も消失していたため再作成（未コミットだったため git から復元不可。以後は作成都度コミットを検討）

### 再ロード結果（全9ロード成功・内容無加工）
- raw_transactions 47,386 / raw_station_master_2024 10,235 / _2025 10,234 / raw_land_price_2024 1,715 / _2025 1,687 — すべてソースと一致

### 列と値の対応検証（カラムシフト検出）
- raw_transactions: 13項目のドメイン検査（種類・区分・市区町村コード・都道府県・徒歩分・価格・面積・建築年・構造・取引時期・改装 等）**すべて0件 = 列ズレなし**
- 改装列の実値域は「改装済み」(2,512件) と空欄 (44,874件) のみで「未改装」は存在しない → 空欄は未改装/不明の区別不能（renovation_unknown_flag 設計に反映する）
- GIS: ソースCSVとBQで 行数・路線数(552)・事業者数(176)・駅名数(8,503)・座標合計値が完全一致（station_master_2025）、地価も同様に一致（land_price_2025）
- 教訓: bq へ日本語を含むクエリを stdin で渡すと cp932 誤変換でリテラルが壊れる → **PYTHONUTF8=1 + 引数渡し**で解決（errors_and_fixes 参照）

## 2026-06-12 — Step 3〜4: 投入前確認・BigQuery raw 投入

### Step 3 投入前確認（scripts/precheck_transactions.py）
- ヘッダー: 5年分とも21列で完全一致
- 空文字率: 取引価格・面積・間取り 0% / 最寄駅名 0.3〜2.9% / 徒歩分 6.0〜8.8% / 建築年 0.2〜2.8% / **改装 94.1〜95.8%**（renovation_unknown_flag 設計の妥当性を裏付け）
- 特殊値: 徒歩分に範囲表記47件（「30分～60分」44、「1H30～2H」2、「1H～1H30」1）。面積・建築年・価格の非数値は0件
- 完全重複行: 2021:56 / 2022:46 / 2023:68 / 2024:60 / 2025:100（計330行。staging で重複の扱いを決定する）

### GIS 変換（scripts/gis_to_csv.py）
- ZIP展開: N02-24/25、L01-24/25 → data/gis/raw/ 配下（ZIP原本保持）
- GeoJSON→CSV（属性値は無変更、ジオメトリから lon/lat のみ算出）→ data/gis/processed/
  - station_master_2024.csv: 10,235行（全国） / station_master_2025.csv: 10,234行
  - land_price_2024.csv: 1,715行×146列 / land_price_2025.csv: 1,687行×148列（大阪府）

### BigQuery 投入
- GCPプロジェクト新規作成: `osaka-fudosan-dataanalysis`（課金は旧プロジェクトと同一アカウントに紐付け）
- データセット: `osaka_real_estate`（asia-northeast1）
- ロード（全列STRING・as-is・ヘッダースキップ。成約CSVはcp932→UTF-8変換コピーを使用、rawファイルは無変更）:

| テーブル | 行数 | ソースとの一致 |
|---|---|---|
| raw_transactions（2021〜2025の5ファイル追記） | 47,386 | 一致 |
| raw_station_master_2024 / _2025 | 10,235 / 10,234 | 一致 |
| raw_land_price_2024 / _2025 | 1,715 / 1,687 | 一致 |

### 投入後検証
- 件数: 全テーブルでソースCSVと完全一致
- raw_transactions: 価格 min 100万円〜max 8.2億円（外れ値候補は Step 5 EDA で分類）、面積 15〜1,960㎡、年別の空欄数は投入前確認と整合
- 駅: 駅名空欄0・座標NULL0・経緯度は日本全域の範囲内
- 地価: 座標は大阪府の範囲内（lon 135.1〜135.7 / lat 34.3〜35.0）

### 次にやること
- Step 5: EDA・外れ値確認（sql/checks/ に確認SQLを作成）

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
