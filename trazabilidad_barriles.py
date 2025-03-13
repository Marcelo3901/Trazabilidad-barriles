import streamlit as st
import requests

st.set_page_config(page_title="Trazabilidad de Barriles", layout="centered")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto&display=swap');
    .stApp {
        font-family: 'Roboto', sans-serif;
        color: #ffffff;
        padding: 1rem;
        font-size: 18px !important;
    }
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

st.markdown("<h2 style='font-size:32px;'>📋 Registro de Barril</h2>", unsafe_allow_html=True)
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

# Lista dinámica de clientes desde archivo local
if "clientes" not in st.session_state:
    st.session_state.clientes = ["Castiza Av. Estudiantes", "Bendita Birra CC sebastian Belalcazar", "Baruk", "Sandona Plaza",
                                 "El Barril", "La estiba las cuadras", "La estiba Villaflor"]

cliente = "Planta Castiza"
if estado_barril == "Despachado":
    cliente = st.selectbox("Cliente", st.session_state.clientes)

responsables = ["Pepe Vallejo", "Ligia Cajigas", "Erika Martinez", "Marcelo Martinez", "Operario 1", "Operario 2"]
responsable = st.selectbox("Responsable", responsables)

observaciones = ""
if estado_barril == "Sucio":
    observaciones = f"Último cliente: {cliente}"
else:
    observaciones = st.text_area("Observaciones", "")

if st.button("Guardar Registro"):
    if codigo_barril and estado_barril and responsable and codigo_valido:
        url = "https://docs.google.com/forms/d/e/1FAIpQLSedFQmZuDdVY_cqU9WdiWCTBWCCh1NosPnD891QifQKqaeUfA/formResponse"
        data = {
            "entry.311770370": codigo_barril,
            "entry.1283669263": estilo_cerveza,
            "entry.1545499818": estado_barril,
            "entry.91059345": cliente,
            "entry.1661747572": responsable,
            "entry.1195378605": observacionesmov
        }
        response = requests.post(url, data=data)
        if response.status_code == 200:
            st.success("✅ Registro enviado correctamente al formulario.")
        else:
            st.error(f"❌ Error al enviar el formulario. Código de estado: {response.status_code}")
    else:
        if not codigo_valido:
            st.warning("⚠️ El código del barril no cumple con el formato esperado.")
        else:
            st.warning("⚠️ Por favor, completa los campos obligatorios")

st.markdown("---")
st.markdown("<h2 style='font-size:32px;'>➕ Registrar Nuevo Cliente</h2>", unsafe_allow_html=True)
nuevo_cliente = st.text_input("Nuevo cliente")
if st.button("Agregar cliente"):
    if nuevo_cliente.strip():
        if nuevo_cliente not in st.session_state.clientes:
            st.session_state.clientes.append(nuevo_cliente)
            st.success("✅ Cliente agregado correctamente.")
        else:
            st.warning("⚠️ El cliente ya está en la lista.")
    else:
        st.warning("⚠️ Por favor, ingresa un nombre válido.")
