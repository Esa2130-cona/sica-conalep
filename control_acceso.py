# ================= IMPORTS =================
import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
import threading
import time 
# ================= CONFIG =================
st.set_page_config(page_title="SICA CONALEP CUAUTLA", layout="wide")
zona = pytz.timezone("America/Mexico_City")
# ================= FUNCIONES GLOBALES =================

def normalizar_matricula(mat):
    if not mat:
        return ""
    return (
        mat.strip()
        .replace('"', '-')
        .replace("'", '-')
        .replace("/", '-')
        .replace("\\", '-')
        .upper()
    )

def cargar(gid):
    ...

def enviar(payload):
    ...


# ---------------- ESTADOS GLOBALES ----------------
if "user" not in st.session_state:
    st.session_state.user = None

if "msg_reporte_ok" not in st.session_state:
    st.session_state.msg_reporte_ok = False

if "limpiar_reporte" not in st.session_state:
    st.session_state.limpiar_reporte = False




# ================= ESTILOS (NO TOCADO) =================
st.markdown("""<style>
.card-acceso {background:white;padding:40px;border-radius:20px;border-left:15px solid #1E8449;}
.card-error {background:#FDEDEC;padding:40px;border-radius:20px;border:5px solid #CB4335;text-align:center;}
.acceso-permitido {color:#1E8449;font-size:65px;font-weight:900;}
.acceso-denegado {color:#CB4335;font-size:75px;font-weight:900;}
.nombre-alumno {color:#1B4F72;font-size:75px;font-weight:bold;text-transform:uppercase;}
.msg-error {color:#943126;font-size:50px;font-weight:bold;}
.datos-escolares {color:#566573;font-size:35px;}
</style>""", unsafe_allow_html=True)


# ================= CONFIG =================
SHEET_ID = "11RZyoBo_MyQkGWfc21WCY_xPFZdKkwTG12YagiZf3yM"
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwHiXcSKzIjrUAt3acJmdvUFAHGBU0mHljLsbSYeetytYJUOdZoFHd-mQJD2k5VO85m1A/exec"

GIDS = {
    "ALUMNOS": 1882885827,
    "USUARIOS": 921806663,
    "ENTRADAS": 25814912,
    "REPORTES": 1066783902,
    "ACADEMICO": 1794524153
}

