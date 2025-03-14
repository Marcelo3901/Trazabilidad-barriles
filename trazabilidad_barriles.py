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

# CARGA DE CLIENTES DESDE LA HOJA Rclientes
sheet_clientes_url = "https://docs.google.com/spreadsheets/d/1FjQ8XBDwDdrlJZsNkQ6YyaygkHLhpKmfLBv6wd3uluY/gviz/tq?tqx=out:csv&sheet=Rclientes"
try:
    df_clientes = pd.read_csv(sheet_clientes_url)
    df_clientes.columns = df_clientes.columns.str.strip()
    df_clientes = df_clientes.dropna(subset=["Nombre"])
    lista_clientes = df_clientes["Nombre"].astype(str).unique().tolist()
except Exception as e:
    lista_clientes = []
    st.error(f"❌ No se pudo cargar la lista de clientes: {e}")

cliente = "Planta Castiza"
if estado_barril == "Despachado":
    cliente = st.selectbox("Cliente", lista_clientes)

responsables = ["Pepe Vallejo", "Ligia Cajigas", "Erika Martinez", "Marcelo Martinez", "Operario 1", "Operario 2"]
responsable = st.selectbox("Responsable", responsables)

observaciones = st.text_area("Observaciones")

# ENVÍO DEL FORMULARIO DE MOVIMIENTO
if st.button("Guardar Registro"):
    if codigo_v
