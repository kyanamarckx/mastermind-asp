from collections import Counter
from itertools import permutations

def feedback(code, guess):
    red = sum(c == g for c, g in zip(code, guess))
    common = sum((Counter(code) & Counter(guess)).values())
    return red, common - red

# How many codes are consistent with 1234 -> (1, 1)?
allCodes = list(permutations(range(1, 7), 4))
print(sum(feedback(c, (1, 2, 3, 4)) == (1, 1) for c in allCodes))
