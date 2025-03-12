import streamlit as st
import pandas as pd
import gspread
import json
from oauth2client.service_account import ServiceAccountCredentials
from gspread_dataframe import set_with_dataframe
from datetime import date

# Configuración de Streamlit
st.set_page_config(page_title="Trazabilidad de Barriles", layout="centered")

st.markdown("<div style='font-size:48px; font-weight:bold; color:#2cc6c1; text-align:center;'>🍺 TRAZABILIDAD BARRILES CASTIZA</div>", unsafe_allow_html=True)
st.markdown("---")

# Conexión con Google Sheets
SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_dict(st.secrets["gcp_service_account"], SCOPE)
credentials = ServiceAccountCredentials.from_json_keyfile_dict(json.loads(cred_json), SCOPE)
client = gspread.authorize(credentials)
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1FjQ8XBDwDdrlJZsNkQ6YyaygkHLhpKmfLBv6wd3uluY/edit?gid=0"
sheet = client.open_by_url(SPREADSHEET_URL).sheet1

def leer_registros():
    registros = sheet.get_all_records()
    return pd.DataFrame(registros)

def guardar_registro(df_nuevo):
    try:
        df_existente = leer_registros()
        df_actualizado = pd.concat([df_existente, df_nuevo], ignore_index=True)
    except:
        df_actualizado = df_nuevo
    sheet.clear()
    set_with_dataframe(sheet, df_actualizado)

st.subheader("📋 Registro de Barril")
fecha_registro = st.date_input("Fecha", date.today())
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
            "Fecha": [str(fecha_registro)],
            "Código": [codigo_barril],
            "Capacidad": [capacidad],
            "Estilo": [estilo_cerveza],
            "Estado": [estado_barril],
            "Cliente": [cliente],
            "Responsable": [responsable],
            "Observaciones": [observaciones]
        })
        guardar_registro(nuevo_registro)
        st.success("✅ Registro guardado correctamente en Google Sheets")
    else:
        if not codigo_valido:
            st.warning("⚠️ El código del barril no cumple con el formato esperado.")
        else:
            st.warning("⚠️ Por favor, completa los campos obligatorios")

# Mostrar reporte general
st.markdown("---")
st.subheader("📑 Reporte General")
df = leer_registros()
if not df.empty:
    st.dataframe(df)
else:
    st.info("No hay registros disponibles.")
