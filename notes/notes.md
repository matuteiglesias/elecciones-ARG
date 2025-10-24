Good. Let’s map what you actually have here and pick the few files that are worth opening before we draft any notes.

# Components I see (by function)

1. **Raw inputs / reference layers**

* CNE official results by mesa/circuito/elección: `datos/BD*/`, `Solo_ResultadosProvisorios_*`, `votos_eleccion_*_table.csv`, `radios_circuitos*.csv`, `codprovs.csv`.
* Geographic references: `ign_departamento/*` shapefile set, `radios_IGN_2010_WGS84/*`, `mapaelectoral/*geojson`, `web/ejido*.geojson`, `circuitos_electorales_AR/geojson`.
* Labeling and disambiguation: `correccion/*.json`, `disambiguar.csv`, `agrupacion_nombre_weight*.csv`, `agrup_nombre_color.csv`, `agrup_nombre_magnitudes.csv`.

2. **Integration / harmonization (keys and spatial joins)**

* Notebooks doing the heavy joins:
  `CNE-INDEC-georef/01b`, `02b`, `03b`, `Tabla resumen y Mapa.ipynb`, `radios en circuitos.ipynb`.
* Derived join outputs: `info/*ref*.csv`, `info/*_CNE_IGN*.csv`, `circs_dpto_prov.geojson`, `secciones_*_TTGL.csv`.

3. **Transform pipelines (tabular to canonical outputs)**

* “Descomposición BD” and early transforms: `notebooks-01-descomposicion-BD/00 - Descomposicion BD.ipynb`, plus `misc_code/99 - (legacy) Limpieza Datos.ipynb`.
* Aggregations by unit: `notebooks-02-analisis-de-datos/*` and `electoral_v1/datos/out/*.csv`.

4. **Geospatial product builds (GeoJSON, recipes, styles)**

* GeoJSON builders: `notebooks-03-web-peronometro/*`, `misc_code/07 - Fuerzas.*GeoJSON.ipynb`.
* Mapbox style layer: `web/mapbox_styles/*`, `styles/*.json`, `style_info.json`, `mapbox-recipes/*.json`.
* Utility module: `matuteiglesias-EleccionesARG_legacy/modules/mapbox_tools.py`.

5. **Web artifacts / publishing**

* `web/*.html` (peronometro, tests, index.html), `elecciones-ARG/web/*` and duplicated `web/` under `electoral_v1`.

6. **Analysis add-ons**

* EPH cross and ecological inference: `notebooks-04 - Cruce EPH/*` including `05 - Ecological Inference.ipynb`, plus `satellite.py`.
* Municipal deep dives: `notebooks-02-analisis-de-datos/07 - Municipal.ipynb`, `09 - Municipal Tablas.ipynb` and `09 - Municipal Tablas.html`.

7. **Legacy / duplication**

* `matuteiglesias-EleccionesARG_legacy/*`, `misc_code/*`, and mirrored `elecciones-ARG` subtree inside `electoral_v1/elecciones-ARG/`.

This split is enough to write a coherent briefing/runbook later, but first we should open a handful of “truth-defining” files to anchor the schema, the joins, and the web stack.

# Shortlist to inspect next (minimal but high-leverage)

## A. Canonical schema and joins

1. `electoral_v1/datos/BD/eleccion_table.csv` and `.../cargo_table.csv`
   — confirm ID keys, naming, and whether these align with your joins.
2. `electoral_v1/datos/BD/mesa(s)_table.csv` and one `votos_eleccion_*_table.csv`
   — verify mesa-level primary key, foreign keys to circuito/sección, and vote value fields.
3. `CNE-INDEC-georef/info/radios_circuitos.csv` and `.../secciones_dptos_ref.csv`
   — check the join keys you actually used for radios → circuitos and secciones → dptos.
4. `CNE-INDEC-georef/mapaelectoral/ref-dptosIGN.geojson`
   — sanity-check geometry, properties, and IDs used down the line.
5. `electoral_v1/datos/info/secciones_departamentos-TTGL.csv`
   — your own resolved mapping used by downstream notebooks.

## B. Disambiguation and labeling

6. `electoral_v1/datos/correccion/*.json` and `elecciones-ARG/notebooks-02-analisis-de-datos/disambiguar.csv`
   — see how party names, cargo tags, and vote type labels are normalized.
7. `misc_code/agrupacion_nombre_weight*.csv` and `web/agrup_nombre_color.csv`
   — confirm buckets and color assignments that affect map legends.

## C. Pipeline definition points

8. `elecciones-ARG/README.md` and `CNE-INDEC-georef/README.md`
   — any stated conventions or steps we can reuse rather than re-inferring.
