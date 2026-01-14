import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import pytz

# ================= CONFIG =================
st.set_page_config(page_title="SICA CONALEP", layout="wide")
zona = pytz.timezone("America/Mexico_City")

SHEET_ID = "11RZyoBo_MyQkGWfc21WCY_xPFZdKkwTG12YagiZf3yM"
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwEzRUIDz4YtnT40VIbAwUs7WOgba0DWjSTYt2d7-QdZKFo3BCetNrB0kSy4Y4w4fTncg/exec"

GID_ALUMNOS = 1882885827
GID_USUARIOS = 921806663
GID_ENTRADAS = 25814912
GID_INCIDENCIAS = 2080119575
GID_ACADEMICO = 1794524153

# ================= UTIL =================
@st.cache_data(ttl=10)
@st.cache_data(ttl=10)
def cargar(gid):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={gid}"
    df = pd.read_csv(url)

    # Limpiar columnas
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.upper()
        .str.replace("Á","A")
        .str.replace("É","E")
        .str.replace("Í","I")
        .str.replace("Ó","O")
        .str.replace("Ú","U")
    )

    return df

df_alumnos = cargar(GID_ALUMNOS)
df_usuarios = cargar(GID_USUARIOS)
df_entradas = cargar(GID_ENTRADAS)
df_incidencias = cargar(GID_INCIDENCIAS)
df_academico = cargar(GID_ACADEMICO)

# ================= LOGIN =================
if "user" not in st.session_state:
    st.session_state.user = None

if not st.session_state.user:
    st.title("🔐 SICA - CONALEP CUAUTLA")
    u = st.text_input("Usuario")
    p = st.text_input("PIN", type="password")
    if st.button("Ingresar"):
        m = df_usuarios[
            (df_usuarios["USUARIO"].str.lower() == u.lower()) &
            (df_usuarios["PIN"].astype(str) == p)
        ]
        if not m.empty:
            st.session_state.user = m.iloc[0].to_dict()
            st.rerun()
        else:
            st.error("Credenciales incorrectas")
    st.stop()

user = st.session_state.user

# ================= MENU =================
opciones = set(["Puerta de Entrada", "Historial Alumnos"])
rol = user["ROL"].upper()

if rol == "ADMIN":
    opciones |= {"Incidencias", "Academico", "Reportes"}

elif rol == "PREFECTO":
    opciones |= {"Incidencias", "Reportes"}

elif rol == "SERVICIOS_ESCOLARES":
    opciones.add("Incidencias")

elif rol == "FORMACION":
    opciones.add("Academico")

menu = st.sidebar.radio("MENÚ", sorted(opciones))
st.sidebar.button("Cerrar sesión", on_click=lambda: st.session_state.update(user=None))

