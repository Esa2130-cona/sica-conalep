import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime
import pytz
import time

# ================= CONFIGURACIÓN INICIAL =================
st.set_page_config(page_title="SICA CONALEP CUAUTLA", layout="wide")
zona = pytz.timezone("America/Mexico_City")

# --- CONEXIÓN A SUPABASE ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error("Error en Secrets: Verifica SUPABASE_URL y SUPABASE_KEY")
        st.stop()

supabase = init_connection()

# --- FUNCIONES GLOBALES ---
def normalizar_matricula(mat):
    if not mat: return ""
    return mat.strip().upper().replace('"', '-').replace("'", '-')

def enviar(tabla, datos):
    # Forzamos nombres de columnas en minúsculas para coincidir con Supabase
    datos_db = {k.lower(): v for k, v in datos.items()}
    return supabase.table(tabla).insert(datos_db).execute()

# ================= ESTILOS CSS =================
st.markdown("""
<style>
    .stApp { background: #0d1117; }
    .kiosko-wrapper { display: flex; flex-direction: column; align-items: center; justify-content: center; margin-top: -20px; }
    .scan-card { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1); backdrop-filter: blur(10px); padding: 30px; border-radius: 24px; text-align: center; width: 100%; max-width: 500px; margin-bottom: 20px; }
    .scan-text { color: #00e676; font-size: 24px; font-weight: 800; text-transform: uppercase; }
    .res-card { width: 100%; max-width: 600px; border-radius: 30px; padding: 40px; text-align: center; animation: slideUp 0.4s ease-out; }
    .res-ok { background: linear-gradient(145deg, #1b5e20, #2e7d32); border: 2px solid #00e676; }
    .res-error { background: linear-gradient(145deg, #b71c1c, #d32f2f); border: 2px solid #ff5252; }
    .student-name { font-size: 50px; font-weight: 900; color: white; margin: 15px 0; text-transform: uppercase; }
    input { text-align: center !important; font-size: 24px !important; color: white !important; border-bottom: 2px solid #00e676 !important; }
    @keyframes slideUp { from { transform: translateY(30px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
</style>
""", unsafe_allow_html=True)

# ================= SISTEMA DE LOGIN =================
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.markdown("<h1 style='color:white; text-align:center;'>🔐 SICA CONALEP CUAUTLA</h1>", unsafe_allow_html=True)
    with st.container():
        u = st.text_input("Usuario").strip()
        p = st.text_input("PIN", type="password").strip()
        if st.button("Ingresar"):
            try:
                # Usamos filtros explícitos para evitar conflictos de nombres
                query = supabase.table("usuarios").select("*").filter("usuario", "eq", u).filter("pin", "eq", p).execute()
                if query.data:
                    st.session_state.user = query.data[0]
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas")
            except Exception as e:
                st.error(f"Error de base de datos: {e}")
                st.info("Verifica que las columnas se llamen 'usuario' y 'pin' en minúsculas y el RLS esté desactivado.")
    st.stop()

user = st.session_state.user
rol = str(user.get("rol", user.get("ROL", ""))).upper()

# ================= MENÚ PRINCIPAL =================
opciones = ["Puerta de Entrada", "Reportes", "Historial", "Bitácora Maestros"]
if rol == "KIOSKO": opciones = ["Puerta de Entrada"]
menu = st.sidebar.radio("📋 MENÚ", opciones)

if st.sidebar.button("Cerrar Sesión"):
    st.session_state.user = None
    st.rerun()

