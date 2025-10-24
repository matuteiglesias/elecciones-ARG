# %%
import pandas as pd

# ----- Function Definitions -----
def harmonize_agrupacion_id(agrupacion_id):
    if pd.isna(agrupacion_id):
        return "000000"
    else:
        try:
            return str(int(float(agrupacion_id))).zfill(6)
        except ValueError:
            return agrupacion_id

# ----- Data Loading -----
BD_path = './../datos/BD151923'

# Carga de datos
df1 = pd.read_csv(f"{BD_path}/votos_eleccion_7_table.csv")
df2 = pd.read_csv(f"{BD_path}/votos_eleccion_8_table.csv")
df = pd.concat([df1, df2])





# %%

# ----- Data Preprocessing -----
# Votos Eleccion Data Preprocessing
df = df[df['cargo_id'].isin([1])]
df['agrupacion_id'] = df['agrupacion_id'].apply(harmonize_agrupacion_id)

# %%


# %%
agrup_lista = pd.read_csv(f'{BD_path}/agrupacion_nombre_table.csv')
claves_dptos = pd.read_csv(f'{BD_path}/claves_dptos_ref.csv')



# %%


# Agrup Lista Data Preprocessing
agrup_lista['agrupacion_id'] = agrup_lista['agrupacion_id'].apply(harmonize_agrupacion_id)
agrup_lista['agrupacion_nombre'] = agrup_lista['agrupacion_nombre'].apply(harmonize_agrupacion_id)

# Claves Dptos Data Preprocessing
claves_dptos = claves_dptos.dropna(subset=['codprov']).astype({'codprov': 'Int64', 'coddepto' : 'Int64', 'IN1' : 'Int64'})
claves_dptos[['codprov', 'coddepto', 'IN1']] = claves_dptos[['codprov', 'coddepto', 'IN1']].astype(str).apply(lambda x: x.str.zfill(x.str.len().max()))
claves_dptos.loc[claves_dptos.seccion_nombre == 'La Plata', 'IN1'] = '06441'


# %%


# %%
# ----- Data Merging & Transformations -----
# Merge with simil_nombre
simil_nombre = agrup_lista.groupby(['eleccion_id', 'distrito_id', 'agrupacion_id']).agrupacion_nombre.first().reset_index()
df = df.merge(simil_nombre)
merged_data = df

# Harmonize 'agrupacion_nombre'
for old_name, new_name in [('CAMBIEMOS BUENOS AIRES', 'CAMBIEMOS'), ('JUNTOS', 'JUNTOS POR EL CAMBIO')]:
    merged_data['agrupacion_nombre'] = merged_data['agrupacion_nombre'].replace(old_name, new_name)
merged_data['agrupacion_nombre'] = merged_data['agrupacion_nombre'].str.title()

# %%
df

# %%
# Group and aggregate data
aggregated_data = merged_data.groupby(['eleccion_id', 'cargo_id', 'agrupacion_id', 'agrupacion_nombre', 'votos_tipo']).agg({'votos_cantidad': 'sum'}).reset_index()

# Top N aggregation
N = 8
top_aggregated_data = aggregated_data.groupby(['eleccion_id', 'cargo_id', 'votos_tipo']).apply(lambda x: x.nlargest(N, 'votos_cantidad')).reset_index(drop=True).rename(columns={'votos_cantidad': 'votos_nacional'})

# Further transformations...
data_copy = df.copy()
for old_name, new_name in [('CAMBIEMOS BUENOS AIRES', 'CAMBIEMOS'), ('JUNTOS', 'JUNTOS POR EL CAMBIO')]:
    data_copy['agrupacion_nombre'] = data_copy['agrupacion_nombre'].replace(old_name, new_name)
data_copy['agrupacion_nombre'] = data_copy['agrupacion_nombre'].str.title().str.strip()
data_copy = data_copy.merge(top_aggregated_data, how='left')
data_copy['agrupacion_nombre_'] = data_copy['agrupacion_nombre'].mask(data_copy['votos_nacional'].isnull(), 'Resto')
data_aggregated = data_copy.groupby(['eleccion_id', 'distrito_id', 'seccion_id', 'circuito_id', 'mesa_id', 'cargo_id', 'agrupacion_nombre_', 'agrupacion_nombre', 'votos_tipo', 'eleccion_id']).agg({'votos_cantidad': 'sum'}).reset_index()


# %%
data_aggregated.groupby(['eleccion_id', 'votos_tipo', 'agrupacion_nombre_', 'cargo_id']).agg({'votos_cantidad': 'sum'}).reset_index().sort_values(['eleccion_id', 'votos_tipo', 'agrupacion_nombre_', 'cargo_id'], ascending=False)

# %%
cargo = pd.read_csv(f'{BD_path}/cargo_tags.csv')
eleccion_tags = pd.read_csv(f'{BD_path}/eleccion_tags.csv')


# %%


# More transformations...
data_circ = data_aggregated.groupby(['eleccion_id', 'cargo_id', 'agrupacion_nombre_', 'agrupacion_nombre', 'votos_tipo', 'distrito_id', 'seccion_id', 'circuito_id'])[['votos_cantidad']].sum()
data_circ = data_circ.reset_index()
data_circ['circuito_id'] = data_circ['circuito_id'].astype(str).str.zfill(6)
# data_circ.to_csv('./../datos/out/votos_agrup_circ.csv')

# data_circ
# data_circ = pd.read_csv('./../datos/out/votos_agrup_circ.csv')

data_circ = data_circ.merge(eleccion_tags).merge(cargo)


# Group by 'eleccion_tag', 'cargo_tag', and 'in1_prov', and calculate the sum of 'votos_cantidad', divide for PCT
sum_votes = data_circ.groupby(['eleccion_tag', 'cargo_tag', 'distrito_id', 'seccion_id', 'votos_tipo', 'circuito_id'])['votos_cantidad'].transform('sum')
data_circ['votos_porcentaje'] = data_circ['votos_cantidad'] / sum_votes
data_circ.reset_index(drop = True).to_csv('./../datos/out/votos_agrup_lista_circ.csv', index = False)

data_circ_ix = data_circ.set_index(['distrito_id', 'seccion_id', 'circuito_id', 'eleccion_tag', 'cargo_tag', 'agrupacion_nombre_', 'agrupacion_nombre', 'votos_tipo'])


data_circ_table_cnt = data_circ_ix['votos_cantidad'].unstack(['eleccion_tag', 'cargo_tag', 'votos_tipo', 'agrupacion_nombre_', 'agrupacion_nombre'])
data_circ_table_pct = data_circ_ix['votos_porcentaje'].unstack(['eleccion_tag', 'cargo_tag', 'votos_tipo', 'agrupacion_nombre_', 'agrupacion_nombre'])

# # ----- Exporting -----
# data_circ_geoms_cnt.to_file('./../datos/geojson/votos_cnt_circ.geojson', driver='GeoJSON')
# data_circ_geoms_pct.to_file('./../datos/geojson/votos_pct_circ.geojson', driver='GeoJSON')


# %%
circuitos.circuito_id.nunique()

# %%
data_circ.nunique()

# %%
circuitos.nunique()

# %% [markdown]
# ## Datos Pobreza

# %%
import numpy as np

# %%


# %%


# Load data
print("Loading data...")
df_files = [
    './../../indice-pobreza-UBA/data/Pobreza/individual_income_sample0.02_2022-05-15_ARG.csv',
    './../../indice-pobreza-UBA/data/Pobreza/individual_income_sample0.02_2022-08-15_ARG.csv',
    './../../indice-pobreza-UBA/data/Pobreza/individual_income_sample0.02_2022-11-15_ARG.csv',
    './../../indice-pobreza-UBA/data/Pobreza/individual_income_sample0.02_2023-02-15_ARG.csv'
]
df = pd.concat([pd.read_csv(file) for file in df_files])

# Process data
print("Processing data...")
df['ingresos'] = 32 * (np.power(10, df['P47T_persona']) - 1)
df['ingresos'] = df['ingresos'].round(-3).astype(int)


# Load and combine geo data
print("Loading and combining geo data...")
geo_files = [
    './../../indice-pobreza-UBA/data/Pobreza/geo_households_sample0.02_2022_ARG.csv',
    './../../indice-pobreza-UBA/data/Pobreza/geo_households_sample0.02_2023_ARG.csv'
]
geo = pd.concat([pd.read_csv(file) for file in geo_files])
hogar_circuito = geo[['HOGAR_REF_ID', 'distrito_id', 'seccion_id', 'seccion_nombre', 'circuito', 'AGLOMERADO']].drop_duplicates()

