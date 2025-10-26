#!/usr/bin/env python3
# pipelines/30_build_dims.py
# Goal: materialize dimension tables from normalized data and finalize eleccion_dim.csv if needed.

import argparse
import hashlib
from pathlib import Path

import pandas as pd
import yaml

# --------------------------
# Helpers
# --------------------------

def load_yaml(p):
    with open(p, "r") as f:
        return yaml.safe_load(f)

def ensure_parents(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)

def canonical_name(series: pd.Series) -> str:
    """Most frequent non-empty; tie-break shortest string."""
    s = series.dropna().astype(str).str.strip()
    s = s[s != ""]
    if s.empty:
        return ""
    vc = s.value_counts()
    top_count = vc.iloc[0]
    candidates = vc[vc == top_count].index.tolist()
    # shortest wins; if tie, lexicographically smallest for determinism
    candidates.sort(key=lambda x: (len(x), x))
    return candidates[0]

def apply_name_harmonization(df: pd.DataFrame, id_cols, name_col):
    """Return a DataFrame where name_col is canonical per id_cols, no in-place mutation."""
    if name_col not in df.columns:
        # Nothing to harmonize; return deduped ids.
        return df[id_cols].drop_duplicates().reset_index(drop=True)
    work = df[id_cols + [name_col]].copy()
    # normalize case gently; you can tune this if you want strict original casing
    work[name_col] = work[name_col].astype("string")
    canon = (
        work.groupby(id_cols, dropna=False)[name_col]
        .apply(canonical_name)
        .reset_index(name=name_col)
    )
    return canon

def stable_md5_id(parts) -> str:
    """Deterministic surrogate id from tuple of parts; returns 32-char hex."""
    key = "|".join("" if p is None else str(p) for p in parts)
    return hashlib.md5(key.encode("utf-8")).hexdigest()

def assign_dense_ids(df: pd.DataFrame, key_cols: list, id_col: str) -> pd.DataFrame:
    """Map sorted unique keys to dense stable ids starting at 1 (as strings)."""
    keys = (
        df[key_cols]
        .astype(str)
        .fillna("")
        .drop_duplicates()
        .sort_values(key_cols)
        .reset_index(drop=True)
    )
    keys[id_col] = (keys.index + 1).astype(str)
    return df.merge(keys, on=key_cols, how="left", validate="m:1")

# --------------------------
# Eleccion dim maintenance
# --------------------------

def finalize_eleccion_dim(df_norm: pd.DataFrame, schema_dir: Path) -> pd.DataFrame:
    """
    Ensure eleccion_dim.csv contains all tuples present in normalized data.
    If missing tuples exist, append rows with deterministic eleccion_id assignment.
    Deterministic rule: sort tuples and assign next integers after current max.
    """
    elec_path = schema_dir / "eleccion_dim.csv"
    if not elec_path.exists():
        raise FileNotFoundError(f"Missing schema file: {elec_path}")

    dim = pd.read_csv(elec_path, dtype="object")
    for c in ["año", "eleccion_tipo", "recuento_tipo", "padron_tipo", "eleccion_id"]:
        if c not in dim.columns:
            raise ValueError("eleccion_dim.csv must include: año, eleccion_tipo, recuento_tipo, padron_tipo, eleccion_id")

    # tuples required by normalized
    need = (
        df_norm[["año", "eleccion_tipo", "recuento_tipo", "padron_tipo"]]
        .astype("string").apply(lambda s: s.str.strip())
        .drop_duplicates()
        .sort_values(["año", "eleccion_tipo", "recuento_tipo", "padron_tipo"])
    )

    have = dim[["año", "eleccion_tipo", "recuento_tipo", "padron_tipo"]].astype("string")
    missing = need.merge(
        have.assign(_have=1),
        on=["año", "eleccion_tipo", "recuento_tipo", "padron_tipo"],
        how="left"
    )
    missing = missing.loc[missing["_have"].isna(), ["año","eleccion_tipo","recuento_tipo","padron_tipo"]]

    if missing.empty:
        # nothing to do
        return dim

    # Assign deterministic next ids.
    # Current max (numeric if possible, else fall back to count)
    try:
        cur = pd.to_numeric(dim["eleccion_id"], errors="coerce")
        start = int(cur.max()) if cur.notna().any() else 0
    except Exception:
        start = dim.shape[0]

    missing = missing.sort_values(["año","eleccion_tipo","recuento_tipo","padron_tipo"]).reset_index(drop=True)
    missing["eleccion_id"] = (missing.index + 1 + start).astype(str)

    new_dim = pd.concat([dim, missing], ignore_index=True)
    new_dim = new_dim[["año","eleccion_tipo","recuento_tipo","padron_tipo","eleccion_id"]]
    new_dim = new_dim.drop_duplicates().reset_index(drop=True)

    # Write back atomically
    tmp = elec_path.with_suffix(".tmp.csv")
    new_dim.to_csv(tmp, index=False)
    tmp.replace(elec_path)

    print(f"[dims] eleccion_dim.csv updated: +{len(missing)} rows")
    return new_dim

# --------------------------
# Main build
# --------------------------

