# -*- coding: utf-8 -*-
"""エグゼクティブサマリー（GA採用担当向け・見どころを主役に）。日本語フォント埋め込み。"""
import os
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.sans-serif"] = ["Yu Gothic", "Meiryo", "MS Gothic", "MS PGothic"]
matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["axes.unicode_minus"] = False
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch
from matplotlib.backends.backend_pdf import PdfPages

OUT = r"C:\Users\sn\Documents\データ分析\osaka-fudosan-dataanalysis\tableau\dashboard_wireframes"
os.makedirs(OUT, exist_ok=True)
PDF = os.path.join(OUT, "summary_revised_fixed.pdf")

DARK = "#23303e"; EDGE = "#9aa7b4"; BLUE = "#3a7bd5"; GREEN = "#3f9d6a"
ORG = "#e07b39"; RED = "#d9534f"; GRAY = "#eef2f6"; SUB = "#52616f"

fig, ax = plt.subplots(figsize=(13.66, 7.68))
ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
fig.patch.set_facecolor("white")

# ヘッダー
ax.add_patch(Rectangle((0.02, 0.93), 0.96, 0.05, fc=DARK, ec="none"))
ax.text(0.035, 0.955, "01  エグゼクティブサマリー", color="white", fontsize=14, fontweight="bold", va="center")
ax.text(0.965, 0.955, "SUMMARY  ->  EVIDENCE  ->  ACTION", color="#c7d2dc", fontsize=9.5, va="center", ha="right")

# タイトル＋GA向けサブ
ax.text(0.035, 0.892, "大阪市 中古マンション ― 仕入れで「次に調べる駅」をデータで絞り込む",
        fontsize=15.5, fontweight="bold", color=DARK, va="center")
ax.text(0.035, 0.855, "公開データだけで、仕入れ初期の“調査優先エリア”を自動抽出（投資用区分の一次スクリーニングを再現／2025年・大阪市・20〜60㎡）",
        fontsize=9.7, color=SUB, va="center")

# 4段階ファネル（終点をベネフィット化）
funnel = [("2,097件", "2025年の対象取引", BLUE),
          ("151駅", "取引が確認できた駅", BLUE),
          ("66駅", "10件以上で比較可能", GREEN),
          ("本命 10駅", "調査対象を 約7% に圧縮", RED)]
fx, fw, gap = 0.035, 0.205, 0.04
for i, (num, lab, col) in enumerate(funnel):
    x = fx + i * (fw + gap)
    ax.add_patch(FancyBboxPatch((x, 0.685), fw, 0.13, boxstyle="round,pad=0.004,rounding_size=0.008",
                 fc=GRAY, ec=EDGE, lw=1.1))
    ax.text(x + fw/2, 0.77, num, fontsize=20, fontweight="bold", color=col, ha="center", va="center")
    ax.text(x + fw/2, 0.715, lab, fontsize=8.8, color=DARK, ha="center", va="center")
    if i < 3:
        ax.text(x + fw + gap/2, 0.75, "->", fontsize=18, color="#7a8896", ha="center", va="center")

# 本命5駅
ax.text(0.035, 0.635, "総合スコア 上位5駅（★本命＝安定×低リスク／▲要確認＝高スコアだがリスク高）",
        fontsize=10, fontweight="bold", color=DARK, va="center")
stations = [("堺筋本町", "★本命", GREEN), ("玉造", "★本命", GREEN), ("大国町", "★本命", GREEN),
            ("松屋町", "★本命", GREEN), ("平野", "▲要確認", RED)]
sx, sw, sg = 0.035, 0.175, 0.015
for i, (nm, tag, col) in enumerate(stations):
    x = sx + i * (sw + sg)
    ax.add_patch(FancyBboxPatch((x, 0.515), sw, 0.10, boxstyle="round,pad=0.004,rounding_size=0.008",
                 fc="white", ec=col, lw=1.6))
    ax.text(x + sw/2, 0.578, nm, fontsize=12.5, fontweight="bold", color=DARK, ha="center", va="center")
    ax.text(x + sw/2, 0.535, tag, fontsize=10, fontweight="bold", color=col, ha="center", va="center")
ax.text(0.035, 0.49, "※ 平野は総合スコア上位だが旧耐震×改装不明が多く、★本命とは分けて「要確認」に（額面の割安を鵜呑みにしない）",
        fontsize=8.6, color=RED, va="center")

# 見どころ（主役）
ax.add_patch(FancyBboxPatch((0.035, 0.135), 0.93, 0.325, boxstyle="round,pad=0.006,rounding_size=0.012",
             fc="#fff7e6", ec=ORG, lw=1.8))
ax.text(0.05, 0.43, "◆ この分析の見どころ（EVIDENCEページで実証）",
        fontsize=12.5, fontweight="bold", color="#9a6a12", va="center")
hooks = [
    ("① 安い物件ほど“訳あり”が多い ― 逆選択をデータで可視化", GREEN,
     "　 最も割安に見える物件ほど旧耐震×改装不明が集中。額面の安さを鵜呑みにしない。"),
    ("② 精度1位のモデルを“あえて却下”", RED,
     "　 一番当たるModel Fは郊外を“偽の割安”にして順位を歪める → 順位が頑健なModel Cを採用（精度＝目的、ではない）。"),
    ("③ 限界もすべて明示", BLUE,
     "　 成約データ＝個別物件は買えない／割安＝相場より下振れ／必ず人が現物・謄本を確認、を正直に提示。"),
]
yy = 0.38
for head, col, body in hooks:
    ax.text(0.05, yy, head, fontsize=10.8, fontweight="bold", color=col, va="center")
    ax.text(0.05, yy - 0.035, body, fontsize=9.2, color=DARK, va="center")
    yy -= 0.092

# フッター
ax.add_patch(Rectangle((0.035, 0.045), 0.93, 0.05, fc="#eef2f6", ec=EDGE, lw=0.8))
ax.text(0.05, 0.07, "使用技術：BigQuery ・ dbt ・ BigQuery ML ・ Tableau",
        fontsize=9.5, fontweight="bold", color=DARK, va="center")
ax.text(0.95, 0.07, "データ：国土交通省 不動産情報ライブラリ（成約価格 2021-2025・大阪府）",
        fontsize=8.5, color=SUB, va="center", ha="right")

fig.savefig(os.path.join(OUT, "summary_revised_fixed.png"), dpi=120, bbox_inches="tight")
with PdfPages(PDF) as pp:
    pp.savefig(fig, bbox_inches="tight")
plt.close(fig)
print("OK:", PDF)