9. `elecciones-ARG/notebooks-01-descomposicion-BD/00 - Descomposicion BD.ipynb`
   — the earliest ETL logic; identify expected column names.
10. `CNE-INDEC-georef/02b - Interseccion espacial de Radios Censales a Circuitos CNE.ipynb`
    — pivotal spatial join. If only one join notebook is inspected, make it this one.

## D. GeoJSON build and web stack

11. `elecciones-ARG/notebooks-03-web-peronometro/03 - Votos y porcentajes. GeoJSON.ipynb`
    — how you compute pct/cnt and write properties.
12. `electoral_v1/web/style_info.json` and `web/mapbox_styles/style_info.json`
    — ensure these match current layer names and legends.
13. `matuteiglesias-EleccionesARG_legacy/modules/mapbox_tools.py`
    — any reusable helpers for style/publish steps.
14. `electoral_v1/web/peronometro.html` and `elecciones-ARG/web/index.html`
    — detect which one is the intended current entrypoint and what assets it expects.

## E. Analysis extras (optional after the above)

15. `notebooks-04 - Cruce EPH/05 - Ecological Inference.ipynb`
    — understand assumptions before we summarize this line.
16. `electoral_v1/datos/out/*.csv`
    — final product shapes: elector counts, votos_* by unit.

# Quick integrity risks to watch while inspecting

* **Schema drift** between BD tables and join outputs — field names for keys often diverge (“id_circ”, “circuito_id”, etc.).
* **Duplicated web assets** — two `style_info.json` and multiple `web/` folders. Decide the canonical one.
* **Color/label drift** — colors in `web/agrup_nombre_color.csv` vs legacy `styles/*.json`.
* **Spatial ID mismatches** — radios/sections mapping made at different times with slightly different IGN sources.
* **Recipe confusion** — multiple `*-recipe.json` files; check which are used by the live HTML.

# Proposed order of opening (fastest signal first)

1. `CNE-INDEC-georef/info/radios_circuitos.csv`
2. `electoral_v1/datos/BD/mesa(s)_table.csv` and one `votos_eleccion_*_table.csv`
3. `CNE-INDEC-georef/02b ... Radios → Circuitos.ipynb`
4. `elecciones-ARG/notebooks-03-web-peronometro/03 - Votos y porcentajes. GeoJSON.ipynb`
5. `electoral_v1/web/style_info.json` and `electoral_v1/web/peronometro.html`
6. `electoral_v1/datos/correccion/*.json` and `web/agrup_nombre_color.csv`

Open those six stops and we’ll have enough ground truth to write a precise **briefing** and a minimal, executable **runbook** for the electoral stack. If you paste any of these file heads or key cells, I’ll extract the fields and lock the schemas.





Here’s a compact, evidence-based dev diary reconstructed from the directory mtimes you pasted. It’s chronological, with what likely happened, why it mattered, and where drift/duplication crept in. I’m explicit when the evidence is weak — git object mtimes can mislead.

# Dev diary (reconstructed)

## 2021-10 — First public map experiments (legacy web + styles)

* **Evidence:** `/media/.../matuteiglesias-EleccionesARG_legacy/styles` (2021-10-15), `.../legacy/html` (2021-10-17).
* **Likely work:** early Mapbox style scaffolding and static HTML test pages.
* **Why it matters:** establishes the original visual grammar and layer naming that later “peronómetro” variants reused.

## 2022-11 — Circuitos base repo initialized

* **Evidence:** `CNE-INDEC-georef/circuitos_electorales_AR/.git/*` and `.../geojson` (2022-11-03/12:00).
* **Likely work:** bringing in canonical circuitos GeoJSON and creating a dedicated repo for CNE–IGN alignment tasks.
* **Why it matters:** this repo becomes the source of truth for spatial joins (circuitos/secciones/departamentos).

## 2023-04 — Data ingestion and corpus build (Resultados Provisorios + corrections)

* **Evidence:** `/media/.../datos/Solo_ResultadosProvisorios_edit/*` folders stamped 2023-04-05, `/media/.../datos/correccion` 2023-04-04.
* **Likely work:** bulk import and normalization of official tables; creation of correction dictionaries (nombres de cargos, tipos de voto).
* **Why it matters:** defines the early canonical BD, later mirrored in `datos/BD`.

## 2023-05 — First integrated pipeline: BD → out, web styles, dual trees appear

