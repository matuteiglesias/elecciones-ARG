#!/usr/bin/env python3
# Goal: produce EDA-ready aggregates from resolved mesas and long votos fact.
# Inputs:
#   - bd_csv_dir/votos_fact.csv              (from step 40)
#   - bd_csv_dir/mesas_resolved.csv          (preferred, if present)
#     OR bd_csv_dir/mesas_table.csv          (fallback canonical; updated by step 55)
#
# Outputs (CSV):
#   - exports/out/n_electores_dpto.csv   (sum electores, nunique(mesa_id))
#   - exports/out/n_electores_circ.csv   (sum electores, nunique(mesa_id))
#   - exports/out/votos_tipo_mesa.csv    (sum votos_cantidad @ mesa grain)
#   - exports/out/votos_tipo_circ.csv    (sum votos_cantidad @ circuito grain)
#   - exports/out/votos_tipo_dpto.csv    (sum votos_cantidad @ departamento/sección grain)
#
# Rules:
#   - Deduplicate the mesa grain first, then aggregate.
#   - Never use `size` as mesa count — always `nunique(mesa_id)`.
#
import argparse
from pathlib import Path
import pandas as pd
import yaml

def load_yaml(p):
    with open(p, "r") as f:
        return yaml.safe_load(f)

def ensure_parents(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)

def read_csv(p: Path) -> pd.DataFrame:
    if not p.exists():
        raise FileNotFoundError(f"Missing input: {p}")
    return pd.read_csv(p, dtype="object")

def write_csv_atomic(df: pd.DataFrame, out: Path):
    ensure_parents(out)
    tmp = out.with_suffix(".tmp.csv")
    df.to_csv(tmp, index=False)
    tmp.replace(out)

def prefer_resolved_mesas(bd_csv_dir: Path) -> pd.DataFrame:
    p_resolved = bd_csv_dir / "mesas_resolved.csv"
    p_canonical = bd_csv_dir / "mesas_table.csv"
    src = p_resolved if p_resolved.exists() else p_canonical
    df = read_csv(src)
    # Normalize expected columns
    if "mesa_electores_resolved" in df.columns:
        # mesas_resolved.csv layout (prefer resolved counts)
        df = df.rename(columns={"mesa_electores_resolved": "mesa_electores"})
    # Keep the common shape
    keep = [c for c in ["eleccion_id","distrito_id","seccion_id","circuito_id","mesa_id","mesa_electores","mesa_tipo"] if c in df.columns]
    df = df[keep].copy()
    # Normalize basics
    for c in ["eleccion_id","distrito_id","seccion_id","circuito_id","mesa_id","mesa_tipo","mesa_electores"]:
        if c in df.columns:
            df[c] = df[c].astype("string").str.strip()
    # circuito_id: zero-pad only if numeric
    if "circuito_id" in df.columns:
        df["circuito_id"] = df["circuito_id"].map(lambda s: s if s is pd.NA or not str(s).isdigit() else str(s).zfill(6))
    # mesa_electores numeric for aggregation
    if "mesa_electores" in df.columns:
        df["_mesa_elect_num"] = pd.to_numeric(df["mesa_electores"], errors="coerce")
    return df

def dedupe_mesas(df_mesas: pd.DataFrame) -> pd.DataFrame:
    """
    Deduplicate to one row per (eleccion_id, distrito_id, seccion_id, circuito_id, mesa_id).
    Elector count rule: first non-null wins (idempotent under canonical inputs).
    """
    key = ["eleccion_id","distrito_id","seccion_id","circuito_id","mesa_id"]
    # Sort so that any non-null mesa_electores appears first (stable if already unique)
    df = df_mesas.copy()
    if "_mesa_elect_num" not in df.columns:
        df["_mesa_elect_num"] = pd.to_numeric(df.get("mesa_electores"), errors="coerce")
    df["_is_null_e"] = df["_mesa_elect_num"].isna()
    df = df.sort_values(key + ["_is_null_e"])  # non-null first
    dedup = df.drop_duplicates(subset=key, keep="first").copy()
    dedup = dedup[key + ["_mesa_elect_num"]].rename(columns={"_mesa_elect_num": "mesa_electores_num"})
    return dedup

