# Historical electoral predecessors

This note records predecessor repositories that informed the current electoral-data estate without making those repositories current dependencies or authorities.

The current operational boundary remains:

- `elecciones-ARG` owns electoral event/result semantics, source-native electoral identities, candidates, vote facts, mesas, aggregates, QA and run manifests.
- `argentina-geography` owns governed geographic releases and factual Census↔electoral spatial relations.
- historical product projections such as Peronómetro are downstream consumers, not source authorities.

## Why this note exists

Several older repositories contain useful evidence but predate the current authority boundaries. Their useful ideas should be preserved as lineage, while duplicated data preparation, GIS logic, scraping and product-specific exports are retired.

A bounded 2026-08-30 audit found no repository-visible code references to `EleccionesARG`, `EleccionesARG21` or `toolkit_Elecciones_ARG`. No literal `Peronometro` / `Peronómetro` marker was found in the audited electoral repositories. That does not prove that old local deployments never consumed their outputs; it only means no current repository-visible dependency was found.

## `EleccionesARG`

Historical role: 2015/2017 electoral workbench.

Observed surfaces:

- cleaned electoral-circuit geometry;
- loaded and unified election results;
- built department/circuit summary tables;
- produced Mapbox-ready geographic exports;
- explored ballot splitting (`corte de boleta`).

Disposition:

| Historical capacity | Current disposition |
| --- | --- |
| Circuit geometry cleaning | **SUPERSEDED** by governed electoral geography and relation releases in `argentina-geography`. |
| Electoral extraction/unification | **SUPERSEDED** by `elecciones-ARG` stages 10–40. |
| Department/circuit aggregates | **SUPERSEDED** by the long vote facts plus stage 60 aggregates in `elecciones-ARG`. |
| Manual cross-election political-force grouping | **LATENT CONSUMER RECIPE**. The old notebook manually aligned labels such as CAMBIEMOS, Frente para la Victoria, Unidad Ciudadana, UNA/1País and FIT across 2015/2017. Do not promote that product-specific political grouping into the canonical pipeline without a named consumer and explicit historical mapping. |
| Mapbox upload/export glue | **RETIRED** as core electoral-data responsibility. A revived visualization should consume governed outputs through its own delivery adapter. |
| Ballot-splitting analysis | **LATENT ANALYSIS RECIPE**. Preserve the historical notebook as evidence; reimplement only if an active analytical consumer requires it. |

### Peronómetro relevance

Peronómetro existed as a public-facing electoral-map product, but the repository audit did not find a literal link proving that `EleccionesARG` was its data source.

The strongest plausible predecessor surface is the 2015/2017 summary notebook: it materialized department/circuit percentages for selected political forces and was paired with Mapbox export work. Treat that as historical product-projection evidence, not as an authoritative current dataset.

If Peronómetro is revived, rebuild the projection from current `elecciones-ARG` facts/dimensions and explicit consumer-owned political-force mappings rather than copying the old summary CSVs or notebooks.

## `EleccionesARG21`

Historical role: frozen 2021 official-data acquisition snapshot.

The repository records ZIP files downloaded from `argentina.gob.ar` around 2021-09-14, an extractor, and reference-table generation.

Disposition:

- **PRESERVE AS HISTORICAL SOURCE EVIDENCE**: the committed official snapshot can help reconstruct what was available at that date.
- **RETIRE AS AN ACTIVE INGEST PATH**: current ingestion belongs in `elecciones-ARG` with exact source identity, hashes, manifests and QA.
- Do not copy the old ZIP mirror into the current repository merely to preserve history.

The current election registry already includes 2021 alongside 2011–2025 election identities; the old repository is therefore not needed merely to represent the 2021 period.

## `eleccionesARG21_scrapper`

Historical role: Selenium/web scraper over `resultados.gob.ar` for 2021 results.

Observed outputs include:

- `results/resultados.json`;
- `results/censo.json`;
- `results/regiones.json`.

Disposition:

- **PRESERVE AS HISTORICAL ACQUISITION SNAPSHOT** because web result surfaces are ephemeral and the committed JSON can document what the site exposed at that time.
- **RETIRE THE SCRAPER** as an active acquisition mechanism. Prefer exact official source files handled by the current ingest pipeline.
- Do not promote the scraped JSON schema into a current contract merely because an old product may have consumed it.

## `toolkit_Elecciones_ARG`

Historical role: convenience bundle of cleaned districts, historical vote tables, list names and electoral/geographic lookup material.

Observed examples include `VOTOS_ARG_DPTO.csv`, `VOTOS_ARG_DPTO_circ.csv` and `radio_ref_circuitos.csv`.

Disposition:

- electoral vote/result material: **SUPERSEDED** by `elecciones-ARG` canonical facts/dimensions and governed aggregates;
- radio↔circuit lookup material: **SUPERSEDED** by `argentina-geography` relation releases;
- political/list naming tables: preserve historically, but new mappings belong with exact election/list source semantics in `elecciones-ARG` or in an explicit downstream consumer.

The toolkit should not remain an ambient dependency or a second electoral-data authority.

## `CensoARG_20102`

Historical role: private Census/EPH/geography research workbench.

Most of the repository is exploratory notebook material and derived Census/geography output. The one method worth preserving as an explicit breadcrumb is the old synthetic electoral-circuit population experiment:

1. take a radio↔circuit intersection table;
2. include Census dwellings from fully contained radios;
3. sample dwellings from partially intersecting radios in proportion to overlap share;
4. join Census household and person records;
5. recode selected Census variables toward EPH-like categories;
6. restrict to people older than 15 for an elector-like comparison;
7. materialize a synthetic circuit population and compare it with 2015/2017 elector counts.

This method is **historical evidence, not a validated current estimator**. It mixes geography assignment, Census sampling, semantic harmonization and electoral validation that now have separate authorities.

If a current consumer needs a circuit-level synthetic population, reconstruct the composition from exact governed parents:

```text
samplerCensoARG          Census donor sampling / stable household-person identity
        +
eph-censo-aligner        explicit Census↔EPH semantic recoding where actually required
        +
argentina-geography      exact radio↔circuit relation facts / geography identity
        +
elecciones-ARG           elector counts and electoral event/result semantics
        ↓
consumer-owned synthetic-circuit method + validation
```

Do not copy `circuito_poblacion_sint.csv`, the old sampling notebook, or its implicit assumptions into any current authority merely to keep the historical workflow alive.

## Decommissioning rule

These predecessor repositories should remain historical evidence only. They are candidates for GitHub archival once machine-local dependencies are checked.

Before archive, classify any local cron/systemd job, shell wrapper, deployment, website build, data-lake path or external script that still names one of the predecessors. A historical dataset or notebook is not by itself a reason to keep the repository writable.

The goal is one current electoral-data authority plus explicit governed geographic parents, while preserving enough lineage to reconstruct old products without reviving old architectures.
