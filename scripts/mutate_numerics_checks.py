#!/usr/bin/env python3
"""Probe the numerical locks.

A statistic that is merely ASSERTED to be bounded is not bounded. Each
mutation below restores a form the code actually had, or a plausible
wrong one; the named test must notice.
"""

import os
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
JOIN = REPO / "materials" / "replicate_join.py"
STATE = REPO / "materials" / "model_state.py"
SUITE = "tests/test_numerics.py"

MUTATIONS = [
    # -- the correlation's bound -------------------------------------------
    ("the clamp removed, restoring the shipped defect exactly", JOIN,
     lambda s: s.replace("    return max(-1.0, min(1.0, rho))",
                         "    return rho  # MUTANT"),
     "test_rho_stays_inside_its_interval_at_the_size_that_broke_it"),
    ("the clamp flattens everything to the endpoint", JOIN,
     lambda s: s.replace("    return max(-1.0, min(1.0, rho))",
                         "    return 1.0  # MUTANT"),
     "test_the_clamp_did_not_flatten_real_correlations"),
    ("the clamp folds the sign away", JOIN,
     lambda s: s.replace("    return max(-1.0, min(1.0, rho))",
                         "    return min(1.0, abs(rho))  # MUTANT"),
     "test_the_clamp_did_not_flatten_real_correlations"),
    ("only the upper bound is applied", JOIN,
     lambda s: s.replace("    return max(-1.0, min(1.0, rho))",
                         "    return min(1.0, rho)  # MUTANT"),
     "test_rho_respects_the_lower_bound_as_well_as_the_upper"),
    ("the finite guard removed, so NaN clamps to a perfect correlation", JOIN,
     lambda s: s.replace(
         "    if any(not math.isfinite(value) for pair in pairs for value in pair):\n"
         "        return None",
         "    if False:  # MUTANT\n        return None"),
     "test_a_clamp_must_not_turn_garbage_into_a_perfect_correlation"),
    ("a zero-variance series gets an invented correlation", JOIN,
     lambda s: s.replace("    if variance_x == 0.0 or variance_y == 0.0:\n        return None",
                         "    if variance_x == 0.0 or variance_y == 0.0:\n        return 0.0  # MUTANT"),
     "test_rho_is_undefined_rather_than_invented_where_it_has_no_value"),
    ("the single-pass form, which cancels catastrophically", JOIN,
     lambda s: s.replace(
         "    numerator = sum((x - mean_x) * (y - mean_y) for x, y in pairs)\n"
         "    variance_x = sum((x - mean_x) ** 2 for x in xs)\n"
         "    variance_y = sum((y - mean_y) ** 2 for y in ys)",
         "    n = len(pairs)  # MUTANT\n"
         "    numerator = sum(x * y for x, y in pairs) - n * mean_x * mean_y\n"
         "    variance_x = sum(x * x for x in xs) - n * mean_x * mean_x\n"
         "    variance_y = sum(y * y for y in ys) - n * mean_y * mean_y"),
     "test_rho_is_unchanged_by_a_shift_that_would_wreck_a_naive_formula"),
    # NOT LISTED: relaxing `len(pairs) < 2` to `< 1`. With one pair the
    # mean equals the value, so variance is exactly 0.0 for every finite
    # float and the zero-variance refusal fires first -- the two forms
    # are behaviourally identical on all finite input, and the only
    # input that separated them (an infinity) is now refused earlier
    # still. An equivalent mutant kept in the list would either sit as a
    # permanent SURVIVED or invite a test written to kill it rather than
    # to check anything, so it is recorded here instead.

    # -- the variance names its estimator ----------------------------------
    ("the divisor silently becomes Bessel-corrected", STATE,
     lambda s: s.replace(
         "        variance = (sum((v - mean) ** 2 for v in values) / n) if n >= 2 else None",
         "        variance = (sum((v - mean) ** 2 for v in values) / (n - 1)) if n >= 2 else None  # MUTANT"),
     "test_the_predictive_variance_is_the_divisor_n_form_it_names"),
    ("one sample reports zero uncertainty instead of none", STATE,
     lambda s: s.replace(
         "        variance = (sum((v - mean) ** 2 for v in values) / n) if n >= 2 else None",
         "        variance = sum((v - mean) ** 2 for v in values) / n  # MUTANT"),
     "test_one_sample_yields_no_uncertainty_rather_than_zero"),
    ("the estimator is named `sample variance` again", STATE,
     lambda s: s.replace("population variance, divisor n", "sample variance"),
     "test_the_module_names_one_estimator_and_not_two"),
]


def _compiles(path, source):
    if path.suffix != ".py":
        return ""
    try:
        compile(source, str(path), "exec")
    except SyntaxError as error:
        return f"does not parse: {error}"
    return ""


def _purge_cache():
    for cached in REPO.rglob("__pycache__"):
        for item in cached.glob("*.pyc"):
            item.unlink(missing_ok=True)


def main() -> int:
    print("=== MUTATION VERIFICATION: the numerical locks ===")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    killed = malformed = 0
    for description, target, mutate, test_name in MUTATIONS:
        original = target.read_text()
        mutated = mutate(original)
        if mutated == original:
            print(f"  MALFORMED  {description:<58} (diff reached nothing)")
            malformed += 1
            continue
        problem = _compiles(target, mutated)
        if problem:
            print(f"  MALFORMED  {description:<58} ({problem})")
            malformed += 1
            continue
        try:
            _purge_cache()
            target.write_text(mutated)
            result = subprocess.run(
                [sys.executable, "-m", "pytest", f"{SUITE}::{test_name}",
                 "-q", "-p", "no:cacheprovider"],
                cwd=REPO, capture_output=True, text=True, env=env)
        finally:
            target.write_text(original)
            _purge_cache()
        if result.returncode != 0:
            print(f"  KILLED     {description:<58} -> {test_name}")
            killed += 1
        else:
            print(f"  SURVIVED   {description:<58} -> {test_name}")
    total = len(MUTATIONS)
    print(f"\n{killed}/{total} mutants killed by their named test"
          + (f" ({malformed} malformed)" if malformed else ""))
    return 0 if killed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
