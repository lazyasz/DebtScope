"""Figures for the DebtScope IEEE paper. Every number comes from docs/BACKTEST.md or the trained model bundle."""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "figs")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "serif", "font.serif": ["Times New Roman", "Times", "DejaVu Serif"],
                     "font.size": 8, "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6,
                     "pdf.fonttype": 42})
DARK, MID, LIGHT, GREY = "#2f3e1f", "#6b8a47", "#b9c9a3", "#9a9a9a"


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


# Fig. 1 - training path and scoring path
fig, ax = plt.subplots(figsize=(7.1, 2.05))
ax.set_xlim(0, 100); ax.set_ylim(0, 30); ax.axis("off")


def box(x, y, w, h, text, fill="#ffffff"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.25,rounding_size=0.8", fc=fill, ec="#333333", lw=0.6))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=6.6, linespacing=1.15)


def arr(x1, y1, x2, y2):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="-|>", lw=0.6, color="#333333",
                                                                    mutation_scale=6))


ax.text(0.5, 28.6, "Offline training path", fontsize=7, style="italic")
row1 = [(0.5, "Technical Debt\nDataset\n(31 Apache projects)"), (17.5, "Bronze\n10 tables\n2,933,680 rows"),
        (34.5, "Silver\n9 tables\n52,428 SZZ links"), (51.5, "Gold feature store\n1,037,222 rows\n14 features"),
        (68.5, "Random Forest\nregressor\n(100 trees)"), (85.5, "Model bundle\n(fault count\npredictor)")]
for x, t in row1:
    box(x, 17.5, 13.5, 9.5, t, "#eef2e8")
for (x, _), (nx, _) in zip(row1, row1[1:]):
    arr(x + 14.0, 22.25, nx - 0.4, 22.25)
ax.text(0.5, 13.2, "Online scoring path (per user workspace)", fontsize=7, style="italic")
row2 = [(0.5, "User's GitHub\nrepository\n(own OAuth token)"), (17.5, "Scanner\nlizard metrics,\nGit churn, smells"),
        (34.5, "Model risk +\nstatic risk\n= TR"), (51.5, "Five-dimension\nscore\nTR, BI, U, M, Age"),
        (68.5, "Effort blend,\nquadrant,\nranked list"), (85.5, "Explanations,\nCopilot, Jira /\nNotion export")]
for x, t in row2:
    box(x, 1.5, 13.5, 9.5, t)
for (x, _), (nx, _) in zip(row2, row2[1:]):
    arr(x + 14.0, 6.25, nx - 0.4, 6.25)
arr(92.25, 17.2, 41.25, 11.4)
save(fig, "fig1_pipeline.pdf")

# Fig. 2 - feature importance of the trained model
imp = [("author_experience_commits", 42.21), ("refactoring_count", 20.05), ("estimated_loc", 10.68),
       ("is_java", 7.71), ("lines_removed", 5.42), ("churn", 5.38), ("lines_added", 4.35), ("is_test", 4.20)]
fig, ax = plt.subplots(figsize=(3.45, 1.95))
names = [n for n, _ in imp][::-1]; vals = [v for _, v in imp][::-1]
ax.barh(names, vals, color=[MID] * 6 + [DARK] * 2, height=0.62)
for i, v in enumerate(vals):
    ax.text(v + 0.6, i, f"{v:.1f}%", va="center", fontsize=6.6)
ax.set_xlim(0, 50); ax.set_xlabel("Mean decrease in impurity (%)")
ax.tick_params(axis="y", labelsize=6.6); ax.spines[["top", "right"]].set_visible(False)
save(fig, "fig2_importance.pdf")

# Fig. 3 - pooled AUC and Spearman rho with 95% bootstrap intervals (within-repo ranks, 372 files)
methods = ["DebtScope", "LOC only", "Churn only", "LOC+churn", "Random"]
auc = [(0.7906, 0.735, 0.842), (0.7694, 0.703, 0.830), (0.7639, 0.695, 0.825), (0.7731, 0.699, 0.838), (0.4905, 0.415, 0.568)]
rho = [(0.3648, 0.283, 0.431), (0.3399, 0.249, 0.417), (0.3359, 0.244, 0.412), (0.3466, 0.247, 0.428), (-0.0056, -0.099, 0.092)]
fig, axs = plt.subplots(1, 2, figsize=(3.45, 1.75))
for ax, data, lab, ref in [(axs[0], auc, "AUC-ROC", 0.5), (axs[1], rho, "Spearman $\\rho$", 0.0)]:
    y = range(len(methods))[::-1]
    for yi, (m, lo, hi), c in zip(y, data, [DARK, MID, MID, MID, GREY]):
        ax.plot([lo, hi], [yi, yi], color=c, lw=1.1)
        ax.plot(m, yi, "o", color=c, ms=3.2)
    ax.axvline(ref, color=GREY, lw=0.6, ls="--")
    ax.set_yticks(list(y)); ax.set_yticklabels(methods if ax is axs[0] else [])
    ax.set_xlabel(lab); ax.spines[["top", "right"]].set_visible(False)
