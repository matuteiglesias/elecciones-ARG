#!/usr/bin/env python3
# pipelines/20_normalize_core.py
# Purpose: enforce types, normalize IDs, map votos_tipo & cargo, and attach stable eleccion_id.
# Contract: read staging/all_raw.csv → write staging/all_normalized.csv (CSV only)

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import yaml

REQUIRED_KEYS = ["año", "eleccion_tipo", "recuento_tipo", "padron_tipo"]
ID_STR = ["distrito_id", "seccionprovincial_id", "seccion_id", "circuito_id", "mesa_id", "agrupacion_id"]

# --------------------------
# Utilities
# --------------------------

def load_yaml(p):
    with open(p, "r") as f:
        return yaml.safe_load(f)

def ensure_parents(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)

def now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def fail(msg, sample=None, code=1, audit_path: Path=None):
    if sample is not None:
        print(msg, file=sys.stderr)
        print(sample, file=sys.stderr)
    else:
        print(msg, file=sys.stderr)
    # if we have an audit path and sample is a DataFrame, persist it
    if audit_path is not None and hasattr(sample, "to_csv"):
        try:
            ensure_parents(audit_path)
            sample.to_csv(audit_path, index=False)
            print(f"[normalize] Wrote audit: {audit_path}", file=sys.stderr)
        except Exception as e:
            print(f"[normalize] Failed to write audit {audit_path}: {e}", file=sys.stderr)
    sys.exit(code)

def norm_key(s):
    if pd.isna(s):
        return pd.NA
    return str(s).strip().upper()

def normalize_agrupacion_id(x):
    if pd.isna(x):
        return pd.NA
    s = str(x).strip()
    # If purely numeric (even like "3.0"), left-pad to 6
    try:
        if s.replace(".", "", 1).isdigit():
            return str(int(float(s))).zfill(6)
    except Exception:
        pass
    return s  # preserve alphanumeric / non-numeric as-is

def read_csv_safe(p: Path) -> pd.DataFrame:
    return pd.read_csv(p, dtype="object")

# --------------------------
# Fallback loaders
# --------------------------

def load_votos_tipo_map(schema_dir: Path) -> dict:
    vt_path = schema_dir / "votos_tipo_map.json"
    if not vt_path.exists():
        fail(f"[normalize] Missing schema file: {vt_path}")
    with open(vt_path, "r") as f:
        vt_map_raw = json.load(f)
    # build normalized-key dict to allow sloppy source strings
    vt_map = {norm_key(k): v for k, v in vt_map_raw.items()}
    # canonical range = set(vt_map_raw.values())
    canon = set(vt_map_raw.values())
    return vt_map, canon

def load_cargo_map(schema_dir: Path, bd_csv_dir: Path | None) -> pd.DataFrame:
    """
    Preferred: schema_dir/cargo_map.csv (name→id).
    Fallback (if enabled and available): bd_csv_dir/cargo_table.csv (id + canonical name) → derive map.
    """
    cargo_path = schema_dir / "cargo_map.csv"
    if cargo_path.exists():
        cargo_map = read_csv_safe(cargo_path)
        for col in ["cargo_id", "cargo_nombre"]:
            if col not in cargo_map.columns:
                fail(f"[normalize] cargo_map.csv must include cargo_id,cargo_nombre. Found: {cargo_map.columns.tolist()}")
        cargo_map["_cargo_nombre_key"] = cargo_map["cargo_nombre"].map(norm_key)
        return cargo_map[["_cargo_nombre_key", "cargo_id"]]

    # fallback: derive from cargo_table.csv if present
    if bd_csv_dir is not None:
        table = bd_csv_dir / "cargo_table.csv"
        if table.exists():
            dim = read_csv_safe(table)
            # expect at minimum cargo_id, cargo_nombre
            need_cols = {"cargo_id", "cargo_nombre"}
            if not need_cols.issubset(dim.columns):
                fail(f"[normalize] cargo_table.csv present but missing columns {need_cols}. Found: {dim.columns.tolist()}")
            # choose a single canonical name per cargo_id (if duplicates)
            dim = dim[["cargo_id", "cargo_nombre"]].dropna().drop_duplicates()
            # map by name→id using normalized name key
            dim["_cargo_nombre_key"] = dim["cargo_nombre"].map(norm_key)
            dim = dim.drop_duplicates(subset=["_cargo_nombre_key"])  # in case multiple ids share a name, keep first
            return dim[["_cargo_nombre_key", "cargo_id"]]

    fail("[normalize] Missing cargo_map.csv and no usable cargo_table.csv fallback.")
    return pd.DataFrame(columns=["_cargo_nombre_key", "cargo_id"])  # unreachable

