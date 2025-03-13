import streamlit as st
import pandas as pd
import datetime

# 👉 Reemplaza con el ID de tu hoja pública
SPREADSHEET_ID = "TU_ID_DE_HOJA"
SHEET_NAME = "Hoja 1"  # Cambia si tu hoja se llama diferente

# Construye la URL del CSV exportable
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}"

st.set_page_config(page_title="Trazabilidad de Barriles", layout="centered")
st.title("🍺 Sistema de Trazabilidad de Barriles")

# 📝 Formulario
with st.form("registro_form"):
    fecha = st.date_input("Fecha", value=datetime.date.today())
    codigo = st.text_input("Código del barril (Ej: 20123, 30123, 58123)")
    capacidad = ""
    if codigo.startswith("20"):
        capacidad = "20L"
    elif codigo.startswith("30"):
        capacidad = "30L"
    elif codigo.startswith("58"):
        capacidad = "58L"
    else:
        capacidad = "Desconocida"

    estilo = st.selectbox("Estilo de cerveza", ["IPA", "Amber", "Golden", "Stout", "Otra"])
    estado = st.selectbox("Estado del barril", ["Despachado", "Lavado en bodega", "Sucio", "En cuarto frío"])
    cliente = st.text_input("Cliente")
    responsable = st.text_input("Responsable")
    observaciones = st.text_area("Observaciones")

    submitted = st.form_submit_button("Guardar")

if submitted:
    st.warning("❗ Este ejemplo aún no guarda en la hoja porque Google Sheets públicas solo permiten lectura. Para guardar necesitas usar Google Forms o conexión autenticada.")
    st.info("➡ Te mostraré los datos que se guardarían:")

    nuevo = pd.DataFrame([{
        "Fecha": fecha,
        "Código": codigo,
        "Capacidad": capacidad,
        "Estilo": estilo,
        "Estado": estado,
        "Cliente": cliente,
        "Responsable": responsable,
        "Observaciones": observaciones
    }])
    st.dataframe(nuevo)

# 📊 Mostrar contenido de la hoja
st.markdown("---")
st.subheader("📑 Registros existentes en hoja pública:")
try:
    df = pd.read_csv(CSV_URL)
    st.dataframe(df)
except Exception as e:
    st.error(f"❌ Error al cargar la hoja pública: {e}")
