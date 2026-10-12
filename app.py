
import streamlit as st
import pandas as pd
from supabase import create_client

# ==========================================
# CONFIGURACION GENERAL
# ==========================================

st.set_page_config(
    page_title="TAPPAD Radar",
    page_icon="📡",
    layout="wide"
)

# ==========================================
# CONEXION A SUPABASE
# ==========================================

def conectar_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]

    return create_client(url, key)


# ==========================================
# LICITACIONES DE DEMOSTRACION
# ==========================================

licitaciones = [
    {
        "Procedimiento": "DEMO-001",
        "Dependencia": "Dependencia de demostración A",
        "Descripción": "Adquisición de material de oficina",
        "Fuente": "ComprasMX",
        "Estado": "Demostración"
    },
    {
        "Procedimiento": "DEMO-002",
        "Dependencia": "Dependencia de demostración B",
        "Descripción": "Servicio de limpieza de instalaciones",
        "Fuente": "SECOP Coahuila",
        "Estado": "Demostración"
    },
    {
        "Procedimiento": "DEMO-003",
        "Dependencia": "Dependencia de demostración C",
        "Descripción": "Mantenimiento de equipos de cómputo",
        "Fuente": "ComprasMX",
        "Estado": "Demostración"
    }
]

df = pd.DataFrame(licitaciones)


# ==========================================
# ENCABEZADO
# ==========================================

st.title("📡 TAPPAD Radar")

st.subheader(
    "Sistema de monitoreo de oportunidades "
    "en licitaciones públicas"
)

st.info(
    "Versión MVP. Las licitaciones mostradas "
    "actualmente son datos de demostración."
)

st.divider()


# ==========================================
# MENU PRINCIPAL
# ==========================================

menu = st.sidebar.radio(
    "Menú principal",
    [
        "Explorar licitaciones",
        "Registrar empresa",
        "Panel administrativo"
    ]
)


# ==========================================
# EXPLORAR LICITACIONES
# ==========================================

if menu == "Explorar licitaciones":

    st.header("Oportunidades de contratación")

    busqueda = st.text_input(
        "Buscar por palabra clave"
    )

    if busqueda.strip():

        filtro = df[
            df["Descripción"].str.contains(
                busqueda.strip(),
                case=False,
                na=False,
                regex=False
            )
            |
            df["Dependencia"].str.contains(
                busqueda.strip(),
                case=False,
                na=False,
                regex=False
            )
        ]

    else:
        filtro = df

    st.dataframe(
        filtro,
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        "Próximamente: integración automática "
        "con ComprasMX y SECOP Coahuila."
    )


# ==========================================
# REGISTRO DE EMPRESAS
# ==========================================

elif menu == "Registrar empresa":

    st.header("Registro de empresas")

    st.write(
        "Registra tu empresa para recibir "
        "información sobre oportunidades "
        "de contratación pública."
    )

    with st.form("formulario_registro"):

        nombre = st.text_input(
            "Nombre de la empresa"
        )

        correo = st.text_input(
            "Correo electrónico"
        )

        palabras = st.text_area(
            "Productos o servicios de interés",
            placeholder=(
                "Ejemplo: limpieza, papelería, "
                "mantenimiento, seguridad"
            )
        )

        enviar = st.form_submit_button(
            "Registrar empresa"
        )

    if enviar:

        if not nombre.strip():
            st.warning(
                "Ingresa el nombre de la empresa."
            )

        elif not correo.strip():
            st.warning(
                "Ingresa un correo electrónico."
            )

        elif not palabras.strip():
            st.warning(
                "Ingresa los productos o servicios "
                "de interés."
            )

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

                st.success(
                    "¡Registro guardado correctamente!"
                )

                st.info(
                    "Tu empresa ha sido registrada "
                    "en TAPPAD Radar."
                )

            except Exception as error:

                st.error(
                    "No fue posible guardar el registro "
                    "en Supabase."
                )

                st.caption(
                    f"Detalle técnico: {error}"
                )


# ==========================================
# PANEL ADMINISTRATIVO
# ==========================================

elif menu == "Panel administrativo":

    st.header("Panel administrativo")

    st.write(
        "Acceso exclusivo para "
        "TAPPAD Consultoría."
    )

    clave = st.text_input(
        "Contraseña de administrador",
        type="password"
    )

    if st.button("Ingresar"):

        try:
            clave_correcta = st.secrets[
                "admin_password"
            ]

            if clave == clave_correcta:

                st.success(
                    "Acceso administrativo autorizado."
                )

                st.subheader(
                    "Estado del sistema"
                )

                st.write(
                    "Aplicación: TAPPAD Radar MVP"
                )

                st.write(
                    "Base de datos: Supabase"
                )

                st.write(
                    "Fuentes previstas: ComprasMX "
                    "y SECOP Coahuila"
                )

                st.info(
                    "La consulta administrativa de "
                    "clientes se implementará "
                    "posteriormente mediante "
                    "un acceso seguro."
                )

            else:

                st.error(
                    "Contraseña incorrecta."
                )

        except Exception as error:

            st.error(
                "No fue posible verificar "
                "el acceso administrativo."
            )


# ==========================================
# PIE DE PAGINA
# ==========================================

st.divider()

st.caption(
    "TAPPAD Radar | "
    "Desarrollado por TAPPAD Consultoría"
)
