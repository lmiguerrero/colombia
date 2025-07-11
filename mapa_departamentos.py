import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from zipfile import ZipFile
import os

# Título
st.title("🗺️ Mapa Interactivo de Departamentos de Colombia")

# Descomprimir shapefile si no está descomprimido
zip_path = "Departamentos.zip"
extract_path = "shapefile"

if not os.path.exists(extract_path):
    with ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)

# Leer shapefile
shapefile_path = [f for f in os.listdir(extract_path) if f.endswith('.shp')][0]
gdf = gpd.read_file(os.path.join(extract_path, shapefile_path))

# Selección de departamentos
deptos = gdf["NOMBRE_DEP"].sort_values().unique().tolist()
seleccionados = st.multiselect("Selecciona uno o más departamentos:", deptos)

# Crear mapa base
m = folium.Map(location=[4.5, -74], zoom_start=5)

# Agregar polígonos al mapa
for _, row in gdf.iterrows():
    color = "blue" if row["NOMBRE_DEP"] in seleccionados else "lightgray"
    folium.GeoJson(
        row["geometry"],
        name=row["NOMBRE_DEP"],
        style_function=lambda x, color=color: {
            "fillColor": color,
            "color": "black",
            "weight": 1,
            "fillOpacity": 0.6,
        },
        tooltip=row["NOMBRE_DEP"]
    ).add_to(m)

# Mostrar el mapa en Streamlit
st_folium(m, width=700, height=500)
