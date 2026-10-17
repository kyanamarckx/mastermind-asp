# IMPORTS
import csv
import argparse
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from pathlib import Path


# FUNCTIONS
def read(path):
    if not path or not Path(path).exists():
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def series(rows, key, **where):
    sel = [r for r in rows if all(r[k] == str(v) for k, v in where.items())]
    sel.sort(key=lambda r: int(r["k"]))

    return [int(r["k"]) for r in sel], [float(r[key]) for r in sel]


def finish(ax, title, ylabel, out):
    ax.set_title(title)
    ax.set_xlabel("Number of colors k (p = 4)")
    ax.set_ylabel(ylabel)
    ax.grid(alpha=0.3)
    ax.legend()
    ax.figure.tight_layout()
    ax.figure.savefig(out, dpi=200)
    plt.close(ax.figure)

    print(f"Saved plot to {out}")


def main():
    ap = argparse.ArgumentParser(description="Plot results of Mastermind ASP solver")
    ap.add_argument("--norep", default="2-normal/results_main/summary.csv", help="Path to results of normal solver (default: 2-normal/results_main/summary.csv)")
    ap.add_argument("--rep", default="3-repetitions/results_repetitions/results.csv", help="Path to results of solver with repetitions (default: 3-repetitions/results_repetitions/results.csv)")
    ap.add_argument("--out", default="4-plots/figures", help="Output directory for plots (default: 4-plots/figures)")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(exist_ok=True)

    norep, rep = read(args.norep), read(args.rep)

    # Playing strength: average number of guesses
    fig, ax = plt.subplots(figsize=(6, 4))

    if norep:
        x, y = series(norep, "avg_turns")
        ax.plot(x, y, marker="o", label="No repetitions")

    for enc, style in (("A", "s--"), ("B", "^:")):
        if rep:
            x, y = series(rep, "avg_turns", encoding=enc)
            ax.plot(x, y, style, label=f"Repetitions ({enc})")

    finish(ax, "Average number of guesses", "Average number of guesses", out / "avg_turns.png")


    # Calculation time: average time per game (grounding + solving)
    fig, ax = plt.subplots(figsize=(6, 4))

    if norep:
        x, y = series(norep, "ms_per_game")
        ax.plot(x, y, marker="o", label="No repetitions")
    if rep:
        for enc, style in (("A", "s--"), ("B", "^:")):
            x, g = series(rep, "ground_ms_per_game", encoding=enc)
            _, s = series(rep, "solve_ms_per_game", encoding=enc)
            ax.plot(x, [a + b for a, b in zip(g, s)], style, label=f"Repetitions ({enc})")

    finish(ax, "Average time per game", "Average time per game [ms] (grounding + solving)", out / "ms_per_game.png")


    # Size of grounded program
    if rep:
        fig, ax = plt.subplots(figsize=(6, 4))
        for enc, style in (("A", "s--"), ("B", "^:")):
            x, y = series(rep, "avg_rules", encoding=enc)
            ax.plot(x, y, style, label=f"Repetitions ({enc})")
        
        finish(ax, "Size of grounded program (with repetitions)", "Average number of rules", out / "ground_size.png")



if __name__ == "__main__":
    main()
