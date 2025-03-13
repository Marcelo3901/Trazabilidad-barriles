import streamlit as st
import pandas as pd
import requests
from urllib.parse import urlencode
import base64
import os

# CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Trazabilidad Barriles Castiza", layout="centered")

# AÑADIR IMAGEN DE FONDO PERSONALIZADA
def add_bg_image(image_file):
    with open(image_file, "rb") as img:
        encoded = base64.b64encode(img.read()).decode()
    st.markdown(
        f"""
        <style>
        .stApp {{
            background-image: url("data:image/png;base64,{encoded}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

# Reemplaza "background.png" con el nombre de tu imagen
if os.path.exists("background.png"):
    add_bg_image("background.png")

# TITULO PRINCIPAL
st.markdown("""
    <h1 style='text-align:center; color:#ffffff;'>🍺 Sistema de Trazabilidad de Barriles - Castiza</h1>
""", unsafe_allow_html=True)

# ------------------------------
# FORMULARIO DE REGISTRO DE BARRILES
# ------------------------------
st.markdown("""<h2 style='color:#ffffff;'>📋 Registro Movimiento Barriles</h2>""", unsafe_allow_html=True)

codigo_barril = st.text_input("Código del barril (Debe tener 5 dígitos y empezar por 20, 30 o 58)")

# Validación del código del barril
codigo_valido = False
if codigo_barril and len(codigo_barril) == 5 and codigo_barril[:2] in ["20", "30", "58"]:
    codigo_valido = True

estilos = ["Golden", "Amber", "Vienna Lager", "Brown Ale Cafe", "Stout",
           "Session IPA", "IPA", "Maracuya", "Barley Wine", "Trigo", "Catharina Sour",
           "Gose", "Imperial IPA", "NEIPA", "Imperial Stout", "Otros"]
estilo_cerveza = st.selectbox("Estilo", estilos)

estado_barril = st.selectbox("Estado del barril", ["Despachado", "Lavado en bodega", "Sucio", "En cuarto frío"])

# Carga dinámica de clientes desde archivo local
try:
    df_clientes = pd.read_csv("clientes.csv")
    lista_clientes = df_clientes.iloc[:, 0].dropna().astype(str).tolist()
except:
    lista_clientes = []

cliente = "Planta Castiza"
if estado_barril == "Despachado":
    cliente = st.selectbox("Cliente", lista_clientes)

responsables = ["Pepe Vallejo", "Ligia Cajigas", "Erika Martinez", "Marcelo Martinez", "Operario 1", "Operario 2"]
responsable = st.selectbox("Responsable", responsables)

observaciones = st.text_area("Observaciones")

# Envío al formulario de Google Forms
if st.button("Guardar Registro"):
    if codigo_valido:
        form_url = "https://docs.google.com/forms/d/e/1FAIpQLSedFQmZuDdVY_cqU9WdiWCTBWCCh1NosPnD891QifQKqaeUfA/formResponse"
        payload = {
            "entry.311770370": codigo_barril,
            "entry.1283669263": estilo_cerveza,
            "entry.1545499818": estado_barril,
            "entry.91059345": cliente,
            "entry.1661747572": responsable,
            "entry.1465957833": observaciones
        }
        response = requests.post(form_url, data=payload)
        if response.status_code in [200, 302]:
            st.success("✅ Registro enviado correctamente")
        else:
            st.error(f"❌ Error al enviar el formulario. Código de estado: {response.status_code}")
    else:
        st.warning("⚠️ Código de barril inválido. Debe tener 5 dígitos y comenzar por 20, 30 o 58.")

# ------------------------------
# REGISTRAR NUEVO CLIENTE
# ------------------------------
st.markdown("---")
st.markdown("""<h2 style='color:#ffffff;'>➕ Registrar Nuevo Cliente</h2>""", unsafe_allow_html=True)
nuevo_cliente = st.text_input("Nombre del nuevo cliente")
direccion_cliente = st.text_input("Dirección (opcional)")

if st.button("Agregar Cliente"):
    if nuevo_cliente.strip() != "":
        try:
            df_nuevo = pd.DataFrame([[nuevo_cliente, direccion_cliente]])
            if lista_clientes:
                df_clientes = pd.concat([df_clientes, df_nuevo], ignore_index=True)
            else:
                df_clientes = df_nuevo
            df_clientes.drop_duplicates(subset=0, keep="first", inplace=True)
            df_clientes.to_csv("clientes.csv", index=False, header=False)
            st.success("✅ Cliente agregado correctamente")
        except:
            st.error("❌ Error al guardar el nuevo cliente")
    else:
        st.warning("⚠️ El nombre del cliente no puede estar vacío")

# ------------------------------
# ELIMINAR CLIENTE
# ------------------------------
st.markdown("---")
st.markdown("""<h2 style='color:#ffffff;'>🗑️ Eliminar Cliente</h2>""", unsafe_allow_html=True)
if lista_clientes:
    cliente_eliminar = st.selectbox("Selecciona cliente a eliminar", lista_clientes)
    if st.button("Eliminar Cliente"):
        try:
            df_clientes = df_clientes[df_clientes.iloc[:, 0] != cliente_eliminar]
            df_clientes.to_csv("clientes.csv", index=False, header=False)
            st.success("✅ Cliente eliminado correctamente")
        except:
            st.error("❌ Error al eliminar el cliente")

# =================== REPORTE GENERAL =======================
st.markdown("---")
st.markdown("""<h2 style='color:#ffffff;'>📑 Últimos 10 Movimientos</h2>""", unsafe_allow_html=True)
try:
    sheet_url = "https://docs.google.com/spreadsheets/d/1FjQ8XBDwDdrlJZsNkQ6YyaygkHLhpKmfLBv6wd3uluY/gviz/tq?tqx=out:csv&sheet=DatosM"
    df = pd.read_csv(sheet_url)
    df.columns = df.columns.str.strip()
    if not df.empty:
        st.dataframe(df.tail(10)[["Código", "Estilo", "Estado", "Cliente", "Responsable", "Observaciones"]])
    else:
        st.warning("⚠️ La hoja de cálculo está vacía.")
except Exception as e:
    st.error(f"⚠️ No se pudo cargar la hoja de cálculo: {e}")

# =================== FILTROS DE BÚSQUEDA =====================
st.markdown("---")
st.markdown("""<h2 style='color:#ffffff;'>🔍 Buscar Barriles</h2>""", unsafe_allow_html=True)

try:
    df = pd.read_csv(sheet_url)
    df.columns = df.columns.str.strip()

    filtro_codigo = st.text_input("🔎 Buscar por código de barril")
    filtro_cliente = st.text_input("🔎 Buscar por cliente")
    filtro_estado = st.selectbox("🔎 Buscar por estado", ["", "Despachado", "Lavado en bodega", "Sucio", "En cuarto frío"])

    df_filtro = df.copy()
    if filtro_codigo:
        df_filtro = df_filtro[df_filtro["Código"].astype(str).str.contains(filtro_codigo)]
    if filtro_cliente:
        df_filtro = df_filtro[df_filtro["Cliente"].astype(str).str.contains(filtro_cliente, case=False)]
    if filtro_estado:
        df_filtro = df_filtro[df_filtro["Estado"] == filtro_estado]

    if not df_filtro.empty:
        st.dataframe(df_filtro[["Código", "Estilo", "Estado", "Cliente", "Responsable", "Observaciones"]])
    else:
        st.warning("No se encontraron resultados con los filtros seleccionados.")
except Exception as e:
    st.error(f"⚠️ No se pudo cargar la hoja de cálculo: {e}")