# Merge data
print("Merging data...")
persona_circuito = df.merge(hogar_circuito)
persona_circuito = persona_circuito.loc[persona_circuito.P03 > 24]


# %%
## Most common aglomerado per seccion
seccion_AGLO = persona_circuito.groupby(['distrito_id', 'seccion_id'])['AGLOMERADO'].agg(lambda x:x.value_counts().index[0]).reset_index()
persona_circuito = persona_circuito.drop('AGLOMERADO', axis=1)
seccion_AGLO.head()

# %% [markdown]
# ## Testeos

# %%
ingreso_medio08 = pd.read_csv('./ingreso_medio_202308.csv')
ingreso_medio10 = pd.read_csv('./ingreso_medio_202310.csv')
# ingreso_medio.to_csv('./ingreso_medio_202308.csv', index=False)
ingreso_medio = ingreso_medio08.merge(ingreso_medio10, on = ['distrito_id', 'seccion_id', 'seccion_nombre', 'circuito_id'], suffixes = ('_08', '_10'))
ingreso_medio['ingresos'] = (ingreso_medio['ingresos_08'] + ingreso_medio['ingresos_10']) / 2


mesas = pd.read_csv('./../datos/BD151923/mesas_table.csv')
mesas.head()

circuitos = mesas.groupby(['distrito_id', 'seccion_id', 'circuito_id']).mesa_electores.agg(['sum', 'count']).reset_index().rename(columns={'sum': 'electores', 'count': 'mesas'})

circuitos = circuitos.merge(ingreso_medio, on = ['distrito_id', 'seccion_id', 'circuito_id'], how = 'left')

circuitos['error'] = abs(circuitos['ingresos_10'] - circuitos['ingresos_08'])
circuitos['Error_bin'] = pd.qcut(circuitos['error'], 5, labels=['1', '6', '13', '25', '50'])#.value_counts() # Error aprox en pesos

circuitos.groupby('Error_bin')[['electores', 'error']].describe().round(1).astype(int)

# %%
import matplotlib.pyplot as plt
import seaborn as sns

# Set style and color palette
sns.set_style('whitegrid')
sns.set_context('paper')
palette = sns.color_palette('tab10')

# Set figure size
fig, ax = plt.subplots(figsize=(10, 6))

# Plot data
sns.scatterplot(
    data=circuitos,
    x='ingresos_08',
    y='ingresos_10',
    hue='Error_bin',
    palette=palette,
    size=circuitos['mesas'].apply(lambda x: min(x / max(circuitos['mesas']) * 5000, 200)),
    sizes=(20, 200),
    alpha=0.2,
    ax=ax
)

# Set axis labels
ax.set_xlabel('Ingreso medio 2008')
ax.set_ylabel('Ingreso medio 2010')

# Set legend
ax.legend(
    title='Distrito',
    bbox_to_anchor=(1.05, 1),
    loc='upper left',
    borderaxespad=0
)

plt.show()


# %%


## Make a fancy plot
import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns

# Set style
sns.set_style('whitegrid')
sns.set_context('paper')

# Set color palette
# palette = sns.color_palette('colorblind')
palette = sns.color_palette('tab10')

# Set figure size
fig, ax = plt.subplots(figsize=(10, 6))

# Plot data
sns.scatterplot(
    data=ingreso_medio,
    x='ingresos_08',
    y='ingresos_10',
    hue='distrito_id',
    palette=palette,
    s='mesas',
    alpha=0.2,
    ax=ax
)

# Set axis labels
ax.set_xlabel('Ingreso medio 2008'); ax.set_ylabel('Ingreso medio 2010')

# Set legend
ax.legend(
    title='Distrito',
    bbox_to_anchor=(1.05, 1),
    loc='upper left',
    borderaxespad=0
)

# fig.savefig('./ingreso_medio_2008_vs_2010.png', dpi=300, bbox_inches='tight')
plt.show()


# %% [markdown]
# ### Tamanos de circuitos

# %%


# %%
votos = data_circ_table_cnt['GRAL23n']['PR'].sum().sort_values(ascending = False)
votos

# %%
100*(4e5/votos.sum())

# %%
votos = data_circ_table_cnt['PASO23n']['PR'].sum().sort_values(ascending = False)
votos

# %%
votos_circuito = data_circ_table_cnt['GRAL23n']['PR'].sum(1).sort_values(ascending=False)

s = votos_circuito.reset_index(drop = True)
(s/s.sum()).cumsum().plot(grid = True)

# %%
votos_circuito.sum()/circuitos.electores.sum()

# %%


# %%
## Tomar los 3000 circuitos grandes, es decir, los que tienen mas de 1000 votos.
votos_circuito.head(2100)

# %%
circuitos_ppales = votos_circuito.loc[votos_circuito > 2000]
circuitos_ppales = circuitos_ppales.index.to_frame().reset_index(drop=True)

# %% [markdown]
# ### Tamanos de listas

# %%
votos_lista = data_circ.loc[data_circ.cargo_id == 1].groupby(['eleccion_id', 'votos_tipo', 'agrupacion_nombre_', 'agrupacion_nombre'])['votos_cantidad'].sum()
votos_lista = votos_lista.sort_values(ascending=False)
main_listas  = votos_lista.head(14)
# s = votos_lista.reset_index(drop = True)
# (s/s.sum()).cumsum().plot(grid = True)
# (s/s.sum()).cumsum()

# %%
main_listas

# %%
# main_listas = info_table['votos_cantidad'].sum().sort_values(ascending=False).head(10)
main_listas = main_listas.index.to_frame().reset_index(drop=True)
main_listas


# %%


# %% [markdown]
# # Votos Por Circuitos
# 
# ## Introducción y Preparación de Datos
# 
# En este análisis, estamos interesados en explorar los datos electorales a nivel de circuito, integrando información demográfica y geográfica para obtener una comprensión más completa de los patrones de votación. Comenzamos cargando y preparando los conjuntos de datos necesarios, incluyendo los ingresos medianos por circuito, las mesas electorales, y la información geográfica de los departamentos y regiones.
# 
# Realizamos agregaciones y fusiones para crear un conjunto de datos de circuitos, que incluye el número de electores, el número de mesas, y los ingresos medianos. También integramos nombres de provincias y regiones para enriquecer nuestro análisis.
# 

# %%
# Aggregation and merging
print("Aggregating data...")
ingreso_medio = (persona_circuito.groupby(['distrito_id', 'seccion_id', 'seccion_nombre', 'circuito'])
                 .agg({'ingresos': 'median'}).reset_index()
                 .assign(circuito_id=lambda df: df['circuito'].astype(str).str.zfill(6))
                 .drop('circuito', axis=1))
ingreso_medio[['distrito_id', 'seccion_id']] = ingreso_medio[['distrito_id', 'seccion_id']].astype('int64')

circuitos = (mesas.groupby(['eleccion_id', 'distrito_id', 'seccion_id', 'circuito_id']).mesa_electores
             .agg(['sum', 'count']).reset_index()
             .rename(columns={'sum': 'electores', 'count': 'mesas'})
             .merge(ingreso_medio, on=['distrito_id', 'seccion_id', 'circuito_id'], how='left'))

prov_nams = pd.read_csv(f'{BD_path}/distrito_table.csv')
radio_region = pd.read_csv('./../datos/info/radio_ref.csv', usecols=['radio', 'NOMDPTO', 'Region'])
radios_circuitos_secciones = pd.read_csv('./../datos/info/radios_circuitos_secciones_ref.csv')[['COD_2010', 'distrito_id', 'seccion_id', 'seccion_nombre']]

merge = radios_circuitos_secciones.merge(radio_region.assign(COD_2010=radio_region['radio'].astype(str).str.zfill(9)), on='COD_2010', how='left')
seccion_region = (merge.drop(['COD_2010', 'radio'], axis=1).drop_duplicates()
                  .groupby(['distrito_id', 'seccion_id', 'seccion_nombre']).first().reset_index())
print("Done!")


# %%
circuitos.groupby(['eleccion_id'])['electores'].sum()

# %% [markdown]
# ## Verificación de Datos
# 
# Antes de proceder con el análisis, es crucial verificar que los datos se hayan cargado y fusionado correctamente. Chequeamos los totales de electores y votos para los cargos de presidente y diputados nacionales en las elecciones PASO y generales de 2023.
# 
# Esto nos ayuda a asegurar la integridad de nuestros datos y a identificar cualquier posible incongruencia antes de avanzar.
# 

