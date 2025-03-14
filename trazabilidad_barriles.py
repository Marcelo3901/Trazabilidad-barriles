import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="Trazabilidad de Barriles", layout="wide")

st.markdown("<h1 style='text-align: center; color: #f5f5dc;'>🍺 App Trazabilidad de Barriles</h1>", unsafe_allow_html=True)
st.markdown("<hr>", unsafe_allow_html=True)

# ----------------------------------------
# FORMULARIO DE REGISTRO PRINCIPAL
# ----------------------------------------
st.markdown("### ➕ Registrar Movimiento de Barril")

codigo = st.text_input("Código del barril (Debe tener 5 dígitos y empezar por 20, 30 o 58)")
estilo = st.selectbox("Estilo de cerveza", ["", "IPA", "APA", "Stout", "Pilsen", "Amber", "Lager", "Latas"])
estado = st.selectbox("Estado del barril", ["", "Despachado", "Lavado en bodega", "Sucio", "En cuarto frío"])

# Leer clientes desde hoja de Google Sheets
try:
    url_clientes = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ3C9_q38KnD8UqOpm3xEXsRu64JpOm49Irh8W_3v5LZb_GKq8f-8J6V8wOYKXYoXpubXvTeIhD8iHk/pub?gid=1091869268&single=true&output=csv"
    df_clientes = pd.read_csv(url_clientes)
    lista_clientes = df_clientes["Nombre"].dropna().unique().tolist()
    cliente = st.selectbox("Cliente", [""] + lista_clientes)
    direccion_cliente = df_clientes[df_clientes["Nombre"] == cliente]["Dirección"].values[0] if cliente else ""
    if direccion_cliente:
        st.info(f"📍 Dirección: {direccion_cliente}")
except Exception as e:
    st.warning(f"No se pudo cargar la lista de clientes: {e}")
    cliente = ""

lote = st.text_input("Lote del producto (9 dígitos - formato DDMMYYXXX)")
responsable = st.text_input("Responsable")
observaciones = st.text_area("Observaciones adicionales")

# ----------------------------------------
# Enviar a Google Form
# ----------------------------------------
if st.button("📤 Enviar Registro"):
    # Validaciones condicionales
    campos_obligatorios = []

    estilo_latas = estilo == "Latas"
    estado_sin_validacion = estado in ["Lavado en bodega", "Sucio"]

    if not responsable.strip():
        campos_obligatorios.append("Responsable")

    if not estilo:
        campos_obligatorios.append("Estilo")

    if not estado:
        campos_obligatorios.append("Estado")

    if not cliente:
        campos_obligatorios.append("Cliente")

    if not estilo_latas and not estado_sin_validacion:
        # Validar Código y Lote solo si no es latas ni barril sucio/lavado
        if not codigo.strip():
            campos_obligatorios.append("Código del barril")
        elif not (codigo.startswith(("20", "30", "58")) and len(codigo) == 5 and codigo.isdigit()):
            campos_obligatorios.append("Formato de código inválido")

        if not lote.strip():
            campos_obligatorios.append("Lote del producto")
        elif not (len(lote) == 9 and lote.isdigit()):
            campos_obligatorios.append("Formato de lote inválido")

    if campos_obligatorios:
        st.warning(f"⚠️ Faltan o son inválidos los siguientes campos: {', '.join(campos_obligatorios)}")
    else:
        form_url = "https://docs.google.com/forms/d/e/1FAIpQLSfFlxlYbGDKT3KJeRkpeQBJ3lNYUfqzMnSH9qgPpyDLDeVyoQ/formResponse"
        payload = {
            "entry.311770370": codigo,
            "entry.1283669263": estilo,
            "entry.1545499818": estado,
            "entry.91059345": cliente,
            "entry.1661747572": responsable,
            "entry.1195378605": observaciones,
            "entry.1781911117": lote
        }
        response = requests.post(form_url, data=payload)
        if response.status_code in [200, 302]:
            st.success("✅ Registro enviado correctamente")
        else:
            st.error(f"❌ Error al enviar el formulario. Código: {response.status_code}")

# ----------------------------------------
# FORMULARIO NUEVO CLIENTE
# ----------------------------------------
st.markdown("---")
st.markdown("<h2 style='color:#fff3aa;'>➕ Registrar Nuevo Cliente</h2>", unsafe_allow_html=True)

nuevo_cliente = st.text_input("Nombre del nuevo cliente")
direccion_cliente_nuevo = st.text_input("Dirección del cliente")

if st.button("Agregar Cliente"):
    if nuevo_cliente.strip() != "":
        form_cliente_url = "https://docs.google.com/forms/d/e/1FAIpQLScllMMM33p5F--_I6Y80gsLUsusGMTk0OA3XDVC9ocngoc2Hw/formResponse"
        payload_cliente = {
            "entry.1250409245": nuevo_cliente,
            "entry.82359015": direccion_cliente_nuevo
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
    url_datos = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQ3C9_q38KnD8UqOpm3xEXsRu64JpOm49Irh8W_3v5LZb_GKq8f-8J6V8wOYKXYoXpubXvTeIhD8iHk/pub?gid=2048815580&single=true&output=csv"
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
