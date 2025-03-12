import streamlit as st
import pandas as pd
from google.cloud import firestore
import os
from datetime import date

# ============================
# CONFIGURACIÓN FIRESTORE
# ============================
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credentials.json"

try:
    db = firestore.Client()
    st.success("✅ Conectado a Firestore correctamente")
except Exception as e:
    st.error(f"❌ Error al conectar con Firestore: {e}")

# ============================
# INTERFAZ DE USUARIO
# ============================
st.set_page_config(page_title="Trazabilidad de Barriles", layout="centered")
st.title("🍺 Trazabilidad Barriles Castiza")

st.markdown("## 📋 Registro de Barril")
fecha_registro = st.date_input("Fecha", value=date.today())
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

# ============================
# GUARDAR REGISTRO EN FIRESTORE
# ============================
def guardar_registro_en_firestore(datos):
    try:
        doc_ref = db.collection("registros_barriles").document()
        doc_ref.set(datos)
        st.success("✅ Registro guardado en Firestore correctamente")
    except Exception as e:
        st.error(f"❌ Error al guardar en Firestore: {e}")

if st.button("Guardar Registro"):
    if codigo_barril and estado_barril and fecha_registro and responsable and codigo_valido:
        datos = {
            "fecha": str(fecha_registro),
            "codigo": codigo_barril,
            "capacidad": capacidad,
            "estilo": estilo_cerveza,
            "estado": estado_barril,
            "cliente": cliente,
            "responsable": responsable,
            "observaciones": observaciones
        }
        guardar_registro_en_firestore(datos)
    else:
        if not codigo_valido:
            st.warning("⚠️ El código del barril no cumple con el formato esperado.")
        else:
            st.warning("⚠️ Por favor, completa todos los campos requeridos.")
