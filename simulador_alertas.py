"""Simulador administrativo, solo lectura. No modifica proveedores ni envía alertas."""
import pandas as pd
import streamlit as st
from motor_coincidencias import generar_coincidencias
from priorizador_alertas import priorizar_oportunidad
from preparador_alertas import vista_previa_correo
from plantilla_correo_html import construir_correo_html
from validador_plazo_oficial import validar_envio_oportunidad


def mostrar_simulador(conectar_admin, estados):
    st.divider()
    st.subheader("Simulador de alertas")
    st.caption("Prueba palabras clave y cobertura estatal sin modificar proveedores ni enviar correos.")
    with st.form("simulador_alertas_form"):
        palabras = st.text_area("Palabras clave de prueba (separadas por comas)", value="limpieza, mantenimiento")
        cobertura = st.selectbox("Estado de cobertura simulado", estados)
        ejecutar = st.form_submit_button("Simular oportunidades")
    if not ejecutar:
        return
    if not palabras.strip() or not any(p.strip() for p in palabras.replace(";", ",").split(",")):
        st.warning("Escribe al menos una palabra clave.")
        return
    try:
        db = conectar_admin()
        licitaciones = db.table("licitaciones").select(
            "id,numero_procedimiento,nombre_procedimiento,descripcion,tipo_contratacion,"
            "entidad_federativa,fecha_apertura,estatus,url_procedimiento"
        ).order("id").limit(1000).execute().data or []
        proveedor = {"id": -1, "activo": True, "palabras_clave": palabras}
        coincidencias = generar_coincidencias(
            [proveedor], licitaciones, {-1: [{"estado": cobertura}]},
            incluir_fuera_de_cobertura=True,
        )
        expedientes = {item["id"]: item for item in licitaciones}
        filas = []
        candidatas_correo = []
        autorizadas_correo = []
        for resultado in coincidencias:
            licitacion = expedientes[resultado["licitacion_id"]]
            prioridad = priorizar_oportunidad(resultado, licitacion)
            decision_plazo = validar_envio_oportunidad({**prioridad, "fecha_apertura": licitacion.get("fecha_apertura"), "estatus": licitacion.get("estatus")})
            if prioridad["categoria_alerta"] == "candidata_revision":
                oportunidad_correo = {
                    "numero_procedimiento": licitacion.get("numero_procedimiento"),
                    "nombre_procedimiento": licitacion.get("nombre_procedimiento"),
                    "terminos": resultado["terminos"],
                    "fecha_apertura": licitacion.get("fecha_apertura"),
                    "url_procedimiento": licitacion.get("url_procedimiento"),
                }
                candidatas_correo.append(oportunidad_correo)
                if decision_plazo["autorizada"]:
                    autorizadas_correo.append(oportunidad_correo)
            filas.append({
                "Estado para alerta": prioridad["categoria_alerta"].replace("_", " "),
                "Plazo oficial": "Autorizado" if decision_plazo["autorizada"] else "Sin autorización",
                "Motivo de bloqueo": decision_plazo["motivo"],
                "Cobertura": resultado["categoria"].replace("_", " "),
                "Vigencia": prioridad["vigencia"].replace("_", " "),
                "Términos": ", ".join(resultado["terminos"]),
                "Procedimiento": licitacion.get("numero_procedimiento"),
                "Nombre": licitacion.get("nombre_procedimiento"),
                "Entidad": licitacion.get("entidad_federativa"),
                "Expediente": licitacion.get("url_procedimiento"),
            })
        st.metric("Coincidencias de la simulación", len(filas))
        st.caption(f"Se evaluaron {len(licitaciones)} expedientes. Ninguna alerta se envió.")
        if filas:
            df = pd.DataFrame(filas)
            resumen = df["Estado para alerta"].value_counts().rename_axis("Clasificación").reset_index(name="Cantidad")
            st.dataframe(resumen, hide_index=True, use_container_width=True)
            st.dataframe(df, hide_index=True, use_container_width=True,
                column_config={"Expediente": st.column_config.LinkColumn("Expediente", display_text="Abrir")})
            st.download_button("Descargar simulación CSV", data=df.to_csv(index=False).encode("utf-8-sig"),
                file_name="tappad_simulacion_alertas.csv", mime="text/csv")
        else:
            st.info("No hay coincidencias con los criterios simulados.")
        st.subheader("Control de plazo de presentación")
        st.metric("Candidatas con apertura futura", len(candidatas_correo))
        st.metric("Aptas según fecha y estatus", len(autorizadas_correo))
        st.caption("La fecha de apertura registrada se utiliza como límite de presentación. El resultado es una simulación, no autoriza un envío real.")
        if len(autorizadas_correo) < len(candidatas_correo):
            st.warning("Algunas candidatas están bloqueadas por fecha o estatus.")
        st.subheader("Vista previa del correo simulado")
        st.caption("Demostración del diseño. No utiliza direcciones reales ni envía mensajes.")
        if candidatas_correo:
            correo = vista_previa_correo("Empresa de ejemplo", candidatas_correo)
            st.text_input("Asunto simulado", value=correo["asunto"], disabled=True, key="simulador_asunto_correo")
            st.text_area("Contenido del correo simulado", value=correo["cuerpo"], height=330, disabled=True, key="simulador_cuerpo_correo")
            st.markdown("**Diseño HTML del correo**")
            st.components.v1.html(
                construir_correo_html("Empresa de ejemplo", candidatas_correo),
                height=min(1000, 460 + 270 * len(candidatas_correo)),
                scrolling=True,
            )
            st.caption(f"Vista previa hipotética de {len(candidatas_correo)} oportunidades. Aptas según fecha y estatus: {len(autorizadas_correo)}. Ningún correo fue enviado.")
        else:
            st.info("Con estos criterios no hay candidatas para preparar un correo. Puedes probar otras palabras clave o cobertura.")
        st.caption("Una candidata a revisión requiere verificar el plazo oficial en ComprasMX; no implica envío automático.")
    except Exception as error:
        st.error("No fue posible completar la simulación.")
        st.caption(f"Tipo de error: {type(error).__name__}")
