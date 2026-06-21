# -*- coding: utf-8 -*-
"""3枚デッキ（SUMMARY→EVIDENCE→ACTION）。日本語フォント埋め込み・文字化け解消版。
1枚物サマリーと旧ChatGPT版の重複を解消し、役割分担で1本に統合する。"""
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
PDF = os.path.join(OUT, "osaka_real_estate_dashboard_revised.pdf")

DARK = "#23303e"; EDGE = "#9aa7b4"; BLUE = "#3a7bd5"; GREEN = "#3f9d6a"
ORG = "#e07b39"; RED = "#d9534f"; GRAY = "#eef2f6"; SUB = "#52616f"
LITE = "#fff7e6"


def new_page():
    fig, ax = plt.subplots(figsize=(13.66, 7.68))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    fig.patch.set_facecolor("white")
    return fig, ax


def chrome(ax, num, title, active):
    ax.add_patch(Rectangle((0.02, 0.93), 0.96, 0.05, fc=DARK, ec="none"))
    ax.text(0.035, 0.955, f"{num}  {title}", color="white", fontsize=14, fontweight="bold", va="center")
    steps = ["SUMMARY", "EVIDENCE", "ACTION"]
    bx = [0.78, 0.865, 0.945]
    for i, s in enumerate(steps):
        on = (i == active)
        ax.text(bx[i], 0.955, s, ha="center", va="center", fontsize=9,
                color="white" if on else "#8b97a3", fontweight="bold" if on else "normal")
    ax.text(0.8225, 0.955, "→", ha="center", va="center", color="#6b7884", fontsize=9)
    ax.text(0.905, 0.955, "→", ha="center", va="center", color="#6b7884", fontsize=9)


def footer(ax, page, total=3):
    ax.add_patch(Rectangle((0.035, 0.045), 0.93, 0.045, fc="#eef2f6", ec=EDGE, lw=0.8))
    ax.text(0.05, 0.0675, "使用技術：BigQuery ・ dbt ・ BigQuery ML ・ Tableau",
            fontsize=9, fontweight="bold", color=DARK, va="center")
    ax.text(0.80, 0.0675, "データ：国土交通省 不動産情報ライブラリ（成約 2021-2025・大阪府）",
            fontsize=8, color=SUB, va="center", ha="right")
    ax.text(0.955, 0.0675, f"{page} / {total}", fontsize=9, color=SUB, va="center", ha="right")


