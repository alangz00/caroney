import streamlit as st
import pandas as pd
from io import BytesIO
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 🔐 Conectar con Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)
sheet = client.open("CaroneyDB").sheet1  # Asegúrate que así se llame tu hoja

# Configuración inicial
st.set_page_config(page_title="Caroney", layout="centered")
st.title("💸 Caroney - alan es un zoquete Tu contabilidad sencilla, prrrfff")
st.markdown("Registra tus ingresos y egresos de forma compacta y bonita. ¡Hecho con cariño!")

# Leer registros guardados en la hoja
if 'records' not in st.session_state:
    sheet_data = sheet.get_all_records()
    st.session_state.records = sheet_data

# Formulario de entrada
with st.form("entry_form"):
    col1, col2 = st.columns(2)
    with col1:
        date = st.date_input("Fecha")
        amount = st.number_input("Monto", min_value=0.0, step=0.01)
    with col2:
        type_ = st.selectbox("Tipo", ["Ingreso", "Egreso"])
        category = st.text_input("Categoría (ej. comida, renta)")

    description = st.text_input("Descripción")
    submitted = st.form_submit_button("Agregar")

    if submitted:
        st.session_state.records.append({
            "Fecha": str(date),
            "Monto": amount if type_ == "Ingreso" else -amount,
            "Tipo": type_,
            "Categoría": category,
            "Descripción": description
        })
        sheet.append_row([str(date), amount if type_ == "Ingreso" else -amount, type_, category, description])
        st.success("Movimiento agregado ✅")

# Mostrar datos
if st.session_state.records:
    df = pd.DataFrame(st.session_state.records)
    st.subheader("📋 Historial")
    st.dataframe(df, use_container_width=True)

    # Totales
    total_ingresos = df[df["Tipo"] == "Ingreso"]["Monto"].sum()
    total_egresos = -df[df["Tipo"] == "Egreso"]["Monto"].sum()
    balance = df["Monto"].sum()

    st.markdown("---")
    st.markdown(f"**Total de ingresos:** ${total_ingresos:.2f}")
    st.markdown(f"**Total de egresos:** ${total_egresos:.2f}")
    st.markdown(f"**Balance actual:** ${balance:.2f}")

    # Descargar como Excel
    towrite = BytesIO()
    df.to_excel(towrite, index=False, sheet_name="Caroney")
    towrite.seek(0)
    st.download_button("📥 Descargar Excel", towrite, "caroney.xlsx")

else:
    st.info("Aún no has registrado nada.")
