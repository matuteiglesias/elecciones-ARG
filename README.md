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

# FAQ

## **Cómo funciona la infraestructura de datos electorales — elecciones-ARG**

Esta infraestructura toma los resultados electorales brutos de distintas fuentes oficiales y los transforma, paso a paso, en un conjunto limpio, coherente y listo para análisis o visualización pública.
El objetivo es que **los datos electorales sean confiables, comparables y auditables**.

---

### **1. Reunir todos los datos crudos**

Cada elección genera decenas de archivos —uno por distrito, por tipo de recuento, o por formato provincial—.
El primer programa (`10_extract_concat_raw.py`) se encarga de **leerlos todos**, detectar su codificación, unificarlos y crear un único archivo grande:
`all_raw.csv`, junto con un registro (`manifest.csv`) que guarda quién aportó cada archivo y su huella digital (hash SHA-256).

👉 Esto garantiza **trazabilidad**: siempre se puede saber de dónde vino cada dato.

---

### **2. Normalizar y limpiar la información**

El segundo paso (`20_normalize_core.py`) **ordena el contenido interno de los archivos**:

* Traduce nombres inconsistentes (por ejemplo “Positivos” vs “POSITIVO”).
* Asigna códigos únicos a cada tipo de elección, cargo y voto.
* Crea un identificador estable (`eleccion_id`) que permite comparar años distintos sin confundir tipos de elección.

👉 Aquí se logra **coherencia estructural**: cada fila de datos significa lo mismo en todas las elecciones.

---

### **3. Construir las tablas de referencia**

El tercer módulo (`30_build_dims.py`) arma **tablas “dimensionales”**: listas de distritos, secciones, circuitos, mesas, cargos, y agrupaciones.
Sirven como diccionarios que permiten vincular los votos con su contexto geográfico y político.

👉 Resultado: un “esqueleto” completo de la elección, donde cada entidad tiene su propio identificador y nombre oficial.

---

### **4. Consolidar los votos**

El cuarto paso (`40_build_facts.py`) reúne todo en una **gran tabla de hechos**:
`votos_fact.csv`, donde cada fila representa los votos de una mesa para un cargo y agrupación determinada.

👉 Este es el corazón del sistema: la base de datos donde **cada voto queda contabilizado de forma verificable**.

---

### **5. Incorporar candidatos (opcional)**

En elecciones recientes, se puede ampliar con `50_load_candidates.py`, que toma las listas oficiales de candidatos y construye tablas persona-a-persona.
Así se puede cruzar información entre elecciones, géneros, o trayectorias.

👉 Permite análisis más humanos: **quién compite, cuántas veces, y en qué lugares**.

---

### **6. Actualizar el padrón de mesas (AyT)**

El módulo `55_load_mesa_roll.py` integra los padrones oficiales (“AyT”) con las mesas registradas en el sistema.
Detecta discrepancias, las documenta y actualiza el padrón maestro.

👉 Esto mantiene la base **sin huecos ni duplicados**, asegurando que las mesas coincidan con las fuentes oficiales.

---

### **7. Generar estadísticas y agregados**

Con `60_build_aggregates.py`, los datos se resumen en distintos niveles (circuito, departamento, provincia).
Produce archivos con cantidad de electores y tipos de votos.

👉 Es la etapa donde los datos se vuelven **útiles para gráficos, dashboards o comparaciones históricas**.

---

### **8. Verificación y control de calidad**

`70_qa_checks.py` actúa como un **sistema de alarmas tempranas**:

* Detecta votos negativos o faltantes.
* Comprueba que los votos totales coincidan con los válidos.
* Evalúa la cobertura y la integridad de las mesas.

👉 Garantiza que los datos publicados sean **consistentes y creíbles**.

---

### **9. Crear el “recibo” de la corrida**

Finalmente, `80_snapshot_manifest.py` genera un **MANIFEST.json**: un resumen con los archivos usados, cantidad de filas y verificaciones de integridad.
Este “recibo” queda guardado como evidencia de que el proceso fue completo y sin alteraciones.

👉 Es la clave de la **reproducibilidad**: cualquiera puede volver a correr el pipeline y obtener los mismos resultados.

---

### **10. En conjunto**

Estos diez módulos conforman una **cadena de confianza**:

1. Extrae los datos crudos.
2. Los limpia y estandariza.
3. Construye una base ordenada y verificable.
4. Genera productos claros para análisis público.

Para los **equipos de política**, esto significa tener información confiable sobre los resultados, los padrones y las tendencias.
Para los **equipos técnicos**, significa contar con un sistema modular, documentado y reproducible que permite construir tableros, informes o auditorías sin depender de archivos sueltos.

---

### **Por qué importa**

* **Transparencia:** cualquiera puede revisar o replicar el proceso.
* **Rigor técnico:** las transformaciones están documentadas y controladas.
* **Impacto público:** los datos electorales se vuelven un bien común, accesible y verificable.