# ========== PAGE 1 : SUMMARY ==========
def page1():
    fig, ax = new_page()
    chrome(ax, "01", "エグゼクティブサマリー", 0)
    ax.text(0.035, 0.892, "大阪市 中古マンション ― 仕入れで「次に調べる駅」をデータで絞り込む",
            fontsize=15.5, fontweight="bold", color=DARK, va="center")
    ax.text(0.035, 0.855, "公開データだけで、仕入れ初期の“調査優先エリア”を自動抽出（投資用区分の一次スクリーニングを再現／2025年・大阪市・20〜60㎡）",
            fontsize=9.7, color=SUB, va="center")
    funnel = [("2,106件", "2025年の対象取引", BLUE), ("151駅", "相場比較が可能な駅", BLUE),
              ("66駅", "10件以上で安定比較", GREEN), ("本命 10駅", "調査対象を 約7% に圧縮", RED)]
    fx, fw, gap = 0.035, 0.205, 0.04
    for i, (num, lab, col) in enumerate(funnel):
        x = fx + i * (fw + gap)
        ax.add_patch(FancyBboxPatch((x, 0.685), fw, 0.13, boxstyle="round,pad=0.004,rounding_size=0.008", fc=GRAY, ec=EDGE, lw=1.1))
        ax.text(x + fw/2, 0.77, num, fontsize=20, fontweight="bold", color=col, ha="center", va="center")
        ax.text(x + fw/2, 0.715, lab, fontsize=8.8, color=DARK, ha="center", va="center")
        if i < 3:
            ax.text(x + fw + gap/2, 0.75, "→", fontsize=18, color="#7a8896", ha="center", va="center")
    ax.text(0.035, 0.635, "総合スコア 上位5駅（★本命＝安定×低リスク／▲要確認＝高スコアだがリスク高）",
            fontsize=10, fontweight="bold", color=DARK, va="center")
    stations = [("堺筋本町", "★本命", GREEN), ("玉造", "★本命", GREEN), ("大国町", "★本命", GREEN),
                ("松屋町", "★本命", GREEN), ("平野", "▲要確認", RED)]
    sx, sw, sg = 0.035, 0.175, 0.015
    for i, (nm, tag, col) in enumerate(stations):
        x = sx + i * (sw + sg)
        ax.add_patch(FancyBboxPatch((x, 0.515), sw, 0.10, boxstyle="round,pad=0.004,rounding_size=0.008", fc="white", ec=col, lw=1.6))
        ax.text(x + sw/2, 0.578, nm, fontsize=12.5, fontweight="bold", color=DARK, ha="center", va="center")
        ax.text(x + sw/2, 0.535, tag, fontsize=10, fontweight="bold", color=col, ha="center", va="center")
    ax.text(0.035, 0.49, "※ 平野は総合スコア上位だが旧耐震×改装不明が多く、★本命とは分けて「要確認」に（額面の割安を鵜呑みにしない）",
            fontsize=8.6, color=RED, va="center")
    ax.add_patch(FancyBboxPatch((0.035, 0.135), 0.93, 0.325, boxstyle="round,pad=0.006,rounding_size=0.012", fc=LITE, ec=ORG, lw=1.8))
    ax.text(0.05, 0.43, "◆ この分析の見どころ（次ページ EVIDENCE で実証）", fontsize=12.5, fontweight="bold", color="#9a6a12", va="center")
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
    footer(ax, 1)
    return fig


