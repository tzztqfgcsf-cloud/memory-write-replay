"""Decomposition of the complete-pipeline difference (controlled path minus Review).
Counts are the decomposition in analysis/expected_results.json; improvement is plotted to the right."""
from pathlib import Path
import matplotlib
matplotlib.use("pdf")
import matplotlib.pyplot as plt

plt.rcParams.update({
    "text.usetex": True,
    "text.latex.preamble": r"\usepackage[T1]{fontenc}\usepackage{libertine}\usepackage[libertine]{newtxmath}",
    "font.size": 8, "axes.linewidth": 0.5, "xtick.major.width": 0.5, "ytick.major.width": 0,
    "pdf.fonttype": 42,
})
EXACT, TOL = "#2a78d6", "#eb6834"   # categorical slots 1 and 2 (validated)
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
rows = ["Proposal term", "Gate: held APPEND", "Gate: held CORRECT", "Gate: invalid extraction", "Complete pipeline"]
# reference violations avoided = -(change in violations); positive changes gained = change in positives
viol = {"exact": [-67, 71, 11, 0, 15], "tol": [-40, 19, 11, 0, -10]}
pos = {"exact": [17, -36, 0, -4, -23], "tol": [44, -88, 0, -4, -48]}

fig, axes = plt.subplots(1, 2, figsize=(5.4, 2.15), sharey=True)
ys = [4.3, 3.3, 2.3, 1.3, 0.0]          # gap before the total row
h = 0.34
for ax, data, title, lim in [(axes[0], viol, r"Reference violations avoided", (-80, 80)),
                             (axes[1], pos, r"Positive changes gained", (-100, 60))]:
    for i, y in enumerate(ys):
        for off, key, col in [(h / 2 + 0.01, "exact", EXACT), (-h / 2 - 0.01, "tol", TOL)]:
            v = data[key][i]
            ax.barh(y + off, v, height=h, color=col, linewidth=0)
            if i == len(ys) - 1:
                ax.text(v + (2.5 if v >= 0 else -2.5), y + off, (f"${v:+d}$" if v else "0"),
                        va="center", ha="left" if v >= 0 else "right", color=INK, fontsize=7)
    ax.axvline(0, color=MUTED, linewidth=0.6)
    ax.axhline(0.65, color=GRID, linewidth=0.6)
    ax.set_xlim(*lim)
    ax.set_title(title, fontsize=8, loc="left", color=INK, pad=4)
    ax.grid(axis="x", color=GRID, linewidth=0.4)
    ax.set_axisbelow(True)
    for s in ["top", "right", "left"]:
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(axis="x", colors=MUTED, labelsize=7)
    ax.text(1.0, 1.015, r"\textit{right is better}", transform=ax.transAxes, ha="right", va="bottom", color=MUTED, fontsize=7)
axes[0].set_yticks(ys)
axes[0].set_yticklabels(rows, color=INK)
axes[0].set_xlabel("Observations of 3,024", color=MUTED, fontsize=7, labelpad=2)
axes[1].set_xlabel("Observations of 1,764", color=MUTED, fontsize=7, labelpad=2)
from matplotlib.patches import Patch
fig.legend(handles=[Patch(color=EXACT, label="Exact reference"), Patch(color=TOL, label="Variant-tolerant reference")],
           loc="upper center", ncol=2, frameon=False, fontsize=7.5, bbox_to_anchor=(0.6, 1.02), handlelength=1.2)
fig.subplots_adjust(left=0.24, right=0.985, top=0.80, bottom=0.2, wspace=0.12)
fig.savefig(Path(__file__).resolve().parent / "figure_10.pdf")
