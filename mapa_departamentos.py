import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from zipfile import ZipFile
import os
import tempfile

st.set_page_config(page_title="Departamentos de Colombia", layout="wide")

st.title("🗺️ Mapa Interactivo de Departamentos de Colombia")

# Función para descomprimir y cargar el shapefile
@st.cache_data
def cargar_shapefile(zip_path):
    with tempfile.TemporaryDirectory() as tmpdir:
        with ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tmpdir)
            shp_files = [f for f in os.listdir(tmpdir) if f.endswith(".shp")]
            if not shp_files:
                st.error("No se encontró un .shp en el ZIP")
                return None
            shp_path = os.path.join(tmpdir, shp_files[0])
            gdf = gpd.read_file(shp_path)
            if gdf.crs != "EPSG:4326":
                gdf = gdf.to_crs(epsg=4326)
            return gdf.copy()

# Cargar shapefile desde archivo local (puedes poner el zip en el mismo directorio del script)
zip_file = "Departamentos.zip"
gdf = cargar_shapefile(zip_file)

# Verifica que se cargó bien
if gdf is None:
    st.stop()

# ---- Barra lateral ----
st.sidebar.header("🎯 Selección de Departamentos")
departamentos = gdf["NOMBRE_DEP"].sort_values().unique().tolist()
seleccionados = st.sidebar.multiselect("Selecciona departamentos", departamentos)
generar_mapa = st.sidebar.button("📍 Generar mapa")

# ---- Lógica del visor ----
if generar_mapa and seleccionados:
    m = folium.Map(location=[4.5, -74], zoom_start=5)

    for _, row in gdf.iterrows():
        if row["NOMBRE_DEP"] in seleccionados:
            color = "blue"
        else:
            color = "lightgray"

        folium.GeoJson(
            row["geometry"],
            name=row["NOMBRE_DEP"],
            style_function=lambda x, color=color: {
                "fillColor": color,
                "color": "black",
                "weight": 1,
                "fillOpacity": 0.5,
            },
            tooltip=row["NOMBRE_DEP"]
        ).add_to(m)

    st_folium(m, width=1000, height=600)

elif not generar_mapa:
    st.info("👈 Usa la barra lateral para seleccionar departamentos y presiona **Generar mapa**.")
elif generar_mapa and not seleccionados:
    st.warning("⚠️ No has seleccionado ningún departamento.")
