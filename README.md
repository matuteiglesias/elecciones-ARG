# Análisis y Visualización de Datos Electorales

Este repositorio contiene una colección de scripts, cuadernos y archivos de datos relacionados con el análisis y visualización de datos electorales en Argentina. Este proyecto proporciona herramientas y conocimientos para explorar y comprender las tendencias electorales, la demografía de los votantes y la dinámica política.

## Datos

El directorio `datos` contiene varios subdirectorios con diferentes tipos de datos utilizados en el análisis:

- `BD`: Contiene archivos resultantes de la descomposición de la información electoral en un esquema de base de datos relacional. Conserva los nombres originales de las entidades mientras aborda variaciones e inconsistencias.

- `geojson`: Incluye archivos GeoJSON que asocian información electoral con polígonos del mapa. Estos archivos representan provincias, departamentos y circuitos electorales, incluyendo datos de votación tanto en porcentajes como en cantidades. Los archivos de polígonos simplificados también están disponibles para reducir el tamaño del archivo sin comprometer la calidad visual.

- `info`: Contiene archivos misceláneos con información adicional, tales como radio referencias censales, mapeos de “secciones” a departamentos, archivos IGN (Instituto Geográfico Nacional) de provincias y departamentos, valores de calibración de escala para colores de mapas y mapeos de circuitos a departamentos y provincias.

- `out`: Contiene archivos resumen que consolidan la información de la votación por circuito, provincia y sección.

## Notebooks

El directorio `notebooks` consta de varios cuadernos Jupyter que realizan tareas de exploración y análisis de datos. Estos cuadernos cubren una variedad de temas, que incluyen:

- Explorar el número de electores y analizar sus variaciones en el tiempo.
- Investigar la distribución de la población entre departamentos y su comparacion con la participacion electoral.
- Analizar el tipo de voto (Positivos, Nulos, etc) a nivel de circuito y departamento.
- Examinar el desempeño y representación de las agrupaciones políticas y alianzas.

## Visualización web

El directorio `web` contiene archivos relacionados con la visualización basada en la web de datos electorales:

- `index.html`: El archivo HTML principal que sirve como punto de entrada para la aplicación web. Proporciona una interfaz interactiva basada en mapas para explorar datos electorales.

- `style_info.json`: un archivo JSON que almacena información sobre diferentes estilos de mapas utilizados en la aplicación web. Permite a los usuarios personalizar la representación visual de los datos.

## Para Comenzar

Para comenzar con tu proyecto, segui estos pasos:

1. Clone el repositorio en su máquina local.
2. Explore el directorio `notebooks` para analizar los datos electorales usando los notebooks Jupyter y genere sus propios analisis.
3. Consulte la web del Peronometro Electoral para conocer los porcentajes de votos obtenidos por distintas fuerzas en cada rincon del pais en distintas elecciones.

Si encuentra útil este código en tu trabajo o investigación, se agradece la cita como Matías N. Iglesias y mencion al repositorio de GitHub: [elecciones-ARG](https://github.com/matuteiglesias/elecciones-ARG) 

Para obtener documentación detallada y ejemplos, consulte los cuadernos individuales y los comentarios dentro del código.

Tenga en cuenta que los datos utilizados en este repositorio se basan en datos electorales disponibles públicamente para Argentina y pueden tener limitaciones y advertencias específicas. Use la información de manera responsable y siempre verifique las fuentes de datos y cualquier conocimiento derivado.

Para cualquier pregunta o problema, comunicarse con los mantenedores del proyecto (M. Iglesias).

¡Ya estas listo para explorar y análizar los datos electorales!