# %%
# Data verification
print("Total electores in circuitos:", circuitos['electores'].sum())
print("Total votos in data_circ:", data_circ.groupby(['eleccion_id', 'cargo_id'])['votos_cantidad'].sum())


# %% [markdown]
# ## Análisis de Datos y Creación de Bins
# 
# Realizamos un análisis exploratorio de los datos para entender mejor la distribución de los votos y las características de los circuitos. Además, creamos bins de electores para facilitar análisis posteriores y visualizaciones.
# 
# También calculamos la fracción de votos que permanecen en el conjunto de datos después de descartar los circuitos pequeños, lo que nos proporciona una medida de cuánto impacta este filtrado en nuestro análisis.
# 

# %%
# Further merging and data preparation
merged_data = (circuitos.merge(data_circ, left_on=['eleccion_id', 'distrito_id', 'seccion_id', 'circuito_id'], 
                               right_on=['eleccion_id', 'distrito_id', 'seccion_id', 'circuito_id'], how='right')
               .merge(prov_nams, on='distrito_id')
               .merge(seccion_region, on=['distrito_id', 'seccion_id', 'seccion_nombre'], how='left')).rename(columns={'electores': 'electores_circuito'})


# %%
print("Total votos in merged_data:", merged_data.groupby(['eleccion_id', 'cargo_id'])['votos_cantidad'].sum())


# %% [markdown]
# ## Cálculo del Peso de circuitos en Votos
# 
# A continuación, calculamos y mostramos la fracción de votos que permanecen en el conjunto de datos `info` después de descartar los circuitos pequeños. Esto nos ayuda a evaluar el impacto de este filtrado en los resultados de nuestro análisis.
# 

# %%

info = merged_data.query("electores_circuito > 3000")

total_votos = merged_data.votos_cantidad.sum()
votos_en_info = info.votos_cantidad.sum()
fraccion_votos = votos_en_info / total_votos
print(f"Fracción de votos en circuitos con más de 2500 electores: {fraccion_votos:.2%}")


# %%
info.head()

# %%
info.columns

# %%
# info_columns = set(info.columns)
# votos_EPH_circuitos_columns = set(votos_EPH_circuitos.columns)
# data_reset_index_columns = set(data.reset_index().columns)

# print("Columns in 'info' but not in 'votos_EPH_circuitos':", info_columns - votos_EPH_circuitos_columns)
# print("Columns in 'votos_EPH_circuitos' but not in 'info':", votos_EPH_circuitos_columns - info_columns)
# print("Columns in 'info' but not in 'data.reset_index()':", info_columns - data_reset_index_columns)
# print("Columns in 'data.reset_index()' but not in 'info':", data_reset_index_columns - info_columns)
# print("Columns in 'votos_EPH_circuitos' but not in 'data.reset_index()':", votos_EPH_circuitos_columns - data_reset_index_columns)
# print("Columns in 'data.reset_index()' but not in 'votos_EPH_circuitos':", data_reset_index_columns - votos_EPH_circuitos_columns)


# %%
# Data analysis and binning
print("Total votos in merged_data:", merged_data.groupby(['eleccion_id', 'cargo_id'])['votos_cantidad'].sum())
print("Total votos in info:", info.groupby(['eleccion_id', 'cargo_id'])['votos_cantidad'].sum())
print("Unique values in info:", info.nunique())

# merged_data['elector_bin'] = pd.cut(merged_data['electores_circuito'], bins=10, labels=False)


# %%

# Agrupar por eleccion_id, cargo_id, distrito_id, seccion_id, circuito_id, votos_tipo, AGRUPACION_NOMBRE_ (es decir, 'Resto' para listas chicas)
df = info.groupby(['eleccion_id', 'eleccion_tag', 'cargo_id', 'cargo_tag', 'distrito_id', 'distrito_nombre', 'seccion_id', 'seccion_nombre', 'NOMDPTO', 'circuito_id', 'votos_tipo', 'agrupacion_nombre_']
                         )[['votos_cantidad', 'votos_porcentaje']].sum().unstack(['eleccion_id', 'eleccion_tag'])

# # Calcular las diferencias
diffc = df['votos_cantidad'].diff(-1, axis=1).dropna(axis = 1, how = 'all')
diffp = df['votos_porcentaje'].diff(-1, axis=1).dropna(axis = 1, how = 'all')

# Add the additional level to the diff DataFrames
diffc.columns = pd.MultiIndex.from_product([['cantidad_diff'], diffc.columns.get_level_values(0), diffc.columns.get_level_values(1)], names=[None, 'eleccion_id', 'eleccion_tag'])
diffp.columns = pd.MultiIndex.from_product([['porcentaje_diff'], diffp.columns.get_level_values(0), diffp.columns.get_level_values(1)], names=[None, 'eleccion_id', 'eleccion_tag'])
diff = pd.concat([diffc, diffp], axis=1)


diff_ = diff.stack(['eleccion_id', 'eleccion_tag'])
df_ = df.stack(['eleccion_id', 'eleccion_tag'])

data = pd.concat([df_, diff_], axis = 1)

# %%
data.head()


# %%
## Graficos differencia por caracteristicas del circuito

# %%
circuitos['cum_pct_by_electors'] = circuitos.sort_values('electores', ascending = False)['electores'].cumsum() / circuitos['electores'].sum()
circuitos['cum_pct_by_income'] = circuitos.sort_values('ingresos', ascending = True)['electores'].cumsum() / circuitos['electores'].sum()

circuitos.head()


# %%
votos_EPH_circuitos = data.reset_index().merge(circuitos)
votos_EPH_circuitos = votos_EPH_circuitos.merge(seccion_AGLO)

check = votos_EPH_circuitos.groupby(['eleccion_id', 'eleccion_tag', 'cargo_id', 'cargo_tag'])['votos_cantidad'].sum()
check

# %%
votos_EPH_circuitos.head()

# %%
votos_EPH_circuitos.eleccion_tag.value_counts()

# %%
# Checks
# votos_EPH_circuitos.groupby(pd.cut(votos_EPH_circuitos.cum_pct_by_electors, 10)).size()
# votos_EPH_circuitos.groupby(pd.cut(votos_EPH_circuitos.cum_pct_by_electors, 10)).votos_cantidad.sum()


# votos_EPH_circuitos.groupby(pd.cut(votos_EPH_circuitos.cum_pct_by_income, 10)).size()
# votos_EPH_circuitos.groupby(pd.cut(votos_EPH_circuitos.cum_pct_by_income, 8)).votos_cantidad.sum()

# %%


# %%


# %%


# %%
import matplotlib.pyplot as plt
import matplotlib.style as style
import seaborn as sns

# Set the theme of the plot and font settings
sns.set_style('whitegrid')  # Set style
sns.set_context('notebook', font_scale=0.8)  # Set context and adjust font size
plt.rcParams['font.family'] = "sans-serif"
plt.rcParams['axes.grid'] = True
plt.rcParams['grid.linewidth'] = 0.5
plt.rcParams['grid.linestyle'] = '--'
plt.rcParams['grid.alpha'] = 0.5

# Function to lighten colors
def lighten_color(hex_color, factor=0.5):
    """Lighten a color by a given factor."""
    # Convert hex to RGB
    hex_color = hex_color.lstrip('#')
    rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    # Calculate the new color
    new_rgb = tuple(int(c + (255 - c) * factor) for c in rgb)
    
    # Convert RGB back to hex
    new_hex = '#{:02x}{:02x}{:02x}'.format(*new_rgb)
    return new_hex

# Define the color palette
colors_dict = {
    'La Libertad Avanza': '#c63667',
    'Union Por La Patria': '#1175a9',
    'Juntos Por El Cambio': '#e1ce26'
}

# Create lighter shades for PASO results
colors_dict_light = {party: lighten_color(color) for party, color in colors_dict.items()}

# Combine colors for both elections
election_colors = {f'{party} - GRAL23n': colors_dict[party] for party in colors_dict}
election_colors.update({f'{party} - PASO23n': colors_dict_light[party] for party in colors_dict_light})


# %%

# Filter data for election 7, cargo 1
# data_filtered = votos_EPH_circuitos[(votos_EPH_circuitos['eleccion_id'] == 7) & (votos_EPH_circuitos['cargo_id'] == 1)].copy()
data_all = votos_EPH_circuitos[(votos_EPH_circuitos['cargo_id'] == 1)].copy()

