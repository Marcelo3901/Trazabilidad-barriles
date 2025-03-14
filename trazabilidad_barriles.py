import streamlit as st
import pandas as pd
import requests
from urllib.parse import urlencode
import base64
import os

# CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Trazabilidad Barriles Castiza", layout="centered")

# IMAGEN DE FONDO PERSONALIZADA Y ESTILOS GENERALES
if os.path.exists("background.jpg"):
    with open("background.jpg", "rb") as img:
        encoded = base64.b64encode(img.read()).decode()
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Roboto&display=swap');
        html, body, [class*="st"]  {{
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
        """,
        unsafe_allow_html=True
    )

# TÍTULO PRINCIPAL
st.markdown("<h1 style='text-align:center; color:#fff3aa;'>🍺 Sistema de Trazabilidad de Barriles - Castiza</h1>", unsafe_allow_html=True)

# ----------------------------------------
# FORMULARIO DE REGISTRO DE BARRILES
# ----------------------------------------
st.markdown("<h2 style='color:#fff3aa;'>📋 Registro Movimiento Barriles</h2>", unsafe_allow_html=True)

# Entrada de código del barril
codigo_barril = st.text_input("Código del barril (Debe tener 5 dígitos y empezar por 20, 30 o 58)")
codigo_valido = codigo_barril.isdigit() and len(codigo_barril) == 5 and codigo_barril[:2] in ["20", "30", "58"]

# Lote del producto (9 dígitos)
lote_producto = st.text_input("Lote del producto (9 dígitos - formato DDMMYYXXX)")
lote_valido = lote_producto.isdigit() and len(lote_producto) == 9

# Estilo de cerveza
estilos = ["Golden", "Amber", "Vienna Lager", "Brown Ale Cafe", "Stout",
           "Session IPA", "IPA", "Maracuyá", "Barley Wine", "Trigo", "Catharina Sour",
           "Gose", "Imperial IPA", "NEIPA", "Imperial Stout", "Otros"]
estilo_cerveza = st.selectbox("Estilo", estilos)

# Estado del barril
estado_barril = st.selectbox("Estado del barril", ["Despachado", "Lavado en bodega", "Sucio", "En cuarto frío"])

# Leer lista de clientes desde Google Sheets
try:
    url_clientes = "https://docs.google.com/spreadsheets/d/1FjQ8XBDwDdrlJZsNkQ6YyaygkHLhpKmfLBv6wd3uluY/gviz/tq?tqx=out:csv&sheet=Rclientes"
    df_clientes = pd.read_csv(url_clientes)
    df_clientes.columns = df_clientes.columns.str.strip()
    lista_clientes = df_clientes["Nombre"].dropna().astype(str).tolist()
except Exception as e:
    lista_clientes = []
    st.warning(f"No se pudieron cargar los clientes: {e}")

# Mostrar campo de cliente solo si el estado es "Despachado"
cliente = "Planta Castiza"
if estado_barril == "Despachado" and lista_clientes:
    cliente = st.selectbox("Cliente", lista_clientes)

# Campos adicionales si hay despacho de latas
incluye_latas = "No"
cantidad_latas = ""
lote_latas = ""
lote_latas_valido = True  # Por defecto

if estado_barril == "Despachado":
    incluye_latas = st.selectbox("¿Incluye despacho de latas?", ["No", "Sí"])
    if incluye_latas == "Sí":
        cantidad_latas = st.number_input("Cantidad de latas", min_value=1, step=1)
        lote_latas = st.text_input("Lote de las latas (9 dígitos - formato DDMMYYXXX)")
        lote_latas_valido = lote_latas.isdigit() and len(lote_latas) == 9

# Responsable
responsables = ["Pepe Vallejo", "Ligia Cajigas", "Erika Martinez", "Marcelo Martinez", "Operario 1", "Operario 2"]
responsable = st.selectbox("Responsable", responsables)

# Observaciones
observaciones = st.text_area("Observaciones")

# Enviar a Google Forms
if st.button("Guardar Registro"):
    if not codigo_valido:
        st.error("⚠️ El código del barril no es válido.")
    elif not lote_valido:
        st.error("⚠️ El lote del producto no es válido.")
    elif incluye_latas == "Sí" and not lote_latas_valido:
        st.error("⚠️ El lote de las latas debe tener 9 dígitos.")
    else:
        form_url = "https://docs.google.com/forms/d/e/1FAIpQLSedFQmZuDdVY_cqU9WdiWCTBWCCh1NosPnD891QifQKqaeUfA/formResponse"
        payload = {
            "entry.311770370": codigo_barril,
            "entry.1283669263": estilo_cerveza,
            "entry.1545499818": estado_barril,
            "entry.91059345": cliente,
            "entry.1661747572": responsable,
            "entry.1465957833": observaciones,
            "entry.1234567890": lote_producto,         # ← CAMBIAR por el ID REAL del campo "Lote producto"
            "entry.9876543210": incluye_latas,         # ← CAMBIAR por el ID REAL del campo "Incluye latas"
            "entry.1122334455": str(cantidad_latas),   # ← CAMBIAR por el ID REAL del campo "Cantidad de latas"
            "entry.9988776655": lote_latas             # ← CAMBIAR por el ID REAL del campo "Lote latas"
        }

        # Enviar el formulario
        response = requests.post(form_url, data=payload)

        if response.status_code == 200:
            st.success("✅ Registro guardado correctamente.")
        else:
            st.warning("⚠️ El registro fue enviado, pero la respuesta del servidor no fue 200. Verifica si se guardó.")
