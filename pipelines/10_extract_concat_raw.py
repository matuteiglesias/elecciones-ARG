import argparse, glob, os, pandas as pd

def run(cfg):
    files = sorted(glob.glob(cfg["raw_glob"], recursive=True))
    assert files, "No raw CSVs found"
    os.makedirs(cfg["staging_dir"], exist_ok=True)

    parts = []
    for f in files:
        df = pd.read_csv(f)
        df.columns = [c.strip().lower() for c in df.columns]
        df["source_file"] = os.path.relpath(f)
        parts.append(df)

    out = pd.concat(parts, ignore_index=True)
    out.to_csv(f'{cfg["staging_dir"]}/all_raw.csv', index=False)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    import yaml; cfg = yaml.safe_load(open(args.config))
    run(cfg)