# ========== PAGE 2 : EVIDENCE ==========
def page2():
    fig, ax = new_page()
    chrome(ax, "02", "EVIDENCE｜モデルの根拠と“安いだけ”を疑う目", 1)
    ax.text(0.035, 0.892, "見どころ①②を実証 ― なぜ“精度1位”を却下し、なぜ割安度とリスクを分けるのか",
            fontsize=13.5, fontweight="bold", color=DARK, va="center")

    # LEFT: model selection
    ax.text(0.035, 0.85, "■ 見どころ② ｜ 精度1位の Model F を“あえて”採用しなかった理由",
            fontsize=11, fontweight="bold", color=RED, va="center")
    cols = [(0.035, 0.165, "観点", "#dfe6ec"), (0.20, 0.145, "Model C（採用）", "#e7f1ea"), (0.345, 0.145, "Model F（不採用）", "#fcebe9")]
    # header
    for x, w, t, c in cols:
        ax.add_patch(Rectangle((x, 0.785), w, 0.045, fc=c, ec=EDGE, lw=0.8))
        ax.text(x + w/2, 0.8075, t, fontsize=8.8, fontweight="bold", color=DARK, ha="center", va="center")
    rows = [("平均誤差 MAE", "約12万/㎡", "約10万/㎡（最小）"),
            ("駅・区別の偏り", "小さい（ほぼ一様）", "郊外を過大評価"),
            ("順位への影響", "頑健", "“偽の割安”で歪む")]
    ry = 0.785
    for r0, r1, r2 in rows:
        ry -= 0.045
        for (x, w, _, _), val, tc in zip(cols, (r0, r1, r2), (DARK, GREEN, RED)):
            ax.add_patch(Rectangle((x, ry), w, 0.045, fc="white", ec=EDGE, lw=0.8))
            ax.text(x + w/2, ry + 0.0225, val, fontsize=8.6, color=tc, ha="center", va="center")
    # bias bars
    ax.text(0.035, 0.585, "区別の予測ズレ（log乖離・＋ほど過大予測＝偽の割安）", fontsize=8.8, fontweight="bold", color=DARK, va="center")
    bias = [("住吉", 0.39), ("平野", 0.33), ("西成", 0.21), ("中央", 0.04), ("西", 0.03)]
    bx0, bw = 0.135, 0.34
    for i, (w_, v) in enumerate(bias):
        y = 0.55 - i * 0.032
        ax.text(0.13, y, w_, fontsize=8.2, color=DARK, ha="right", va="center")
        ax.add_patch(Rectangle((bx0, y - 0.011), bw * (v / 0.45), 0.022, fc=ORG if v > 0.1 else "#9fb0bf", ec="none"))
        ax.text(bx0 + bw * (v / 0.45) + 0.006, y, f"+{v:.2f}", fontsize=7.6, color=SUB, va="center")
    ax.add_patch(FancyBboxPatch((0.035, 0.135), 0.43, 0.20, boxstyle="round,pad=0.006,rounding_size=0.01", fc=LITE, ec=ORG, lw=1.4))
    ax.text(0.05, 0.31, "採用基準＝精度ではなく「順位の頑健性」", fontsize=10, fontweight="bold", color="#9a6a12", va="center")
    ax.text(0.05, 0.275, "一様な誤差は順位を保つが、構造化した偏り\n（郊外だけ過大）は順位を壊す。最も当たる\nモデルでも、目的（割安駅の順位づけ）に合わ\nなければ採用しない。", fontsize=9, color=DARK, va="top")

    # RIGHT: adverse selection
    ax.text(0.51, 0.85, "■ 見どころ① ｜ 安い物件ほど“訳あり”が多い（逆選択）",
            fontsize=11, fontweight="bold", color=GREEN, va="center")
    ax.text(0.51, 0.815, "価格帯別の「旧耐震×改装不明」比率（イメージ／実数はダッシュボード）", fontsize=8.6, color=SUB, va="center")
    bands = [("最安帯", 0.58), ("安い", 0.41), ("中位", 0.27), ("高い", 0.14)]
    base_x, max_w = 0.62, 0.30
    for i, (lb, v) in enumerate(bands):
        y = 0.76 - i * 0.058
        ax.text(0.61, y, lb, fontsize=8.6, color=DARK, ha="right", va="center")
        ax.add_patch(Rectangle((base_x, y - 0.018), max_w * (v / 0.6), 0.036, fc=RED if i == 0 else "#d98b85", ec="none"))
        ax.text(base_x + max_w * (v / 0.6) + 0.006, y, f"{int(v*100)}%", fontsize=8, color=SUB, va="center")
    ax.add_patch(FancyBboxPatch((0.51, 0.135), 0.455, 0.34, boxstyle="round,pad=0.006,rounding_size=0.01", fc="#eef6ef", ec=GREEN, lw=1.4))
    ax.text(0.525, 0.445, "額面の安さ＝買い、ではない", fontsize=10.5, fontweight="bold", color="#2c6e49", va="center")
    ax.text(0.525, 0.405, "最も割安に見える帯ほど旧耐震×改装不明が集中する\n（＝市場が値段でリスクを織り込んでいる）。\n\nだから「割安度」と「建物リスク」を分けて評価し、\n割安なだけの駅を本命と即断しない。これが平野を\n★本命でなく▲要確認に置く理由。", fontsize=9, color=DARK, va="top")
    footer(ax, 2)
    return fig


