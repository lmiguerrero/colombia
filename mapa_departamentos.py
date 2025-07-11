import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from zipfile import ZipFile
import os

# Título principal
st.title("🗺️ Mapa Interactivo de Departamentos de Colombia")

# Ruta al zip
zip_path = "Departamentos.zip"
extract_path = "shapefile"

# Descomprimir solo una vez
if not os.path.exists(extract_path):
    with ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)

# Cargar shapefile
shp_file = [f for f in os.listdir(extract_path) if f.endswith(".shp")][0]
gdf = gpd.read_file(os.path.join(extract_path, shp_file))

# Opciones en la barra lateral
st.sidebar.header("🎯 Selección de Departamentos")
deptos = gdf["NOMBRE_DEP"].sort_values().unique().tolist()
seleccionados = st.sidebar.multiselect("Selecciona departamentos", deptos)

# Botón de acción
generar = st.sidebar.button("📍 Generar mapa")

# Mostrar mapa si se presiona el botón
if generar and seleccionados:
    # Crear mapa base
    m = folium.Map(location=[4.5, -74], zoom_start=5)

    # Agregar polígonos
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

    # Mostrar mapa
    st_folium(m, width=700, height=500)

elif not generar:
    st.info("👈 Usa la barra lateral para seleccionar departamentos y presiona **Generar mapa**.")
elif generar and not seleccionados:
    st.warning("⚠️ No has seleccionado ningún departamento.")
