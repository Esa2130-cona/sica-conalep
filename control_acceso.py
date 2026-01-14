import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import os
import pytz

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="SICA Conalep Cuautla", layout="wide")
zona_horaria = pytz.timezone('America/Mexico_City')

# Estilos
st.markdown("""
    <style>
    .stApp { background-color: #F8F9FA; color: #212529; }
    h1, h2, h3 { color: #006437 !important; }
    .big-font { font-size:38px !important; font-weight: bold; color: #006437; }
    .status-box { padding: 25px; border-radius: 20px; text-align: center; background-color: #FFFFFF; border: 3px solid #006437; color: #006437; box-shadow: 0px 4px 15px rgba(0,0,0,0.1); }
    .aviso-box { padding: 15px; background-color: #FFF3CD; color: #856404; border-radius: 12px; border-left: 8px solid #FFC107; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN A GOOGLE SHEETS ---
SHEET_ID = "11RZyoBo_MyQkGWfc21WCY_xPFZdKkwTG12YagiZf3yM"

@st.cache_data(ttl=5)
def cargar_datos(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    try:
        df = pd.read_csv(url)
        # LIMPIEZA DE COLUMNAS (Para evitar el KeyError)
        df.columns = [str(c).strip().upper() for c in df.columns]
        # Eliminar columnas sin nombre (Unnamed)
        df = df.loc[:, ~df.columns.str.contains('^UNNAMED')]
        
        if 'MATRICULA' in df.columns:
            df['MATRICULA'] = df['MATRICULA'].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Error en pestaña GID {gid}: {e}")
        return pd.DataFrame()

# Cargar pestañas usando tus GIDs
df_alumnos = cargar_datos(0) # Pestaña Alumnos
df_academico = cargar_datos(1114227031) # Pestaña Academico
df_incidencias = cargar_datos(569107936) # Pestaña Incidencias
df_usuarios = cargar_datos(1418859187) # Pestaña Usuarios

# --- LOGIN ---
if 'user_data' not in st.session_state:
    st.session_state.user_data = None

if st.session_state.user_data is None:
    st.title("🛡️ SICA - Login")
    u_log = st.text_input("Usuario")
    p_log = st.text_input("PIN", type="password")
    if st.button("INGRESAR"):
        if not df_usuarios.empty:
            # Buscamos ignorando mayúsculas en el usuario
            match = df_usuarios[(df_usuarios['USUARIO'].str.lower() == u_log.lower()) & (df_usuarios['PIN'].astype(str) == p_log)]
            if not match.empty:
                st.session_state.user_data = match.iloc[0].to_dict()
                st.rerun()
            else: st.error("Usuario o PIN incorrectos")
        else: st.error("No se pudo cargar la base de usuarios")
    st.stop()

# --- INTERFAZ ---
user = st.session_state.user_data
st.sidebar.title(f"👤 {user['NOMBRE']}")
menu = st.sidebar.radio("Menú", ["Puerta de Entrada", "Historial Alumnos", "Gestión"])

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.user_data = None
    st.rerun()

# --- MODULO 1: ENTRADA ---
if menu == "Puerta de Entrada":
    st.title("🚀 Registro de Acceso")
    
    if 'scanned_id' not in st.session_state: st.session_state.scanned_id = ""

    def on_scan():
        raw = st.session_state.lector
        st.session_state.scanned_id = raw.replace("'", "-").strip()
        st.session_state.lector = ""

    st.text_input("👇 ESCANEE AQUÍ", key="lector", on_change=on_scan)
    mat = st.session_state.scanned_id

    if mat:
        # Buscamos al alumno
        alumno_row = df_alumnos[df_alumnos['MATRICULA'] == mat]
        if not alumno_row.empty:
            al = alumno_row.iloc[0]
            c1, c2 = st.columns([1, 2])
            with c1:
                # Mostrar foto
                foto = f"Fotos-Alumnos/{mat}.jpg"
                if os.path.exists(foto): st.image(foto, width=300)
                else: st.info("📷 Foto pendiente")
            with c2:
                st.markdown(f"<p class='big-font'>{al['NOMBRE']} {al['PRIMER APELLIDO']}</p>", unsafe_allow_html=True)
                st.write(f"### Grupo: {al.get('GRUPO', 'S/G')}")
                
                # Aviso
                aviso = al.get('AVISO_ENTRADA', "")
                if pd.notna(aviso) and aviso != "":
                    st.markdown(f"<div class='aviso-box'>📢 AVISO: {aviso}</div>", unsafe_allow_html=True)
                
                hora = datetime.now(zona_horaria).strftime('%H:%M:%S')
                st.markdown(f"<div class='status-box'>✅ ACCESO REGISTRADO<br>{hora}</div>", unsafe_allow_html=True)
        else:
            st.error(f"Matrícula {mat} no encontrada.")

# --- MODULO 2: HISTORIAL ---
elif menu == "Historial Alumnos":
    st.title("🔍 Buscador de Expedientes")
    buscar = st.text_input("Matrícula").replace("'", "-").strip()
    if buscar:
        al_info = df_alumnos[df_alumnos['MATRICULA'] == buscar]
        if not al_info.empty:
            st.header(f"Alumno: {al_info.iloc[0]['NOMBRE']}")
            
            # Datos Académicos
            ac_info = df_academico[df_academico['MATRICULA'] == buscar]
            if not ac_info.empty:
                st.write("### 📊 Datos Académicos")
                st.dataframe(ac_info)
            
            # Incidencias
            inc_info = df_incidencias[df_incidencias['MATRICULA'] == buscar]
            st.write("### 📜 Historial de Conducta")
            if not inc_info.empty:
                st.table(inc_info)
            else: st.success("Sin reportes.")
        else: st.error("No encontrado.")

elif menu == "Gestión":
    st.link_button("Abrir Google Sheets", f"https://docs.google.com/spreadsheets/d/{SHEET_ID}")
