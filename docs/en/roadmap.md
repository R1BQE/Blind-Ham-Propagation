# Project roadmap

**Language:** [Русский](../roadmap.md) | English

This is a working plan, not a claim that planned features are already implemented. Update status as work is completed.

## Stage 1 — Stable and understandable solar monitor

Status: in progress. The overview/details split is implemented; local NVDA verification and source-quality work remain pending.

- [x] Integrate NOAA SWPC global indicators.
- [x] Integrate NOAA D-RAP data.
- [x] Integrate HamQSL XML feed.
- [x] Keep provider failures independent and report partial data.
- [ ] Verify the live HamQSL XML structure and timestamps against real responses.
- [ ] Reduce the default screen to a concise operational summary.
- [ ] Move secondary/raw indicators into an expandable details section.
- [ ] Define provider comparison rules per physical quantity.
- [ ] Show preferred value, source, and observation time only when comparison is scientifically justified.
- [ ] Clearly flag disagreement, stale data, and incomparable products.
- [ ] Verify MUF product semantics and geographic reference before any QTH-specific display.

Acceptance: a radio amateur can quickly understand current broad conditions without confusing global indicators, local model estimates, and path-specific predictions.

## Stage 2 — QTH and path report

Status: partial foundation exists; a path-specific propagation model remains planned.

- [x] Maidenhead locator validation and coordinate conversion.
- [x] Local solar geometry.
- [x] Nearest NOAA D-RAP grid cell.
- [ ] Add a destination locator/region workflow.
- [ ] Calculate great-circle distance and azimuth in both directions.
- [ ] Calculate solar illumination context along the path.
- [ ] Evaluate a suitable HF propagation model and its licence.
- [ ] Present band-by-band estimates with model name, input assumptions, timestamp, and uncertainty.
- [ ] Do not show invented success percentages.

Acceptance: a user can enter two endpoints and understand path geometry and what the model can/cannot say about each band.

## Stage 3 — Reception observations

Status: initial implementation exists; real-data validation and usability improvements remain.

- [x] PSK Reporter MQTT pilot collector.
- [x] Bounded SQLite storage.
- [x] Independent regional TX and RX statistics.
- [x] Distance/bearing details for reported stations.
- [ ] Validate collector behavior against live MQTT traffic.
- [ ] Improve concise summaries by band, mode, direction, and time.
- [ ] Make the observation window and geographic uncertainty clear.
- [ ] Add bands/modes only after measuring feed volume and resource use.
- [ ] Consider WSPR observations only after access/terms review.

Acceptance: users can distinguish regional stations heard remotely from remote stations heard by regional receivers.

## Stage 4 — PWA and operational readiness

Status: foundation exists; final validation remains.

- [ ] Verify manifest, icons, and installation on Android and desktop browsers.
- [ ] Verify offline shell behavior and clear messaging when live data are unavailable.
- [ ] Verify update behavior after a new deployment.
- [ ] Check production reverse proxy and systemd configuration.
- [ ] Document backup/retention and operational diagnostics.

Acceptance: the application installs cleanly, updates predictably, and communicates offline/stale states accurately.

## Stage 5 — Documentation and contribution workflow

Status: in progress.

- [x] Repository instructions for AI coding agents.
- [x] AI-assisted development guide.
- [x] API and testing documentation.
- [x] Data-source semantics and roadmap.
- [x] Russian and English README/documentation versions.
- [ ] Keep all documents synchronized with implementation.
- [x] GitHub Actions workflow runs pytest on pushes and pull requests to main.
- [ ] Add Ruff linting to CI.
- [ ] Review licensing/attribution for every integrated code and data source.

Acceptance: a new developer or AI assistant can understand the architecture, run tests, safely modify a feature, and report validation without relying on undocumented chat history.
