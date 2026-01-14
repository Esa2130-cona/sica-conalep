import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- CONFIGURACIÓN ---
# ID del nuevo archivo que me pasaste
SHEET_ID = "1A9fA0TEjHiLFYpimAobC9xSZFHrCNZl3"
URL_CSV = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
WEBHOOK_URL = "https://script.google.com/macros/s/AKfycbz_JkainmoGoEv3PpMUtPMlq2yLHpVQqo4ND_NyBVODN5wd6EBe9yn81RnwfY6TNVu1uA/exec" # Pon aquí la URL de Apps Script

st.set_page_config(page_title="SICA Conalep Cuautla", layout="wide")

# --- CARGA DE DATOS ---
@st.cache_data(ttl=30)
def cargar_alumnos():
    try:
        df = pd.read_csv(URL_CSV)
        df['MATRICULA'] = df['MATRICULA'].astype(str).str.strip()
        return df.set_index('MATRICULA')
    except:
        return pd.DataFrame()

db = cargar_alumnos()

# --- GESTIÓN DE USUARIOS (SIMULADA POR AHORA) ---
# Puedes mover esto a otra pestaña del Google Sheet después
usuarios = {
    "admin": {"pin": "2026", "rol": "Administrador", "nombre": "Admin General"},
    "prefectura": {"pin": "1234", "rol": "Prefectura", "nombre": "Prefecto de Turno"},
    "escolares": {"pin": "5678", "rol": "Servicios Escolares", "nombre": "Control Escolar"},
    "tecnica": {"pin": "9999", "rol": "Formación Técnica", "nombre": "Jefe de Formación"}
}

# --- LOGIN ---
if 'user' not in st.session_state:
    st.session_state.user = None

if st.session_state.user is None:
    st.title("🛡️ SICA - CONALEP CUAUTLA")
    with st.container(border=True):
        u = st.text_input("ID de Usuario")
        p = st.text_input("PIN", type="password")
        if st.button("INGRESAR", use_container_width=True):
            if u in usuarios and usuarios[u]["pin"] == p:
                st.session_state.user = usuarios[u]
                st.rerun()
            else: st.error("Acceso denegado")
    st.stop()

# --- INTERFAZ SEGÚN ROL ---
user = st.session_state.user
st.sidebar.title(f"👤 {user['nombre']}")
st.sidebar.info(f"Rol: {user['rol']}")

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.user = None
    st.rerun()

# --- MÓDULOS ---

# 1. CONTROL DE ACCESO (Para todos, especialmente Prefectura)
if user['rol'] in ["Prefectura", "Administrador"]:
    with st.expander("🚪 PANEL DE ENTRADA", expanded=True):
        if 'scanned' not in st.session_state: st.session_state.scanned = ""
        
        def on_scan():
            # Esta función limpia el input
            st.session_state.scanned = st.session_state.barcode
            st.session_state.barcode = ""

        st.text_input("👇 ESCANEAR AQUÍ", key="barcode", on_change=on_scan)
        
        # --- LA CORRECCIÓN DEFINITIVA AQUÍ ---
        # Forzamos que 'mat' siempre cambie la comilla por el guion antes de buscar
        mat = st.session_state.scanned.replace("'", "-").strip()
        
        if mat:
            # Ahora 'mat' ya no tiene comillas, por lo que entrará aquí:
            if mat in db.index:
                al = db.loc[mat]
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.image(f"Fotos-Alumnos/{mat}.jpg", width=250)
                with c2:
                    st.header(f"{al['NOMBRE']} {al['PRIMER APELLIDO']}")
                    st.write(f"**Grupo:** {al['GRUPO']}")
                    
                    # Avisos de Escolares
                    aviso = al.get('AVISO_ENTRADA', "")
                    if pd.notna(aviso) and aviso != "":
                        st.warning(f"📢 AVISO: {aviso}")
                    
                    # Botones de reporte
                    col_a, col_b = st.columns(2)
                    if col_a.button("⏰ RETARDO"):
                        # Aquí llamarías a la función para guardar en el sheet
                        st.toast("Retardo registrado")
            else:
                st.error("No registrado")

# 2. PANEL ADMINISTRATIVO (Servicios Escolares / Técnica / Admin)
if user['rol'] in ["Servicios Escolares", "Formación Técnica", "Administrador"]:
    st.divider()
    st.header("📋 Gestión Administrativa")
    tab1, tab2 = st.tabs(["🔍 Buscador Académico", "📢 Publicar Avisos"])
    
    with tab1:
        st.subheader("Información Integral del Alumno")
        busc = st.text_input("Buscar por matrícula para ver historial académico")
        if busc in db.index:
            alumno_data = db.loc[busc]
            st.write(alumno_data) # Muestra todo: Promedios, materias, etc.
            
    with tab2:
        st.subheader("Crear Aviso en Pantalla")
        target = st.text_input("Matrícula del alumno a notificar")
        msg = st.text_area("Mensaje del aviso")
        if st.button("Publicar Aviso"):

            st.success("El aviso aparecerá la próxima vez que el alumno escanee su credencial.")
