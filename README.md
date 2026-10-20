# :game_die: Mastermind in ASP - Consistent-Guess Strategy
> Kyana Marckx

This repository contains the work developed for the *Model-based AI* course assignment. The project focuses on modeling the board game Mastermind in Answer Set Programming (ASP) with [clingo](https://potassco.org/clingo/), and on studying how a simple codebreaker strategy scales with the number of colors.

A codebreaker is modeled in ASP: the answer sets are exactly the codes that are consistent with all feedback received so far, and the strategy plays the first answer set found. Two rule variants are studied (colors may or may not repeated within a code), and two ASP encodings of the white-peg feedback are compared.

A final report summarizes the research questions, modeling decisions, experimental setup, results, and conclusions.

_____
### Repository structure
````text
mastermind-asp
├── 1-installations/
│   └── install.py
├── 2-normal/
│   ├── experiment_main.py
│   └── results_main/
│       ├── games.csv
│       ├── summary.csv
│       └── turns.csv
├── 3-repetitions/
│   ├── experiment_repetitions.py
│   └── results_repetitions/
│       ├── games.csv
│       └── results.csv
├── 4-plots/
│   ├── plot.py
│   └── figures/
│       ├── avg_turns.png
│       ├── ground_size.png
│       └── ms_per_game.png
├── E-testings/
│   ├── example.lp
│   ├── feedback.py
│   ├── mastermind.lp
│   └── mastermind.py
├── report/
│   └── Report_MastermindASP-KyanaMarckx.pdf
└── README.md
````

_____
### Application domain: *Game solving - Mastermind*
Mastermind is a code-breaking game for two players. The codemaker hides a code of $p$ colored pegs (here $p=4$, with $k$ colors to choose from). The codebreaker guesses and receives two numbers as feedback: the red (or black, depending on the game variant) pegs (right color, right position) and the white pegs (right color, wrong position each peg counted at most once). The game ends when the code is found or after 12 guesses have been made.

The project studies the following question:
> How do playing strength and computational cost of a consistent-guess Mastermind strategy implemented in ASP scale with the number of colors $k$, for codes of four positions ($p=4$), and how do the rules (repetition of colors allowed or not) and the encoding of the feedback influence this?


## :jigsaw: 1 - Model the game in ASP
In the first part, Mastermind is formalised as an ASP program following the *generate - define - test* pattern. The codemaker is passive (a fixed secret code), and the codebreaker uses a multi-shot clingo loop: after every guess and its feedback are added as new program parts, and the solver is asked for one consistent code.

### Main activities
- Formalisation of the rules and the feedback (red pegs, total color matches, white pegs)
- A generating choice rule for the code, with an extra rule fr the variant **without** repetition
- Feedback constraints that remove all codes inconsistent with earlier guesses
- Two encodings of the color matches for the variant **with** repetition:
  - **Encoding A**: per color the minimum occurrences in guess and code (`#min` and `#sum`)
  - **Encoding B**: unary occurrence indexing (`cocc/2`, `gocc/3`) with only `#count`
- A multi-shot Python driver that plays complete games under the 12-guess limit with a fixed first guess ((1,2,3,4) without repetition, (1,1,2,2) with repetition)
- Validation of the encodings against a brute-force Python reference

### Validation
Both encodings are validated by comparing the number of answer sets after random guesses and feedback with the number of consistent codes counted in Python.


## :jigsaw: 2 - Experiments
In the second part, the strategy is played against secret codes for $p=4$ and $k=4..10$, with and without repetition. If there are at most 2000 codes, all codes are played; otherwise a random sample of 300 codes (seed=42) is used. Per game, the number of guesses, the grounding and solving time, and (with repetition) the size of the ground program are recorded.

### Main activities
- Scaling of the number of guesses and computation time with $k$ (without repetition)
- Effect of allowing repeated colors
- Comparison of encodings A and B (ground program size and run time)
- Comparison of the average number of guesses with published values

### Results
The strategy solved every game within 12 guesses in all configurations, and no game exceeded the 60s time limit.

### Average number of guesses (p=4)
| k | No repetition | Repetition, encoding A | Repetition, encoding B |
| :-----: | :-----: | :-----: | :-----: |
| 4 | 3.58 | 3.73 | 3.71 |
| 5 | 3.95 | 4.23 | 4.20 |
| 6 | 4.16 | 4.72 | 4.71 |
| 7 | 4.53 | 5.14 | 5.20 |
| 8 | 4.91 | 5.65 | 5.67 |
| 9 | 5.20 | 6.19 | 6.13 |
| 10 | 5.62 | 6.69 | 6.57 |

Averages are exact where all codes were played (no repetition: $k \le 8$; repetition: $k \le 6$) and sample means otherwise.

Key findings include:
- Without repetition, the average number of guesses grows by about 0.34 per additional color, while one round of grounding and solving stays roughly 1ms
- With repetition, the growth is about 0.5 guesses per color, and a round costs more (about 1.25-1.30ms for encoding B and 1.41-1.64ms for encoding A)
- Encoding B yields a 34-49% smaller ground program and 12-22% lower run time than encoding A, with an advantage that grows with $k$
- The first-model strategy is roughly 8-11% above the best published averages (eg. 4.72 versus the optimal 4.340 for 4 positions and 6 colors with repetition; 5.62 versus the optimal 5.213 for 4 positions and 10 colors without repetition)

These results show that, for these sizes, ASP is not a computational bottleneck for a consistent-guess strategy, and that the choice of encoding matters mainly for the size of the ground program. The strategy depends on clingo's search order (the first model is not uniformly random), and all timings come from a single machine.


## :blue_book: Report
The final report provides a detailed description of the research question, the ASP models, the experimental methodology, the obtained results, and the conclusions. References used throughout the project are also documented there.