# ========== PAGE 3 : ACTION ==========
def page3():
    fig, ax = new_page()
    chrome(ax, "03", "ACTION｜本命10駅と“次の一手”", 2)
    ax.text(0.035, 0.892, "見どころ③ ― 限界を明示したうえで、人が確認すべき優先順位を渡す",
            fontsize=13.5, fontweight="bold", color=DARK, va="center")

    # LEFT: 本命/要確認
    ax.text(0.035, 0.845, "■ 調査の出発点：本命と要確認", fontsize=11, fontweight="bold", color=DARK, va="center")
    ax.text(0.035, 0.80, "★ 本命（安定×低リスク：10駅）", fontsize=10, fontweight="bold", color=GREEN, va="center")
    honmei = ["堺筋本町", "玉造", "大国町", "松屋町", "ほか6駅"]
    for i, nm in enumerate(honmei):
        x = 0.035 + (i % 3) * 0.15
        y = 0.74 - (i // 3) * 0.06
        c = "#9fb0bf" if nm == "ほか6駅" else GREEN
        ax.add_patch(FancyBboxPatch((x, y - 0.022), 0.135, 0.044, boxstyle="round,pad=0.003,rounding_size=0.006", fc="white", ec=c, lw=1.4))
        ax.text(x + 0.0675, y, nm, fontsize=9.5, fontweight="bold", color=DARK, ha="center", va="center")
    ax.text(0.035, 0.59, "▲ 要確認（高スコアだがリスク高）", fontsize=10, fontweight="bold", color=RED, va="center")
    ax.add_patch(FancyBboxPatch((0.035, 0.50), 0.30, 0.06, boxstyle="round,pad=0.003,rounding_size=0.006", fc="#fcebe9", ec=RED, lw=1.4))
    ax.text(0.185, 0.53, "平野（旧耐震×改装不明が多い）", fontsize=9.5, fontweight="bold", color=RED, ha="center", va="center")
    ax.text(0.035, 0.455, "全66駅の順位・全本命リストはダッシュボード④（スクリーニング結果）参照", fontsize=8.4, color=SUB, va="center")

    # RIGHT: next actions
    ax.text(0.51, 0.845, "■ 次の一手（現地で確認する順）", fontsize=11, fontweight="bold", color=BLUE, va="center")
    acts = [("①", "現地・現物・周辺の実勢相場", "机上の割安が現地でも成立するか"),
            ("②", "謄本・管理組合・修繕積立の状態", "管理不全・係争・滞納の有無"),
            ("③", "旧耐震は耐震補強の履歴", "改装済≠耐震補強済。履歴を実確認")]
    for i, (no, t, subt) in enumerate(acts):
        y = 0.77 - i * 0.10
        ax.add_patch(FancyBboxPatch((0.51, y - 0.04), 0.455, 0.08, boxstyle="round,pad=0.004,rounding_size=0.008", fc=GRAY, ec=EDGE, lw=1.1))
        ax.text(0.535, y, no, fontsize=15, fontweight="bold", color=BLUE, ha="center", va="center")
        ax.text(0.565, y + 0.013, t, fontsize=10, fontweight="bold", color=DARK, va="center")
        ax.text(0.565, y - 0.018, subt, fontsize=8.4, color=SUB, va="center")

    # BOTTOM: limitations
    ax.add_patch(FancyBboxPatch((0.035, 0.135), 0.93, 0.20, boxstyle="round,pad=0.006,rounding_size=0.012", fc="#fcebe9", ec=RED, lw=1.6))
    ax.text(0.05, 0.305, "◆ この分析の限界（正直に明示）", fontsize=11.5, fontweight="bold", color="#a23b34", va="center")
    lims = ["成約データ＝相場の把握用。個別物件の購入可否は判断しない（“買うべき”とは言わない）。",
            "「割安」＝モデル相場より下振れ。訳あり・再建築不可・管理不全などの可能性を含む。",
            "最終判断は必ず人が現物・書類で行う。本ツールは“最初に調べる先”を絞る一次スクリーニング。"]
    for i, t in enumerate(lims):
        ax.text(0.05, 0.255 - i * 0.04, "・ " + t, fontsize=9.2, color=DARK, va="center")
    footer(ax, 3)
    return fig


with PdfPages(PDF) as pp:
    for i, f in enumerate((page1(), page2(), page3()), start=1):
        f.savefig(os.path.join(OUT, f"storyboard_p{i}.png"), dpi=120, bbox_inches="tight")
        pp.savefig(f, bbox_inches="tight")
        plt.close(f)
print("OK:", PDF)
