import streamlit as st
import pandas as pd
import requests
from urllib.parse import urlencode
import base64
import os

# CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Trazabilidad Barriles Castiza", layout="centered")

# AÑADIR IMAGEN DE FONDO PERSONALIZADA Y ESTILOS GENERALES
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
        input[type="number"] {{
            appearance: textfield;
            -moz-appearance: textfield;
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

# TITULO PRINCIPAL
st.markdown("""
    <h1 style='text-align:center; color:#fff3aa;'>🍺 Sistema de Trazabilidad de Barriles - Castiza</h1>
""", unsafe_allow_html=True)

# ------------------------------
# FORMULARIO DE REGISTRO DE BARRILES
# ------------------------------
st.markdown("""<h2 style='color:#fff3aa;'>📋 Registro Movimiento Barriles</h2>""", unsafe_allow_html=True)

# CAMPO DE CÓDIGO COMO NÚMERO PARA TELÉFONOS MÓVILES
codigo_barril = st.number_input("Código del barril (Debe tener 5 dígitos y empezar por 20, 30 o 58)", format="%05d", step=1)
codigo_barril = str(int(codigo_barril)).zfill(5) if codigo_barril else ""

codigo_valido = False
if codigo_barril and len(codigo_barril) == 5 and codigo_barril[:2] in ["20", "30", "58"]:
    codigo_valido = True

estilos = ["Golden", "Amber", "Vienna Lager", "Brown Ale Cafe", "Stout",
           "Session IPA", "IPA", "Maracuya", "Barley Wine", "Trigo", "Catharina Sour",
           "Gose", "Imperial IPA", "NEIPA", "Imperial Stout", "Otros"]
estilo_cerveza = st.selectbox("Estilo", estilos)

estado_barril = st.selectbox("Estado del barril", ["Despachado", "Lavado en bodega", "Sucio", "En cuarto frío"])

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