# ================= MÓDULO: PUERTA DE ENTRADA =================
if menu == "Puerta de Entrada":
    st.markdown("<div class='kiosko-wrapper'>", unsafe_allow_html=True)
    st.markdown("<div class='scan-card'><div class='scan-text'>📡 SISTEMA DE ACCESO</div></div>", unsafe_allow_html=True)

    if "resultado" not in st.session_state: st.session_state.resultado = None

    def procesar_scan():
        mat = normalizar_matricula(st.session_state.scan_input)
        st.session_state.scan_input = ""
        if not mat: return
        
        try:
            # Busqueda flexible (soporta min/MAY en las columnas de la DB)
            al_query = supabase.table("alumnos").select("*").filter("matricula", "eq", mat).execute()
            av_query = supabase.table("avisos").select("mensaje").filter("matricula", "eq", mat).filter("activo", "eq", True).execute()

            if not al_query.data:
                st.session_state.resultado = {"tipo": "error", "mensaje": "NO REGISTRADO"}
            else:
                al = al_query.data[0]
                nombre = al.get("nombre", al.get("NOMBRE", "Estudiante"))
                grupo = al.get("grupo", al.get("GRUPO", "N/A"))
                
                aviso = av_query.data[0]["mensaje"] if av_query.data else None
                
                enviar("entradas", {
                    "fecha": datetime.now(zona).strftime("%Y-%m-%d"),
                    "hora": datetime.now(zona).strftime("%H:%M:%S"),
                    "matricula": mat,
                    "nombre": nombre,
                    "grupo": grupo,
                    "registro_por": user.get("usuario", "Sistema")
                })
                st.session_state.resultado = {"tipo": "ok", "nombre": nombre, "grupo": grupo, "aviso": aviso}
        except Exception as e:
            st.session_state.resultado = {"tipo": "error", "mensaje": f"Error DB: {str(e)[:40]}"}

    st.text_input("", key="scan_input", on_change=procesar_scan, placeholder="ESCANEE AQUÍ", autocomplete="off")

    if st.session_state.resultado:
        res = st.session_state.resultado
        if res["tipo"] == "ok":
            st.markdown(f"""
                <div class='res-card res-ok'>
                    <div style='font-size:30px; color:#00e676;'>✅ ACCESO PERMITIDO</div>
                    <div class='student-name'>{res['nombre']}</div>
                    <div style='font-size:25px; color:white;'>GRUPO: {res['grupo']}</div>
                </div>
            """, unsafe_allow_html=True)
            if res["aviso"]: st.warning(f"⚠️ AVISO: {res['aviso']}")
        else:
            st.markdown(f"<div class='res-card res-error'><h1>❌ {res['mensaje']}</h1></div>", unsafe_allow_html=True)
        
        time.sleep(2.0)
        st.session_state.resultado = None
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ================= MÓDULO: REPORTES =================
elif menu == "Reportes":
    st.title("🚨 Gestión de Reportes")
    mat_rep = st.text_input("Matrícula para reporte").strip().upper()
    if mat_rep:
        try:
            al_res = supabase.table("alumnos").select("*").filter("matricula", "eq", mat_rep).execute()
            if al_res.data:
                al = al_res.data[0]
                st.subheader(f"Alumno: {al.get('nombre', al.get('NOMBRE'))}")
                tipo = st.selectbox("Incidencia", ["Uniforme", "Conducta", "Retardo", "Falta"])
                desc = st.text_area("Detalles")
                if st.button("Guardar Reporte"):
                    enviar("reportes", {
                        "fecha": datetime.now(zona).strftime("%Y-%m-%d"),
                        "matricula": mat_rep,
                        "nombre": al.get('nombre', al.get('NOMBRE')),
                        "tipo": tipo,
                        "descripcion": desc,
                        "registrado_por": user.get("usuario")
                    })
                    st.success("Reporte guardado")
            else:
                st.error("No se encontró el alumno")
        except: st.error("Error al buscar alumno")

# ================= MÓDULO: HISTORIAL =================
elif menu == "Historial":
    st.title("📊 Consulta de Historial")
    mat_h = st.text_input("Matrícula a consultar").strip().upper()
    if mat_h:
        try:
            ent = supabase.table("entradas").select("*").filter("matricula", "eq", mat_h).execute()
            if ent.data:
                st.table(pd.DataFrame(ent.data)[["fecha", "hora", "nombre"]])
            else: st.info("Sin registros")
        except: st.error("Error en consulta")























































































