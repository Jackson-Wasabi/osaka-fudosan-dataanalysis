# -*- coding: utf-8 -*-
"""ダッシュボードのワイヤーフレーム（レイアウト設計図）を多ページPDFで生成。"""
import os
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["font.sans-serif"] = ["Yu Gothic", "Meiryo", "MS Gothic", "MS PGothic"]
matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["axes.unicode_minus"] = False
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle, Polygon
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
np.random.seed(3)

OUT = r"C:\Users\sn\Documents\データ分析\osaka-fudosan-dataanalysis\tableau\dashboard_wireframes"
os.makedirs(OUT, exist_ok=True)
PDF = os.path.join(OUT, "dashboard_mockups.pdf")

GRAY = "#e9edf2"; EDGE = "#9aa7b4"; DARK = "#2b3a4a"; ACC = "#d9534f"
BLUE = "#3a7bd5"; ORG = "#e8913a"; GREEN = "#4a9d6a"


def newpage(title):
    fig, ax = plt.subplots(figsize=(13.66, 7.68))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    fig.patch.set_facecolor("white")
    ax.add_patch(Rectangle((0.02, 0.92), 0.96, 0.06, fc=DARK, ec="none"))
    ax.text(0.04, 0.95, title, color="white", fontsize=15, fontweight="bold", va="center")
    ax.text(0.96, 0.95, "① 概要  →  ② 結果  →  ③ 根拠（の流れ）", color="#cdd6df",
            fontsize=9, va="center", ha="right")
    return fig, ax


def box(ax, x, y, w, h, label, fc=GRAY):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.004,rounding_size=0.008",
                                fc=fc, ec=EDGE, lw=1.2))
    if label:
        ax.text(x + 0.012, y + h - 0.025, label, fontsize=10, fontweight="bold", color=DARK, va="top")


def hbars(ax, x, y, w, h, n=5, vals=None, colors=None):
    vals = vals or [0.95, 0.9, 0.86, 0.8, 0.74][:n]
    for i, v in enumerate(vals):
        yy = y + h - (i + 1) * (h / (n + 1))
        c = colors[i] if colors else BLUE
        ax.add_patch(Rectangle((x, yy - 0.018), w * v, 0.03, fc=c, ec="none", alpha=0.85))


def scatter(ax, x, y, w, h):
    px = x + 0.04 + np.random.rand(120) * (w - 0.06)
    base = (px - x - 0.04) / (w - 0.06)
    py = y + 0.05 + base * (h - 0.12) + np.random.randn(120) * 0.025
    py = np.clip(py, y + 0.04, y + h - 0.06)
    cols = np.where(base + np.random.randn(120) * 0.1 < 0.35, ACC, GREEN)
    ax.scatter(px, py, s=8, c=cols, alpha=0.6, edgecolors="none")
    ax.plot([x + 0.04, x + w - 0.02], [y + 0.05, y + h - 0.06], color="black", lw=1.5)


def grid_table(ax, x, y, w, h, rows=6):
    for i in range(rows + 1):
        yy = y + 0.02 + i * ((h - 0.06) / rows)
        ax.plot([x + 0.02, x + w - 0.02], [yy, yy], color=EDGE, lw=0.7)
    for cx in [0.18, 0.32, 0.46, 0.6, 0.74, 0.86]:
        ax.plot([x + w * cx, x + w * cx], [y + 0.02, y + h - 0.04], color=EDGE, lw=0.6)


def osaka_map(ax, x, y, w, h):
    poly = [(0.25, 0.15), (0.45, 0.05), (0.7, 0.12), (0.85, 0.4), (0.78, 0.7),
            (0.55, 0.9), (0.3, 0.85), (0.12, 0.55), (0.18, 0.3)]
    pts = [(x + 0.04 + px * (w - 0.08), y + 0.04 + py * (h - 0.1)) for px, py in poly]
    ax.add_patch(Polygon(pts, closed=True, fc="#f3f6fa", ec=EDGE, lw=1.0))
    cx = x + 0.04 + 0.5 * (w - 0.08); cy = y + 0.04 + 0.5 * (h - 0.1)
    for _ in range(30):
        a = np.random.rand() * 6.28; r = np.random.rand() * 0.22
        dx = np.cos(a) * r * (w - 0.08); dy = np.sin(a) * r * (h - 0.1)
        s = 8 + np.random.rand() * 60
        c = ACC if np.random.rand() < 0.25 else BLUE
        ax.add_patch(Circle((cx + dx, cy + dy), 0.006 + s * 0.0002, fc=c, ec="white", lw=0.4, alpha=0.8))


