# Instructions for AI coding agents

These instructions apply to the entire repository.

## Before changing code

1. Read this file and `README.md`.
2. Read the relevant documents in `docs/`: start with `architecture.md`, then `ai-development-guide.md`, `data-sources.md`, `api.md` and `testing.md` as relevant.
3. Inspect the current implementation and tests before proposing or making changes. Documentation can lag behind code; verify both.
4. Check the current Git branch and recent changes. Do not overwrite unrelated work.

## Project purpose

Blind-Ham Propagation is an accessible amateur-radio space-weather, propagation-context and reception-observation service. It combines external measurements, model products, geometric calculations and real reception reports. These categories must remain distinguishable.

## Non-negotiable engineering rules

- Do not invent measurements, forecasts, MUF values, propagation probabilities or reception reports.
- Preserve provider name, product, observation timestamp, retrieval timestamp, units and quality/freshness information wherever available.
- Never average values from different providers merely because their labels look similar. Compare their definitions, units, observation times, spatial coverage and quality first.
- Do not label global indices or a distant station's measurement as a local QTH measurement.
- Distinguish measurements, model estimates, geometric calculations and PSK Reporter observations in API fields and user-facing text.
- Handle each external source independently. A failed provider should not hide valid results from other providers.
- Use bounded timeouts, bounded caches/storage and resilient error handling for external services.
- Keep secrets, credentials, local settings and personal data out of Git.
- Add or update tests for changed behavior. Prefer deterministic tests with mocked network responses.
- Keep API response changes documented in `docs/api.md`.
- Keep source, product, licence, attribution and limitations documented in `docs/data-sources.md` and `docs/licensing.md`.
- Do not deploy to the production VDS unless the user explicitly requests deployment.

## Accessibility requirements

- Use semantic HTML and programmatically associated labels.
- All functionality must work with a keyboard; do not require a mouse.
- Preserve visible focus and logical focus order.
- Announce loading, success, empty and error states to assistive technology.
- Do not communicate status by colour alone.
- Prefer concise plain Russian in the interface. Explain specialist terms where they first appear.
- Never make a map, chart, colour or icon the only way to understand a result. Provide equivalent text or a table.
- Respect reduced-motion preferences.
- Test controls and results with screen-reader-friendly markup; avoid inserting untrusted source text as HTML.

## Workflow

1. Make the smallest coherent change.
2. Add/update tests and documentation.
3. Run `python -m pytest tests -q` and, when relevant, `ruff check backend tests`.
4. For frontend changes, run a JavaScript syntax check and manually inspect keyboard/accessibility behavior where possible.
5. Report exactly what was tested. Never claim tests or live-source checks were run if they were not.
6. Summarize changed files, important design decisions, known limitations and the commit.

## Scope and compatibility

- Preserve the existing FastAPI + vanilla JavaScript architecture unless a change is explicitly justified.
- Avoid introducing dependencies for functionality already supported by the standard library or current stack.
- Keep Windows local development and Debian VDS deployment working.
- Keep local-only lifecycle endpoints out of production.
- Do not silently change collector scope, retention, public endpoints or deployment behavior.

## Documentation maintenance

When changing architecture, endpoints, data providers, configuration, setup or deployment, update the corresponding documentation in the same change. Prefer explicit statements of what is implemented, what is experimental and what remains planned.