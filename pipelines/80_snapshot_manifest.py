#!/usr/bin/env python3
# Snapshot manifest: what was built, from what, and with which warnings.
# Output:
#   snapshots/<YYYYMMDD-HHMM>/MANIFEST.json
#
import argparse, json, os
from pathlib import Path
from datetime import datetime
from hashlib import md5
import pandas as pd
import yaml

def load_yaml(p):
    with open(p, "r") as f:
        return yaml.safe_load(f)

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def file_md5(path: Path, chunk=1<<20):
    h = md5()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b: break
            h.update(b)
    return h.hexdigest()

def csv_rows(path: Path):
    try:
        # cheap/fast row count without loading everything in memory
        with open(path, "rb") as f:
            return sum(1 for _ in f) - 1  # minus header
    except Exception:
        # fallback
        try:
            return int(pd.read_csv(path).shape[0])
        except Exception:
            return None

def harvest_csvs(root: Path, rels: list[str]):
    out = []
    for rel in rels:
        p = root / rel
        if p.exists():
            out.append(p)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="Path to YAML config (pipelines/00_config.yml)")
    args = ap.parse_args()

    cfg = load_yaml(args.config)
    staging_dir = Path(cfg.get("staging_dir", "canon/staging"))
    bd_csv_dir  = Path(cfg.get("bd_csv_dir",  "canon/bd/csv"))
    exports_dir = Path(cfg.get("exports_dir", "exports/out"))

    # destination snapshot dir
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    snap_dir = Path("snapshots") / stamp
    ensure_dir(snap_dir)

    # pull QA report if present
    qa_json = Path("exports/qa/report.json")
    qa_payload = None
    if qa_json.exists():
        qa_payload = json.loads(qa_json.read_text(encoding="utf-8"))

    # manifest skeleton
    manifest = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "config": {"staging_dir": str(staging_dir), "bd_csv_dir": str(bd_csv_dir), "exports_dir": str(exports_dir)},
        "qa": qa_payload if qa_payload else {"status":"UNKNOWN"},
        "inputs": {},
        "tables": {},
        "exports": {},
    }

    # Inputs (from staging manifest if present)
    stage_manifest = staging_dir / "manifest.csv"
    if stage_manifest.exists():
        try:
            dfm = pd.read_csv(stage_manifest, dtype="object")
            # normalize headers if needed
            cols = [c.strip() for c in dfm.columns]
            dfm.columns = cols
            manifest["inputs"]["staging_manifest_rows"] = int(dfm.shape[0])
            # summary by source_sha256
            byhash = (dfm.groupby("source_sha256")["rows_out"]
                      .apply(lambda s: sum(int(x) for x in s.dropna()))
                      .reset_index(name="rows_out_sum"))
            manifest["inputs"]["by_sha256"] = byhash.to_dict(orient="records")
        except Exception as e:
            manifest["inputs"]["error"] = f"failed to parse staging manifest: {e}"

    # Tables of interest (row counts + md5)
    table_files = [
        "eleccion_table.csv",
        "distrito_table.csv",
        "seccion_table.csv",
        "circuito_table.csv",
        "mesas_table.csv",
        "agrupacion_lista_table.csv",
        "cargo_table.csv",
        "persona_dim.csv",
        "persona_social_dim.csv",
        "candidatura_fact.csv",
        "votos_fact.csv",
        "mesa_roll.csv",
        "mesas_resolved.csv",
    ]
    for rel in table_files:
        p = bd_csv_dir / rel
        if p.exists():
            manifest["tables"][rel] = {
                "rows": csv_rows(p),
                "md5": file_md5(p),
                "size_bytes": os.path.getsize(p)
            }

    # Exports (EDA CSVs)
    export_files = [
        "n_electores_dpto.csv",
        "n_electores_circ.csv",
        "votos_tipo_mesa.csv",
        "votos_tipo_circ.csv",
        "votos_tipo_dpto.csv",
    ]
    for rel in export_files:
        p = exports_dir / rel
        if p.exists():
            manifest["exports"][rel] = {
                "rows": csv_rows(p),
                "md5": file_md5(p),
                "size_bytes": os.path.getsize(p)
            }

    # Write manifest
    out = snap_dir / "MANIFEST.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[snapshot] Wrote {out}")

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
# Snapshot manifest: what was built, from what, and with which warnings.
# Output:
#   snapshots/<YYYYMMDD-HHMM>/MANIFEST.json
#
import argparse, json, os
from pathlib import Path
from datetime import datetime
from hashlib import md5
import pandas as pd
import yaml

