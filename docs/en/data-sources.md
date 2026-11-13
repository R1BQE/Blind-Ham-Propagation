# Data sources and interpretation

**Language:** [Русский](../data-sources.md) | English

This document describes how the service should interpret external feeds. Provider availability and product formats can change; verify current provider documentation before modifying an integration.

## NOAA SWPC

Official public products: https://services.swpc.noaa.gov/json/ and https://services.swpc.noaa.gov/products/

The current backend retrieves global space-weather indicators including F10.7 solar radio flux, planetary Kp index, solar-wind proton speed, interplanetary magnetic field Bt and Bz (GSM), and GOES X-ray flux.

These values describe broad solar/geomagnetic conditions. They are not direct measurements of propagation on a specific path. Preserve each product's own timestamp, unit, and meaning.

## NOAA D-RAP

Product: https://www.swpc.noaa.gov/products/d-region-absorption-predictions-d-rap

D-RAP estimates high-frequency radio-wave absorption in the D region. The local QTH report selects the nearest available published grid cell; it does not interpolate a value at the exact station coordinates. The grid value is a model estimate, not a direct local measurement.

D-RAP is not MUF and must not be described as an MUF forecast or a guarantee that a band is open.

## HamQSL solar XML

Endpoint: https://www.hamqsl.com/solarxml.php

The service fetches the XML feed through the backend. The current client uses a shared in-memory cache with a 60-minute lifetime and parses XML while preserving attributes and repeated elements. The feed includes a mixture of solar/geomagnetic indicators, calculated HF band conditions, VHF condition notices, and MUF-related fields.

Important interpretation rules:

- Keep the original field name and provider metadata available during normalization.
- Do not assume every field describes the user's QTH or a selected radio path.
- The HamQSL solar page identifies Lowell GIRO Data Center (LGDC) as the source of its MUF data. The XML `muf` field does not by itself identify a station, calculation point, or radio path. Do not present it as the MUF for the user's Maidenhead locator unless that geographic relationship is independently established. The frontend labels it as a HamQSL-provided MUF value and states this limitation.
- Calculated band-condition labels are provider assessments, not guaranteed contact success.
- Preserve the feed update time separately from backend retrieval time.
- If the provider is unavailable, show NOAA data that did arrive and identify the missing provider.

Check the XML endpoint and field semantics against the current provider response before changing the parser.

## PSK Reporter

Documentation: https://www.mqtt.pskreporter.info/

PSK Reporter supplies reception reports from participating stations. A spot is evidence that a particular receiver decoded a particular transmission at a particular time and frequency. It is not a propagation forecast and does not prove that another station will achieve the same result.

The project uses an MQTT topic-filter pilot and stores a bounded recent history in SQLite. The regional report keeps two directions separate:

- TX: transmissions from stations inside the selected region that were heard by remote receivers.
- RX: remote transmissions heard by receivers inside the region.

A station's Maidenhead locator represents an area, not an exact antenna coordinate. Distances and bearings calculated from locator-cell centres are estimates. Keep this limitation visible.

## Other candidate sources — not currently integrated

### GIRO / DIDBase

GIRO provides ionosonde observations. Access and use conditions may restrict some forms of use, and station coverage varies. Do not integrate until current terms, attribution requirements, and the intended service use have been reviewed. See https://giro.uml.edu/didbase/RulesOfTheRoad.html.

### KC2G / prop.kc2g.com

A potential source for ionospheric maps and station-derived products. Before integration, establish the exact product definition, spatial/time resolution, update cadence, availability, licence/terms, and whether the data can support the intended geographic/path-specific interpretation. A map layer alone is not automatically a path MUF.

### WSPR.live

A potential source for historical WSPR reception observations. Verify current access conditions, query limits, data semantics, and redistribution rules before integration.

## Comparing providers

Never choose a value solely because it looks more plausible. For every proposed comparison, evaluate whether the physical quantity and definition match, units/scales match, observation times are close enough, geographic coverage and spatial resolution match, measured/modelled/derived status is equivalent, quality flags are compatible, and either feed is stale, provisional, or missing.

If all criteria support comparison, the application may select a preferred source using an explicit documented rule and show the source/time. If criteria do not support comparison, show the values separately and explain the difference. Do not average incompatible values. The current solar monitor deliberately does not automatically compare NOAA and HamQSL measurements: similar labels alone are insufficient to establish equivalent definitions, averaging periods, or geographic scope.

## General data-quality rules

- Store/display observation time and retrieval time separately, preferably UTC.
- Expose source and unit for every scientific value.
- Apply a documented freshness threshold per product, not one universal threshold.
- Report stale, missing, malformed, and unavailable data explicitly.
- Do not silently substitute a global index for a local measurement.
- Distinguish measurements, model outputs, geometric calculations, and reception observations.
- Do not infer a closed band from the absence of PSK Reporter spots.
- Never fabricate MUF, SNR, propagation probability, or contact success.
