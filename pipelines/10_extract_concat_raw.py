#!/usr/bin/env python3
# 10_extract_concat_raw.py — robust CSV ingest, normalization, and provenance (streamed)

import argparse, csv, datetime as dt, glob, hashlib, io, os, re, sys, tempfile
from typing import Dict, List, Optional, Tuple

import pandas as pd
import yaml

# import logging

# # Initialize a logger for this module
# logger = logging.getLogger("extract")
# logger.setLevel(logging.INFO)  # will be overridden by config later
# handler = logging.StreamHandler()
# formatter = logging.Formatter("[%(asctime)s] %(levelname)s - %(message)s",
#                               datefmt="%Y-%m-%d %H:%M:%S")
# handler.setFormatter(formatter)
# logger.addHandler(handler)



from pipelines.utils_logging import get_logger
log = get_logger(__name__)

from pathlib import Path



# ---------- helpers

def sha256_of_file(path: str, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            h.update(chunk)
    return h.hexdigest()

def detect_read_csv_kwargs(path: str, encodings: List[str]) -> Tuple[Dict, str, str]:
    """
    Try encodings in order; use engine='python' with sep=None to sniff delimiter.
    Returns (kwargs, chosen_encoding, dialect_name)
    """
    last_err = None
    for enc in encodings:
        try:
            # Peek first KB to sniff delimiter with csv.Sniffer
            with open(path, "rb") as fb:
                head = fb.read(2048)
            try:
                sample = head.decode(enc, errors="strict")
                dialect = csv.Sniffer().sniff(sample)
                sep = dialect.delimiter
                dialect_name = {",":"comma",";":"semicolon","\t":"tsv"}.get(sep, f"char:{sep}")
            except Exception:
                sep = None  # let pandas sniff
                dialect_name = "auto"

            kwargs = dict(
                sep=sep, engine="python", encoding=enc, dtype="object",
                keep_default_na=False, na_values=[""], quoting=csv.QUOTE_MINIMAL
            )
            # quick parse of a small chunk to validate
            _ = pd.read_csv(path, nrows=50, **kwargs)
            return kwargs, enc, dialect_name
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"Failed to read (encoding/dialect) '{path}': {last_err}")