# Create bins for cum_pct_by_income
bins = np.linspace(0, 1, 21)
data_all['income_bin'] = pd.cut(data_all['cum_pct_by_income'], bins, labels=False)

# Filter for the main parties and elections of interest
main_parties = ['La Libertad Avanza', 'Union Por La Patria', 'Juntos Por El Cambio']
elections_of_interest = ['GRAL23n', 'PASO23n']
data_all = data_all[(data_all['agrupacion_nombre_'].isin(main_parties)) & (data_all['eleccion_tag'].isin(elections_of_interest))]



# %%

# Create subplots
fig, axs = plt.subplots(1, len(main_parties), figsize=(15, 5), sharey=True)

# Loop over main parties and create boxplots
for i, party in enumerate(main_parties):
    data_filtered = data_all[(data_all['agrupacion_nombre_'] == party)]
    
    # Create the combined party - election tag for hue
    data_filtered['party_election'] = data_filtered['agrupacion_nombre_'] + ' - ' + data_filtered['eleccion_tag']
    
    # Set the order of the series
    hue_order = sorted(data_filtered['party_election'].unique(), key=lambda x: ('GRAL' in x, x))
    
    # Create boxplot for votos_porcentaje
    ax = sns.boxplot(x='income_bin', y='votos_porcentaje', hue='party_election', data=data_filtered,
                     palette=election_colors, linewidth=0.5, whis=1.5, fliersize=2, ax=axs[i],
                     hue_order=hue_order)
    ax.set_title(f'{party} - Voting Patterns')
    ax.set_xlabel('Income Level Bin')
    if i == 0:
        ax.set_ylabel('Percentage of Votes')
    else:
        ax.set_ylabel('')

    # ax = sns.boxplot(x='income_bin', y='porcentaje_diff', hue='party_election', data=data_filtered,
    #             palette=election_colors, linewidth=0.5, whis=1.5, fliersize=2, ax=axs[i],
    #              hue_order=hue_order)
    # ax.set_title('Voting Patterns Across Income Levels (Percentage Difference)')
    # ax.set_xlabel('Income Level Bin')
    # ax.set_ylabel('Percentage Difference')
    
    # Manually set alpha for box patches
    for patch in ax.patches:
        patch.set_alpha(0.75)

    # Set legend
    ax.legend(title='Party - Election', fontsize='small')

plt.tight_layout()
plt.show()

# %%


# %%

# Filter data for election 7, cargo 1
# data_filtered = votos_EPH_circuitos[(votos_EPH_circuitos['eleccion_id'] == 7) & (votos_EPH_circuitos['cargo_id'] == 1)].copy()
data_all = votos_EPH_circuitos[(votos_EPH_circuitos['cargo_id'] == 1)].copy()

# Create bins for cum_pct_by_income
bins = np.linspace(0, 1, 11)
data_all['income_bin'] = pd.cut(data_all['cum_pct_by_income'], bins, labels=False)

# Filter for the main parties and elections of interest
main_parties = ['La Libertad Avanza', 'Union Por La Patria', 'Juntos Por El Cambio']
elections_of_interest = ['GRAL23n', 'PASO23n']
data_all = data_all[(data_all['agrupacion_nombre_'].isin(main_parties)) & (data_all['eleccion_tag'].isin(elections_of_interest))]



# %%
# main_parties

# data_filtered = data_all[(data_all['agrupacion_nombre_'] == 'Juntos Por El Cambio') & (data_all['AGLOMERADO'] == 33)]

# # Create the combined party - election tag for hue
# data_filtered['party_election'] = data_filtered['agrupacion_nombre_'] + ' - ' + data_filtered['eleccion_tag']

# # Set the order of the series
# hue_order = sorted(data_filtered['party_election'].unique(), key=lambda x: ('GRAL' in x, x))



# # Create boxplot with modifications for votos_porcentaje
# plt.figure(figsize=(10, 6))
# ax = sns.boxplot(x='income_bin', y='votos_porcentaje', hue='party_election', data=data_filtered,
#                  palette=election_colors, linewidth=0.5, whis=1.5, fliersize=2,
#                  hue_order=hue_order)
# ax.set_title('Voting Patterns Across Income Levels (Percentage of Votes)')
# ax.set_xlabel('Income Level Bin')
# ax.set_ylabel('Percentage of Votes')

# # Manually set alpha for box patches
# for patch in ax.patches:
#     patch.set_alpha(0.75)

# # Set legend
# plt.legend(title='Party - Election', fontsize='small')
# plt.show()



# %%

# Create subplots
fig, axs = plt.subplots(1, len(main_parties), figsize=(15, 5), sharey=True)

# Loop over main parties and create boxplots
for i, party in enumerate(main_parties):
    data_filtered = data_all[(data_all['agrupacion_nombre_'] == party) & (data_all['AGLOMERADO'].isin([32, 33]))]
    
    # Create the combined party - election tag for hue
    data_filtered['party_election'] = data_filtered['agrupacion_nombre_'] + ' - ' + data_filtered['eleccion_tag']
    
    # Set the order of the series
    hue_order = sorted(data_filtered['party_election'].unique(), key=lambda x: ('GRAL' in x, x))
    
    # # Create boxplot for votos_porcentaje
    # ax = sns.boxplot(x='income_bin', y='votos_porcentaje', hue='party_election', data=data_filtered,
    #                  palette=election_colors, linewidth=0.5, whis=1.5, fliersize=2, ax=axs[i],
    #                  hue_order=hue_order)
    # ax.set_title(f'{party} - Voting Patterns')
    # ax.set_xlabel('Income Level Bin')
    # if i == 0:
    #     ax.set_ylabel('Percentage of Votes')
    # else:
    #     ax.set_ylabel('')

    ax = sns.boxplot(x='income_bin', y='porcentaje_diff', hue='party_election', data=data_filtered,
                palette=election_colors, linewidth=0.5, whis=1.5, fliersize=2, ax=axs[i],
                 hue_order=hue_order)
    ax.set_title('Voting Patterns Across Income Levels (Percentage Difference)')
    ax.set_xlabel('Income Level Bin')
    ax.set_ylabel('Percentage Difference')
    
    # Manually set alpha for box patches
    for patch in ax.patches:
        patch.set_alpha(0.75)

    # Set legend
    ax.legend(title='Party - Election', fontsize='small')

plt.tight_layout()
plt.show()

# %%

# Create subplots
fig, axs = plt.subplots(1, len(main_parties), figsize=(15, 5), sharey=True)

# Loop over main parties and create boxplots
for i, party in enumerate(main_parties):
    data_filtered = data_all[(data_all['agrupacion_nombre_'] == party) & (~data_all['AGLOMERADO'].isin([32, 33]))]
    
    # Create the combined party - election tag for hue
    data_filtered['party_election'] = data_filtered['agrupacion_nombre_'] + ' - ' + data_filtered['eleccion_tag']
    
    # Set the order of the series
    hue_order = sorted(data_filtered['party_election'].unique(), key=lambda x: ('GRAL' in x, x))
    
    # # Create boxplot for votos_porcentaje
    # ax = sns.boxplot(x='income_bin', y='votos_porcentaje', hue='party_election', data=data_filtered,
    #                  palette=election_colors, linewidth=0.5, whis=1.5, fliersize=2, ax=axs[i],
    #                  hue_order=hue_order)
    # ax.set_title(f'{party} - Voting Patterns')
    # ax.set_xlabel('Income Level Bin')
    # if i == 0:
    #     ax.set_ylabel('Percentage of Votes')
    # else:
    #     ax.set_ylabel('')

    ax = sns.boxplot(x='income_bin', y='porcentaje_diff', hue='party_election', data=data_filtered,
                palette=election_colors, linewidth=0.5, whis=1.5, fliersize=2, ax=axs[i],
                 hue_order=hue_order)
    ax.set_title('Voting Patterns Across Income Levels (Percentage Difference)')
    ax.set_xlabel('Income Level Bin')
    ax.set_ylabel('Percentage Difference')
    
    # Manually set alpha for box patches
    for patch in ax.patches:
        patch.set_alpha(0.75)

    # Set legend
    ax.legend(title='Party - Election', fontsize='small')

plt.tight_layout()
plt.show()

# %%
data_filtered = data_all.loc[data_all['AGLOMERADO'] == 33]#[(data_all['agrupacion_nombre_'] == 'Juntos Por El Cambio')]

