# -*- coding: utf-8 -*-
"""2025年分: isExists/url 形式(大容量時にサーバがURLを返す方式)に対応"""
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
KEY = "6da659233e9c4d3b9daaedfb22c750d9"
DEST = r"C:\Users\sn\Documents\データ分析\osaka-fudosan-dataanalysis\data\raw"
year = 2025

params = {
    "language": "ja", "areaCondition": "address", "prefecture": "27",
    "closedPrice": "true", "kind": "used",
    "seasonFrom": f"{year}1", "seasonTo": f"{year}4",
}
url = BASE + "?" + urllib.parse.urlencode(params)
req = urllib.request.Request(url, headers={"Ocp-Apim-Subscription-Key": KEY})

payload = None
for attempt in range(1, 4):
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            payload = json.loads(r.read().decode("utf-8"))
        break
    except Exception as e:
        print(f"attempt {attempt} failed: {e}")
        time.sleep(10 * attempt)

if payload is None:
    raise SystemExit("download failed")

print("payload keys:", sorted(payload.keys()))
print("isExists:", payload.get("isExists"), "zipFileName:", payload.get("zipFileName"))

if payload.get("body"):
    blob = base64.b64decode(payload["body"])
elif payload.get("isExists") and payload.get("url"):
    print("fetching from url:", payload["url"][:120])
    with urllib.request.urlopen(payload["url"], timeout=300) as r:
        blob = r.read()
else:
    raise SystemExit(f"unexpected payload: {json.dumps(payload)[:300]}")

zf = zipfile.ZipFile(io.BytesIO(blob))
outdir = os.path.join(DEST, f"osaka_condo_seiyaku_{year}")
os.makedirs(outdir, exist_ok=True)
for name in zf.namelist():
    path = os.path.join(outdir, name)
    if os.path.exists(path):
        print(f"SKIP (exists): {path}")
        continue
    data = zf.read(name)
    with open(path, "wb") as f:
        f.write(data)
    lines = data.decode("cp932", errors="replace").splitlines()
    print(f"saved: {name} ({len(data):,} bytes, {len(lines):,} lines)")
