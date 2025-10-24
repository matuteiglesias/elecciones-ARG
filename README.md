# Resultados electorales Argentina 2011-2025 — datos, estimación y visualización

Este repo contiene **datos de referencia (vía lake), notebooks y utilidades** para
**resultados electorales Argentina 2025** (elecciones legislativas) y ejercicios de
**nowcasting** (estimaciones tempranas) por mesa/circuito/distrito. Incluye estilos web
(Mapbox) y análisis con DuckDB/Parquet. Enfoque especial en **Provincia de Buenos Aires 2025**.

> Lake: `$ELEC_LAKE=/media/matias/Elements/electoral_lake` (canon/raw/geo/exports)

## Qué hay aquí (rápido)
- **Nowcasting**: betas por mesa para estimaciones tempranas (Sheets-ready).
- **Analítica**: notebooks de descomposición y cruce EPH.
- **Web**: plantillas de estilos; los artefactos se generan a `exports/web` en el lake.
- **Datos**: *no* en Git; están en el **data lake** (Parquet/GeoJSON).

## Palabras clave y alcance
- *Elecciones Legislativas 2025*, *Resultados provisorios*, *Buenos Aires 2025*, *DINE datos*,
  *resultados por mesa*, *datos abiertos*, *Argentina 2025*.
