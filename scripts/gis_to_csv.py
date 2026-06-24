# -*- coding: utf-8 -*-
"""GIS GeoJSON → CSV 変換（BigQuery ロード用）
属性値は一切変更せず、ジオメトリから lon/lat のみ算出して列追加する。
- N02 Station: LineString の中点 → lon, lat
- L01 地価公示: Point → lon, lat
出力: data/gis/processed/*.csv (UTF-8)
"""
import csv
import json
import os

GIS = os.path.join(os.path.dirname(__file__), "..", "data", "gis")

JOBS = [
    # (入力geojson, 出力csv)
    (r"N02-25_GML\N02-25_GML\UTF-8\N02-25_Station.geojson", "station_master_2025.csv"),
    (r"L01-25_27_GML\L01-25_27_GML\L01-25_27.geojson", "land_price_2025.csv"),
]

def line_midpoint(coords):
    """LineString の単純中点（座標列の中央要素）"""
    return coords[len(coords) // 2]

for src_rel, dst_name in JOBS:
    src = os.path.join(GIS, "raw", src_rel)
    dst = os.path.join(GIS, "processed", dst_name)
    with open(src, encoding="utf-8") as f:
        gj = json.load(f)
    feats = gj["features"]
    # 全フィーチャのキー和集合（順序は初出順）
    keys = []
    for ft in feats:
        for k in ft["properties"].keys():
            if k not in keys:
                keys.append(k)
    with open(dst, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(keys + ["lon", "lat"])
        for ft in feats:
            geom = ft["geometry"]
            if geom["type"] == "Point":
                lon, lat = geom["coordinates"][0], geom["coordinates"][1]
            elif geom["type"] == "LineString":
                lon, lat = line_midpoint(geom["coordinates"])
            else:
                lon, lat = "", ""
            props = ft["properties"]
            w.writerow([props.get(k, "") for k in keys] + [lon, lat])
    print(f"{dst_name}: {len(feats):,} rows / {len(keys) + 2} cols")
