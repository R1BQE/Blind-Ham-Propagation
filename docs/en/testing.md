# Testing and validation

**Language:** [Русский](../testing.md) | English

## Test environment

Python 3.11 or newer is required. Install the project and development dependencies:

```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Debian/Linux:
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Automated tests

Run the full suite from the repository root:

```bash
python -m pytest tests -q
```

Run one test module:

```bash
python -m pytest tests/test_hamqsl.py -q
```

Run a single test by name:

```bash
python -m pytest tests/test_hamqsl.py -k xml -q
```

Run static lint checks:

```bash
ruff check backend tests
```

Do not change or weaken assertions merely to make a failing test pass. Identify whether the failure is caused by a regression, changed provider format, environment problem, or obsolete test expectation.

## Test design

- Unit-test locator conversion, distance/bearing calculations, parsing, and normalization with deterministic input.
- Mock HTTP and MQTT boundaries. The regular test suite must not depend on live third-party services.
- Cover valid, empty, malformed, missing-field, timeout, and provider-error responses.
- Test cache expiry and cache hits with controlled time where possible.
- Test API validation, response structure, and partial-provider failure behavior.
- Test that TX and RX regional observations remain independent.
- Test storage bounds, duplicate handling, and stale-observation filtering.
- Avoid tests that depend on current time without freezing or injecting a clock.

## Frontend checks

For changed JavaScript files, run a syntax check with Node.js when available:

```bash
node --check frontend/js/app.js
node --check frontend/js/solar-monitor.js
```

Then launch locally with `run-windows.bat` on Windows. Check page startup/navigation, loading/success/empty/error states, manual and automatic refresh where applicable, keyboard-only operation and visible focus, screen-reader names and labels, table headers and status announcements, responsive layout, and browser-console errors.

A JavaScript syntax check is not an accessibility audit. Do not claim NVDA/VoiceOver testing unless it was actually performed.

## Live data checks

Live feeds are useful for manual integration checks but should not be required for unit tests. Record the date/time and provider tested. A successful HTTP response alone does not prove that a field is semantically correct or current; inspect source timestamps, units, location, and product documentation.

## Before committing

Run the full Python suite after changes that affect backend behavior. Run frontend syntax checks after JavaScript changes. Review the final diff and ensure documentation matches the implementation. Record any checks that could not be performed.
