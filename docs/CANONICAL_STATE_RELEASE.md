# The open-source release: `canonical-state`

The twin compiler, derived as its own distribution. What it is, what it
is deliberately not called, and the two defects its deriver found.

```bash
python3 release/canonical_state/build.py --check      # verify
python3 release/canonical_state/build.py --out DIR    # emit
```

## What ships

| package | role |
|---|---|
| `core.canonical` | the state, its schema, typed deltas, validation, content-addressed versions |
| `core.projection` | the frozen read-only view handed downstream |
| `morpho` | a small declarative language -- lexer, parser, AST, IR -- with per-node identity and provenance |
| `backends` | deterministic compilers from IR to a Three.js scene, an SVG diagram, a graph report |
| `runtime` | the candidate -> validate -> commit-or-reject gate |
| `adapters` | JSON and CSV ingestion at the boundary |
| `renderer` | a browser view, three.js vendored with its notices |

**35 modules, 2,702 lines, 13 test files, zero Python dependencies.**

## Why it is a separate distribution

This repository holds two programs. Measured over every file in both,
the twin compiler and the evidence platform import each other **zero**
times, and outside the twin compiler nothing imports it: not the
evidence platform, not DAQ, not SCL. Two programs under one name would
be one distribution claiming to be two things, so they derive
separately. Same deriver discipline as `provenance-pool` -- a
projection, never a committed copy, because **a mirror is not a source**.

## What it is deliberately not called

Not a scientific or numerical library, and the packaging does not say it
is. That is a measurement, not modesty:

- the shipped packages import **no numeric module at all** -- no `math`,
  no `statistics`, nothing;
- the arithmetic in 2,702 lines is set difference, list concatenation,
  SVG layout margins and token indices;
- `backends/simulation` and `backends/neural` state in their own
  docstrings that they are **INTERFACE SHAPES ONLY** -- a `Protocol` and
  two dataclasses each, no dynamics and no model.

They ship as declared seams so an implementation has a fixed contract to
build against, one that routes its output through validation like any
other candidate. Both claims are locked:
`test_nothing_shipped_imports_a_numeric_module` and
`test_the_two_seams_ship_and_implement_nothing`.

What it is instead: domain-neutral infrastructure for state. One
canonical versioned truth, every view a projection with no write path.

## The two defects the deriver found

**A packaging list that installed nothing.** The first `pyproject.toml`
declared the five top-level package names. `pip install .` then produced
a distribution in which `core/` and `backends/` contained nothing but
`__init__.py` -- `core.canonical`, `core.projection` and all four
backend subpackages simply absent, and every documented import broken.

The derived suite passed throughout, and was telling the truth about the
wrong artefact: it runs with `cwd` inside the emitted tree, so `.` is on
`sys.path` and it imports the **source**, which is the one thing a user
never has. **A check that cannot fail where the defect lives**, again.
Found only by installing the result and importing it from elsewhere.

`_check_packaging_covers_the_tree` now compares the declared list
against the emitted tree in both directions -- a tree package missing
from the declaration is the defect above; a declared package missing
from the tree is a name resolving to nothing.

**A page that could name a file it did not ship.** `renderer/index.html`
resolves `three` through an importmap pointing at
`./vendor/three.module.js`, vendored deliberately so the page has no
runtime dependency on a CDN. Stripping `vendor/` to save 1.3 MB would
emit a page that fails on open -- the import check's defect in another
language, invisible to any amount of parsing Python.
`_check_assets_resolve` reads the other language for the same reason.

## A silent loss in the selection rule

The rule inherited from `provenance-pool` keeps a test when its internal
imports are all shipped packages. A test importing a helper from its own
directory -- `from tests.fixtures_time_series import ...` -- has an
internal head of `tests`, which is not a package name, so the rule
dropped it. The release simply contained one fewer test and still
reported success.

`support_files` now ships the repository's root `conftest.py` and the
clean non-test modules in `tests/`, and the selection rule allows a
`tests.` head only when every helper it names is one of them. Both
directions are driven, on constructed inputs, because no test in this
repository imports an unclean `tests.` helper today -- so the branch that
must refuse has no natural input, and an allowance granted
unconditionally passed every other lock.

Without the conftest the derived suite does not fail; it **errors at
setup thirty times**, which reads as broken code rather than a missing
file.

## Licence provenance

`LICENSE` is byte-identical to `provenance-pool`'s
(`sha256:cfc7749b...`), asserted rather than assumed. `NOTICE` names the
vendored three.js r160, its file, and its MIT licence -- a distribution
that redistributes somebody else's code without saying so is a licensing
defect, not a documentation one.

That lock had to be rewritten: the first version asserted the string
`"three.js"`, which the project URL in the same sentence also contains,
so a notice that had stopped saying *which* three.js still passed. It
now checks the version and the filename.

## Locks

`tests/test_release_canonical_state.py` -- 30 locks, every refusal driven
over **both** answers. `scripts/mutate_canonical_state_release_checks.py`
-- 22/22 mutants killed by their named test.
