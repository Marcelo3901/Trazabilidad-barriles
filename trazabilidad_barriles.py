import streamlit as st
import requests
import datetime

st.set_page_config(page_title="Trazabilidad Barriles - Google Forms", layout="centered")
st.title("📦 Trazabilidad de Barriles - Enviar a Google Forms")

# Formulario principal
st.subheader("📋 Registro de Barril")
fecha = st.date_input("Fecha", value=datetime.date.today())
codigo = st.text_input("Código del barril")

# Determinar capacidad
capacidad = ""
if codigo.startswith("20") and len(codigo) == 5:
    capacidad = "20L"
elif codigo.startswith("30") and len(codigo) == 5:
    capacidad = "30L"
elif codigo.startswith("58") and len(codigo) == 5:
    capacidad = "58L"

estilos = ["Golden", "Amber", "Vienna Lager", "Brown Ale Cafe", "Stout",
           "Session IPA", "IPA", "Maracuya", "Barley Wine", "Trigo", "Catharina Sour",
           "Gose", "Imperial IPA", "NEIPA", "Imperial Stout", "Otros"]
estilo = st.selectbox("Estilo", estilos)

estado = st.selectbox("Estado del barril", ["Despachado", "Lavado en bodega", "Sucio", "En cuarto frío"])

clientes = ["Castiza Av. Estudiantes", "Bendita Birra CC sebastian Belalcazar", "Baruk", "Sandona Plaza",
            "El Barril", "La estiba las cuadras", "La estiba Villaflor"]
cliente = st.selectbox("Cliente", clientes)

responsables = ["Pepe Vallejo", "Ligia Cajigas", "Erika Martinez", "Marcelo Martinez", "Operario 1", "Operario 2"]
responsable = st.selectbox("Responsable", responsables)

observaciones = st.text_area("Observaciones")

# Enviar datos al formulario
if st.button("Enviar a Google Forms"):
    if not codigo or not capacidad:
        st.warning("⚠️ Código inválido o no reconocido (debe comenzar por 20, 30 o 58 y tener 5 dígitos)")
    else:
        form_url = "https://docs.google.com/forms/d/e/1FAIpQLSedFQmZuDdVY_cqU9WdiWCTBWCCh1NosPnD891QifQKqaeUfA/formResponse"

        payload = {
               "entry.311770370": codigo,
                # "entry.1839807382": capacidad,  ←  removido temporalmente
                "entry.1283669263": estilo,
                "entry.1545499818": estado,
                "entry.91059345": cliente,
                "entry.1661747572": responsable,
                "entry.1195378605": observaciones
        }

        response = requests.post(form_url, data=payload)

        if response.status_code == 200 or response.status_code == 302:
            st.success("✅ Registro enviado correctamente al formulario")
        else:
            st.error(f"❌ Error al enviar el formulario. Código de estado: {response.status_code}")
