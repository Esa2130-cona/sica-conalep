import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import os

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="SICA Conalep Cuautla", layout="wide", page_icon="🛡️")

# Estilos visuales
st.markdown("""
    <style>
    .stApp { background-color: #f0f2f6; color: white; }
    .big-font { font-size:35px !important; font-weight: bold; color: #2ecc71; }
    .status-box { padding: 20px; border-radius: 15px; text-align: center; font-size: 25px; background-color: #1e272e; border: 2px solid #2ecc71; }
    .aviso-box { padding: 15px; background-color: #f1c40f; color: black; border-radius: 10px; font-weight: bold; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN A GOOGLE SHEETS (NUEVO LINK) ---
# He configurado el link para que fuerce la descarga del CSV y evitar el Error 400
SHEET_ID = "11RZyoBo_MyQkGWfc21WCY_xPFZdKkwTG12YagiZf3yM"
URL_CSV = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

@st.cache_data(ttl=10)
def cargar_base():
    try:
        df = pd.read_csv(URL_CSV)
        # Limpiamos nombres de columnas por si acaso hay espacios en el Excel
        df.columns = df.columns.str.strip()
        if 'MATRICULA' in df.columns:
            df['MATRICULA'] = df['MATRICULA'].astype(str).str.strip()
            return df.set_index('MATRICULA')
        else:
            st.error("No se encontró la columna 'MATRICULA' en el archivo.")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return pd.DataFrame()

db = cargar_base()

# --- 3. USUARIOS ---
usuarios = {
    "admin": {"pin": "2026", "rol": "Administrador", "nombre": "Admin General"},
    "prefectura": {"pin": "1234", "rol": "Prefectura", "nombre": "Prefecto de Turno"},
    "escolares": {"pin": "5678", "rol": "Servicios Escolares", "nombre": "Control Escolar"}
}

if 'user' not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.title("🛡️ SICA - CONALEP CUAUTLA")
    with st.container(border=True):
        u = st.text_input("Usuario")
        p = st.text_input("PIN", type="password")
        if st.button("INGRESAR", use_container_width=True):
            if u in usuarios and usuarios[u]["pin"] == p:
                st.session_state.user = usuarios[u]
                st.rerun()
            else:
                st.error("PIN o Usuario incorrecto")
    st.stop()

# --- 4. PANEL DE CONTROL ---
user = st.session_state.user
st.sidebar.title(f"👤 {user['nombre']}")

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.user = None
    st.rerun()

# --- 5. INTERFAZ DE ENTRADA ---
if user['rol'] in ["Prefectura", "Administrador"]:
    st.header("🚀 Registro de Entrada")
    
    if 'scanned' not in st.session_state:
        st.session_state.scanned = ""

    def on_scan():
        # CORRECCIÓN INMEDIATA DE LA COMILLA POR GUION
        raw = st.session_state.barcode
        st.session_state.scanned = raw.replace("'", "-").strip()
        st.session_state.barcode = ""

    st.text_input("👇 ESCANEE AQUÍ", key="barcode", on_change=on_scan)
    
    # Doble limpieza al asignar la variable para la búsqueda
    mat = st.session_state.scanned.replace("'", "-").strip()

    if mat:
        if mat in db.index:
            al = db.loc[mat]
            c1, c2 = st.columns([1, 2])
            with c1:
                # Mostrar foto o imagen genérica
                foto = f"Fotos-Alumnos/{mat}.jpg"
                if os.path.exists(foto):
                    st.image(foto, width=280)
                else:
                    st.info("📷 Foto no disponible")
            
            with c2:
                st.markdown(f"<p class='big-font'>{al['NOMBRE']} {al['PRIMER APELLIDO']}</p>", unsafe_allow_html=True)
                st.write(f"### Grupo: {al['GRUPO']}")
                
                # Avisos
                aviso = al.get('AVISO_ENTRADA', "")
                if pd.notna(aviso) and aviso != "":
                    st.markdown(f"<div class='aviso-box'>📢 AVISO: {aviso}</div>", unsafe_allow_html=True)

                st.markdown(f"<div class='status-box'>✅ ACCESO REGISTRADO<br>{datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)
        else:
            st.error(f"❌ Matrícula {mat} no encontrada.")

# --- 6. ADMINISTRACIÓN ---
if user['rol'] in ["Servicios Escolares", "Administrador"]:
    st.divider()
    st.subheader("🔍 Buscador de Expedientes")
    busc = st.text_input("Matrícula a consultar").replace("'", "-").strip()
    if busc in db.index:
        st.table(db.loc[[busc]])


