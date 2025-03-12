import streamlit as st
import pandas as pd
import os
import base64
from datetime import date
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe, set_with_dataframe

# ---------------- CONFIGURACIÓN DE PÁGINA Y ESTILO ----------------
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

def add_bg_from_local(image_file):
    with open(image_file, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
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

if os.path.exists('images/image (2).jpg'):
    add_bg_from_local('images/image (2).jpg')

# ---------------- AUTENTICACIÓN GOOGLE SHEETS ----------------
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
CREDENTIALS_FILE = "credentials.json"

try:
    credentials = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=SCOPE)
    client = gspread.authorize(credentials)
    SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1FjQ8XBDwDdrlJZsNkQ6YyaygkHLhpKmfLBv6wd3uluY/edit#gid=0"
    sheet = client.open_by_url(SPREADSHEET_URL).sheet1
except Exception as e:
    st.error(f"❌ Error al conectar con Google Sheets: {e}")
    st.stop()

# ---------------- FORMULARIO DE REGISTRO ----------------
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
            df_existente = get_as_dataframe(sheet, evaluate_formulas=True)
            df_existente = df_existente.dropna(how='all')
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
