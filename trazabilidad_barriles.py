import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Trazabilidad de Barriles", layout="wide")

st.title("📦 Trazabilidad de Barriles - Cervecería")

# ---- FORMULARIO DE REGISTRO ----
st.header("➕ Registrar Movimiento de Barril")

with st.form("registro_form"):
    codigo = st.text_input("Código del barril")
    if codigo:
        capacidad = "20L" if codigo.startswith("20") else "30L" if codigo.startswith("30") else "58L" if codigo.startswith("58") else "Desconocida"
        st.markdown(f"**Capacidad detectada:** {capacidad}")
    else:
        capacidad = ""

    estilo = st.selectbox("Estilo de Cerveza", ["Golden", "IPA", "APA", "Stout", "Amber", "Porter", "Sin alcohol"])
    estado = st.selectbox("Estado del Barril", ["Despacho", "Lavado en bodega", "Sucio", "En cuarto frío"])

    # Cargar clientes desde hoja de cálculo pública (hoja 'Rclientes')
    url_clientes = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR1UCCXZpPgCwU4sm_T-Hw95CjViZ63lxAEkB3gZClkhHiOmav0JWWOtbMDrjsh8PySTqXwQb_6Q5HM/pub?gid=1534553329&single=true&output=csv"
    try:
        df_clientes = pd.read_csv(url_clientes)
        clientes = df_clientes['Nombre'].tolist()
        direcciones = dict(zip(df_clientes['Nombre'], df_clientes['Dirección']))
        cliente = st.selectbox("Cliente", clientes)
        direccion_cliente = direcciones.get(cliente, "")
        st.markdown(f"**Dirección:** {direccion_cliente}")
    except Exception as e:
        st.error("Error al cargar la lista de clientes.")
        cliente = ""

    responsable = st.text_input("Responsable del Movimiento")
    observaciones = st.text_area("Observaciones Adicionales")

    if estado == "Despacho":
        mostrar_latas = st.checkbox("¿Registrar también latas en esta orden?")
        if mostrar_latas:
            latas_tipo = st.selectbox("Tipo de lata", ["473ml", "355ml"])
            latas_cantidad = st.number_input("Cantidad de latas", min_value=1, step=1)
        else:
            latas_tipo = ""
            latas_cantidad = ""
    else:
        latas_tipo = ""
        latas_cantidad = ""

    submitted = st.form_submit_button("Registrar Movimiento")

    if submitted:
        try:
            form_url = "https://docs.google.com/forms/d/e/1FAIpQLSdJ6_NiUwQn5TeDCSmrVK8mN3wckfMQoQuc7x0HfO9bVtNWlw/formResponse"
            payload = {
                "entry.311770370": codigo,
                "entry.1283669263": estilo,
                "entry.1545499818": estado,
                "entry.91059345": cliente,
                "entry.1661747572": responsable,
                "entry.1195378605": observaciones,
                "entry.1885433786": capacidad,
                "entry.248416800": latas_tipo,
                "entry.1372620529": latas_cantidad
            }
            response = requests.post(form_url, data=payload)
            if response.status_code == 200:
                st.success("✅ Movimiento registrado correctamente.")
            else:
                st.warning("Registro enviado pero el formulario puede no haberlo procesado correctamente.")
        except Exception as e:
            st.error(f"Error al enviar el formulario: {e}")

# ---- VISUALIZAR REGISTROS EXISTENTES ----
st.header("📋 Historial de Movimientos")

try:
    url_datos = "https://docs.google.com/spreadsheets/d/e/2PACX-1vR1UCCXZpPgCwU4sm_T-Hw95CjViZ63lxAEkB3gZClkhHiOmav0JWWOtbMDrjsh8PySTqXwQb_6Q5HM/pub?gid=1448936826&single=true&output=csv"
    df = pd.read_csv(url_datos)
    st.dataframe(df)
except Exception as e:
    st.error("No se pudieron cargar los registros.")
