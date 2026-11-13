# Licensing and third-party sources

**Language:** [Русский](../licensing.md) | English

## Project licence

Blind-Ham-Propagation is distributed under the GNU General Public License version 3 or, at the recipient's option, any later version — GPL-3.0-or-later. The full text is in the root `LICENSE` file.

## External software components

| Component | Licence / status | Inclusion requirements |
|---|---|---|
| gauthig/propagation | GPL-3.0 (according to its repository) | Compatible with the project licence; preserve authorship, notices, and source code for modifications |
| hfcast-engine / hfcast | Apache-2.0 (according to its repository) | Preserve LICENSE/NOTICE and change notices; review transitive dependencies |
| FastAPI, Uvicorn, HTTPX, paho-mqtt | Separate project licences | Record exact versions and licences of all direct and transitive dependencies before release |
| Solar Monitor (R1BQE/solarMonitor) | A GPLv2 text is present in the repository | Do not copy files automatically before verifying their origin and rights to all included fragments. Account ownership alone does not prove that all code is original |

## Data sources and services

The program licence does not automatically apply to data obtained from external services. Before public launch, record access, reuse, caching, attribution, and rate-limit requirements for each source.

| Source | Purpose | What to verify |
|---|---|---|
| HamQSL XML | Solar and geomagnetic indicators, band-condition estimates, fixed-point MUF | XML terms, attribution, request frequency, and caching rules |
| NOAA SWPC | Space weather, D-RAP, GloTEC, and other products | Terms for each product, source attribution, redistribution restrictions |
| GIRO / KC2G | Ionosonde data, foF2, and MUF maps | API/dataset terms, attribution, permission to cache and publish derived data |
| PSK Reporter | Radio-station reception observations | MQTT/API terms, allowed collection rate and volume, storage, and republication |

## Project rules

1. Do not include code or data with unclear distribution terms.
2. Record the project URL, exact version, licence, and local modifications for each third-party software component.
3. Show the source and observation time for every data source; store server retrieval time separately.
4. Do not conflate software licences with data-use terms.
5. Do not present model estimates as measurements or hide formulas, coefficients, or model versions.
6. Prepare a list of direct and transitive dependency licences before release.
