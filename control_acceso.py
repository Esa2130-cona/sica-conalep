import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
import threading
import time 

st.set_page_config(page_title="SICA CONALEP CUAUTLA", layout="wide")
zona = pytz.timezone("America/Mexico_City")

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
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwK34FQ5zo5yW7FKl_O1gpdzu8pYB4Q_UfL9QiRUH-jyZ0vHd738MQnJcTbHibmbO6RLA/exec"

GIDS = {
    "ALUMNOS": 1882885827,
    "USUARIOS": 921806663,
    "ENTRADAS": 25814912,
    "INCIDENCIAS": 2080119575,
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

# ================= MENU =================
opciones = ["Puerta de Entrada", "Historial Alumnos", "Dashboard"]
if rol == "ADMIN": opciones += ["Usuarios"]
if rol in ["ADMIN","PREFECTO"]: opciones += ["Reportes"]

menu = st.sidebar.radio("MENÚ PRINCIPAL", opciones)

# ================= PUERTA =================
if menu == "Puerta de Entrada":
    df = cargar(GIDS["ALUMNOS"])
    df.columns = [c.strip().upper() for c in df.columns]

    st.markdown("<h4 style='text-align:center;'>ESCANEE CREDENCIAL</h4>", unsafe_allow_html=True)

    if "scan_input" not in st.session_state:
        st.session_state.scan_input = ""
    if "resultado" not in st.session_state:
        st.session_state.resultado = None

    def procesar_scan():
        mat = st.session_state.scan_input.strip()
        st.session_state.scan_input = ""

        if not mat:
            return

        a = df[df["MATRICULA"].astype(str).str.strip() == mat]

        if a.empty:
            st.session_state.resultado = {
                "tipo": "error",
                "mensaje": "MATRÍCULA NO ENCONTRADA"
            }
        else:
            al = a.iloc[0]

            st.session_state.resultado = {
                "tipo": "ok",
                "alumno": al
            }

            payload = {
                "TIPO_REGISTRO": "ENTRADA",
                "FECHA_REGISTRO": datetime.now(zona).strftime("%Y-%m-%d %H:%M:%S"),
                "FECHA": datetime.now(zona).strftime("%Y-%m-%d"),
                "HORA": datetime.now(zona).strftime("%H:%M:%S"),
                "MATRICULA": str(al["MATRICULA"]),
                "NOMBRE": al["NOMBRE"],
                "GRUPO": al["GRUPO"],
                "REGISTRO_POR": user["USUARIO"]
            }

            threading.Thread(target=enviar, args=(payload,)).start()

    # 👉 ESTO SIEMPRE SE RENDERIZA
    st.text_input(
        "Esperando lectura...",
        key="scan_input",
        on_change=procesar_scan
    )

    # 👉 RESULTADO VISUAL ABAJO
    if st.session_state.resultado:
        r = st.session_state.resultado

        if r["tipo"] == "ok":
            st.markdown(f"""
            <div style="background:#0f5132;color:white;padding:40px;border-radius:20px;text-align:center;">
                <h1>✔ ACCESO PERMITIDO</h1>
                <h2>{r['alumno']['NOMBRE']}</h2>
                <h3>Grupo: {r['alumno']['GRUPO']}</h3>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background:#842029;color:white;padding:40px;border-radius:20px;text-align:center;">
                <h1>✖ ACCESO DENEGADO</h1>
                <h2>MATRÍCULA NO VÁLIDA</h2>
            </div>
            """, unsafe_allow_html=True)

        time.sleep(2)
        st.session_state.resultado = None
        st.rerun()


# === VISTA VISUAL DE RESULTADO ===
if st.session_state.resultado:
    r = st.session_state.resultado

    if r["tipo"] == "ok":
        st.markdown(f"""
        <div style="
            background-color:#0f5132;
            color:white;
            padding:40px;
            border-radius:20px;
            text-align:center;
            margin-top:20px;
        ">
            <h1>✔ ACCESO PERMITIDO</h1>
            <h2>{r['alumno']['NOMBRE']}</h2>
            <h3>Grupo: {r['alumno']['GRUPO']}</h3>
        </div>
        """, unsafe_allow_html=True)

        # 🔊 sonido OK
        # st.audio("ok.mp3", autoplay=True)

    else:
        st.markdown("""
        <div style="
            background-color:#842029;
            color:white;
            padding:40px;
            border-radius:20px;
            text-align:center;
            margin-top:20px;
        ">
            <h1>✖ ACCESO DENEGADO</h1>
            <h2>MATRÍCULA NO VÁLIDA</h2>
        </div>
        """, unsafe_allow_html=True)
          # ⏱️ ESPERA 2 SEGUNDOS Y LIMPIA
    time.sleep(2)
    st.session_state.resultado = None
    st.rerun()

        # 🔊 sonido ERROR
        # st.audio("error.mp3", autoplay=True)

    # 👇 MOSTRAR RESULTADO
    if st.session_state.resultado:
        r = st.session_state.resultado

        if r["tipo"] == "ok":
            st.success(r["mensaje"])
            # 🔊 sonido OK (si ya lo tenías)
            # st.audio("ok.mp3", autoplay=True)

        else:
            st.error(r["mensaje"])
            # 🔊 sonido ERROR
            # st.audio("error.mp3", autoplay=True)

        # limpiar después de mostrar
        st.session_state.resultado = None


# ================= INCIDENCIAS =================
    elif menu == "Reportes":
    df = cargar(GIDS["ALUMNOS"])
    mat = st.text_input("Matrícula").strip()

    if mat:
        a = df[df["MATRICULA"].astype(str) == mat]

        if not a.empty:
            tipo = st.selectbox("Tipo", ["Retardo", "Falta", "Uniforme", "Conducta"])
            obs = st.text_area("Descripción")

            if st.button("Guardar"):
                enviar({
                    "TIPO_REGISTRO": "REPORTE",
                    "FECHA": datetime.now(zona).strftime("%Y-%m-%d"),
                    "HORA": datetime.now(zona).strftime("%H:%M:%S"),
                    "MATRICULA": mat,
                    "NOMBRE": a.iloc[0]["NOMBRE"],
                    "GRUPO": a.iloc[0]["GRUPO"],
                    "TIPO": tipo,
                    "DESCRIPCION": obs,
                    "REGISTRADO_POR": user["USUARIO"]
                })

                st.success("Reporte registrado")

# ================= USUARIOS =================
elif menu == "Usuarios":
    st.title("👤 Administración de Usuarios")
    df = cargar(GIDS["USUARIOS"])
    st.dataframe(df)

    with st.form("nuevo"):
        u = st.text_input("Usuario")
        p = st.text_input("PIN")
        r = st.selectbox("Rol",["ADMIN","PREFECTO"])
        if st.form_submit_button("Crear"):
            enviar ({"TIPO_REGISTRO":"USUARIO","USUARIO":u,"PIN":p,"ROL":r})

            st.success("Usuario creado")

# ================= DASHBOARD =================
elif menu == "Dashboard":
    st.title("📊 Dashboard Analítico")
    df_e = cargar(GIDS["ENTRADAS"])
    df_i = cargar(GIDS["INCIDENCIAS"])

    st.metric("Total Entradas", len(df_e))
    st.metric("Total Incidencias", len(df_i))
    st.bar_chart(df_i["TIPO"].value_counts())

# ================= HISTORIAL =================
elif menu == "Historial Alumnos":
    df = cargar(GIDS["ENTRADAS"])
    m = st.text_input("Matrícula").strip()
    if m:
        st.dataframe(df[df["MATRICULA"].astype(str)==m])






























