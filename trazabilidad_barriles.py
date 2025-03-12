import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread_dataframe import get_as_dataframe, set_with_dataframe

# Configurar la página
st.set_page_config(page_title="Trazabilidad Barriles", layout="centered")
st.title("🍺 Trazabilidad de Barriles")

# Conexión con Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

try:
    credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
    client = gspread.authorize(credentials)
    sheet = client.open_by_url("https://docs.google.com/spreadsheets/d/1FjQ8XBDwDdrlJZsNkQ6YyaygkHLhpKmfLBv6wd3uluY/edit#gid=0").sheet1
except Exception as e:
    st.error(f"❌ Error al conectar con Google Sheets: {e}")
    st.stop()

# Formulario
fecha = st.date_input("Fecha")
codigo = st.text_input("Código del barril")
capacidad = ""
if codigo.startswith("20"): capacidad = "20L"
elif codigo.startswith("30"): capacidad = "30L"
elif codigo.startswith("58"): capacidad = "58L"

estilo = st.selectbox("Estilo de cerveza", ["Golden", "Amber", "Stout", "IPA", "Otros"])
estado = st.selectbox("Estado del barril", ["Despachado", "Lavado en bodega", "Sucio", "En cuarto frío"])
cliente = st.text_input("Cliente")
responsable = st.selectbox("Responsable", ["Marcelo", "Operario 1", "Operario 2"])
obs = st.text_area("Observaciones")

if st.button("Guardar"):
    if not codigo:
        st.warning("⚠️ Código obligatorio")
    else:
        nuevo = pd.DataFrame({
            "Fecha": [fecha],
            "Código": [codigo],
            "Capacidad": [capacidad],
            "Estilo": [estilo],
            "Estado": [estado],
            "Cliente": [cliente],
            "Responsable": [responsable],
            "Observaciones": [obs]
        })
        try:
            existente = get_as_dataframe(sheet)
            existente = existente.dropna(how='all')
        except:
            existente = pd.DataFrame()

        actualizado = pd.concat([existente, nuevo], ignore_index=True)
        sheet.clear()
        set_with_dataframe(sheet, actualizado)
        st.success("✅ Registro guardado en Google Sheets")