def gbars0(ax, x, y, w, h, n=8):
    x0 = x + w * 0.45
    ax.plot([x0, x0], [y + 0.04, y + h - 0.05], color="black", lw=1.3)
    ax.text(x0, y + 0.015, "0", fontsize=7, ha="center")
    for i in range(n):
        yy = y + h - 0.06 - i * ((h - 0.12) / n)
        cv = (np.random.rand() - 0.4) * 0.4; fv = cv + 0.16
        ax.add_patch(Rectangle((x0, yy - 0.012), w * 0.42 * cv, 0.012, fc=BLUE, ec="none"))
        ax.add_patch(Rectangle((x0, yy - 0.026), w * 0.42 * fv, 0.012, fc=ORG, ec="none"))


with PdfPages(PDF) as pp:
    # Page 1: サマリー（採用担当を惹きつける版）
    fig, ax = newpage("(1) 00_サマリー（つかみ：問題 → 成果 → 分析の芯）")
    # タイトル＋サブタイトル
    ax.add_patch(FancyBboxPatch((0.04, 0.795), 0.92, 0.105,
                 boxstyle="round,pad=0.004,rounding_size=0.008", fc="#dfeaf7", ec=EDGE, lw=1.2))
    ax.text(0.06, 0.872, "大阪市の中古マンション ― 相場より割安な「狙い目エリア」を見つける分析",
            fontsize=16, fontweight="bold", color=DARK, va="center")
    ax.text(0.06, 0.822, "投資用に物件を仕入れる際、「まず調べるべきエリア」を公開データから自動で絞り込む（2025年・大阪市・20〜60㎡）",
            fontsize=10, color="#46586a", va="center")
    # 漏斗BAN（駅で統一・矢印でつなぐ）
    funnel = [("2,097件 / 151駅", "2025年に売れた中古マンション（全駅）", BLUE),
              ("66駅", "データが十分な駅に絞る（取引10件以上）", GREEN),
              ("本命 10駅", "安心して薦められる駅 ＝ 全体の約7%", ACC)]
    for i, (num, lab, col) in enumerate(funnel):
        bx = 0.04 + i * 0.315
        box(ax, bx, 0.59, 0.29, 0.175, "")
        ax.text(bx + 0.145, 0.70, num, fontsize=22, fontweight="bold", color=col, ha="center", va="center")
        ax.text(bx + 0.145, 0.625, lab, fontsize=9.5, color=DARK, ha="center", va="center")
        if i < 2:
            ax.text(bx + 0.305, 0.677, "→", fontsize=22, color="#6a7785", ha="center", va="center")
    # 本命トップ5（駅｜価格帯｜リスク｜棒）= 行動できる情報
    box(ax, 0.04, 0.345, 0.55, 0.215, "本命の駅トップ5（全10駅中）｜ 駅 ・ 1㎡の価格 ・ リスク率")
    honmei = [("堺筋本町", "63万/㎡", "6%", 0.95), ("玉造", "63万/㎡", "0%", 0.90),
              ("大国町", "64万/㎡", "0%", 0.85), ("松屋町", "64万/㎡", "7%", 0.78),
              ("森ノ宮", "60万/㎡", "0%", 0.74)]
    for i, (nm, pr, rk, v) in enumerate(honmei):
        yy = 0.488 - i * 0.030
        ax.text(0.055, yy, nm, fontsize=9, fontweight="bold", va="center", color=DARK)
        ax.text(0.135, yy, pr, fontsize=8.5, va="center", color="#46586a")
        ax.text(0.205, yy, "リスク" + rk, fontsize=8.5, va="center", color=(GREEN if rk == "0%" else ACC))
        ax.add_patch(Rectangle((0.275, yy - 0.011), 0.29 * v, 0.022, fc=BLUE, ec="none", alpha=0.8))
    # 分析の芯（hook = 続きを見たくなる仕掛け）
    ax.add_patch(FancyBboxPatch((0.61, 0.345), 0.35, 0.215,
                 boxstyle="round,pad=0.006,rounding_size=0.01", fc="#fff7e6", ec=ORG, lw=1.6))
    ax.text(0.625, 0.535, "◆ この分析で工夫した点（詳しくは各タブで）",
            fontsize=10.5, fontweight="bold", color="#9a6a12", va="top")
    insights = ["・一番 “当たる” 予測モデルを、あえて不採用に",
                "    （郊外を “ニセのお買い得” にしてしまうため）",
                "・“安い物件ほど訳あり” をデータで見える化",
                "・分析の限界も正直に明示（買いとは断定しない）"]
    for j, t in enumerate(insights):
        ax.text(0.625, 0.488 - j * 0.034, t, fontsize=9, color=DARK, va="top")
    # 方法1行＋フッター（技術・出典）
    ax.text(0.04, 0.305,
            "やり方：① 妥当な価格をデータで予測 → ② 実際の売値と比べ「駅の中で安い」物件を抽出 → ③ 5項目で点数化して順位づけ",
            fontsize=8.5, color="#46586a")
    ax.add_patch(Rectangle((0.04, 0.05), 0.92, 0.055, fc="#eef2f6", ec=EDGE, lw=0.8))
    ax.text(0.055, 0.077, "使用技術：BigQuery ・ dbt ・ BigQuery ML ・ Tableau",
            fontsize=9.5, fontweight="bold", color=DARK, va="center")
    ax.text(0.955, 0.077, "データ：国交省 不動産情報ライブラリ（成約価格 2021-2025・大阪府）",
            fontsize=8.5, color="#46586a", va="center", ha="right")
    fig.savefig(os.path.join(OUT, "page1.png"), dpi=110, bbox_inches="tight")
    pp.savefig(fig, bbox_inches="tight"); plt.close(fig)

    # Page 2: スクリーニング結果（結論型）
    fig, ax = newpage("(2) スクリーニング結果")
    ax.text(0.04, 0.885, "どの駅・エリアを優先的に調べるべきかを一目で（地図＋ランキング）",
            fontsize=11, fontweight="bold", color="#9a6a12", va="center")
    box(ax, 0.04, 0.10, 0.50, 0.75, "割安な狙い目は “中心部” に集中（色=割安・大きさ=取引量・赤=要確認）")
    osaka_map(ax, 0.05, 0.12, 0.48, 0.68)
    box(ax, 0.56, 0.47, 0.40, 0.38, "配点を変えても上位に残る駅 ＝ 頑健な “本命”（66駅）")
    grid_table(ax, 0.57, 0.49, 0.38, 0.30, 6)
    box(ax, 0.56, 0.10, 0.40, 0.33, "操作・凡例")
    ax.add_patch(FancyBboxPatch((0.58, 0.31), 0.34, 0.055, boxstyle="round,pad=0.004", fc="white", ec=EDGE))
    ax.text(0.59, 0.337, "配点パターン：[バランス] [割安重視] [リスク重視]", fontsize=9, va="center", color=DARK)
    ax.text(0.59, 0.25, "凡例：色が濃い＝割安 ／ 赤＝リスク高（要確認）", fontsize=9, va="center", color=DARK)
    ax.text(0.59, 0.18, "クリック連動：地図で駅を選ぶと右の表が絞られる", fontsize=9, va="center", color=BLUE)
    ax.text(0.04, 0.05, "※ 全画面共通：調査候補です。買い判断ではなく、現物・謄本の確認が前提。",
            fontsize=8, color="#6a7785")
    fig.savefig(os.path.join(OUT, "page2.png"), dpi=110, bbox_inches="tight")
    pp.savefig(fig, bbox_inches="tight"); plt.close(fig)

    # Page 3: モデルの根拠（結論型）
    fig, ax = newpage("(3) モデルの根拠")
    ax.text(0.04, 0.885, "なぜこのモデルか／限界は何か ― 検証で示す（評価・バイアス・散布図）",
            fontsize=11, fontweight="bold", color="#9a6a12", va="center")
    box(ax, 0.04, 0.48, 0.45, 0.355, "Baselineから検証し、説明できる Model C を採用")
    hbars(ax, 0.07, 0.50, 0.40, 0.30, 7, vals=[0.95, 0.78, 0.77, 0.62, 0.62, 0.64, 0.5],
          colors=[BLUE, BLUE, BLUE, GREEN, BLUE, BLUE, BLUE])
    ax.text(0.265, 0.495, "→ 精度1位のFを “あえて却下” ＝判断力（緑=採用）",
            fontsize=8.5, ha="center", color="#46586a")
    box(ax, 0.51, 0.48, 0.45, 0.355, "F は周縁を “偽の割安” にする → だから却下")
    gbars0(ax, 0.52, 0.50, 0.43, 0.30, 8)
    ax.text(0.735, 0.495, "→ F(橙)は郊外を “ニセのお買い得” にする", fontsize=8.5, ha="center", color="#46586a")
    box(ax, 0.04, 0.095, 0.92, 0.35, "安い物件ほど “訳あり”（赤）が多い ＝ 逆選択")
    scatter(ax, 0.06, 0.115, 0.88, 0.30)
    ax.text(0.5, 0.06, "→ 赤(旧耐震×改装不明)が安い側に偏る／雲が線より上＝モデルの系統バイアスも正直に明示",
            fontsize=8.5, ha="center", color="#46586a")
    fig.savefig(os.path.join(OUT, "page3.png"), dpi=110, bbox_inches="tight")
    pp.savefig(fig, bbox_inches="tight"); plt.close(fig)

print("OK:", PDF)
