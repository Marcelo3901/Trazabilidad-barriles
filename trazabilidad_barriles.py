import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Trazabilidad de Barriles - Castiza", layout="centered")
st.markdown("""
    <style>
    .big-title {
        font-size: 48px !important;
        font-weight: bold;
        color: #2cc6c1;
        text-align: center;
        margin-bottom: 30px;
        text-shadow: 2px 2px 4px #000000;
    }
    .stButton > button {
        background-color: #2cc6c1 !important;
        color: white !important;
        border-radius: 12px;
        padding: 14px 28px;
        font-size: 22px;
        font-weight: bold;
        border: none;
        width: 100%;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        transition: 0.3s ease-in-out;
    }
    .stButton > button:hover {
        background-color: #1ba8a3 !important;
        transform: scale(1.03);
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='big-title'>🍺 TRAZABILIDAD BARRILES CASTIZA</div>", unsafe_allow_html=True)

# Inicializar lista de clientes (simulación en memoria)
if "clientes" not in st.session_state:
    st.session_state.clientes = ["Castiza Av. Estudiantes", "Bendita Birra CC sebastian Belalcazar", "Baruk", "Sandona Plaza",
                                 "El Barril", "La estiba las cuadras", "La estiba Villaflor"]

st.markdown("""
<h2 style='font-size:32px;'>➕ Registrar Nuevo Cliente</h2>
""", unsafe_allow_html=True)
nuevo_cliente = st.text_input("Nombre del nuevo cliente")
if st.button("Agregar Cliente"):
    if nuevo_cliente and nuevo_cliente not in st.session_state.clientes:
        st.session_state.clientes.append(nuevo_cliente)
        st.success("✅ Cliente agregado exitosamente")
    else:
        st.warning("⚠️ Ingresa un nombre válido o el cliente ya existe")

st.markdown("""
<h2 style='font-size:32px;'>📋 Registro de Barril</h2>
""", unsafe_allow_html=True)
codigo_barril = st.text_input("Código del barril")

estilos = ["Golden", "Amber", "Vienna Lager", "Brown Ale Cafe", "Stout",
           "Session IPA", "IPA", "Maracuya", "Barley Wine", "Trigo", "Catharina Sour",
           "Gose", "Imperial IPA", "NEIPA", "Imperial Stout", "Otros"]
estilo_cerveza = st.selectbox("Estilo", estilos)
estado_barril = st.selectbox("Estado del barril", ["Despachado", "Lavado en bodega", "Sucio", "En cuarto frío"])

cliente = "Planta Castiza"
if estado_barril == "Despachado":
    cliente = st.selectbox("Cliente", st.session_state.clientes)

responsables = ["Pepe Vallejo", "Ligia Cajigas", "Erika Martinez", "Marcelo Martinez", "Operario 1", "Operario 2"]
responsable = st.selectbox("Responsable", responsables)

observaciones = st.text_area("Observaciones")

if st.button("Guardar Registro"):
    if codigo_barril and estado_barril and responsable:
        # Enviar a Google Form (POST)
        url = "https://docs.google.com/forms/d/e/1FAIpQLSedFQmZuDdVY_cqU9WdiWCTBWCCh1NosPnD891QifQKqaeUfA/formResponse"
        payload = {
            "entry.311770370": codigo_barril,
            "entry.1283669263": estilo_cerveza,
            "entry.1545499818": estado_barril,
            "entry.91059345": cliente,
            "entry.1661747572": responsable,
            "entry.1195378605": observaciones
        }
        response = requests.post(url, data=payload)
        if response.status_code == 200:
            st.success("✅ Registro enviado exitosamente")
        else:
            st.error(f"❌ Error al enviar el formulario. Código de estado: {response.status_code}")
    else:
        st.warning("⚠️ Completa todos los campos requeridos")

st.markdown("---")
st.markdown("<h2 style='font-size:32px;'>🔍 Filtros de búsqueda</h2>", unsafe_allow_html=True)
codigo_filtro = st.text_input("Buscar por código de barril")
cliente_filtro = st.selectbox("Filtrar por cliente", ["Todos"] + st.session_state.clientes)
estado_filtro = st.selectbox("Filtrar por estado", ["Todos", "Despachado", "Lavado en bodega", "Sucio", "En cuarto frío"])

st.info("🔔 Los resultados filtrados se reflejarán en el reporte general si usas integración con Google Sheets o cargas el CSV.")
