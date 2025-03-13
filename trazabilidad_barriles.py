import streamlit as st
import pandas as pd

# Enlace público de tu hoja de Google Sheets vinculada al formulario
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/e/XXXXX/pub?gid=0&single=true&output=csv"  # ← reemplaza con tu enlace

st.set_page_config(page_title="Trazabilidad de Barriles", layout="wide")
st.title("📦 Trazabilidad de Barriles - Castiza")

st.markdown("Consulta de registros generados automáticamente desde Google Forms")

# Cargar los datos directamente desde el Google Sheet (formato CSV)
try:
    df = pd.read_csv(GOOGLE_SHEET_URL)
    st.success("✅ Datos cargados correctamente desde Google Sheets.")
    
    # Mostrar tabla
    st.dataframe(df)

    # Filtro por código o cliente
    filtro = st.text_input("🔍 Buscar por código del barril o cliente:")
    if filtro:
        resultado = df[df.apply(lambda row: filtro.lower() in row.to_string().lower(), axis=1)]
        if not resultado.empty:
            st.write(resultado)
        else:
            st.warning("No se encontraron coincidencias.")

except Exception as e:
    st.error("❌ No se pudieron cargar los datos. Verifica el enlace de Google Sheets.")
    st.exception(e)
