## Project context

TERRALERT is a geospatial decision-support platform for Morocco’s
Haut-Commissariat au Plan (HCP). The pilot covers 11 communes around
Tangier, with a planned expansion to Tanger–Tétouan–Al Hoceïma.

The platform will monitor four hazards: floods, wildfires, heatwaves,
and cold waves. It will combine weather forecasts, historical climate
data, satellite observations, and geographic layers. Scientific rules
and indices will classify risk by commune. The HCP will eventually
view the results through maps, dashboards, and alerts.

The planned pipeline is:
Data ingestion → validation → preparation → spatial storage →
risk analysis → maps and alerts.

## Current checkpoint

The rebuild has completed local database infrastructure, weather fixture and
single-point live ingestion, pilot communes, CHIRPS and flood imports, drainage,
provisional population staging, and source audits through NOAA/NCEI. The
Meteostat comparison is paused because its CSV was unavailable. See
[the progress record](docs/TERRALERT_INGESTION_PROGRESS.md) for verification,
provenance limitations and pending work. The v1 repository
`oumaima-hahati/TERRALERT` was a reference; this v2 repository is
`vany-gr34/terralert-v2`.
