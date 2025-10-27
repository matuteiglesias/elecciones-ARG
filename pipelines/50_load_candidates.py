#!/usr/bin/env python3
# Goal: ingest candidate slates (2025+) into person-centric tables that join to lista/agrupacion/cargo/distrito.
# Inputs:
#   - raw candidate file: Excel/CSV (columns like Posicion, Nombres, Apellido, Candidatura, DNI, Genero, Fecha Nacimiento, Twitter, Facebook, Instagram, WEB, YouTube, otra_red, plus optional: distrito_nombre, cargo_nombre, agrupacion_nombre, lista_numero/lista_nombre, titularidad)
#   - dims from step 30: eleccion_table.csv, distrito_table.csv, cargo_table.csv, agrupacion_lista_table.csv
#   - optional: agrupacion_crosswalk.csv (maps source agrupacion/lista names to IDs)
#
# Outputs:
#   - canon/bd/csv/persona_dim.csv              (upsert)
#   - canon/bd/csv/persona_social_dim.csv       (upsert)
#   - canon/bd/csv/candidatura_fact.csv         (new or upsert by natural key)
#   - canon/bd/csv/agrupacion_lista_table.csv   (upsert if new lists appear)
#
# Config (pipelines/00_config.yml):
#   staging_dir: canon/staging
#   schema_dir:  canon/schema
#   bd_csv_dir:  canon/bd/csv
#   candidates_path: "path/to/2025 Candidaturas ... .xlsx"
#   eleccion_filter:
#     año: "2025"
#     eleccion_tipo: "GENERAL"        # or "PASO"
#     recuento_tipo: "PROVISORIO"     # match your eleccion_table
#     padron_tipo: "NORMAL"
#   # optional mapping of source columns to expected semantics
#   columns_map:
#     posicion: "Posicion"
#     nombres: "Nombres"
#     apellido: "Apellido"
#     candidatura_text: "Candidatura"
#     dni: "DNI"
#     genero: "Genero"
#     fecha_nac: "Fecha Nacimiento"
#     twitter: "Twitter"
#     facebook: "Facebook"
#     instagram: "Instagram"
#     web: "WEB"
#     youtube: "YouTube"
#     otra_red: "otra_red"
#     distrito_nombre: "distrito_nombre"      # if present in file
#     cargo_nombre: "cargo_nombre"            # if present in file
#     agrupacion_nombre: "agrupacion_nombre"  # if present in file
#     lista_numero: "lista_numero"            # if present in file
#     lista_nombre: "lista_nombre"            # if present in file
#     titularidad: "Titularidad"              # if present in file; else fallback rule below
#   suplentes_from_position: null             # e.g., 11 -> >=11 are SUPLENTE; null = default all TITULAR
#   agrupacion_crosswalk_path: ""            # optional csv with columns: source_agrupacion, agrupacion_id, [lista_numero, lista_nombre]
#
# Grain & rules:
#   - persona_id: "DNI:<dni>" if clean dni present, else md5 of (nombres, apellido, fecha_nac, genero)
#   - titularidad ∈ {"TITULAR","SUPLENTE"} (map/normalize; default TITULAR unless rule/column provided)
#   - candidatura_fact natural key:
#       (eleccion_id,distrito_id,cargo_id,agrupacion_id,lista_id,titularidad,posicion,persona_id)
#     Uniqueness enforced; duplicates fail.
#   - lista_id: stable md5 over (eleccion_id,distrito_id,cargo_id,agrupacion_id,lista_numero?,lista_nombre?) — consistent with step 30.
#
import argparse
import hashlib
import sys
from pathlib import Path

import pandas as pd
import yaml

def load_yaml(p): 
    with open(p, "r") as f: 
        return yaml.safe_load(f)

def ensure_parents(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)

def read_table(p: Path) -> pd.DataFrame:
    if not p.exists():
        raise FileNotFoundError(f"Missing input: {p}")
    if p.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(p, dtype="object")
    return pd.read_csv(p, dtype="object")

def to_csv_atomic(df: pd.DataFrame, out: Path):
    ensure_parents(out)
    tmp = out.with_suffix(".tmp.csv")
    df.to_csv(tmp, index=False)
    tmp.replace(out)

def norm(s):
    if pd.isna(s): return ""
    return str(s).strip()

def norm_upper(s):
    return norm(s).upper()

def stable_md5(parts) -> str:
    key = "|".join("" if p is None else str(p) for p in parts)
    return hashlib.md5(key.encode("utf-8")).hexdigest()

