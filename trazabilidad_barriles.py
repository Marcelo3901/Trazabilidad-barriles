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

# FORMULARIO DE REGISTRO DE BARRILES
st.markdown("<h2 style='color:#fff3aa;'>📋 Registro Movimiento Barriles</h2>", unsafe_allow_html=True)

estado_barril = st.selectbox("Estado del barril", ["Despacho", "Lavado en bodega", "Sucio", "En cuarto frío"])

codigo_barril = ""
lote_producto = ""

if estado_barril in ["Despacho", "En cuarto frío", "Lavado en bodega", "Sucio"]:
    codigo_barril = st.text_input("Código del barril (Debe tener 5 dígitos y empezar por 20, 30 o 58)")

if estado_barril in ["Despacho", "En cuarto frío"]:
    lote_producto = st.text_input("Lote del producto (9 dígitos - formato DDMMYYXXX)")

estilos = ["Golden", "Amber", "Vienna Lager", "Brown Ale Cafe", "Stout",
           "Session IPA", "IPA", "Maracuyá", "Barley Wine", "Trigo", "Catharina Sour",
           "Gose", "Imperial IPA", "NEIPA", "Imperial Stout", "Otros"]
estilo_cerveza = st.selectbox("Estilo", estilos)

try:
    url_clientes = "https://docs.google.com/spreadsheets/d/1FjQ8XBDwDdrlJZsNkQ6YyaygkHLhpKmfLBv6wd3uluY/gviz/tq?tqx=out:csv&sheet=Rclientes"
    df_clientes = pd.read_csv(url_clientes)
    df_clientes.columns = df_clientes.columns.str.strip()
    df_clientes.dropna(subset=["Nombre"], inplace=True)
    df_clientes = df_clientes[df_clientes["Nombre"].str.strip() != ""]
    lista_clientes = df_clientes["Nombre"].dropna().astype(str).tolist()
    dict_direcciones = df_clientes.set_index("Nombre")["Dirección"].to_dict()
except Exception as e:
    lista_clientes = []
    dict_direcciones = {}
    st.warning(f"No se pudieron cargar los clientes: {e}")

cliente = "Planta Castiza"
direccion_cliente = ""
if estado_barril == "Despacho" and lista_clientes:
    cliente = st.selectbox("Cliente", lista_clientes)
    direccion_cliente = dict_direcciones.get(cliente, "")
    st.text_input("Dirección del cliente", value=direccion_cliente, disabled=True)

# DESPACHO DE LATAS CON MÚLTIPLES ENTRADAS
latas = []
incluye_latas = "No"
if estado_barril == "Despacho":
    incluye_latas = st.selectbox("¿Incluye despacho de latas?", ["No", "Sí"])
    if incluye_latas == "Sí":
        st.markdown("""
        <h4 style='color:#fff3aa;'>🧃 Despacho Latas</h4>
        """, unsafe_allow_html=True)

        if "num_latas" not in st.session_state:
            st.session_state.num_latas = 1

        for i in range(st.session_state.num_latas):
            st.markdown(f"**[ORDEN {i+1}]**")
            cantidad = st.number_input(f"Cantidad (Orden {i+1})", min_value=1, key=f"cantidad_lata_{i}")
            lote = st.text_input(f"Lote (orden {i+1})", key=f"lote_lata_{i}")
            latas.append((cantidad, lote))

        if st.button("➕ Agregar otra lata"):
            st.session_state.num_latas += 1

responsables = ["Pepe Vallejo", "Ligia Cajigas", "Erika Martinez", "Marcelo Martinez", "Operario 1", "Operario 2"]
responsable = st.selectbox("Responsable", responsables)

observaciones = st.text_area("Observaciones")

if st.button("Guardar Registro"):
    if incluye_latas == "Sí" and len(latas) > 0:
        form_latas_url = "https://docs.google.com/forms/d/e/1FAIpQLSerxxOI1npXAptsa3nvNNBFHYBLV9OMMX-4-Xlhz-VOmitRfQ/formResponse"
        for idx, (cant, lot) in enumerate(latas):
            payload_latas = {
                "entry.457965266": str(cant),
                "entry.689047838": estilo_cerveza,
                "entry.2096096606": lot,
                "entry.1478892985": cliente,
                "entry.1774006398": responsable
            }
            requests.post(form_latas_url, data=payload_latas)
        st.success("✅ Registro de latas enviado correctamente")
        st.balloons()
    else:
        if not codigo_barril.strip():
            st.warning("⚠️ Debes ingresar un código de barril antes de enviar el formulario.")
        else:
            form_url = "https://docs.google.com/forms/d/e/1FAIpQLSedFQmZuDdVY_cqU9WdiWCTBWCCh1NosPnD891QifQKqaeUfA/formResponse"
            payload = {
                "entry.311770370": codigo_barril,
                "entry.1283669263": estilo_cerveza,
                "entry.1545499818": estado_barril,
                "entry.91059345": cliente,
                "entry.1661747572": responsable,
                "entry.1465957833": observaciones,
                "entry.1234567890": lote_producto if estado_barril in ["Despacho", "En cuarto frío"] else "",
                "entry.1122334455": incluye_latas
            }
            response = requests.post(form_url, data=payload)
            if response.status_code in [200, 302]:
                st.success("✅ Registro enviado correctamente")
                st.balloons()
            else:
                st.error(f"❌ Error al enviar el formulario. Código: {response.status_code}")

# FORMULARIO NUEVO CLIENTE
st.markdown("---")
st.markdown("<h2 style='color:#fff3aa;'>➕ Registrar Nuevo Cliente</h2>", unsafe_allow_html=True)

nuevo_cliente = st.text_input("Nombre del nuevo cliente")
direccion_nuevo_cliente = st.text_input("Dirección del cliente")

if st.button("Agregar Cliente"):
    if nuevo_cliente.strip() != "":
        form_cliente_url = "https://docs.google.com/forms/d/e/1FAIpQLScllMMM33p5F--_I6Y80gsLUsusGMTk0OA3XDVC9ocngoc2Hw/formResponse"
        payload_cliente = {
            "entry.1250409245": nuevo_cliente,
            "entry.82359015": direccion_nuevo_cliente
        }
        response = requests.post(form_cliente_url, data=payload_cliente)
        if response.status_code in [200, 302]:
            st.success("✅ Cliente agregado correctamente")
        else:
            st.error(f"❌ Error al agregar cliente. Código: {response.status_code}")