def atomic_write_csv(df_iter, out_path: str, header: List[str]):
    """Stream DataFrame chunks to a temp file, then atomic replace."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, newline="", encoding="utf-8") as tmp:
        tmp_path = tmp.name
        first = True
        for df in df_iter:
            # enforce column order
            df = df.reindex(columns=header, fill_value="")
            df.to_csv(tmp, index=False, header=first, mode="a", lineterminator="\n")
            first = False
    os.replace(tmp_path, out_path)

def atomic_write_manifest(rows: list[dict], out_path: str):
    out_dir = os.path.dirname(out_path) or "."
    os.makedirs(out_dir, exist_ok=True)

    mdf = pd.DataFrame(rows)

    # temp file next to destination to avoid EXDEV
    with tempfile.NamedTemporaryFile(
        mode="w",
        delete=False,
        dir=out_dir,
        prefix=".manifest.",
        suffix=".tmp",
        encoding="utf-8",
        newline="",
    ) as tmp:
        tmp_path = tmp.name
        mdf.to_csv(tmp, index=False)
        tmp.flush()
        os.fsync(tmp.fileno())

    # atomic swap on the same filesystem
    os.replace(tmp_path, out_path)


def normalize_headers(cols: List[str], alias_map: Dict[str, str]) -> List[str]:
    norm = []
    for c in cols:
        k = c.strip().lower()
        norm.append(alias_map.get(k, k))
    return norm

def path_tuple_from_regex(path: str, regex_specs: List[Dict]) -> Dict[str, str]:
    out = {}
    for spec in regex_specs:
        m = re.search(spec["regex"], path)
        if not m:
            continue
        for k, v in m.groupdict().items():
            out[k] = v
        # value mapping and casting
        mapping = spec.get("map", {})
        for key, rule in mapping.items():
            if key in out:
                if isinstance(rule, dict):
                    out[key] = rule.get(out[key], out[key])
                elif isinstance(rule, str) and rule == "int":
                    out[key] = int(out[key])
        break
    return out

# ---------- core

def run(cfg):
    ingest = cfg.get("ingest", {})
    staging_dir = cfg.get("staging_dir", "canon/staging")
    manifest_cfg = ingest.get("manifest", {"write": True, "out": f"{staging_dir}/manifest.csv"})
    out_csv = os.path.join(staging_dir, "all_raw.csv")
    tmp_csv = os.path.join(staging_dir, "all_raw.tmp.csv")

    # defaults
    sources = ingest.get("sources", [{"pattern": "raw/**/ResultadosElectorales.csv", "kind": "csv"}])
    encodings = [ingest.get("encoding", "utf-8-sig")] + ingest.get("fallback_encodings", ["latin-1"])
    bad_lines = ingest.get("bad_lines", "error")
    on_dup = ingest.get("on_duplicate_files", "keep_first")
    required_min = [c.strip().lower() for c in ingest.get("required_min_columns", ["año","eleccion_tipo","recuento_tipo","padron_tipo"])]
    alias_map = {k.strip().lower(): v.strip().lower() for k, v in ingest.get("header_aliases", {}).items()}
    path_regex_specs = ingest.get("path_regex", [
        {"regex": r".*/ResultadosElectorales_(?P<eleccion_tipo>PASO|General|Ballotage)(?P<año>\d{4}).*",
         "map": {"eleccion_tipo":{"PASO":"PASO","General":"GENERAL","Ballotage":"BALLOTAGE"}, "año":"int"}}
    ])

    # resolve files (CSV only, as requested)
    files = []
    for src in sources:
        if src.get("kind","csv") != "csv":
            continue  # ignore non-CSV as per user request
        files.extend(glob.glob(src["pattern"], recursive=True))
    files = sorted(set(files))
    if not files:
        raise SystemExit("No raw CSVs found for patterns in config.")


    # compute hashes, handle duplicate files by policy
    logger.info("Hashing %d candidate files and applying duplicate policy: %s", len(files), on_dup)


    # >>> ALWAYS-DEFINED TOTALS & SENTINEL
    rows_read_total = 0
    rows_written_total = 0
    current_file = None


    seen_hash: Dict[str, Dict] = {}
    material_files = []
    for f in files[:4]:   ## FAST MODE
        if not os.path.isfile(f):
            logger.debug("Skipping non-file path: %s", f)
            continue
        try:
            h = sha256_of_file(f)
            mtime = os.path.getmtime(f)
            size = os.path.getsize(f)
            rec = {"path": f, "sha256": h, "mtime": mtime, "size": size}
            if h in seen_hash:
                prev = seen_hash[h]
                if on_dup == "keep_first":
                    logger.info("↪︎ Duplicate content (keep_first): keeping %s, skipping %s", prev["path"], f)
                    continue
                elif on_dup == "keep_latest":
                    if mtime > prev["mtime"]:
                        logger.info("↪︎ Duplicate content (keep_latest): replacing %s with newer %s", prev["path"], f)
                        seen_hash[h] = rec
                        material_files = [x for x in material_files if x["path"] != prev["path"]]
                        material_files.append(rec)
                    else:
                        logger.info("↪︎ Duplicate content (keep_latest): keeping %s, skipping older %s", prev["path"], f)
                        continue
                elif on_dup == "error":
                    raise RuntimeError(f"Duplicate file content detected:\n  {prev['path']}\n  {f}")
            else:
                seen_hash[h] = rec
                material_files.append(rec)
                logger.debug("✓ Added file: %s (sha256=%s, size=%d)", f, h[:12], size)
        except Exception as e:
            logger.exception("Error hashing/appraising file %s: %s", f, e)
            raise

    if not material_files:
        logger.error("After duplicate policy, no files remain to ingest.")
        raise SystemExit("After duplicate policy, no files remain to ingest.")

    logger.info("📦 Material files selected: %d", len(material_files))
    for r in material_files:
        logger.debug("  · %s (sha256=%s, mtime=%s, size=%d)",
                    r["path"], r["sha256"][:12], dt.datetime.fromtimestamp(r["mtime"]).isoformat(), r["size"])

    # batch id
    digest = hashlib.sha256((",".join(sorted(r["sha256"] for r in material_files))).encode()).hexdigest()[:12]
    ingest_batch_id = f"{dt.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}_{digest}"
    logger.info("🧾 Ingest batch id: %s (from %d file hashes)", ingest_batch_id, len(material_files))

    # stream processing per file
    manifest_rows = []
    header_union = None
    wrote_header = False

    # prepare output temp file
    os.makedirs(staging_dir, exist_ok=True)
    if os.path.exists(tmp_csv):
        logger.debug("Removing pre-existing temp CSV: %s", tmp_csv)
        os.remove(tmp_csv)

    # Before the per-file loop, assign deterministic short IDs for files:
    for i, rec in enumerate(material_files, start=1):
        # e.g., 4-char prefix from sha + incremental index for readability
        rec["source_id"] = f"{str(rec['sha256'])[:6]}-{i:02d}"

    for rec in material_files:
        fpath = rec["path"]
        sha = rec["sha256"]
        source_id = rec["source_id"]
        logger.info("→ Processing file: %s", fpath)
        election_label = Path(fpath).parent.name

        # set pandas bad_lines policy
        if bad_lines == "error":
            on_bad_lines = "error"
        elif bad_lines == "skip":
            on_bad_lines = "skip"
        else:
            on_bad_lines = "warn"
        logger.debug("  bad_lines policy: %s", on_bad_lines)

        # detect csv kwargs
        try:
            read_kwargs, chosen_enc, dialect_name = detect_read_csv_kwargs(fpath, encodings)
            logger.info("  Reader: encoding=%s, dialect=%s", chosen_enc, dialect_name)
        except Exception as e:
            logger.exception("[ingest] failed dialect/encoding detection for %s: %s", fpath, e)
            raise RuntimeError(f"[ingest] failed dialect/encoding detection for {fpath}: {e}")

        read_kwargs["on_bad_lines"] = on_bad_lines

        # read file in chunks; maintain within-file exact-row de-dup via rolling hash set
        # Build the set once per file
        rowhash_seen: set[int] = set()

        # Decide which columns define an "exact duplicate row".
        # If you want full-row including provenance, put `dedup_cols = list(chunk.columns)`.
        # Usually better: dedupe on data columns only (exclude provenance & the mutable header_union cols).
        rows_in = 0
        rows_out = 0

        # To enforce required_min after aliasing, we must parse first chunk to get columns
        first_chunk = True
        standardized_cols = None
        dedup_cols = standardized_cols  # post-alias, pre-provenance
        tuple_from_path = path_tuple_from_regex(fpath, path_regex_specs)
        if tuple_from_path:
            logger.debug("  tuple_from_path: %s", tuple_from_path)

        try:
            for chunk_idx, chunk in enumerate(pd.read_csv(fpath, chunksize=250_000, **read_kwargs), start=1):


                if chunk_idx % 4 == 0:
                    logging.info("… progress: %s rows read, %s written", rows_read_total, rows_written_total)



                if chunk_idx < 5:  ## FAST MODE

                                        
                    chunk_rows = len(chunk)
                    rows_in += chunk_rows
                    logger.debug("  [chunk %d] read %d rows", chunk_idx, chunk_rows)

                    # normalize headers
                    old_cols = list(chunk.columns)
                    chunk.columns = normalize_headers(old_cols, alias_map)
                    if logger.isEnabledFor(logging.DEBUG) and old_cols != list(chunk.columns):
                        logger.debug("  [chunk %d] header aliasing applied: %s → %s", chunk_idx, old_cols, list(chunk.columns))

                    if first_chunk:
                        missing = [c for c in required_min if c not in chunk.columns]
                        if missing:
                            logger.error("  Missing required columns %s in %s", missing, fpath)
                            raise RuntimeError(f"[ingest] missing required columns {missing} in {fpath}")
                        standardized_cols = list(chunk.columns)
                        first_chunk = False
                        logger.debug("  standardized_cols initialized (%d): %s", len(standardized_cols), standardized_cols)

                    # align columns to first chunk (add missing columns if later chunks shift)
                    added = 0
                    for col in standardized_cols:
                        if col not in chunk.columns:
                            chunk[col] = ""
                            added += 1
                    if added:
                        logger.debug("  [chunk %d] added %d missing standardized cols", chunk_idx, added)

                    extra_cols = [c for c in chunk.columns if c not in standardized_cols]
                    if extra_cols:
                        standardized_cols += [c for c in extra_cols if c not in standardized_cols]
                        logger.info("  [chunk %d] discovered %d new columns → header expanded: %s", chunk_idx, len(extra_cols), extra_cols)

                    # trim whitespace in object-like columns WITHOUT turning NaN into "nan"
                    obj_like = [c for c in chunk.columns if chunk[c].dtype == "object" or pd.api.types.is_string_dtype(chunk[c])]
                    for c in obj_like:
                        chunk[c] = chunk[c].map(lambda x: x.strip() if isinstance(x, str) else x)

                    # optional: cross-check tuple columns vs path-extracted values
                    tuple_mismatch = 0
                    for k, v in tuple_from_path.items():
                        if k in chunk.columns:
                            if len(chunk) > 0 and str(chunk.iloc[0][k]) != str(v):
                                tuple_mismatch = 1
                                logger.debug("  [chunk %d] tuple mismatch for '%s': file='%s' vs path='%s'",
                                            chunk_idx, k, str(chunk.iloc[0][k]), str(v))
                        else:
                            chunk[k] = v
                            logger.debug("  [chunk %d] filled missing tuple column '%s' from path: %s", chunk_idx, k, v)

                    # ---------- DE-DUP (within-file) BEFORE adding provenance ----------
                    # Define which columns to hash:
                    #  - Start from the current data columns
                    #  - Exclude any provenance/system columns by name (even if present from earlier runs)
                    PROVENANCE_COLS = {"source_id", "source_sha256", "source_label", "ingest_batch_id", "source_file"}
                    candidate_cols = [c for c in chunk.columns if c not in PROVENANCE_COLS and c is not None]

                    # If a config-provided dedup_cols exists, intersect it safely; otherwise use all candidate data cols.
                    if 'dedup_cols' in locals() or 'dedup_cols' in globals():
                        # Ensure list, drop None, preserve order & only keep present columns
                        _cfg_cols = [c for c in (dedup_cols or []) if c is not None]
                        effective_dedup_cols = [c for c in _cfg_cols if c in chunk.columns and c not in PROVENANCE_COLS]
                        if not effective_dedup_cols:
                            # fallback to all candidate data cols
                            effective_dedup_cols = candidate_cols
                            logger.warning("  [chunk %d] dedup_cols from config resolved to empty; falling back to all data columns", chunk_idx)
                    else:
                        effective_dedup_cols = candidate_cols

                    # De-duplicate with fast pandas hashing; fall back to row-wise hashing if something odd happens
                    try:
                        hashes = pd.util.hash_pandas_object(chunk[effective_dedup_cols], index=False).astype("uint64").to_numpy()
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug("  [chunk %d] de-dup using %d columns", chunk_idx, len(effective_dedup_cols))
                    except Exception as e_hash:
                        logger.warning("  [chunk %d] fast hash failed (%s); falling back to row-wise hashing", chunk_idx, e_hash)
                        def _row_hash_series(s):
                            return hashlib.md5(("\x1f".join(s.astype(str).tolist())).encode("utf-8")).hexdigest()
                        hashes = chunk[effective_dedup_cols].apply(_row_hash_series, axis=1)

                    # Create keep mask using a rolling set of seen hashes
                    if not isinstance(rowhash_seen, set):
                        rowhash_seen = set()
                    keep_mask = ~pd.Series(hashes).isin(rowhash_seen).to_numpy()
                    dropped = int((~keep_mask).sum())
                    rowhash_seen.update(pd.Series(hashes)[keep_mask].tolist())
                    deduped = chunk.loc[keep_mask]

                    # ---------- NOW add provenance (excluded from de-dup key) ----------
                    deduped["source_id"] = source_id
                    deduped["source_sha256"] = sha
                    deduped["source_label"] = election_label
                    deduped["ingest_batch_id"] = ingest_batch_id

                    # initialize/expand union header
                    if header_union is None:
                        header_union = list(deduped.columns)
                        logger.debug("  header_union initialized with %d columns", len(header_union))
                    else:
                        new_cols = [c for c in deduped.columns if c not in header_union]
                        if new_cols:
                            header_union.extend(new_cols)
                            logger.info("  header_union expanded by %d columns: %s", len(new_cols), new_cols)

                    # append to tmp CSV
                    mode = "a"
                    header = not wrote_header
                    with open(tmp_csv, mode, encoding="utf-8", newline="") as fo:
                        deduped.reindex(columns=header_union, fill_value="").to_csv(
                            fo, index=False, header=header, lineterminator="\n"
                        )
                        wrote_header = True

                    rows_out += len(deduped)
                    if dropped:
                        logger.debug("  [chunk %d] wrote %d rows (dropped %d exact dupes)", chunk_idx, len(deduped), dropped)
                    else:
                        logger.debug("  [chunk %d] wrote %d rows", chunk_idx, len(deduped))

# TODO

# Fix the manifest inflation (per-chunk vs per-file)

# Where you build manifest_rows, ensure you append once per file (outside the chunk loop). If you can’t move it cleanly, guard with a seen set:

#                 seen = set()
# ...
# sha = file_meta["sha256"]
# if sha not in seen:
#     manifest_rows.append(file_meta)
#     seen.add(sha)




                # manifest row per file
                man = {
                    "source_id": source_id,
                    "source_file": os.path.relpath(fpath),
                    "source_sha256": sha,
                    "rows_in": rows_in,
                    "rows_out": rows_out,
                    "rows_dropped_dupe": rows_in - rows_out,
                    "encoding": chosen_enc,
                    "dialect": dialect_name,
                    "tuple_mismatch": tuple_mismatch,
                }
                for k in ["año","eleccion_tipo","recuento_tipo","padron_tipo"]:
                    if k in tuple_from_path:
                        man[k] = tuple_from_path[k]
                manifest_rows.append(man)
                logger.info("✓ File done: %s | in=%d, out=%d, dropped=%d, enc=%s, dialect=%s",
                            fpath, rows_in, rows_out, rows_in - rows_out, chosen_enc, dialect_name)

        except Exception as e:
            logger.exception("[ingest] error while processing %s: %s", fpath, e)
            raise RuntimeError(f"[ingest] error while processing {fpath}: {e}")

    # finalize: atomic replace all_raw.csv and manifest.csv
    os.replace(tmp_csv, out_csv)
    logger.info("💾 Wrote concatenated CSV → %s (header columns: %d)", out_csv, len(header_union) if header_union else 0)

    if manifest_cfg.get("write", True):
        manifest_out = manifest_cfg.get("out", os.path.join(staging_dir, "manifest.csv"))
        atomic_write_manifest(manifest_rows, manifest_out)
        logger.info("🗒️  Wrote manifest → %s (files: %d)", manifest_out, len(manifest_rows))

    print(f"[ingest] OK: {len(material_files)} files → {out_csv}")
    if manifest_cfg.get("write", True):
        print(f"[ingest] manifest: {manifest_out}")



# ---------- CLI
import logging

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="Path to 00_config.yml")
    args = ap.parse_args()
    with open(args.config, "r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)

    # --- apply logging level from config ---
    log_cfg = cfg.get("logging", {})
    level_name = log_cfg.get("level", "INFO").upper()
    logger = get_logger("extract", cfg.get("logging", {}).get("level", "INFO"))

    logger.setLevel(getattr(logging, level_name, logging.INFO))
    logger.info("Logging initialized at level %s", level_name)

    run(cfg)
