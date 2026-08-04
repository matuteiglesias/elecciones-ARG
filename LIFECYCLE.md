# Repository lifecycle

**State:** `maintenance`  
**Decision date:** 2026-08-03  
**Review cadence:** annual  
**Next portfolio review:** August 2027

## Why this state

This repository is retained as the canonical electoral-data pipeline in the current GitHub estate. Its default commitment is bounded verification and correction, not continuous feature development.

## Maintenance policy

- Preserve the existing extraction, normalization, dimensional-model, fact-table, QA, and manifest workflow.
- Run the documented pipeline only when a current electoral-data need or annual verification justifies the cost.
- Correct observed breakage, source changes, or unsupported public claims.
- Do not undertake dependency upgrades, framework changes, or broad refactors merely because the repository is old.
- Treat generated electoral outputs as dated artifacts; a recent repository push does not prove that the latest election data has been rebuilt.

## Verification boundary

This lifecycle declaration does not certify that `make all`, every source adapter, or every current-data claim works on 2026-08-03. Runtime verification should record:

1. source and election coverage;
2. exact data cutoff;
3. command executed;
4. QA result;
5. manifest or output timestamp;
6. any missing district, office, list, or table.

## Lineage

Older electoral repositories may point here as their successor. Historical predecessors remain useful for genealogy, but they are not current authority unless explicitly stated otherwise.
