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

# Código del barril
codigo_barril = st.text_input("Código del barril (Debe tener 5 dígitos y empezar por 20, 30 o 58)")

# Estilo de cerveza
estilos = ["Golden", "Amber", "Vienna Lager", "Brown Ale Cafe", "Stout",
           "Session IPA", "IPA", "Maracuyá", "Barley Wine", "Trigo", "Catharina Sour",
           "Gose", "Imperial IPA", "NEIPA", "Imperial Stout", "Otros"]
estilo_cerveza = st.selectbox("Estilo", estilos)

# Estado del barril
estado_barril = st.selectbox("Estado del barril", ["Despachado", "Lavado en bodega", "Sucio", "En cuarto frío"])

# Mostrar lote solo si estado es "Despachado" o "En cuarto frío"
lote_producto = ""
if estado_barril in ["Despachado", "En cuarto frío"]:
    lote_producto = st.text_input("Lote del producto (9 dígitos - formato DDMMYYXXX)")

# Leer lista de clientes desde Google Sheets
try:
    url_clientes = "https://docs.google.com/spreadsheets/d/1FjQ8XBDwDdrlJZsNkQ6YyaygkHLhpKmfLBv6wd3uluY/gviz/tq?tqx=out:csv&sheet=Rclientes"
    df_clientes = pd.read_csv(url_clientes)
    df_clientes.columns = df_clientes.columns.str.strip()
    lista_clientes = df_clientes["Nombre"].dropna().astype(str).tolist()
except Exception as e:
    lista_clientes = []
    st.warning(f"No se pudieron cargar los clientes: {e}")

# Mostrar cliente solo si estado es "Despachado"
cliente = "Planta Castiza"
if estado_barril == "Despachado" and lista_clientes:
    cliente = st.selectbox("Cliente", lista_clientes)

# Campos adicionales para despacho de latas
incluye_latas = "No"
cantidad_latas = ""
lote_latas = ""
cantidad_latas2 = ""
lote_latas2 = ""

if estado_barril == "Despachado":
    incluye_latas = st.selectbox("¿Incluye despacho de latas?", ["No", "Sí"])
    if incluye_latas == "Sí":
        cantidad_latas = st.number_input("Cantidad de latas", min_value=1, step=1)
        lote_latas = st.text_input("Lote de las latas (9 dígitos - formato DDMMYYXXX)")
        agregar_otro_lote = st.checkbox("Agregar otro lote de latas")
        if agregar_otro_lote:
            cantidad_latas2 = st.number_input("Cantidad de latas (lote adicional)", min_value=1, step=1, key="cant2")
            lote_latas2 = st.text_input("Lote adicional de las latas (9 dígitos - formato DDMMYYXXX)", key="lote2")

# Responsable
responsables = ["Pepe Vallejo", "Ligia Cajigas", "Erika Martinez", "Marcelo Martinez", "Operario 1", "Operario 2"]
responsable = st.selectbox("Responsable", responsables)

# Observaciones
observaciones = st.text_area("Observaciones")

# BOTÓN DE GUARDADO
if st.button("Guardar Registro"):
    codigo_valido = codigo_barril.isdigit() and len(codigo_barril) == 5 and codigo_barril[:2] in ["20", "30", "58"]
    lote_valido = lote_producto.isdigit() and len(lote_producto) == 9 if lote_producto else True

    if incluye_latas == "Sí" or (codigo_valido and lote_valido):
        # Enviar formulario de barriles
        form_url_barriles = "https://docs.google.com/forms/d/e/1FAIpQLSedFQmZuDdVY_cqU9WdiWCTBWCCh1NosPnD891QifQKqaeUfA/formResponse"
        payload_barril = {
            "entry.311770370": codigo_barril,
            "entry.1283669263": estilo_cerveza,
            "entry.1545499818": estado_barril,
            "entry.91059345": cliente,
            "entry.1661747572": responsable,
            "entry.1465957833": observaciones,
            "entry.1234567890": lote_producto,
            "entry.9876543210": incluye_latas,
            "entry.1122334455": str(cantidad_latas),
            "entry.9988776655": lote_latas,
            "entry.2233445566": str(cantidad_latas2),
            "entry.6677889900": lote_latas2
        }
        response_barril = requests.post(form_url_barriles, data=payload_barril)

        # Enviar formulario de latas
        if estado_barril == "Despachado" and incluye_latas == "Sí":
            form_url_latas = "https://docs.google.com/forms/d/e/1FAIpQLSerxxOI1npXAptsa3nvNNBFHYBLV9OMMX-4-Xlhz-VOmitRfQ/formResponse"
            payload_lata1 = {
                "entry.689047838": estilo_cerveza,
                "entry.457965266": str(cantidad_latas),
                "entry.2096096606": lote_latas,
                "entry.1478892985": cliente,
                "entry.1774006398": responsable
            }
            requests.post(form_url_latas, data=payload_lata1)

            if cantidad_latas2 and lote_latas2:
                payload_lata2 = {
                    "entry.689047838": estilo_cerveza,
                    "entry.457965266": str(cantidad_latas2),
                    "entry.2096096606": lote_latas2,
                    "entry.1478892985": cliente,
                    "entry.1774006398": responsable
                }
                requests.post(form_url_latas, data=payload_lata2)

        st.success("✅ Registro enviado correctamente.")
    else:
        st.warning("❌ Debes ingresar un código válido del barril y un lote del producto, o seleccionar despacho de latas.")