def main(args):
    cfg = load_yaml(args.config)
    staging_dir = Path(cfg.get("staging_dir", "canon/staging"))
    schema_dir = Path(cfg.get("schema_dir", "canon/bd/schema"))
    bd_csv_dir = Path(cfg.get("bd_csv_dir", "canon/bd/csv"))  # output dim path

    in_norm = staging_dir / "all_normalized.csv"
    if not in_norm.exists():
        raise FileNotFoundError(f"Missing input: {in_norm}")

    df = pd.read_csv(in_norm, dtype="object")

    # Make sure eleccion_dim is finalized if needed
    eleccion_dim = finalize_eleccion_dim(df, schema_dir)

    # -------- eleccion_table --------
    eleccion_table = (
        df[["eleccion_id", "año", "eleccion_tipo", "recuento_tipo", "padron_tipo"]]
        .drop_duplicates()
        .sort_values(["eleccion_id"])
        .reset_index(drop=True)
    )
    out = bd_csv_dir / "eleccion_table.csv"
    ensure_parents(out)
    eleccion_table.to_csv(out, index=False)

    # -------- distrito_table (harmonized) --------
    distrito_dim = apply_name_harmonization(df, ["distrito_id"], "distrito_nombre") \
        .sort_values(["distrito_id"]).reset_index(drop=True)
    distrito_dim.to_csv(bd_csv_dir / "distrito_table.csv", index=False)

    # -------- seccion_table (harmonized) --------
    seccion_dim = apply_name_harmonization(df, ["distrito_id","seccion_id"], "seccion_nombre") \
        .sort_values(["distrito_id","seccion_id"]).reset_index(drop=True)
    seccion_dim.to_csv(bd_csv_dir / "seccion_table.csv", index=False)

    # -------- circuito_table (harmonized) --------
    circuito_cols = ["eleccion_id","distrito_id","seccion_id","seccionprovincial_id","circuito_id"]
    circuito_dim = apply_name_harmonization(df, circuito_cols, "circuito_nombre") \
        .sort_values(circuito_cols).reset_index(drop=True)
    circuito_dim.to_csv(bd_csv_dir / "circuito_table.csv", index=False)

    # -------- mesas_table --------
    mesas_cols = ["eleccion_id","distrito_id","seccion_id","circuito_id","mesa_id","mesa_electores","mesa_tipo"]
    mesas_dim = (
        df[[c for c in mesas_cols if c in df.columns]]
        .drop_duplicates()
        .sort_values(["eleccion_id","distrito_id","seccion_id","circuito_id","mesa_id"])
        .reset_index(drop=True)
    )
    # Light normalization for mesa_tipo values
    if "mesa_tipo" in mesas_dim.columns:
        mesas_dim["mesa_tipo"] = (
            mesas_dim["mesa_tipo"].astype("string").str.strip().str.upper()
            .replace({"NATIVO":"NATIVOS", "EXTRANJERO":"EXTRANJEROS"})
        )
    mesas_dim.to_csv(bd_csv_dir / "mesas_table.csv", index=False)

    # -------- cargo_table (harmonized) --------
    cargo_dim = apply_name_harmonization(df, ["cargo_id"], "cargo_nombre") \
        .sort_values(["cargo_id"]).reset_index(drop=True)
    cargo_dim.to_csv(bd_csv_dir / "cargo_table.csv", index=False)

    # -------- agrupacion_lista_table (lista_dim) --------
    # Grain: (eleccion_id, distrito_id, cargo_id, agrupacion_id, lista_numero?, lista_nombre)
    # Build deterministic surrogate lista_id
    base_cols = ["eleccion_id","distrito_id","cargo_id","agrupacion_id"]
    opt_cols = []
    if "lista_numero" in df.columns: opt_cols.append("lista_numero")
    if "lista_nombre" in df.columns: opt_cols.append("lista_nombre")

    lista_dim = (
        df[base_cols + opt_cols]
        .dropna(subset=["eleccion_id","distrito_id","cargo_id","agrupacion_id"])
        .drop_duplicates()
        .reset_index(drop=True)
    )

    # Fill missing optional fields with empty string for id determinism
    for c in opt_cols:
        lista_dim[c] = lista_dim[c].astype("string").fillna("").str.strip()

    # Deterministic lista_id via md5 over the tuple
    id_parts_cols = base_cols + opt_cols
    lista_dim["lista_id"] = [
        stable_md5_id([lista_dim.at[i, c] for c in id_parts_cols])
        for i in lista_dim.index
    ]

    # Order columns
    ordered = ["lista_id"] + id_parts_cols
    lista_dim = lista_dim[ordered].sort_values(id_parts_cols).reset_index(drop=True)
    lista_dim.to_csv(bd_csv_dir / "agrupacion_lista_table.csv", index=False)

    print(f"[dims] Wrote:")
    print(f"  - {bd_csv_dir/'eleccion_table.csv'} ({len(eleccion_table):,} rows)")
    print(f"  - {bd_csv_dir/'distrito_table.csv'} ({len(distrito_dim):,} rows)")
    print(f"  - {bd_csv_dir/'seccion_table.csv'} ({len(seccion_dim):,} rows)")
    print(f"  - {bd_csv_dir/'circuito_table.csv'} ({len(circuito_dim):,} rows)")
    print(f"  - {bd_csv_dir/'mesas_table.csv'} ({len(mesas_dim):,} rows)")
    print(f"  - {bd_csv_dir/'cargo_table.csv'} ({len(cargo_dim):,} rows)")
    print(f"  - {bd_csv_dir/'agrupacion_lista_table.csv'} ({len(lista_dim):,} rows)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="Path to YAML config (pipelines/00_config.yml)")
    main(ap.parse_args())
