# IMPORTS
import sys
import time
import clingo
from collections import Counter
from itertools import permutations



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


def new_control(p, k, models=1):
    ctrl = clingo.Control([str(models), "--warn=none"])
    ctrl.add("base", [], f"#const p = {p}. #const k = {k}. " + BASE)
    ctrl.ground([("base", [])])
    
    return ctrl


def first_model(ctrl):
    found = []
    ctrl.solve(on_model=lambda m: found.append(m.symbols(atoms=True)))

    if not found:
        return None
    syms = [s for s in found[0] if s.name == "code"]
    code = {s.arguments[0].number: s.arguments[1].number for s in syms}

    return tuple(code[i] for i in sorted(code))


def play(secret, p, k, first_guess):
    ctrl = new_control(p, k)
    guess = first_guess
    turn_ground = turn_solve = 0.0

    for turn in range(1, MAX_TURNS + 1):
        fb = feedback(secret, guess)
        if fb[0] == p:
            # print(f"Turn {turn}: guess {guess} -> feedback {fb} (correct!)")
            return turn, turn_ground, turn_solve

        t0 = time.perf_counter()
        ctrl.add(f"turn{turn}", [], turn_program(turn, guess, fb))
        ctrl.ground([(f"turn{turn}", [])])
        t1 = time.perf_counter()
        guess = first_model(ctrl)
        turn_solve += time.perf_counter() - t1
        turn_ground += t1 - t0

        if guess is None:
            raise RuntimeError(f"No valid guess found on turn {turn}.")

    return None, turn_ground, turn_solve


def run_all(p, k):
    first = tuple(range(1, p+1))
    results, turn_ground, turn_solve = [], 0.0, 0.0

    for secret in permutations(range(1, k+1), p):
        n, g, s = play(secret, p, k, first)
        results.append(n)
        turn_ground += g
        turn_solve += s

    solved = [n for n in results if n is not None]
    print(f"p={p}, k={k}: {len(results)} codes, solved {len(solved)} games")
    print(f"\t Average: {sum(solved)/len(solved):.4f}, max: {max(solved)}, min: {min(solved)}")
    print(f"\t Spread: {sorted(Counter(solved).items())}")
    print(f"\t Grounding time: {turn_ground:.2f}s, Solving time: {turn_solve:.2f}s")



if __name__ == "__main__":
    p = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    k = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    run_all(p, k)