def load_yaml(p):
    with open(p, "r") as f:
        return yaml.safe_load(f)

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def file_md5(path: Path, chunk=1<<20):
    h = md5()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b: break
            h.update(b)
    return h.hexdigest()

def csv_rows(path: Path):
    try:
        # cheap/fast row count without loading everything in memory
        with open(path, "rb") as f:
            return sum(1 for _ in f) - 1  # minus header
    except Exception:
        # fallback
        try:
            return int(pd.read_csv(path).shape[0])
        except Exception:
            return None

def harvest_csvs(root: Path, rels: list[str]):
    out = []
    for rel in rels:
        p = root / rel
        if p.exists():
            out.append(p)
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="Path to YAML config (pipelines/00_config.yml)")
    args = ap.parse_args()

    cfg = load_yaml(args.config)
    staging_dir = Path(cfg.get("staging_dir", "canon/staging"))
    bd_csv_dir  = Path(cfg.get("bd_csv_dir",  "canon/bd/csv"))
    exports_dir = Path(cfg.get("exports_dir", "exports/out"))

    # destination snapshot dir
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    snap_dir = Path("snapshots") / stamp
    ensure_dir(snap_dir)

    # pull QA report if present
    qa_json = Path("exports/qa/report.json")
    qa_payload = None
    if qa_json.exists():
        qa_payload = json.loads(qa_json.read_text(encoding="utf-8"))

    # manifest skeleton
    manifest = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "config": {"staging_dir": str(staging_dir), "bd_csv_dir": str(bd_csv_dir), "exports_dir": str(exports_dir)},
        "qa": qa_payload if qa_payload else {"status":"UNKNOWN"},
        "inputs": {},
        "tables": {},
        "exports": {},
    }

    # Inputs (from staging manifest if present)
    stage_manifest = staging_dir / "manifest.csv"
    if stage_manifest.exists():
        try:
            dfm = pd.read_csv(stage_manifest, dtype="object")
            # normalize headers if needed
            cols = [c.strip() for c in dfm.columns]
            dfm.columns = cols
            manifest["inputs"]["staging_manifest_rows"] = int(dfm.shape[0])
            # summary by source_sha256
            byhash = (dfm.groupby("source_sha256")["rows_out"]
                      .apply(lambda s: sum(int(x) for x in s.dropna()))
                      .reset_index(name="rows_out_sum"))
            manifest["inputs"]["by_sha256"] = byhash.to_dict(orient="records")
        except Exception as e:
            manifest["inputs"]["error"] = f"failed to parse staging manifest: {e}"

    # Tables of interest (row counts + md5)
    table_files = [
        "eleccion_table.csv",
        "distrito_table.csv",
        "seccion_table.csv",
        "circuito_table.csv",
        "mesas_table.csv",
        "agrupacion_lista_table.csv",
        "cargo_table.csv",
        "persona_dim.csv",
        "persona_social_dim.csv",
        "candidatura_fact.csv",
        "votos_fact.csv",
        "mesa_roll.csv",
        "mesas_resolved.csv",
    ]
    for rel in table_files:
        p = bd_csv_dir / rel
        if p.exists():
            manifest["tables"][rel] = {
                "rows": csv_rows(p),
                "md5": file_md5(p),
                "size_bytes": os.path.getsize(p)
            }

    # Exports (EDA CSVs)
    export_files = [
        "n_electores_dpto.csv",
        "n_electores_circ.csv",
        "votos_tipo_mesa.csv",
        "votos_tipo_circ.csv",
        "votos_tipo_dpto.csv",
    ]
    for rel in export_files:
        p = exports_dir / rel
        if p.exists():
            manifest["exports"][rel] = {
                "rows": csv_rows(p),
                "md5": file_md5(p),
                "size_bytes": os.path.getsize(p)
            }

    # Write manifest
    out = snap_dir / "MANIFEST.json"
    out.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[snapshot] Wrote {out}")

if __name__ == "__main__":
    main()
