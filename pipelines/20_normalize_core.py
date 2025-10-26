import argparse, json, pandas as pd, yaml

ID_STR = ["distrito_id","seccionprovincial_id","seccion_id","circuito_id","mesa_id","agrupacion_id"]

def normalize_agrupacion_id(x):
    if pd.isna(x): return pd.NA
    s = str(x).strip()
    return s if not s.isdigit() else s.zfill(6)

def run(cfg):
    stages = cfg["staging_dir"]
    schema_dir = cfg["schema_dir"]
    df = pd.read_csv(f"{stages}/all_raw.csv")

    # as strings for geo keys
    for c in ID_STR:
        if c in df: df[c] = df[c].astype("string")

    if "circuito_id" in df: df["circuito_id"] = df["circuito_id"].str.strip().str.zfill(6)
    if "agrupacion_id" in df: df["agrupacion_id"] = df["agrupacion_id"].map(normalize_agrupacion_id)

    # votos_tipo map
    vt_map = json.load(open(f"{schema_dir}/votos_tipo_map.json"))
    before = set(df["votos_tipo"].dropna().unique())
    df["votos_tipo"] = df["votos_tipo"].map(vt_map)
    after = set(df["votos_tipo"].dropna().unique())
    unmapped = before - set(vt_map.keys())
    assert not unmapped, f"Unmapped votos_tipo: {sorted(list(unmapped))[:10]}"

    # cargo map
    cargo_map = pd.read_csv(f"{schema_dir}/cargo_map.csv")
    if "cargo_id" not in df or df["cargo_id"].isna().any():
        df = df.merge(cargo_map, on="cargo_nombre", how="left", validate="m:1")
        assert df["cargo_id"].notna().all(), "Unmapped cargo_nombre → cargo_id"

    # stable ele
