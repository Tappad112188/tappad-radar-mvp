import hmac
import re
import requests
import pandas as pd
import streamlit as st
from supabase import create_client
TURNSTILE_SITE_KEY = st.secrets.get("TURNSTILE_SITE_KEY", "")
TURNSTILE_JS = """
export default function({ parentElement, data, setStateValue }) {
    const container = parentElement.querySelector("#tappad-turnstile");

    function renderWidget() {
        if (!container || container.dataset.rendered) return;
        if (!window.turnstile) return;

        container.dataset.rendered = "true";

        window.turnstile.render(container, {
            sitekey: data.sitekey,
            callback: (token) => setStateValue("token", token),
            "expired-callback": () => setStateValue("token", ""),
            "error-callback": (code) => {
                setStateValue("token", "");
                setStateValue("error_code", String(code || "desconocido"));
            }
        });
    }

    if (window.turnstile) {
        renderWidget();
    } else {
        const script = document.createElement("script");
        script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
        script.onload = renderWidget;
        document.head.appendChild(script);
    }
}
"""

turnstile_component = st.components.v2.component(
    "tappad_turnstile",
    html='<div id="tappad-turnstile"></div>',
    js=TURNSTILE_JS,
)

st.set_page_config(page_title="TAPPAD Radar", page_icon="📡", layout="wide")


def conectar_supabase():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


def conectar_supabase_admin():
    # La clave administrativa permanece en Streamlit Secrets.
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ADMIN_KEY"])


ESTADOS_MX = [
    "Aguascalientes", "Baja California", "Baja California Sur", "Campeche",
    "Chiapas", "Chihuahua", "Ciudad de México", "Coahuila", "Colima",
    "Durango", "Guanajuato", "Guerrero", "Hidalgo", "Jalisco", "México",
    "Michoacán", "Morelos", "Nayarit", "Nuevo León", "Oaxaca", "Puebla",
    "Querétaro", "Quintana Roo", "San Luis Potosí", "Sinaloa", "Sonora",
    "Tabasco", "Tamaulipas", "Tlaxcala", "Veracruz", "Yucatán", "Zacatecas",
]

st.title("📡 TAPPAD Radar")
st.subheader("Sistema de monitoreo de oportunidades en licitaciones públicas")
st.info("Versión MVP. Importación automática de ComprasMX configurada dos veces al día. Los expedientes pueden estar vigentes o concluidos.")
st.divider()

menu = st.sidebar.radio("Menú principal", ["Explorar licitaciones", "Registrar empresa", "Panel administrativo"])

if menu == "Explorar licitaciones":
    st.header("Oportunidades de contratación")
    st.caption("Fuente: expedientes guardados en Supabase. Verifica siempre los detalles en ComprasMX.")
    busqueda = st.text_input("Buscar por palabra clave").strip()

    try:
        supabase_admin = conectar_supabase_admin()
        respuesta = (
            supabase_admin.table("licitaciones")
            .select("numero_procedimiento,nombre_procedimiento,descripcion,nombre_dependencia,"
                    "tipo_procedimiento,estatus,entidad_federativa,fecha_publicacion,"
                    "fecha_apertura,fecha_fallo,fuente,url_procedimiento")
            .order("fecha_publicacion", desc=True)
            .limit(1000)
            .execute()
        )
        df = pd.DataFrame(respuesta.data or [])
        if df.empty:
            st.info("Aún no hay licitaciones almacenadas.")
        else:
            def opciones(columna):
                return sorted(df[columna].dropna().astype(str).loc[lambda s: s.str.strip() != ""].unique().tolist())

            col1, col2, col3 = st.columns(3)
            with col1:
                estados = st.multiselect("Estatus del procedimiento", opciones("estatus"))
            with col2:
                entidades = st.multiselect("Entidad federativa", opciones("entidad_federativa"))
            with col3:
                tipos = st.multiselect("Tipo de procedimiento", opciones("tipo_procedimiento"))

            if busqueda:
                columnas_busqueda = [
                    "numero_procedimiento", "nombre_procedimiento", "descripcion",
                    "nombre_dependencia", "tipo_procedimiento", "entidad_federativa"
                ]
                filtro = pd.Series(False, index=df.index)
                for columna in columnas_busqueda:
                    filtro |= df[columna].fillna("").astype(str).str.contains(
                        busqueda, case=False, na=False, regex=False
                    )
                df = df.loc[filtro]
            if estados:
                df = df[df["estatus"].isin(estados)]
            if entidades:
                df = df[df["entidad_federativa"].isin(entidades)]
            if tipos:
                df = df[df["tipo_procedimiento"].isin(tipos)]

            st.metric("Licitaciones encontradas", len(df))
            if df.empty:
                st.info("No se encontraron procedimientos con los filtros seleccionados.")
            else:
                columnas = {
                    "numero_procedimiento": "Procedimiento",
                    "nombre_procedimiento": "Nombre",
                    "descripcion": "Descripción",
                    "nombre_dependencia": "Dependencia",
                    "tipo_procedimiento": "Tipo",
                    "estatus": "Estado",
                    "entidad_federativa": "Entidad",
                    "fecha_publicacion": "Publicación",
                    "fecha_apertura": "Apertura",
                    "fecha_fallo": "Fallo programado",
                    "fuente": "Fuente",
                    "url_procedimiento": "Expediente",
                }
                st.dataframe(
                    df[list(columnas)].rename(columns=columnas),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Expediente": st.column_config.LinkColumn(
                            "Expediente", display_text="Abrir en ComprasMX"
                        )
                    },
                )
            st.caption("Los filtros se aplican a los 1,000 expedientes más recientes consultados. Las fechas provienen de ComprasMX.")
    except KeyError:
        st.error("Falta configurar SUPABASE_URL o SUPABASE_ADMIN_KEY en Streamlit Secrets.")
    except Exception as e:
        st.error("No fue posible consultar las licitaciones.")
        st.error(f"Tipo de error: {type(e).__name__}")

    st.caption("Próximamente: integración de SECOP Coahuila y alertas personalizadas.")

