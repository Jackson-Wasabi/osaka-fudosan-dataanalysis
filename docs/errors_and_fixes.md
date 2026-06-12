# エラーと修正の記録 (errors_and_fixes)

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
