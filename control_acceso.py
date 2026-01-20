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
    /* Fondo General (Azul muy oscuro/negro institucional) */
    .stApp { background: #050a10; }
    
    /* Etiquetas de los campos (Usuario, PIN, etc.) */
    .stWidgetLabel p {
        color: #e0e0e0 !important;
        font-weight: 500;
        letter-spacing: 0.5px;
        font-size: 16px !important;
    }

    /* Cajas de Texto (Inputs y Textareas) */
    input, textarea, [data-baseweb="select"] > div {
        color: #ffffff !important; /* Texto Blanco Puro */
        -webkit-text-fill-color: #ffffff !important;
        background-color: rgba(255, 255, 255, 0.07) !important; /* Fondo sutil */
        border: 1px solid rgba(30, 132, 73, 0.3) !important; /* Borde verde institucional sutil */
        border-radius: 12px !important;
        padding: 10px !important;
    }

    /* Efecto al hacer clic en una caja (Focus) */
    input:focus, textarea:focus {
        border: 1px solid #1E8449 !important; /* Verde Conalep brillante al seleccionar */
        box-shadow: 0 0 10px rgba(30, 132, 73, 0.2) !important;
        outline: none !important;
    }

    /* Estilo para los botones (Moderno Institucional) */
    .stButton>button {
        background-color: #1E8449 !important;
        color: white !important;
        border-radius: 10px !important;
        border: none !important;
        font-weight: 600 !important;
        width: 100%;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #145A32 !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.4) !important;
    }

    /* Ajustes para el Kiosko */
    .scan-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-top: 4px solid #1E8449; /* Detalle institucional arriba */
        padding: 30px;
        border-radius: 20px;
    }
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

# ================= MÓDULO: REPORTES (LÓGICA 3 LLAMADAS + 1 REPORTE) =================
elif menu == "Reportes":
    st.title("🚨 Gestión de Incidencias")
    
    # Input de matrícula
    mat_rep = st.text_input("Ingrese Matrícula del Alumno").strip().upper()
    
    if mat_rep:
        try:
            # 1. Buscamos al alumno (usando minúsculas como corregiste)
            al_res = supabase.table("alumnos").select("*").eq("matricula", mat_rep).execute()
            
            if al_res.data:
                al = al_res.data[0]
                # Soporta si el nombre está en min o MAY en la base de datos
                nombre_alumno = al.get("nombre", al.get("NOMBRE", "Estudiante"))
                st.subheader(f"Alumno: {nombre_alumno}")
                
                # 2. CONTAR REPORTES PREVIOS
                # El sistema cuenta cuántas filas existen con esa matrícula en la tabla 'reportes'
                historial_rep = supabase.table("reportes").select("id", count="exact").eq("matricula", mat_rep).execute()
                total_previo = historial_rep.count if historial_rep.count is not None else 0
                
                # 3. DETERMINAR NIVEL SEGÚN TU REGLA (3 llamadas, luego reporte)
                if total_previo == 0:
                    nivel_sugerido = "LLAMADA 1"
                    st.info(f"📌 Primera incidencia: {nivel_sugerido}")
                elif total_previo == 1:
                    nivel_sugerido = "LLAMADA 2"
                    st.info(f"📌 Segunda incidencia: {nivel_sugerido}")
                elif total_previo == 2:
                    nivel_sugerido = "LLAMADA 3"
                    st.warning(f"⚠️ ÚLTIMA LLAMADA: {nivel_sugerido}")
                else:
                    nivel_sugerido = "REPORTE"
                    st.error(f"🚫 NIVEL CRÍTICO: {nivel_sugerido}")

                # 4. FORMULARIO
                tipo = st.selectbox("Tipo de falta", ["Uniforme", "Conducta", "Retardo", "Celular", "Otro"])
                desc = st.text_area("Descripción de lo sucedido")
                
                # Botón para guardar
                if st.button("Guardar Registro"):
                    enviar("reportes", {
                        "fecha": datetime.now(zona).strftime("%Y-%m-%d"),
                        "matricula": mat_rep,
                        "nombre": nombre_alumno,
                        "nivel": nivel_sugerido,
                        "tipo": tipo,
                        "descripcion": desc,
                        "registrado_por": user.get("usuario", "Prefecto")
                    })
                    st.success(f"✅ Se registró la {nivel_sugerido} correctamente.")
                    time.sleep(2)
                    st.rerun()
            else:
                st.error("Matrícula no encontrada.")
        except Exception as e:
            st.error(f"Error en la consulta: {e}")
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


























































































