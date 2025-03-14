import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# URL de lectura de datos del formulario de barriles (hoja de Google Sheets)
url_datos = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQGl3m5Hx7jOfhHj7a_ZP39pSHozEf5aIk-0U_KxLzo7xJQ1UV3TxXguHtkfFgNZvDnXqRu_V9Djq4v/pub?output=csv"
url_clientes = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRp2WaIAPuZDpFzxnX0KHZZlMg3P5d6oRNB_a7BYzqJ7W_uVYVWlsfE5eOgBvAxDj0faRhffCnFoUUL/pub?output=csv"

st.set_page_config(page_title="Trazabilidad de Barriles", layout="wide")
st.markdown("<h1 style='color:#f5e342;'>📦 Trazabilidad de Barriles</h1>", unsafe_allow_html=True)

# ----------------------------------------
# FORMULARIO REGISTRO DE BARRILES
# ----------------------------------------
st.markdown("---")
st.markdown("<h2 style='color:#fff3aa;'>📝 Registrar Movimiento de Barril</h2>", unsafe_allow_html=True)

codigo = st.text_input("Código del barril (opcional para 'Barril sucio' y 'Lavado en bodega')")
lote_barril = st.text_input("Lote del producto (9 dígitos: DDMMYYXXX)")
estilo = st.selectbox("Estilo de cerveza", ["Pale Ale", "IPA", "Stout", "Lager", "Amber Ale", "Otro"])
cliente = ""

try:
    df_clientes = pd.read_csv(url_clientes)
    df_clientes.columns = df_clientes.columns.str.strip()
    cliente = st.selectbox("Cliente", df_clientes["Nombre"] + " - " + df_clientes["Dirección"])
except:
    cliente = st.text_input("Cliente (ingrese manual si no carga lista)")

estado = st.selectbox("Estado del barril", ["Despachado", "Lavado en bodega", "Sucio", "En cuarto frío"])
responsable = st.text_input("Responsable del registro")
observaciones = st.text_area("Observaciones")

# Campos adicionales si estado es "Despachado"
incluir_latas = False
cantidad_latas = ""
lote_latas = ""
cantidad_latas_2 = ""
lote_latas_2 = ""

if estado == "Despachado":
    incluir_latas = st.selectbox("¿Incluye despacho de latas?", ["No", "Sí"])
    if incluir_latas == "Sí":
        cantidad_latas = st.number_input("Cantidad de latas", min_value=0, step=1)
        lote_latas = st.text_input("Lote de las latas (9 dígitos: DDMMYYXXX)")

        agregar_segundo_lote = st.checkbox("¿Agregar latas de otro lote?")
        if agregar_segundo_lote:
            cantidad_latas_2 = st.number_input("Cantidad de latas (segundo lote)", min_value=0, step=1)
            lote_latas_2 = st.text_input("Lote de las latas (segundo lote)")

if st.button("Registrar Movimiento"):
    if estado in ["Barril sucio", "Lavado en bodega"] or codigo.strip() != "":
        form_url = "https://docs.google.com/forms/d/e/1FAIpQLSd_kmL2A1nFtsuUlQINrDLlUsbi0iMupEL1UxuYUsEw8qchXQ/formResponse"
        payload = {
            "entry.311770370": codigo,
            "entry.1283669263": estilo,
            "entry.1545499818": estado,
            "entry.91059345": cliente,
            "entry.1661747572": responsable,
            "entry.1195378605": observaciones,
            "entry.1234567890": lote_barril  # Suponiendo que se añadió este campo en el formulario
        }
        if estado == "Despachado" and incluir_latas == "Sí":
            payload["entry.1122334455"] = str(cantidad_latas)
            payload["entry.2233445566"] = lote_latas
            if cantidad_latas_2 and lote_latas_2:
                payload["entry.3344556677"] = str(cantidad_latas_2)
                payload["entry.4455667788"] = lote_latas_2

        response = requests.post(form_url, data=payload)
        if response.status_code in [200, 302]:
            st.success("✅ Registro enviado correctamente")
        else:
            st.error(f"❌ Error al enviar el formulario. Código: {response.status_code}")
    else:
        st.warning("⚠️ El campo 'Código' es obligatorio para este tipo de registro")

# ----------------------------------------
# FORMULARIO NUEVO CLIENTE
# ----------------------------------------
st.markdown("---")
st.markdown("<h2 style='color:#fff3aa;'>➕ Registrar Nuevo Cliente</h2>", unsafe_allow_html=True)

nuevo_cliente = st.text_input("Nombre del nuevo cliente")
direccion_cliente = st.text_input("Dirección del cliente")

if st.button("Agregar Cliente"):
    if nuevo_cliente.strip() != "":
        form_cliente_url = "https://docs.google.com/forms/d/e/1FAIpQLScllMMM33p5F--_I6Y80gsLUsusGMTk0OA3XDVC9ocngoc2Hw/formResponse"
        payload_cliente = {
            "entry.1250409245": nuevo_cliente,
            "entry.82359015": direccion_cliente
        }
        response = requests.post(form_cliente_url, data=payload_cliente)
        if response.status_code in [200, 302]:
            st.success("✅ Cliente agregado correctamente")
        else:
            st.error(f"❌ Error al enviar el cliente. Código: {response.status_code}")
    else:
        st.warning("⚠️ El nombre del cliente no puede estar vacío")

# ----------------------------------------
# BUSCAR REGISTROS
# ----------------------------------------
st.markdown("---")
st.markdown("<h2 style='color:#fff3aa;'>🔍 Buscar Barriles</h2>", unsafe_allow_html=True)

try:
    df_search = pd.read_csv(url_datos)
    df_search.columns = df_search.columns.str.strip()

    filtro_codigo = st.text_input("🔎 Buscar por código de barril")
    filtro_cliente = st.text_input("🔎 Buscar por cliente")
    filtro_estado = st.selectbox("📌 Filtrar por estado", ["", "Despachado", "Lavado en bodega", "Sucio", "En cuarto frío"])

    df_filtrado = df_search.copy()
    if filtro_codigo:
        df_filtrado = df_filtrado[df_filtrado["Código"].astype(str).str.contains(filtro_codigo)]
    if filtro_cliente:
        df_filtrado = df_filtrado[df_filtrado["Cliente"].astype(str).str.contains(filtro_cliente, case=False)]
    if filtro_estado:
        df_filtrado = df_filtrado[df_filtrado["Estado"] == filtro_estado]

    if not df_filtrado.empty:
        st.dataframe(df_filtrado[["Código", "Estilo", "Estado", "Cliente", "Responsable", "Observaciones"]])
    else:
        st.warning("No se encontraron resultados.")
except Exception as e:
    st.error(f"⚠️ No se pudo cargar la hoja de búsqueda: {e}")