elif menu == "Registrar empresa":
    st.header("Registro de proveedores")
    st.write("Registra tu empresa e indica qué licitaciones te interesan.")
    st.caption("El registro no activa una suscripción ni el envío automático de alertas.")

    try:
        supabase = conectar_supabase()
        catalogo = (
            supabase.table("giros_comerciales")
            .select("id,nombre")
            .eq("activo", True)
            .order("nombre")
            .execute()
        ).data or []
    except Exception:
        catalogo = []
        st.error("No fue posible consultar los giros comerciales. Inténtalo más tarde.")

    if catalogo:
        nombres_giros = {item["nombre"]: item["id"] for item in catalogo}

        st.write("### Verificación de seguridad")
        verificacion = turnstile_component(
            data={"sitekey": TURNSTILE_SITE_KEY},
            default={"token": "", "error_code": ""},
            key="turnstile_registro",
            on_token_change=lambda: None,
            on_error_code_change=lambda: None,
        )
        token_turnstile = verificacion.token
        if verificacion.error_code:
            st.warning(f"Turnstile informó el código de error: {verificacion.error_code}")

        with st.form("formulario_registro_proveedor"):
            st.subheader("Datos empresariales")
            empresa = st.text_input("Razón social o nombre comercial *", max_chars=200)
            rfc = st.text_input("RFC", max_chars=13)
            contacto = st.text_input("Nombre de contacto", max_chars=150)
            correo = st.text_input("Correo electrónico *", max_chars=254)
            telefono = st.text_input("Teléfono", max_chars=25)
            ciudad = st.text_input("Ciudad de domicilio", max_chars=120)
            estado_domicilio = st.selectbox("Estado de domicilio", ["No especificado"] + ESTADOS_MX)

            st.subheader("Productos y servicios")
            giros = st.multiselect("Giros comerciales *", list(nombres_giros))
            palabras = st.text_area(
                "Productos o servicios específicos *",
                placeholder="Ejemplo: artículos de limpieza, mantenimiento de oficinas",
                max_chars=2000,
            )

            st.subheader("Cobertura de oportunidades")
            st.caption("Selecciona estados completos o municipios específicos. Esta cobertura es independiente de tu domicilio.")
            estados_cobertura = st.multiselect("Estados completos", ESTADOS_MX)
            estado_municipio = st.selectbox("Estado de municipios específicos", ["Ninguno"] + ESTADOS_MX)
            municipios = st.text_input(
                "Municipios de ese estado, separados por coma",
                placeholder="Ejemplo: Saltillo, Ramos Arizpe",
                max_chars=500,
                
            )
            consentimiento = st.checkbox(
                "Confirmo que tengo autorización para proporcionar estos datos y recibir comunicaciones relacionadas con mi solicitud."
            )
            enviar = st.form_submit_button("Registrar proveedor")

        if enviar:
            rfc_limpio = rfc.strip().upper()
            correo_limpio = correo.strip().lower()
            ubicaciones = [{"estado": estado, "municipio": None} for estado in estados_cobertura]
            if estado_municipio != "Ninguno":
                municipios_unicos = list(dict.fromkeys(
                    m.strip() for m in municipios.split(",") if m.strip()
                ))
                ubicaciones.extend(
                    {"estado": estado_municipio, "municipio": municipio}
                    for municipio in municipios_unicos
                )
            email_valido = re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", correo_limpio)
            rfc_valido = not rfc_limpio or re.fullmatch(r"[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}", rfc_limpio)
            if not empresa.strip() or not email_valido or not palabras.strip():
                st.warning("Completa la empresa, un correo válido y los servicios de interés.")
            elif not rfc_valido:
                st.warning("Verifica el formato del RFC (12 o 13 caracteres).")
            elif not giros:
                st.warning("Selecciona al menos un giro comercial.")
            elif not ubicaciones:
                st.warning("Selecciona al menos un estado o municipio de cobertura.")
            elif not consentimiento:
                st.warning("Confirma que tienes autorización para proporcionar los datos.")
            elif not token_turnstile:
                st.warning("Completa la verificación de seguridad antes de registrarte.")
            else:
                datos = {
                    "p_empresa": empresa.strip(),
                    "p_correo": correo_limpio,
                    "p_palabras_clave": palabras.strip(),
                    "p_rfc": rfc_limpio or None,
                    "p_nombre_contacto": contacto.strip() or None,
                    "p_telefono": telefono.strip() or None,
                    "p_ciudad": ciudad.strip() or None,
                    "p_estado": estado_domicilio if estado_domicilio != "No especificado" else None,
                    "p_giros": [nombres_giros[nombre] for nombre in giros],
                    "p_ubicaciones": ubicaciones,
                }
                try:
                    respuesta = requests.post(
                        st.secrets["SUPABASE_URL"].rstrip("/")
                        + "/functions/v1/registro-proveedor-seguro",
                        json={"turnstile_token": token_turnstile, "datos": datos},
                        timeout=15,
                    )
                    if respuesta.status_code == 200 and respuesta.json().get("ok") is True:
                        st.success("Solicitud de registro recibida correctamente.")
                        st.info("La activación de alertas y suscripciones se habilitará posteriormente.")
                    elif respuesta.status_code == 409:
                        st.warning("Este correo ya está registrado. Contacta a TAPPAD Consultoría si necesitas actualizar tus datos.")
                    elif respuesta.status_code == 403:
                        st.warning("La verificación de seguridad no fue válida o expiró. Inténtalo de nuevo.")
                    else:
                        st.error("No fue posible completar el registro. Revisa tus datos e inténtalo más tarde.")
                except (requests.RequestException, ValueError, KeyError):
                    st.error("No fue posible conectar con el servicio de registro. Inténtalo más tarde.")
    elif not catalogo:
        st.info("El registro estará disponible cuando se cargue el catálogo de giros.")

