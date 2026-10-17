#const p = 4.
#const k = 6.
position(1..p).
color(1..k).

% Generate: each position gets assigned exactly one color
1 { code(P, C) : color(C) } 1 :- position(P).

% Main variant: a color can only be used once in a code
{ code(P, C) : position(P) } 1 :- color(C).

#show code/2.


turn(T) :- feedback(T, _, _).

% Red: positions with the same color
red(T, N) :- turn(T), N = #count{ P : guess(T, P, C), code(P, C) }.

% Total amount of colors in common
common(T, N) :- turn(T), N = #count{ C : guess(T, _, C), code(_, C) }.

% Test
:- feedback(T, R, _), red(T, R2), R != R2.
:- feedback(T, R, W), common(T, N), N != R+W.
