import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from zipfile import ZipFile
import os
import tempfile
import requests

st.set_page_config(page_title="Departamentos de Colombia", layout="wide")
st.title("🗺️ Mapa Interactivo de Departamentos de Colombia")

# --- Inicializar st.session_state ---
if 'mapa_generado' not in st.session_state:
    st.session_state.mapa_generado = False
if 'departamentos_seleccionados_previos' not in st.session_state:
    st.session_state.departamentos_seleccionados_previos = []

# Función para cargar shapefile (adaptada para URL)
@st.cache_data
def cargar_shapefile(source_path_or_url):
    st.info(f"Attempting to load data from: {source_path_or_url}")
    temp_zip_file = None
    try:
        # Download the file if it's a URL
        if source_path_or_url.startswith("http://") or source_path_or_url.startswith("https://"):
            response = requests.get(source_path_or_url, stream=True)
            response.raise_for_status() # Raise an error for bad HTTP status codes
            temp_zip_file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
            with temp_zip_file as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            zip_path = temp_zip_file.name
            st.success("ZIP file temporarily downloaded.")
        else: # If it's a local file path
            zip_path = source_path_or_url
            if not os.path.exists(zip_path):
                st.error(f"Error! Local ZIP file not found at: {zip_path}")
                return None

        # Unzip and read process (same as before)
        with tempfile.TemporaryDirectory() as tmpdir:
            with ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdir)
            shp_files = [f for f in os.listdir(tmpdir) if f.endswith(".shp")]
            if not shp_files:
                st.error("No .shp file found in the ZIP.")
                st.write(f"Files found in ZIP: {os.listdir(tmpdir)}")
                return None
            shp_path = os.path.join(tmpdir, shp_files[0])
            gdf = gpd.read_file(shp_path)
            if gdf.crs != "EPSG:4326":
                gdf = gdf.to_crs(epsg=4326)
            st.success(f"Shapefile loaded successfully. CRS: {gdf.crs}")
            return gdf.copy()
    except requests.exceptions.RequestException as e:
        st.error(f"Error downloading ZIP file from URL: {e}")
        return None
    except Exception as e:
        st.error(f"Unexpected error during shapefile loading: {e}")
        return None
    finally:
        if temp_zip_file and os.path.exists(temp_zip_file.name):
            os.unlink(temp_zip_file.name) # Ensure the temporary file is deleted

# --- CORRECTED URL HERE ---
zip_file = "https://raw.githubusercontent.com/lmiguerrero/colombia/main/Departamentos.zip"
gdf = cargar_shapefile(zip_file)
if gdf is None:
    st.stop()
else:
    st.success(f"GeoDataFrame loaded with {len(gdf)} departments.")

# Sidebar
st.sidebar.header("🎯 Selección de Departamentos")
departamentos = gdf["NOMBRE_DEP"].sort_values().unique().tolist()
seleccionados = st.sidebar.multiselect("Selecciona departamentos", departamentos, default=st.session_state.departamentos_seleccionados_previos)

if st.sidebar.button("📍 Generar mapa"):
    if seleccionados:
        st.session_state.mapa_generado = True
        st.session_state.departamentos_seleccionados_previos = seleccionados
    else:
        st.session_state.mapa_generado = False
        st.warning("⚠️ No has seleccionado ningún departamento.")

if set(seleccionados) != set(st.session_state.departamentos_seleccionados_previos) and seleccionados:
    st.session_state.mapa_generado = True
    st.session_state.departamentos_seleccionados_previos = seleccionados
elif not seleccionados and st.session_state.mapa_generado:
    st.session_state.mapa_generado = False
    st.session_state.departamentos_seleccionados_previos = []

# Show map based on session state
if st.session_state.mapa_generado and st.session_state.departamentos_seleccionados_previos:
    st.info(f"Showing map for selected departments.")
    gdf_sel = gdf.copy()
    gdf_sel["seleccionado"] = gdf_sel["NOMBRE_DEP"].isin(st.session_state.departamentos_seleccionados_previos)

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
elif not st.session_state.mapa_generado:
    st.info("👈 Usa la barra lateral para seleccionar departamentos y presiona **Generar mapa**.")
