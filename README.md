[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)]()
[![Data Pipeline](https://img.shields.io/badge/type-ETL%20Pipeline-orange.svg)]()
[![Open Data](https://img.shields.io/badge/datos%20abiertos-✓-blue.svg)]()

# Infraestructura de Datos Electorales — Argentina

Este repositorio estandariza resultados electorales argentinos y conserva la identidad propia de elecciones, cargos, listas, mesas, distritos, secciones y circuitos. Produce tablas dimensionales, hechos electorales, agregados, QA y manifests reproducibles.

## Qué autoridad posee

`elecciones-ARG` posee semántica de **eventos y resultados electorales**: `eleccion_id`, cargos, agrupaciones/listas, tipos de voto, mesas y las claves electorales presentes en las fuentes.

No posee una geografía censal/administrativa “equivalente” a esas claves. Las geometrías y relaciones entre circuitos electorales y geografías Census/administrativas viven en `argentina-geography` como artefactos versionados. Un `circuito_id`, `seccion_id` o `coddepto` electoral no debe reinterpretarse silenciosamente como un ID INDEC/IGN.

La integración correcta es por artefacto explícito y release exacta; no por imports de un checkout hermano ni por similitud de códigos.

## Pipeline actual

```text
pipelines/
 ├── 00_config.yml              → Configuración del pipeline
 ├── 10_extract_concat_raw.py   → Fusiona, registra procedencia y hashea fuentes
 ├── 20_normalize_core.py       → Normaliza esquemas y categorías
 ├── 30_build_dims.py           → Construye dimensiones electorales
 ├── 40_build_facts.py          → Construye hechos de votos
 ├── 50_load_candidates.py      → Incorpora candidatos cuando existe fuente soportada
 ├── 55_load_mesa_roll.py       → Integra padrón/roll de mesas (AyT)
 ├── 60_build_aggregates.py     → Genera agregados electorales
 ├── 70_qa_checks.py            → Ejecuta controles de calidad
 ├── 80_snapshot_manifest.py    → Emite el recibo/manifiesto de la corrida
 └── utils_logging.py           → Logging compartido

canon/
 ├── bd/csv/                    → Salidas canónicas CSV
 └── bd/parquet/                → Derivados Parquet cuando corresponda
```

## Ejecución

```bash
make all

du -h canon/
head canon/bd/csv/votos_fact.csv
```

Los outputs deben interpretarse con su cobertura y fecha de corte. Un commit reciente del repositorio no prueba por sí mismo que se haya reconstruido la elección más reciente.

## Cadena de confianza

1. **10 — adquisición:** concatena fuentes y conserva huellas/procedencia.
2. **20 — normalización:** armoniza esquema y categorías electorales.
3. **30 — dimensiones:** materializa elecciones, distritos, secciones, circuitos, mesas, cargos y agrupaciones.
4. **40 — hechos:** produce la tabla de votos a su grano declarado.
5. **50 — candidatos:** agrega identidad de candidaturas cuando la fuente existe.
6. **55 — mesas:** integra evidencia adicional del padrón/roll de mesas.
7. **60 — agregados:** deriva resúmenes electorales desde los hechos.
8. **70 — QA:** controla dominios, cobertura e invariantes.
9. **80 — manifest:** registra inputs, outputs y evidencia de la corrida.

## Geografía electoral y Argentina Geography

Las dimensiones electorales de este repositorio pueden enlazarse con releases de `argentina-geography`, pero esa relación es explícita y versionada.

En particular:

- la jerarquía electoral distrito → sección → circuito es distinta de provincia → departamento → radio;
- códigos con apariencia similar no implican identidad;
- una relación Census↔circuito puede ser N:M;
- este repositorio no debe inventar un “ganador” geográfico ni elegir un circuito por mayor solapamiento;
- la elección de qué vintage geográfico corresponde a cada evento electoral es política del consumidor y debe quedar declarada.

El objetivo es que resultados electorales y geografía puedan combinarse sin mezclar sus autoridades.

## QA y reproducibilidad

`70_qa_checks.py` verifica inconsistencias electorales observables; `80_snapshot_manifest.py` produce el recibo de la corrida. La verificación de una reconstrucción real debería registrar como mínimo fuente/cobertura electoral, fecha de corte, comando, QA, manifest y ausencias conocidas.

## Alcance

Esta infraestructura facilita análisis, auditorías y visualizaciones de datos electorales. No declara resultados oficiales por sí misma, no sustituye a las fuentes electorales oficiales y no posee geografía Census/administrativa.

Ver también `LIFECYCLE.md` y `SYSTEM.yaml` para la frontera operativa y de autoridad del repositorio.
