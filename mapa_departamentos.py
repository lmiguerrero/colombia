import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from zipfile import ZipFile
import os
import tempfile

st.set_page_config(page_title="Departamentos de Colombia", layout="wide")
st.title("🗺️ Mapa Interactivo de Departamentos de Colombia")

# --- Inicializar st.session_state ---
# Esto es crucial para que Streamlit recuerde el estado
if 'mapa_generado' not in st.session_state:
    st.session_state.mapa_generado = False
if 'departamentos_seleccionados_previos' not in st.session_state:
    st.session_state.departamentos_seleccionados_previos = []

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
zip_file = "Departamentos.zip" # Asegúrate de que este archivo esté en tu repositorio de GitHub
gdf = cargar_shapefile(zip_file)
if gdf is None:
    st.stop()

# Barra lateral
st.sidebar.header("🎯 Selección de Departamentos")
departamentos = gdf["NOMBRE_DEP"].sort_values().unique().tolist()
# Mantén la selección actual del usuario
seleccionados = st.sidebar.multiselect("Selecciona departamentos", departamentos, default=st.session_state.departamentos_seleccionados_previos)

# Cuando el botón "Generar mapa" se presiona
if st.sidebar.button("📍 Generar mapa"):
    if seleccionados:
        st.session_state.mapa_generado = True
        st.session_state.departamentos_seleccionados_previos = seleccionados # Guarda la selección
    else:
        st.session_state.mapa_generado = False
        st.warning("⚠️ No has seleccionado ningún departamento.")

# Si hay un cambio en la selección SIN presionar el botón "Generar mapa",
# podríamos querer invalidar el mapa previo o regenerarlo.
# Una forma sencilla es restablecer el estado si la selección cambia.
# Esta lógica es clave para que el mapa se actualice cuando cambian los departamentos,
# incluso si no se vuelve a pulsar el botón "Generar mapa" explícitamente.
if set(seleccionados) != set(st.session_state.departamentos_seleccionados_previos) and seleccionados:
    st.session_state.mapa_generado = True # Podríamos regenerar el mapa automáticamente con la nueva selección
    st.session_state.departamentos_seleccionados_previos = seleccionados
elif not seleccionados: # Si se deseleccionan todos, el mapa debería ocultarse
    st.session_state.mapa_generado = False
    st.session_state.departamentos_seleccionados_previos = []


# Mostrar mapa basado en el estado de la sesión
if st.session_state.mapa_generado and st.session_state.departamentos_seleccionados_previos:
    st.info(f"Mostrando mapa para los departamentos seleccionados.")
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