def mk_persona_id(dni, nombres, apellido, fecha_nac, genero):
    dni = norm(dni)
    if dni and dni.isdigit():
        return f"DNI:{dni}"
    # fallback hash
    return "PX:"+stable_md5([norm_upper(nombres), norm_upper(apellido), norm(fecha_nac), norm_upper(genero)])

def normalize_titularidad(x):
    t = norm_upper(x)
    if t in {"TITULAR", "SUPLENTE"}: return t
    # Map common variants
    if t in {"TIT", "TITU"}: return "TITULAR"
    if t in {"SUP", "SUPL"}: return "SUPLENTE"
    return ""  # unknown -> handle via default later

PLATFORM_MAP = {
    "twitter": "TWITTER",
    "facebook": "FACEBOOK",
    "instagram": "INSTAGRAM",
    "web": "WEB",
    "youtube": "YOUTUBE",
    "otra_red": "OTRA",
}

def split_socials(row, cols_map):
    out = []
    for src_col, plat in PLATFORM_MAP.items():
        col = cols_map.get(src_col, "")
        if not col or col not in row.index: 
            continue
        val = norm(row[col])
        if not val:
            continue
        # cheap parse: strip leading @ and whitespace
        handle = val.lstrip("@").strip()
        out.append({"platform": plat, "handle_or_url": handle, "raw": val})
    return out

def left_join(df_left, df_right, on, right_cols, err_if_missing=False, err_label=""):
    merged = df_left.merge(df_right[on+right_cols], on=on, how="left", validate="m:1")
    if err_if_missing:
        miss = merged[right_cols].isna().any(axis=1)
        if miss.any():
            sample = merged.loc[miss, on].drop_duplicates().head(20)
            raise ValueError(f"Unmapped keys in {err_label}: \n{sample.to_string(index=False)}")
    return merged