# ================= PUERTA =================
if menu == "Puerta de Entrada":
    st.markdown("<h1 style='text-align: center;'>🚪 CONTROL DE ACCESO AlUMNOS</h1>", unsafe_allow_html=True)
    
    # Input para el escáner
    mat = st.text_input("ESPERANDO ESCANEO DE CREDENCIAL...", key="input_scanner").strip()

    if mat:
        # Buscar alumno
        a = df_alumnos[df_alumnos["MATRICULA"].astype(str) == mat]
        
        if a.empty:
            st.markdown(f"""<div style='background-color:#F2D7D5; padding:30px; border-radius:15px; text-align:center;'>
                <h1 style='color:#943126;'>❌ MATRÍCULA NO ENCONTRADA</h1>
                <p>Por favor, acuda a Servicios Escolares.</p>
                </div>""", unsafe_allow_html=True)
        else:
            al = a.iloc[0]
            nombre = f"{al['NOMBRE']} {al['PRIMER APELLIDO']}"
            grupo = al['GRUPO']
            # Obtener foto (columna FOTO) o usar una por defecto
            url_foto = al.get('FOTO', "https://cdn-icons-png.flaticon.com/512/3135/3135715.png")
            
            # --- DISEÑO DE BIENVENIDA ---
            st.divider()
            col1, col2 = st.columns([1, 2])
            
            with col1:
                st.image(url_foto, width=300)
            
            with col2:
                st.markdown(f"<p class='status-acceso'>✅ ACCESO PERMITIDO</p>", unsafe_allow_html=True)
                st.markdown(f"<p class='nombre-alumno'>{nombre}</p>", unsafe_allow_html=True)
                st.markdown(f"### GRUPO: {grupo}")
                st.markdown(f"#### HORA: {datetime.now(zona).strftime('%H:%M:%S')}")
                st.balloons()

            # Registro automático en la base de datos (Google Sheets)
            payload = {
                "TIPO_REGISTRO": "ENTRADA",
                "FECHA": datetime.now(zona).strftime("%Y-%m-%d"),
                "HORA": datetime.now(zona).strftime("%H:%M:%S"),
                "MATRICULA": mat,
                "NOMBRE": nombre,
                "GRUPO": grupo,
                "REGISTRO_POR": user["NOMBRE"]
            }
            try:
                requests.post(APPS_SCRIPT_URL, json=payload)
            except:
                st.warning("Error de conexión al guardar, pero el alumno ha sido verificado.")

# ================= INCIDENCIAS =================
elif menu == "Incidencias":
    st.title("🚨 Incidencias")
    mat = st.text_input("Matrícula").replace("'", "-").strip()
    if mat:
        al = df_alumnos[df_alumnos["MATRICULA"] == mat]
        if not al.empty:
            al = al.iloc[0]
            tipo = st.selectbox("Tipo", ["Retardo", "Falta", "Disciplina"])
            desc = st.text_area("Descripción")
            if st.button("Registrar incidencia"):
                requests.post(APPS_SCRIPT_URL, json={
                    "TIPO_REGISTRO": "INCIDENCIA",
                    "FECHA": datetime.now(zona).strftime("%Y-%m-%d"),
                    "HORA": datetime.now(zona).strftime("%H:%M:%S"),
                    "MATRICULA": mat,
                    "NOMBRE": al["NOMBRE"],
                    "GRUPO": al["GRUPO"],
                    "TIPO": tipo,
                    "DESCRIPCION": desc,
                    "REGISTRO_POR": user["NOMBRE"]
                })
                st.success("Incidencia registrada")

# ================= ACADEMICO =================
elif menu == "Academico":
    st.title("📚 Registro Académico")
    mat = st.text_input("Matrícula")
    materia = st.text_input("Materia")
    periodo = st.text_input("Periodo")
    cal = st.number_input("Calificación", 0, 100)
    if st.button("Guardar"):
        requests.post(APPS_SCRIPT_URL, json={
            "TIPO_REGISTRO": "ACADEMICO",
            "MATRICULA": mat,
            "MATERIA": materia,
            "PERIODO": periodo,
            "CALIFICACION": cal,
            "REGISTRO_POR": user["NOMBRE"]
        })
        st.success("Registro académico guardado")

# ================= HISTORIAL =================
elif menu == "Historial Alumnos":
    st.title("📊 Historial")
    tab1, tab2 = st.tabs(["Por alumno", "Por día"])

    with tab1:
        mat = st.text_input("Matrícula alumno")
        if mat:
            st.dataframe(df_entradas[df_entradas["MATRICULA"] == mat])

    with tab2:
        f = st.date_input("Fecha")
        st.dataframe(df_entradas[df_entradas["FECHA"] == str(f)])

# ================= REPORTES =================
elif menu == "Reportes":
    st.title("📈 Reporte mensual")
    df_entradas["FECHA"] = pd.to_datetime(df_entradas["FECHA"])
    mensual = df_entradas.groupby(df_entradas["FECHA"].dt.to_period("M")).size()
    st.bar_chart(mensual)





