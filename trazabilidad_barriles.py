import streamlit as st
import pandas as pd
import os
import base64
import json
import gspread
from gspread_dataframe import set_with_dataframe, get_as_dataframe
from datetime import date

# -----------------------------
# CONFIGURACIÓN STREAMLIT
# -----------------------------
st.set_page_config(page_title="Trazabilidad de Barriles", layout="centered")
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto&display=swap');
    .stApp {
        font-family: 'Roboto', sans-serif;
        color: #ffffff;
        padding: 1rem;
        font-size: 18px !important;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------
# FONDO PERSONALIZADO (opcional)
# -----------------------------
def add_bg_from_local(image_file):
    if os.path.exists(image_file):
        with open(image_file, "rb") as f:
            encoded_string = base64.b64encode(f.read()).decode()
        st.markdown(f"""
            <style>
            .stApp {{
                background-image: url("data:image/jpeg;base64,{encoded_string}");
                background-size: cover;
                background-position: center;
                background-repeat: no-repeat;
                background-attachment: fixed;
            }}
            </style>
        """, unsafe_allow_html=True)

add_bg_from_local('images/image (2).jpg')

# -----------------------------
# AUTENTICACIÓN GOOGLE SHEETS
# -----------------------------
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

try:
    # Modo Streamlit Cloud (usando secrets)
    credentials_dict = st.secrets["gcp_service_account"]
except:
    # Modo local (usando archivo credentials.json)
    with open("credentials.json") as source:
        credentials_dict = json.load(source)

credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
client = gspread.authorize(credentials)

# URL de la hoja de cálculo
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1FjQ8XBDwDdrlJZsNkQ6YyaygkHLhpKmfLBv6wd3uluY"
sheet = client.open_by_url(SPREADSHEET_URL).sheet1

# -----------------------------
# INTERFAZ DE LA APP
# -----------------------------
st.markdown("<div class='big-title'>🍺 TRAZABILIDAD BARRILES CASTIZA</div>", unsafe_allow_html=True)

st.markdown("<h2 style='font-size:32px;'>📋 Registro de Barril</h2>", unsafe_allow_html=True)
fecha_registro = st.date_input("Fecha")
codigo_barril = st.text_input("Código del barril")

capacidad = ""
codigo_valido = False
if codigo_barril.startswith("20") and len(codigo_barril) == 5:
    capacidad = "20L"
    codigo_valido = True
elif codigo_barril.startswith("30") and len(codigo_barril) == 5:
    capacidad = "30L"
    codigo_valido = True
elif codigo_barril.startswith("58") and len(codigo_barril) == 5:
    capacidad = "58L"
    codigo_valido = True

estilos = ["Golden", "Amber", "Vienna Lager", "Brown Ale Cafe", "Stout",
           "Session IPA", "IPA", "Maracuya", "Barley Wine", "Trigo", "Catharina Sour",
           "Gose", "Imperial IPA", "NEIPA", "Imperial Stout", "Otros"]
estilo_cerveza = st.selectbox("Estilo", estilos)
estado_barril = st.selectbox("Estado del barril", ["Despachado", "Lavado en bodega", "Sucio", "En cuarto frío"])

clientes = ["Castiza Av. Estudiantes", "Bendita Birra CC sebastian Belalcazar", "Baruk", "Sandona Plaza",
            "El Barril", "La estiba las cuadras", "La estiba Villaflor"]
cliente = "Planta Castiza"
if estado_barril == "Despachado":
    cliente = st.selectbox("Cliente", clientes)

responsables = ["Pepe Vallejo", "Ligia Cajigas", "Erika Martinez", "Marcelo Martinez", "Operario 1", "Operario 2"]
responsable = st.selectbox("Responsable", responsables)

observaciones = ""
if estado_barril == "Sucio":
    observaciones = f"Último cliente: {cliente}"
else:
    observaciones = st.text_area("Observaciones", "")

if st.button("Guardar Registro"):
    if codigo_barril and estado_barril and fecha_registro and responsable and codigo_valido:
        nuevo_registro = pd.DataFrame({
            "Fecha": [fecha_registro],
            "Código": [codigo_barril],
            "Capacidad": [capacidad],
            "Estilo": [estilo_cerveza],
            "Estado": [estado_barril],
            "Cliente": [cliente],
            "Responsable": [responsable],
            "Observaciones": [observaciones]
        })

        try:
            df_existente = get_as_dataframe(sheet, evaluate_formulas=True).dropna(how='all')
        except:
            df_existente = pd.DataFrame()

        df_actualizado = pd.concat([df_existente, nuevo_registro], ignore_index=True)
        sheet.clear()
        set_with_dataframe(sheet, df_actualizado)
        st.success("✅ Registro guardado correctamente")
    else:
        if not codigo_valido:
            st.warning("⚠️ El código del barril no cumple con el formato esperado.")
        else:
            st.warning("⚠️ Por favor, completa los campos obligatorios")

# -----------------------------
# CONSULTAR DATOS (opcional)
# -----------------------------
st.markdown("---")
st.markdown("<h2 style='font-size:32px;'>📑 Reporte General</h2>", unsafe_allow_html=True)
try:
    df = get_as_dataframe(sheet).dropna(how='all')
    st.dataframe(df)
except:
    st.info("No hay registros para mostrar aún")