def load_or_finalize_eleccion_dim(df: pd.DataFrame, schema_dir: Path, allow_autofinalize: bool) -> pd.DataFrame:
    """
    Load eleccion_dim.csv. If missing tuples and allow_autofinalize=True,
    append deterministically (same policy as 30_build_dims).
    """
    elec_dim_path = schema_dir / "eleccion_dim.csv"
    if not elec_dim_path.exists():
        fail(f"[normalize] Missing schema file: {elec_dim_path} (maintain this as contract)")

    dim = read_csv_safe(elec_dim_path)
    for c in ["año", "eleccion_tipo", "recuento_tipo", "padron_tipo", "eleccion_id"]:
        if c not in dim.columns:
            fail("[normalize] eleccion_dim.csv must include: año, eleccion_tipo, recuento_tipo, padron_tipo, eleccion_id.")

    # normalize join keys (strings trimmed)
    for col in ["año", "eleccion_tipo", "recuento_tipo", "padron_tipo"]:
        dim[col] = dim[col].astype("string").str.strip()

    needed = (
        df[["año", "eleccion_tipo", "recuento_tipo", "padron_tipo"]]
        .astype("string").apply(lambda s: s.str.strip())
        .drop_duplicates()
        .sort_values(["año", "eleccion_tipo", "recuento_tipo", "padron_tipo"])
    )
    have = dim[["año", "eleccion_tipo", "recuento_tipo", "padron_tipo"]].assign(_have=1)
    chk = needed.merge(have, on=["año","eleccion_tipo","recuento_tipo","padron_tipo"], how="left")
    missing = chk.loc[chk["_have"].isna(), ["año","eleccion_tipo","recuento_tipo","padron_tipo"]]

    if missing.empty:
        return dim

    if not allow_autofinalize:
        audit = missing.head(200)
        audit_path = schema_dir / "audits" / f"missing_eleccion_tuples_{now_tag()}.csv"
        fail(
            "[normalize] Found election tuples not present in eleccion_dim.csv. Do NOT invent IDs.\n"
            "→ Run 30_build_dims.py to finalize, or set allow_autofinalize_eleccion_dim: true.",
            sample=audit, audit_path=audit_path
        )

    # deterministic append
    try:
        cur = pd.to_numeric(dim["eleccion_id"], errors="coerce")
        start = int(cur.max()) if cur.notna().any() else 0
    except Exception:
        start = dim.shape[0]
    missing = missing.sort_values(["año","eleccion_tipo","recuento_tipo","padron_tipo"]).reset_index(drop=True)
    missing["eleccion_id"] = (missing.index + 1 + start).astype(str)

    new_dim = pd.concat([dim, missing], ignore_index=True)
    new_dim = new_dim[["año","eleccion_tipo","recuento_tipo","padron_tipo","eleccion_id"]].drop_duplicates().reset_index(drop=True)

    # Write back atomically
    tmp = elec_dim_path.with_suffix(".tmp.csv")
    ensure_parents(tmp)
    new_dim.to_csv(tmp, index=False)
    tmp.replace(elec_dim_path)
    print(f"[normalize] eleccion_dim.csv autofinalized: +{len(missing)} rows")

    return new_dim

# --------------------------
# Main
# --------------------------

