import streamlit as st
import pandas as pd
import requests
from urllib.parse import urlencode

# CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Registro de Despacho de Latas", layout="centered")

# TÍTULO PRINCIPAL
st.markdown("<h1 style='text-align:center; color:#fff3aa;'>📦 Registro de Despacho de Latas</h1>", unsafe_allow_html=True)

# LEER LISTA DE CLIENTES DESDE GOOGLE SHEETS
try:
    url_clientes = "https://docs.google.com/spreadsheets/d/1FjQ8XBDwDdrlJZsNkQ6YyaygkHLhpKmfLBv6wd3uluY/gviz/tq?tqx=out:csv&sheet=Rclientes"
    df_clientes = pd.read_csv(url_clientes)
    df_clientes.columns = df_clientes.columns.str.strip()
    lista_clientes = df_clientes["Nombre"].dropna().astype(str).tolist()
except Exception as e:
    lista_clientes = []
    st.warning(f"No se pudieron cargar los clientes: {e}")

# FORMULARIO DE REGISTRO
st.markdown("<h2 style='color:#fff3aa;'>📋 Ingresar Datos</h2>", unsafe_allow_html=True)

# Estilo de cerveza
estilos = ["Golden", "Amber", "Vienna Lager", "Brown Ale Cafe", "Stout",
           "Session IPA", "IPA", "Maracuyá", "Barley Wine", "Trigo", "Catharina Sour",
           "Gose", "Imperial IPA", "NEIPA", "Imperial Stout", "Otros"]
estilo_cerveza = st.selectbox("Estilo", estilos)

# Cantidad de latas
cantidad_latas = st.number_input("Cantidad de latas", min_value=1, step=1)

# Lote del producto
lote_producto = st.text_input("Lote de las latas (9 dígitos - formato DDMMYYXXX)")
lote_valido = lote_producto.isdigit() and len(lote_producto) == 9

# Cliente
cliente = st.selectbox("Cliente", lista_clientes) if lista_clientes else "Planta Castiza"

# Responsable
responsables = ["Pepe Vallejo", "Ligia Cajigas", "Erika Martinez", "Marcelo Martinez", "Operario 1", "Operario 2"]
responsable = st.selectbox("Responsable", responsables)

# Botón para ingresar segundo lote de latas
agregar_otro_lote = st.checkbox("Agregar otro lote de latas")
cantidad_latas2 = ""
lote_latas2 = ""

if agregar_otro_lote:
    cantidad_latas2 = st.number_input("Cantidad de latas (lote adicional)", min_value=1, step=1, key="cant2")
    lote_latas2 = st.text_input("Lote adicional de las latas (9 dígitos - formato DDMMYYXXX)", key="lote2")

# ENVIAR A GOOGLE FORMS
if st.button("Guardar Registro"):
    if lote_valido:
        form_url = "https://docs.google.com/forms/d/e/1FAIpQLSerxxOI1npXAptsa3nvNNBFHYBLV9OMMX-4-Xlhz-VOmitRfQ/formResponse"
        
        payload = {
            "entry.689047838": estilo_cerveza,
            "entry.457965266": str(cantidad_latas),
            "entry.2096096606": lote_producto,
            "entry.1478892985": cliente,
            "entry.1774006398": responsable,
        }
        
        response = requests.post(form_url, data=payload)
        if response.status_code == 200:
            st.success("✅ Registro enviado correctamente.")
        else:
            st.warning("⚠️ Hubo un problema al enviar el formulario. Intenta nuevamente.")

        # Enviar segundo lote si se agregó
        if agregar_otro_lote and lote_latas2.isdigit() and len(lote_latas2) == 9:
            payload2 = {
                "entry.689047838": estilo_cerveza,
                "entry.457965266": str(cantidad_latas2),
                "entry.2096096606": lote_latas2,
                "entry.1478892985": cliente,
                "entry.1774006398": responsable,
            }
            response2 = requests.post(form_url, data=payload2)
            if response2.status_code == 200:
                st.success("✅ Segundo lote registrado correctamente.")
            else:
                st.warning("⚠️ Hubo un problema al enviar el segundo lote. Intenta nuevamente.")
    else:
        st.warning("❌ El lote del producto debe tener el formato correcto.")
