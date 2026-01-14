import streamlit as st
import pandas as pd
import requests
from datetime import datetime

# --- 1. CONFIGURACIÓN Y ESTILO ---
st.set_page_config(page_title="SICA Conalep Cuautla", layout="wide", page_icon="🛡️")

st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: white; }
    .big-font { font-size:35px !important; font-weight: bold; color: #2ecc71; }
    .status-box { padding: 20px; border-radius: 15px; text-align: center; font-size: 25px; background-color: #1e272e; border: 2px solid #2ecc71; }
    .aviso-box { padding: 15px; background-color: #f1c40f; color: black; border-radius: 10px; font-weight: bold; margin-bottom: 10px; }
    .reporte-box { padding: 15px; background-color: #e74c3c; color: white; border-radius: 10px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN A GOOGLE SHEETS ---
SHEET_ID = "1A9fA0TEjHiLFYpimAobC9xSZFHrCNZl3"
URL_CSV = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
# Reemplaza la siguiente línea con tu URL de Apps Script cuando la tengas
WEBHOOK_URL = "TU_URL_DE_APPS_SCRIPT_AQUI" 

@st.cache_data(ttl=30)
def cargar_alumnos():
    try:
        df = pd.read_csv(URL_CSV)
        # Limpieza básica de la base de datos al cargar
        df['MATRICULA'] = df['MATRICULA'].astype(str).str.strip()
        return df.set_index('MATRICULA')
    except Exception as e:
        st.error(f"Error cargando base de datos: {e}")
        return pd.DataFrame()

db = cargar_alumnos()

# --- 3. GESTIÓN DE USUARIOS ---
usuarios = {
    "admin": {"pin": "2026", "rol": "Administrador", "nombre": "Admin General"},
    "prefectura": {"pin": "1234", "rol": "Prefectura", "nombre": "Prefecto de Turno"},
    "escolares": {"pin": "5678", "rol": "Servicios Escolares", "nombre": "Control Escolar"},
    "tecnica": {"pin": "9999", "rol": "Formación Técnica", "nombre": "Jefe de Formación"}
}

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
            else:
                st.error("Acceso denegado. Verifique usuario y PIN.")
    st.stop()

# --- 4. PANEL SEGÚN ROL ---
user = st.session_state.user
st.sidebar.title(f"👤 {user['nombre']}")
st.sidebar.info(f"Rol: {user['rol']}")

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.user = None
    st.rerun()

# --- 5. MÓDULO DE CONTROL DE ACCESO (PREFECTURA) ---
if user['rol'] in ["Prefectura", "Administrador"]:
    st.header("🚀 Registro de Entrada")
    
    # Inicializar el estado si no existe
    if 'scanned' not in st.session_state:
        st.session_state.scanned = ""

    # Función que se ejecuta al escanear
    def on_scan():
        raw_data = st.session_state.barcode
        # CORRECCIÓN NIVEL 1: Antes de guardar en la sesión
        limpio = raw_data.replace("'", "-").strip()
        st.session_state.scanned = limpio
        st.session_state.barcode = ""

    st.text_input("👇 ESCANEE MATRÍCULA AQUÍ", key="barcode", on_change=on_scan)

    # CORRECCIÓN NIVEL 2: Al leer de la sesión para buscar en la DB
    mat = st.session_state.scanned.replace("'", "-").strip()

    if mat:
        if mat in db.index:
            alumno = db.loc[mat]
            col_foto, col_info = st.columns([1, 2])
            
            with col_foto:
                # Intenta mostrar foto, si no existe muestra icono por defecto
                foto_path = f"Fotos-Alumnos/{mat}.jpg"
                if os.path.exists(foto_path):
                    st.image(foto_path, width=280)
                else:
                    st.warning("📷 Foto no disponible")
            
            with col_info:
                st.markdown(f"<p class='big-font'>{alumno['NOMBRE']} {alumno['PRIMER APELLIDO']}</p>", unsafe_allow_html=True)
                st.write(f"### Grupo: {alumno['GRUPO']}")
                
                # --- AVISOS DE SERVICIOS ESCOLARES ---
                aviso = alumno.get('AVISO_ENTRADA', "")
                if pd.notna(aviso) and aviso != "":
                    st.markdown(f"<div class='aviso-box'>📢 AVISO: {aviso}</div>", unsafe_allow_html=True)
                
                # --- ESTADO ACADÉMICO ---
                estado = str(alumno.get('ESTADO_ACADEMICO', "")).upper()
                if "RIESGO" in estado or "REPORTE" in estado:
                    st.markdown(f"<div class='reporte-box'>⚠️ {estado}</div>", unsafe_allow_html=True)

                st.markdown(f"<div class='status-box'>✅ ACCESO REGISTRADO<br>{datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)
                
                # Botones de incidencias
                c1, c2 = st.columns(2)
                if c1.button("⏰ REGISTRAR RETARDO"):
                    st.toast("Retardo enviado a la nube...")
                if c2.button("🚫 REPORTE DISCIPLINA"):
                    st.toast("Reporte generado.")
        else:
            st.error(f"❌ La matrícula [{mat}] no existe en la base de datos.")

# --- 6. MÓDULO ADMINISTRATIVO (ESCOLARES / TÉCNICA) ---
if user['rol'] in ["Servicios Escolares", "Formación Técnica", "Administrador"]:
    st.divider()
    st.header("📋 Gestión y Consulta Administrativa")
    tab1, tab2 = st.tabs(["🔍 Buscador de Expedientes", "📢 Control de Avisos"])
    
    with tab1:
        id_busc = st.text_input("Ingrese Matrícula para ver historial académico")
        # CORRECCIÓN NIVEL 3: También en el buscador manual por si el admin se equivoca
        id_busc = id_busc.replace("'", "-").strip()
        
        if id_busc in db.index:
            al_data = db.loc[id_busc]
            st.write(f"### Datos de: {al_data['NOMBRE']}")
            st.table(al_data) 
        elif id_busc:
            st.error("No se encontró al alumno.")

    with tab2:
        st.subheader("Gestión de Avisos en Puerta")
        st.info("Para actualizar avisos masivamente, use el enlace de Google Sheets.")
        st.link_button("📂 Abrir Google Sheets", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}")
