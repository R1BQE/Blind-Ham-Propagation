# AI-assisted development guide

This document is the practical entry point for an AI assistant asked to work on this repository.

## 1. Understand the project

Read, in this order:

1. `AGENTS.md` — mandatory repository rules.
2. `README.md` — project purpose, status and quick start.
3. `docs/architecture.md` — component boundaries and data flow.
4. `docs/data-sources.md` — provider semantics and limitations.
5. `docs/api.md` — public HTTP contract.
6. `docs/testing.md` — test and validation commands.
7. `docs/development-and-deployment.md` — local and production operation.
8. `docs/licensing.md` — third-party code and data obligations.

Then inspect the actual files relevant to the requested task. Do not rely on this guide as a substitute for reading implementation and tests.

## 2. Repository map

- `backend/app/main.py`: FastAPI application creation and router setup.
- `backend/app/api/routes.py`: HTTP and WebSocket route handlers.
- `backend/app/services/`: provider clients, calculations, persistence and domain services.
- `backend/app/collectors/`: long-running data collection components.
- `frontend/index.html`: page structure and script loading.
- `frontend/js/app.js`: frontend application behavior, navigation and API interaction.
- `frontend/js/solar-monitor.js`: solar/geomagnetic monitor rendering and interpretation.
- `frontend/css/app.css`: responsive presentation and focus styling.
- `tests/`: pytest unit and API tests.
- `scripts/`: local/production setup helpers.
- `deploy/`: service and web-server configuration examples.
- `data/`, `logs/`: runtime data; do not commit their contents.

The exact tree can evolve. Confirm paths in the current branch before editing.

## 3. Architecture boundaries

Provider modules should fetch and normalize one provider's data. Domain services should combine or interpret normalized data only when the semantics support it. API routes should validate requests, call services and return structured responses; avoid putting provider parsing or complex calculations directly in route handlers. Frontend code should render API results and explain their meaning without silently changing the underlying scientific values.

Keep external network access behind provider/service modules so tests can mock it. Keep calculations deterministic and independently testable.

## 4. Data semantics

Every value shown to a user should be traceable to a source or a clearly described calculation. Preserve units and UTC timestamps. Treat observation time and retrieval time as separate fields.

Before comparing two providers, verify:
- the physical quantity and definition;
- unit and scale;
- observation time and update cadence;
- geographic reference and spatial resolution;
- provisional/final or quality flags;
- whether the value is measured, modelled or derived.

Do not choose a provider merely because its number looks more plausible. If the data are not comparable, show them separately and explain why. If one provider is stale or missing, identify that state instead of fabricating a replacement.

MUF is not interchangeable with F10.7, TEC, foF2 or D-RAP. D-RAP estimates D-region absorption; it is not an HF maximum usable frequency. A global index is not a path-specific forecast.

## 5. User interface and accessibility

Use plain Russian, short labels and progressive disclosure: show the few values that help answer the immediate question first, with detailed/raw values available separately. Use semantic headings, labels, buttons and tables. Ensure keyboard access, visible focus, useful accessible names and live announcements. Provide textual equivalents for visual output.

When simplifying a display, do not delete the underlying data or obscure source and timestamp details. A user must be able to expand details and discover why a summary was produced.

## 6. Typical task workflow

For a bug:
1. Reproduce or identify the failing path.
2. Inspect logs, route, service and related tests.
3. Add a focused regression test.
4. Fix the root cause.
5. Run the relevant tests and full test suite.

For a new provider:
1. Verify public endpoint, terms, attribution and rate limits.
2. Document product semantics and units.
3. Implement an isolated client with timeout and error handling.
4. Normalize values without losing provider metadata.
5. Add mocked tests for valid, missing, malformed, stale and failed responses.
6. Add API and UI integration with source/time/freshness disclosure.
7. Update data-source and API documentation.

For a UI change:
1. Inspect current HTML, JS and CSS.
2. Preserve keyboard behavior and responsive layout.
3. Use text nodes/textContent for external data, not unsafe HTML interpolation.
4. Check labels, focus order, status announcements and empty/error states.
5. Keep detailed data available without overwhelming the default view.

For a new calculation:
1. State inputs, assumptions, units and reference frame.
2. Implement a pure function where practical.
3. Add known-value and boundary tests.
4. Explain uncertainty and do not present an estimate as a measurement.

## 7. Commands

Install development dependencies:

```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Run tests:

```bash
python -m pytest tests -q
ruff check backend tests
```

On Windows, the supported local launcher is `run-windows.bat`. Read `docs/development-and-deployment.md` before changing launcher or deployment behavior.

## 8. Completion report

At the end of a task, report:
- what changed and why;
- files changed;
- tests actually executed and their results;
- any checks not possible (especially live external feeds);
- known limitations and follow-up work;
- commit SHA and branch, if changes were committed.

Never say “all tests pass” unless the full suite was actually run.