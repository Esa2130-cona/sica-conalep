import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz
import threading

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
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwEzRUIDz4YtnT40VIbAwUs7WOgba0DWjSTYt2d7-QdZKFo3BCetNrB0kSy4Y4w4fTncg/exec"

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
if rol in ["ADMIN","PREFECTO"]: opciones += ["Incidencias"]

menu = st.sidebar.radio("MENÚ PRINCIPAL", opciones)

# ================= PUERTA =================
if menu == "Puerta de Entrada":
    df = cargar(GIDS["ALUMNOS"])
    df.columns = [str(c).strip().upper() for c in df.columns]

    st.markdown("<h4 style='text-align: center; color: gray;'>ESCANEE CREDENCIAL</h4>", unsafe_allow_html=True)

    # ---- estados seguros ----
    if "scan_input" not in st.session_state:
        st.session_state.scan_input = ""
    if "scan_value" not in st.session_state:
        st.session_state.scan_value = ""

    def procesar_scan():
        st.session_state.scan_value = st.session_state.scan_input
        st.session_state.scan_input = ""

    st.text_input(
        "Esperando lectura...",
        key="scan_input",
        on_change=procesar_scan
    )

    mat = st.session_state.scan_value.replace("'", "-").strip()

    if mat:
        st.session_state.scan_value = ""

        a = df[df["MATRICULA"].astype(str).str.strip() == mat]

        if a.empty:
            # ---- ACCESO NO PERMITIDO ----
            play_audio("https://www.soundjay.com/buttons/beep-04.mp3")
            st.markdown(f"""
                <div class='card-error'>
                    <div class='acceso-denegado'>🚫 ACCESO NO PERMITIDO</div>
                    <div class='msg-error'>MATRÍCULA NO REGISTRADA O BAJA</div>
                    <p style='font-size:30px;'>La matrícula <b>{mat}</b> no existe en la base de datos.</p>
                </div>
            """, unsafe_allow_html=True)

        else:
            # ---- ACCESO PERMITIDO ----
            al = a.iloc[0]
            nombre = f"{al['NOMBRE']} {al['PRIMER APELLIDO']} {al.get('SEGUNDO APELLIDO','')}"

            st.divider()
            c1, c2 = st.columns([1, 2.5])

            with c1:
                st.image(
                    al.get('FOTO', "https://cdn-icons-png.flaticon.com/512/3135/3135715.png"),
                    use_container_width=True
                )

            with c2:
                st.markdown(f"""
                    <div class='card-acceso'>
                        <div class='acceso-permitido'>✅ ACCESO PERMITIDO</div>
                        <div class='nombre-alumno'>{nombre}</div>
                        <div class='datos-escolares'>
                            <b>GRUPO:</b> {al['GRUPO']}<br>
                            <b>HORA:</b> {datetime.now(zona).strftime('%H:%M:%S')}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

            payload = {
                "TIPO_REGISTRO": "ENTRADA",
                "FECHA": datetime.now(zona).strftime("%Y-%m-%d"),
                "HORA": datetime.now(zona).strftime("%H:%M:%S"),
                "MATRICULA": mat,
                "NOMBRE": nombre,
                "GRUPO": al["GRUPO"],
                "REGISTRO_POR": user["NOMBRE"]
            }

            threading.Thread(
                target=enviar_registro_background,
                args=(payload,)
            ).start()

        st.rerun()

# ================= INCIDENCIAS =================
elif menu == "Incidencias":
    df = cargar(GIDS["ALUMNOS"])
    mat = st.text_input("Matrícula").strip()
    if mat:
        a = df[df["MATRICULA"].astype(str)==mat]
        if not a.empty:
            tipo = st.selectbox("Tipo",["Retardo","Falta","Uniforme","Conducta"])
            obs = st.text_area("Observaciones")
            if st.button("Guardar"):
                enviar({"TIPO_REGISTRO":"INCIDENCIA","MATRICULA":mat,"TIPO":tipo,"OBS":obs})
                st.success("Incidencia registrada")

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
            enviar({"TIPO_REGISTRO":"USUARIO","USUARIO":u,"PIN":p,"ROL":r})
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







