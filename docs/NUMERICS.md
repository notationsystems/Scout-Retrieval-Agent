# Numerics: what the published statistics are, and what they are not

Publishing means strangers compute with these numbers. This records what
each one is, where the floating-point boundaries are, and what was found
by running the code rather than reading it.

## The finding: a correlation that was not a correlation

`materials.replicate_join.correlation` computes Pearson's ρ by the
textbook two-pass form. The formula is correct. The **output was not
always in [-1, 1]**.

| n | draws with \|ρ\| > 1 | worst excess |
|---|---|---|
| 2 | 30,745 / 200,000 (**15.4%**) | 4.44e-16 |
| 3 | 0 / 200,000 | — |
| 5 | 0 / 200,000 | — |
| 10 | 0 / 200,000 | — |

n = 2 is structural: with two points ρ is exactly ±1 in exact
arithmetic, so *any* rounding lands outside the interval. And **n = 2 is
this module's own case** — the pairing it exists to recover is a
replicate pair, and its docstring records a real report where "the truth
is n = 2". The one sample size affected was the one it was written for.

### One ulp, but not a small consequence

The excess is a single unit in the last place. What breaks is not
proportional to its size:

```python
rho = 1.0000000000000002
math.acos(rho)       # ValueError: math domain error
math.sqrt(1 - rho**2)# ValueError: math domain error
math.atanh(rho)      # ValueError: math domain error
```

The angle between two series, a residual standard deviation, and the
Fisher z-transform behind every confidence interval on a correlation.
A caller doing ordinary statistics got a **crash, not an inaccuracy**.

Clamping is sound *because* the excess is bounded by rounding: it
returns the nearest representable value that is actually a correlation.
It is not masking a computational error — the two-pass form is already
the numerically stable one, and no summation order removes this, since
the true value *is* the endpoint.

### One operation stays undefined, correctly

`math.atanh(±1.0)` still raises. That is right: Fisher's z of a perfect
correlation genuinely diverges, and no clamp should invent a finite
value for it. What the fix changed is the **reason for the failure** —
before, `atanh` refused a number that was not a correlation at all; now
it refuses a correlation that truly has no finite z. The first is an
artefact the caller cannot act on; the second is a fact about their data.

## The regression the fix introduced

The clamp made a *worse* bug than the one it fixed, and it is worth
recording because it is not obvious:

```python
min(1.0, float("nan"))            # 1.0
max(-1.0, min(1.0, float("nan"))) # 1.0
```

Python's `min` keeps its first argument when the comparison is False,
and every comparison with NaN is False. So an infinity or NaN anywhere
in either series — which propagates to a NaN quotient — was silently
converted from `nan` into **1.0, a confident perfect correlation**.
Unclamped NaN at least announces itself. `1.0` does not.

**A bound that turns garbage into a confident answer is worse than the
out-of-range value it was added to fix.** So non-finite input is refused
before any arithmetic, and the clamp only ever sees finite values.

This was found by pursuing a mutant that looked equivalent and was not.

## The predictive variance names one estimator

`materials.model_state.predict` reports `uncertainty` as the
**population variance, divisor n**. The module previously called this
"population variance" in two docstrings and "sample variance" in three
others — different estimators, since "sample variance" conventionally
carries Bessel's correction. It now says one thing.

### What divisor n costs, measured

Estimating a true variance of 100.0, 200,000 trials per row:

| n | E[÷n] (as shipped) | E[÷(n−1)] | bias of ÷n |
|---|---|---|---|
| 2 | 50.1 | 100.2 | **−49.9%** |
| 3 | 66.5 | 99.7 | −33.5% |
| 5 | 80.0 | 100.0 | −20.0% |
| 10 | 90.0 | 100.0 | −10.0% |
| 30 | 96.7 | 100.0 | −3.3% |

÷n is biased low by exactly (n−1)/n, and **that factor varies with n**.
It is not a constant rescaling, so it does not cancel when ranking cells
with different sample counts: a cell with two samples looks more certain
than one with ten at the same true spread. Anything selecting
experiments on variance reduction should know this — it under-explores
where data is thinnest, which is backwards.

The estimator is **unchanged** here. Switching it would alter every
number the library reports, and that is a decision for the project
rather than a correction to make in passing. It is documented so the
choice is visible.

### Why one sample gives `None` rather than `0.0`

Under divisor n a single sample has a perfectly defined variance: zero.
Returning it would be the more dangerous answer — it asserts certainty
from one observation, which is how a wrong number gets believed. `None`
says *not determinable from this cell*, which is what is true.

So the `n >= 2` guard is **not** the n−1 convention leaking in. It is a
refusal that outranks the estimator's own domain.

## What was checked and found clean

Every division in the shipped packages is guarded at its zero:
`evidence/metrics.py` (5), `evidence/quarantine.py` (`attempted <= 0`),
`evidence/fep_interface.py` (`investigation_cost > 0`),
`materials/model_state.py`. `materials/surrogate.py` guards `None` and
non-finite input and reports a negative variance reduction honestly
rather than clamping it to zero. The only `sqrt` and the only
float-equality-against-zero in the shipped tree are the two in
`correlation`, both addressed above.

## Locks

`tests/test_numerics.py` — 11 locks, each driven at the sample size
where the property actually bites, with counts large enough to catch a
15% event. `scripts/mutate_numerics_checks.py` — 10/10 mutants killed.

One mutant is deliberately **not** in that list: relaxing `len(pairs) < 2`
to `< 1`. With one pair the mean equals the value, so variance is
exactly 0.0 for every finite float and the zero-variance refusal fires
first. The two forms are behaviourally identical on all finite input,
and the only input that separated them — an infinity — is now refused
earlier still. Keeping an equivalent mutant would either sit as a
permanent SURVIVED or invite a test written to kill it rather than to
check anything.

## A note on how these were found

Neither defect is visible in the formula. The Pearson expression is the
correct stable one; the variance expression computes exactly what it
computes. Both were found by **running the functions over many inputs
and looking at the range of the output** — and the estimator mutants
were only caught because a mutation battery noticed that the first
version of the test *recomputed the formula instead of calling the
function*, so it was checking its own arithmetic. That is this project's
mirror rule appearing inside its own verification.
