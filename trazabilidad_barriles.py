import streamlit as st
import requests
import pandas as pd

# ------------------------------
# TÍTULO PRINCIPAL
st.title("🍺 App de Trazabilidad de Barriles - Cervecería")

# ------------------------------
# LECTURA DE CLIENTES DESDE HOJA GOOGLE SHEETS
url_hoja_clientes = "https://docs.google.com/spreadsheets/d/e/1FAIpQLScllMMM33p5F--_I6Y80gsLUsusGMTk0OA3XDVC9ocngoc2Hw/gviz/tq?tqx=out:csv&sheet=Rclientes"

try:
    df_clientes = pd.read_csv(url_hoja_clientes)
    lista_clientes = df_clientes["Nombre"].dropna().tolist()
except Exception as e:
    st.error(f"❌ Error al cargar clientes: {e}")
    lista_clientes = []

# ------------------------------
# FORMULARIO PRINCIPAL
with st.form("formulario_barriles"):
    st.subheader("📋 Registro de Movimiento de Barriles")

    codigo = st.text_input("Código del Barril (Ej: 20XXX, 30XXX, 58XXX)", max_chars=10)

    estilos = ["IPA", "Lager", "Stout", "Pale Ale", "Amber", "Porter", "Wheat", "Otro"]
    estilo = st.selectbox("Estilo de Cerveza", estilos)

    estado = st.selectbox("Estado del Barril", ["Despachado", "Lavado en bodega", "Sucio", "En cuarto frío"])

    cliente = st.selectbox("Cliente", lista_clientes if lista_clientes else ["No disponible"])

    responsable = st.text_input("Responsable del Movimiento")

    lote_producto = st.text_input("Lote del Producto (9 dígitos: DDMMYYXXX)", max_chars=9, help="Ej: 140325001")

    observaciones = st.text_area("Observaciones Adicionales")

    # Variables por defecto
    incluir_latas = "No"
    cantidad_latas = ""
    lote_latas = ""

    # Si el estado es Despachado, mostrar sección extra para despacho de latas
    if estado == "Despachado":
        incluir_latas = st.selectbox("¿Incluye despacho de Latas de Cerveza?", ["No", "Sí"])
        if incluir_latas == "Sí":
            cantidad_latas = st.number_input("Cantidad de Latas Despachadas", min_value=0, step=1)
            lote_latas = st.text_input("Lote de las Latas (9 dígitos: DDMMYYXXX)", max_chars=9)

    # Botón de envío
    enviado = st.form_submit_button("✅ Enviar Registro")

# ------------------------------
# ENVÍO A GOOGLE FORMS
if enviado:
    try:
        # URL del formulario de Google Forms (reemplazar con tu URL real)
        url_formulario = "https://docs.google.com/forms/d/e/1FAIpQLSfL2RQWBjJ2oLBTRIXA7wq8xS8Q_fyi7PEPrxSWea-Dwr6a-Q/formResponse"

        # Diccionario de campos con sus códigos "entry"
        datos_formulario = {
            "entry.311770370": codigo,
            "entry.1283669263": estilo,
            "entry.1545499818": estado,
            "entry.91059345": cliente,
            "entry.1661747572": responsable,
            "entry.632654837": lote_producto,  # <- Campo NUEVO: Lote del producto
            "entry.1195378605": observaciones,
        }

        # Agregar información adicional solo si aplica
        if estado == "Despachado" and incluir_latas == "Sí":
            info_latas = f"{int(cantidad_latas)} latas - Lote: {lote_latas}"
            datos_formulario["entry.2024031401"] = info_latas  # <- Campo NUEVO: Info de latas (añadir en tu Form)

        # Envío de datos
        response = requests.post(url_formulario, data=datos_formulario)

        if response.status_code == 200 or response.status_code == 302:
            st.success("✅ Registro enviado exitosamente.")
        else:
            st.warning("⚠️ Registro enviado, pero no se recibió respuesta clara del formulario.")

    except Exception as e:
        st.error(f"❌ Error al enviar los datos: {e}")
