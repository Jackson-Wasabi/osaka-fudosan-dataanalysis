# エラーと修正の記録 (errors_and_fixes)

## 2026-06-15 — dbt / bq / gcloud が全て起動時に約30秒ハング（Step 8）

- **事象**: `dbt run` はおろか `dbt --version`（接続不要）すら90秒でタイムアウト。`bq query 'SELECT 1'` も同様にハング。一方 `python -c "import json"` や `import dbt.cli.main`(4.3s) は正常で、googleapis への素の HTTPS 接続も <1s で到達。
- **切り分け**: (1)ネットワーク正常 (2)dbtのインポートは4.3sで正常 → 実行時にハング。faulthandler でスタックを強制ダンプした結果、`google.auth.default()` → `google/auth/_cloud_sdk.py:106 get_project_id()` → `subprocess`(=`gcloud` 子プロセス起動)で停止と判明。`gcloud config get-value project`（ローカル操作のみ）単体でも30秒タイムアウト＝**根本原因は gcloud コマンド自体の起動ハング**。これが google.auth 経由で bq・dbt-bigquery 全てに波及していた。ロックファイル・滞留プロセスは無し。前日(2026-06-14 09:03)は正常稼働しており環境側の変化が原因。
- **回避策（採用）**: gcloud を呼ぶ経路（`_get_gcloud_sdk_credentials`）を通らないよう、ADC 本体 `%APPDATA%\gcloud\application_default_credentials.json` を中立な場所にコピーし、明示指定する。
  ```bash
  export GOOGLE_APPLICATION_CREDENTIALS=/tmp/adc.json          # ADCのコピーを直接指定
  export GOOGLE_CLOUD_PROJECT=osaka-fudosan-dataanalysis        # プロジェクトも環境変数で渡す
  export DO_NOT_TRACK=1                                         # 念のため匿名統計も無効
  ```
  これで `google.auth.default()` が **40秒→0.44秒**。dbt run / test / Python BigQuery クライアントが全て正常化。
- **副次対応**: `dbt_project.yml` に `flags: send_anonymous_usage_stats: false` を追加（統計送信のネットワーク待ちも予防）。検証クエリは `bq` を避け Python BigQuery クライアント（同じ環境変数）で実行（scripts/verify_intermediate.py）。
- **恒久対応の候補（未実施）**: gcloud の再ログイン/修復、または dbt を service-account keyfile 方式へ切替（gcloud 非依存）。今回は上記回避策で進行。
- **教訓**: 「dbtがハング」でも犯人はdbtとは限らない。インポート時間と実行時間を分け、スタックダンプで停止箇所を1点に特定すると、無関係な層（ここではgcloud）まで遡れる。

## 2026-06-15 — Step 8 検証で staging の2バグを検出（scope NULL誤判定 / 地価の市フィルタ列違い）

- **事象1（scope件数超過）**: stg_transactions の scope_flag が 8,226 件（D-011 確定値 7,796 と不一致・+430）。
- **原因1**: scope 判定が `CASE WHEN NOT (A AND B AND C ...) THEN FALSE ELSE TRUE` 形式で、walk/age/price に NULL があると内側が NULL → `NOT NULL`=NULL → WHEN 不一致 → `ELSE TRUE` に落ち、欠損行（築年数NULL 476件等）が誤って対象になった。
- **修正1**: `COALESCE(A AND B AND C AND price_per_sqm>=50000, FALSE)` に変更し NULL→FALSE を確定。excluded_reason も各列の `IS NULL OR ...` を明示。→ **7,796件で D-011 一致**。
- **事象2（地価0件）**: int_station_land_price_features が0行。
- **原因2**: stg_land_price の大阪市フィルタが `STARTS_WITH(L01_006,'大阪市')` だったが、実データの L01_006 は「前年連番」(001/000)で市名ではない（列の取り違え）。
- **修正2**: 行政区域コード `STARTS_WITH(L01_001,'271')`（大阪市24区）に変更。市区名は住所 `L01_025` から `REGEXP_EXTRACT(.. '大阪市.+?区')` で抽出。point_id は標準地番号 `L01_001_L01_002_L01_003` に。→ **574地点**取得。
- **事象3（地価距離が無意味）**: 修正2後、最寄り地価距離の中央値が328km。駅名のみの結合で全国同名駅（例「本町」）の座標まで平均し代表点が大阪外へずれていた。
- **修正3**: 共通テーブル int_station_geo を新設し、大阪府バウンディングボックス（lat34.2-35.1/lon135.0-135.8）に限定してから駅座標を集約。地価結合と物件結合の両方が参照（ロジック一元化）。→ 距離 **中央値242m・最大5.5km・1000m超4駅**に正常化。
- **教訓**: raw の列は名前(L01_xxx)だけで意味を推測せず、実値を必ず目視。空間結合は「名前一致」だけでなく「位置の妥当性（距離分布）」で検証する。

