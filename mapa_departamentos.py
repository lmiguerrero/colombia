import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from zipfile import ZipFile
import os
import tempfile
import requests
from io import BytesIO
import pandas as pd # Se sigue necesitando pandas para gdf.columns y dtypes

st.set_page_config(page_title="Departamentos de Colombia", layout="wide")
st.title("🗺️ Mapa Interactivo de Departamentos de Colombia")

# --- Inicializar st.session_state (CRÍTICO para la persistencia del mapa) ---
if 'mapa_generado' not in st.session_state:
    st.session_state.mapa_generado = False
if 'departamentos_seleccionados_previos' not in st.session_state:
    st.session_state.departamentos_seleccionados_previos = []

# --- Función para descargar y cargar el archivo ZIP de departamentos ---
@st.cache_data
def descargar_y_cargar_departamentos(url):
    """
    Descarga un archivo ZIP desde una URL, lo extrae, y carga el shapefile
    de departamentos en un GeoDataFrame, seleccionando solo la columna 'NOMBRE_DEP'.
    """
    st.info(f"Intentando cargar datos geográficos... Esto puede tardar unos segundos la primera vez.")
    try:
        r = requests.get(url)
        r.raise_for_status() # Lanza una excepción para errores HTTP (4xx o 5xx)
        with zipfile.ZipFile(BytesIO(r.content)) as zip_ref:
            with tempfile.TemporaryDirectory() as tmpdir:
                zip_ref.extractall(tmpdir)
                shp_path = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.endswith(".shp")]
                if not shp_path:
                    st.error("❌ Error: No se encontró ningún archivo .shp en el ZIP. Asegúrate de que el ZIP contenga un shapefile válido.")
                    return None
                
                gdf = None
                try:
                    # Cargar solo 'NOMBRE_DEP' y la geometría para optimizar
                    gdf = gpd.read_file(shp_path[0], include_fields=['NOMBRE_DEP'])
                except Exception as e:
                    st.warning(f"⚠️ Advertencia: Error al cargar shapefile con encoding predeterminado. Intentando con 'latin1'. (Detalle: {e})")
                    try:
                        gdf = gpd.read_file(shp_path[0], encoding='latin1', include_fields=['NOMBRE_DEP'])
                    except Exception as e_latin1:
                        st.error(f"❌ Error crítico: No se pudo cargar el shapefile ni con encoding predeterminado ni con 'latin1'. (Detalle: {e_latin1})")
                        return None
                
                # Asegurarse de que el GeoDataFrame final esté en CRS 4326 para Folium
                if gdf is not None and gdf.crs != "EPSG:4326":
                    st.info("ℹ️ Reproyectando datos a EPSG:4326 para compatibilidad con el mapa.")
                    gdf = gdf.to_crs(epsg=4326)
                
                # Asegurarse de que 'NOMBRE_DEP' sea string y rellenar NaN
                if gdf is not None and 'NOMBRE_DEP' in gdf.columns:
                    gdf['NOMBRE_DEP'] = gdf['NOMBRE_DEP'].fillna('').astype(str)
                
                st.success(f"Datos de departamentos cargados con {len(gdf)} registros.")
                return gdf

    except requests.exceptions.HTTPError as e:
        st.error(f"❌ Error HTTP al descargar el archivo ZIP: {e}. Por favor, verifica la URL y tu conexión a internet.")
        return None
    except requests.exceptions.ConnectionError as e:
        st.error(f"❌ Error de conexión al descargar el archivo ZIP: {e}. Asegúrate de tener conexión a internet.")
        return None
    except zipfile.BadZipFile:
        st.error("❌ El archivo descargado no es un ZIP válido. Asegúrate de que la URL apunte a un archivo ZIP.")
        return None
    except Exception as e:
        st.error(f"❌ Error inesperado al cargar el archivo ZIP: {e}. Por favor, contacta al soporte.")
        return None

# --- URL del ZIP de Departamentos ---
zip_file_url = "https://raw.githubusercontent.com/lmiguerrero/colombia/main/Departamentos.zip"
gdf_departamentos = descargar_y_cargar_departamentos(zip_file_url)

# --- Verificar si los datos se cargaron ---
if gdf_departamentos is None:
    st.stop() # Detiene la ejecución si no hay datos

# --- Barra lateral ---
st.sidebar.header("🎯 Selección de Departamentos")
departamentos_disponibles = sorted(gdf_departamentos["NOMBRE_DEP"].unique().tolist())
seleccionados = st.sidebar.multiselect(
    "Selecciona departamentos",
    options=departamentos_disponibles,
    default=st.session_state.departamentos_seleccionados_previos,
    placeholder="Elige uno o más departamentos"
)

# --- Botones de acción ---
col_botones = st.sidebar.columns(2)
with col_botones[0]:
    if st.button("📍 Generar mapa"):
        if seleccionados:
            st.session_state.mapa_generado = True
            st.session_state.departamentos_seleccionados_previos = seleccionados
        else:
            st.session_state.mapa_generado = False
            st.warning("⚠️ No has seleccionado ningún departamento.")
with col_botones[1]:
    if st.button("🔄 Reiniciar selección"):
        st.session_state.mapa_generado = False
        st.session_state.departamentos_seleccionados_previos = []
        st.rerun() # Reinicia la aplicación para limpiar la selección visual

# Lógica para mostrar el mapa
if st.session_state.mapa_generado:
    gdf_sel = gdf_departamentos.copy()
    gdf_sel["seleccionado"] = gdf_sel["NOMBRE_DEP"].isin(st.session_state.departamentos_seleccionados_previos)

    st.subheader("🗺️ Mapa de Departamentos Seleccionados")

    if not gdf_sel["seleccionado"].any():
        st.warning("⚠️ No se encontraron departamentos seleccionados para mostrar. Por favor, ajusta tus selecciones.")
    else:
        # Calcular los límites y el centro para ajustar el zoom del mapa
        # Usamos solo los departamentos seleccionados para calcular el ajuste del mapa
        gdf_para_bounds = gdf_sel[gdf_sel["seleccionado"]].copy()
        bounds = gdf_para_bounds.total_bounds
        centro_lat = (bounds[1] + bounds[3]) / 2
        centro_lon = (bounds[0] + bounds[2]) / 2

        with st.spinner("Generando mapa..."):
            m = folium.Map(location=[centro_lat, centro_lon], zoom_start=6) # Fondo predeterminado de Folium

            def style_function_departamentos(feature):
                es_seleccionado = feature["properties"]["seleccionado"]
                return {
                    "fillColor": "blue" if es_seleccionado else "lightgray", # Azul para seleccionados, gris claro para el resto
                    "color": "black", # Borde negro
                    "weight": 1,
                    "fillOpacity": 0.6
                }

            folium.GeoJson(
                gdf_sel,
                name="Departamentos de Colombia",
                style_function=style_function_departamentos,
                tooltip=folium.GeoJsonTooltip(fields=["NOMBRE_DEP"], aliases=["Departamento:"])
            ).add_to(m)

            folium.LayerControl().add_to(m) # Permite activar/desactivar capas

            m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]]) # Ajustar el mapa a los departamentos seleccionados

            st_folium(m, width=1000, height=600)
else:
    st.info("👈 Usa la barra lateral para seleccionar departamentos y presiona **Generar mapa**.")

# Opcional: Footer simple si deseas uno
# st.markdown(
#     """
#     <div style="text-align: center; font-size: 0.8em; color: gray; margin-top: 50px;">
#         Visor de Departamentos de Colombia | © 2025
#     </div>
#     """,
#     unsafe_allow_html=True
# )
