# -*- coding: utf-8 -*-
"""BigQuery raw テーブルの各列に日本語説明(description)を設定する。
スキーマのメタデータのみ変更し、データ・型・列順は一切変更しない。
docs/data_dictionary.md と同期させること。
"""
import json
import os
import subprocess
import tempfile

PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "osaka-fudosan-dataanalysis")
DATASET = "osaka_real_estate"

TX = {
    "kind": "種類（中古マンション等のみ）",
    "price_category": "価格情報区分（成約価格情報のみ）",
    "city_code": "市区町村コード（5桁、例: 27102=大阪市都島区）",
    "prefecture_name": "都道府県名（大阪府のみ）",
    "city_name": "市区町村名（例: 大阪市都島区）",
    "district_name": "地区名（例: 網島町）",
    "nearest_station_name": "最寄駅：名称（表記ゆれあり）",
    "nearest_station_distance_min": "最寄駅：距離（分）。範囲表記（30分～60分等）が混在",
    "trade_price_total": "取引価格（総額・円）",
    "layout": "間取り（全角、例: ２ＬＤＫ）",
    "area_sqm": "面積（㎡、5㎡単位の丸め）",
    "built_year": "建築年（例: 1980年。「戦前」あり）",
    "building_structure": "建物の構造（ＳＲＣ/ＲＣ/鉄骨造等）",
    "use_type": "用途",
    "future_use_purpose": "今後の利用目的",
    "city_planning": "都市計画（用途地域）",
    "building_coverage_ratio": "建ぺい率（％）",
    "floor_area_ratio": "容積率（％）",
    "trade_period": "取引時期（例: 2021年第1四半期）",
    "renovation": "改装（「改装済み」or 空欄のみ。空欄は未改装/不明の区別不能）",
    "trade_circumstances": "取引の事情等（ほぼ欠損）",
}

SM = {
    "n02_001": "鉄道区分コード（11=普通鉄道JR, 12=普通鉄道 等）",
    "n02_002": "事業者種別コード（2=JR在来線, 3=公営, 4=民営, 5=第三セクター等）",
    "n02_003": "路線名（例: 御堂筋線）",
    "n02_004": "運営会社（例: 大阪市高速電気軌道）",
    "n02_005": "駅名",
    "n02_005c": "駅コード（緯度降順の一意番号）",
    "n02_005g": "駅グループコード（乗換駅等の同一駅を束ねる。駅名寄せに有用）",
    "lon": "経度（駅ジオメトリの簡易中点、当方算出）",
    "lat": "緯度（駅ジオメトリの簡易中点、当方算出）",
}

LP = {
    "l01_001": "行政区域コード（当年・5桁）",
    "l01_002": "用途区分（当年。000=住宅地, 005=商業地等）",
    "l01_003": "連番（当年。市区町村・用途区分単位）",
    "l01_004": "前年の行政区域コード（同一地点判定用）",
    "l01_005": "前年の用途区分",
    "l01_006": "前年の連番",
    "l01_007": "調査年（例: 2025）",
    "l01_008": "公示価格（円/㎡）。nearest_land_price の源泉",
    "l01_009": "対前年変動率（%）。land_price_change_rate に利用",
    "l01_010": "選定状況（継続・新規等）",
    "l01_011": "前年からの変更有無: 所在並びに地番・住居表示",
    "l01_012": "前年からの変更有無: 地積",
    "l01_013": "前年からの変更有無: 利用の現況",
    "l01_014": "前年からの変更有無: 建物構造",
    "l01_015": "前年からの変更有無: 供給施設",
    "l01_016": "前年からの変更有無: 最寄り駅迄の道路距離",
    "l01_017": "前年からの変更有無: 都市計画の用途区分",
    "l01_018": "前年からの変更有無: 防火地域",
    "l01_019": "前年からの変更有無: 都市計画区分",
    "l01_020": "前年からの変更有無: 森林法",
    "l01_021": "前年からの変更有無: 自然公園法",
    "l01_022": "前年からの変更有無: 建蔽率",
    "l01_023": "前年からの変更有無: 容積率",
    "l01_024": "標準地名（全国一意の市区町村を示す地名）",
    "l01_025": "所在並びに地番",
    "l01_026": "住居表示",
    "l01_027": "地積（㎡）",
    "l01_028": "利用の現況・大分類（住宅/店舗等。住宅系絞り込みに使用）",
    "l01_029": "利用の現況・詳細",
    "l01_032": "ガス供給の有無",
    "l01_033": "水道の有無",
    "l01_034": "下水道の有無",
    "l01_036": "間口比率（短い方を1.0とする）",
    "l01_037": "奥行比率（短い方を1.0とする）",
    "l01_038": "地上階層（階。不明=0）",
    "l01_039": "地下階層（階。不明=0）",
    "l01_042": "前面道路の幅員（m）",
    "l01_047": "周辺の土地の利用の現況",
    "l01_048": "最寄り駅名（バス停名等の場合あり）",
    "l01_050": "最寄り駅までの道路距離（m）",
    "l01_051": "都市計画の用途区分（2中専/商業等）",
    "l01_052": "防火地域（防火/準防等）",
    "l01_053": "都市計画区分（市街化等）",
    "l01_057": "建蔽率の上限（%。記載なし=0）",
    "l01_058": "容積率の上限（%。記載なし=0）",
    "l01_059": "割増容積率の使用前提か（true/false）",
    "l01_061": "選定年次ビット（各年の選定有無を0/1で連結）",
    "lon": "経度（標準地Point、当方算出）",
    "lat": "緯度（標準地Point、当方算出）",
}
LP_GENERIC = "詳細属性（製品仕様書 KS-PS-L01-v3_3 参照）"
LP_SERIES = "年次別公示価格系列（円/㎡。新しい列ほど近年。非選定年は空/0）"

TABLES = [
    ("raw_transactions", TX, None, None),
    ("raw_station_master_2025", SM, None, None),
    ("raw_land_price_2025", LP, LP_GENERIC, LP_SERIES),
]

env = dict(os.environ, PYTHONUTF8="1")

for table, mapping, generic, series in TABLES:
    ref = f"{PROJECT}:{DATASET}.{table}"
    schema = json.loads(subprocess.run(
        ["bq", "show", "--schema", "--format=prettyjson", ref],
        capture_output=True, text=True, encoding="utf-8", env=env, shell=True).stdout)
    for field in schema:
        name = field["name"]
        if name in mapping:
            field["description"] = mapping[name]
        elif generic:
            num = int(name.split("_")[1]) if name.startswith("l01_") else 0
            field["description"] = series if num >= 71 else generic
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False,
                                     encoding="utf-8") as f:
        json.dump(schema, f, ensure_ascii=False)
        tmp = f.name
    r = subprocess.run(["bq", "update", ref, tmp], capture_output=True,
                       text=True, encoding="utf-8", env=env, shell=True)
    print(table, "->", "OK" if r.returncode == 0 else "FAIL: " + r.stderr[:200])
    os.unlink(tmp)
