import streamlit as st
import geopandas as gpd
import folium
from streamlit_folium import st_folium
from zipfile import ZipFile
import os
import tempfile
import requests
import pandas as pd # Asegúrate de tener pandas importado

st.set_page_config(page_title="Departamentos de Colombia", layout="wide")
st.title("🗺️ Mapa Interactivo de Departamentos de Colombia")

# --- Inicializar st.session_state ---
if 'mapa_generado' not in st.session_state:
    st.session_state.mapa_generado = False
if 'departamentos_seleccionados_previos' not in st.session_state:
    st.session_state.departamentos_seleccionados_previos = []

# Función para cargar shapefile (adaptada para URL y simplificada)
@st.cache_data
def cargar_shapefile(source_path_or_url):
    st.info(f"Intentando cargar datos desde: {source_path_or_url}")
    temp_zip_file = None
    try:
        # Descargar el archivo si es una URL
        if source_path_or_url.startswith("http://") or source_path_or_url.startswith("https://"):
            response = requests.get(source_path_or_url, stream=True)
            response.raise_for_status() # Lanza un error para códigos de estado HTTP incorrectos
            temp_zip_file = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
            with temp_zip_file as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            zip_path = temp_zip_file.name
            st.success("Archivo ZIP descargado temporalmente.")
        else: # Si es una ruta de archivo local
            zip_path = source_path_or_url
            if not os.path.exists(zip_path):
                st.error(f"¡Error! No se encontró el archivo ZIP local en: {zip_path}")
                return None

        # Proceso de descompresión y lectura
        with tempfile.TemporaryDirectory() as tmpdir:
            with ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdir)
            shp_files = [f for f in os.listdir(tmpdir) if f.endswith(".shp")]
            if not shp_files:
                st.error("No se encontró un .shp en el ZIP")
                st.write(f"Archivos encontrados en ZIP: {os.listdir(tmpdir)}")
                return None
            shp_path = os.path.join(tmpdir, shp_files[0])

            # Cargar solo las columnas necesarias para mayor eficiencia y evitar errores
            gdf = gpd.read_file(shp_path, include_fields=['NOMBRE_DEP']) # Carga solo 'NOMBRE_DEP' y la geometría

            if gdf.crs != "EPSG:4326":
                gdf = gdf.to_crs(epsg=4326)
            st.success(f"Shapefile cargado exitosamente. CRS: {gdf.crs}")

            # Opcional: Eliminar cualquier otra columna que no sea 'NOMBRE_DEP' o 'geometry'
            # (Aunque include_fields ya debería manejarlo, esto es una doble verificación)
            cols_to_keep = ['NOMBRE_DEP', 'geometry']
            current_cols = gdf.columns.tolist()
            cols_to_drop = [col for col in current_cols if col not in cols_to_keep]
            if cols_to_drop:
                gdf = gdf.drop(columns=cols_to_drop)
                st.info(f"Columnas eliminadas para simplificación: {cols_to_drop}")

            return gdf.copy()
    except requests.exceptions.RequestException as e:
        st.error(f"Error al descargar el archivo ZIP desde la URL: {e}")
        return None
    except Exception as e:
        st.error(f"Error inesperado durante la carga del shapefile: {e}")
        return None
    finally:
        if temp_zip_file and os.path.exists(temp_zip_file.name):
            os.unlink(temp_zip_file.name) # Asegura que el archivo temporal se borre

# Cargar shapefile con la URL de descarga directa
zip_file = "https://raw.githubusercontent.com/lmiguerrero/colombia/main/Departamentos.zip"
gdf = cargar_shapefile(zip_file)
if gdf is None:
    st.stop()
else:
    st.success(f"GeoDataFrame cargado con {len(gdf)} departamentos. Columnas: {gdf.columns.tolist()}")
    # st.write("Tipos de datos del GeoDataFrame:", gdf.dtypes) # Puedes descomentar para depurar

# Barra lateral
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

# Lógica para actualizar el mapa automáticamente si la selección cambia sin presionar el botón
if set(seleccionados) != set(st.session_state.departamentos_seleccionados_previos) and seleccionados:
    st.session_state.mapa_generado = True
    st.session_state.departamentos_seleccionados_previos = seleccionados
elif not seleccionados and st.session_state.mapa_generado:
    st.session_state.mapa_generado = False
    st.session_state.departamentos_seleccionados_previos = []

# Mostrar mapa basado en el estado de la sesión
if st.session_state.mapa_generado and st.session_state.departamentos_seleccionados_previos:
    st.info(f"Mostrando mapa para los departamentos seleccionados.")
    gdf_sel = gdf.copy()
    gdf_sel["seleccionado"] = gdf_sel["NOMBRE_DEP"].isin(st.session_state.departamentos_seleccionados_previos)

    # NO ES NECESARIA LA LIMPIEZA ADICIONAL AQUÍ
    # porque ya cargamos solo 'NOMBRE_DEP' y la geometría,
    # que son tipos de datos serializables (string y geometría)

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