@st.cache_data(ttl=5)
def cargar(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    return pd.read_csv(url)

def enviar(payload):
    try: requests.post(APPS_SCRIPT_URL, json=payload, timeout=10)

    except: pass

# ================= LOGIN =================
if "user" not in st.session_state:
    st.session_state.user = None

df_usuarios = cargar(GIDS["USUARIOS"])

if not st.session_state.user:
    st.title("🔐 SICA - CONALEP CUAUTLA")
    u = st.text_input("Usuario")
    p = st.text_input("PIN", type="password")
    if st.button("Ingresar"):
        r = df_usuarios[(df_usuarios["USUARIO"].astype(str)==u)&(df_usuarios["PIN"].astype(str)==p)]
        if not r.empty:
            st.session_state.user = r.iloc[0].to_dict()
            st.rerun()
        else:
            st.error("Credenciales incorrectas")
    st.stop()

user = st.session_state.user
rol = user.get("ROL","").upper()
# ================= DATA GLOBAL =================
df_reportes = cargar(GIDS["REPORTES"])
df_reportes.columns = [c.strip().upper() for c in df_reportes.columns]
if "NIVEL" not in df_reportes.columns:
    df_reportes["NIVEL"] = ""

df_reportes["NIVEL"] = df_reportes["NIVEL"].astype(str)


# ===== Inicialización segura de estados globales =====

if "resultado" not in st.session_state:
    st.session_state.resultado = None

if "scan_input" not in st.session_state:
    st.session_state.scan_input = ""

if "rep_mat" not in st.session_state:
    st.session_state.rep_mat = ""

if "rep_tipo" not in st.session_state:
    st.session_state.rep_tipo = "Retardo"

if "rep_desc" not in st.session_state:
    st.session_state.rep_desc = ""

# ===== BANDERAS DE CONTROL =====
if "limpiar_reporte" not in st.session_state:
    st.session_state.limpiar_reporte = False

# ================= MENU =================
if rol == "KIOSKO":
    opciones = [
        "Puerta de Entrada"
    ]

elif rol == "PREFECTO":
    opciones = [
        "Reportes",
        "Historial Alumnos"
    ]

elif rol == "USUARIO_GENERAL":
    opciones = [
        "Dashboard Director",
        "Historial Alumnos",
        "Reportes"
    ]

elif rol == "DIRECTOR":
    opciones = [
        "Dashboard Director",
        "Historial Alumnos"
    ]

elif rol == "ADMIN":
    opciones = [
        "Puerta de Entrada",
        "Dashboard",
        "Dashboard Director",
        "Reportes",
        "Historial Alumnos",
        "Usuarios"
    ]

else:
    st.error("Rol no autorizado")
    st.stop()

menu = st.sidebar.radio("📋 MENÚ PRINCIPAL", opciones)


# ================= PUERTA DE ENTRADA (REDiseño MODERNO) =================
if menu == "Puerta de Entrada":
    df = cargar(GIDS["ALUMNOS"])
    df.columns = [c.strip().upper() for c in df.columns]

    # ==== ESTILO ULTRA MODERNO PARA KIOSKO ====
    st.markdown("""
    <style>
    /* Fondo General Profundo */
    .stApp {
        background: #0d1117;
    }
    
    .kiosko-wrapper {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        font-family: 'Inter', 'Segoe UI', sans-serif;
        margin-top: -20px;
    }

    /* Caja de Escaneo - Minimalista y Futurista */
    .scan-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px);
        padding: 30px;
        border-radius: 24px;
        text-align: center;
        width: 100%;
        max-width: 500px;
        margin-bottom: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    }

    .scan-text {
        color: #00e676;
        font-size: 24px;
        font-weight: 800;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 10px;
    }

    .sub-text {
        color: #8b949e;
        font-size: 14px;
    }

    /* Tarjetas de Resultado - Grandes para monitores chicos */
    .res-card {
        width: 100%;
        max-width: 600px;
        border-radius: 30px;
        padding: 40px;
        text-align: center;
        animation: slideUp 0.4s ease-out;
        box-shadow: 0 20px 50px rgba(0,0,0,0.6);
    }

    .res-ok {
        background: linear-gradient(145deg, #1b5e20, #2e7d32);
        border: 2px solid #00e676;
    }

    .res-error {
        background: linear-gradient(145deg, #b71c1c, #d32f2f);
        border: 2px solid #ff5252;
    }

    .status-title {
        font-size: 45px;
        font-weight: 900;
        margin: 0;
        color: white;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }

    .student-name {
        font-size: 55px;
        font-weight: 900;
        color: #ffffff;
        margin: 20px 0;
        line-height: 1.1;
        text-transform: uppercase;
    }

    .student-group {
        font-size: 35px;
        background: rgba(0,0,0,0.2);
        display: inline-block;
        padding: 5px 25px;
        border-radius: 50px;
        color: rgba(255,255,255,0.9);
    }

    @keyframes slideUp {
        from { transform: translateY(30px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }

    /* Ocultar input feo de Streamlit */
    div[data-baseweb="input"] {
        background: transparent !important;
        border: none !important;
    }
    input {
        text-align: center !important;
        font-size: 20px !important;
        color: white !important;
        border-bottom: 2px solid #00e676 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Layout Principal
    st.markdown("<div class='kiosko-wrapper'>", unsafe_allow_html=True)
    
    # Encabezado Kiosko
    st.markdown("""
        <div class='scan-card'>
            <div class='scan-text'>📡 SISTEMA DE ACCESO</div>
            <div class='sub-text'>LISTO PARA ESCANEAR CREDENCIAL</div>
        </div>
    """, unsafe_allow_html=True)

    # El input se mantiene funcional (sin cambios en lógica)
    def procesar_scan():
        mat = normalizar_matricula(st.session_state.scan_input)
        st.session_state.scan_input = ""
        if not mat: return
        
        a = df[df["MATRICULA"].astype(str).str.strip() == mat]
        if a.empty:
            st.session_state.resultado = {"tipo": "error", "mensaje": "NO REGISTRADO"}
        else:
            al = a.iloc[0]
            enviar({
                "TIPO_REGISTRO": "ENTRADA",
                "FECHA": datetime.now(zona).strftime("%Y-%m-%d"),
                "HORA": datetime.now(zona).strftime("%H:%M:%S"),
                "MATRICULA": al["MATRICULA"],
                "NOMBRE": al["NOMBRE"],
                "GRUPO": al["GRUPO"],
                "REGISTRO_POR": user["USUARIO"]
            })
            st.session_state.resultado = {"tipo": "ok", "alumno": al}

    st.text_input("", key="scan_input", on_change=procesar_scan, placeholder="Esperando lectura...")

    # Renderizado de Resultados Modernos
    if st.session_state.resultado:
        r = st.session_state.resultado
        
        if r["tipo"] == "ok":
            st.markdown(f"""
                <div class='res-card res-ok'>
                    <div class='status-title'>✅ ACCESO PERMITIDO</div>
                    <div class='student-name'>{r['alumno']['NOMBRE']}</div>
                    <div class='student-group'>{r['alumno']['GRUPO']}</div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class='res-card res-error'>
                    <div class='status-title'>❌ ERROR</div>
                    <div class='student-name'>{r['mensaje']}</div>
                    <div class='student-group'>INTENTA DE NUEVO</div>
                </div>
            """, unsafe_allow_html=True)

        time.sleep(2.5)
        st.session_state.resultado = None
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ================= REPORTES =================
elif menu == "Reportes":

    # ✅ Mostrar mensaje después de guardar
    if st.session_state.msg_reporte_ok:
        st.success("✅ Registro guardado correctamente")
        st.session_state.msg_reporte_ok = False

    # 🔄 Limpiar campos si se guardó un reporte
    if st.session_state.limpiar_reporte:
        st.session_state.rep_mat = ""
        st.session_state.rep_tipo = "Conducta"
        st.session_state.rep_desc = ""
        st.session_state.limpiar_reporte = False

    df = cargar(GIDS["ALUMNOS"])
    df_r = df_reportes

    # ---- estados ----
    if "rep_mat" not in st.session_state:
        st.session_state.rep_mat = ""
    if "rep_tipo" not in st.session_state:
        st.session_state.rep_tipo = "Conducta"
    if "rep_desc" not in st.session_state:
        st.session_state.rep_desc = ""

    mat = st.text_input("Matrícula", key="rep_mat").strip()

    if mat:
        a = df[df["MATRICULA"].astype(str) == mat]

        if not a.empty:

            llamadas = df_r[
                (df_r["MATRICULA"].astype(str) == mat) &
                (df_r["NIVEL"].astype(str).str.contains("LLAMADA", na=False))
            ]

            num_llamadas = len(llamadas)

            if num_llamadas == 0:
                nivel = "LLAMADA 1"
            elif num_llamadas == 1:
                nivel = "LLAMADA 2"
            elif num_llamadas == 2:
                nivel = "LLAMADA 3"
            else:
                nivel = "REPORTE"

            st.info(f"📌 Nivel actual: {nivel}")

            tipo = st.selectbox(
                "Tipo de incidencia",
                ["Conducta", "Uniforme", "Retardo", "Falta"],
                key="rep_tipo"
            )

            obs = st.text_area("Descripción", key="rep_desc")

            if st.button("Guardar"):
                enviar({
                    "TIPO_REGISTRO": "REPORTE",
                    "FECHA": datetime.now(zona).strftime("%Y-%m-%d"),
                    "HORA": datetime.now(zona).strftime("%H:%M:%S"),
                    "MATRICULA": mat,
                    "NOMBRE": a.iloc[0]["NOMBRE"],
                    "GRUPO": a.iloc[0]["GRUPO"],
                    "NIVEL": nivel,
                    "TIPO": tipo,
                    "DESCRIPCION": obs,
                    "REGISTRADO_POR": user["USUARIO"]
                })

                # 👉 activar mensaje
                st.session_state.msg_reporte_ok = True

                # 👉 limpiar formulario
                st.session_state.limpiar_reporte = True

                st.rerun()


# ================= USUARIOS =================
elif menu == "Usuarios":
    st.title("👤 Administración de Usuarios")
    df = cargar(GIDS["USUARIOS"])
    st.dataframe(df)

    with st.form("nuevo"):
        u = st.text_input("Usuario")
        p = st.text_input("PIN")
        r = st.selectbox("Rol",["ADMIN","PREFECTO","DIRECTOR"])
        if st.form_submit_button("Crear"):
            enviar ({"TIPO_REGISTRO":"USUARIO","USUARIO":u,"PIN":p,"ROL":r})

            st.success("Usuario creado")

# ================= DASHBOARD =================
elif menu == "Dashboard":
    st.title("📊 Dashboard Analítico")
    df_e = cargar(GIDS["ENTRADAS"])
    df_i = cargar(GIDS["REPORTES"])

    st.metric("Total Entradas", len(df_e))
    st.metric("Total Reportes", len(df_i))
    st.bar_chart(df_i["TIPO"].value_counts())

# ================= HISTORIAL =================
elif menu == "Historial Alumnos":
    st.title("📊 Historial del Alumno")

    df_e = cargar(GIDS["ENTRADAS"])
    df_r = cargar(GIDS["REPORTES"])  # 👈 AQUÍ ESTÁ LA CLAVE

    df_e.columns = [c.strip().upper() for c in df_e.columns]
    df_r.columns = [c.strip().upper() for c in df_r.columns]

    if "hist_mat" not in st.session_state:
        st.session_state.hist_mat = ""
    if "hist_buscar" not in st.session_state:
        st.session_state.hist_buscar = ""

    def buscar():
        st.session_state.hist_buscar = st.session_state.hist_mat
        st.session_state.hist_mat = ""

    st.text_input(
        "Escanee o ingrese la matrícula",
        key="hist_mat",
        on_change=buscar
    )

    mat = st.session_state.hist_buscar.strip()

    if mat:
        entradas = df_e[df_e["MATRICULA"].astype(str) == mat]
        reportes = df_r[df_r["MATRICULA"].astype(str) == mat]

        st.subheader("📥 Entradas")
        if entradas.empty:
            st.info("Sin registros de entrada")
        else:
            st.dataframe(
                entradas.sort_values("FECHA_REGISTRO", ascending=False),
                use_container_width=True
            )

        st.subheader("🚨 Reportes")
        if reportes.empty:
            st.success("El alumno no tiene reportes")
        else:
            st.dataframe(
                reportes.sort_values("FECHA", ascending=False),
                use_container_width=True
            )

# ================= MENU DIRECTOR =================
elif menu == "Dashboard Director":
    st.title("📱 Dashboard Dirección")

    df_e = cargar(GIDS["ENTRADAS"])
    df_r = cargar(GIDS["REPORTES"])

    # Normalizar
    df_e.columns = [c.strip().upper() for c in df_e.columns]
    df_r.columns = [c.strip().upper() for c in df_r.columns]

    df_e["FECHA"] = pd.to_datetime(df_e["FECHA"], errors="coerce")
    df_r["FECHA"] = pd.to_datetime(df_r["FECHA"], errors="coerce")

    hoy = datetime.now(zona).date()

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "👨‍🎓 Entradas Hoy",
        len(df_e[df_e["FECHA"].dt.date == hoy])
    )

    col2.metric(
        "⚠ Reportes Hoy",
        len(df_r[df_r["FECHA"].dt.date == hoy])
    )

    col3.metric(
        "📊 Total Entradas",
        len(df_e)
    )

    st.divider()

    # 📈 Entradas por periodo
    st.subheader("📈 Entradas por periodo")

    periodo = st.selectbox("Periodo", ["Día", "Semana", "Mes"])

    if periodo == "Día":
        rep = df_e.groupby(df_e["FECHA"].dt.date).size()
    elif periodo == "Semana":
        rep = df_e.groupby(df_e["FECHA"].dt.to_period("W")).size()
    else:
        rep = df_e.groupby(df_e["FECHA"].dt.to_period("M")).size()

    st.line_chart(rep)

    st.divider()

    # 🚨 Grupos con más reportes
    st.subheader("🚨 Grupos con más reportes")

    grp_rep = (
        df_r.groupby("GRUPO")
        .size()
        .sort_values(ascending=False)
    )

    st.bar_chart(grp_rep)

    st.divider()

    # 👤 Alumnos con más reportes
    st.subheader("👤 Alumnos con más reportes")

    if df_r.empty:
        st.info("Aún no hay reportes registrados")
    else:
        top_al = (
            df_r.groupby(["MATRICULA", "NOMBRE"])
            .size()
            .reset_index(name="REPORTES")
            .sort_values("REPORTES", ascending=False)
        )

        st.dataframe(top_al.head(10), use_container_width=True)























































