elif menu == "Panel administrativo":
    st.header("Panel administrativo")
    st.write("Acceso exclusivo para TAPPAD Consultoría.")

    if "admin_autorizado" not in st.session_state:
        st.session_state.admin_autorizado = False

    if not st.session_state.admin_autorizado:
        with st.form("acceso_admin"):
            clave = st.text_input("Contraseña de administrador", type="password")
            ingresar = st.form_submit_button("Ingresar")
        if ingresar:
            try:
                esperada = str(st.secrets["admin_password"])
                if clave and hmac.compare_digest(clave, esperada):
                    st.session_state.admin_autorizado = True
                    st.rerun()
                else:
                    st.error("Contraseña incorrecta.")
            except KeyError:
                st.error("Falta configurar admin_password en Streamlit Secrets.")
    else:
        if st.button("Cerrar sesión administrativa"):
            st.session_state.admin_autorizado = False
            st.rerun()

        st.subheader("Clientes registrados")
        if st.button("Actualizar listado"):
            st.rerun()

        try:
            supabase_admin = conectar_supabase_admin()
            respuesta = (
                supabase_admin.table("clientes")
                .select("id,empresa,correo,palabras_clave,activo,fecha_registro")
                .order("fecha_registro", desc=True)
                .limit(1000)
                .execute()
            )
            clientes = respuesta.data or []
            st.metric("Clientes mostrados", len(clientes))
            if clientes:
                datos = pd.DataFrame(clientes)
                datos = datos.rename(columns={
                    "id": "ID", "empresa": "Empresa", "correo": "Correo",
                    "palabras_clave": "Palabras clave", "activo": "Activo",
                    "fecha_registro": "Fecha de registro",
                })
                st.dataframe(datos, use_container_width=True, hide_index=True)
                st.caption("Se muestran hasta 1,000 registros. Este panel es solo de consulta.")
            else:
                st.info("Todavía no hay empresas registradas.")
        except KeyError:
            st.error("Falta configurar SUPABASE_ADMIN_KEY o SUPABASE_URL en Streamlit Secrets.")
        except Exception as error:
            st.error("No fue posible consultar los clientes. Revisa la clave administrativa y los permisos de Supabase.")
            st.caption(f"Tipo de error: {type(error).__name__}")

st.divider()
st.caption("TAPPAD Radar | Desarrollado por TAPPAD Consultoría")