# Create the combined party - election tag for hue
data_filtered['party_election'] = data_filtered['agrupacion_nombre_'] + ' - ' + data_filtered['eleccion_tag']

# Set the order of the series
hue_order = sorted(data_filtered['party_election'].unique(), key=lambda x: ('GRAL' in x, x))


# %%

# Create boxplot with modifications for porcentaje_diff
plt.figure(figsize=(10, 6))
ax = sns.boxplot(x='income_bin', y='porcentaje_diff', hue='party_election', data=data_filtered,
                 palette=election_colors, linewidth=0.5, whis=1.5, fliersize=2,
                 hue_order=hue_order)
ax.set_title('Voting Patterns Across Income Levels (Percentage Difference)')
ax.set_xlabel('Income Level Bin')
ax.set_ylabel('Percentage Difference')

# Manually set alpha for box patches
for patch in ax.patches:
    patch.set_alpha(0.75)

plt.ylim(-.15, .15)
# Set legend
plt.legend(title='Party - Election', fontsize='small')
plt.show()


# %%
data_filtered.columns

# %%
# Create boxplot with modifications
plt.figure(figsize=(10, 6))
ax = sns.boxplot(x='income_bin', y='porcentaje_diff', hue='party_election', data=data_filtered,
                 palette=election_colors, linewidth=0.5, whis=1.5, fliersize=2,
                 hue_order=hue_order)
ax.set_title('Voting Patterns Across Income Levels')
ax.set_xlabel('Income Level Bin')
ax.set_ylabel('Percentage of Votes')

# Manually set alpha for box patches
for patch in ax.patches:
    patch.set_alpha(0.75)

# Set legend
plt.legend(title='Party - Election', fontsize='small')
plt.show()

# %% [markdown]
# ## Seteo de Graficos

# %%
# info_plot.sort_values(by='votos_porcentaje', ascending=True).reset_index(drop = True)['votos_cantidad'].cumsum().plot()

# Line2D
from matplotlib.lines import Line2D


def weighted_quantile(values, quantiles, sample_weight=None, values_sorted=False):
    """Compute the weighted quantiles of a 1D numpy array."""
    values = np.array(values)
    quantiles = np.array(quantiles)
    if sample_weight is None:
        sample_weight = np.ones(len(values))
    sample_weight = np.array(sample_weight)
    assert np.all(quantiles >= 0) and np.all(quantiles <= 1), 'quantiles should be in [0, 1]'
    
    if not values_sorted:
        sorter = np.argsort(values)
        values = values[sorter]
        sample_weight = sample_weight[sorter]
    
    weighted_quantiles = np.cumsum(sample_weight) - 0.5 * sample_weight
    weighted_quantiles /= np.sum(sample_weight)
    
    return np.interp(quantiles, weighted_quantiles, values)



import matplotlib.pyplot as plt

def plot_scatter(fig, ax1, info, votos_tipo, agrupacion_nombre_, agrupacion_nombre, ingreso_medio, colors_dict, shade=False, alpha=0.5):
    info_plot = info.loc[(info.votos_tipo == votos_tipo) 
                         & (info['agrupacion_nombre_'] == agrupacion_nombre_) 
                         & (info['agrupacion_nombre'] == agrupacion_nombre)][['distrito_id', 'distrito_nombre', 'circuito_id', 'votos_cantidad', 'votos_porcentaje']]
    info_plot = info_plot.merge(ingreso_medio)

    color = 'gray' if shade else colors_dict.get(agrupacion_nombre_, 'black')

    scatter_plot = ax1.scatter(info_plot['ingresos'], 
               info_plot['votos_porcentaje'] * 100, 
               s=info_plot['votos_cantidad'] / 60,
               color=color,
               alpha=alpha, 
               edgecolors="w", 
               linewidth=0.5)

    ax1.set_xlabel('Ingreso mediano en el CIRCUITO (AR$)')
    ax1.set_ylabel('Votos Porcentaje (%)')
    ax1.set_xlim(50000, 350000)
    ax1.set_ylim(0, 75)
    ax1.set_title(f'Agrupación: {agrupacion_nombre_}', fontsize = 10)
    ax1.grid(True, which='both', linestyle='--', linewidth=0.5)

    # Format the x-axis in engineering notation
    ax1.xaxis.set_major_formatter(lambda x, _: f'{x*1e-3:.0f}k')

    return scatter_plot  # Return scatter plot object for legend


def plot_weighted_box(fig, ax, info, votos_tipo, agrupacion_nombre_, agrupacion_nombre, ingreso_medio, bins=np.arange(10000, 200000, 20000), wbins = False, nweighted=10, max_size = 100):
    info_plot = info.loc[(info.votos_tipo == votos_tipo) 
                         & (info['agrupacion_nombre_'] == agrupacion_nombre_) 
                         & (info['agrupacion_nombre'] == agrupacion_nombre)][['distrito_id', 'distrito_nombre', 'circuito_id', 'votos_cantidad', 'votos_porcentaje']]
    info_plot = info_plot.merge(ingreso_medio)
    info_plot_sorted = info_plot.sort_values(by='votos_porcentaje', ascending=True).reset_index(drop=True)

    if wbins == 'weighted':
        binning = pd.cut(info_plot_sorted.sort_values('ingresos')['votos_cantidad'].cumsum(), nweighted, retbins=True, labels=range(1, nweighted + 1))
        labels, bins = binning[0], binning[1]
        info_plot_sorted['x_bins'] = labels
    else:
        info_plot_sorted['x_bins'] = pd.cut(info_plot_sorted.ingresos, bins=bins, labels=False)

    grouped = info_plot_sorted.groupby('x_bins')
    q1_list, q2_list, q3_list, bin_means = [], [], [], []

    votos_cantidad_list = []
    for bin_num, group in grouped:
        if not group.votos_porcentaje.empty and not group.votos_cantidad.empty:
            q1_val = weighted_quantile(group.votos_porcentaje, 0.25, sample_weight=group.votos_cantidad)
            q2_val = weighted_quantile(group.votos_porcentaje, 0.5, sample_weight=group.votos_cantidad)
            q3_val = weighted_quantile(group.votos_porcentaje, 0.75, sample_weight=group.votos_cantidad)

            q1_list.append(q1_val)
            q2_list.append(q2_val)
            q3_list.append(q3_val)
            bin_means.append(group.ingresos.mean())  # Calculate mean of the bin for x-axis positioning
            votos_cantidad_list.append(group.votos_cantidad.sum())  # Store the sum of votos_cantidad for each group

        else:
            q1_list.append(None)
            q2_list.append(None)
            q3_list.append(None)
            bin_means.append(None)
            votos_cantidad_list.append(None)

    max_votos_cantidad = max(v for v in votos_cantidad_list if v is not None)  # Get the maximum votos_cantidad value
    # print(votos_cantidad_list)
    
    for x, (q1, q2, q3, votos_cantidad) in zip(bin_means, zip(q1_list, q2_list, q3_list, votos_cantidad_list)):
        if q1 is not None and q2 is not None and q3 is not None and votos_cantidad is not None:
            
            q1, q2, q3 = q1*100, q2*100, q3*100  # Convert to percentages
            errbarlw = 1 if wbins == 'weighted' else 1
            ax.plot([x, x], [q1, q3], color='.3', linewidth=errbarlw, alpha = .5)
            ax.plot([x-0.2*10000, x+0.2*10000], [q1, q1], color='.3', linewidth=errbarlw, alpha = .5)
            ax.plot([x-0.2*10000, x+0.2*10000], [q3, q3], color='.3', linewidth=errbarlw, alpha = .5)

            square_size = (votos_cantidad / max_votos_cantidad) * max_size; #print(square_size)
            
            ax.scatter(x, q2, s=square_size, c='w', edgecolors='black', marker='s', alpha=0.5, linewidths=0.5, zorder=10)        

    # We will rely on the scatter plot's X-axis labeling for income
    ax.set_xlabel('Ingreso mediano en el CIRCUITO (AR$)')
    ax.set_ylabel('Votos Porcentaje (%)')
    ax.grid(True, which='both', linestyle='--', linewidth=0.5, axis='y')
    # Format the x-axis in engineering notation
    ax.xaxis.set_major_formatter(lambda x, _: f'{x*1e-3:.0f}k')


# %%


# %%
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import colorsys

