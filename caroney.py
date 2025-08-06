import streamlit as st
import pandas as pd
from io import BytesIO
import datetime
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 🔐 Conectar con Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
service_account_info = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
client = gspread.authorize(creds)
sheet = client.open("carodb").sheet1  # Asegúrate que así se llame tu hoja

# Configuración inicial
st.set_page_config(page_title="Caroney", layout="centered")
st.title("💸 Caroney - Tu contabilidad sencilla... se supone")
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
    # Construir la fila limpiamente
        row = [
        str(date),
        float(amount if type_ == "Ingreso" else -amount),
        str(type_).strip(),
        str(category).strip() if category else "Sin categoría",
        str(description).strip() if description else ""
    ]

        # Mostrar para depurar
        st.write("Fila que se va a guardar:", row)
    
        # Guardar en el estado de sesión
        st.session_state.records.append({
            "Fecha": str(date),
            "Monto": row[1],
            "Tipo": row[2],
            "Categoría": row[3],
            "Descripción": row[4]
        })
    
        # Guardar en Google Sheets
        sheet.append_row(row)
        st.success("Movimiento agregado ✅")


# Mostrar datos
if st.session_state.records:
    df = pd.DataFrame(st.session_state.records)

    df["Fecha"] = pd.to_datetime(df["Fecha"])
    hoy = datetime.date.today()
    df_dia = df[df["Fecha"].dt.date == hoy]

    st.subheader("📅 Movimientos de hoy")
    st.dataframe(df_dia, use_container_width=True)

    ingresos_hoy = df_dia[df_dia["Tipo"] == "Ingreso"]["Monto"].sum()
    egresos_hoy = -df_dia[df_dia["Tipo"] == "Egreso"]["Monto"].sum()
    balance_hoy = df_dia["Monto"].sum()

    st.markdown(f"**Ingresos hoy:** ${ingresos_hoy:.2f}")
    st.markdown(f"**Egresos hoy:** ${egresos_hoy:.2f}")
    st.markdown(f"**Balance hoy:** ${balance_hoy:.2f}")
    
    
    if "mostrar_filtro" not in st.session_state:
        st.session_state.mostrar_filtro = False

    if st.button("📆 Filtrar por fechas"):
        st.session_state.mostrar_filtro = not st.session_state.mostrar_filtro

    if st.session_state.mostrar_filtro:
        min_date = df["Fecha"].min().date()
        max_date = df["Fecha"].max().date()
    
        start_date, end_date = st.date_input(
            "Selecciona el rango:",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date
        )
    
        filtro = (df["Fecha"].dt.date >= start_date) & (df["Fecha"].dt.date <= end_date)
        df_filtro = df[filtro]
    
        st.subheader("📆 Movimientos filtrados")
        st.dataframe(df_filtro, use_container_width=True)
    
        ingresos_f = df_filtro[df_filtro["Tipo"] == "Ingreso"]["Monto"].sum()
        egresos_f = -df_filtro[df_filtro["Tipo"] == "Egreso"]["Monto"].sum()
        balance_f = df_filtro["Monto"].sum()
    
        st.markdown(f"**Ingresos filtrados:** ${ingresos_f:.2f}")
        st.markdown(f"**Egresos filtrados:** ${egresos_f:.2f}")
        st.markdown(f"**Balance filtrado:** ${balance_f:.2f}")
    
        towrite = BytesIO()
        df_filtro.to_excel(towrite, index=False, sheet_name="Caroney")
        towrite.seek(0)
        st.download_button("📥 Descargar Excel filtrado", towrite, "caroney_filtrado.xlsx")
            
    if "mostrar_historial_completo" not in st.session_state:
        st.session_state.mostrar_historial_completo = False
        
    if st.button("📖 Ver todos los movimientos"):
        st.session_state.mostrar_historial_completo = not st.session_state.mostrar_historial_completo
   
    if st.session_state.mostrar_historial_completo:
        st.subheader("📋 Historial completo")
        st.dataframe(df, use_container_width=True)

        total_ingresos = df[df["Tipo"] == "Ingreso"]["Monto"].sum()
        total_egresos = -df[df["Tipo"] == "Egreso"]["Monto"].sum()
        balance_total = df["Monto"].sum()

        st.markdown(f"**Total de ingresos:** ${total_ingresos:.2f}")
        st.markdown(f"**Total de egresos:** ${total_egresos:.2f}")
        st.markdown(f"**Balance general:** ${balance_total:.2f}")

        from openpyxl import Workbook
        from openpyxl.utils.dataframe import dataframe_to_rows
        from openpyxl.styles import Font, Alignment

        df_export = df.copy()
        df_export["Fecha"] = pd.to_datetime(df_export["Fecha"]).dt.date

        resumen = pd.DataFrame([
            {"Fecha": "TOTAL", "Monto": total_ingresos, "Tipo": "Ingreso", "Descripción": "Ingresos totales"},
            {"Fecha": "TOTAL", "Monto": total_egresos, "Tipo": "Egreso", "Descripción": "Egresos totales"},
            {"Fecha": "TOTAL", "Monto": balance_total, "Descripción": "Balance neto"}
        ])

        df_export = pd.concat([df_export, pd.DataFrame([{}]), resumen], ignore_index=True)

        wb = Workbook()
        ws = wb.active
        ws.title = "Caroney"

        for r in dataframe_to_rows(df_export, index=False, header=True):
            ws.append(r)

        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center")

        for col in ws.columns:
            max_len = max(len(str(cell.value)) if cell.value else 0 for cell in col)
            ws.column_dimensions[col[0].column_letter].width = max_len + 2

        from openpyxl import Workbook
        from openpyxl.utils.dataframe import dataframe_to_rows
        from openpyxl.styles import Font, Alignment, Border, Side

        df_export = df.copy()
        df_export["Fecha"] = pd.to_datetime(df_export["Fecha"]).dt.date

        resumen = pd.DataFrame([
            {"Fecha": "TOTAL", "Monto": total_ingresos, "Tipo": "Ingreso", "Descripción": "Ingresos totales"},
            {"Fecha": "TOTAL", "Monto": total_egresos, "Tipo": "Egreso", "Descripción": "Egresos totales"},
            {"Fecha": "TOTAL", "Monto": balance_total, "Descripción": "Balance neto"}
        ])

        df_export = pd.concat([df_export, pd.DataFrame([{}]), resumen], ignore_index=True)

        wb = Workbook()
        ws = wb.active
        ws.title = "Caroney"

        for r in dataframe_to_rows(df_export, index=False, header=True):
            ws.append(r)

        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(horizontal="center")

        for col in ws.columns:
            max_len = max(len(str(cell.value)) if cell.value else 0 for cell in col)
            ws.column_dimensions[col[0].column_letter].width = max_len + 2

        thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin")
        )

        for row in ws.iter_rows(min_row=1, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
            for cell in row:
                if cell.value is not None:
                    cell.border = thin_border

        towrite_full = BytesIO()
        wb.save(towrite_full)
        towrite_full.seek(0)
        st.download_button("📥 Descargar Excel completo", towrite_full, "caroney_completo.xlsx")



else:
    st.info("Aún no has registrado nada.")