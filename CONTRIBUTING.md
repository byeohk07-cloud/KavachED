# Contributing to KavachED

Thanks for helping make student support clearer and more useful.

## Setup

Use Python 3.10 or newer, create a virtual environment, install `requirements.txt`, then run `streamlit run app.py`. Run `pytest` before submitting changes.

## Branch and commit conventions

- Branches: `feature/short-description`, `fix/short-description`, or `docs/short-description`.
- Commits: short imperative summaries, for example `Add workspace-scoped student search`.

## Code style

- Keep persistence in `core/db.py` and use parameterized SQL.
- Include workspace and student access scope in data reads and writes.
- Keep risk calculations deterministic and covered by unit tests.
- Prefer short functions, useful type hints, and clear user-facing errors.

## Pull request checklist

- [ ] Explain the user problem and the change.
- [ ] Add or update tests.
- [ ] Run `pytest`.
- [ ] Check teacher/student access boundaries.
- [ ] Check light/dark appearance and narrow layouts.
- [ ] Update user and technical documentation where appropriate.
- [ ] Do not include secrets or real student information.
