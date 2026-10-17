"""步骤 ⑥ 痛点矩阵图。

输入：results/03_pain_matrix.csv（由 src/analyze.py 生成）
输出：results/pain_matrix.png
  横轴 = 提及条数，纵轴 = 负面占比，气泡大小 = 负面条数，
  气泡颜色 = 该方面负面评论中 ai_can_help 的比例（蓝色顺序色，越深 = AI 越能缓解）。
口径：非 generic 评论 141 条，比例只在过滤后的样本内有意义。
"""

from pathlib import Path

import warnings

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager
from matplotlib.colors import LinearSegmentedColormap, Normalize

matplotlib.use("Agg")
warnings.filterwarnings("ignore")
import logging
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "results/03_pain_matrix.csv"
OUT = ROOT / "results/pain_matrix.png"

FONT = "/System/Library/Fonts/Hiragino Sans GB.ttc"
font_manager.fontManager.addfont(FONT)
plt.rcParams["font.family"] = font_manager.FontProperties(fname=FONT).get_name()

SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"
# 参考色板的蓝色顺序色阶（step 150 → 650）
BLUES = LinearSegmentedColormap.from_list(
    "blues", ["#b7d3f6", "#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"])

# 标签位置微调（点距离很近时避免重叠），单位：点
OFFSET = {
    "质量/故障": (10, 6), "性价比": (-14, 10), "智能识别准确度": (12, -12),
    "使用方法与操作": (0, 22), "清洁力": (10, 6), "外观/手感/材质": (10, 6),
    "App 与连接": (10, 0), "牙龈敏感/出血": (10, 0), "刷头": (12, 10),
    "噪音/震感": (-14, 4), "续航/充电": (10, -6),
}


def main() -> None:
    d = pd.read_csv(SRC, encoding="utf-8-sig")
    ai = d["负面中_ai_can_help占比"].fillna(0)

    fig, ax = plt.subplots(figsize=(9, 6.2), dpi=200)
    fig.patch.set_facecolor(SURFACE)
    ax.set_facecolor(SURFACE)

    norm = Normalize(0, 0.8)
    sc = ax.scatter(d["提及条数"], d["负面占比"], s=d["负面条数"] * 45 + 30, c=ai, cmap=BLUES, norm=norm,
                    edgecolors=SURFACE, linewidths=2, zorder=3)

    for _, r in d.iterrows():
        dx, dy = OFFSET.get(r["tag_name"], (10, 0))
        ha = "right" if dx < 0 else "center" if dx == 0 else "left"
        ax.annotate(f"{r['tag_name']}", (r["提及条数"], r["负面占比"]), xytext=(dx, dy),
                    textcoords="offset points", ha=ha, va="center", fontsize=9.5, color=INK, zorder=4)

    ax.axhline(0.5, color=INK2, lw=0.8, ls=(0, (4, 4)), zorder=1)
    ax.text(52.5, 0.51, "负面占比 50%", fontsize=8, color=INK2, ha="right", va="bottom")

    ax.set_xlim(0, 54)
    ax.set_ylim(-0.04, 1.04)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_xlabel("提及条数（非 generic 评论，共 141 条）", color=INK2, fontsize=10)
    ax.set_ylabel("负面占比", color=INK2, fontsize=10)
    ax.grid(color=GRID, lw=0.6, zorder=0)
    for side in ["top", "right"]:
        ax.spines[side].set_visible(False)
    for side in ["left", "bottom"]:
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9)

    cb = fig.colorbar(sc, ax=ax, fraction=0.035, pad=0.02)
    cb.set_label("负面评论中 AI 能缓解的比例（ai_can_help）", color=INK2, fontsize=9)
    cb.ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    cb.ax.tick_params(colors=INK2, labelsize=8)
    cb.outline.set_visible(False)

    for n in [5, 10, 20]:
        ax.scatter([], [], s=n * 45 + 30, c="#cfcec9", edgecolors=SURFACE, label=f"{n} 条负面")
    ax.legend(title="气泡大小", loc="upper right", frameon=False, fontsize=8, title_fontsize=8,
              labelcolor=INK2, labelspacing=2.2, borderpad=1.2, handletextpad=1.6)

    ax.set_title("电动牙刷评论痛点矩阵（京东 6 个型号，方向性发现）", loc="left", fontsize=12.5, color=INK, pad=14)
    fig.text(0.01, 0.005, "数据：京东公开评论 171 条（中差评刻意多抽），排除空泛好评后 141 条。个人作品集项目，非 usmile 官方。",
             fontsize=7.5, color=INK2)
    fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(OUT, facecolor=SURFACE)
    print(f"已写出 {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
