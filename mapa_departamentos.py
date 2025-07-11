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

# --- URL al nuevo archivo ZIP corregido ---
ZIP_URL = "https://raw.githubusercontent.com/lmiguerrero/colombia/main/Deptos.zip"

# --- Función para descargar y cargar shapefile desde ZIP ---
@st.cache_data(show_spinner="📥 Descargando y cargando datos...")
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
                gdf = gpd.read_file(shp_path)

                if 'DeNombre' not in gdf.columns:
                    st.error("❌ El shapefile no contiene la columna 'DeNombre'.")
                    return None

                gdf = gdf[['DeNombre', 'geometry']].copy()
                gdf = gdf[gdf.geometry.notnull() & gdf.is_valid]

                if gdf.crs != "EPSG:4326":
                    gdf = gdf.to_crs(epsg=4326)

                gdf['DeNombre'] = gdf['DeNombre'].fillna('').astype(str)

                return gdf

    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error al descargar el archivo ZIP: {e}")
        return None
    except Exception as e:
        st.error(f"❌ Error general al cargar datos: {e}")
        return None

# --- Cargar shapefile ---
gdf = cargar_departamentos_desde_zip(ZIP_URL)
if gdf is None or gdf.empty:
    st.stop()

# --- Barra lateral para selección de departamentos ---
st.sidebar.header("🎯 Selección de Departamentos")
departamentos = sorted(gdf['DeNombre'].unique())
seleccionados = st.sidebar.multiselect(
    "Selecciona uno o más departamentos:",
    options=departamentos,
    default=[]
)

# --- Botón para generar el mapa ---
if st.sidebar.button("📍 Generar mapa"):

    gdf['seleccionado'] = gdf['DeNombre'].isin(seleccionados)
    gdf_sel = gdf[gdf['seleccionado']].copy()

    if gdf_sel.empty:
        st.warning("⚠️ No se encontraron geometrías válidas para los departamentos seleccionados.")
    else:
        bounds = gdf_sel.total_bounds
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
            gdf,
            style_function=estilo,
            tooltip=folium.GeoJsonTooltip(fields=["DeNombre"], aliases=["Departamento:"])
        ).add_to(m)

        folium.LayerControl().add_to(m)
        m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

        st.subheader("🗺️ Mapa generado")
        st_folium(m, width=1000, height=600)

else:
    st.info("👈 Usa la barra lateral para seleccionar uno o más departamentos y luego presiona **Generar mapa**.")
