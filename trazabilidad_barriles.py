import streamlit as st
import requests
import pandas as pd

# ============================
# CONFIGURACIÓN DEL FORMULARIO GOOGLE LATAS
# ============================
FORM_URL_LATAS = "https://docs.google.com/forms/d/e/1FAIpQLSerxxOI1npXAptsa3nvNNBFHYBLV9OMMX-4-Xlhz-VOmitRfQ/formResponse"

# Campos del formulario (entry.xxxxx)
ENTRY_ESTILO = "entry.689047838"
ENTRY_CANTIDAD = "entry.457965266"
ENTRY_LOTE = "entry.2096096606"
ENTRY_CLIENTE = "entry.1478892985"
ENTRY_RESPONSABLE = "entry.1774006398"

# URL de hoja de cálculo de latas (solo para lectura, los datos se ven reflejados ahí automáticamente)
URL_HOJA_DATOS_LATAS = "https://docs.google.com/spreadsheets/d/1FjQ8XBDwDdrlJZsNkQ6YyaygkHLhpKmfLBv6wd3uluY/export?format=csv&gid=0"

# ============================
# FUNCIÓN PARA ENVIAR DATOS AL FORMULARIO DE LATAS
# ============================
def enviar_lote_latas(estilo, cantidad, lote, cliente, responsable):
    form_data = {
        ENTRY_ESTILO: estilo,
        ENTRY_CANTIDAD: cantidad,
        ENTRY_LOTE: lote,
        ENTRY_CLIENTE: cliente,
        ENTRY_RESPONSABLE: responsable
    }
    response = requests.post(FORM_URL_LATAS, data=form_data)
    return response.status_code == 200 or response.status_code == 302

# ============================
# INTERFAZ STREAMLIT
# ============================
st.set_page_config(page_title="Registro de Latas", page_icon="🍺")
st.title("📦 Registro de Despacho de Latas")

st.subheader("➕ Registrar Despacho de Latas")

# Primer lote
with st.form(key="form_lote_latas"):
    st.markdown("### Lote Principal")
    estilo_1 = st.text_input("Estilo")
    cantidad_1 = st.number_input("Cantidad", min_value=1, step=1)
    lote_1 = st.text_input("Lote")
    cliente_1 = st.text_input("Cliente")
    responsable_1 = st.text_input("Responsable")
    
    # Sección para múltiples lotes opcionales
    st.markdown("### ➕ Agregar Otro Lote (Opcional)")
    agregar_otro = st.checkbox("Agregar otro lote de latas")

    estilo_2 = cantidad_2 = lote_2 = cliente_2 = responsable_2 = None
    if agregar_otro:
        estilo_2 = st.text_input("Estilo (Segundo lote)", key="estilo2")
        cantidad_2 = st.number_input("Cantidad (Segundo lote)", min_value=1, step=1, key="cantidad2")
        lote_2 = st.text_input("Lote (Segundo lote)", key="lote2")
        cliente_2 = st.text_input("Cliente (Segundo lote)", key="cliente2")
        responsable_2 = st.text_input("Responsable (Segundo lote)", key="responsable2")

    submitted = st.form_submit_button("📤 Enviar Registro")

    if submitted:
        if not estilo_1 or not cantidad_1 or not lote_1 or not cliente_1 or not responsable_1:
            st.warning("Por favor completa todos los campos del lote principal.")
        else:
            exito1 = enviar_lote_latas(estilo_1, cantidad_1, lote_1, cliente_1, responsable_1)
            if exito1:
                st.success("✅ Lote principal enviado correctamente.")
            else:
                st.error("❌ Error al enviar el lote principal.")

            if agregar_otro:
                if not estilo_2 or not cantidad_2 or not lote_2 or not cliente_2 or not responsable_2:
                    st.warning("Debes completar todos los campos del segundo lote si marcaste la opción.")
                else:
                    exito2 = enviar_lote_latas(estilo_2, cantidad_2, lote_2, cliente_2, responsable_2)
                    if exito2:
                        st.success("✅ Segundo lote enviado correctamente.")
                    else:
                        st.error("❌ Error al enviar el segundo lote.")

# ============================
# MOSTRAR DATOS DESDE GOOGLE SHEETS
# ============================
st.subheader("📄 Registros Actuales de Latas")

try:
    df_latas = pd.read_csv(URL_HOJA_DATOS_LATAS)
    st.dataframe(df_latas, use_container_width=True)
except Exception as e:
    st.error("No se pudo cargar la hoja de registros de latas.")
    st.exception(e)
