import streamlit as st
import pandas as pd
import base64
import os
from datetime import date
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import get_as_dataframe, set_with_dataframe

# ======== CONEXIÓN CON GOOGLE SHEETS ========
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# Cargar el archivo de credenciales directamente
credentials = Credentials.from_service_account_file("credentials.json", scopes=SCOPE)

# Autenticación con gspread
client = gspread.authorize(credentials)

# URL de la hoja de cálculo
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1FjQ8XBDwDdrlJZsNkQ6YyaygkHLhpKmfLBv6wd3uluY/edit#gid=0"
sheet = client.open_by_url(SPREADSHEET_URL).sheet1

# ======== DISEÑO INTERFAZ STREAMLIT ========
st.set_page_config(page_title="Trazabilidad de Barriles", layout="centered")
st.title("🍺 TRAZABILIDAD BARRILES CASTIZA")

# === REGISTRO DE BARRIL ===
st.header("📋 Registro de Barril")
fecha_registro = st.date_input("Fecha")
codigo_barril = st.text_input("Código del barril")

# Validación del código
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

if estado_barril == "Sucio":
    observaciones = f"Último cliente: {cliente}"
else:
    observaciones = st.text_area("Observaciones", "")

# === GUARDAR REGISTRO ===
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

        # Reemplazar hoja completa con datos actualizados
        sheet.clear()
        set_with_dataframe(sheet, df_actualizado)

        st.success("✅ Registro guardado correctamente.")
    else:
        if not codigo_valido:
            st.warning("⚠️ Código inválido. Debe iniciar con 20, 30 o 58 y tener 5 dígitos.")
        else:
            st.warning("⚠️ Por favor, completa todos los campos obligatorios.")
