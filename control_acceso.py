import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import os
import pytz

# --- CONFIGURACIÓN ---
SHEET_ID = "11RZyoBo_MyQkGWfc21WCY_xPFZdKkwTG12YagiZf3yM"
# URL de lectura para las distintas pestañas
URL_ALUMNOS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
URL_ACADEMICO = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=1114227031"
URL_INCIDENCIAS = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=569107936"
# URL de tu Webhook (Google Apps Script) para guardar
WEBHOOK_URL = "TU_URL_DE_APPS_SCRIPT_AQUI" 

zona_horaria = pytz.timezone('America/Mexico_City')

st.set_page_config(page_title="SICA Conalep", layout="wide")

# Estilos Institucionales
st.markdown("""
    <style>
    .stApp { background-color: #F8F9FA; }
    .big-font { font-size:38px !important; font-weight: bold; color: #006437; }
    .status-box { padding: 20px; border-radius: 15px; background-color: #FFFFFF; border: 3px solid #006437; color: #006437; text-align: center; box-shadow: 0px 4px 10px rgba(0,0,0,0.1); }
    .aviso-box { padding: 15px; background-color: #FFF3CD; color: #856404; border-radius: 10px; border-left: 8px solid #FFC107; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- CARGA DE DATOS ---
@st.cache_data(ttl=10)
def cargar_datos(url):
    try:
        df = pd.read_csv(url)
        if 'MATRICULA' in df.columns:
            df['MATRICULA'] = df['MATRICULA'].astype(str).str.strip()
            return df
        return df
    except: return pd.DataFrame()

df_alumnos = cargar_datos(URL_ALUMNOS).set_index('MATRICULA') if not cargar_datos(URL_ALUMNOS).empty else pd.DataFrame()
df_academico = cargar_datos(URL_ACADEMICO).set_index('MATRICULA') if not cargar_datos(URL_ACADEMICO).empty else pd.DataFrame()
df_incidencias = cargar_datos(URL_INCIDENCIAS)

# --- SISTEMA DE USUARIOS ---
# Puedes agregar aquí los usuarios que tienes en tu pestaña 'Usuarios'
usuarios = {"admin": "2026", "prefecto": "1234", "escolares": "5678"}

if 'user' not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.title("🛡️ Acceso SICA")
    u = st.text_input("Usuario")
    p = st.text_input("PIN", type="password")
    if st.button("Entrar"):
        if u in usuarios and usuarios[u] == p:
            st.session_state.user = u
            st.rerun()
    st.stop()

# --- FUNCION PARA GUARDAR REPORTES ---
def enviar_reporte(mat, tipo, desc=""):
    try:
        datos = {
            "pestana": "Incidencias",
            "matricula": mat,
            "tipo": tipo,
            "descripcion": desc,
            "usuario": st.session_state.user
        }
        requests.post(WEBHOOK_URL, json=datos)
        st.toast(f"✅ {tipo} guardado en la nube")
    except:
        st.error("Error al conectar con la base de datos para guardar.")

# --- VISTA PREFECTURA (ENTRADA Y REPORTES) ---
st.sidebar.button("Cerrar Sesión", on_click=lambda: st.session_state.update({"user": None}))

menu = st.sidebar.radio("Menú", ["Acceso Estudiantil", "Consulta Historial", "Servicios Escolares"])

if menu == "Acceso Estudiantil":
    st.title("🚀 Control de Entrada")
    if 'scanned' not in st.session_state: st.session_state.scanned = ""
    
    def on_scan():
        st.session_state.scanned = st.session_state.barcode.replace("'", "-").strip()
        st.session_state.barcode = ""

    st.text_input("👇 ESCANEE AQUÍ", key="barcode", on_change=on_scan)
    mat = st.session_state.scanned

    if mat in df_alumnos.index:
        al = df_alumnos.loc[mat]
        c1, c2 = st.columns([1, 2])
        with c1:
            st.image(f"Fotos-Alumnos/{mat}.jpg", width=300) # O icono por defecto
        with c2:
            st.markdown(f"<p class='big-font'>{al['NOMBRE']} {al['PRIMER APELLIDO']}</p>", unsafe_allow_html=True)
            st.write(f"### Grupo: {al['GRUPO']}")
            
            # Mostrar Aviso
            if pd.notna(al.get('AVISO_ENTRADA')):
                st.markdown(f"<div class='aviso-box'>📢 AVISO: {al['AVISO_ENTRADA']}</div>", unsafe_allow_html=True)
            
            st.markdown(f"<div class='status-box'>✅ ACCESO: {datetime.now(zona_horaria).strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)
            
            # BOTONES DE REPORTE RÁPIDO
            st.divider()
            col_a, col_b = st.columns(2)
            if col_a.button("⏰ REGISTRAR RETARDO"):
                enviar_reporte(mat, "RETARDO")
            if col_b.button("🚫 REPORTE DISCIPLINA"):
                motivo = st.text_input("Motivo del reporte")
                if st.button("Confirmar Reporte"):
                    enviar_reporte(mat, "DISCIPLINA", motivo)

# --- VISTA ADMINISTRACIÓN (CONSULTA 360) ---
elif menu == "Consulta Historial":
    st.title("🔍 Buscador Integral de Alumnos")
    busc = st.text_input("Matrícula del alumno").replace("'", "-").strip()
    
    if busc in df_alumnos.index:
        # 1. Datos Personales
        al = df_alumnos.loc[busc]
        st.subheader(f"Expediente de {al['NOMBRE']} {al['PRIMER APELLIDO']}")
        
        # 2. Datos Académicos (de la pestaña Academico)
        if busc in df_academico.index:
            ac = df_academico.loc[busc]
            col1, col2, col3 = st.columns(3)
            col1.metric("Promedio General", ac.get('PROMEDIO_GENERAL', 'N/A'))
            col2.metric("Materias Adeudadas", ac.get('MATERIAS_ADEUDADAS', '0'))
            col3.warning(f"Estado: {ac.get('ESTADO_ACADEMICO', 'Regular')}")
        
        # 3. Historial de Incidencias (de la pestaña Incidencias)
        st.write("---")
        st.write("### 📜 Historial de Reportes y Retardos")
        mis_reportes = df_incidencias[df_incidencias['MATRICULA'] == busc]
        if not mis_reportes.empty:
            st.dataframe(mis_reportes, use_container_width=True)
        else:
            st.success("Este alumno no cuenta con reportes de conducta.")

elif menu == "Servicios Escolares":
    st.title("📢 Gestión de Avisos")
    st.info("Para modificar avisos o datos académicos, puedes usar los formularios de aquí o editar el Google Sheets directamente.")
    st.link_button("Abrir Google Sheets", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}")
