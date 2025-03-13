import streamlit as st
import requests
import pandas as pd

# Lista dinámica de clientes (inicialmente vacía o con algunos predefinidos)
if "clientes" not in st.session_state:
    st.session_state.clientes = ["Castiza Av. Estudiantes", "Bendita Birra CC sebastian Belalcazar", "Baruk", "Sandona Plaza",
                                  "El Barril", "La estiba las cuadras", "La estiba Villaflor"]

# Título principal
st.title("🍺 Trazabilidad de Barriles Castiza")

# --- Registro de barril ---
st.header("📋 Registro de Barril")
codigo_barril = st.text_input("Código del barril")

estilos = ["Golden", "Amber", "Vienna Lager", "Brown Ale Cafe", "Stout",
           "Session IPA", "IPA", "Maracuya", "Barley Wine", "Trigo", "Catharina Sour",
           "Gose", "Imperial IPA", "NEIPA", "Imperial Stout", "Otros"]
estilo_cerveza = st.selectbox("Estilo", estilos)

estado_barril = st.selectbox("Estado del barril", ["Despachado", "Lavado en bodega", "Sucio", "En cuarto frío"])

# Cliente solo se muestra si estado es Despachado
cliente = "Planta Castiza"
if estado_barril == "Despachado":
    cliente = st.selectbox("Cliente", st.session_state.clientes)

responsables = ["Pepe Vallejo", "Ligia Cajigas", "Erika Martinez", "Marcelo Martinez", "Operario 1", "Operario 2"]
responsable = st.selectbox("Responsable", responsables)

observaciones = st.text_area("Observaciones")

if st.button("Guardar Registro"):
    if codigo_barril and responsable:
        # Enviar los datos al formulario
        form_url = "https://docs.google.com/forms/d/e/1FAIpQLSedFQmZuDdVY_cqU9WdiWCTBWCCh1NosPnD891QifQKqaeUfA/formResponse"
        form_data = {
            "entry.311770370": codigo_barril,
            "entry.1283669263": estilo_cerveza,
            "entry.1545499818": estado_barril,
            "entry.91059345": cliente,
            "entry.1661747572": responsable,
            "entry.1465957833": observaciones
        }
        response = requests.post(form_url, data=form_data)
        if response.status_code == 200:
            st.success("✅ Registro enviado correctamente")
        else:
            st.error(f"❌ Error al enviar el formulario. Código de estado: {response.status_code}")
    else:
        st.warning("⚠️ Por favor, complete todos los campos obligatorios")

# --- Registrar nuevo cliente ---
st.header("➕ Registrar nuevo cliente")
nuevo_cliente = st.text_input("Nombre del nuevo cliente")
if st.button("Agregar Cliente"):
    if nuevo_cliente.strip():
        if nuevo_cliente not in st.session_state.clientes:
            st.session_state.clientes.append(nuevo_cliente.strip())
            st.success("✅ Cliente agregado a la lista")
        else:
            st.warning("⚠️ El cliente ya existe")
    else:
        st.warning("⚠️ Ingrese un nombre válido")

# --- Eliminar cliente ---
st.header("🗑️ Eliminar cliente")
cliente_a_eliminar = st.selectbox("Selecciona un cliente a eliminar", st.session_state.clientes)
if st.button("Eliminar Cliente"):
    st.session_state.clientes.remove(cliente_a_eliminar)
    st.success(f"✅ Cliente '{cliente_a_eliminar}' eliminado correctamente")

# --- Filtros (visualización futura) ---
st.header("🔍 Filtros de búsqueda")
st.text_input("Filtrar por Código de Barril")
st.selectbox("Filtrar por Cliente", st.session_state.clientes)
st.selectbox("Filtrar por Estado del Barril", ["Todos", "Despachado", "Lavado en bodega", "Sucio", "En cuarto frío"])
