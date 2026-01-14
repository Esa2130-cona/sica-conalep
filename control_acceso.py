import streamlit as st
import pandas as pd
from datetime import datetime
import os
import pytz

# --------------------------------------------------
# 1. CONFIGURACIÓN GENERAL
# --------------------------------------------------
st.set_page_config(
    page_title="SICA Conalep Cuautla",
    layout="wide"
)

zona_horaria = pytz.timezone("America/Mexico_City")

st.markdown("""
<style>
.stApp { background-color: #F8F9FA; color: #212529; }
h1, h2, h3 { color: #006437 !important; }
.big-font { font-size:35px !important; font-weight:bold; color:#006437; }
.status-box {
    padding: 25px;
    border-radius: 20px;
    text-align: center;
    background-color: #FFFFFF;
    border: 3px solid #006437;
    color: #006437;
    box-shadow: 0px 4px 15px rgba(0,0,0,0.1);
}
.aviso-box {
    padding: 15px;
    background-color: #FFF3CD;
    color: #856404;
    border-radius: 12px;
    border-left: 8px solid #FFC107;
    font-weight: bold;
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# 2. GOOGLE SHEETS
# --------------------------------------------------
SHEET_ID = "11RZyoBo_MyQkGWfc21WCY_xPFZdKkwTG12YagiZf3yM"

@st.cache_data(ttl=10)
def cargar_base(nombre_hoja):
    url = (
        f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
        f"/gviz/tq?tqx=out:csv&sheet={nombre_hoja}"
    )
    try:
        df = pd.read_csv(url)
        df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
        df.columns = [str(c).strip().upper() for c in df.columns]

        if "MATRICULA" in df.columns:
            df["MATRICULA"] = (
                df["MATRICULA"]
                .astype(str)
                .str.strip()
                .str.replace("'", "-", regex=False)
            )

        return df
    except Exception as e:
        st.error(f"❌ Error al cargar la hoja: {nombre_hoja}")
        st.exception(e)
        return pd.DataFrame()

# Cargar hojas
df_alumnos     = cargar_base("Alumnos")
df_academico   = cargar_base("Academico")
df_incidencias = cargar_base("Incidencias")
df_usuarios    = cargar_base("Usuarios")

# --------------------------------------------------
# 3. LOGIN
# --------------------------------------------------
if "user_data" not in st.session_state:
    st.session_state.user_data = None

if st.session_state.user_data is None:
    st.title("🛡️ SICA - CONALEP CUAUTLA")

    usuario = st.text_input("Usuario")
    pin = st.text_input("PIN", type="password")

    if st.button("INGRESAR", use_container_width=True):
        if df_usuarios.empty:
            st.error("No se pudo cargar la base de usuarios")
            st.stop()

        match = df_usuarios[
            (df_usuarios["USUARIO"].astype(str).str.lower() == usuario.lower()) &
            (df_usuarios["PIN"].astype(str) == pin)
        ]

        if not match.empty:
            st.session_state.user_data = match.iloc[0].to_dict()
            st.rerun()
        else:
            st.error("Usuario o PIN incorrectos")

    st.stop()

# --------------------------------------------------
# 4. PANEL PRINCIPAL
# --------------------------------------------------
user = st.session_state.user_data

st.sidebar.title(f"👤 {user.get('NOMBRE', 'Usuario')}")
opciones = ["Puerta de Entrada", "Historial Alumnos"]

if user.get("ROL") == "ADMIN":
    opciones.append("Administrar Usuarios")

if user.get("ROL") in ["PREFECTO", "ADMIN"]:
    opciones.append("Reportes")

if user.get("ROL") in ["SERV_ESCOLARES", "ADMIN"]:
    opciones.append("Incidencias")

if user.get("ROL") in ["FORMACION", "ADMIN"]:
    opciones.append("Académico")

menu = st.sidebar.radio("MENÚ", opciones)
if st.sidebar.button("Cerrar Sesión"):
    st.session_state.user_data = None
    st.rerun()

# --------------------------------------------------
# 5. PUERTA DE ENTRADA
# --------------------------------------------------
if menu == "Puerta de Entrada":
    st.title("🚀 Registro de Acceso")

    if "id_leido" not in st.session_state:
        st.session_state.id_leido = ""

    def al_escanear():
        raw = st.session_state.input_lector
        st.session_state.id_leido = raw.replace("'", "-").strip()
        st.session_state.input_lector = ""

    st.text_input("👇 ESCANEE AQUÍ", key="input_lector", on_change=al_escanear)

    mat = st.session_state.id_leido

    if mat:
        res = df_alumnos[df_alumnos["MATRICULA"] == mat]

        if not res.empty:
            al = res.iloc[0]

            c1, c2 = st.columns([1, 2])

            with c1:
                foto = f"Fotos-Alumnos/{mat}.jpg"
                if os.path.exists(foto):
                    st.image(foto, width=300)
                else:
                    st.info("📷 Foto no disponible")

            with c2:
                st.markdown(
                    f"<p class='big-font'>{al.get('NOMBRE','')} {al.get('PRIMER APELLIDO','')}</p>",
                    unsafe_allow_html=True
                )

                st.write(f"### Grupo: {al.get('GRUPO', 'S/G')}")

                aviso = al.get("AVISO_ENTRADA", "")
                if pd.notna(aviso) and str(aviso).strip() != "":
                    st.markdown(
                        f"<div class='aviso-box'>📢 AVISO: {aviso}</div>",
                        unsafe_allow_html=True
                    )

                hora = datetime.now(zona_horaria).strftime("%H:%M:%S")
                st.markdown(
                    f"<div class='status-box'>✅ ACCESO REGISTRADO<br>{hora}</div>",
                    unsafe_allow_html=True
                )
        else:
            st.error(f"❌ La matrícula {mat} no existe.")

# --------------------------------------------------
# 6. HISTORIAL DE ALUMNOS
# --------------------------------------------------
elif menu == "Historial Alumnos":
    st.title("🔍 Consulta de Expedientes")

    m_busc = st.text_input("Matrícula del alumno").replace("'", "-").strip()

    if m_busc:
        busc_res = df_alumnos[df_alumnos["MATRICULA"] == m_busc]

        if not busc_res.empty:
            al_h = busc_res.iloc[0]

            st.header(
                f"Expediente: {al_h.get('NOMBRE','')} {al_h.get('PRIMER APELLIDO','')}"
            )

            t1, t2 = st.tabs(["📊 Académico", "📜 Incidencias"])

            with t1:
                ac_h = df_academico[df_academico["MATRICULA"] == m_busc]
                st.dataframe(ac_h, hide_index=True)

            with t2:
                in_h = df_incidencias[df_incidencias["MATRICULA"] == m_busc]
                st.dataframe(in_h, hide_index=True)

        else:
            st.error("Matrícula no encontrada.")
elif menu == "Administrar Usuarios":
    st.title("👥 Alta de Usuarios")

    st.subheader("➕ Nuevo usuario")

    with st.form("form_usuario"):
        nuevo_usuario = st.text_input("Usuario")
        nuevo_pin = st.text_input("PIN")
        nuevo_nombre = st.text_input("Nombre completo")
        nuevo_rol = st.selectbox(
            "Rol",
            ["ADMIN", "PREFECTO", "SERV_ESCOLARES", "FORMACION"]
        )

        guardar = st.form_submit_button("Guardar usuario")

    if guardar:
        if not all([nuevo_usuario, nuevo_pin, nuevo_nombre]):
            st.error("Todos los campos son obligatorios")
        else:
            # Evitar usuarios duplicados
            if nuevo_usuario.lower() in df_usuarios["USUARIO"].astype(str).str.lower().values:
                st.error("Ese usuario ya existe")
            else:
                nueva_fila = {
                    "USUARIO": nuevo_usuario,
                    "PIN": nuevo_pin,
                    "NOMBRE": nuevo_nombre,
                    "ROL": nuevo_rol
                }

                df_usuarios = pd.concat(
                    [df_usuarios, pd.DataFrame([nueva_fila])],
                    ignore_index=True
                )

                # Guardar en Google Sheets
                url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit"
                st.success("✅ Usuario creado (recarga la app)")

    st.divider()
    st.subheader("📋 Usuarios existentes")
    st.dataframe(df_usuarios, hide_index=True)
elif menu == "Reportes":
    st.title("📝 Registro de Reportes")

    matricula = st.text_input("Matrícula del alumno").replace("'", "-").strip()

    alumno = None
    if matricula:
        res = df_alumnos[df_alumnos["MATRICULA"] == matricula]
        if not res.empty:
            alumno = res.iloc[0]
            st.success(
                f"Alumno: {alumno.get('NOMBRE','')} {alumno.get('PRIMER APELLIDO','')} | "
                f"Grupo: {alumno.get('GRUPO','')}"
            )
        else:
            st.error("Matrícula no encontrada")

    tipo = st.selectbox(
        "Tipo de reporte",
        ["Disciplina", "Conducta", "Uniforme", "Asistencia", "Otro"]
    )

    descripcion = st.text_area("Descripción del reporte")

    if st.button("Registrar reporte"):
        if not matricula or alumno is None or not descripcion:
            st.error("Completa todos los campos correctamente")
        else:
            fecha = datetime.now(zona_horaria).strftime("%Y-%m-%d")
            hora = datetime.now(zona_horaria).strftime("%H:%M:%S")

            nuevo_reporte = {
                "FECHA": fecha,
                "HORA": hora,
                "MATRICULA": matricula,
                "NOMBRE": f"{alumno.get('NOMBRE','')} {alumno.get('PRIMER APELLIDO','')}",
                "GRUPO": alumno.get("GRUPO", ""),
                "TIPO": tipo,
                "DESCRIPCION": descripcion,
                "REGISTRO_POR": user.get("NOMBRE", "")
            }

            st.success("✅ Reporte listo para guardarse")
            st.json(nuevo_reporte)

