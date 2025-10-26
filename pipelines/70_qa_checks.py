#!/usr/bin/env python3
# QA trip-wire: fail fast on silent data problems.
# Inputs (expected in bd_csv_dir):
#   - eleccion_table.csv  (from 30)
#   - mesas_resolved.csv  (preferred, from 55) OR mesas_table.csv (fallback)
#   - votos_fact.csv      (from 40)
#   - distrito_table.csv, seccion_table.csv, circuito_table.csv (from 30) [for parent-child]
#   - persona_dim.csv, candidatura_fact.csv (from 50)  [optional]
# Outputs:
#   - exports/qa/report.json
#   - exports/qa/report.txt
#   - exports/qa/*.csv with offenders for quick triage
#
import argparse, json, sys, os
from pathlib import Path
import pandas as pd
import yaml
from hashlib import md5
from datetime import datetime

OK, WARN, FAIL = "OK", "WARN", "FAIL"

def load_yaml(p):
    with open(p, "r") as f:
        return yaml.safe_load(f)

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def read_csv(p: Path, required=True):
    if not p.exists():
        if required:
            raise FileNotFoundError(f"Missing required: {p}")
        return None
    return pd.read_csv(p, dtype="object")

def prefer_resolved_mesas(bd_csv_dir: Path):
    p_res = bd_csv_dir / "mesas_resolved.csv"
    p_tab = bd_csv_dir / "mesas_table.csv"
    src = p_res if p_res.exists() else p_tab
    df = read_csv(src)
    # normalize common fields
    for c in ["eleccion_id","distrito_id","seccion_id","circuito_id","mesa_id","mesa_electores","mesa_tipo"]:
        if c in df.columns:
            df[c] = df[c].astype("string").str.strip()
    if "circuito_id" in df.columns:
        df["circuito_id"] = df["circuito_id"].map(lambda s: s if pd.isna(s) or not str(s).isdigit() else str(s).zfill(6))
    # legacy rename
    if "mesa_electores_resolved" in df.columns and "mesa_electores" not in df.columns:
        df = df.rename(columns={"mesa_electores_resolved": "mesa_electores"})
    return df, src.name

def pct(n, d):
    if d == 0: return 100.0
    return 100.0 * n / d

def head_sorted(df, n=10):
    return df.sort_values(list(df.columns), ascending=True).head(n)

