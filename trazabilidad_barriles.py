
# ------------------ BOTÓN DE ENVÍO ------------------
if st.button("Registrar devolución"):
    if tipo_devolucion == "Barril":
        try:
            # ✅ URL del formulario de Google Forms para barriles
            url_form_barril = "https://docs.google.com/forms/d/e/1FAIpQLSedFQmZuDdVY_cqU9WdiWCTBWCCh1NosPnD891QifQKqaeUfA/formResponse"

            # 📤 Datos a enviar (asegúrate que los entry.xxx coincidan con tu formulario real)
            form_data_barril = {
                "entry.311770370": codigo_barril,          # Código del barril
                "entry.1283669263": estilo_cerveza,        # Estilo (opcional)
                "entry.1545499818": "Devolución",          # Estado fijo al devolver
                "entry.91059345": cliente,                 # Cliente
                "entry.1661747572": responsable,           # Responsable
                "entry.1465957833": observaciones,         # Observaciones
                "entry.1234567890": normalizar_lote_barril(lote_producto, agregar_prefijo_l=True),
                "entry.1437332932": normalizar_lote_barril(lote_producto, agregar_prefijo_l=True)
            }

            response = requests.post(url_form_barril, data=form_data_barril)

            if response.status_code in [200, 302]:
                st.success("✅ Devolución de barril registrada correctamente.")
            else:
                st.warning(f"⚠️ Error al enviar devolución. Código: {response.status_code}")
        except Exception as e:
            st.error(f"❌ Error al registrar devolución de barril: {e}")

    elif tipo_devolucion == "Latas":
        try:
            url_form_latas = "https://docs.google.com/forms/d/e/1FAIpQLSerxxOI1npXAptsa3nvNNBFHYBLV9OMMX-4-Xlhz-VOmitRfQ/formResponse"

            form_data_latas = {
                "entry.457965266": str(cantidad_latas),        # Cantidad
                "entry.689047838": estilo_cerveza,             # Estilo
                "entry.2096096606": lote_latas,                # Lote
                "entry.1478892985": cliente,                   # Cliente
                "entry.1774006398": responsable,               # Responsable
                "entry.1179145668": "Devolución"               # NUEVO CAMPO - Tipo de movimiento
            }

            response = requests.post(url_form_latas, data=form_data_latas)
            if response.status_code in [200, 302]:
                st.success("✅ Devolución de latas registrada correctamente.")
                st.toast("🍺 Devolución registrada")
            else:
                st.warning(f"⚠️ Error al enviar devolución. Código: {response.status_code}")
        except Exception as e:
            st.error(f"❌ Error al registrar devolución de latas: {e}")

# ------------------ REGISTRO DE BAJA DE PRODUCTO ------------------
st.markdown("---")
st.title("🗑️ Registro de Baja de Producto (Barril o Latas)")

tipo_baja = st.selectbox("Selecciona tipo de baja:", ["", "Barril", "Latas"])
responsable_baja = st.text_input("Responsable que da de baja")
observaciones_baja = st.text_area("Observaciones de baja (opcional)")
fecha_actual_baja = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

# Campos específicos
if tipo_baja == "Barril":
    codigo_barril_baja = st.text_input("Código del barril a dar de baja")
    estilo_baja_barril = st.text_input("Estilo de cerveza (opcional)")
    lote_barril_baja = st.text_input("Lote del producto (opcional)")

elif tipo_baja == "Latas":
    cantidad_latas_baja = st.number_input("Cantidad de latas a dar de baja", min_value=1, step=1)
    estilo_latas_baja = st.text_input("Estilo de cerveza")
    lote_latas_baja = st.text_input("Lote del producto")

# Botón para registrar baja
if st.button("Registrar Baja de Producto"):

    if tipo_baja == "Barril":
        try:
            url_form_barril_baja = "https://docs.google.com/forms/d/e/1FAIpQLSedFQmZuDdVY_cqU9WdiWCTBWCCh1NosPnD891QifQKqaeUfA/formResponse"

            form_data_baja_barril = {
                "entry.311770370": codigo_barril_baja,                      # Código del barril
                "entry.1283669263": estilo_baja_barril,                    # Estilo
                "entry.1545499818": "Baja",                                # Estado automático "Baja"
                "entry.1661747572": responsable_baja,                      # Responsable
                "entry.1465957833": observaciones_baja,                    # Observaciones
                "entry.1234567890": normalizar_lote_barril(lote_barril_baja, agregar_prefijo_l=True),
                "entry.1437332932": lote_barril_baja                       # Repetido si es necesario
            }

            response = requests.post(url_form_barril_baja, data=form_data_baja_barril)
            if response.status_code in [200, 302]:
                st.success("✅ Baja de barril registrada correctamente.")
                st.balloons()
            else:
                st.warning(f"⚠️ Error al registrar baja. Código: {response.status_code}")
        except Exception as e:
            st.error(f"❌ Error al registrar baja de barril: {e}")

    elif tipo_baja == "Latas":
        try:
            url_form_latas_baja = "https://docs.google.com/forms/d/e/1FAIpQLSerxxOI1npXAptsa3nvNNBFHYBLV9OMMX-4-Xlhz-VOmitRfQ/formResponse"

            form_data_baja_latas = {
                "entry.457965266": str(cantidad_latas_baja),              # Cantidad
                "entry.689047838": estilo_latas_baja,                     # Estilo
                "entry.2096096606": lote_latas_baja,                      # Lote
                "entry.1774006398": responsable_baja,                     # Responsable
                "entry.1179145668": "Baja"                                # Campo adicional para indicar baja
            }

            response = requests.post(url_form_latas_baja, data=form_data_baja_latas)
            if response.status_code in [200, 302]:
                st.success("✅ Baja de latas registrada correctamente.")
                st.snow()
            else:
                st.warning(f"⚠️ Error al registrar baja. Código: {response.status_code}")
        except Exception as e:
            st.error(f"❌ Error al registrar baja de latas: {e}")
