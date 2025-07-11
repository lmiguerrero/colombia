import streamlit as st
import geopandas as gpd
import pandas as pd
import zipfile
import tempfile
import os
import folium
import requests
from io import BytesIO
from streamlit_folium import st_folium

st.set_page_config(page_title="Departamentos de Colombia", layout="wide")

# --- Estilos generales e institucionales de tu otro visor ---
st.markdown("""
    <style>
    /* Colores base de la marca Bogotá: Ajuste para un tono principal menos oscuro */
    :root {
        --bogota-blue-dark: #06038D; /* Pantone 2738 C - para acentos o texto oscuro */
        --bogota-blue-medium: #1C3F93; /* Nuevo color principal de fondo (antes era acento) */
        --bogota-blue-light: #5B8EE6; /* Un azul más claro para elementos interactivos */
        --text-color-light: white;
        --text-color-dark: black;
    }

    /* Estilos generales de la aplicación */
    html, body, .stApp {
        background-color: var(--bogota-blue-medium); /* Fondo azul medio de Bogotá */
        color: var(--text-color-light);
        font-family: 'Inter', sans-serif;
    }
    section[data-testid="stSidebar"] {
        background-color: var(--bogota-blue-dark); /* Sidebar con el azul oscuro principal */
        color: var(--text-color-light);
    }
    .stButton>button, .stDownloadButton>button {
        background-color: var(--bogota-blue-light); /* Botones con azul claro de Bogotá */
        color: var(--text-color-light);
        border: none;
        border-radius: 6px;
        transition: background-color 0.3s ease; /* Suaviza el cambio de color al pasar el ratón */
    }
    .stButton>button:hover, .stDownloadButton>button:hover {
        background-color: #79A3EF; /* Tono ligeramente diferente al pasar el ratón */
    }
    /* Estilos para los campos de entrada */
    .stTextInput>div>div>input,
    .stSelectbox>div>div>div>input,
    .stMultiSelect>div>div>div>div>div { /* Selector para el multiselect */
        color: var(--text-color-dark);
        background-color: var(--text-color-light);
        border-radius: 4px;
    }
    /* Contorno para el mapa */
    .element-container:has(> iframe) {
        height: 650px !important;
        border: 2px solid var(--bogota-blue-light); /* Contorno con azul claro de Bogotá */
        border-radius: 8px;
    }
    /* Tooltips de Folium */
    .leaflet-tooltip {
        background-color: rgba(255, 255, 255, 0.9);
        color: var(--text-color-dark);
        font-weight: bold;
    }
    /* Dataframe de Streamlit */
    .stDataFrame {
        background-color: var(--text-color-light);
        color: var(--text-color-dark);
        border-radius: 8px;
    }
    /* Botones de descarga específicos */
    .stDownloadButton > button {
        background-color: var(--text-color-light);
        color: var(--bogota-blue-dark);
        border: 1px solid var(--bogota-blue-medium);
        border-radius: 6px;
        font-weight: bold;
    }
    /* Estilo para el pie de página fijo */
    .fixed-footer {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        text-align: center;
        padding: 10px 0;
        background-color: var(--bogota-blue-dark); /* Fondo azul oscuro */
        color: #b0c9a8; /* Texto claro (puede ajustarse a un tono de azul más claro si se prefiere) */
        font-size: 0.8em;
        z-index: 1000; /* Asegura que esté por encima de otros contenidos */
        border-top: 1px solid var(--bogota-blue-medium); /* Un borde sutil con azul medio */
    }
    /* Estilo para etiquetas (labels) de los widgets */
    label {
        color: var(--text-color-light) !important;
        font-weight: bold;
    }
    /* Asegurar que las etiquetas de checkbox y slider también sean blancas */
    .stCheckbox > label,
    .stSlider > label,
    .stCheckbox label > div, /* Nuevo selector para el texto anidado dentro del checkbox */
    .stSlider label > div { /* Nuevo selector para el texto anidado dentro del slider */
        color: var(--text-color-light) !important;
    }
    /* Estilo para el cuadro de estadísticas de ocupaciones */
    .stats-box { /* Mantenido por si acaso, aunque no se usa directamente aquí */
        margin-top: 1em;
        margin-bottom: 1.5em;
        padding: 0.7em;
        background-color: white; /* Fondo blanco puro */
        border-radius: 8px;
        font-size: 16px;
        color: var(--bogota-blue-dark); /* Texto oscuro */
    }
    </style>
""", unsafe_allow_html=True)

# --- Función para descargar y cargar el archivo ZIP de departamentos ---
@st.cache_data
def descargar_y_cargar_departamentos(url):
    """
    Descarga un archivo ZIP desde una URL, lo extrae, y carga el shapefile
    de departamentos en un GeoDataFrame, seleccionando solo la columna 'NOMBRE_DEP'.
    """
    try:
        with st.spinner("Cargando datos de departamentos... Esto puede tardar unos segundos la primera vez."):
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
                    
                    # Asegurarse de que 'NOMBRE_DEP' sea string y rellenar NaN (aunque 'include_fields' debería limpiar)
                    if gdf is not None and 'NOMBRE_DEP' in gdf.columns:
                        gdf['NOMBRE_DEP'] = gdf['NOMBRE_DEP'].fillna('').astype(str)
                    
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
url_zip_departamentos = "https://raw.githubusercontent.com/lmiguerrero/colombia/main/Departamentos.zip"
gdf_departamentos = descargar_y_cargar_departamentos(url_zip_departamentos)

