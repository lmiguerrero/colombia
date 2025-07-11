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

# --- CRÍTICO: Inicializar st.session_state al principio de todo ---
# Esto asegura que estas variables siempre existan antes de ser accedidas.
if 'mapa_generado' not in st.session_state:
    st.session_state.mapa_generado = False
if 'departamentos_seleccionados_previos' not in st.session_state:
    st.session_state.departamentos_seleccionados_previos = []

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

                if 'DeNombre' not in gdf.columns:
                    st.error(f"❌ El shapefile no contiene la columna 'DeNombre'. Columnas disponibles: {gdf.columns.tolist()}")
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
    # Usar la selección previa del estado de sesión para persistencia
    default=st.session_state.departamentos_seleccionados_previos
)

# --- Botones de acción ---
col_botones = st.sidebar.columns(2)
with col_botones[0]:
    if st.button("📍 Generar mapa"):
        if seleccionados:
            st.session_state.mapa_generado = True
            # Guardar la selección actual en el estado de sesión
            st.session_state.departamentos_seleccionados_previos = seleccionados
        else:
            st.session_state.mapa_generado = False
            st.warning("⚠️ No has seleccionado ningún departamento.")
with col_botones[1]:
    if st.button("🔄 Reiniciar selección"):
        st.session_state.mapa_generado = False
        st.session_state.departamentos_seleccionados_previos = []
        st.rerun() # Reinicia la aplicación para limpiar la selección visual y el mapa

# --- Lógica para mostrar el mapa (controlada por st.session_state) ---
if st.session_state.mapa_generado:
    # Usar la selección guardada en el estado de sesión para dibujar el mapa
    gdf['seleccionado'] = gdf['DeNombre'].isin(st.session_state.departamentos_seleccionados_previos)
    gdf_sel = gdf[gdf['seleccionado']].copy()

    st.subheader("🗺️ Mapa de Departamentos Seleccionados")

    if gdf_sel.empty:
        st.warning("⚠️ No se encontraron geometrías válidas para los departamentos seleccionados. Por favor, ajusta tus selecciones.")
    else:
        bounds = gdf_sel.total_bounds
        centro = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]

        with st.spinner("Generando mapa..."): # Añadido spinner para la generación del mapa
            m = folium.Map(location=centro, zoom_start=6)

            def estilo(f):
                return {
                    'fillColor': 'blue' if f['properties']['seleccionado'] else 'lightgray',
                    'color': 'black',
                    'weight': 1,
                    'fillOpacity': 0.6
                }

            folium.GeoJson(
                gdf, # Usamos el gdf completo para que se muestren todos los departamentos (seleccionados y no seleccionados)
                style_function=estilo,
                tooltip=folium.GeoJsonTooltip(fields=["DeNombre"], aliases=["Departamento:"])
            ).add_to(m)

            folium.LayerControl().add_to(m)
            m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])

            st_folium(m, width=1000, height=600)
else:
    st.info("👈 Usa la barra lateral para seleccionar uno o más departamentos y luego presiona **Generar mapa**.")
