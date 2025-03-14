import streamlit as st
import pandas as pd
import requests

# ----------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA
# ----------------------------------------------------
st.set_page_config(page_title="Trazabilidad de Barriles", layout="wide")
st.title("🍺 App de Trazabilidad de Barriles")

# ----------------------------------------------------
# ENLACE A LA HOJA DE RESPUESTAS DE BARRILES (FORMULARIO)
# IMPORTANTE: Reemplazar con tu enlace exportado en CSV
# ----------------------------------------------------
url_datos = "https://docs.google.com/spreadsheets/d/e/1FAIpQLSfXXXXXXXxxxxxxXxxxxXX/pub?output=csv"

# ----------------------------------------------------
# REGISTRO DE NUEVO CLIENTE
# ----------------------------------------------------
st.markdown("---")
st.markdown("<h2 style='color:#fff3aa;'>➕ Registrar Nuevo Cliente</h2>", unsafe_allow_html=True)

nuevo_cliente = st.text_input("Nombre del nuevo cliente")
direccion_cliente = st.text_input("Dirección del cliente")
responsable_cliente = st.text_input("Responsable del alta de cliente")

if st.button("Agregar Cliente"):
    if nuevo_cliente.strip() != "":
        # Enlace al formulario de nuevo cliente
        form_cliente_url = "https://docs.google.com/forms/d/e/1FAIpQLScllMMM33p5F--_I6Y80gsLUsusGMTk0OA3XDVC9ocngoc2Hw/formResponse"

        