## 2026-06-12 — bq クエリの日本語リテラルが壊れ、検証が全件不一致に見えた

- **事象**: 列値検証SQLで日本語比較（kind != '中古マンション等' 等）が全行不一致。一方で数値系チェックは正常。
- **原因**: cmd の stdin リダイレクト経由で bq に渡した UTF-8 クエリを、Python(bq) が cp932 として誤デコードし、クエリ内の日本語リテラルだけが文字化けした。**データ自体は正常だった**。
- **修正**: `$env:PYTHONUTF8='1'` を設定し、クエリは stdin ではなく引数として渡す（Windows の引数は UTF-16 で受け渡されるため文字化けしない）。コメント行(`--`)はフラグ誤認を避けるため除去し、改行は空白に畳む。
- **教訓**: 「検証が失敗した＝データが悪い」とは限らない。検証系自体の検証（既知の正しい値での突合）を先に行う。

## 2026-06-12 — renovation 列の検証で偽陽性2,512件

- **事象**: renovation の値域チェック（'', '改装済', '未改装'）で2,512件が不一致。
- **原因**: 実データの表記は「改装済**み**」で、「未改装」は存在しなかった。検証条件側の想定誤り。
- **修正**: 値域を ('', '改装済み') に修正。空欄=未改装/不明の区別不能という発見は staging 設計（renovation_unknown_flag）に反映する。

## 2026-06-12 — reinfolib CSV API が500エラーを返し続けた

- **事象**: 内部API `/in-api/api-aur/aur/csv/transactionPrices` に検索条件付きGETを送ると、件数API・検索APIは200で動くのにCSV APIだけ常に500。本物のChromium(Playwright)からのfetchでも500。
- **原因**: `kind` パラメータの値形式の誤り。検索系APIのコード値（中古マンション等="07"）をそのまま使っていたが、CSV APIは**文字列名**（`kind=used`）を要求する。UI自動操作でダウンロードに成功した際のリクエストURLから `kind=residential`（名前形式）であることを発見した。
- **修正**: `kind=used` に変更したところ通常のHTTP GETで200。全年分取得成功。
- **教訓**: 同一サイト内でもAPIごとにパラメータの値体系が異なることがある。実際に成功するリクエストを1件観測（UI自動操作+ネットワークログ）してから一般化する。

## 2026-06-12 — 2025年分で KeyError: 'body'

- **事象**: 2025年分のレスポンスに base64 の `body` がなく `{"isExists": true, "url": ...}` 形式だった。
- **原因**: レスポンスサイズが大きい場合、サーバはZIPをAzure Blobに置き、URLを返す仕様（フロントエンドコードの `t.isExists ? window.location=t.url : ...` と一致）。
- **修正**: `isExists=true` のとき返却URLからZIPを直接取得するよう対応（download_transactions_2025.py）。

## 2026-06-12 — 検証スクリプトの UnicodeEncodeError

- **事象**: cp932コンソールで「✓」を print できず UnicodeEncodeError。
- **修正**: 記号をOK/NGに置換し、`python -X utf8` で実行。

## 2026-06-12 — PDF 手順書が Read ツールで読めない

- **事象**: `osaka_fudosan_dataanalysis_manual_v9.pdf` を Claude Code の Read ツールで開くと `pdftoppm failed: Command 'pdftoppm' not found` エラー。
- **原因**: PDF→画像変換に使う Poppler (pdftoppm) が Windows 環境に未インストール。
- **修正**: Python 3.12 に pypdf 6.13.2 をインストールし、`scripts/extract_pdf.py` でテキスト抽出（出力: `../manual_v9_extracted.txt`、24ページ・約3万字）。
- **再発防止**: 今後 PDF を読む場合は同スクリプトを再利用する。

## 2026-06-12 — PowerShell here-string 内の Python raw 文字列が壊れる

- **事象**: PowerShell の `@'...'@` 経由で `python -c` に複数行コードを渡すと、raw 文字列の引用符が欠落して SyntaxError。日本語パスも文字化け。
- **原因**: PowerShell→python -c の引数受け渡しで引用符の解釈が競合。cp932 コンソールと UTF-8 パスの不整合。
- **修正**: インラインコードをやめ、UTF-8 の .py ファイル（extract_pdf.py）に書き出してから実行する方式に変更。
- **再発防止**: 複数行 Python は必ずファイル化して実行する。
