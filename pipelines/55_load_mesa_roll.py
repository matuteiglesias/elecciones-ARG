#!/usr/bin/env python3
# Goal: load AyT mesa counts (2025) and upsert into canonical mesas_table.csv.
# Also persist a mesa_roll.csv (audit trail) and a discrepancies report (AyT - canonical) BEFORE the upsert.
#
# Inputs:
#   - AyT XLS/CSV with columns akin to: DISTRITO, SECCION, CIRCUITO, MESA, CANT_ELECTORES AyT
#   - bd_csv_dir/eleccion_table.csv  (from step 30)
#   - bd_csv_dir/mesas_table.csv     (canonical from step 30)
#
# Outputs:
#   - bd_csv_dir/mesa_roll.csv                 (upsert; PK = keys + roll_source='AyT')
#   - bd_csv_dir/mesa_roll_discrepancias.csv   (delta AyT - canonical; includes missing-on-either-side notes)
#   - bd_csv_dir/mesas_table.csv               (UPDATED canonical: AyT values merged for the target election)
#
# Config (pipelines/00_config.yml):
#   bd_csv_dir: canon/bd/csv
#   ayt_path: "/media/.../00_DINE_Total pais 2025 Final_21-10 (1).xlsx"
#   eleccion_filter:
#     año: "2025"
#     eleccion_tipo: "GENERAL"
#     recuento_tipo: "PROVISORIO"
#     padron_tipo: "NORMAL"
#   ayt_columns_map:
#     distrito_id: "DISTRITO"
#     seccion_id:  "SECCION"
#     circuito_id: "CIRCUITO"
#     mesa_id:     "MESA"
#     n_electores: "CANT_ELECTORES AyT"
#   canonical_mesa_tipo_fill: "NATIVOS"
#
import argparse
from pathlib import Path
import pandas as pd
import yaml

def load_yaml(p):
    with open(p, "r") as f:
        return yaml.safe_load(f)

def read_table(p: Path) -> pd.DataFrame:
    if not p.exists():
        raise FileNotFoundError(f"Missing input: {p}")
    if p.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(p, dtype="object")
    return pd.read_csv(p, dtype="object")

def to_csv_atomic(df: pd.DataFrame, out: Path):
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".tmp.csv")
    df.to_csv(tmp, index=False)
    tmp.replace(out)

def norm_str(s):
    if pd.isna(s): return ""
    return str(s).strip()

def as_str(df: pd.DataFrame, cols):
    for c in cols:
        if c in df.columns:
            df[c] = df[c].astype("string").map(lambda x: norm_str(x))
    return df

def zfill6(s):
    s = norm_str(s)
    return s.zfill(6) if s.isdigit() else s  # pad only numerics

def require_eleccion_id(elec_tbl: pd.DataFrame, flt: dict) -> str:
    req = (
        (elec_tbl["año"           ].astype(str).str.strip() == str(flt["año"]).strip()) &
        (elec_tbl["eleccion_tipo" ].astype(str).str.strip() == str(flt["eleccion_tipo"]).strip()) &
        (elec_tbl["recuento_tipo" ].astype(str).str.strip() == str(flt["recuento_tipo"]).strip()) &
        (elec_tbl["padron_tipo"   ].astype(str).str.strip() == str(flt["padron_tipo"]).strip())
    )
    hit = elec_tbl.loc[req]
    if hit.empty:
        raise ValueError(f"No eleccion_id found for filter: {flt}")
    return norm_str(hit.iloc[0]["eleccion_id"])

