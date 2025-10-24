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


# %% [markdown]
# ## Datos Pobreza

# %%
import numpy as np

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
df['ingresos'] = 25 * (np.power(10, df['P47T_persona']) - 1)
df['ingresos'] = df['ingresos'].round(-3).astype(int)

# Load and combine geo data
print("Loading and combining geo data...")
geo_files = [
    './../../indice-pobreza-UBA/data/Pobreza/geo_households_sample0.02_2022_ARG.csv',
    './../../indice-pobreza-UBA/data/Pobreza/geo_households_sample0.02_2023_ARG.csv'
]
geo = pd.concat([pd.read_csv(file) for file in geo_files])
hogar_circuito = geo[['HOGAR_REF_ID', 'distrito_id', 'seccion_id', 'seccion_nombre', 'circuito']].drop_duplicates()

# Merge data
print("Merging data...")
persona_circuito = df.merge(hogar_circuito)

# Aggregation
print("Aggregating data...")
ingreso_medio = persona_circuito.groupby(['distrito_id', 'seccion_id', 'seccion_nombre', 'circuito']).agg({'ingresos': 'median'}).reset_index()
ingreso_medio['circuito_id'] = ingreso_medio['circuito'].astype(str).str.zfill(6)
ingreso_medio.drop('circuito', axis=1, inplace=True)
ingreso_medio[['distrito_id', 'seccion_id']] = ingreso_medio[['distrito_id', 'seccion_id']].astype('int64')

print("Done!")


# %%
ingreso_medio08 = pd.read_csv('./ingreso_medio_202308.csv')
ingreso_medio10 = pd.read_csv('./ingreso_medio_202310.csv')
# ingreso_medio.to_csv('./ingreso_medio_202308.csv', index=False)
ingreso_medio = ingreso_medio08.merge(ingreso_medio10, on = ['distrito_id', 'seccion_id', 'seccion_nombre', 'circuito_id'], suffixes = ('_08', '_10'))
ingreso_medio['ingresos'] = (ingreso_medio['ingresos_08'] + ingreso_medio['ingresos_10']) / 2

mesas = pd.read_csv('./../datos/BD151923/mesas_table.csv')
mesas.head()

circuitos = mesas.groupby(['distrito_id', 'seccion_id', 'circuito_id']).mesa_electores.agg(['sum', 'count']).reset_index().rename(columns={'sum': 'electores', 'count': 'mesas'})

circuitos = circuitos.merge(ingreso_medio, on = ['distrito_id', 'seccion_id', 'circuito_id'])


# %%
circuitos['error'] = abs(circuitos['ingresos_10'] - circuitos['ingresos_08'])
circuitos['Error_bin'] = pd.qcut(circuitos['error'], 5, labels=['1', '6', '13', '25', '50'])#.value_counts()

# %%
circuitos.groupby('Error_bin')[['electores', 'error']].describe().round(-3).astype(int)

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


# %%


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
# ## Unir Ingresos con votos

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
# main_listas

# %%
# main_listas = info_table['votos_cantidad'].sum().sort_values(ascending=False).head(10)
main_listas = main_listas.index.to_frame().reset_index(drop=True)
main_listas


# %% [markdown]
# ### Merge

# %%
# import geopandas as gpd
# circs_ref = gpd.read_file('./../datos/geojson/circs_ref.geojson')


# %%
# radio_region.COD_2010.unique()

# %%
# radios_circuitos_secciones.COD_2010.unique()

# %%
radio_region = pd.read_csv('./../datos/info/radio_ref.csv', usecols = ['radio', 'NOMDPTO', 'Region'])
radio_region['COD_2010'] = radio_region['radio'].astype(str).str.zfill(9)
radios_circuitos_secciones = pd.read_csv('./../datos/info/radios_circuitos_secciones_ref.csv')[['COD_2010', 'distrito_id', 'seccion_id', 'seccion_nombre']]

merge = radios_circuitos_secciones.merge(radio_region, on = 'COD_2010', how = 'left')

seccion_region = merge.drop(['COD_2010', 'radio'], axis = 1).drop_duplicates()
seccion_region = seccion_region.groupby(['distrito_id', 'seccion_id', 'seccion_nombre']).first()
seccion_region = seccion_region.reset_index()
seccion_region


# %%
# df = pd.read_csv('./../datos/info/DPTO_PROV_Region.csv')
# df#.PROV.unique()

