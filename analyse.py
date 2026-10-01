#!/usr/bin/env python3
"""Charts sur les exports BehaviorSpace (NetLogo).

Usage:  python analyse.py [dossier_csv]
Produit des PNG dans charts/ et un resume des agregats dans charts/resume.csv
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import PercentFormatter

BASE = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
OUT = BASE / "charts"
SKIPROWS = 6  # 6 lignes d'en-tete BehaviorSpace avant les noms de colonnes

METRIC = "normalized-max-avg-idleness"
MEAN, STD = f"(mean) {METRIC}", f"(std) {METRIC}"

COLORS = {
    "cognitif": "#1f77b4",
    "max-idle": "#ff7f0e",
    "random": "#2ca02c",
    "do nothing": "#d62728",
}
N_STRATEGIES = 4


def find(prefix):
    matches = sorted(p for p in BASE.glob(f"*{prefix}*.csv") if not p.name.startswith("."))
    if not matches:
        raise SystemExit(f"aucun fichier *{prefix}*.csv dans {BASE}")
    return matches[0]


def load(prefix):
    df = pd.read_csv(find(prefix), skiprows=SKIPROWS)
    df.columns = [c.strip() for c in df.columns]
    return df


def save(fig, name):
    path = OUT / name
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"  -> {path}")


def main():
    OUT.mkdir(exist_ok=True)
    table = load("table")
    stats = load("stats")
    strategies = sorted(stats["strategie"].unique())
    patrols = sorted(table["n-patrouille"].unique())
    final_step = int(stats["[step]"].max())

    print(f"{len(table)} lignes table, {len(stats)} lignes stats, {final_step} steps")

    # --- 1. evolution temporelle de la moyenne, un panneau par strategie --------
    fig, axes = plt.subplots(1, N_STRATEGIES, figsize=(5 * N_STRATEGIES, 4.5), sharey=True)
    for ax, strat in zip(axes, strategies):
        sub = stats[stats["strategie"] == strat]
        for n, g in sub.groupby("n-patrouille"):
            ax.plot(g["[step]"], g[MEAN], label=f"n={n}", lw=1.4)
        ax.set_title(strat)
        ax.set_xlabel("step")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("idle moyen normalise")
    axes[-1].legend(fontsize=8, title="n-patrouille")
    fig.suptitle("Evolution de l'idle moyen normalise")
    save(fig, "1-evolution-moyenne.png")

    # --- 2. valeur finale : boxplot par strategie, groupe par n-patrouille -----
    ends = stats[stats["[step]"] == final_step]
    endruns = table[table["[step]"] == final_step]
    # echelle y libre par panneau : les strategies n'ont pas les memes ordres de grandeur
    fig, axes = plt.subplots(1, N_STRATEGIES, figsize=(4 * N_STRATEGIES, 4.5))
    for ax, strat in zip(axes, strategies):
        vals = [endruns.loc[(endruns["strategie"] == strat) & (endruns["n-patrouille"] == n), METRIC]
                for n in patrols]
        ax.boxplot(vals, tick_labels=[str(n) for n in patrols], showmeans=True)
        ax.set_title(f"{strat}  (moyenne={ends[ends['strategie'] == strat][MEAN].iloc[0]:.1f})")
        ax.set_xlabel("n-patrouille")
        ax.grid(alpha=0.3, axis="y")
    axes[0].set_ylabel("idle normalise au step final")
    fig.suptitle(f"Distribution par run au step {final_step}")
    save(fig, "2-boxplot-final.png")

    # --- 3. heatmap step x n-patrouille, un panneau par strategie -------------
    fig, axes = plt.subplots(1, N_STRATEGIES, figsize=(5.5 * N_STRATEGIES, 4.2), sharey=True)
    vmax = ends[MEAN].max()
    for ax, strat in zip(axes, strategies):
        sub = stats[stats["strategie"] == strat]
        piv = sub.pivot_table(index="n-patrouille", columns="[step]", values=MEAN)
        im = ax.imshow(piv.to_numpy(), aspect="auto", origin="lower", cmap="viridis",
                       vmin=0, vmax=vmax, extent=[piv.columns.min(), piv.columns.max(),
                                                  piv.index.min() - 0.5, piv.index.max() + 0.5])
        ax.set_title(strat)
        ax.set_xlabel("step")
        fig.colorbar(im, ax=ax, label="idle moyen")
    axes[0].set_ylabel("n-patrouille")
    fig.suptitle("Carte de chaleur idle moyen (n-patrouille x step)")
    save(fig, "3-heatmap.png")

    # --- 4. temps pour atteindre 90% de la valeur finale -----------------------
    rows = []
    fig, ax = plt.subplots(figsize=(9, 4.5))
    width = 0.8 / len(strategies)
    x = range(len(patrols))
    for i, strat in enumerate(strategies):
        xs, ys = [], []
        for j, n in enumerate(patrols):
            sub = stats[(stats["strategie"] == strat) & (stats["n-patrouille"] == n)].sort_values("[step]")
            target = 0.9 * sub[MEAN].iloc[-1]
            reached = sub.loc[sub[MEAN] >= target, "[step]"]
            xs.append(j + i * width)
            ys.append(reached.min() if len(reached) else float("nan"))
        ax.bar(xs, ys, width=width, label=strat, color=COLORS.get(strat))
        for a, b in zip(xs, ys):
            rows.append({"strategie": strat, "n-patrouille": patrols[int(a - i * width)],
                         "step_90pct": b})
    ax.set_xticks([v + width * (len(strategies) - 1) / 2 for v in x])
    ax.set_xticklabels(patrols)
    ax.set_xlabel("n-patrouille")
    ax.set_ylabel("step ou 90% du palier final est atteint")
    ax.yaxis.set_major_formatter(PercentFormatter(final_step))
    ax.set_ylim(0, final_step)
    ax.set_title("Convergence : temps pour atteindre 90% de la valeur finale")
    ax.legend()
    ax.grid(alpha=0.3, axis="y")
    save(fig, "4-convergence.png")
    pd.DataFrame(rows).to_csv(OUT / "resume-convergence.csv", index=False)

    # --- 5. ecart-type entre runs au cours du temps ----------------------------
    fig, axes = plt.subplots(1, N_STRATEGIES, figsize=(5 * N_STRATEGIES, 4.2), sharey=True)
    for ax, strat in zip(axes, strategies):
        sub = stats[stats["strategie"] == strat]
        piv = sub.pivot_table(index="n-patrouille", columns="[step]", values=STD)
        for n in patrols:
            if n in piv.index:
                ax.plot(piv.columns, piv.loc[n], lw=1.3, label=f"n={n}")
        ax.set_title(strat)
        ax.set_xlabel("step")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("ecart-type entre runs")
    axes[-1].legend(fontsize=8, title="n-patrouille")
    fig.suptitle("Dispersion entre runs (1 run = pas de variance, sauf 'do nothing')")
    save(fig, "5-ecart-type.png")

    # --- 6. tableau de synthese ------------------------------------------------
    summary = (ends.groupby(["strategie", "n-patrouille"])[MEAN]
               .agg(["mean", "std", "count"])
               .rename(columns={"mean": "idle_moyen_final", "std": "idle_ecart_type_final",
                                "count": "n_runs"})
               .reset_index())
    summary.to_csv(OUT / "resume-final.csv", index=False)
    print("\nValeur finale par strategie :")
    print(summary.pivot(index="n-patrouille", columns="strategie",
                        values="idle_moyen_final").round(2).to_string())


if __name__ == "__main__":
    main()
