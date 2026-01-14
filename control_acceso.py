import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import os
import pytz # NUEVA LIBRERÍA PARA LA HORA

# --- 1. CONFIGURACIÓN Y ESTILO VISUAL ---
st.set_page_config(page_title="SICA Conalep Cuautla", layout="wide", page_icon="🛡️")

# Definimos la zona horaria de México
zona_horaria = pytz.timezone('America/Mexico_City')

st.markdown("""
    <style>
    .stApp { background-color: #F8F9FA; color: #212529; }
    h1, h2, h3, h4 { color: #006437 !important; font-family: 'Segoe UI', sans-serif; }
    .big-font { font-size:38px !important; font-weight: bold; color: #006437; line-height: 1.2; }
    .status-box { 
        padding: 25px; border-radius: 20px; text-align: center; font-size: 28px; 
        background-color: #FFFFFF; border: 3px solid #006437; color: #006437;
        box-shadow: 0px 4px 15px rgba(0,0,0,0.1); margin-top: 15px;
    }
    .aviso-box { 
        padding: 15px; background-color: #FFF3CD; color: #856404; 
        border-radius: 12px; font-weight: bold; margin-bottom: 15px;
        border-left: 8px solid #FFC107;
    }
    .stTextInput label { color: #006437 !important; font-size: 18px !important; font-weight: bold !important; }
    [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #E9ECEF; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN A GOOGLE SHEETS ---
SHEET_ID = "11RZyoBo_MyQkGWfc21WCY_xPFZdKkwTG12YagiZf3yM"
URL_CSV = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

@st.cache_data(ttl=10)
def cargar_base():
    try:
        df = pd.read_csv(URL_CSV)
        df.columns = df.columns.str.strip()
        if 'MATRICULA' in df.columns:
            df['MATRICULA'] = df['MATRICULA'].astype(str).str.strip()
            return df.set_index('MATRICULA')
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return pd.DataFrame()

db = cargar_base()

# --- 3. SISTEMA DE USUARIOS ---
usuarios = {
    "admin": {"pin": "2026", "rol": "Administrador", "nombre": "Admin General"},
    "prefectura": {"pin": "1234", "rol": "Prefectura", "nombre": "Prefecto de Turno"},
    "escolares": {"pin": "5678", "rol": "Servicios Escolares", "nombre": "Control Escolar"}
}

if 'user' not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.title("🛡️ SICA - CONALEP CUAUTLA")
    with st.container():
        u = st.text_input("Usuario")
        p = st.text_input("PIN de Acceso", type="password")
        if st.button("INGRESAR AL SISTEMA", use_container_width=True):
            if u in usuarios and usuarios[u]["pin"] == p:
                st.session_state.user = usuarios[u]
                st.rerun()
            else: st.error("Credenciales incorrectas")
    st.stop()

# --- 4. PANEL DE USUARIO ---
user = st.session_state.user
st.sidebar.markdown(f"### Bienvenido\n**{user['nombre']}**")
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.user = None
    st.rerun()

# --- 5. INTERFAZ DE ENTRADA ---
if user['rol'] in ["Prefectura", "Administrador"]:
    st.title("🚀 Control de Acceso Estudiantil")
    
    if 'scanned' not in st.session_state: st.session_state.scanned = ""

    def on_scan():
        raw = st.session_state.barcode
        st.session_state.scanned = raw.replace("'", "-").strip()
        st.session_state.barcode = ""

    st.text_input("👇 ESCANEE CREDENCIAL AQUÍ", key="barcode", on_change=on_scan)
    mat = st.session_state.scanned.replace("'", "-").strip()

    if mat:
        if mat in db.index:
            al = db.loc[mat]
            # OBTENEMOS LA HORA LOCAL DE MÉXICO
            hora_mexico = datetime.now(zona_horaria).strftime('%H:%M:%S')
            
            col_foto, col_info = st.columns([1, 2])
            with col_foto:
                foto_path = f"Fotos-Alumnos/{mat}.jpg"
                if os.path.exists(foto_path): st.image(foto_path, width=300)
                else: st.info("📷 Foto no disponible")
            
            with col_info:
                st.markdown(f"<p class='big-font'>{al['NOMBRE']} {al['PRIMER APELLIDO']}</p>", unsafe_allow_html=True)
                st.write(f"### Grupo: {al['GRUPO']}")
                
                aviso = al.get('AVISO_ENTRADA', "")
                if pd.notna(aviso) and aviso != "":
                    st.markdown(f"<div class='aviso-box'>📢 AVISO ESCOLAR: {aviso}</div>", unsafe_allow_html=True)

                st.markdown(f"""
                    <div class='status-box'>
                        ✅ ACCESO REGISTRADO<br>
                        <span style='font-size: 20px;'>Hora local: {hora_mexico}</span>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.error(f"❌ Matrícula {mat} no registrada.")

# --- 6. ADMINISTRACIÓN ---
if user['rol'] in ["Servicios Escolares", "Administrador"]:
    st.divider()
    st.header("🔍 Consulta de Expedientes")
    busc = st.text_input("Matrícula a buscar").replace("'", "-").strip()
    if busc in db.index:
        st.table(db.loc[[busc]])
