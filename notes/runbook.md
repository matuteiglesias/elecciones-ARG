Here’s a compact runbook you can actually use. I’ll keep it operational, point out where things usually break, and flag invariants you should protect.

# Runbook — elecciones-ARG data pipeline

## 0) Pre-reqs & layout

* Python 3.10+, `pip install -e .` in repo root.
* Packages: `pandas`, `pyyaml`, `openpyxl`.
* Expected tree (short):
  `canon/staging/`, `canon/schema/`, `canon/bd/csv/`, `exports/out/`, `pipelines/*.py`

**Config**: `pipelines/00_config.yml`

```yaml
staging_dir: canon/staging
schema_dir:  canon/schema
bd_csv_dir:  canon/csv
exports_dir: exports/out
# For 55_load_mesa_roll.py
ayt_path: "/media/matias/Elements/electoral_lake/raw/2025/00_DINE_Total pais 2025 Final_21-10 (1).xlsx"
eleccion_filter:
  año: "2025"
  eleccion_tipo: "GENERAL"
  recuento_tipo: "PROVISORIO"
  padron_tipo: "NORMAL"
ayt_columns_map:
  distrito_id: "DISTRITO"
  seccion_id:  "SECCION"
  circuito_id: "CIRCUITO"
  mesa_id:     "MESA"
  n_electores: "CANT_ELECTORES AyT"
canonical_mesa_tipo_fill: "NATIVOS"
```

## 1) Extract & concatenate raw → staging

Purpose: read all vendor CSVs, detect encoding/dialect, chunk-append, produce a single `all_raw.csv` and a provenance `manifest.csv`.

```bash
PYTHONPATH=$(pwd) python3 pipelines/10_extract_concat_raw.py --config pipelines/00_config.yml
```

You should see:

* `canon/staging/all_raw.csv` (no types enforced)
* `canon/staging/manifest.csv` (source_id, sha256, rows, dialect, etc.)

**Tripwire**: if `manifest.csv` shows repeated identical SHA with different row counts, you’re double-counting files. Fix your glob.

## 2) Normalize core (IDs, mappings, eleccion_id)

Purpose: clean structural fields, map `votos_tipo` (via `votos_tipo_map.json`), map `cargo`, attach strict `eleccion_id` via `eleccion_dim.csv`.

```bash
PYTHONPATH=$(pwd) python3 pipelines/20_normalize_core.py --config pipelines/00_config.yml
```

Outputs:

* `canon/staging/all_normalized.csv`

**Guardrails that will fail fast (by design):**

* Missing `votos_tipo_map.json` or unmapped keys.
* `cargo_map.csv` incomplete.
* `eleccion_dim.csv` missing tuples → **do not** invent IDs; extend via step 30.

## 3) Build dimension tables

Purpose: harmonize names, materialize core dims, finalize/append `eleccion_dim` if needed.

```bash
PYTHONPATH=$(pwd) python3 pipelines/30_build_dims.py --config pipelines/00_config.yml
```

Outputs (in `canon/bd/csv/`):

* `eleccion_table.csv`, `distrito_table.csv`, `seccion_table.csv`, `circuito_table.csv`,
  `mesas_table.csv`, `cargo_table.csv`, `agrupacion_lista_table.csv`

**Edge-case to watch**: name canonicalization uses “most frequent, shortest” heuristic—don’t feed mixed-casing or stray trailing spaces upstream; fix those in 20_ if they recur.

## 4) Build long facts (votos)

Purpose: produce a single long `votos_fact.csv` across elections/cargos, with stable keys.

```bash
PYTHONPATH=$(pwd) python3 pipelines/40_build_facts.py --config pipelines/00_config.yml
```

Outputs:

* `canon/bd/csv/votos_fact.csv`

**Invariant**: no negative `votos_cantidad`. If you see them, your vendor file probably encodes missing as “-” or uses parentheses.

## 5) (Optional) Load candidates (2025+)

Purpose: ingest slates to person-centric tables and a candidatura fact; dedupe socials to long form.

```bash
PYTHONPATH=$(pwd) python3 pipelines/50_load_candidates.py --config pipelines/00_config.yml
```

Outputs:

* `persona_dim.csv`, `persona_social_dim.csv`, `candidatura_fact.csv` (+ potential lista upserts)

**ID rule**: `persona_id` from DNI else MD5 of (nombres, apellido, fecha_nacimiento, genero).

## 6) Upsert padrón de mesa (AyT 2025) into canonical

Purpose: fold AyT padrón por mesa into `mesas_table.csv` for target election; keep an audit roll and discrepancies.

```bash
PYTHONPATH=$(pwd) python3 pipelines/55_load_mesa_roll.py --config pipelines/00_config.yml
```

Outputs:

* `mesa_roll.csv` (audit; PK includes `roll_source`)
* `mesa_roll_discrepancias.csv` (Δ AyT − canonical, pre-upsert)
* **UPDATED** `mesas_table.csv` (AyT rows inserted/overwritten for the target `eleccion_id`; `mesa_tipo=NATIVOS` where touched)

**Decision**: Prefer maintaining only **canonical** going forward; remove `mesas_resolved.csv` if present to avoid ambiguity.

