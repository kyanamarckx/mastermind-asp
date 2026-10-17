# IMPORTS
import sys
import csv
import time
import clingo
import random
import argparse
import platform

from pathlib import Path
from itertools import product
from collections import Counter



# CONSTANT VARIABLES
MAX_TURNS = 12

BASE = """
position(1..p).
color(1..k).

% Repetitions variant: each position can be assigned any color
1 { code(P, C) : color(C) } 1 :- position(P).
"""

# Encoding A: count with #min
BASE_A = "nc(C, N) :- color(C), N = #count{ P :  code(P, C) }.\n"
RULES_A = """
red({turn}, N) :- N = #count{{ P : guess({turn}, P, C), code(P, C) }}.
ng({turn}, C, N) :- color(C), N = #count{{ P : guess({turn}, P, C) }}.
m({turn}, C, M) :- ng({turn}, C, A), nc(C, R), M = #min{{ A; R }}.
common({turn}, S) :- S = #sum{{ M, C : m({turn}, C, M) }}.
"""

# Encoding B: count without #min
BASE_B = "cocc(C, I) :- color(C), I = 1..p, I <= #count{ P : code(P, C) }.\n"
RULES_B = """
red({turn}, N) :- N = #count{{ P : guess({turn}, P, C), code(P, C) }}.
gocc({turn}, C, I) :- color(C), I = 1..p, I <= #count{{ P : guess({turn}, P, C) }}.
common({turn}, N) :- N = #count{{ C, I : gocc({turn}, C, I), cocc(C, I) }}.
"""

TESTS = """
:- feedback({turn}, R, _), red({turn}, N), N != R.
:- feedback({turn}, R, W), common({turn}, N), N != R+W.
"""

ENCODINGS = {
    "A": (BASE_A, RULES_A),
    "B": (BASE_B, RULES_B)
}


# FUNCTIONS
def feedback(code, guess):
    red = sum(c == g for c, g in zip(code, guess))
    common = sum((Counter(code) & Counter(guess)).values())
    
    return red, common - red


def turn_program(turn, guess, feedback, encoding):
    facts = "".join(f"guess({turn}, {p}, {c}). " for p, c in enumerate(guess, 1))
    facts += f"feedback({turn}, {feedback[0]}, {feedback[1]}). "

    return facts + (ENCODINGS[encoding][1] + TESTS).format(turn=turn)


def new_control(p, k, encoding, models=1):
    ctrl = clingo.Control([str(models), "--warn=none", "--stats"])
    ctrl.add("base", [], f"#const p = {p}. #const k = {k}. " + BASE + ENCODINGS[encoding][0])
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

    return tuple(code[i] for i in sorted(code)), False


def ground_size(ctrl):
    lp = ctrl.statistics["problem"]["lp"]

    return int(lp["rules"]), int(lp["atoms"])


def play(secret, p, k, first_guess, encoding, timeout):
    start = time.perf_counter()
    ctrl = new_control(p, k, encoding)
    guess = first_guess
    status = "failed"
    turns = None
    tg = ts = 0.0

    for turn in range(1, MAX_TURNS + 1):
        fb = feedback(secret, guess)
        if fb[0] == p:
            status = "solved"
            turns = turn
            break
        if turn == MAX_TURNS:
            break

        t0 = time.perf_counter()
        ctrl.add(f"turn{turn}", [], turn_program(turn, guess, fb, encoding))
        ctrl.ground([(f"turn{turn}", [])])
        t1 = time.perf_counter()
        time_left = timeout - (t1 - start)
        guess, timed_out = first_model(ctrl, time_left)
        t2 = time.perf_counter()
        tg += t1 - t0
        ts += t2 - t1

        if timed_out:
            status = "timeout"
            break
        if guess is None:
            raise RuntimeError(f"No valid guess found on turn {turn}.")

    rules, atoms = ground_size(ctrl)

    return {
        "status": status,
        "turns": turns,
        "ground_time": tg,
        "solve_time": ts,
        "rules": rules,
        "atoms": atoms
    }


def first_guess_for(p):
    half = p // 2

    return tuple([1] * half + [2] * (p - half))


def choose_codes(p, k, max_exhaustive, sample, seed):
    n = k ** p
    if n <= max_exhaustive:
        return list(product(range(1, k + 1), repeat=p)), "exhaustive"

    rng = random.Random(seed * 1000 + k)

    return sorted({tuple(rng.randint(1, k) for _ in range(p)) for _ in range(sample)}), "sample"


