import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import os
import pytz

# --- 1. CONFIGURACIÓN ---
st.set_page_config(page_title="SICA Conalep Cuautla", layout="wide")
zona_horaria = pytz.timezone('America/Mexico_City')

st.markdown("""
    <style>
    .stApp { background-color: #F8F9FA; color: #212529; }
    h1, h2, h3 { color: #006437 !important; }
    .big-font { font-size:35px !important; font-weight: bold; color: #006437; }
    .status-box { padding: 25px; border-radius: 20px; text-align: center; background-color: #FFFFFF; border: 3px solid #006437; color: #006437; box-shadow: 0px 4px 15px rgba(0,0,0,0.1); }
    .aviso-box { padding: 15px; background-color: #FFF3CD; color: #856404; border-radius: 12px; border-left: 8px solid #FFC107; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FUNCIÓN DE LIMPIEZA PROFUNDA ---
SHEET_ID = "11RZyoBo_MyQkGWfc21WCY_xPFZdKkwTG12YagiZf3yM"

@st.cache_data(ttl=5)
def cargar_base_blindada(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    try:
        # Leer el CSV crudo
        df = pd.read_csv(url)
        
        # ELIMINAR columnas que sean todas NaN o vacías
        df = df.dropna(axis=1, how='all')
        
        # LIMPIAR NOMBRES DE COLUMNAS: Quitar espacios, comillas y pasar a MAYÚSCULAS
        df.columns = [str(c).strip().replace('"', '').replace("'", "").upper() for c in df.columns]
        
        # ELIMINAR columnas "UNNAMED"
        df = df.loc[:, ~df.columns.str.contains('^UNNAMED')]
        
        # Si existe la columna MATRICULA, limpiamos sus datos
        if 'MATRICULA' in df.columns:
            df['MATRICULA'] = df['MATRICULA'].astype(str).str.strip().replace("'", "-")
            
        return df
    except Exception as e:
        st.error(f"Error en pestaña {gid}: {e}")
        return pd.DataFrame()

# Cargar las pestañas con sus GIDs correspondientes
df_alumnos = cargar_base_blindada(0)
df_academico = cargar_base_blindada(1114227031)
df_incidencias = cargar_base_blindada(569107936)
df_usuarios = cargar_base_blindada(1418859187)

# --- 3. LOGIN ---
if 'user_data' not in st.session_state:
    st.session_state.user_data = None

if st.session_state.user_data is None:
    st.title("🛡️ SICA - CONALEP CUAUTLA")
    u = st.text_input("Usuario")
    p = st.text_input("PIN", type="password")
    if st.button("INGRESAR"):
        if not df_usuarios.empty:
            # Buscamos ignorando mayúsculas
            match = df_usuarios[(df_usuarios['USUARIO'].astype(str).str.lower() == u.lower()) & 
                                (df_usuarios['PIN'].astype(str) == p)]
            if not match.empty:
                st.session_state.user_data = match.iloc[0].to_dict()
                st.rerun()
            else: st.error("Usuario o PIN incorrectos")
        else: st.error("No se pudo conectar con la base de Usuarios.")
    st.stop()

# --- 4. PANEL PRINCIPAL ---
user = st.session_state.user_data
st.sidebar.title(f"👤 {user.get('NOMBRE', 'Usuario')}")
menu = st.sidebar.radio("MENÚ", ["Puerta de Entrada", "Historial Alumnos"])

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.user_data = None
    st.rerun()

# --- MODULO: ENTRADA ---
if menu == "Puerta de Entrada":
    st.title("🚀 Registro de Acceso")
    
    if 'id_leido' not in st.session_state: st.session_state.id_leido = ""

    def al_escanear():
        raw = st.session_state.input_lector
        # CORREGIR COMILLA POR GUION EN TIEMPO REAL
        st.session_state.id_leido = raw.replace("'", "-").strip()
        st.session_state.input_lector = ""

    st.text_input("👇 ESCANEE AQUÍ", key="input_lector", on_change=al_escanear)
    
    mat = st.session_state.id_leido
    
    if mat:
        # Búsqueda filtrada
        res = df_alumnos[df_alumnos['MATRICULA'] == mat]
        
        if not res.empty:
            al = res.iloc[0]
            c1, c2 = st.columns([1, 2])
            with c1:
                foto = f"Fotos-Alumnos/{mat}.jpg"
                if os.path.exists(foto): st.image(foto, width=300)
                else: st.info("📷 Foto no disponible")
            with c2:
                st.markdown(f"<p class='big-font'>{al.get('NOMBRE','')} {al.get('PRIMER APELLIDO','')}</p>", unsafe_allow_html=True)
                st.write(f"### Grupo: {al.get('GRUPO', 'S/G')}")
                
                # Aviso de entrada (Columna avisos)
                aviso = al.get('AVISO_ENTRADA', "")
                if pd.notna(aviso) and str(aviso).strip() != "":
                    st.markdown(f"<div class='aviso-box'>📢 AVISO: {aviso}</div>", unsafe_allow_html=True)
                
                h = datetime.now(zona_horaria).strftime('%H:%M:%S')
                st.markdown(f"<div class='status-box'>✅ ACCESO REGISTRADO<br>{h}</div>", unsafe_allow_html=True)
        else:
            st.error(f"❌ La matrícula {mat} no existe en la base. Verifique que esté en la pestaña ALUMNOS.")

# --- MODULO: HISTORIAL ---
elif menu == "Historial Alumnos":
    st.title("🔍 Consulta de Expedientes")
    m_busc = st.text_input("Ingrese Matrícula").replace("'", "-").strip()
    if m_busc:
        busc_res = df_alumnos[df_alumnos['MATRICULA'] == m_busc]
        if not busc_res.empty:
            al_h = busc_res.iloc[0]
            st.header(f"Alumno: {al_h.get('NOMBRE','')} {al_h.get('PRIMER APELLIDO','')}")
            
            t1, t2 = st.tabs(["📊 Académico", "📜 Incidencias"])
            with t1:
                ac_h = df_academico[df_academico['MATRICULA'] == m_busc]
                st.dataframe(ac_h, hide_index=True)
            with t2:
                in_h = df_incidencias[df_incidencias['MATRICULA'] == m_busc]
                st.table(in_h)
        else: st.error("Matrícula no encontrada.")