save(fig, "fig3_pooled.pdf")

# Fig. 4 - paired bootstrap differences, DebtScope minus baseline (1,000 resamples on identical files)
base = ["LOC only", "Churn only", "LOC+churn", "Random"]
d_auc = [(0.0211, -0.0299, 0.0713), (0.0266, -0.0112, 0.0668), (0.0175, -0.0285, 0.0645), (0.3000, 0.1982, 0.3948)]
d_rho = [(0.0249, -0.0371, 0.0862), (0.0289, -0.0171, 0.0775), (0.0182, -0.0372, 0.0750), (0.3704, 0.2370, 0.4890)]
fig, axs = plt.subplots(1, 2, figsize=(3.45, 1.45))
for ax, data, lab in [(axs[0], d_auc, "$\\Delta$AUC"), (axs[1], d_rho, "$\\Delta\\rho$")]:
    y = range(len(base))[::-1]
    for yi, (m, lo, hi) in zip(y, data):
        c = DARK if lo > 0 else GREY
        ax.plot([lo, hi], [yi, yi], color=c, lw=1.1); ax.plot(m, yi, "o", color=c, ms=3.2)
    ax.axvline(0, color="#333333", lw=0.6)
    ax.set_yticks(list(y)); ax.set_yticklabels(base if ax is axs[0] else [])
    ax.set_xlabel(lab); ax.spines[["top", "right"]].set_visible(False)
save(fig, "fig4_paired.pdf")
print("figures written to", OUT)

# Fig. 5 - leave-one-repository-out pooled AUC (docs/BACKTEST.md, section 6B)
omit = ["flask", "requests", "express", "fastify", "gson", "javapoet"]
ds = [0.7813, 0.8135, 0.7908, 0.7834, 0.7877, 0.7955]
loc = [0.7484, 0.8281, 0.7675, 0.7550, 0.7531, 0.7715]
ch = [0.7455, 0.8158, 0.7613, 0.7299, 0.7654, 0.7672]
fig, ax = plt.subplots(figsize=(3.45, 1.7))
x = range(len(omit)); w = 0.26
ax.bar([i - w for i in x], ds, w, color=DARK, label="DebtScope")
ax.bar(list(x), loc, w, color=MID, label="LOC only")
ax.bar([i + w for i in x], ch, w, color=LIGHT, label="Churn only")
ax.set_xticks(list(x)); ax.set_xticklabels(omit, fontsize=6.6); ax.set_ylim(0.70, 0.85)
ax.set_ylabel("Pooled AUC"); ax.set_xlabel("Omitted repository")
ax.legend(fontsize=6.3, ncol=3, frameon=False, loc="upper center", bbox_to_anchor=(0.5, 1.2))
ax.spines[["top", "right"]].set_visible(False)
save(fig, "fig5_loro.pdf")

# Fig. 6 - regression error against the mean baseline
fig, ax = plt.subplots(figsize=(3.45, 1.45))
labs = ["MAE", "RMSE"]; b = [7.310, 20.477]; r = [4.739, 15.685]
ax.barh([1.2, 0.2], b, 0.35, color=GREY, label="Mean baseline")
ax.barh([0.85, -0.15], r, 0.35, color=DARK, label="Random Forest")
for y, v in zip([1.2, 0.2, 0.85, -0.15], b + r):
    ax.text(v + 0.3, y, f"{v:.2f}", va="center", fontsize=6.6)
ax.set_yticks([1.02, 0.02]); ax.set_yticklabels(labs); ax.set_xlim(0, 24); ax.set_xlabel("Faults per file (test set)")
ax.legend(fontsize=6.3, frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.28)); ax.spines[["top", "right"]].set_visible(False)
save(fig, "fig6_error.pdf")
