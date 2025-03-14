import streamlit as st
import pandas as pd
import requests
from urllib.parse import urlencode
import base64
import os

# CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Trazabilidad Barriles Castiza", layout="centered")

# IMAGEN DE FONDO Y ESTILOS
if os.path.exists("background.jpg"):
    with open("background.jpg", "rb") as img:
        encoded = base64.b64encode(img.read()).decode()
    st.markdown(f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto&display=swap');
        html, body, [class*="st"] {{
            font-family: 'Roboto', sans-serif;
            color: #fff3aa;
        }}
        .stApp {{
            background-image: url("data:image/jpeg;base64,{encoded}");
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            background-attachment: fixed;
        }}
        .stTextInput > div > div > input,
        .stSelectbox > div > div,
        .stTextArea > div > textarea {{
            background-color: #ffffff10 !important;
            color: #fff3aa !important;
            border-radius: 10px;
        }}
        .stButton > button {{
            background-color: #55dcad !important;
            color: #fff3aa !important;
            border: none;
            border-radius: 10px;
            font-weight: bold;
        }}
        .stDataFrame, .stTable {{
            background-color: rgba(0,0,0,0.6);
            border-radius: 10px;
        }}
        </style>
    """, unsafe_allow_html=True)

# TÍTULO PRINCIPAL
st.markdown("""
    <h1 style='text-align:center; color:#fff3aa;'>🍺 Sistema de Trazabilidad de Barriles - Castiza</h1>
""", unsafe_allow_html=True)

# ========================
# FORMULARIO DE MOVIMIENTO DE BARRILES
# ========================
st.markdown("""<h2 style='color:#fff3aa;'>📋 Registro Movimiento Barriles</h2>""", unsafe_allow_html=True)

codigo_barril = st.text_input("Código del barril (Debe tener 5 dígitos y empezar por 20, 30 o 58)")
codigo_valido = len(codigo_barril) == 5 and codigo_barril[:2] in ["20", "30", "58"]

estilos = ["Golden", "Amber", "Vienna Lager", "Brown Ale Cafe", "Stout", "Session IPA", "IPA", "Maracuya",
           "Barley Wine", "Trigo", "Catharina Sour", "Gose", "Imperial IPA", "NEIPA", "Imperial Stout", "Otros"]
estilo_cerveza = st.selectbox("Estilo", estilos)

estado_barril = st.selectbox("Estado del barril", ["Despachado", "Lavado en bodega", "Sucio", "En cuarto frío"])

# LECTURA DE CLIENTES DESDE GOOGLE SHEETS (ya enlazado al formulario)
sheet_url = "https://docs.google.com/spreadsheets/d/1FjQ8XBDwDdrlJZsNkQ6YyaygkHLhpKmfLBv6wd3uluY/gviz/tq?tqx=out:csv&sheet=DatosM"
try:
    df_clientes = pd.read_csv(sheet_url)
    df_clientes.columns = df_clientes.columns.str.strip()
    lista_clientes = df_clientes["Cliente"].dropna().astype(str).unique().tolist()
except Exception as e:
    lista_clientes = []
    st.error(f"❌ No se pudo cargar la lista de clientes: {e}")

cliente = "Planta Castiza"
if estado_barril == "Despachado":
    cliente = st.selectbox("Cliente", lista_clientes)

responsables = ["Pepe Vallejo", "Ligia Cajigas", "Erika Martinez", "Marcelo Martinez", "Operario 1", "Operario 2"]
responsable = st.selectbox("Responsable", responsables)

observaciones = st.text_area("Observaciones")

# Envío del formulario
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
            st.error(f"❌ Error al enviar el formulario. Código: {response.status_code}")
    else:
        st.warning("⚠️ Código inválido. Debe tener 5 dígitos y comenzar por 20, 30 o 58.")

# ========================
# REGISTRO DE NUEVO CLIENTE
# ========================
st.markdown("---")
st.markdown("""<h2 style='color:#fff3aa;'>➕ Registrar Nuevo Cliente</h2>""", unsafe_allow_html=True)

nuevo_cliente = st.text_input("Nombre del nuevo cliente")
direccion_cliente = st.text_input("Dirección (opcional)")

if st.button("Agregar Cliente"):
    if nuevo_cliente.strip() != "":
        form_cliente_url = "https://docs.google.com/forms/d/e/1FAIpQLScllMMM33p5F--_I6Y80gsLUsusGMTk0OA3XDVC9ocngoc2Hw/formResponse"
        payload_cliente = {
            "entry.1250409245": nuevo_cliente,
            "entry.82359015": direccion_cliente
        }
        response_cliente = requests.post(form_cliente_url, data=payload_cliente)
        if response_cliente.status_code in [200, 302]:
            st.success("✅ Cliente registrado correctamente (se reflejará al refrescar la hoja)")
        else:
            st.error("❌ Error al registrar cliente")
    else:
        st.warning("⚠️ El nombre del cliente no puede estar vacío")

# ========================
# ÚLTIMOS MOVIMIENTOS
# ========================
st.markdown("---")
st.markdown("""<h2 style='color:#fff3aa;'>📑 Últimos 10 Movimientos</h2>""", unsafe_allow_html=True)

try:
    df = pd.read_csv(sheet_url)
    df.columns = df.columns.str.strip()
    if not df.empty and "Código" in df.columns:
        df = df[df["Código"].notna()]
        st.dataframe(df.tail(10)[["Código", "Estilo", "Estado", "Cliente", "Responsable", "Observaciones"]])
    else:
        st.warning("⚠️ La hoja de cálculo está vacía o sin columnas válidas.")
except Exception as e:
    st.error(f"⚠️ No se pudo cargar la hoja de cálculo: {e}")

# ========================
# BÚSQUEDA DE BARRILES
# ========================
st.markdown("---")
st.markdown("""<h2 style='color:#fff3aa;'>🔍 Buscar Barriles</h2>""", unsafe_allow_html=True)

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

