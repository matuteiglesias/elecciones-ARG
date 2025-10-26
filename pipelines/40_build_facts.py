#!/usr/bin/env python3
# pipelines/40_build_facts.py

import argparse
from pathlib import Path
import sys
import pandas as pd
import yaml

FACT_OUT = "votos_fact.csv"

# Columns we keep in the fact (only those that exist will be written)
FACT_COLS_PREF = [
    "eleccion_id", "año", "eleccion_tipo", "recuento_tipo", "padron_tipo",
    "distrito_id", "seccionprovincial_id", "seccion_id", "circuito_id", "mesa_id",
    "cargo_id", "agrupacion_id", "lista_numero", "votos_tipo", "votos_cantidad"
]

LEGACY_MIN_COLS = [
    "eleccion_id", "distrito_id", "seccion_id", "seccionprovincial_id",
    "circuito_id", "mesa_id", "cargo_id", "agrupacion_id", "lista_numero",
    "votos_tipo", "votos_cantidad"
]

def fail(msg, sample=None, code=1):
    print(msg, file=sys.stderr)
    if sample is not None:
        print(sample, file=sys.stderr)
    sys.exit(code)

def load_yaml(p):
    with open(p, "r") as f:
        return yaml.safe_load(f)

def ensure_parents(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)

def read_normalized(staging_dir: Path) -> pd.DataFrame:
    p = staging_dir / "all_normalized.csv"
    if not p.exists():
        fail(f"[facts] Missing input: {p}")
    # Keep strings; coerce only votos_cantidad
    df = pd.read_csv(p, dtype="object")
    if "votos_cantidad" in df.columns:
        df["votos_cantidad"] = pd.to_numeric(df["votos_cantidad"], errors="coerce")
    return df

def compute_grain_columns(df: pd.DataFrame) -> list:
    # Mesa × cargo × agrupacion/lista × votos_tipo
    key = [
        "eleccion_id", "distrito_id", "seccion_id", "circuito_id", "mesa_id",
        "cargo_id", "agrupacion_id", "votos_tipo"
    ]
    if "lista_numero" in df.columns:
        key.insert(key.index("votos_tipo"), "lista_numero")
    # guard: ensure keys exist
    missing = [c for c in key if c not in df.columns]
    if missing:
        fail(f"[facts] Missing required key columns for fact grain: {missing}")
    return key

def assert_no_duplicates(df: pd.DataFrame, grain: list):
    dup_mask = df.duplicated(subset=grain, keep=False)
    if dup_mask.any():
        sample = df.loc[dup_mask, grain].head(15).to_string(index=False)
        fail("[facts] Duplicate rows at fact grain. Normalize upstream; do not aggregate here.", sample)

def write_csv_atomic(df: pd.DataFrame, out_path: Path):
    ensure_parents(out_path)
    tmp = out_path.with_suffix(".tmp.csv")
    df.to_csv(tmp, index=False)
    tmp.replace(out_path)

def write_legacy_shards(df_fact: pd.DataFrame, bd_csv_dir: Path):
    # Keep only columns available
    cols = [c for c in LEGACY_MIN_COLS if c in df_fact.columns]
    for eleccion_id, part in df_fact.groupby("eleccion_id", sort=True):
        out = bd_csv_dir / f"votos_eleccion_{eleccion_id}_table.csv"
        write_csv_atomic(part[cols].copy(), out)

def maybe_write_parquet(df_fact: pd.DataFrame, parquet_dir: Path, parquet_min_rows: int):
    if not parquet_dir or str(parquet_dir).strip() in ("", ".", "./"):
        return
    if parquet_min_rows is None:
        parquet_min_rows = 1_000_000  # default safeguard
    # Partition by year and election type if columns exist
    if "año" not in df_fact.columns or "eleccion_tipo" not in df_fact.columns:
        return
    # Only write partitions that are “heavy enough”
    for (year, etype), g in df_fact.groupby(["año", "eleccion_tipo"], sort=True):
        if len(g) < parquet_min_rows:
            continue
        # Keep a lean set of columns (whatever exists from FACT_COLS_PREF)
        cols = [c for c in FACT_COLS_PREF if c in g.columns]
        sub = g[cols].copy()
        out_dir = parquet_dir / "votos_fact" / f"year={year}" / f"eleccion_tipo={etype}"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "part-00000.parquet"
        # pyarrow preferred; pandas will pick it if installed
        sub.to_parquet(out_path, index=False)
        print(f"[facts] Parquet wrote: {out_path} ({len(sub):,} rows)")

def main(args):
    cfg = load_yaml(args.config)
    staging_dir = Path(cfg.get("staging_dir", "canon/staging"))
    bd_csv_dir = Path(cfg.get("bd_csv_dir", "canon/bd/csv"))
    parquet_dir_cfg = cfg.get("parquet_dir", "").strip()
    parquet_dir = Path(parquet_dir_cfg) if parquet_dir_cfg else None
    parquet_min_rows = cfg.get("parquet_min_rows", None)

    df = read_normalized(staging_dir)

    # Build the long fact frame (select & order columns that exist)
    keep_cols = [c for c in FACT_COLS_PREF if c in df.columns]
    fact = df[keep_cols].copy()

    # Enforce grain and duplicates check
    grain = compute_grain_columns(fact)
    assert_no_duplicates(fact, grain)

    # Write votos_fact.csv
    fact_out = bd_csv_dir / FACT_OUT
    write_csv_atomic(fact, fact_out)

    # Write legacy per-elección shards for compatibility
    write_legacy_shards(fact, bd_csv_dir)

    # Optional Parquet for heavy partitions
    if parquet_dir is not None:
        maybe_write_parquet(fact, parquet_dir, parquet_min_rows)

    # Small, explicit footer
    print(f"[facts] OK → {fact_out} ({len(fact):,} rows)")
    print(f"[facts] Grain = {grain}")
    print(f"[facts] Legacy shards under {bd_csv_dir}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="Path to YAML config (pipelines/00_config.yml)")
    main(ap.parse_args())