def validate(p=3, k=4):
    all_codes = list(product(range(1, k + 1), repeat=p))
    rng = random.Random(0)
    bad = checks = 0

    for encoding in "AB":
        for _ in range(30):
            secret = rng.choice(all_codes)
            ctrl = new_control(p, k, encoding, models=0)
            history = []

            for turn in range(1, 4):
                guess = rng.choice(all_codes)
                fb = feedback(secret, guess)
                history.append((guess, fb))
                ctrl.add(f"turn{turn}", [], turn_program(turn, guess, fb, encoding))
                ctrl.ground([(f"turn{turn}", [])])
                n = [0]
                ctrl.solve(on_model=lambda m: n.__setitem__(0, n[0] + 1))
                ref = sum(all(feedback(c, g) == f for g, f in history) for c in all_codes)
                checks += 1
                bad += n[0] != ref

    print(f"Validation p={p}, k={k}: {checks} checks, {bad} bad results")
    return bad == 0


def main():
    ap = argparse.ArgumentParser(description="Mastermind ASP solver with color repetitions")
    ap.add_argument("--p", type=int, default=4, help="Number of positions (default: 4)")
    ap.add_argument("--kmin", type=int, default=4, help="Minimum number of colors (default: 4)")
    ap.add_argument("--kmax", type=int, default=10, help="Maximum number of colors (default: 10)")
    ap.add_argument("--max-exhaustive", type=int, default=2000, help="Maximum number of codes for exhaustive search (default: 2000)")
    ap.add_argument("--sample", type=int, default=300, help="Number of codes to sample when exceeding max-exhaustive (default: 300)")
    ap.add_argument("--seed", type=int, default=42, help="Random seed for sampling (default: 42)")
    ap.add_argument("--timeout", type=float, default=60.0, help="Timeout in seconds for each game (default: 60.0)")
    ap.add_argument("--output", default="3-repetitions/results_repetitions", help="Output directory for results (default: results_repetitions)")
    ap.add_argument("--validate", action="store_true", help="Run validation tests (default: False)")
    args = ap.parse_args()

    if args.validate:
        ok = validate(p=3, k=4) and validate(p=4, k=3) and validate(p=3, k=5)
        sys.exit(0 if ok else 1)

    out = Path(args.output)
    out.mkdir(exist_ok=True, parents=True)
    print(f"clingo version {clingo.__version__}, python {platform.python_version()}, platform {platform.platform()}, seed {args.seed}, timeout {args.timeout}s")

    first = first_guess_for(args.p)
    rows = []

    with open(out / "games.csv", "w", newline="") as f:
        games_w = csv.writer(f)
        games_w.writerow(["p", "k", "encoding", "secret", "status", "turns", "ground_s", "solve_s", "rules", "atoms"])
        for k in range(max(args.kmin, 2), args.kmax + 1):
            codes, mode = choose_codes(args.p, k, args.max_exhaustive, args.sample, args.seed)
            for encoding in "AB":
                status, solved = Counter(), []
                tg = ts = rules = atoms = 0.0

                for secret in codes:
                    r = play(secret, args.p, k, first, encoding, args.timeout)
                    status[r["status"]] += 1
                    tg += r["ground_time"]
                    ts += r["solve_time"]
                    rules += r["rules"]
                    atoms += r["atoms"]

                    if r["status"] == "solved":
                        solved.append(r["turns"])

                    games_w.writerow([args.p, k, encoding, "".join(map(str, secret)), r["status"], r["turns"] or "", f"{r['ground_time']:.4f}", f"{r['solve_time']:.4f}", r["rules"], r["atoms"]])

                n = len(codes)
                row = {
                    "p": args.p,
                    "k": k,
                    "encoding": encoding,
                    "mode": mode,
                    "games": n,
                    "solved": status["solved"],
                    "failed": status["failed"],
                    "timeout": status["timeout"],
                    "success_rate": round(status["solved"] / n, 4),
                    "avg_turns": round(sum(solved) / len(solved), 4) if solved else "",
                    "max_turns": max(solved) if solved else "",
                    "ground_ms_per_game": round(1000 * tg / n, 2),
                    "solve_ms_per_game": round(1000 * ts / n, 2),
                    "avg_rules": round(rules / n, 2),
                    "avg_atoms": round(atoms / n, 2)
                }

                assert sum(status.values()) == n, f"Status counts do not sum to total games for p={args.p}, k={k}, encoding={encoding}"
                print(row, flush=True)
                rows.append(row)

    with open(out / "results.csv", "w", newline="") as f:
        results_w = csv.DictWriter(f, fieldnames=rows[0].keys())
        results_w.writeheader()
        results_w.writerows(rows)

    print(f"Results written to {out / 'results.csv'}")



if __name__ == "__main__":
    main()
