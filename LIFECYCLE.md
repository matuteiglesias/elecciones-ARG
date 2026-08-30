# Repository lifecycle

**State:** `active-bounded`  
**Decision date:** 2026-08-26  
**Review cadence:** quarterly  
**Next portfolio review:** November 2026

## Why this state

This repository remains the canonical electoral-data pipeline in the current GitHub estate and now has a concrete interoperability seam with `argentina-geography`. That makes it an active bounded producer/consumer surface rather than a merely dormant maintenance archive.

Active does not imply continuous modernization. Work should be driven by named electoral-data needs, source changes, reproducibility fixes or explicit downstream integration.

## Active boundary

The repository owns electoral event/result semantics: election identity, cargos, lists/agrupaciones, vote facts, mesas and the source-native electoral hierarchy used by the pipeline.

It does not own Census/administrative geography, geometric circuit releases or factual Census↔electoral spatial relations. Those are external artifacts from `argentina-geography` and must remain explicitly versioned.

## Development policy

- Preserve extraction, normalization, dimensions, fact tables, candidates/mesa-roll integration, aggregates, QA and manifest stages.
- Correct observed breakage, source changes or misleading public claims.
- Add integration only when exact source/release identities and key semantics are explicit.
- Do not infer that electoral section/circuit codes are INDEC/IGN identifiers.
- Do not undertake broad framework/dependency refactors merely because the repository is old.
- Treat generated electoral outputs as dated artifacts; a recent code push does not prove current election coverage.

## Verification boundary

A meaningful runtime verification should record source/election coverage, exact cutoff, command, QA result, manifest/output timestamp and any missing district, office, list, mesa or table.

## Lineage

Older electoral repositories may point here as their successor. Historical predecessors remain useful for genealogy but are not current authority unless explicitly stated. Geographic interoperability is supplied by exact `argentina-geography` releases rather than copied GIS logic.

A bounded predecessor audit completed on 2026-08-30. See [`docs/HISTORICAL_PREDECESSORS.md`](docs/HISTORICAL_PREDECESSORS.md) for the current disposition of the audited legacy workbenches and data-preparation repositories.
