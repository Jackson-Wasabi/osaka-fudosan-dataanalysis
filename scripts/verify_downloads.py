# -*- coding: utf-8 -*-
"""Step 2 ダウンロード検証: 行数・種類・価格情報区分・四半期分布・旧ファイル一致・ZIP整合性"""
import csv
import hashlib
import io
import os
import zipfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEW = os.path.join(REPO, "data")
# 旧プロジェクトとの突合（任意）。環境変数 OLD_DATA_DIR で上書き可。未設定なら隣接フォルダを既定にする。
OLD = os.environ.get(
    "OLD_DATA_DIR",
    os.path.join(os.path.dirname(REPO), "osaka-condo-station-opportunity-analysis", "data"),
)

def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

print("===== 取引CSV =====")
for year in range(2020, 2026):
    d = os.path.join(NEW, "raw", f"osaka_condo_seiyaku_{year}")
    if not os.path.isdir(d):
        print(f"{year}: MISSING DIR")
        continue
    for name in os.listdir(d):
        path = os.path.join(d, name)
        with open(path, encoding="cp932", errors="replace", newline="") as f:
            rows = list(csv.reader(f))
        if len(rows) <= 1:
            print(f"{year}: {name} -> EMPTY ({len(rows)} rows)")
            continue
        header, data = rows[0], rows[1:]
        kinds = sorted({r[0] for r in data})
        cats = sorted({r[1] for r in data})
        periods = sorted({r[18] for r in data})
        prefs = sorted({r[3] for r in data})
        n_osaka_city = sum(1 for r in data if r[4].startswith("大阪市"))
        print(f"{year}: {name}")
        print(f"  data rows={len(data):,} / 種類={kinds} / 区分={cats} / 都道府県={prefs}")
        print(f"  取引時期={periods[0]}〜{periods[-1]} ({len(periods)}区分) / 大阪市内行={n_osaka_city:,}")
        # 旧ファイルとの一致確認
        old_path = os.path.join(OLD, "raw", f"osaka_condo_seiyaku_{year}", name)
        if os.path.exists(old_path):
            same = md5(path) == md5(old_path)
            print(f"  旧ファイル照合: {'MD5一致 OK' if same else 'MD5不一致 NG'}")

print()
print("===== GISzip =====")
for name in ["N02-25_GML.zip", "L01-25_27_GML.zip"]:
    path = os.path.join(NEW, "gis", "raw", name)
    if not os.path.exists(path):
        print(f"{name}: MISSING")
        continue
    with zipfile.ZipFile(path) as z:
        bad = z.testzip()
        n = len(z.namelist())
    size = os.path.getsize(path)
    line = f"{name}: {size:,} bytes / {n} entries / 整合性={'OK' if bad is None else 'NG:' + bad}"
    old_path = os.path.join(OLD, "gis", "raw", name)
    if os.path.exists(old_path):
        line += f" / 旧ファイル照合: {'MD5一致 OK' if md5(path) == md5(old_path) else 'MD5不一致 NG'}"
    print(line)

