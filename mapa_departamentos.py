import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from zipfile import ZipFile
import os
import tempfile

st.set_page_config(page_title="Departamentos de Colombia", layout="wide")
st.title("🗺️ Mapa Interactivo de Departamentos de Colombia")

@st.cache_data
def cargar_shapefile(zip_path):
    st.info(f"Intentando cargar: {zip_path}") # Debug: Ruta del ZIP
    if not os.path.exists(zip_path):
        st.error(f"¡Error! No se encontró el archivo ZIP en: {zip_path}")
        return None
    with tempfile.TemporaryDirectory() as tmpdir:
        st.info(f"Descomprimiendo en: {tmpdir}") # Debug: Directorio temporal
        with ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tmpdir)
        shp_files = [f for f in os.listdir(tmpdir) if f.endswith(".shp")]
        if not shp_files:
            st.error("No se encontró un .shp en el ZIP")
            st.write(f"Archivos encontrados en ZIP: {os.listdir(tmpdir)}") # Debug: Contenido del ZIP
            return None
        shp_path = os.path.join(tmpdir, shp_files[0])
        st.info(f"Cargando SHP: {shp_path}") # Debug: Ruta del SHP
        try:
            gdf = gpd.read_file(shp_path)
            st.info(f"Shapefile cargado exitosamente. CRS inicial: {gdf.crs}") # Debug: CRS inicial
            if gdf.crs != "EPSG:4326":
                gdf = gdf.to_crs(epsg=4326)
                st.info(f"CRS reproyectado a: {gdf.crs}") # Debug: CRS reproyectado
            return gdf.copy()
        except Exception as e:
            st.error(f"Error al leer shapefile con GeoPandas: {e}")
            return None

# Cargar shapefile
zip_file = "Departamentos.zip"
gdf = cargar_shapefile(zip_file)
if gdf is None:
    st.stop()
else:
    st.success(f"GeoDataFrame cargado con {len(gdf)} departamentos.") # Debug: Éxito en la carga

# Resto del código (barra lateral y visualización del mapa)
st.sidebar.header("🎯 Selección de Departamentos")
departamentos = gdf["NOMBRE_DEP"].sort_values().unique().tolist()
seleccionados = st.sidebar.multiselect("Selecciona departamentos", departamentos)
generar_mapa = st.sidebar.button("📍 Generar mapa")

# Mostrar mapa
if generar_mapa and seleccionados:
    st.info(f"Generando mapa para {len(seleccionados)} departamentos seleccionados.") # Debug: Selección
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