# Adjusting the colors to be more muted
def adjust_color(color, saturation_scale=0.6, lightness_scale=1.1):
    r, g, b = [x / 255.0 for x in color]
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    s *= saturation_scale
    l *= lightness_scale
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return (r, g, b)

colors_dict = {
    'La Libertad Avanza': adjust_color([255, 0, 255]),  # Adjusted Magenta
    'Union Por La Patria': adjust_color([0, 255, 255]), # Adjusted Cyan
    'Juntos Por El Cambio': adjust_color([255, 255, 0]) # Adjusted Yellow
}

# Create a new figure with 1 row and 3 columns for the subplots
fig, axs = plt.subplots(1, 3, figsize=(14, 4))

for ax, agrupacion in zip(axs, main_listas['agrupacion_nombre_'].unique()):
    if agrupacion in colors_dict:
        # Filter rows for the current political force
        rows_for_agrupacion = main_listas[main_listas['agrupacion_nombre_'] == agrupacion]
        
        # Initialize an empty list to collect legend handles and labels
        legend_elements = []  
        
        # Loop through each row in the filtered dataframe
        for _, row in rows_for_agrupacion.iterrows():
            # Plot weighted box
            # plot_weighted_box(fig, ax, info, row['votos_tipo'], agrupacion, row['agrupacion_nombre'], ingreso_medio, bins='weighted', nweighted=10)
            plot_weighted_box(fig, ax, info, row['votos_tipo'], agrupacion, row['agrupacion_nombre'], ingreso_medio, bins=np.arange(50000, 350000, 15000))
            
            # Plot scatter
            scatter_plot = plot_scatter(fig, ax, info, row['votos_tipo'], agrupacion, row['agrupacion_nombre'], ingreso_medio, colors_dict, shade=False, alpha=0.05)
            
            # Get color for the current political force
            color = colors_dict.get(agrupacion, 'black')
            
            # Add a legend element for the current political force
            legend_elements.append(Line2D([0], [0], marker='o', color='w', markerfacecolor=color, markersize=10, label=f"Lista {row['agrupacion_nombre']}"))

        # Add legend to the current subplot
        ax.legend(handles=legend_elements)

# # Adding a title to the entire plot
# title_font = {'fontweight': 'bold'}
# plt.suptitle('Votos (%) de las agrupaciones en las Generales 2023', fontdict=title_font, y=1.05)

# Showing the plot
plt.tight_layout()
plt.savefig('images/votos_vs_ingresosPASO23.jpg')
plt.show()


# %%
# # Aggregation
# print("Aggregating data...")
# ingreso_medio = persona_circuito.groupby(['distrito_id', 'seccion_id', 'seccion_nombre', 'circuito']).agg({'ingresos': 'median'}).reset_index()
# ingreso_medio['circuito_id'] = ingreso_medio['circuito'].astype(str).str.zfill(6)
# ingreso_medio.drop('circuito', axis=1, inplace=True)
# ingreso_medio[['distrito_id', 'seccion_id']] = ingreso_medio[['distrito_id', 'seccion_id']].astype('int64')

# circuitos = mesas.groupby(['distrito_id', 'seccion_id', 'circuito_id']).mesa_electores.agg(['sum', 'count']).reset_index().rename(columns={'sum': 'electores', 'count': 'mesas'})
# circuitos = circuitos.merge(ingreso_medio, on = ['distrito_id', 'seccion_id', 'circuito_id'], how = 'left')

# print("Done!")

# %%
# df = pd.read_csv('./../datos/info/radio_ref.csv')
# prov_region = df[['PROV_REF_ID', 'NOMPROV', 'Region']].drop_duplicates().sort_values(by='PROV_REF_ID')
# prov_region = prov_region.rename(columns = {'PROV_REF_ID': 'distrito_id'})
# # prov_region.groupby()
# # PROV_REF_ID	NOMPROV	Region

# %%
xx

# %%
info = circuitos_ppales.merge(data_circ.loc[(data_circ.cargo_id == 1) & (data_circ.eleccion_id == 7)])
info = main_listas.merge(info)
info = info.merge(prov_nams).merge(seccion_region, how = 'left')
info.head()


# %%
import matplotlib.pyplot as plt
import seaborn as sns

# %%
# Create a dictionary of colors for 'agrupacion_nombre_'
colors_dict = {
    'La Libertad Avanza': '#FF00FF',  # Magenta
    'Union Por La Patria': '#00FFFF', # Cyan
    'Juntos Por El Cambio': '#FFFF00' # Yellow
}    # ... add other agrupacion_nombre_ colors here ...



# %%
# votos_tipo = 'POSITIVO'
# agrupacion_nombre_ = 'Union Por La Patria'
# agrupacion_nombre = 3005

# info_plot = info.loc[(info.votos_tipo == votos_tipo) 
#                         & (info['agrupacion_nombre_'] == agrupacion_nombre_) 
#                         & (info['agrupacion_nombre'] == agrupacion_nombre)][['distrito_id', 'distrito_nombre', 'circuito_id', 'votos_cantidad', 'votos_porcentaje']]
# info_plot = info_plot.merge(ingreso_medio)
# info_plot_sorted = info_plot.sort_values(by='votos_porcentaje', ascending=True).reset_index(drop=True)


# %%


# info_plot_sorted['bins'] = pd.cut(info_plot_sorted.sort_values('ingresos')['votos_cantidad'].cumsum(), 10, labels = range(1, 11))
# info_plot_sorted.groupby('bins')['ingresos'].agg(['size', 'mean'])

# ingreso_medio.

# pd.qcut(, 10)

# %%


# Create a new figure with 1 row and 3 columns for the subplots
fig, axs = plt.subplots(1, 3, figsize=(14, 4))

for ax, agrupacion in zip(axs, main_listas['agrupacion_nombre_'].unique()):
    if agrupacion in colors_dict:
        rows_for_agrupacion = main_listas[main_listas['agrupacion_nombre_'] == agrupacion]
        
        legend_elements = []  # To collect legend handles and labels
        for idx, row in enumerate(rows_for_agrupacion.iterrows()):
            _, row = row
            should_shade = idx == 1
            # plot_weighted_box(fig, ax, info, row['votos_tipo'], agrupacion, row['agrupacion_nombre'], ingreso_medio, bins=np.arange(10000, 200000, 20000))
            plot_weighted_box(fig, ax, info, row['votos_tipo'], agrupacion, row['agrupacion_nombre'], ingreso_medio, bins='weighted', nweighted=10)
            
            scatter_plot = plot_scatter(fig, ax, info, row['votos_tipo'], agrupacion, row['agrupacion_nombre'], ingreso_medio, colors_dict, shade=should_shade, alpha=0.1)
            color = 'gray' if should_shade else colors_dict.get(agrupacion, 'black')
            legend_elements.append(Line2D([0], [0], marker='o', color='w', markerfacecolor=color, markersize=10, label=f"Lista {row['agrupacion_nombre']}"))

        # Add legend to ax after all plots are drawn
        ax.legend(handles=legend_elements)

# Adjust layout
plt.tight_layout()
# create if not exists
# import 
from pathlib import Path
Path('images').mkdir(parents=True, exist_ok=True)
# Save figure
plt.savefig('images/votos_vs_ingresosPASO23.jpg')
plt.show()


# %%
circuitos_list = ingreso_medio.loc[(ingreso_medio.ingresos < 100000)].circuito_id.unique()

# %%
antis = info.loc[(info.agrupacion_nombre == 'Union Por La Patria') & (info.votos_porcentaje < .16) & (info.circuito_id.isin(circuitos_list))].groupby('distrito_nombre')['votos_cantidad'].sum().sort_values()
antis

# %%
antis.sum()

# %%


# %%
# Extract unique regions
unique_regions = seccion_region.drop_duplicates(subset=['Region'])['Region']