* **Evidence:** `/media/.../elecciones-ARG` git activity 2023-05-23/24; `/media/.../web/mapbox_styles/*` 2023-05-21–23; `/media/.../datos/out` 2023-05-23/18:24; `CNE-INDEC-georef/mapaelectoral/*` 2023-05-18.
* **Likely work:** end-to-end: load results, aggregate to units, produce out/*.csv; generate map styles and first public pages. Start of duplication: an `elecciones-ARG` subtree inside the external drive alongside the main repo.
* **Why it matters:** first “working loop” from raw → aggregated → map.

## 2023-07 — Consolidation and analysis notebooks

* **Evidence:** `/media/.../elecciones-ARG/notebooks-02-analisis-de-datos` 2023-07-12; repo-level `.git/objects` activity 2023-07-26; `datos/info` internal and mirrored both updated the same day (2023-07-26).
* **Likely work:** analytic notebooks for N de electores, tipos de voto por circuito/depto, agrupaciones; info tables refined and duplicated across trees (risk of divergence).
* **Why it matters:** analytical structure solidifies; duplication risk begins (internal vs external mirror).

## 2023-08 — Web “peronómetro” + EPH cross line starts

* **Evidence:** `elecciones-ARG/notebooks-03-web-peronometro` 2023-08-19/22; `notebooks-04 - Cruce EPH/images` 2023-08-19; external drive `PASO2023` 2023-08-14; `/datos/stats_circuitos` 2023-08-16.
* **Likely work:** generating GeoJSON pct/cnt layers, style scales; starting EPH cross and circuit stats; prepping for 2023 cycle visuals.
* **Why it matters:** the map-build automation and scaling logic show up; socio-econ cross joins get a first pass.

## 2023-10 — General 2023 ingestion and municipal deep-dives

* **Evidence:** `/media/.../ResultadosElectorales_General2023` 2023-10-24; internal `notebooks-01-descomposicion-BD` and `notebooks-02-analisis-de-datos` 2023-10-24; `municipal` and `2023 2DA VUELTA` subdirs 2023-10-24/25; `elecciones-ARG/web` 2023-10-31.
* **Likely work:** full 2023 general election load, decomposition, municipal tabulation, publishing updated web.
* **Why it matters:** this is a real production spike; artifacts and notebooks likely reflect final 2023 conventions.

## 2024-04 — Spatial reference refresh (IGN/CNE join assets)

* **Evidence:** `CNE-INDEC-georef/*` bursts 2024-04-04 to 04-25 across `datos`, `ign_departamento`, `mapaelectoral`, `info`.
* **Likely work:** updating reference geographies and join CSVs; possibly recomputing radios→circuitos and secciones→dptos.
* **Why it matters:** if IDs or geometries changed, any downstream GeoJSON/joins before this date are stale.

## 2024-12 — Minor repo updates

* **Evidence:** `CNE-INDEC-georef/.git/refs/remotes/origin` 2024-12-25.
* **Likely work:** pulls or small updates; no clear pipeline change.

## 2025-02 — New BD slice and cleanup passes

* **Evidence:** `elecciones-ARG/datos/BD151923` 2025-02-17; external `/datos` and `/misc_code` 2025-02-27.
* **Likely work:** adding or reorganizing BD shards; housekeeping scripts and ad-hoc notebooks in `misc_code`.
* **Why it matters:** introduces another potential canonical data location; naming suggests grouping of years 15-19-23.

## 2025-05 — EPH line revisited; georef repo touched

* **Evidence:** `elecciones-ARG/notebooks-04 - Cruce EPH` 2025-05-26; `CNE-INDEC-georef` 2025-05-02/03.
* **Likely work:** resuming EPH cross and ecological inference; minor georef maintenance.
* **Why it matters:** the EPH line is alive and should be in the current briefing/runbook.

## 2025-10 — Recent VCS churn (no clear content writes)

* **Evidence:** `.git` object trees touched in both repos on 2025-10-15; `elecciones-ARG/.git` and `CNE-INDEC-georef/.git`.
* **Caveat:** git object mtimes do not guarantee working tree edits; treat as “recent repo activity,” not data changes.

---

## Cross-cutting observations

* **Duplication drift:** you have overlapping trees: the internal repo `elecciones-ARG` and a mirrored/expanded external `electoral_v1/elecciones-ARG`. Styles and `style_info.json` also appear in multiple places. This is the biggest integrity risk.
* **Spatial baseline changes in 2024-04:** any pre-April 2024 maps likely embed older IDs or shapes; confirm before mixing with newer outputs.
* **BD fragmentation:** `datos/BD` vs `datos/BD151923` plus the legacy BD under `electoral_v1/datos/BD`. Choose one canonical root.

---

## What I’d inspect next to turn this into a precise, file-level timeline

Minimal “heads” to paste so we can lock versions and keys:

1. `elecciones-ARG/datos/BD151923` — list of files and a sample head of each table (`head -n 3`)
2. `electoral_v1/datos/BD/*table.csv` — heads for `eleccion_table`, `cargo_table`, `mesas_table`, and one `votos_eleccion_*`
3. `CNE-INDEC-georef/info/radios_circuitos.csv` and `.../secciones_dptos_ref.csv` — first 5 lines
4. `elecciones-ARG/web/style_info.json` **and** `/media/.../web/style_info.json` — diff to detect drift
5. `elecciones-ARG/notebooks-03-web-peronometro/03 - Votos y porcentajes. GeoJSON.ipynb` — notebook JSON head with cell list to see which scripts write the GeoJSONs

If you want me to refine the diary to a week-level sequence, run these and paste the newest 30 lines each:

```bash
# file-level, newest first
find elecciones-ARG -type f -printf "%TY-%Tm-%Td %TH:%TM %p\n" \
  | sort -r | head -n 200

find CNE-INDEC-georef -type f -printf "%TY-%Tm-%Td %TH:%TM %p\n" \
  | sort -r | head -n 200

find /media/matias/Elements/electoral_v1 -type f -printf "%TY-%Tm-%Td %TH:%TM %p\n" \
  | sort -r | head -n 200
```

---

## One-screen **Briefing stub** (you can drop in once we confirm keys)

* **Purpose:** Build and publish election maps and aggregates for AR, 2011–2023.
* **Last state:** Spatial refs refreshed Apr-2024; EPH cross revived May-2025; potential BD drift due to `BD151923`.
* **Core loop:** Raw CNE → BD tables → joins (CNE-IGN) → aggregates → GeoJSON pct/cnt → web peronómetro.
* **Dependencies:** IGN deptos, circuitos GeoJSON, correction dicts, Mapbox styles.
* **Open frictions:** duplicated trees and style files; unresolved canonical BD root.
* **Next unlocks:**

  1. Decide canonical tree: internal `elecciones-ARG` vs external `electoral_v1/elecciones-ARG`.
  2. Diff `style_info.json` and color CSVs; select single source.
  3. Verify join keys post-2024 refresh; record in runbook.

Want me to convert this into a standardized `briefing.md` and `runbook.md` pair once you paste the file heads above?






Let’s reverse-engineer the model from what you pasted. I’ll be explicit about what’s solid vs. what’s inferred, and I’ll flag the places that will break if we move to a real DB.

# 1) Domains and what each folder is actually doing

* **BD/** — core *relational* slices (dimensions + a sharded fact):
  `eleccion_table`, `cargo_table(+_tags)`, `distrito_table`, `seccion_table`, `seccionprovincial_table`, `circuito_table`, `mesas_table`, `agrupacion_lista_table`, and **`votos_eleccion_*_table`** (mesa-level vote facts partitioned by election id).
* **info/** — *reference joins* and *lookup dictionaries* across official sources (CNE/IGN/INDEC) and your own conventions (fuerzas, style basenames, demographic references).
* **correccion/** — normalization dictionaries for names/labels/types used in ETL.
* **out/** — *derived aggregates* (circ / secc / prov, by tipo / fuerza), plus simple inventory tables.
* **geojson/** — *map artifacts* (pct/cnt by unit) and Mapbox recipe hints.
* **stats_circuitos/** — *external indicators* (EPH/INDEC-like tables) keyed by (prov, dpto, circuito, year), for joins at circuito level.
* **Solo_ResultadosProvisorios_edit/** — archival raw ingests grouped by election.

This is consistent and already close to a star schema with slowly growing dimensions + a very large fact, just sharded by `eleccion_id`.

---

# 2) Canonical schema (proposed) with columns, PKs, FKs

I’m writing this as a **normalized Postgres** target. Types are chosen to stop the float-ID drift I see in the CSVs (`0.0`, leading zeros, etc.).

## 2.1 Dimensions

### `eleccion`

* **Columns:**
  `eleccion_id INT PRIMARY KEY`
  `anio SMALLINT NOT NULL`
  `eleccion_tipo TEXT CHECK (eleccion_tipo IN ('PASO','GENERAL','2DA_VUELTA', ...))`
  `recuento_tipo TEXT`  (e.g., PROVISORIO)
  `padron_tipo TEXT`    (e.g., NORMAL)
  `eleccion_tag TEXT UNIQUE` *(from BD/eleccion_tags.csv)*
* **Notes:** present in `BD/eleccion_table.csv` + `eleccion_tags.csv`. Year also appears elsewhere as `ANO4` in stats.

### `cargo`

* **Columns:**
  `cargo_id INT PRIMARY KEY`
  `cargo_nombre TEXT NOT NULL`
  `cargo_tag TEXT` *(DN/PR etc.; from cargo_tags)*
* **Notes:** small, stable lookup.

### `distrito`

* **Columns:**
  `distrito_id INT PRIMARY KEY`
  `distrito_nombre TEXT NOT NULL`
* **Notes:** from `BD/distrito_table.csv`.

### `seccionprovincial`

* **Columns:**
  `distrito_id INT NOT NULL REFERENCES distrito`
  `seccionprovincial_id INT NOT NULL DEFAULT 0`
  `seccionprovincial_nombre TEXT`
  **PK:** `(distrito_id, seccionprovincial_id)`
* **Notes:** CSV shows `0` used widely; treat it as “no aplica”.

### `seccion`

* **Columns:**
  `distrito_id INT NOT NULL REFERENCES distrito`
  `seccion_id INT NOT NULL`
  `seccionprovincial_id INT NOT NULL DEFAULT 0` REFERENCES seccionprovincial(distrito_id,seccionprovincial_id)
  `seccion_nombre TEXT NOT NULL`
* **PK:** `(distrito_id, seccion_id)`
* **Notes:** CSVs sometimes have floats (`0.0`), so cast to INT on load.

### `circuito`

* **Columns:**
  `eleccion_id INT NOT NULL REFERENCES eleccion`
  `distrito_id INT NOT NULL REFERENCES distrito`
  `seccion_id INT NOT NULL` REFERENCES seccion(distrito_id,seccion_id)
  `seccionprovincial_id INT NOT NULL DEFAULT 0`
  `circuito_id TEXT NOT NULL` *(keep as TEXT to preserve leading zeros & alphanum like `0009A`, `00417B`)*
  `circuito_nombre TEXT`
* **PK:** `(eleccion_id, distrito_id, seccion_id, circuito_id)`
* **Notes:** You currently record circuits per election in `BD/circuito_table.csv`. Good: circuits do change across cycles; keying by election prevents silent mismatches.

### `mesa`

* **Columns:**
  `eleccion_id INT NOT NULL REFERENCES eleccion`
  `distrito_id INT NOT NULL`
  `seccion_id INT NOT NULL`
  `circuito_id TEXT NOT NULL`
  `mesa_id TEXT NOT NULL` *(keep TEXT to preserve zero-padding)*
  `mesa_electores INT`
  `mesa_tipo TEXT` *(NATIVOS, etc.)*
* **PK:** `(eleccion_id, distrito_id, seccion_id, circuito_id, mesa_id)`
* **FK:** to `circuito` via `(eleccion_id,distrito_id,seccion_id,circuito_id)`
* **Notes:** from `BD/mesas_table.csv`.

### `agrupacion` / `lista`

Given `BD/agrupacion_lista_table.csv` mixes both:

* **Option A (simple, denormalized):** keep a single table `agrupacion_lista`:

  * **Columns:**
    `eleccion_id INT`
    `distrito_id INT`
    `agrupacion_id TEXT` *(TEXT to avoid `509.0` issues)*
    `votos_tipo TEXT` *(POSITIVO, BLANCO, etc.)*
    `lista_numero TEXT` *(TEXT; can be alpha/num)*
    `agrupacion_nombre TEXT`
    `lista_nombre TEXT`
  * **PK candidate:** `(eleccion_id,distrito_id,agrupacion_id,lista_numero)`
  * **Use:** join for labels/metadata when summarizing.
* **Option B (proper 3NF):** split into `agrupacion` and `lista`, but given variation by distrito/eleccion, Option A is pragmatic.

---

## 2.2 Fact table (mesa-level votes)

### `voto_mesa`

* **Columns:**
  `eleccion_id INT NOT NULL`
  `distrito_id INT NOT NULL`
  `seccionprovincial_id INT NOT NULL DEFAULT 0`
  `seccion_id INT NOT NULL`
  `circuito_id TEXT NOT NULL`
  `mesa_id TEXT NOT NULL`
  `cargo_id INT NOT NULL`
  `agrupacion_id TEXT` *(nullable for COMANDO/NULO/BLANCO/… rows where party is not present)*
  `agrupacion_nombre TEXT` *(optional shadow label)*
  `lista_numero TEXT` *(nullable)*
  `votos_tipo TEXT NOT NULL` *(POSITIVO, BLANCO, NULO, RECURRIDO, COMANDO, etc.)*
  `votos_cantidad INT NOT NULL`
* **PK (logical):** `(eleccion_id,distrito_id,seccion_id,circuito_id,mesa_id,cargo_id,COALESCE(agrupacion_id,'~'),votos_tipo,COALESCE(lista_numero,'~'))`
* **FKs:**
  → `mesa` (same 5-tuple)
  → `cargo(cargo_id)`
  → optionally `agrupacion_lista` if you want label integrity
* **Storage:** *Partition by* `eleccion_id` (what you already have as `votos_eleccion_*_table.csv`). In PG, use range/hash partitions per `eleccion_id` for speed.

---

## 2.3 Reference / integration dimensions (from `info/`)

These aren’t required to define the fact, but they power joins & maps:

### `seccion_dpto_ref` (from `info/secciones_dptos_ref.csv`)

* **Columns:**
  `(distrito_id,seccion_id)` + `seccionprovincial_id,seccion_nombre`
  `PROV_REF_ID,IDPROV,NOMPROV`
  `DPTO_REF_ID,IDDPTO,NOMDPTO,DPTO` *(DPTO looks like a 4-digit code like 2001/2002 for CABA comunas)*
* **PK:** `(distrito_id, seccion_id)` (plus versioning if these change over time).

### `radio_ref` (from `info/radio_ref.csv`)

* **Columns:** many, but the stable keys are `PROV_REF_ID, IDPROV, DPTO_REF_ID, IDDPTO, CPV2010_REF_ID, IDRADIO, radio` + human names + region.
* **Use:** if you later go radio→circuito joins or demographics.

### `DistritosSecciones`

* **Columns:** `distrito_id,distrito_nombre,seccion_id,seccion_nombre,tag`
* **Use:** inventory per election/tag; not authoritative keys.

### `agrupacion_nombre_weight_labels`

* **Columns:** `agrupacion_nombre, votos_cantidad, fuerza`
* **Use:** map arbitrary *agrupaciones* to a *fuerza* bucket (PERON, etc.) for rollups.

---

## 2.4 External indicators (from `stats_circuitos/`)

All have:
`Region, PROV, NOMPROV, DPTO, circuito, ANO4, <metric columns…>`

* **Proposed table:** `indicador_circuito`

  * **Columns:**
    `indicador TEXT` *(e.g., 'CAT_INAC','CAT_OCUP','CH07','H09', …)*
    `ano SMALLINT` *(from ANO4)*
    `prov TEXT` *(code? check if numeric string)*
    `nomprov TEXT`
    `dpto TEXT`
    `circuito TEXT` *(matches your circuito_id formatting with alphanum)*
    `k TEXT` *(the metric column name)*
    `v NUMERIC` *(value)*
  * **PK:** `(indicador, ano, prov, dpto, circuito, k)`
  * **Join key:** `(DPTO, circuito, ANO4)` → **must be reconciled** to your `(distrito,seccion,circuito,eleccion.anio)`. You’ll likely go through `seccion_dpto_ref` to map DPTO to `(distrito,seccion)` then attach `circuito`.

---

# 3) Data products already present (and how they derive)

### Aggregates in `out/`

* **`elecciones_ppales`**
  Columns: `anio, eleccion_tipo, recuento_tipo, padron_tipo, cargo_id, cargo_nombre`
  → *dimensional inventory* of “main elections” per cargo.
* **`elecciones_cargos_votos`**
  `anio, eleccion_tipo, recuento_tipo, padron_tipo, cargo_id, cargo_nombre, votos_tipo, votos_cantidad_size, votos_cantidad_sum`
  → rollup of `voto_mesa` grouped by `(eleccion.dim fields, cargo, votos_tipo)`.
* **`n_electores_circ` / `n_electores_dpto`**
  sums (`mesa_electores`) grouped by circ or depto. Beware duplicate “mesa_electores” header printed twice in the head you pasted (one is alias for sum/size).
  → from `mesa` with `GROUP BY` joins to seccion/dpto.
* **`votos_circ` / `votos_secc` / `votos_prov`**
  fields show `eleccion_id, cargo_id, fuerza, …, votos_cantidad`
  → rollups of POSITIVO votes by **fuerza** bucket (via `agrupacion_nombre_weight_labels`), grouped by the spatial unit.
  (Empty `fuerza` in your heads suggests some rows are unclassified—needs fixing).
* **`votos_tipo_circ` / `votos_tipo_dpto` / `votos_tipo_mesa`**
  explicit *vote type* rollups (BLANCO, IMPUGNADO, etc.).
  Note: `votos_tipo_mesa` is huge (624MB), so consider materialized view in DB + indices.

### Map layers in `geojson/`

* `votos_cnt_*` / `votos_pct_*` / `votos_*` for circ/prov/secc
  → feature properties likely include counts / percentages by fuerza or top lines.
* `*_recipe.json` files
  → instructions tying layer names to styles (Mapbox) and which fields to symbolize.

---

# 4) Edge cases you need to fix before DB-ifying

1. **Floaty IDs in CSVs**
   You’ve got `0.0`, `503.0`, etc. in IDs and `seccionprovincial_id`. These must cast to `INT` and `TEXT` decisively on load.
2. **Alphanumeric circuitos**
   Examples: `0009A`, `00417B`. Keep them **TEXT** end-to-end. Don’t coerce to int.
3. **Missing agrupación fields for administrative votes**
   Rows with `votos_tipo in ('COMANDO','NULO','RECURRIDO','BLANCO')` have empty `agrupacion_id/nombre`. Make those columns nullable and **exclude from fuerza rollups**.
4. **Election-dependent circuito geometry**
   Since `circuito_table` is keyed by `eleccion_id`, any spatial joins for maps must also be versioned, or you’ll mix geometries across years.
5. **DPTO mapping**
   `stats_circuitos` uses `DPTO` string codes; your production rollups use `(distrito,seccion)` or `DPTO_REF_ID`. Freeze a canonical bridge: `DPTO_REF_ID <-> (distrito,seccion)`.

---

# 5) Minimal DDL sketch (enough to start loading)

```sql
-- dims
CREATE TABLE eleccion (
  eleccion_id INT PRIMARY KEY,
  anio SMALLINT NOT NULL,
  eleccion_tipo TEXT NOT NULL,
  recuento_tipo TEXT NOT NULL,
  padron_tipo TEXT NOT NULL,
  eleccion_tag TEXT UNIQUE
);

CREATE TABLE cargo (
  cargo_id INT PRIMARY KEY,
  cargo_nombre TEXT NOT NULL,
  cargo_tag TEXT
);

CREATE TABLE distrito (
  distrito_id INT PRIMARY KEY,
  distrito_nombre TEXT NOT NULL
);

CREATE TABLE seccionprovincial (
  distrito_id INT REFERENCES distrito,
  seccionprovincial_id INT NOT NULL DEFAULT 0,
  seccionprovincial_nombre TEXT,
  PRIMARY KEY (distrito_id, seccionprovincial_id)
);

CREATE TABLE seccion (
  distrito_id INT REFERENCES distrito,
  seccion_id INT NOT NULL,
  seccionprovincial_id INT NOT NULL DEFAULT 0,
  seccion_nombre TEXT NOT NULL,
  PRIMARY KEY (distrito_id, seccion_id),
  FOREIGN KEY (distrito_id, seccionprovincial_id)
    REFERENCES seccionprovincial(distrito_id, seccionprovincial_id)
);

CREATE TABLE circuito (
  eleccion_id INT REFERENCES eleccion,
  distrito_id INT REFERENCES distrito,
  seccion_id INT,
  seccionprovincial_id INT NOT NULL DEFAULT 0,
  circuito_id TEXT NOT NULL,
  circuito_nombre TEXT,
  PRIMARY KEY (eleccion_id, distrito_id, seccion_id, circuito_id),
  FOREIGN KEY (distrito_id, seccion_id) REFERENCES seccion(distrito_id, seccion_id)
);

CREATE TABLE mesa (
  eleccion_id INT REFERENCES eleccion,
  distrito_id INT,
  seccion_id INT,
  circuito_id TEXT,
  mesa_id TEXT,
  mesa_electores INT,
  mesa_tipo TEXT,
  PRIMARY KEY (eleccion_id, distrito_id, seccion_id, circuito_id, mesa_id),
  FOREIGN KEY (eleccion_id, distrito_id, seccion_id, circuito_id)
    REFERENCES circuito(eleccion_id, distrito_id, seccion_id, circuito_id)
);

-- optional denorm for labels
CREATE TABLE agrupacion_lista (
  eleccion_id INT REFERENCES eleccion,
  distrito_id INT REFERENCES distrito,
  agrupacion_id TEXT,
  lista_numero TEXT,
  votos_tipo TEXT,
  agrupacion_nombre TEXT,
  lista_nombre TEXT,
  PRIMARY KEY (eleccion_id, distrito_id, agrupacion_id, lista_numero)
);

-- fact (partitioned by eleccion_id in practice)
CREATE TABLE voto_mesa (
  eleccion_id INT NOT NULL,
  distrito_id INT NOT NULL,
  seccionprovincial_id INT NOT NULL DEFAULT 0,
  seccion_id INT NOT NULL,
  circuito_id TEXT NOT NULL,
  mesa_id TEXT NOT NULL,
  cargo_id INT NOT NULL REFERENCES cargo,
  agrupacion_id TEXT,
  agrupacion_nombre TEXT,
  lista_numero TEXT,
  votos_tipo TEXT NOT NULL,
  votos_cantidad INT NOT NULL,
  PRIMARY KEY (eleccion_id, distrito_id, seccion_id, circuito_id, mesa_id, cargo_id,
               COALESCE(agrupacion_id,'~'), votos_tipo, COALESCE(lista_numero,'~')),
  FOREIGN KEY (eleccion_id, distrito_id, seccion_id, circuito_id, mesa_id)
    REFERENCES mesa(eleccion_id, distrito_id, seccion_id, circuito_id, mesa_id)
);
```

*(For real PG, you can’t use `COALESCE` in a PK; use nullable columns + a generated “surrogate” key, or store `agrupacion_id/lista_numero` as `TEXT DEFAULT '~'`.)*

---

# 6) How existing CSVs slot into the schema

* **Load order:** `eleccion` → `cargo` → `distrito` → `seccionprovincial` → `seccion` → `circuito` → `mesa` → `agrupacion_lista` → `voto_mesa` (per `votos_eleccion_*` shard).
* **`out/*.csv`** become *materialized views* over `voto_mesa` + `mesa` + `agrupacion_nombre_weight_labels`.
* **`geojson/*.geojson`** are *ETL outputs* of views above joined with geometry (not shown here; if you persist geometries, use `postgis` and keep a `geom` table keyed by the same unit keys + `eleccion_id` version).
* **`stats_circuitos/*.csv`** load into `indicador_circuito` and join to `circuito` via a *bridge* using `info/secciones_dptos_ref.csv` (and, if needed, a `circuito` naming concordance).

---

# 7) Things that don’t hold unless we fix them

* `fuerza` missing in `out/votos_*` heads → either the mapping didn’t run or some names don’t match the weighting table. Expect leakage; add a **left join diagnostic** to count unmapped agrupaciones by election.
* Duplicated header lines in `n_electores_*` (you pasted a two-row header). Clean at ETL or enforce CSV writer config.
* `seccionprovincial_id` appears as float in several CSVs (`0.0`). Coerce to INT on load.
* Some `votos_*` shards include `COMANDO` rows for many `cargo_id`s. In views, **exclude** non-POSITIVE where required or they will pollute denominators.

---

# 8) Minimal set of DB views/materializations to reproduce `out/`

1. **Electores por circuito**

```sql
CREATE MATERIALIZED VIEW mv_electores_circ AS
SELECT eleccion_id, distrito_id, seccion_id, circuito_id,
       SUM(mesa_electores) AS mesa_electores_sum,
       COUNT(*)            AS mesa_count
FROM mesa
GROUP BY 1,2,3,4;
```

2. **Votos por tipo y circuito**

```sql
CREATE MATERIALIZED VIEW mv_votos_tipo_circ AS
SELECT eleccion_id, cargo_id, distrito_id, seccionprovincial_id,
       seccion_id, circuito_id, votos_tipo, SUM(votos_cantidad) AS votos
FROM voto_mesa
GROUP BY 1,2,3,4,5,6,7;
```

3. **Votos por fuerza (need mapping)**

```sql
-- staging: map agrupacion_nombre->fuerza
-- (or join by agrupacion_id if you stabilize it)
CREATE MATERIALIZED VIEW mv_votos_fuerza_circ AS
WITH map AS (
  SELECT UPPER(TRIM(agrupacion_nombre)) AS key, fuerza
  FROM info_agrupacion_nombre_weight_labels
)
SELECT v.eleccion_id, v.cargo_id, f.fuerza,
       v.distrito_id, v.seccion_id, v.circuito_id,
       SUM(v.votos_cantidad) AS votos
FROM voto_mesa v
JOIN map f
  ON UPPER(TRIM(v.agrupacion_nombre)) = f.key
WHERE v.votos_tipo = 'POSITIVO'
GROUP BY 1,2,3,4,5,6;
```

*(Replace `info_agrupacion_nombre_weight_labels` with the actual loaded table name.)*

---

# 9) Migration path without pain

1. **Staging loads** with strict casting:

   * All IDs to **INT** or **TEXT** (no floats).
   * Strip whitespace; preserve leading zeros for circuitos/mesas.
2. **Surrogates where needed:** if agrupación IDs are not stable across years/distritos, do not pretend they are. Keep them text + eleccion/distrito scoped.
3. **Partition `voto_mesa`** by `eleccion_id`. You already shard by files; keep that physically in DB.
4. **Bridge tables** for DPTO/SECCION and for any circuito renames across years. These are small and save 90% of headaches.
5. **Materialize `out/`** as views with indexes; keep `geojson/` as export step (or store geometries in PostGIS).

---

If you paste **one** representative row for: a POSITIVO vote, a BLANCO vote, and a COMANDO row (each with all fields), I can verify the *exact* PK/NULLability rules and give you loader SQL that will pass on the first try.






