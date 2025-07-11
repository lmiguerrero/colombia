import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from zipfile import ZipFile
import os
import tempfile
import requests
from io import BytesIO

st.set_page_config(page_title="Departamentos de Colombia", layout="wide")

st.title("🗺️ Mapa Interactivo de Departamentos de Colombia")
st.info("Intentando cargar datos geográficos... Esto puede tardar unos segundos la primera vez.")

# --- URL del archivo ZIP en GitHub (versión RAW) ---
ZIP_URL = "https://raw.githubusercontent.com/lmiguerrero/colombia/main/Depto.zip"

# --- Función para descargar y cargar el shapefile desde un ZIP ---
@st.cache_data(show_spinner="Descargando y cargando datos...")
def cargar_departamentos_desde_zip(url):
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()

        zip_buffer = BytesIO(response.content)

        with ZipFile(zip_buffer) as zip_ref:
            with tempfile.TemporaryDirectory() as tmpdir:
                zip_ref.extractall(tmpdir)
                shp_files = [f for f in os.listdir(tmpdir) if f.endswith(".shp")]

                if not shp_files:
                    st.error("❌ No se encontró ningún archivo .shp en el ZIP.")
                    return None

                shp_path = os.path.join(tmpdir, shp_files[0])

                try:
                    gdf = gpd.read_file(shp_path)
                except Exception:
                    gdf = gpd.read_file(shp_path, encoding="latin1")

                if 'NOMBRE_DEP' not in gdf.columns:
                    st.error("❌ La columna 'NOMBRE_DEP' no existe en el shapefile.")
                    return None

                gdf = gdf[['NOMBRE_DEP', 'geometry']]

                if gdf.crs != "EPSG:4326":
                    gdf = gdf.to_crs(epsg=4326)

                gdf['NOMBRE_DEP'] = gdf['NOMBRE_DEP'].fillna('').astype(str)

                return gdf

    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error al descargar el archivo ZIP: {e}")
        return None
    except Exception as e:
        st.error(f"❌ Error general al cargar datos: {e}")
        return None

# --- Cargar datos geográficos ---
gdf = cargar_departamentos_desde_zip(ZIP_URL)

if gdf is None:
    st.stop()

# --- Barra lateral para selección de departamentos ---
st.sidebar.header("🎯 Selección de Departamentos")
departamentos = sorted(gdf['NOMBRE_DEP'].unique())
seleccionados = st.sidebar.multiselect(
    "Selecciona uno o más departamentos:",
    options=departamentos,
    default=[]
)

# --- Botón para generar el mapa ---
if st.sidebar.button("📍 Generar mapa") and seleccionados:
    gdf_sel = gdf.copy()
    gdf_sel['seleccionado'] = gdf_sel['NOMBRE_DEP'].isin(seleccionados)

    gdf_show = gdf_sel[gdf_sel['seleccionado']]
    bounds = gdf_show.total_bounds
    centro = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]

    m = folium.Map(location=centro, zoom_start=6)

    def estilo(f):
        return {
            'fillColor': 'blue' if f['properties']['seleccionado'] else 'lightgray',
            'color': 'black',
            'weight': 1,
            'fillOpacity': 0.6
        }

    folium.GeoJson(
        gdf_sel,
        style_function=estilo,
        tooltip=folium.GeoJsonTooltip(fields=["NOMBRE_DEP"], aliases=["Departamento:"])
    ).add_to(m)

    folium.LayerControl().add_to(m)
    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

    st.subheader("🗺️ Mapa generado")
    st_folium(m, width=1000, height=600)

elif seleccionados:
    st.info("Presiona 'Generar mapa' para visualizar los departamentos seleccionados.")
else:
    st.info("👈 Usa la barra lateral para seleccionar uno o más departamentos.")
