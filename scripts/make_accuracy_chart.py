# -*- coding: utf-8 -*-
"""§6 モデル評価の可視化: Baseline vs 採用モデルC の予測精度比較。
出典: sql/bqml/02_evaluate.sql（Fold A・テスト2025・n=2,097・Duan smearing補正）。
出力: outputs/figures/09_model_accuracy.png
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.sans-serif"] = ["Yu Gothic", "Meiryo", "MS Gothic", "MS PGothic"]
matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["axes.unicode_minus"] = False
import matplotlib.pyplot as plt

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(REPO, "outputs", "figures", "09_model_accuracy.png")

NAVY = "#14304a"; GRAY = "#aab4c0"; ORANGE = "#c1771a"; SUB = "#5b6b7b"

labels = ["±10%以内", "±20%以内"]
baseline = [17.6, 35.6]   # hit10, hit20 (%)
modelc   = [26.9, 54.0]

fig, ax = plt.subplots(figsize=(8.4, 4.1), dpi=120)
x = np.arange(len(labels)); w = 0.34
b1 = ax.bar(x - w/2, baseline, w, label="Baseline（駅中央値そのまま）", color=GRAY)
b2 = ax.bar(x + w/2, modelc, w, label="採用：Model C", color=NAVY)
for bars in (b1, b2):
    for r in bars:
        ax.text(r.get_x() + r.get_width()/2, r.get_height() + 1.2, f"{r.get_height():.0f}%",
                ha="center", va="bottom", fontsize=10.5, fontweight="bold", color="#1f2733")

ax.set_ylim(0, 64)
ax.set_ylabel("予測が実勢価格に近かった割合", fontsize=10, color=SUB)
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=12)
ax.set_title("予測はどれだけ実勢価格に近いか ― Baseline vs 採用モデルC", fontsize=13, fontweight="bold", color=NAVY, pad=10)
ax.legend(loc="upper left", fontsize=9.5, frameon=False)
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)
ax.tick_params(length=0)
ax.grid(axis="y", color="#e3e9ef", linewidth=0.8)
ax.set_axisbelow(True)

fig.text(0.5, 0.015,
         "誤差率の中央値（MdAPE）28.6% → 18.3% に改善 ＝ Model Cは予測の半分が実勢の ±18% 以内に収まる",
         ha="center", fontsize=9.8, color=ORANGE, fontweight="bold")
plt.subplots_adjust(bottom=0.17, top=0.88)
fig.savefig(OUT, facecolor="white")
print("saved:", OUT)
