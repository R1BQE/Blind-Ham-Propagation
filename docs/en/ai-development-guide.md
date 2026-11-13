# AI-assisted development guide

**Language:** [Русский](../ai-development-guide.md) | English

This document is the practical entry point for an AI assistant working on this repository.

## 1. Understand the project

Read, in this order:

1. `AGENTS.en.md` — repository rules in English; `AGENTS.md` is the Russian default.
2. `README.en.md` — project purpose, status, and quick start.
3. `docs/en/architecture.md` — component boundaries and data flow.
4. `docs/en/data-sources.md` — provider semantics and limitations.
5. `docs/en/api.md` — public HTTP contract.
6. `docs/en/testing.md` — tests and validation commands.
7. `docs/en/development-and-deployment.md` — local and production operation.
8. `docs/en/licensing.md` — third-party code and data obligations.

Then inspect the actual files relevant to the task. Do not rely on this guide instead of reading implementation and tests.

## 2. Repository map

- `backend/app/main.py`: FastAPI application creation and router setup.
- `backend/app/api/routes.py`: HTTP and WebSocket route handlers.
- `backend/app/services/`: provider clients, calculations, persistence, and domain services.
- `backend/app/collectors/`: long-running data collection components.
- `frontend/index.html`: page structure and script loading.
- `frontend/js/app.js`: frontend behavior, navigation, and API interaction.
- `frontend/js/solar-monitor.js`: solar/geomagnetic monitor rendering and interpretation.
- `frontend/css/app.css`: responsive presentation and focus styling.
- `tests/`: pytest unit and API tests.
- `scripts/`: local and production setup helpers.
- `deploy/`: service and web-server configuration examples.
- `data/`, `logs/`: runtime data; do not commit their contents.

The tree can evolve. Confirm paths in the current branch before editing.

## 3. Architecture boundaries

Provider modules should fetch and normalize one provider's data. Domain services should combine or interpret normalized data only when the semantics support it. API routes should validate requests, call services, and return structured responses; avoid putting provider parsing or complex calculations directly in route handlers.

Keep external network access behind provider/service modules so tests can mock it. Keep calculations deterministic and independently testable.

## 4. Data semantics

Every value shown to a user should be traceable to a source or a clearly described calculation. Preserve units and UTC timestamps. Treat observation time and retrieval time as separate fields.

Before comparing providers, verify the physical quantity and definition, unit and scale, observation time and update cadence, geographic reference and spatial resolution, quality flags, and whether the value is measured, modelled, or derived.

Do not choose a provider merely because its number looks more plausible. If data are not comparable, show them separately and explain why. If a provider is stale or missing, identify that state instead of fabricating a replacement.

MUF is not interchangeable with F10.7, TEC, foF2, or D-RAP. D-RAP estimates D-region absorption; it is not an HF maximum usable frequency. A global index is not a path-specific forecast.

## 5. User interface and accessibility

Use plain Russian, short labels, and progressive disclosure: show the few values that answer the immediate question first, with detailed/raw values available separately. Use semantic headings, labels, buttons, and tables. Ensure keyboard access, visible focus, useful accessible names, and live announcements. Provide textual equivalents for visual output.

When simplifying a display, do not delete underlying data or obscure source and timestamp details. A user must be able to expand details and understand how a summary was produced.

## 6. Typical task workflow

For a bug: reproduce or identify the failing path; inspect logs, route, service, and tests; add a focused regression test; fix the root cause; run relevant tests and the full suite.

For a new provider: verify endpoint, terms, attribution, and rate limits; document product semantics and units; implement an isolated client with timeout/error handling; normalize without losing metadata; add mocked tests for valid, missing, malformed, stale, and failed responses; integrate API/UI with source/time/freshness disclosure; update data-source and API documentation.

For a UI change: inspect HTML, JS, and CSS; preserve keyboard behavior and responsive layout; use text nodes/`textContent` for external data; check labels, focus order, announcements, and empty/error states; keep detailed data available.

For a new calculation: state inputs, assumptions, units, and reference frame; implement a pure function where practical; add known-value and boundary tests; explain uncertainty and never present an estimate as a measurement.

## 7. Commands

Install development dependencies:

```bash
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -e ".[dev]"
```

Run tests and lint:

```bash
python -m pytest tests -q
ruff check backend tests
```

On Windows, the supported local launcher is `run-windows.bat`. Read `docs/en/development-and-deployment.md` before changing launcher or deployment behavior.

## 8. Completion report

At the end of a task, report what changed and why, files changed, tests actually executed and results, checks that could not be performed (especially live external feeds), known limitations/follow-up work, and commit SHA/branch if committed.

Never say “all tests pass” unless the full suite was actually run.
