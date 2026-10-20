"""Simulador administrativo, solo lectura. No modifica proveedores ni envía alertas."""
import pandas as pd
import streamlit as st
from motor_coincidencias import generar_coincidencias
from priorizador_alertas import priorizar_oportunidad


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
        for resultado in coincidencias:
            licitacion = expedientes[resultado["licitacion_id"]]
            prioridad = priorizar_oportunidad(resultado, licitacion)
            filas.append({
                "Estado para alerta": prioridad["categoria_alerta"].replace("_", " "),
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
        st.caption("Una candidata a revisión requiere verificar el plazo oficial en ComprasMX; no implica envío automático.")
    except Exception as error:
        st.error("No fue posible completar la simulación.")
        st.caption(f"Tipo de error: {type(error).__name__}")
