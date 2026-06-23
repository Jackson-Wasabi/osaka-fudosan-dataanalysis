# -*- coding: utf-8 -*-
"""不動産情報ライブラリから大阪府・中古マンション等・成約価格情報を年単位でダウンロード
保存先: osaka-fudosan-dataanalysis/data/raw/osaka_condo_seiyaku_YYYY/(zip内のCSVをそのまま展開)
"""
import base64
import io
import json
import os
import time
import urllib.request
import urllib.parse
import urllib.error
import zipfile

BASE = "https://www.reinfolib.mlit.go.jp/in-api/api-aur/aur/csv/transactionPrices"
# reinfolib サイトのフロントエンドが全ブラウザ訪問者に配布する公開キー（個人の認証情報ではない）。
# 直書きを避け環境変数 REINFOLIB_KEY を優先。未設定時は公開キーをデフォルトとして使う。
KEY = os.environ.get("REINFOLIB_KEY", "6da659233e9c4d3b9daaedfb22c750d9")
DEST = r"C:\Users\sn\Documents\データ分析\osaka-fudosan-dataanalysis\data\raw"
YEARS = [2020, 2021, 2022, 2023, 2024, 2025]

def fetch_year(year, retries=3):
    params = {
        "language": "ja",
        "areaCondition": "address",
        "prefecture": "27",          # 大阪府
        "closedPrice": "true",       # 成約価格情報のみ
        "kind": "used",              # 中古マンション等
        "seasonFrom": f"{year}1",
        "seasonTo": f"{year}4",
    }
    url = BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Ocp-Apim-Subscription-Key": KEY})
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.loads(r.read().decode("utf-8"))
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as e:
            print(f"  attempt {attempt} failed: {e}")
            if attempt < retries:
                time.sleep(10 * attempt)
    return None

for year in YEARS:
    outdir = os.path.join(DEST, f"osaka_condo_seiyaku_{year}")
    print(f"=== {year} ===")
    payload = fetch_year(year)
    if payload is None:
        print(f"  GIVE UP year {year}")
        continue
    blob = base64.b64decode(payload["body"])
    zf = zipfile.ZipFile(io.BytesIO(blob))
    os.makedirs(outdir, exist_ok=True)
    for name in zf.namelist():
        data = zf.read(name)
        path = os.path.join(outdir, name)
        if os.path.exists(path):
            print(f"  SKIP (already exists, raw保護): {path}")
            continue
        with open(path, "wb") as f:
            f.write(data)
        lines = data.decode("cp932", errors="replace").splitlines()
        print(f"  saved: {name} ({len(data):,} bytes, {len(lines):,} lines)")
    time.sleep(5)

print("ALL DONE")
