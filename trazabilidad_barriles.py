import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from gspread_dataframe import set_with_dataframe
from datetime import date

st.write("Mis secrets:", st.secrets)

# 📌 Configuración inicial de la app
st.set_page_config(page_title="Trazabilidad de Barriles", layout="centered")

# 🔹 Título
st.markdown("<h1 style='text-align: center; color: #2cc6c1;'>🍺 TRAZABILIDAD BARRILES CASTIZA</h1>", unsafe_allow_html=True)

# 📌 CONEXIÓN CON GOOGLE SHEETS
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# 📌 Cargar credenciales desde st.secrets
cred_json = json.dumps(st.secrets["gcp_service_account"])
credentials = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(cred_json), SCOPE)
client = gspread.authorize(credentials)

# 📌 Abrir la hoja de Google Sheets
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/TU_SPREADSHEET_ID/edit?gid=0"
sheet = client.open_by_url(SPREADSHEET_URL).sheet1

# 📌 Leer datos desde Google Sheets
def leer_registros():
    registros = sheet.get_all_records()
    return pd.DataFrame(registros)

# 📌 Guardar nuevos registros
def guardar_registro(df_nuevo):
    df_existente = leer_registros()
    df_actualizado = pd.concat([df_existente, df_nuevo], ignore_index=True)
    sheet.clear()
    set_with_dataframe(sheet, df_actualizado)

# 📌 FORMULARIO DE REGISTRO
st.subheader("📋 Registrar un Nuevo Barril")

fecha = st.date_input("Fecha", date.today())
codigo = st.text_input("Código del barril")
estilo = st.selectbox("Estilo de Cerveza", ["Golden", "IPA", "Stout", "Otros"])
estado = st.selectbox("Estado", ["Despachado", "Lavado en bodega", "Sucio", "En cuarto frío"])
cliente = st.text_input("Cliente", "Planta Castiza")
responsable = st.selectbox("Responsable", ["Pepe Vallejo", "Ligia Cajigas", "Erika Martinez"])
observaciones = st.text_area("Observaciones", "")

# 📌 Guardar en la hoja de Google Sheets
if st.button("Guardar Registro"):
    if codigo:
        nuevo_registro = pd.DataFrame({
            "Fecha": [str(fecha)],
            "Código": [codigo],
            "Estilo": [estilo],
            "Estado": [estado],
            "Cliente": [cliente],
            "Responsable": [responsable],
            "Observaciones": [observaciones]
        })
        guardar_registro(nuevo_registro)
        st.success("✅ Registro guardado correctamente en Google Sheets")
    else:
        st.warning("⚠️ Debes ingresar un código válido.")

# 📌 Mostrar datos en la app
st.subheader("📑 Registros Actuales")
df = leer_registros()
if not df.empty:
    st.dataframe(df)
else:
    st.info("No hay registros aún.")



