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

# --- URL al archivo ZIP en GitHub (versión RAW) ---
# Confirmado que el archivo dentro es 'Departamento.shp' y la columna es 'DeNombre'
ZIP_URL = "https://raw.githubusercontent.com/lmiguerrero/colombia/main/Deptos.zip"

# --- Función para descargar y cargar el shapefile desde un ZIP ---
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
                
                # Intentar leer el shapefile. Si falla por codificación, intentar latin1
                try:
                    gdf = gpd.read_file(shp_path)
                except Exception:
                    gdf = gpd.read_file(shp_path, encoding="latin1")

                # --- ¡CORRECCIÓN AQUÍ! La columna esperada es 'DeNombre' ---
                if 'DeNombre' not in gdf.columns:
                    # Agregando un mensaje de depuración útil si la columna no se encuentra
                    st.error(f"❌ El shapefile no contiene la columna 'DeNombre'. Columnas disponibles: {gdf.columns.tolist()}")
                    return None

                # Seleccionar solo la columna 'DeNombre' y la geometría
                gdf = gdf[['DeNombre', 'geometry']].copy()
                
                # Limpiar geometrías nulas o inválidas
                gdf = gdf[gdf.geometry.notnull() & gdf.is_valid]

                # Reproyectar a EPSG:4326 si es necesario para Folium
                if gdf.crs != "EPSG:4326":
                    gdf = gdf.to_crs(epsg=4326)

                # Asegurarse de que la columna 'DeNombre' sea string y sin NaNs
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
# --- ¡CORRECCIÓN AQUÍ! Usando 'DeNombre' para las opciones del multiselect ---
departamentos = sorted(gdf['DeNombre'].unique())
seleccionados = st.sidebar.multiselect(
    "Selecciona uno o más departamentos:",
    options=departamentos,
    default=[]
)

# --- Botón para generar el mapa ---
if st.sidebar.button("📍 Generar mapa"):

    # --- ¡CORRECCIÓN AQUÍ! Usando 'DeNombre' para la selección ---
    gdf['seleccionado'] = gdf['DeNombre'].isin(seleccionados)
    gdf_sel = gdf[gdf['seleccionado']].copy()

    if gdf_sel.empty:
        st.warning("⚠️ No se encontraron geometrías válidas para los departamentos seleccionados.")
    else:
        bounds = gdf_sel.total_bounds
        centro = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]

        m = folium.Map(location=centro, zoom_start=6)

        def estilo(f):
            # 'seleccionado' se añade al gdf, así que se puede usar en las propiedades
            return {
                'fillColor': 'blue' if f['properties']['seleccionado'] else 'lightgray',
                'color': 'black',
                'weight': 1,
                'fillOpacity': 0.6
            }

        folium.GeoJson(
            gdf, # Usamos el gdf completo para que se muestren todos los departamentos (seleccionados y no seleccionados)
            style_function=estilo,
            # --- ¡CORRECCIÓN AQUÍ! Usando 'DeNombre' para el tooltip ---
            tooltip=folium.GeoJsonTooltip(fields=["DeNombre"], aliases=["Departamento:"])
        ).add_to(m)

        folium.LayerControl().add_to(m)
        m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

        st.subheader("🗺️ Mapa generado")
        st_folium(m, width=1000, height=600)

else:
    st.info("👈 Usa la barra lateral para seleccionar uno o más departamentos y luego presiona **Generar mapa**.")
