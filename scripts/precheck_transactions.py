# -*- coding: utf-8 -*-
"""Step 3 投入前確認: ヘッダー一貫性・NULL候補率・特殊値・重複の確認（読み取りのみ）"""
import csv
import os
from collections import Counter

BASE = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
YEARS = [2021, 2022, 2023, 2024, 2025]

headers = {}
all_rows = {}
for y in YEARS:
    d = os.path.join(BASE, f"osaka_condo_seiyaku_{y}")
    name = [n for n in os.listdir(d) if n.endswith(".csv")][0]
    with open(os.path.join(d, name), encoding="cp932", newline="") as f:
        rows = list(csv.reader(f))
    headers[y] = rows[0]
    all_rows[y] = rows[1:]

print("===== 1. ヘッダー一貫性 =====")
ref = headers[YEARS[0]]
print(f"2021年カラム数: {len(ref)}")
same = all(headers[y] == ref for y in YEARS)
print("5年分ヘッダー完全一致:", "OK" if same else "NG")
if not same:
    for y in YEARS:
        if headers[y] != ref:
            print(f"  {y}: {headers[y]}")

print()
print("===== 2. 空文字率（NULL候補）主要列 =====")
cols = {6: "最寄駅：名称", 7: "最寄駅：距離（分）", 8: "取引価格（総額）", 9: "間取り",
        10: "面積（㎡）", 11: "建築年", 19: "改装", 5: "地区名"}
print(f"{'列名':<14} " + " ".join(f"{y}年" for y in YEARS))
for idx, label in cols.items():
    rates = []
    for y in YEARS:
        n = len(all_rows[y])
        empty = sum(1 for r in all_rows[y] if not r[idx].strip())
        rates.append(f"{100*empty/n:5.1f}%")
    print(f"{label:<14} " + "  ".join(rates))

print()
print("===== 3. 特殊値の確認 =====")
def special(idx, pred, label):
    total = Counter()
    for y in YEARS:
        for r in all_rows[y]:
            v = r[idx].strip()
            if v and pred(v):
                total[v] += 1
    top = total.most_common(8)
    print(f"{label}: {sum(total.values())}件 {top}")

special(10, lambda v: not v.replace(".", "").isdigit(), "面積の非数値")
special(11, lambda v: not (v.endswith("年") and v[:-1].isdigit()), "建築年の非標準値")
special(7, lambda v: not v.isdigit(), "徒歩分の非数値")
special(8, lambda v: not v.isdigit(), "取引価格の非数値")

print()
print("===== 4. 完全重複行 =====")
for y in YEARS:
    c = Counter(tuple(r) for r in all_rows[y])
    dup = sum(n - 1 for n in c.values() if n > 1)
    print(f"{y}: 全{len(all_rows[y])}行中、完全重複 {dup}行")

print()
print("===== 5. 市区町村の分布（大阪市/それ以外） =====")
for y in YEARS:
    n = len(all_rows[y])
    osaka = sum(1 for r in all_rows[y] if r[4].startswith("大阪市"))
    print(f"{y}: 大阪市 {osaka:,} / 府内その他 {n - osaka:,}")