# Loop over each unique region
for region in unique_regions:
    
    # Filter the data for the current region
    region_ids = seccion_region[seccion_region['Region'] == region]['distrito_id'].unique()
    filtered_info = info[info['distrito_id'].isin(region_ids)]

    # Create a new figure with 1 row and 3 columns for the subplots
    fig, axs = plt.subplots(1, 3, figsize=(14, 4))
    
    # Loop over each agrupacion within the filtered data
    for ax, agrupacion in zip(axs, main_listas['agrupacion_nombre_'].unique()):
        if agrupacion in colors_dict:
            rows_for_agrupacion = main_listas[main_listas['agrupacion_nombre_'] == agrupacion]
            
            legend_elements = []  # To collect legend handles and labels
            for idx, row in enumerate(rows_for_agrupacion.iterrows()):
                _, row = row
                should_shade = idx == 1
                plot_weighted_box(fig, ax, filtered_info, row['votos_tipo'], agrupacion, row['agrupacion_nombre'], ingreso_medio, bins='weighted', nweighted = 8)
                
                scatter_plot = plot_scatter(fig, ax, filtered_info, row['votos_tipo'], agrupacion, row['agrupacion_nombre'], ingreso_medio, colors_dict, shade=should_shade, alpha=0.1)
                color = 'gray' if should_shade else colors_dict.get(agrupacion, 'black')
                legend_elements.append(Line2D([0], [0], marker='o', color='w', markerfacecolor=color, markersize=10, label=f"Lista {row['agrupacion_nombre']}"))

            # Add legend to ax after all plots are drawn
            ax.legend(handles=legend_elements)
    
 # Set super title for the region
    plt.suptitle(f"Region: {region}", y=1.05)  # You might need to adjust the 'y' value for the best positioning
    
    # Adjust layout
    plt.tight_layout()
    
    # Save each region's figure separately
    plt.savefig(f'images/votos_vs_ingresosPASO23_region_{region}.jpg', bbox_inches='tight')  # Adding bbox_inches ensures everything is captured
    plt.show()


# %% [markdown]
# ## Mirar data de Region

# %%
# seccion_region.loc[seccion_region.Region == 'Pampeana'].sample(30)

# %% [markdown]
# seccion_region

# %%
# info.loc[info.distrito_id == 21][['distrito_id', 'seccion_id', 'distrito_nombre', 'NOMDPTO']].drop_duplicates()

# %%

# agrupacion_nombre_ = 'La Libertad Avanza'

filtered_info = info.loc[(info.votos_tipo == 'POSITIVO')][['distrito_id', 'distrito_nombre', 'seccion_nombre', 'circuito_id', 'agrupacion_nombre_', 'votos_cantidad', 'votos_porcentaje']]
filtered_info = filtered_info.merge(ingreso_medio)
    # info_plot_sorted = info_plot.sort_values(by='votos_porcentaje', ascending=True).reset_index(drop=True)
    # info_plot_sorted['x_bins'] = pd.cut(info_plot_sorted.ingresos, bins=bins, labels=False)


# Extract the desired columns
result_data = filtered_info[['distrito_id', 'distrito_nombre', 'seccion_id', 'seccion_nombre', 'circuito_id', 'agrupacion_nombre_',
                             'ingresos', 'votos_porcentaje', 'votos_cantidad']]