def build_n_electores_tables(mesas_dedup: pd.DataFrame, out_dir: Path):
    # Departamento/Sección
    gcols_dpto = ["eleccion_id","distrito_id","seccion_id"]
    dpto = (
        mesas_dedup
        .groupby(gcols_dpto, dropna=False)
        .agg(n_electores=("mesa_electores_num","sum"),
             mesa_count = ("mesa_id","nunique"))  # mesa_id preserved in index during groupby? ensure presence:
        .reset_index()
    )
    # Circuito
    gcols_circ = ["eleccion_id","distrito_id","seccion_id","circuito_id"]
    circ = (
        mesas_dedup
        .groupby(gcols_circ, dropna=False)
        .agg(n_electores=("mesa_electores_num","sum"),
             mesa_count = ("mesa_id","nunique"))
        .reset_index()
    )
    # Write (cast n_electores to Int64->string to match CSV vibe, but leave numeric is fine too)
    for df, name in [(dpto, "n_electores_dpto.csv"), (circ, "n_electores_circ.csv")]:
        df["n_electores"] = pd.to_numeric(df["n_electores"], errors="coerce").round(0).astype("Int64")
        out = out_dir / name
        write_csv_atomic(df, out)

def build_votos_tipo_tables(votos_fact: pd.DataFrame, out_dir: Path):
    # Ensure numeric, normalized IDs
    df = votos_fact.copy()
    df["votos_cantidad"] = pd.to_numeric(df["votos_cantidad"], errors="coerce").fillna(0)

    # Common keys present in facts (defensive picks)
    keys_common = ["eleccion_id","cargo_id","distrito_id","seccionprovincial_id","seccion_id","circuito_id","mesa_id","votos_tipo"]
    present = [k for k in keys_common if k in df.columns]

    # By mesa
    keys_mesa = [k for k in ["eleccion_id","cargo_id","distrito_id","seccionprovincial_id","seccion_id","circuito_id","mesa_id","votos_tipo"] if k in df.columns]
    vt_mesa = df.groupby(keys_mesa, dropna=False)["votos_cantidad"].sum().reset_index()
    write_csv_atomic(vt_mesa, out_dir / "votos_tipo_mesa.csv")

    # By circuito (drop mesa_id)
    keys_circ = [k for k in keys_mesa if k != "mesa_id"]
    vt_circ = df.groupby(keys_circ, dropna=False)["votos_cantidad"].sum().reset_index()
    write_csv_atomic(vt_circ, out_dir / "votos_tipo_circ.csv")

    # By departamento/sección (drop mesa_id, circuito_id)
    keys_dpto = [k for k in keys_circ if k != "circuito_id"]
    vt_dpto = df.groupby(keys_dpto, dropna=False)["votos_cantidad"].sum().reset_index()
    write_csv_atomic(vt_dpto, out_dir / "votos_tipo_dpto.csv")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="Path to YAML config (pipelines/00_config.yml)")
    args = ap.parse_args()

    cfg = load_yaml(args.config)
    bd_csv_dir = Path(cfg.get("bd_csv_dir", "canon/bd/csv"))
    exports_dir = Path(cfg.get("exports_dir", "exports/out"))

    # 1) Source frames
    votos_fact = read_csv(bd_csv_dir / "votos_fact.csv")          # step 40
    mesas_src  = prefer_resolved_mesas(bd_csv_dir)                # step 55 (resolved) or step 30 canonical

    # 2) Deduplicate mesa grain first
    mesas_dedup = dedupe_mesas(mesas_src)

    # 3) n_electores aggregates (sum electores, nunique mesas)
    build_n_electores_tables(mesas_dedup, exports_dir)

    # 4) votos_tipo aggregates
    build_votos_tipo_tables(votos_fact, exports_dir)

    print("[aggregates] OK")
    print(f"  exports → {exports_dir}/(n_electores_*.csv, votos_tipo_*.csv)")

if __name__ == "__main__":
    main()
