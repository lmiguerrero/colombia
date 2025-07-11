import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from zipfile import ZipFile
import os
import tempfile

st.set_page_config(page_title="Departamentos de Colombia", layout="wide")
st.title("🗺️ Mapa Interactivo de Departamentos de Colombia")

# Función para cargar shapefile desde zip
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

# Cargar shapefile
zip_file = "Departamentos.zip"
gdf = cargar_shapefile(zip_file)
if gdf is None:
    st.stop()

# Barra lateral
st.sidebar.header("🎯 Selección de Departamentos")
departamentos = gdf["NOMBRE_DEP"].sort_values().unique().tolist()
seleccionados = st.sidebar.multiselect("Selecciona departamentos", departamentos)
generar_mapa = st.sidebar.button("📍 Generar mapa")

# Mostrar mapa
if generar_mapa and seleccionados:
    gdf_sel = gdf.copy()
    gdf_sel["seleccionado"] = gdf_sel["NOMBRE_DEP"].isin(seleccionados)

    m = folium.Map(location=[4.5, -74], zoom_start=5)

    folium.GeoJson(
        gdf_sel,
        style_function=lambda feature: {
            "fillColor": "blue" if feature["properties"]["seleccionado"] else "lightgray",
            "color": "black",
            "weight": 1,
            "fillOpacity": 0.6,
        },
        tooltip=folium.GeoJsonTooltip(fields=["NOMBRE_DEP"], aliases=["Departamento:"])
    ).add_to(m)

    st_folium(m, width=1000, height=600)

elif not generar_mapa:
    st.info("👈 Usa la barra lateral para seleccionar departamentos y presiona **Generar mapa**.")
elif generar_mapa and not seleccionados:
    st.warning("⚠️ No has seleccionado ningún departamento.")