def main(args):
    cfg = load_yaml(args.config)

    # Dirs
    staging_dir  = Path(cfg.get("staging_dir", "canon/staging"))
    schema_dir   = Path(cfg.get("schema_dir", "canon/schema"))
    bd_csv_dir   = Path(cfg.get("bd_csv_dir")) if cfg.get("bd_csv_dir") else None
    audits_dir   = Path(cfg.get("audits_dir", staging_dir / "audits"))

    # Behavior flags
    strict_circuito_numeric          = bool(cfg.get("strict_circuito_numeric", False))
    allow_autofinalize_eleccion_dim  = bool(cfg.get("allow_autofinalize_eleccion_dim", False))
    enforce_votos_tipo_domain        = bool(cfg.get("enforce_votos_tipo_domain", True))

    out_csv = staging_dir / "all_normalized.csv"
    in_raw  = staging_dir / "all_raw.csv"
    if not in_raw.exists():
        fail(f"[normalize] Missing input: {in_raw}")

    # ---------- load ----------
    df = read_csv_safe(in_raw)  # keep strings; coerce selectively

    # ---------- basic column guards ----------
    missing_req = [c for c in REQUIRED_KEYS if c not in df.columns]
    if missing_req:
        fail(f"[normalize] Missing required cols {missing_req} in {in_raw}")

    # ---------- ID casts (strings) ----------
    for c in ID_STR:
        if c in df.columns:
            df[c] = df[c].astype("string")

    # circuito_id handling
    if "circuito_id" in df.columns:
        s = df["circuito_id"].astype("string").str.strip()
        if strict_circuito_numeric:
            non_num = s.notna() & ~s.str.fullmatch(r"\d+")
            if non_num.any():
                audit = df.loc[non_num, ["circuito_id"]].drop_duplicates().head(200)
                fail("[normalize] circuito_id contains non-numeric values",
                     sample=audit,
                     audit_path=(audits_dir / f"bad_circuito_non_numeric_{now_tag()}.csv"))
            df["circuito_id"] = s.str.zfill(6)
        else:
            # len==6 invariant only; allow alphanumerics (pad only if numeric)
            df["circuito_id"] = s.where(~s.str.fullmatch(r"\d+"),
                                        s.str.zfill(6))

    # agrupacion_id normalization
    if "agrupacion_id" in df.columns:
        df["agrupacion_id"] = df["agrupacion_id"].map(normalize_agrupacion_id).astype("string")

    # ---------- votos_tipo mapping ----------
    vt_map, vt_canon = load_votos_tipo_map(schema_dir)
    if "votos_tipo" not in df.columns:
        fail("[normalize] Missing column votos_tipo in input")

    src_keys = pd.Series(df["votos_tipo"].dropna().unique(), dtype="object")
    unmapped = sorted(set(norm_key(x) for x in src_keys.tolist()) - set(vt_map.keys()))
    if unmapped:
        sample_list = unmapped[:200]
        audit = pd.DataFrame({"unmapped_votos_tipo": sample_list})
        fail("[normalize] Unmapped votos_tipo keys found. Update votos_tipo_map.json.",
             sample=audit,
             audit_path=(audits_dir / f"unmapped_votos_tipo_{now_tag()}.csv"))

    df["votos_tipo"] = df["votos_tipo"].map(lambda x: vt_map.get(norm_key(x), pd.NA))
    if enforce_votos_tipo_domain:
        bad_domain = ~df["votos_tipo"].isin(list(vt_canon))
        if bad_domain.any():
            audit = df.loc[bad_domain, ["votos_tipo"]].value_counts().reset_index()
            audit.columns = ["votos_tipo","count"]
            fail("[normalize] votos_tipo outside canonical domain", sample=audit.head(200),
                 audit_path=(audits_dir / f"bad_votos_tipo_domain_{now_tag()}.csv"))

    # ---------- cargo mapping (name→id), with fallback to cargo_table ----------
    cargo_map = load_cargo_map(schema_dir, bd_csv_dir)
    need_merge = ("cargo_id" not in df.columns) or df["cargo_id"].isna().any()
    if need_merge:
        if "cargo_nombre" not in df.columns:
            fail("[normalize] Need cargo mapping but cargo_nombre not present in input")
        df["_cargo_nombre_key"] = df["cargo_nombre"].map(norm_key)
        before_rows = len(df)
        df = df.merge(cargo_map, on="_cargo_nombre_key", how="left", validate="m:1")
        assert len(df) == before_rows, "[normalize] cargo merge changed row count (bug)"
        # fill cargo_id if originally present but nulls existed
        if "cargo_id" not in df.columns:
            df.rename(columns={"cargo_id_y": "cargo_id"}, inplace=True, errors="ignore")
        # check NAs
        if df["cargo_id"].isna().any():
            bad = df.loc[df["cargo_id"].isna(), ["cargo_nombre"]].drop_duplicates()
            fail("[normalize] Unmapped cargo_nombre → cargo_id. Add to cargo_map.csv (or cargo_table).",
                 sample=bad.head(200),
                 audit_path=(audits_dir / f"unmapped_cargo_{now_tag()}.csv"))
        df.drop(columns=["_cargo_nombre_key"], errors="ignore", inplace=True)

    # ---------- stable eleccion_id via eleccion_dim.csv ----------
    # Try to auto-finalize if configured; else fail strictly
    elec_dim = load_or_finalize_eleccion_dim(df, schema_dir, allow_autofinalize_eleccion_dim)

    # attach id
    for col in ["año", "eleccion_tipo", "recuento_tipo", "padron_tipo"]:
        df[col] = df[col].astype("string").str.strip()
        elec_dim[col] = elec_dim[col].astype("string").str.strip()

    before = len(df)
    df = df.merge(
        elec_dim[["año","eleccion_tipo","recuento_tipo","padron_tipo","eleccion_id"]],
        on=["año","eleccion_tipo","recuento_tipo","padron_tipo"],
        how="left",
        validate="m:1"
    )
    assert len(df) == before, "[normalize] eleccion join changed row count (bug)"
    if df["eleccion_id"].isna().any():
        fail("[normalize] eleccion_id join produced NA after finalize/presence check.")

    # ---------- write ----------
    ensure_parents(out_csv)
    tmp = out_csv.with_suffix(".tmp.csv")
    df.to_csv(tmp, index=False)
    tmp.replace(out_csv)
    print(f"[normalize] OK → {out_csv}")

    # ---------- invariants ----------
    if "circuito_id" in df.columns:
        bad_len = df["circuito_id"].dropna().map(len).ne(6).sum()
        if bad_len:
            fail(f"[normalize] Post-write invariant failed: circuito_id length != 6 in {bad_len} rows")
    if "agrupacion_id" in df.columns and df["agrupacion_id"].dtype.name != "string":
        fail("[normalize] agrupacion_id is not string dtype after normalization")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="Path to YAML config (pipelines/00_config.yml)")
    main(ap.parse_args())