def main(args):
    cfg = load_yaml(args.config)
    bd_csv_dir = Path(cfg.get("bd_csv_dir", "canon/bd/csv"))
    ayt_path   = Path(cfg["ayt_path"])
    colmap     = cfg.get("ayt_columns_map", {})
    elec_flt   = cfg.get("eleccion_filter", {})
    mesa_tipo_fill = cfg.get("canonical_mesa_tipo_fill", "NATIVOS")

    # ---- load dims
    eleccion_table = read_table(bd_csv_dir / "eleccion_table.csv")
    mesas_table_path = bd_csv_dir / "mesas_table.csv"
    mesas_table = read_table(mesas_table_path)

    for k in ["año","eleccion_tipo","recuento_tipo","padron_tipo"]:
        if k not in elec_flt:
            raise ValueError(f"eleccion_filter missing key: {k}")
    eleccion_id_target = require_eleccion_id(eleccion_table, elec_flt)

    # ---- load AyT source
    ayt_raw = read_table(ayt_path)

    # map/validate columns
    m_distrito = colmap.get("distrito_id", "DISTRITO")
    m_seccion  = colmap.get("seccion_id",  "SECCION")
    m_circuito = colmap.get("circuito_id", "CIRCUITO")
    m_mesa     = colmap.get("mesa_id",     "MESA")
    m_elect    = colmap.get("n_electores", "CANT_ELECTORES AyT")

    need = [m_distrito, m_seccion, m_circuito, m_mesa, m_elect]
    missing = [c for c in need if c not in ayt_raw.columns]
    if missing:
        raise ValueError(f"AyT file missing expected columns: {missing}")

    ayt = ayt_raw[[m_distrito,m_seccion,m_circuito,m_mesa,m_elect]].copy()
    ayt.columns = ["distrito_id","seccion_id","circuito_id","mesa_id","n_electores"]

    # normalize IDs as strings
    ayt = as_str(ayt, ["distrito_id","seccion_id","circuito_id","mesa_id","n_electores"])
    ayt["circuito_id"] = ayt["circuito_id"].map(lambda s: zfill6(s.replace(" ", "")))
    ayt["_n_elect_num"] = pd.to_numeric(ayt["n_electores"], errors="coerce")
    ayt["eleccion_id"]  = eleccion_id_target
    ayt["roll_source"]  = "AyT"

    # primary keys
    key = ["eleccion_id","distrito_id","seccion_id","circuito_id","mesa_id"]
    pk_roll = key + ["roll_source"]

    # ---- upsert mesa_roll.csv (audit; optional downstream usage)
    mesa_roll_path = bd_csv_dir / "mesa_roll.csv"
    ayt_for_roll = ayt[pk_roll + ["n_electores"]].copy()
    ayt_for_roll["n_electores"] = ayt["_n_elect_num"].round(0).astype("Int64").astype("string")

    if mesa_roll_path.exists():
        cur = read_table(mesa_roll_path)
        cur = as_str(cur, pk_roll + ["n_electores"])
        merged_roll = pd.concat([cur, ayt_for_roll], ignore_index=True)
        merged_roll = merged_roll.drop_duplicates(subset=pk_roll, keep="last")
    else:
        merged_roll = ayt_for_roll
    to_csv_atomic(merged_roll[pk_roll + ["n_electores"]], mesa_roll_path)

    # ---- prepare canonical & discrepancies BEFORE upsert
    mt = mesas_table.copy()
    mt = as_str(mt, key + ["mesa_electores","mesa_tipo"])
    mt["circuito_id"] = mt["circuito_id"].map(zfill6)

    # 2025 slice
    mt_yr   = mt[mt["eleccion_id"] == eleccion_id_target].copy()
    mt_else = mt[mt["eleccion_id"] != eleccion_id_target].copy()

    # left join to compare
    comp = mt_yr.merge(
        ayt[["eleccion_id","distrito_id","seccion_id","circuito_id","mesa_id","n_electores"]],
        on=key, how="outer", indicator=True
    )

    # numeric deltas where both present
    comp["_canon"] = pd.to_numeric(comp["mesa_electores"], errors="coerce")
    comp["_ayt"]   = pd.to_numeric(comp["n_electores"],  errors="coerce")
    both = comp[comp["_merge"] == "both"].copy()
    both["delta"] = both["_ayt"] - both["_canon"]
    both["abs_delta"] = both["delta"].abs().astype("Int64")

    # missing cases
    only_canon = comp[comp["_merge"] == "left_only"].copy()
    only_canon["delta"] = pd.NA
    only_canon["abs_delta"] = pd.NA
    only_canon["_note"] = "missing_in_AyT"

    only_ayt = comp[comp["_merge"] == "right_only"].copy()
    only_ayt["delta"] = pd.NA
    only_ayt["abs_delta"] = pd.NA
    only_ayt["_note"] = "missing_in_canonical"

    discrepancias = pd.concat([
        both[key + ["mesa_electores","n_electores","delta","abs_delta"]].assign(_note="both"),
        only_canon[key + ["mesa_electores","n_electores","delta","abs_delta","_note"]],
        only_ayt[key + ["mesa_electores","n_electores","delta","abs_delta","_note"]],
    ], ignore_index=True).sort_values(by=["_note","abs_delta"], ascending=[True, False], kind="mergesort").reset_index(drop=True)

    discrep_path = bd_csv_dir / "mesa_roll_discrepancias.csv"
    to_csv_atomic(discrepancias, discrep_path)

    # ---- canonical upsert: fold AyT into mesas_table for target election
    # 1) overwrite where both exist
    upd = mt_yr.merge(
        ayt[["eleccion_id","distrito_id","seccion_id","circuito_id","mesa_id","n_electores"]],
        on=key, how="left", validate="m:1", suffixes=("", "_ayt")
    )
    # prefer AyT where present
    has_ayt = upd["n_electores"].notna()
    upd.loc[has_ayt, "mesa_electores"] = pd.to_numeric(upd.loc[has_ayt, "n_electores"], errors="coerce").round(0).astype("Int64").astype("string")
    # fill mesa_tipo for touched rows (and keep existing for untouched)
    upd.loc[has_ayt, "mesa_tipo"] = upd.loc[has_ayt, "mesa_tipo"].mask(upd.loc[has_ayt, "mesa_tipo"].isna() | (upd.loc[has_ayt, "mesa_tipo"]==""), mesa_tipo_fill)
    upd = upd[key + ["mesa_electores","mesa_tipo"]]

    # 2) append AyT-only keys as new canonical rows with mesa_tipo fill
    ayt_only = ayt.merge(mt_yr[key], on=key, how="left", indicator=True)
    ayt_only = ayt_only[ayt_only["_merge"]=="left_only"].copy()
    new_rows = pd.DataFrame(columns=upd.columns)
    if not ayt_only.empty:
        new_rows = ayt_only.copy()
        new_rows["mesa_electores"] = pd.to_numeric(new_rows["n_electores"], errors="coerce").round(0).astype("Int64").astype("string")
        new_rows["mesa_tipo"] = mesa_tipo_fill
        new_rows = new_rows[key + ["mesa_electores","mesa_tipo"]]

    # 3) rebuild canonical for target year
    mt_yr_updated = pd.concat([upd, new_rows], ignore_index=True).drop_duplicates(subset=key, keep="last")
    # 4) splice back with other years
    mesas_table_updated = pd.concat([mt_else, mt_yr_updated], ignore_index=True)
    # 5) write canonical
    to_csv_atomic(mesas_table_updated[["eleccion_id","distrito_id","seccion_id","circuito_id","mesa_id","mesa_electores","mesa_tipo"]], mesas_table_path)

    # ---- done
    print("[mesa-roll] OK")
    print(f"  mesa_roll (audit) → {mesa_roll_path}")
    print(f"  discrepancias (pre-upsert) → {discrep_path}")
    print(f"  mesas_table (canonical, UPDATED) → {mesas_table_path}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="Path to YAML config (pipelines/00_config.yml)")
    main(ap.parse_args())
