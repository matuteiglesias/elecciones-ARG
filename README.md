[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)]()
[![Data Pipeline](https://img.shields.io/badge/type-ETL%20Pipeline-orange.svg)]()
[![Open Data](https://img.shields.io/badge/datos%20abiertos-✓-blue.svg)]()



# **Infraestructura de Datos Electorales — Argentina**

Este repositorio estandariza y armoniza los conjuntos de datos electorales de la Argentina —desde los CSV provinciales originales hasta tablas de hechos listas para análisis y visualización.
El pipeline automatiza la **ingesta**, **deduplicación**, **normalización** y **generación de tablas canónicas**, garantizando reproducibilidad y trazabilidad de cada etapa.

---

## **Estructura del repositorio**

```
pipelines/
 ├── 10_extract_concat_raw.py   → Fusiona y hashea los archivos electorales crudos
 ├── 20_normalize_core.py       → Normaliza esquemas y nombres
 ├── 30_build_dims.py           → Construye las tablas de dimensiones
 ├── 40_build_facts.py          → Genera la tabla de hechos (mesa×cargo×lista×votos_tipo)
 └── utils_logging.py           → Configuración unificada de logging
canon/
 ├── bd/csv/                    → Salidas finales en formato CSV
 └── bd/parquet/                → Exportaciones opcionales en Parquet
logs/                           → Ejecuciones registradas con marca temporal
```

---

## **Guía de ejecución (Runbook)**

```bash
# Reconstrucción completa del pipeline
make all

# Inspeccionar resultados
du -h canon/
head canon/bd/csv/votos_fact.csv
```

Cada script puede ejecutarse de forma independiente.
El pipeline genera logs detallados bajo `logs/latest` para auditoría y depuración.

---

## **Notas técnicas**

* Identificador de elección (`eleccion_id`) **determinístico**, derivado de:
  `(año, eleccion_tipo, recuento_tipo, padron_tipo)`
* Política de duplicados: **keep_first**
* Los valores faltantes se preservan (no se rellenan con ceros)
* Grano de la tabla de hechos:
  **mesa × cargo × agrupación/lista × votos_tipo**
* CSVs codificados en **UTF-8**, delimitados por comas, listos para cargar en **DuckDB**, **pandas** o motores SQL.
* Todos los scripts son **idempotentes**: las salidas dependen solo de los datos fuente, no del orden de ejecución.

---

## **Propósito y alcance**

Esta infraestructura busca **fortalecer el acceso público a los datos electorales**, ofrecer **procesos reproducibles** y **facilitar el análisis comparativo** entre años, provincias y tipos de elección.
El sistema está preparado para integrarse con tableros interactivos o entornos analíticos, manteniendo un diseño modular y extensible.

---

## **Palabras clave (SEO)**

* *Datos electorales Argentina*
* *Pipeline Python ETL elecciones*
* *Normalización de resultados electorales*
* *Transparencia y datos abiertos*
* *Buenos Aires / elecciones nacionales 2019–2025*
* *Análisis reproducible de elecciones argentinas*

---

## **Próximos pasos**

* Incorporar actualizaciones en tiempo real durante los comicios.
* Publicar comparaciones históricas por distrito y tipo de cargo.
* Integrar visualizaciones interactivas y servicios API para terceros.


