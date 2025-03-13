import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Trazabilidad de Barriles", layout="centered")

# ------------------ FORMULARIO GOOGLE ------------------
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSedFQmZuDdVY_cqU9WdiWCTBWCCh1NosPnD891QifQKqaeUfA/formResponse"

FIELDS = {
    "codigo": "entry.311770370",
    "estilo": "entry.1283669263",
    "estado": "entry.1545499818",
    "cliente": "entry.91059345",
    "responsable": "entry.1661747572",
    "observaciones": "entry.1465957833"
}

# ------------------ LISTA DE CLIENTES ------------------
if "clientes" not in st.session_state:
    st.session_state.clientes = [
        "Castiza Av. Estudiantes",
        "Bendita Birra CC sebastian Belalcazar",
        "Baruk",
        "Sandona Plaza",
        "El Barril",
        "La estiba las cuadras",
        "La estiba Villaflor"
    ]

st.title("🍺 Sistema de Trazabilidad de Barriles")

st.header("📋 Registro de Barril")
codigo_barril = st.text_input("Código del barril (5 dígitos, comienza por 20, 30 o 58)")

codigo_valido = False
if len(codigo_barril) == 5 and codigo_barril[:2] in ["20", "30", "58"]:
    codigo_valido = True

estilos = ["Golden", "Amber", "Vienna Lager", "Brown Ale Cafe", "Stout",
           "Session IPA", "IPA", "Maracuya", "Barley Wine", "Trigo",
           "Catharina Sour", "Gose", "Imperial IPA", "NEIPA", "Imperial Stout", "Otros"]
estilo = st.selectbox("Estilo", estilos)

estado = st.selectbox("Estado del barril", ["Despachado", "Lavado en bodega", "Sucio", "En cuarto frío"])

if estado == "Despachado":
    cliente = st.selectbox("Cliente", st.session_state.clientes)
else:
    cliente = "Planta Castiza"

responsables = ["Pepe Vallejo", "Ligia Cajigas", "Erika Martinez", "Marcelo Martinez", "Operario 1", "Operario 2"]
responsable = st.selectbox("Responsable", responsables)

if estado == "Sucio":
    observaciones = f"Último cliente: {cliente}"
else:
    observaciones = st.text_area("Observaciones")

if st.button("Guardar Registro"):
    if codigo_valido:
        data = {
            FIELDS["codigo"]: codigo_barril,
            FIELDS["estilo"]: estilo,
            FIELDS["estado"]: estado,
            FIELDS["cliente"]: cliente,
            FIELDS["responsable"]: responsable,
            FIELDS["observaciones"]: observaciones
        }
        response = requests.post(FORM_URL, data=data)
        if response.status_code == 200:
            st.success("✅ Registro enviado correctamente")
        else:
            st.error(f"❌ Error al enviar el formulario. Código de estado: {response.status_code}")
    else:
        st.warning("⚠️ Código inválido. Debe tener 5 dígitos y comenzar por 20, 30 o 58.")

st.markdown("---")

st.header("➕ Registro de Nuevo Cliente")
nuevo_cliente = st.text_input("Nombre del nuevo cliente")
if st.button("Agregar Cliente"):
    if nuevo_cliente and nuevo_cliente not in st.session_state.clientes:
        st.session_state.clientes.append(nuevo_cliente)
        st.success("✅ Cliente agregado a la lista")
    elif nuevo_cliente in st.session_state.clientes:
        st.info("⚠️ Cliente ya existe en la lista")
    else:
        st.warning("⚠️ Nombre vacío")

st.header("🗑️ Eliminar Cliente")
cliente_eliminar = st.selectbox("Selecciona cliente a eliminar", st.session_state.clientes)
if st.button("Eliminar Cliente"):
    st.session_state.clientes.remove(cliente_eliminar)
    st.success(f"✅ Cliente '{cliente_eliminar}' eliminado")

st.markdown("---")

st.header("🔍 Filtros")
st.info("Estos filtros serán funcionales cuando se agregue conexión directa a la hoja de respuestas")
st.text_input("Buscar por código de barril")
st.selectbox("Filtrar por cliente", st.session_state.clientes)
st.selectbox("Filtrar por estado", ["Despachado", "Lavado en bodega", "Sucio", "En cuarto frío"])