# %%
# df = pd.read_csv('./../datos/info/radio_ref.csv')
# prov_region = df[['PROV_REF_ID', 'NOMPROV', 'Region']].drop_duplicates().sort_values(by='PROV_REF_ID')
# prov_region = prov_region.rename(columns = {'PROV_REF_ID': 'distrito_id'})
# # prov_region.groupby()
# # PROV_REF_ID	NOMPROV	Region

# %%
prov_nams = pd.read_csv(f'{BD_path}/distrito_table.csv')

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
               c=color,
               alpha=alpha, 
               edgecolors="w", 
               linewidth=0.5)

    ax1.set_xlabel('Ingreso mediano en el CIRCUITO (AR$)')
    ax1.set_ylabel('Votos Porcentaje (%)')
    ax1.set_xlim(0, 200000)
    ax1.set_ylim(0, 70)
    ax1.set_title(f'Agrupación: {agrupacion_nombre_}', fontsize = 10)
    ax1.grid(True, which='both', linestyle='--', linewidth=0.5)

    # Format the x-axis in engineering notation
    ax1.xaxis.set_major_formatter(lambda x, _: f'{x*1e-3:.0f}k')

    return scatter_plot  # Return scatter plot object for legend


def plot_weighted_box(fig, ax, info, votos_tipo, agrupacion_nombre_, agrupacion_nombre, ingreso_medio, bins=np.arange(10000, 200000, 20000), nweighted=10):
    info_plot = info.loc[(info.votos_tipo == votos_tipo) 
                         & (info['agrupacion_nombre_'] == agrupacion_nombre_) 
                         & (info['agrupacion_nombre'] == agrupacion_nombre)][['distrito_id', 'distrito_nombre', 'circuito_id', 'votos_cantidad', 'votos_porcentaje']]
    info_plot = info_plot.merge(ingreso_medio)
    info_plot_sorted = info_plot.sort_values(by='votos_porcentaje', ascending=True).reset_index(drop=True)

    if bins == 'weighted':
        binning = pd.cut(info_plot_sorted.sort_values('ingresos')['votos_cantidad'].cumsum(), nweighted, retbins=True, labels=range(1, nweighted + 1))
        labels, bins = binning[0], binning[1]
        info_plot_sorted['x_bins'] = labels
    else:
        info_plot_sorted['x_bins'] = pd.cut(info_plot_sorted.ingresos, bins=bins, labels=False)

    grouped = info_plot_sorted.groupby('x_bins')
    q1_list, q2_list, q3_list, bin_means = [], [], [], []

    for bin_num, group in grouped:
        if not group.votos_porcentaje.empty and not group.votos_cantidad.empty:
            q1_val = weighted_quantile(group.votos_porcentaje, 0.25, sample_weight=group.votos_cantidad)
            q2_val = weighted_quantile(group.votos_porcentaje, 0.5, sample_weight=group.votos_cantidad)
            q3_val = weighted_quantile(group.votos_porcentaje, 0.75, sample_weight=group.votos_cantidad)
            q1_list.append(q1_val)
            q2_list.append(q2_val)
            q3_list.append(q3_val)
            bin_means.append(group.ingresos.mean())  # Calculate mean of the bin for x-axis positioning
        else:
            q1_list.append(None)
            q2_list.append(None)
            q3_list.append(None)
            bin_means.append(None)

    for x, (q1, q2, q3) in zip(bin_means, zip(q1_list, q2_list, q3_list)):
        q1, q2, q3 = q1*100, q2*100, q3*100  # Convert to percentages
        ax.plot([x, x], [q1, q3], color='.3', linewidth=1.5, alpha = .5)
        ax.plot([x-0.2*10000, x+0.2*10000], [q1, q1], color='.3', linewidth=1.5, alpha = .5)
        ax.plot([x-0.2*10000, x+0.2*10000], [q3, q3], color='.3', linewidth=1.5, alpha = .5)
        ax.plot(x, q2, 'k*', alpha = .5)
    # We will rely on the scatter plot's X-axis labeling for income
    ax.set_xlabel('Ingreso mediano en el CIRCUITO (AR$)')
    ax.set_ylabel('Votos Porcentaje (%)')
    ax.grid(True, which='both', linestyle='--', linewidth=0.5, axis='y')
    # Format the x-axis in engineering notation
    ax.xaxis.set_major_formatter(lambda x, _: f'{x*1e-3:.0f}k')


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


