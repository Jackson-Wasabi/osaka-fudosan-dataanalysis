# -*- coding: utf-8 -*-
"""Step 10 フェーズ2: モデル評価の実行（読み取り専用）。
gcloud サブプロセスのハング回避のため ADC コピーを明示指定して接続する。
実行: GOOGLE_APPLICATION_CREDENTIALS=/tmp/adc.json GOOGLE_CLOUD_PROJECT=osaka-fudosan-dataanalysis python -u scripts/evaluate_models.py
"""
import os
import re
from google.cloud import bigquery

PROJ = "osaka-fudosan-dataanalysis"
DS = f"{PROJ}.osaka_real_estate"
SQL_FILE = os.path.join(os.path.dirname(__file__), "..", "sql", "bqml", "02_evaluate.sql")
client = bigquery.Client(project=PROJ)

EXPECTED = ["model_a", "model_b", "model_c", "model_d",
            "model_e_tree", "model_f_time", "model_c_foldb"]


def check_models():
    print("=== フェーズ1モデルの存在確認 ===")
    found = {m.model_id for m in client.list_models(DS)}
    for name in EXPECTED:
        print(f"  {'OK ' if name in found else 'MISSING'} {name}")
    missing = [m for m in EXPECTED if m not in found]
    if missing:
        raise SystemExit(f"モデル未作成: {missing} → フェーズ1を先に実行")
    print()


def print_table(rows):
    rows = [dict(r) for r in rows]
    if not rows:
        print("  (0 rows)")
        return
    cols = list(rows[0].keys())
    widths = {c: max(len(c), *(len(str(r[c])) for r in rows)) for c in cols}
    print("  " + " | ".join(c.ljust(widths[c]) for c in cols))
    print("  " + "-+-".join("-" * widths[c] for c in cols))
    for r in rows:
        print("  " + " | ".join(str(r[c]).ljust(widths[c]) for c in cols))


def split_statements(text):
    # コメント行を除去せず、; で分割（SQL内に ; は無い前提）
    parts = [s.strip() for s in text.split(";")]
    return [s for s in parts if re.search(r"\bSELECT\b", s, re.I)]


BLOCK_TITLES = [
    "ブロック1: モデル比較表（Baseline〜F・テスト2025・smearing補正済）",
    "ブロック2: Fold A/B 安定性（Model C）",
    "ブロック3: 残差診断（面積帯・築年帯・徒歩帯）",
    "ブロック4: 区別の系統残差",
]


def main():
    check_models()
    with open(SQL_FILE, encoding="utf-8") as f:
        statements = split_statements(f.read())
    for i, stmt in enumerate(statements):
        title = BLOCK_TITLES[i] if i < len(BLOCK_TITLES) else f"ブロック{i+1}"
        print(f"\n=== {title} ===")
        print_table(client.query(stmt).result())
    print("\n評価完了")


if __name__ == "__main__":
    main()