# %%
table = result_data.groupby(['distrito_id', 'seccion_id', 'circuito_id', 'agrupacion_nombre_'])[['ingresos', 'votos_porcentaje', 'votos_cantidad']].first()#.reset_index()
table = table.unstack(-1)
table = table.loc[(table[('votos_porcentaje', 'La Libertad Avanza')] > .35)]
table = table.loc[(table[('ingresos', 'La Libertad Avanza')] > 50000) & (table[('ingresos', 'La Libertad Avanza')] < 100000)]
sorted = table.sort_values(by = ('votos_cantidad', 'La Libertad Avanza'), ascending = False) 
principal = sorted.iloc[:len(sorted)//2].sort_index()
# x = sorted[('votos_cantidad', 'La Libertad Avanza')]
# (x.cumsum()/x.sum()).plot()
data = principal.stack().reset_index()

data = data.merge(info[['distrito_id', 'seccion_id', 'distrito_nombre', 'seccion_nombre', 'Region']].drop_duplicates(), on=['distrito_id', 'seccion_id'], how='left')



# %%
# Group by seccion, circuito, and agrupacion
grouped_data = data.groupby(['distrito_nombre', 'seccion_nombre', 'circuito_id', 'agrupacion_nombre_']).agg({
    'votos_cantidad': 'sum',
    'votos_porcentaje': 'mean'
}).reset_index()

# Pivot the table for better readability
pivot_data = grouped_data.pivot_table(index=['distrito_nombre', 'seccion_nombre', 'circuito_id'], 
                                      columns='agrupacion_nombre_', 
                                      values=['votos_cantidad', 'votos_porcentaje']).reset_index()

# # Extract and display summaries for each seccion
# summary_tables = {}
# unique_secciones = data['seccion_nombre'].unique()

# for seccion in unique_secciones:
#     summary_tables[seccion] = pivot_data[pivot_data['seccion_nombre'] == seccion]


# %%
secciones = filtered_info.groupby(['distrito_nombre', 'seccion_nombre'])['votos_cantidad'].sum().sort_values(ascending = False).reset_index()
secciones

import warnings
# # You have already created the grouped and pivot data.
# You have the grouped data as a DataFrame named secciones.

# Loop over the largest places
for idx, row in secciones.head(len(secciones)//2).head().iterrows():
    distrito = row['distrito_nombre']
    seccion = row['seccion_nombre']
    
    # Extract data for the current distrito and seccion
    summary_table = pivot_data[(pivot_data['distrito_nombre'] == distrito) & (pivot_data['seccion_nombre'] == seccion)]
    
    # Check if the summary table is not empty
    if len(summary_table) > 0:
        
        # For simplification, I'm removing the distrito and seccion columns, as they will be displayed in the title
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            summary_table = summary_table.drop(columns=['distrito_nombre', 'seccion_nombre'])

        # Multiply percentages by 100 and round to 1 decimal
        for col in summary_table.columns:
            if 'votos_porcentaje' in col:
                summary_table[col] = (summary_table[col] * 100).round(1)
        
        # Display the table
        print(f"Distrito: {distrito}, Seccion: {seccion}")
        display(summary_table.reset_index(drop = True))
        print("\n" + "="*100 + "\n")  # To separate the tables


# %%
# Extract unique distrito_id and corresponding distrito_nombre pairs
unique_distritos = info.drop_duplicates(subset=['distrito_id', 'distrito_nombre'])[['distrito_id', 'distrito_nombre']].tail()

# Loop over each unique distrito_id and its corresponding distrito_nombre
for _, distrito_row in unique_distritos.iterrows():
    distrito_id = distrito_row['distrito_id']
    distrito_nombre = distrito_row['distrito_nombre']

    # Filter the data for the current distrito_id
    filtered_info = info[info['distrito_id'] == distrito_id]

    # Create a new figure with 1 row and 3 columns for the subplots
    fig, axs = plt.subplots(1, 3, figsize=(14, 4))
    
    # Loop over each agrupacion within the filtered data
    for ax, agrupacion in zip(axs, main_listas['agrupacion_nombre_'].unique()):
        if agrupacion in colors_dict:
            rows_for_agrupacion = main_listas[main_listas['agrupacion_nombre_'] == agrupacion]
            
            legend_elements = []  # To collect legend handles and labels
            for idx, row in enumerate(rows_for_agrupacion.iterrows()):
                _, row = row
                should_shade = idx == 1
                plot_weighted_box(fig, ax, filtered_info, row['votos_tipo'], agrupacion, row['agrupacion_nombre'], ingreso_medio, bins='weighted', nweighted=5)
                
                scatter_plot = plot_scatter(fig, ax, filtered_info, row['votos_tipo'], agrupacion, row['agrupacion_nombre'], ingreso_medio, colors_dict, shade=should_shade, alpha = .35)
                color = 'gray' if should_shade else colors_dict.get(agrupacion, 'black')
                legend_elements.append(Line2D([0], [0], marker='o', color='w', markerfacecolor=color, markersize=10, label=f"Lista {row['agrupacion_nombre']}"))

            # Add legend to ax after all plots are drawn
            ax.legend(handles=legend_elements)


     # Set super title for the region
    plt.suptitle(f"Distrito: {distrito_nombre}", y=1.02)
    
    # Adjust layout
    plt.tight_layout()
    
    # Save each region's figure separately
    plt.savefig(f'images/votos_vs_ingresosPASO23_distrito_{distrito_nombre}.jpg', bbox_inches='tight')  # Adding bbox_inches ensures everything is captured)
    plt.show()


# %%
# for index, row in main_listas.iterrows():
#     # Check if the agrupacion_nombre_ has a color defined in colors_dict
#     # if row['agrupacion_nombre_'] in colors_dict:
#     # Create a new figure for each iteration
#     fig, axs = plt.subplots(1, 1, figsize=(6, 5))

#     plot_scatter(fig, axs, info, row['votos_tipo'], row['agrupacion_nombre_'], row['agrupacion_nombre'], ingreso_medio, colors_dict)
#     plot_weighted_box(fig, axs, info, row['votos_tipo'], row['agrupacion_nombre_'], row['agrupacion_nombre'], ingreso_medio)

#     plt.tight_layout()
#     plt.show()

# %%
info

# %%


# %%
xx

# %%
import pandas as pd

import math

def harmonize_agrupacion_id(agrupacion_id):
    if pd.isna(agrupacion_id):
        return "000000"
    else:
        try:
            # Attempt to convert string to float and then to integer
            return str(int(float(agrupacion_id))).zfill(6)
        except ValueError:
            # If conversion fails, return original string value
            return agrupacion_id

# %%
# Read the CSV file into a DataFrame
df = pd.read_csv('./../datos/BD/votos_eleccion_17_table.csv') 


# Filter the DataFrame using loc and the condition (for example, where 'cargo_id' is 1 or 3)
df = df.loc[df['cargo_id'].isin([1, 3])]
data = df
data['agrupacion_id'] = data['agrupacion_id'].apply(harmonize_agrupacion_id)

# %%
cargo = pd.read_csv('./../datos/BD/cargo_table.csv')

agrup_lista = pd.read_csv('./../datos/BD/agrupacion_lista_table.csv')
agrup_lista['agrupacion_id'] = agrup_lista['agrupacion_id'].apply(harmonize_agrupacion_id)
agrup_lista['agrupacion_nombre'] = agrup_lista['agrupacion_nombre'].apply(harmonize_agrupacion_id)
agrup_lista


simil_nombre = agrup_lista.groupby(['eleccion_id', 'distrito_id', 'distrito_nombre', 'agrupacion_id']).agrupacion_nombre.first().reset_index()

merged_data = data.merge(simil_nombre)

# %%

merged_data['agrupacion_nombre'] = merged_data['agrupacion_nombre'].replace('CAMBIEMOS BUENOS AIRES', 'CAMBIEMOS')
merged_data['agrupacion_nombre'] = merged_data['agrupacion_nombre'].replace('JUNTOS', 'JUNTOS POR EL CAMBIO', regex=False)
merged_data['agrupacion_nombre'] = merged_data['agrupacion_nombre'].str.title()




# %%
out = merged_data.groupby(['eleccion_id', 'cargo_id', 'agrupacion_nombre', 'agrupacion_nombre', 'votos_tipo'])[['votos_cantidad']].sum().reset_index()
out


# %%
n = 6
main = out.groupby(['eleccion_id', 'cargo_id', 'votos_tipo']).apply(lambda x: x.nlargest(n, 'votos_cantidad')).reset_index(drop=True).rename(columns={'votos_cantidad': 'votos_nacional'})
main


# %%


# %%
data_copy = data.copy()

# %%
data_copy['agrupacion_nombre'] = data_copy['agrupacion_nombre'].replace('CAMBIEMOS BUENOS AIRES', 'CAMBIEMOS')
data_copy['agrupacion_nombre'] = data_copy['agrupacion_nombre'].replace('JUNTOS', 'JUNTOS POR EL CAMBIO')
data_copy['agrupacion_nombre'] = data_copy['agrupacion_nombre'].str.title()



data_copy = data_copy.merge(main, how = 'left')

## Limpiar

data_copy['agrupacion_nombre'] = data_copy['agrupacion_nombre'].str.title().str.strip()

data_copy['agrupacion_nombre_'] = data_copy['agrupacion_nombre'].mask(data_copy['votos_nacional'].isnull()).fillna('Resto')

data_aggregated = data_copy.groupby(['distrito_id', 'distrito_nombre', 'seccion_id', 'circuito_id', 'mesa_id', 'cargo_id', 'agrupacion_nombre_', 'votos_tipo', 'eleccion_id'])['votos_cantidad'].sum()
data_aggregated = data_aggregated.reset_index()

# %%
## Seccion_id no es necesario, alcanza con provincia-circuito. Pero lo agregamos porque a traves de los circuitos se relaciona el seccion_id con el id de deptos en IGN.
data_circ = data_aggregated.groupby(['eleccion_id', 'cargo_id', 'agrupacion_nombre_', 'votos_tipo', 'distrito_id', 'distrito_nombre', 'seccion_id', 'circuito_id'])[['votos_cantidad']].sum()
# data_circ.to_csv('./../datos/out/votos_agrup_circ.csv')
data_circ.groupby('cargo_id').votos_cantidad.sum()

# %%
claves_dptos = pd.read_csv('./../datos/BD/claves_dptos_ref.csv')
claves_dptos = claves_dptos.loc[~claves_dptos.codprov.isna()].astype({'codprov': 'Int64', 'coddepto' : 'Int64', 'IN1' : 'Int64'})
claves_dptos['codprov'] = claves_dptos['codprov'].astype(str).str.zfill(2)
claves_dptos['coddepto'] = claves_dptos['coddepto'].astype(str).str.zfill(3)
claves_dptos['IN1'] = claves_dptos['IN1'].astype(str).str.zfill(5)
claves_dptos.loc[(claves_dptos.seccion_nombre == 'La Plata'), 'IN1'] = '06441'
claves_dptos.head()

prov_ids = claves_dptos.copy()
prov_ids['in1_prov'] = prov_ids['IN1'].astype(str).str[:2]
prov_ids = prov_ids[['distrito_id', 'distrito_nombre', 'in1_prov']].drop_duplicates().reset_index(drop=True)

# prov_ids = pd.read_csv('./../datos/info/radio_ref.csv')[['PROV_REF_ID', 'IDPROV']].drop_duplicates().rename(columns = {'IDPROV': 'in1_prov', 'PROV_REF_ID': 'distrito_id'}).reset_index(drop = True)
# prov_ids['in1_prov'] = prov_ids['in1_prov'].astype(str).str.zfill(2)
# prov_ids.head()

eleccion_tags = pd.read_csv('./../datos/BD/eleccion_tags.csv')


# %%
# data_circ = pd.read_csv('./../datos/out/votos_circ.csv').merge(prov_ids)
data_circ = pd.read_csv('./../datos/out/votos_agrup_circ.csv').merge(prov_ids)
# data_circ['agrupacion_nombre_'] = data_circ['agrupacion_nombre_'].fillna('NO POSITIVOS')

# Guardar ref provs - dptos - circs
dist_secc_circ = data_circ.copy() # save for later

# data_circ
data_circ = data_circ.merge(eleccion_tags).merge(cargo)


# Group by 'eleccion_tag', 'cargo_tag', and 'in1_prov', and calculate the sum of 'votos_cantidad', divide for PCT
sum_votes = data_circ.groupby(['eleccion_tag', 'cargo_tag', 'in1_prov', 'votos_tipo', 'circuito_id'])['votos_cantidad'].transform('sum')
data_circ['votos_porcentaje'] = data_circ['votos_cantidad'] / sum_votes


data_circ = data_circ.set_index(['distrito_id', 'distrito_nombre', 'circuito_id', 'eleccion_tag', 'cargo_tag', 'agrupacion_nombre_', 'votos_tipo'])


data_circ_table_cnt = data_circ['votos_cantidad'].unstack(['eleccion_tag', 'cargo_tag', 'votos_tipo', 'agrupacion_nombre_'])
data_circ_table_pct = data_circ['votos_porcentaje'].unstack(['eleccion_tag', 'cargo_tag', 'votos_tipo', 'agrupacion_nombre_'])


# %%

data_circ_geoms_cnt.to_file('./../datos/geojson/votos_cnt_circ.geojson', driver='GeoJSON') # Save the GeoDataFrame to GeoJSON
data_circ_geoms_pct.to_file('./../datos/geojson/votos_pct_circ.geojson', driver='GeoJSON') # Save the GeoDataFrame to GeoJSON


data_circ_geoms_cnt.to_file('./../datos/geojson/votos_cnt_circ.geojson', driver='GeoJSON') # Save the GeoDataFrame to GeoJSON
data_circ_geoms_pct.to_file('./../datos/geojson/votos_pct_circ.geojson', driver='GeoJSON') # Save the GeoDataFrame to GeoJSON


data_circ_geoms_cnt.to_file('./../datos/geojson/votos_cnt_circ.geojson', driver='GeoJSON') # Save the GeoDataFrame to GeoJSON
data_circ_geoms_pct.to_file('./../datos/geojson/votos_pct_circ.geojson', driver='GeoJSON') # Save the GeoDataFrame to GeoJSON


