# mapa_departamentos.py

import geopandas as gpd
import streamlit as st
import folium
from streamlit_folium import st_folium

# Cargar shapefile (ajusta la ruta al archivo .shp)
shp_path = "limites_departamentales.shp"
gdf = gpd.read_file(shp_path)

# Convertir nombres de departamento a lista para selección
deptos = gdf["NOMBRE_DEP"].sort_values().unique().tolist()

# Selección de departamentos
seleccion = st.multiselect("Selecciona departamentos", deptos)

# Crear el mapa
m = folium.Map(location=[4.5, -74], zoom_start=5)

# Agregar todos los departamentos
for _, row in gdf.iterrows():
    color = "red" if row["NOMBRE_DEP"] in seleccion else "lightgray"
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

# Mostrar el mapa
st_folium(m, width=700, height=500)
