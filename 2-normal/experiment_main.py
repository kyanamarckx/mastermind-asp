# IMPORTS
import sys
import csv
import time
import clingo
import random
import argparse
import platform

from pathlib import Path
from itertools import permutations
from collections import Counter, defaultdict



# CONSTANT VARIABLES
MAX_TURNS = 12

BASE = """
position(1..p).
color(1..k).

% Generate: each position gets assigned exactly one color
1 { code(P, C) : color(C) } 1 :- position(P).

% Main variant: a color can only be used once in a code
{ code(P, C) : position(P) } 1 :- color(C).
"""


# FUNCTIONS
def feedback(code, guess):
    red = sum(c == g for c, g in zip(code, guess))
    common = sum((Counter(code) & Counter(guess)).values())
    
    return red, common - red


def turn_program(turn, guess, feedback):
    facts = "".join(f"guess({turn}, {p}, {c}). " for p, c in enumerate(guess, 1))
    facts += f"feedback({turn}, {feedback[0]}, {feedback[1]}). "

    rules = f"""
    red({turn}, N) :- N = #count{{ P : guess({turn}, P, C), code(P, C) }}.
    common({turn}, N) :- N = #count{{ C : guess({turn}, _, C), code(_, C) }}.
    :- feedback({turn}, R, _), red({turn}, N), N != R.
    :- feedback({turn}, R, W), common({turn}, N), N != R+W.
    """

    return facts + rules


def new_control(p, k):
    ctrl = clingo.Control(["1", "--warn=none"])
    ctrl.add("base", [], f"#const p = {p}. #const k = {k}. " + BASE)
    ctrl.ground([("base", [])])
    
    return ctrl


def first_model(ctrl, time_left):
    found = []
    with ctrl.solve(on_model=lambda m: found.append(m.symbols(atoms=True)), async_=True) as handle:
        if not handle.wait(max(time_left, 0.001)):
            handle.cancel()
            handle.get()
            return None, True
        if not found:
            return None, False

        syms = [s for s in found[0] if s.name == "code"]
        code = {s.arguments[0].number: s.arguments[1].number for s in syms}

        return tuple(code[p] for p in sorted(code)), False


def play(secret, p, k, first_guess, timeout):
    start = time.perf_counter()
    ctrl = new_control(p, k)
    guess = first_guess
    ground_times, solve_times = [], []
    status = "failed"
    turns = None

    for turn in range(1, MAX_TURNS + 1):
        fb = feedback(secret, guess)
        if fb[0] == p:
            status = "solved"
            turns = turn
            break
        if turn == MAX_TURNS:
            break

        t0 = time.perf_counter()
        ctrl.add(f"turn{turn}", [], turn_program(turn, guess, fb))
        ctrl.ground([(f"turn{turn}", [])])
        t1 = time.perf_counter()
        guess, timed_out = first_model(ctrl, timeout - (t1 - start))
        t2 = time.perf_counter()
        ground_times.append(t1 - t0)
        solve_times.append(t2 - t1)

        if timed_out:
            status = "timeout"
            break
        if guess is None:
            raise RuntimeError(f"No valid guess found on turn {turn}.")

    return {"status": status, "turns": turns, "ground": ground_times, "solve": solve_times}


def choose_codes(p, k, max_exhaustive, sample, seed):
    codes = list(permutations(range(1, k + 1), p))
    if len(codes) <= max_exhaustive:
        return codes, "exhaustive"

    rng = random.Random(seed * 1000 + k)

    return sorted(rng.sample(codes, sample)), "sample"


def run_k(p, k, args, games_w, turns_acc):
    first = tuple(range(1, p + 1))
    codes, mode = choose_codes(p, k, args.max_exhaustive, args.sample, args.seed)
    solved, statuses = [], Counter()
    tg = ts = 0.0
    for secret in codes:
        r = play(secret, p, k, first, args.timeout)
        statuses[r["status"]] += 1
        g, s = sum(r["ground"]), sum(r["solve"])
        tg += g
        ts += s

        if r["status"] == "solved":
            solved.append(r["turns"])
        for i, (gt, st) in enumerate(zip(r["ground"], r["solve"]), start=2):
            turns_acc[(k, i)].append((gt, st))

        games_w.writerow([p, k, "".join(map(str, secret)), r["status"], r["turns"] or "", f"{g:.4f}", f"{s:.4f}"])
        
    n = len(codes)
    row = {
        "p": p,
        "k": k,
        "mode": mode,
        "games": n,
        "solved": statuses["solved"],
        "timeout": statuses["timeout"],
        "failed": statuses["failed"],
        "success_rate": round(statuses["solved"] / n, 4),
        "avg_turns": round(sum(solved) / len(solved), 4) if solved else "",
        "max_turns": max(solved) if solved else "",
        "ground_s_total": round(tg, 4),
        "solve_s_total": round(ts, 4),
        "ms_per_game": round(1000 * (tg + ts) / n, 2),
    }
    print(row, flush=True)

    return row


def main():
    ap = argparse.ArgumentParser(description="Mastermind ASP solver")
    ap.add_argument("--p", type=int, default=4, help="Number of positions")
    ap.add_argument("--kmin", type=int, default=4, help="Minimum number of colors")
    ap.add_argument("--kmax", type=int, default=10, help="Maximum number of colors")
    ap.add_argument("--max-exhaustive", type=int, default=2000, help="Maximum number of codes to solve exhaustively")
    ap.add_argument("--sample", type=int, default=300, help="Number of codes to sample if not exhaustive")
    ap.add_argument("--seed", type=int, default=42, help="Random seed for sampling codes")
    ap.add_argument("--timeout", type=float, default=60.0, help="Timeout in seconds for each game")
    ap.add_argument("--output", default="2-normal/results_main", help="Output for results")
    args = ap.parse_args()

    out = Path(args.output)
    out.mkdir(exist_ok=True)
    print(f"clingo version: {clingo.__version__}, python: {platform.python_version()}, platform: {platform.platform()}, seed: {args.seed}, timeout: {args.timeout}s")

    turns_acc = defaultdict(list)
    summary = []
    with open(out / "games.csv", "w", newline="") as f:
        games_w = csv.writer(f)
        games_w.writerow(["p", "k", "secret", "status", "turns", "ground_s", "solve_s"])
        for k in range(max(args.kmin, args.p), args.kmax + 1):
            row = run_k(args.p, k, args, games_w, turns_acc)
            summary.append(row)

    with open(out / "summary.csv", "w", newline="") as f:
        summary_w = csv.DictWriter(f, fieldnames=summary[0].keys())
        summary_w.writeheader()
        summary_w.writerows(summary)

    with open(out / "turns.csv", "w", newline="") as f:
        turns_w = csv.writer(f)
        turns_w.writerow(["k", "guess_nr", "n", "mean_ground_ms", "mean_solve_ms"])
        for (k, turn), times in sorted(turns_acc.items()):
            n = len(times)
            turns_w.writerow([k, turn, n, round(1000 * sum(t[0] for t in times) / n, 3), round(1000 * sum(t[1] for t in times) / n, 3)])

    print(f"Results written to {out.resolve()}")



if __name__ == "__main__":
    sys.exit(main())
