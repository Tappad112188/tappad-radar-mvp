
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="TAPPAD Radar",
    page_icon="💼",
    layout="wide"
)


def normalizar(text):
    if not text:
        return ""

    text = str(text).lower().strip()
    reemplazos = [
        ("á", "a"), ("é", "e"), ("í", "i"),
        ("ó", "o"), ("ú", "u"), ("ü", "u"),
        ("ñ", "n")
    ]

    for a, b in reemplazos:
        text = text.replace(a, b)

    return text


# Datos temporales de demostración.
# Todavía no constituyen una base de datos permanente.
if "lista_clientes" not in st.session_state:
    st.session_state.lista_clientes = []

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


st.title("💼 TAPPAD Radar")
st.caption(
    "Prototipo de monitoreo de oportunidades de contratación pública."
)

vista = st.radio(
    "Selecciona una vista",
    ["Vista del cliente", "Acceso de consultor"],
    horizontal=True
)


# --------------------------------------------------
# VISTA DEL CLIENTE
# --------------------------------------------------
if vista == "Vista del cliente":

    st.header("Registro de empresas")
    st.write(
        "Registra tu empresa y las palabras clave "
        "de los productos o servicios que ofreces."
    )

    with st.form("formulario_registro", clear_on_submit=True):
        nombre = st.text_input(
            "Nombre de la empresa / razón social",
            placeholder="Ej. Materiales Sierra Madre S.A."
        )

        correo = st.text_input(
            "Correo electrónico",
            placeholder="empresa@ejemplo.com"
        )

        palabras = st.text_input(
            "Palabras clave separadas por comas",
            placeholder="limpieza, software, computadoras"
        )

        enviar = st.form_submit_button(
            "REGISTRAR EMPRESA"
        )

    if enviar:
        if not nombre.strip() or not correo.strip() or not palabras.strip():
            st.error("Completa los tres campos para continuar.")

        elif "@" not in correo or "." not in correo.split("@")[-1]:
            st.error("Introduce un correo electrónico válido.")

        else:
            nuevo = {
                "nombre": nombre.strip(),
                "correo": correo.strip().lower(),
                "keywords": palabras.strip()
            }

            st.session_state.lista_clientes.append(nuevo)

            st.success(
                f"Registro de demostración recibido para {nombre.strip()}."
            )

            st.info(
                "Este prototipo no guarda los registros de forma permanente, "
                "no envía correos y no consulta automáticamente los portales. "
                "Las oportunidades siguientes son datos de demostración."
            )

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
                        f"- **{lic['titulo']}** — "
                        f"{lic['portal']} — {lic['dependencia']} "
                        f"({lic['id']})"
                    )
            else:
                st.warning(
                    "No hay coincidencias en los datos de demostración."
                )


# --------------------------------------------------
# VISTA PRIVADA DEL CONSULTOR
# --------------------------------------------------
elif vista == "Acceso de consultor":

    st.header("Panel privado de consultor")

    # La contraseña debe configurarse en Streamlit Secrets.
    try:
        clave_admin = st.secrets.get("admin_password", "")
    except Exception:
        clave_admin = ""

    if not clave_admin:
        st.error(
            "El panel está bloqueado porque todavía no se ha configurado "
            "la contraseña de administrador."
        )
        st.markdown(
            "Configúrala en la sección **Settings → Secrets** "
            "de la aplicación en Streamlit."
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
            if password == clave_admin:
                st.session_state.admin_autenticado = True
                st.rerun()
            else:
                st.session_state.admin_autenticado = False
                st.error("Contraseña incorrecta.")

        if st.session_state.admin_autenticado:
            st.success("Sesión de administrador activa.")

            if st.button("Cerrar sesión"):
                st.session_state.admin_autenticado = False
                st.rerun()

            st.subheader("Clientes registrados en esta sesión")

            if st.session_state.lista_clientes:
                st.dataframe(
                    pd.DataFrame(st.session_state.lista_clientes),
                    use_container_width=True
                )
            else:
                st.info(
                    "No hay registros en esta sesión. "
                    "Los registros aún no se comparten entre usuarios."
                )

            st.subheader("Datos de licitaciones de demostración")
            st.dataframe(
                pd.DataFrame(licitaciones_gobierno),
                use_container_width=True
            )

            st.warning(
                "El panel está protegido por contraseña, pero este "
                "prototipo todavía no utiliza una base de datos compartida. "
                "Las licitaciones son ejemplos, no resultados extraídos "
                "en tiempo real."
            )