## 7) Build aggregates for EDA

Purpose: dedupe mesa grain, then write electors & votos_tipo cubes. Never use `.size`—use `nunique(mesa_id)`.

```bash
python3 pipelines/60_build_aggregates.py --config pipelines/00_config.yml
```

Outputs (in `exports/out/`):

* `n_electores_{dpto,circ}.csv`
* `votos_tipo_{mesa,circ,dpto}.csv`

**Sanity**: rows in `n_electores_circ.csv` should match `circuito_table.csv` for built elections.

## 8) QA checks (trip-wire)

Purpose: fail fast on structural issues; warn on expected-but-not-fatal gaps during ingestion.

```bash
python3 pipelines/70_qa_checks.py --config pipelines/00_config.yml
```

Outputs:

* `exports/qa/report.json` + `report.txt`

Checks:

* coverage votos↔mesas ≥ 98% per `eleccion_id`
* non-negativity (votes/electors)
* vote conservation (see “Second look” below)
* ID stability (strings; `circuito_id` length=6)
* `eleccion_id` completeness; candidates continuity/dup detection

**Second look**: Your recent **WARN** is from `POS_list_vs_total_mismatch` on 8,453 circuit groups. That usually means duplicate aggregate POSITIVO rows or a rule mismatch. Decide whether aggregated `POSITIVO` are authoritative; if not, scope the check to single-aggregate groups or compare at mesa grain.

## 9) Snapshot (receipt)

Purpose: mint a manifest with inputs, table/export row counts, md5s, and QA summary.

```bash
python3 pipelines/80_snapshot_manifest.py --config pipelines/00_config.yml
```

Output:

* `snapshots/<YYYYMMDD-HHMM>/MANIFEST.json`

**How to use**: Keep these in VCS; they’re cheap and anchor reproducibility (md5 + counts + QA).

---

## Minimal “happy-path” command block

```bash
# 1→4 core
PYTHONPATH=$(pwd) python3 pipelines/10_extract_concat_raw.py --config pipelines/00_config.yml
PYTHONPATH=$(pwd) python3 pipelines/20_normalize_core.py   --config pipelines/00_config.yml
PYTHONPATH=$(pwd) python3 pipelines/30_build_dims.py       --config pipelines/00_config.yml
PYTHONPATH=$(pwd) python3 pipelines/40_build_facts.py      --config pipelines/00_config.yml

# 5 optional, 6 AyT upsert, 7 aggregates
PYTHONPATH=$(pwd) python3 pipelines/50_load_candidates.py  --config pipelines/00_config.yml   # optional
PYTHONPATH=$(pwd) python3 pipelines/55_load_mesa_roll.py   --config pipelines/00_config.yml
python3                pipelines/60_build_aggregates.py    --config pipelines/00_config.yml

# 8 QA + 9 snapshot
python3 pipelines/70_qa_checks.py        --config pipelines/00_config.yml
python3 pipelines/80_snapshot_manifest.py --config pipelines/00_config.yml
```

---

## Troubleshooting (fast)

* **20_normalize_core bombs on `votos_tipo`**
  → open `canon/schema/votos_tipo_map.json`; add unmapped keys exactly once, rerun 20.

* **30_build_dims says missing election tuple**
  → add the tuple in `eleccion_dim.csv` via 30 (it auto-appends deterministically), rerun 20 then 30.

* **55 upsert creates huge deltas**
  → inspect `mesa_roll_discrepancias.csv`; if too many large deltas, abort and fix AyT source or tighten 55 with a threshold gate.

* **70 QA WARN on vote conservation**
  → run the three triage snippets I suggested earlier to isolate duplication vs rule mismatch; adjust the QA to skip multi-aggregate groups.

* **Exports row counts look low/high**
  → ensure 60 is reading the intended mesas source (canonical). If `mesas_resolved.csv` lingers, either delete it or force canonical in `prefer_resolved_mesas`.

---

## Invariants worth enforcing (or you’ll chase ghosts later)

* All geo IDs are strings; `circuito_id` is 6-char, left-padded **only if numeric**.
* Never invent `mesa_electores=0`; leave missing as missing and surface in discrepancy reports.
* `eleccion_id` is assigned **only** via `eleccion_dim.csv` (30 owns that contract).
* Mesa counts in aggregates must be `nunique(mesa_id)` over a deduped mesa grain.

---

## Performance notes (so you don’t regress)

* Large `votos_fact.csv`: favor `dtype="object"` on read; convert only the needed numeric columns.
* When appending/upserting (55), always write temp file then atomic replace—already in your code.
* For EDA exports, you can mirror to Parquet if notebooks start to bog down.

---

## Optional hardening (future)

* Add a **gate** in 55: fail if `abs_delta > 50` for more than, say, 0.5% of mesas.
* In 70, write a **small CSV of worst offenders** for conservation (top |delta| with keys) alongside the JSON.
* Add a `make` target or `tox` env to run 10→80 in sequence, and a `—only` switch per step.

That’s the backbone. If you want this packaged as `make` targets or a CLI entry point (`python -m pipelines run --until 60`), I can sketch that next.