def write_small_csv(df, path: Path, n=2000):
    if df is None or df.empty:
        return
    ensure_dir(path.parent)
    df.head(n).to_csv(path, index=False)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="Path to YAML config (pipelines/00_config.yml)")
    args = ap.parse_args()

    cfg = load_yaml(args.config)
    bd_csv_dir = Path(cfg.get("bd_csv_dir", "canon/bd/csv"))
    exports_dir = Path(cfg.get("exports_dir", "exports/out"))
    qa_dir = Path("exports/qa")
    ensure_dir(qa_dir)

    report = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "status": OK,
        "checks": [],
        "notes": [],
    }
    failures = 0
    warnings = 0

    # Load inputs
    elec = read_csv(bd_csv_dir / "eleccion_table.csv")
    mesas, mesas_src = prefer_resolved_mesas(bd_csv_dir)
    votos = read_csv(bd_csv_dir / "votos_fact.csv")
    persona = read_csv(bd_csv_dir / "persona_dim.csv", required=False)
    cand = read_csv(bd_csv_dir / "candidatura_fact.csv", required=False)

    # Parent tables for R3
    distrito = read_csv(bd_csv_dir / "distrito_table.csv")
    seccion = read_csv(bd_csv_dir / "seccion_table.csv")
    circuito = read_csv(bd_csv_dir / "circuito_table.csv")

    # Common keys / grain
    KEY_MESA = ["eleccion_id","distrito_id","seccion_id","circuito_id","mesa_id"]
    FACT_GRAIN = KEY_MESA + ["cargo_id","agrupacion_id","lista_numero","votos_tipo"]

    # --- Check: Elección completeness ----------------------------------------------------------
    facts_eids = set(votos["eleccion_id"].dropna().unique().tolist())
    table_eids = set(elec["eleccion_id"].dropna().unique().tolist())
    missing_eids = sorted(list(facts_eids - table_eids))
    st = FAIL if missing_eids else OK
    failures += (st == FAIL)
    report["checks"].append({
        "name": "eleccion_completeness",
        "status": st,
        "details": {"missing_in_eleccion_table": missing_eids}
    })

    # --- R6: ID shape checks (all strings; circuito_id len==6) --------------------------------
    st_id = OK
    detail = {}
    # dtype checks on MESAS (authoritative for IDs)
    for col in ["eleccion_id","distrito_id","seccion_id","circuito_id","mesa_id"]:
        if col in mesas.columns and mesas[col].dtype.name not in ("object","string"):
            st_id = FAIL
            detail["bad_dtype_"+col] = str(mesas[col].dtype)
    if "circuito_id" in mesas.columns:
        bad_len = mesas["circuito_id"].dropna().map(len).ne(6).sum()
        if bad_len:
            st_id = FAIL
            detail["circuito_id_bad_len_rows"] = int(bad_len)
    failures += (st_id == FAIL)
    report["checks"].append({"name":"id_shape_checks", "status": st_id, "details": detail})

    # --- Non-negativity (votes and electors) ---------------------------------------------------
    st_nonneg = OK
    neg_cols = []
    if "votos_cantidad" in votos.columns:
        vneg = pd.to_numeric(votos["votos_cantidad"], errors="coerce")
        if (vneg < 0).any():
            st_nonneg = FAIL
            neg_cols.append("votos_cantidad")
    if "mesa_electores" in mesas.columns:
        eneg = pd.to_numeric(mesas["mesa_electores"], errors="coerce")
        if (eneg < 0).any():
            st_nonneg = FAIL
            neg_cols.append("mesa_electores")
    failures += (st_nonneg == FAIL)
    report["checks"].append({"name":"non_negativity", "status": st_nonneg, "details":{"negative_columns":neg_cols}})

    # --- R1: Orphan facts (facts without mesa) -------------------------------------------------
    votos_keys = votos[KEY_MESA].drop_duplicates()
    mesas_keys = mesas[KEY_MESA].drop_duplicates()
    orphan = (
        votos_keys.merge(mesas_keys.assign(_hit=1), on=KEY_MESA, how="left")
        .loc[lambda d: d["_hit"].isna(), KEY_MESA]
    )
    st_orphan = FAIL if not orphan.empty else OK
    failures += (st_orphan == FAIL)
    write_small_csv(orphan, qa_dir / "orphan_facts.csv")
    # per election counts
    orphan_counts = orphan.groupby("eleccion_id").size().reset_index(name="rows").to_dict(orient="records")
    report["checks"].append({"name":"R1_orphan_facts", "status": st_orphan,
                             "details":{"rows": int(orphan.shape[0]), "by_eleccion_id": orphan_counts}})

    # --- R2: Duplicate facts at grain ----------------------------------------------------------
    dup_mask = votos.duplicated(FACT_GRAIN, keep=False)
    dup_rows = votos.loc[dup_mask, FACT_GRAIN + ["votos_cantidad"]]
    st_dup = FAIL if not dup_rows.empty else OK
    failures += (st_dup == FAIL)
    write_small_csv(dup_rows, qa_dir / "duplicate_facts_at_grain.csv")
    report["checks"].append({"name":"R2_duplicate_facts_at_grain",
                             "status": st_dup, "details":{"rows": int(dup_rows.shape[0])}})

    # --- R3: Parent–child integrity (circuito→seccion→distrito) -------------------------------
    # normalize ID fields
    for df in (distrito, seccion, circuito):
        for c in ["distrito_id","seccion_id","circuito_id"]:
            if c in df.columns:
                df[c] = df[c].astype("string").str.strip()

    # seccion parent distrito
    sec_bad = seccion.merge(distrito[["distrito_id"]].assign(_ok=1),
                            on="distrito_id", how="left")
    sec_bad = sec_bad[sec_bad["_ok"].isna()][["distrito_id","seccion_id"]]
    # circuito parent seccion
    circ_bad = circuito.merge(seccion[["distrito_id","seccion_id"]].assign(_ok=1),
                              on=["distrito_id","seccion_id"], how="left")
    circ_bad = circ_bad[circ_bad["_ok"].isna()][["distrito_id","seccion_id","circuito_id"]]

    st_pc = FAIL if (not sec_bad.empty or not circ_bad.empty) else OK
    failures += (st_pc == FAIL)
    write_small_csv(sec_bad, qa_dir / "parent_missing_seccion_vs_distrito.csv")
    write_small_csv(circ_bad, qa_dir / "parent_missing_circuito_vs_seccion.csv")
    report["checks"].append({"name":"R3_parent_child_integrity", "status": st_pc,
                             "details":{"seccion_missing_parent_rows": int(sec_bad.shape[0]),
                                        "circuito_missing_parent_rows": int(circ_bad.shape[0])}})

    # --- R4: Coverage: share of MESAS with any votos rows -------------------------------------
    mesas_hit = mesas_keys.merge(votos_keys.assign(_hit=1), on=KEY_MESA, how="left")
    mesas_covered_pct_overall = pct(mesas_hit["_hit"].notna().sum(), mesas_hit.shape[0])
    # by election
    cov_mesas_by_eid = (
        mesas_hit.groupby("eleccion_id")["_hit"]
        .apply(lambda s: pct(s.notna().sum(), s.shape[0]))
        .reset_index(name="coverage_pct")
        .to_dict(orient="records")
    )
    # This is informational; failing here is often too strict. Mark WARN if <98.
    st_cov_mesas = OK if (mesas_covered_pct_overall >= 98.0 and all(d["coverage_pct"] >= 98.0 for d in cov_mesas_by_eid)) else WARN
    warnings += (st_cov_mesas == WARN)
    report["checks"].append({"name":"R4_coverage_mesas_with_votes",
                             "status": st_cov_mesas,
                             "details":{"overall_pct": round(mesas_covered_pct_overall,2),
                                        "by_eleccion_id": cov_mesas_by_eid}})

    # --- R5: POS conservation mismatches by level (mesa, circuito, distrito) ------------------
    POS_BUCKETS = {"POSITIVO","BLANCO","NULO","IMPUGNADO","RECURRIDO"}
    vc = votos.copy()
    vc["votos_cantidad"] = pd.to_numeric(vc["votos_cantidad"], errors="coerce").fillna(0)
    issues_by_level = []
    # policy: lists are authoritative; vendor aggregate POSITIVO rows (agrupacion_id is null) are QA-only
    tol_abs = float(cfg.get("qa_tol_pos_delta_abs", 3.0))
    levels = {
        "mesa": KEY_MESA,
        "circuito": ["eleccion_id","cargo_id","distrito_id","seccion_id","circuito_id"],
        "distrito": ["eleccion_id","cargo_id","distrito_id"]
    }
    for lvl_name, base in levels.items():
        dets = {}
        # list vs total POSITIVO
        if "agrupacion_id" in vc.columns:
            pos_list = vc[(vc["votos_tipo"]=="POSITIVO") & (vc["agrupacion_id"].notna())].groupby(base)["votos_cantidad"].sum()
            pos_total = vc[(vc["votos_tipo"]=="POSITIVO") & (vc["agrupacion_id"].isna())].groupby(base)["votos_cantidad"].sum()
            comp = pos_total.to_frame("pos_total").join(pos_list.to_frame("pos_list"), how="outer").fillna(0.0)
            comp["delta_pos"] = comp["pos_total"] - comp["pos_list"]
            bad = comp[comp["delta_pos"].abs() > tol_abs].reset_index()
            dets["POS_list_vs_total_mismatch_rows"] = int(bad.shape[0])
            write_small_csv(bad.assign(level=lvl_name), qa_dir / f"pos_list_vs_total_mismatch_{lvl_name}.csv")
        # bucket conservation (sum buckets >= sum POSITIVO)
        vtb = vc[vc["votos_tipo"].isin(POS_BUCKETS)]
        tot = vtb.groupby(base)["votos_cantidad"].sum().rename("sum_buckets")
        pos = vc[vc["votos_tipo"]=="POSITIVO"].groupby(base)["votos_cantidad"].sum().rename("sum_positivo")
        chk = tot.to_frame().join(pos, how="left").fillna(0.0)
        bad2 = chk[chk["sum_buckets"] + 1e-9 < chk["sum_positivo"]].reset_index()
        dets["bucket_less_than_positivo_rows"] = int(bad2.shape[0])
        write_small_csv(bad2.assign(level=lvl_name), qa_dir / f"bucket_less_than_positivo_{lvl_name}.csv")
        issues_by_level.append({"level": lvl_name, **dets})
    # classify: WARN if any issues; FAIL if egregious (configurable threshold)
    total_bad = sum(d["POS_list_vs_total_mismatch_rows"] + d["bucket_less_than_positivo_rows"] for d in issues_by_level)
    st_cons = OK if total_bad == 0 else WARN
    warnings += (st_cons == WARN)
    report["checks"].append({"name":"R5_vote_conservation", "status": st_cons, "details": issues_by_level})

    # --- Coverage votos->mesas (your original strict 98% join) --------------------------------
    joined = votos_keys.merge(mesas_keys.assign(_hit=1), on=KEY_MESA, how="left")
    coverage = (1.0 - joined["_hit"].isna().mean()) * 100.0
    cov_by_eid = (
        votos_keys.assign(_one=1)
        .merge(mesas_keys.assign(_hit=1), on=KEY_MESA, how="left")
        .groupby("eleccion_id")["_hit"]
        .apply(lambda s: pct(s.notna().sum(), s.shape[0]))
        .reset_index(name="coverage_pct")
        .to_dict(orient="records")
    )
    st_cov = OK if coverage >= 98.0 and all(d["coverage_pct"] >= 98.0 for d in cov_by_eid) else FAIL
    failures += (st_cov == FAIL)
    report["checks"].append({
        "name":"coverage_votos_to_mesas",
        "status": st_cov,
        "details": {"overall_pct": round(coverage,2), "by_eleccion_id": cov_by_eid, "mesas_source": mesas_src}
    })

    # --- Candidates (existing logic) -----------------------------------------------------------
    if cand is not None and not cand.empty:
        base = ["eleccion_id","distrito_id","cargo_id","agrupacion_id","lista_id","titularidad"]
        dup = cand.duplicated(subset=base+["posicion","persona_id"], keep=False)
        st_dup_c = OK if not dup.any() else FAIL
        failures += (st_dup_c == FAIL)
        report["checks"].append({"name":"candidatos_duplicates", "status": st_dup_c,
                                 "details":{"duplicate_rows": int(dup.sum())}})
        cand["posicion_num"] = pd.to_numeric(cand["posicion"], errors="coerce")
        gap_issues = 0
        for key, grp in cand.groupby(base):
            s = sorted([int(x) for x in grp["posicion_num"].dropna().unique()])
            if not s: continue
            expected = list(range(1, max(s)+1))
            if s != expected:
                gap_issues += 1
        st_cont = OK if gap_issues == 0 else WARN
        report["checks"].append({"name":"candidatos_position_continuity", "status": st_cont,
                                 "details":{"groups_with_gaps": gap_issues}})
        warnings += (st_cont == WARN)
    else:
        report["checks"].append({"name":"candidatos_checks", "status": WARN,
                                 "details":"candidatura_fact.csv/persona_dim.csv missing or empty"})
        warnings += 1

    # --- R7: New unknown keys since last baseline (votos_tipo, cargo_id) ----------------------
    baseline_path = qa_dir / "last_keys.json"
    current_keys = {
        "votos_tipo": sorted([x for x in votos["votos_tipo"].dropna().unique()]),
        "cargo_id":   sorted([x for x in votos["cargo_id"].dropna().unique()]),
    }
    if baseline_path.exists():
        with open(baseline_path, "r") as f:
            prev = json.load(f)
        new_vt = sorted(list(set(current_keys["votos_tipo"]) - set(prev.get("votos_tipo", []))))
        new_cargo = sorted(list(set(current_keys["cargo_id"]) - set(prev.get("cargo_id", []))))
        st_new = OK if (not new_vt and not new_cargo) else WARN
        warnings += (st_new == WARN)
        report["checks"].append({"name":"R7_new_unknown_keys",
                                 "status": st_new,
                                 "details":{"new_votos_tipo": new_vt, "new_cargo_id": new_cargo}})
    else:
        # No baseline yet: write one; OK status with note
        report["notes"].append("Initialized baseline keys at exports/qa/last_keys.json")
        report["checks"].append({"name":"R7_new_unknown_keys",
                                 "status": OK,
                                 "details":"baseline initialized; no diff computed"})

    # Refresh baseline every run (so next run diffs from this)
    with open(baseline_path, "w") as f:
        json.dump(current_keys, f, ensure_ascii=False, indent=2)

    # --- Write report & decide exit code ------------------------------------------------------
    out_json = qa_dir / "report.json"
    out_txt  = qa_dir / "report.txt"
    ensure_dir(out_json.parent)
    report["status"] = FAIL if failures else (WARN if warnings else OK)
    with open(out_json, "w") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(out_txt, "w") as f:
        f.write(f"[QA] status={report['status']} failures={failures} warnings={warnings}\n")
        for c in report["checks"]:
            f.write(f"- {c['name']}: {c['status']}\n")

    if failures:
        print(f"[QA] FAIL ({failures} failing checks). See {out_json}", file=sys.stderr)
        sys.exit(2)
    elif warnings:
        print(f"[QA] WARN ({warnings} warnings). See {out_json}")
    else:
        print("[QA] OK")

if __name__ == "__main__":
    main()
