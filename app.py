
import streamlit as st
import pandas as pd
from supabase import create_client

st.set_page_config(
    page_title="TAPPAD Radar",
    page_icon="💼",
    layout="wide"
)


def normalizar(text):
    if not text:
        return ""

    text = str(text).lower().strip()
    for a, b in [
        ("á", "a"), ("é", "e"), ("í", "i"),
        ("ó", "o"), ("ú", "u"), ("ü", "u"),
        ("ñ", "n")
    ]:
        text = text.replace(a, b)

    return text


@st.cache_resource
def conectar_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


licitaciones_gobierno = [
    {
        "id": "DEMO-001",
        "portal": "ComprasMX (demo)",
        "titulo": "Construcción de puente vehicular y vialidades",
        "dependencia": "SCT"
    },
    {
        "id": "DEMO-002",
        "portal": "Coahuila (demo)",
        "titulo": "Adquisición de licencias de software y computadoras",
        "dependencia": "SEFIN Coahuila"
    },
    {
        "id": "DEMO-003",
        "portal": "ComprasMX (demo)",
        "titulo": "Servicio de limpieza profunda y sanitización",
        "dependencia": "IMSS"
    },
    {
        "id": "DEMO-004",
        "portal": "Coahuila (demo)",
        "titulo": "Pavimentación y bacheo asfáltico en Saltillo",
        "dependencia": "Infraestructura Coahuila"
    }
]

st.title("TAPPAD Radar")
st.caption(
    "Prototipo de monitoreo de oportunidades de contratación pública."
)

vista = st.radio(
    "Selecciona una vista",
    ["Vista del cliente", "Acceso de consultor"],
    horizontal=True
)

if vista == "Vista del cliente":
    st.header("Registro de empresas")
    st.write(
        "Registra tu empresa y las palabras clave "
        "de los productos o servicios que ofreces."
    )

    with st.form("formulario_registro", clear_on_submit=True):
        nombre = st.text_input(
            "Nombre de la empresa / razón social"
        )
        correo = st.text_input("Correo electrónico")
        palabras = st.text_input(
            "Palabras clave separadas por comas"
        )
        enviar = st.form_submit_button("REGISTRAR EMPRESA")

    if enviar:
        if not nombre.strip() or not correo.strip() or not palabras.strip():
            st.error("Completa los tres campos para continuar.")

        elif "@" not in correo or "." not in correo.split("@")[-1]:
            st.error("Introduce un correo electrónico válido.")

        else:
            try:
                
supabase = conectar_supabase()

supabase.table("clientes").insert(
    {
        "empresa": nombre.strip(),
        "correo": correo.strip().lower(),
        "palabras_clave": palabras.strip()
    },
    returning="minimal"
).execute()

st.success("¡Registro guardado correctamente!")


                if resultado.data:
                    st.success(
                        "Empresa registrada correctamente. "
                        "El registro quedó guardado en la base de datos."
                    )
                else:
                    st.error(
                        "No se confirmó el registro. "
                        "Verifica la tabla en Supabase antes de volver a intentarlo."
                    )

            except Exception as error:
                st.error(
                    "No fue posible guardar el registro en Supabase. "
                    "Revisa la configuración y los permisos de la base de datos."
                )
                st.caption(f"Detalle técnico: {error}")

            palabras_lista = [
                normalizar(p.strip())
                for p in palabras.split(",")
                if p.strip()
            ]

            coincidencias = []

            for lic in licitaciones_gobierno:
                texto = normalizar(
                    lic["titulo"] + " " + lic["dependencia"]
                )
                if any(k in texto for k in palabras_lista):
                    coincidencias.append(lic)

            st.subheader("Coincidencias de demostración")

            if coincidencias:
                for lic in coincidencias:
                    st.markdown(
                        f"- **{lic['titulo']}** — {lic['portal']} — "
                        f"{lic['dependencia']} ({lic['id']})"
                    )
            else:
                st.info(
                    "No hay coincidencias en los datos de demostración."
                )

            st.warning(
                "Las licitaciones mostradas son ejemplos. "
                "Todavía no se consultan automáticamente los portales "
                "ni se envían alertas por correo."
            )

elif vista == "Acceso de consultor":
    st.header("Panel privado de consultor")

    try:
        clave_admin = st.secrets.get("admin_password", "")
    except Exception:
        clave_admin = ""

    if not clave_admin:
        st.error(
            "Falta configurar admin_password en Streamlit → Settings → Secrets."
        )
    else:
        if "admin_autenticado" not in st.session_state:
            st.session_state.admin_autenticado = False

        with st.form("formulario_admin"):
            password = st.text_input(
                "Contraseña de administrador",
                type="password"
            )
            entrar = st.form_submit_button("Iniciar sesión")

        if entrar:
            st.session_state.admin_autenticado = (
                password == clave_admin
            )

            if st.session_state.admin_autenticado:
                st.rerun()
            else:
                st.error("Contraseña incorrecta.")

        if st.session_state.admin_autenticado:
            st.success("Sesión de administrador activa.")

            if st.button("Cerrar sesión"):
                st.session_state.admin_autenticado = False
                st.rerun()

            st.subheader("Estado del sistema")
            st.write(
                "Los nuevos registros se guardan en Supabase. "
                "La consulta de los registros desde este panel privado "
                "se configurará en un siguiente paso."
            )

            st.subheader("Licitaciones de demostración")
            st.dataframe(
                pd.DataFrame(licitaciones_gobierno),
                use_container_width=True
            )

            st.warning(
                "Los cuatro registros de licitaciones son ejemplos, "
                "no datos extraídos en tiempo real."
            )