# --- Verificar si los datos se cargaron ---
if gdf_departamentos is None:
    st.warning("⚠️ No se pudieron cargar los datos de departamentos. El visor no puede funcionar sin ellos.")
    st.stop()

st.title("🗺️ Mapa Interactivo de Departamentos de Colombia")

# --- Barra lateral ---
st.sidebar.header("🎯 Selección de Departamentos")
departamentos_disponibles = sorted(gdf_departamentos["NOMBRE_DEP"].unique().tolist())
seleccionados = st.sidebar.multiselect(
    "Selecciona departamentos",
    options=departamentos_disponibles,
    default=st.session_state.departamentos_seleccionados_previos,
    placeholder="Elige uno o más departamentos"
)

# Sección de configuración del mapa
fondos_disponibles = {
    "OpenStreetMap": "OpenStreetMap",
    "CartoDB Claro (Positron)": "CartoDB positron",
    "CartoDB Oscuro": "CartoDB dark_matter",
    "Satélite (Esri)": "Esri.WorldImagery",
    "Esri NatGeo World Map": "Esri.NatGeoWorldMap",
    "Esri World Topo Map": "Esri.WorldTopoMap"
}
fondo_seleccionado = st.sidebar.selectbox("🗺️ Fondo del mapa", list(fondos_disponibles.keys()), index=1)

st.sidebar.header("🎨 Estilos del Mapa")
mostrar_relleno_poligonos = st.sidebar.checkbox("Mostrar relleno de departamentos", value=True)

# --- Botones de acción ---
col_botones = st.sidebar.columns(2)
with col_botones[0]:
    if st.button("🧭 Aplicar filtros y mostrar mapa"):
        if seleccionados:
            st.session_state.mapa_generado = True
            st.session_state.departamentos_seleccionados_previos = seleccionados
        else:
            st.session_state.mapa_generado = False
            st.warning("⚠️ No has seleccionado ningún departamento.")
with col_botones[1]:
    if st.button("🔄 Reiniciar visor"):
        st.session_state.mapa_generado = False
        st.session_state.departamentos_seleccionados_previos = []
        st.rerun()

# Lógica para mostrar el mapa
if st.session_state.mapa_generado:
    gdf_sel = gdf_departamentos.copy()
    gdf_sel["seleccionado"] = gdf_sel["NOMBRE_DEP"].isin(st.session_state.departamentos_seleccionados_previos)

    st.subheader("🗺️ Mapa de Departamentos")

    if not gdf_sel["seleccionado"].any(): # Si no hay departamentos seleccionados en el filtro actual
        st.warning("⚠️ No se encontraron departamentos seleccionados para mostrar. Por favor, ajusta tus selecciones.")
    else:
        # Calcular los límites y el centro para ajustar el zoom del mapa
        # Usamos solo los departamentos seleccionados para calcular el ajuste del mapa
        gdf_para_bounds = gdf_sel[gdf_sel["seleccionado"]].copy()
        bounds = gdf_para_bounds.total_bounds
        centro_lat = (bounds[1] + bounds[3]) / 2
        centro_lon = (bounds[0] + bounds[2]) / 2

        with st.spinner("Generando mapa..."):
            m = folium.Map(location=[centro_lat, centro_lon], zoom_start=6, tiles=fondos_disponibles[fondo_seleccionado])

            def style_function_departamentos(feature):
                es_seleccionado = feature["properties"]["seleccionado"]
                return {
                    "fillColor": "#5B8EE6" if es_seleccionado else "lightgray", # Azul Bogotá para seleccionados, gris para el resto
                    "color": "#1C3F93", # Borde azul oscuro de Bogotá
                    "weight": 1.5,
                    "fillOpacity": 0.6 if mostrar_relleno_poligonos else 0
                }

            folium.GeoJson(
                gdf_sel,
                name="Departamentos de Colombia",
                style_function=style_function_departamentos,
                tooltip=folium.GeoJsonTooltip(fields=["NOMBRE_DEP"], aliases=["Departamento:"])
            ).add_to(m)

            folium.LayerControl().add_to(m) # Añadir control de capas

            m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]]) # Ajustar el mapa a los departamentos seleccionados

            # Leyenda del mapa
            leyenda_html_departamentos = '''
            <div style="position: absolute; bottom: 10px; right: 10px; z-index: 9999;
                         background-color: white; padding: 10px; border: 1px solid #ccc;
                         font-size: 14px; box-shadow: 2px 2px 4px rgba(0,0,0,0.1);">
                <strong>Leyenda</strong><br>
                <i style="background:#5B8EE6; opacity:0.7; width:10px; height:10px; display:inline-block; border:1px solid #1C3F93;"></i> Departamento Seleccionado<br>
                <i style="background:lightgray; opacity:0.7; width:10px; height:10px; display:inline-block; border:1px solid black;"></i> Otros Departamentos<br>
            </div>
            '''
            m.get_root().html.add_child(folium.Element(leyenda_html_departamentos))

            st_folium(m, width=1200, height=600)
else:
    st.info("👈 Usa la barra lateral para seleccionar departamentos y presiona **Aplicar filtros y mostrar mapa**.")

# --- Footer global para la pantalla principal del visor ---
st.markdown(
    """
    <div class="fixed-footer">
        Realizado por Ing. Topográfico Luis Miguel Guerrero | © 2025. Contacto: luis.guerrero@urt.gov.co
    </div>
    """,
    unsafe_allow_html=True
)