def main(args):
    cfg = load_yaml(args.config)
    staging_dir = Path(cfg.get("staging_dir", "canon/staging"))
    bd_csv_dir  = Path(cfg.get("bd_csv_dir", "canon/bd/csv"))
    bd_schema_dir  = Path(cfg.get("bd_schema_dir", "canon/schema"))

    cand_path   = Path(cfg["candidates_path"])
    cols_map    = cfg.get("columns_map", {})
    supl_cut    = cfg.get("suplentes_from_position", None)

    elec_filter = cfg.get("eleccion_filter", {})
    eleccion_table = read_table(bd_csv_dir / "eleccion_table.csv")  # step 30 output
    eleccion_table_ = read_table(bd_schema_dir / "eleccion_dim.csv")  # step 30 output
    eleccion_table = pd.concat([eleccion_table, eleccion_table_]).drop_duplicates()

    # 20,2025,GENERAL,PROVISORIO,NORMAL


    # find eleccion_id by tuple
    for k in ["año","eleccion_tipo","recuento_tipo","padron_tipo"]:
        if k not in elec_filter:
            raise ValueError(f"eleccion_filter missing key: {k}")
    row = eleccion_table.loc[
        (eleccion_table["año"].astype(str).str.strip()==str(elec_filter["año"]).strip()) &
        (eleccion_table["eleccion_tipo"].astype(str).str.strip()==str(elec_filter["eleccion_tipo"]).strip()) &
        (eleccion_table["recuento_tipo"].astype(str).str.strip()==str(elec_filter["recuento_tipo"]).strip()) &
        (eleccion_table["padron_tipo"].astype(str).str.strip()==str(elec_filter["padron_tipo"]).strip())
    ]
    if row.empty:
        raise ValueError(f"No eleccion_id found for {elec_filter}")
    eleccion_id = norm(row.iloc[0]["eleccion_id"])

    # other dims
    distrito_table = read_table(bd_csv_dir / "distrito_table.csv")
    cargo_table    = read_table(bd_csv_dir / "cargo_table.csv")
    lista_dim      = read_table(bd_csv_dir / "agrupacion_lista_table.csv")

    # optional agrupacion crosswalk (source name -> agrupacion_id and optionally lista info)
    agr_x_path = cfg.get("agrupacion_crosswalk_path", "")
    agr_x = None
    if agr_x_path:
        ax = Path(agr_x_path)
        if ax.exists():
            agr_x = read_table(ax)

    # ---- read candidates file
    raw = read_table(cand_path)

    # rename expected columns if present
    def col(name): 
        # return the physical column name from mapping if exists and present, else the logical itself
        phys = cols_map.get(name, name)
        return phys if phys in raw.columns else name

    # minimal required columns for a row
    need = [col("Posicion") if "Posicion" in raw.columns else cols_map.get("posicion","Posicion"),
            cols_map.get("nombres","Nombres"),
            cols_map.get("apellido","Apellido")]
    miss = [c for c in need if c not in raw.columns]
    if miss:
        raise ValueError(f"Missing required source columns: {miss}")

    # project to working set (don’t fail if optional are absent)
    keep = set([
        cols_map.get("posicion","Posicion"),
        cols_map.get("nombres","Nombres"),
        cols_map.get("apellido","Apellido"),
        cols_map.get("candidatura_text","Candidatura"),
        cols_map.get("dni","DNI"),
        cols_map.get("genero","Genero"),
        cols_map.get("fecha_nac","Fecha Nacimiento"),
        cols_map.get("twitter","Twitter"),
        cols_map.get("facebook","Facebook"),
        cols_map.get("instagram","Instagram"),
        cols_map.get("web","WEB"),
        cols_map.get("youtube","YouTube"),
        cols_map.get("otra_red","otra_red"),
        cols_map.get("distrito_nombre","distrito_nombre"),
        cols_map.get("cargo_nombre","cargo_nombre"),
        cols_map.get("agrupacion_nombre","agrupacion_nombre"),
        cols_map.get("lista_numero","lista_numero"),
        cols_map.get("lista_nombre","lista_nombre"),
        cols_map.get("titularidad","Titularidad"),
    ])
    keep = [c for c in keep if c in raw.columns]
    df = raw[keep].copy()

    # normalize basics
    df["posicion"]   = pd.to_numeric(df[cols_map.get("posicion","Posicion")], errors="coerce")
    df["nombres"]    = df[cols_map.get("nombres","Nombres")].astype("string").str.strip()
    df["apellido"]   = df[cols_map.get("apellido","Apellido")].astype("string").str.strip()
    if cols_map.get("dni","DNI") in df.columns:
        df["dni"]    = df[cols_map.get("dni","DNI")].astype("string").str.replace(r"\D+","", regex=True).str.strip()
    else:
        df["dni"]    = ""
    df["genero"]     = (df[cols_map.get("genero","Genero")] if cols_map.get("genero","Genero") in df.columns else "").astype("string")
    df["fecha_nac"]  = (df[cols_map.get("fecha_nac","Fecha Nacimiento")] if cols_map.get("fecha_nac","Fecha Nacimiento") in df.columns else "").astype("string")

    # titularidad
    if cols_map.get("titularidad","Titularidad") in df.columns:
        df["titularidad"] = df[cols_map.get("titularidad","Titularidad")].map(normalize_titularidad)
    else:
        df["titularidad"] = ""  # will fill below
    # default TITULAR unless configured cut-off
    if supl_cut is None:
        df.loc[df["titularidad"]=="", "titularidad"] = "TITULAR"
    else:
        df.loc[df["titularidad"]=="", "titularidad"] = df["posicion"].apply(lambda p: "SUPLENTE" if (pd.notna(p) and supl_cut and int(p)>=int(supl_cut)) else "TITULAR")

    # persona_id
    df["persona_id"] = [
        mk_persona_id(df.at[i,"dni"], df.at[i,"nombres"], df.at[i,"apellido"], df.at[i,"fecha_nac"], df.at[i,"genero"])
        for i in df.index
    ]

    # --- distrito/cargo/agrupacion/lista mapping
    # distrito_id via distrito_table if a distrito name is present; else leave null (you can fill by context if file is per distrito)
    if cols_map.get("distrito_nombre","distrito_nombre") in df.columns:
        dkey = "distrito_nombre"
        dt = distrito_table.rename(columns={"distrito_nombre": dkey})
        dt[dkey] = dt[dkey].astype("string").str.strip()
        df[dkey] = df[dkey].astype("string").str.strip()
        df = left_join(df, dt, on=[dkey], right_cols=["distrito_id"], err_if_missing=True, err_label="distrito_nombre→distrito_id")
    else:
        df["distrito_id"] = pd.NA

    # cargo_id via cargo_table by name if present
    if cols_map.get("cargo_nombre","cargo_nombre") in df.columns:
        ckey = "cargo_nombre"
        ct = cargo_table.rename(columns={"cargo_nombre": ckey})
        ct[ckey] = ct[ckey].astype("string").str.strip()
        df[ckey] = df[ckey].astype("string").str.strip()
        df = left_join(df, ct, on=[ckey], right_cols=["cargo_id"], err_if_missing=True, err_label="cargo_nombre→cargo_id")
    else:
        df["cargo_id"] = pd.NA

    # agrupacion/lista:
    # preferred: use existing lista_dim (agrupacion_lista_table) if (eleccion_id,distrito_id,cargo_id,agrupacion_id,lista_*) exists
    # otherwise: use crosswalk; otherwise: invent combo & upsert deterministically
    lista_dim = lista_dim.copy()
    need_cols = {"eleccion_id","distrito_id","cargo_id","agrupacion_id"}
    if not need_cols.issubset(set(lista_dim.columns)):
        raise ValueError(f"agrupacion_lista_table.csv missing required cols: {need_cols}")

    # bring optional lista fields from source if present
    has_ln = cols_map.get("lista_numero","lista_numero") in df.columns
    has_lname = cols_map.get("lista_nombre","lista_nombre") in df.columns
    if has_ln:    df["lista_numero"] = df[cols_map.get("lista_numero","lista_numero")].astype("string").fillna("").str.strip()
    else:         df["lista_numero"] = ""
    if has_lname: df["lista_nombre"] = df[cols_map.get("lista_nombre","lista_nombre")].astype("string").fillna("").str.strip()
    else:         df["lista_nombre"] = ""

    # agrupacion_id: try crosswalk by source agrupacion name, else require it's already in lista_dim rows for this election/distrito/cargo
    if cols_map.get("agrupacion_nombre","agrupacion_nombre") in df.columns:
        df["agrupacion_nombre"] = df[cols_map.get("agrupacion_nombre","agrupacion_nombre")].astype("string").str.strip()
    else:
        df["agrupacion_nombre"] = ""

    if agr_x is not None and "agrupacion_nombre" in df.columns and "source_agrupacion" in agr_x.columns and "agrupacion_id" in agr_x.columns:
        ax = agr_x.rename(columns={"source_agrupacion":"agrupacion_nombre"})
        df = df.merge(ax[["agrupacion_nombre","agrupacion_id"]].drop_duplicates(), on="agrupacion_nombre", how="left")
    else:
        # try to infer agrupacion_id from existing lista_dim by matching lista_numero/lista_nombre within the election/distrito/cargo
        key_cols = ["eleccion_id","distrito_id","cargo_id"]
        lista_dim["lista_numero"] = lista_dim.get("lista_numero","").astype("string").fillna("").str.strip()
        lista_dim["lista_nombre"] = lista_dim.get("lista_nombre","").astype("string").fillna("").str.strip()
        # left join on the tightest available
        join_keys = key_cols + (["lista_numero"] if has_ln else []) + (["lista_nombre"] if has_lname else [])
        tmp = df.assign(eleccion_id=eleccion_id)
        df = tmp.merge(lista_dim[join_keys+["agrupacion_id","lista_id"]].drop_duplicates(),
                       on=join_keys, how="left")

    # where agrupacion_id still missing, we’ll create lista rows
    mask_new_list = df["agrupacion_id"].isna()
    if mask_new_list.any():
        # we must have distrito_id and cargo_id to build a valid list key
        missing = df.loc[mask_new_list & (df["distrito_id"].isna() | df["cargo_id"].isna()), 
                         ["distrito_id","cargo_id","agrupacion_nombre","lista_numero","lista_nombre"]]
        if not missing.empty:
            raise ValueError("Cannot create lista without distrito_id and cargo_id. Sample:\n"+missing.head(10).to_string(index=False))
        # derive agrupacion_id deterministically from agrupacion_nombre if present; else fail
        if (df.loc[mask_new_list,"agrupacion_nombre"]=="").any():
            raise ValueError("agrupacion_id unknown and agrupacion_nombre absent; cannot upsert lista deterministically.")
        # Here you can plug a maintained agrupacion dimension; as a starter, hash the agrupacion name (scoped to election)
        df.loc[mask_new_list, "agrupacion_id"] = [
            "AGR:"+stable_md5([eleccion_id, df.at[i,"agrupacion_nombre"]]) for i in df.loc[mask_new_list].index
        ]

    # ensure lista_id present: compute for rows without one
    need_id = df["lista_id"].isna() if "lista_id" in df.columns else pd.Series(True, index=df.index)
    if need_id.any():
        def compute_lista_id(i):
            return stable_md5([
                eleccion_id,
                df.at[i,"distrito_id"],
                df.at[i,"cargo_id"],
                df.at[i,"agrupacion_id"],
                df.at[i,"lista_numero"],
                df.at[i,"lista_nombre"],
            ])
        df.loc[need_id, "lista_id"] = [compute_lista_id(i) for i in df.loc[need_id].index]

    # --- build persona_dim (upsert)
    persona_cols = ["persona_id","dni","nombres","apellido","genero","fecha_nac"]
    persona_dim_path = bd_csv_dir / "persona_dim.csv"
    if persona_dim_path.exists():
        persona_dim = read_table(persona_dim_path)
        if "persona_id" not in persona_dim.columns:
            raise ValueError("persona_dim.csv must include persona_id")
        # upsert: prefer existing non-empty values; else take new
        newp = df[persona_cols].drop_duplicates("persona_id")
        persona_dim = newp.set_index("persona_id").combine_first(persona_dim.set_index("persona_id")).reset_index()
    else:
        persona_dim = df[persona_cols].drop_duplicates("persona_id").reset_index(drop=True)
    to_csv_atomic(persona_dim, persona_dim_path)

    # --- build persona_social_dim (long) upsert by (persona_id, platform, handle_or_url)
    rows = []
    for i, r in df.iterrows():
        socials = split_socials(r, cols_map)
        for s in socials:
            rows.append({"persona_id": r["persona_id"], **s})
    social_long = pd.DataFrame(rows, columns=["persona_id","platform","handle_or_url","raw"]).drop_duplicates()
    social_path = bd_csv_dir / "persona_social_dim.csv"
    if social_path.exists():
        old = read_table(social_path)
        social_long = pd.concat([old, social_long], ignore_index=True).drop_duplicates()
    to_csv_atomic(social_long, social_path)

    # --- upsert lista_dim (agrupacion_lista_table.csv)
    lista_dim_path = bd_csv_dir / "agrupacion_lista_table.csv"
    # prepare new rows
    new_lista = (
        df.assign(eleccion_id=eleccion_id)[
            ["lista_id","eleccion_id","distrito_id","cargo_id","agrupacion_id","lista_numero","lista_nombre"]
        ].drop_duplicates()
    )
    # merge/upsert by lista_id
    if lista_dim_path.exists():
        current = read_table(lista_dim_path)
        # combine_first on lista_id to avoid clobbering existing values
        merged = new_lista.set_index("lista_id").combine_first(current.set_index("lista_id")).reset_index()
        to_csv_atomic(merged[["lista_id","eleccion_id","distrito_id","cargo_id","agrupacion_id","lista_numero","lista_nombre"]], lista_dim_path)
    else:
        to_csv_atomic(new_lista, lista_dim_path)

    # --- build candidatura_fact
    # natural key: (eleccion_id,distrito_id,cargo_id,agrupacion_id,lista_id,titularidad,posicion,persona_id)
    cf = df.assign(eleccion_id=eleccion_id)[
        ["eleccion_id","distrito_id","cargo_id","agrupacion_id","lista_id","titularidad","posicion","persona_id"]
    ].copy()
    # Checks
    if cf.isna().any().any():
        na_cols = cf.columns[cf.isna().any()].tolist()
        raise ValueError(f"Nulls in candidatura_fact columns: {na_cols}")
    # uniqueness
    dup = cf.duplicated(subset=["eleccion_id","distrito_id","cargo_id","agrupacion_id","lista_id","titularidad","posicion","persona_id"], keep=False)
    if dup.any():
        sample = cf.loc[dup].head(20).to_string(index=False)
        raise ValueError("[candidatura] Duplicate rows at grain; fix upstream.\n"+sample)

    cf_path = bd_csv_dir / "candidatura_fact.csv"
    if cf_path.exists():
        old = read_table(cf_path)
        # upsert by the natural key
        key = ["eleccion_id","distrito_id","cargo_id","agrupacion_id","lista_id","titularidad","posicion","persona_id"]
        merged = pd.concat([old, cf], ignore_index=True).drop_duplicates(subset=key, keep="last")
        to_csv_atomic(merged[key], cf_path)
    else:
        to_csv_atomic(cf, cf_path)

    print("[candidatos] OK")
    print(f"  eleccion_id: {eleccion_id}")
    print(f"  persona_dim → {persona_dim_path}")
    print(f"  persona_social_dim → {social_path}")
    print(f"  candidatura_fact → {cf_path}")
    print(f"  agrugacion/lista upsert → {lista_dim_path}")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="Path to YAML config (pipelines/00_config.yml)")
    main(ap.parse_args())
