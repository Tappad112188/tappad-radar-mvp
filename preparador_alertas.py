"""Preparación de alertas por revisión de ComprasMX.

No envía mensajes ni modifica registros. Las oportunidades candidatas
requieren validación del plazo oficial antes de su notificación real.
"""
from control_notificaciones import separar_notificaciones
from motor_coincidencias import generar_coincidencias
from priorizador_alertas import priorizar_oportunidad
from formato_alertas import fecha_legible, frase_oportunidades
from validador_plazo_oficial import validar_envio_oportunidad


def preparar_alertas(proveedores, licitaciones, coberturas_por_cliente, historial, ahora=None):
    """Agrupa nuevas candidatas por proveedor y separa bloqueadas y reintentos."""
    coincidencias = generar_coincidencias(
        proveedores, licitaciones, coberturas_por_cliente,
        incluir_fuera_de_cobertura=False,
    )
    expedientes = {l["id"]: l for l in licitaciones}
    candidatas = []
    for coincidencia in coincidencias:
        licitacion = expedientes[coincidencia["licitacion_id"]]
        # Solo coincidencias con cobertura geográfica confirmada pueden notificarse.
        if coincidencia["categoria"] != "dentro_de_cobertura":
            continue
        prioridad = priorizar_oportunidad(coincidencia, licitacion, ahora=ahora)
        decision = validar_envio_oportunidad({**prioridad, "fecha_apertura": licitacion.get("fecha_apertura"), "estatus": licitacion.get("estatus")}, ahora=ahora)
        if not decision["autorizada"]:
            continue
        candidatas.append({
            "cliente_id": coincidencia["cliente_id"],
            "licitacion_id": coincidencia["licitacion_id"],
            "terminos": coincidencia["terminos"],
            "numero_procedimiento": licitacion.get("numero_procedimiento"),
            "nombre_procedimiento": licitacion.get("nombre_procedimiento"),
            "url_procedimiento": licitacion.get("url_procedimiento"),
            "fecha_apertura": licitacion.get("fecha_apertura"),
            "fuente": licitacion.get("fuente") or "ComprasMX",
            "fecha_publicacion": licitacion.get("fecha_publicacion"),
            "fecha_junta_aclaraciones": licitacion.get("fecha_junta_aclaraciones"),
            "fecha_fallo_programado": licitacion.get("fecha_fallo_programado"),
        })
    separadas = separar_notificaciones(candidatas, historial)
    por_proveedor = {}
    for item in separadas["nuevas"]:
        por_proveedor.setdefault(item["cliente_id"], []).append(item)
    return {
        "por_proveedor": por_proveedor,
        "candidatas": candidatas,
        "retenidas": separadas["retenidas"],
        "reintentos": separadas["reintentos"],
        "resumen": {
            "oportunidades_aptas": len(candidatas),
            "nuevas": len(separadas["nuevas"]),
            "duplicadas": len(separadas["retenidas"]),
            "reintentos": len(separadas["reintentos"]),
            "correos_simulados": len(por_proveedor),
        },
    }


def vista_previa_correo(empresa, oportunidades):
    """Devuelve asunto y cuerpo de texto sin realizar envío."""
    asunto = "TAPPAD Radar | Nuevas oportunidades para " + str(empresa)
    lineas = [
        "Hola, " + str(empresa) + ":",
        "",
        frase_oportunidades(len(oportunidades)),
        "Revisa los expedientes oficiales antes de participar:",
        "",
    ]
    for oportunidad in oportunidades:
        lineas.extend([
            "- " + str(oportunidad.get("numero_procedimiento") or "Sin número"),
            "  " + str(oportunidad.get("nombre_procedimiento") or "Sin título"),
            "  Coincidencia: " + ", ".join(oportunidad.get("terminos") or []),
            "  Fuente: " + str(oportunidad.get("fuente") or "ComprasMX"),
            "  Publicación: " + fecha_legible(oportunidad.get("fecha_publicacion")),
            "  Junta de aclaraciones: " + fecha_legible(oportunidad.get("fecha_junta_aclaraciones")),
            "  Presentación y apertura (fecha límite): " + fecha_legible(oportunidad.get("fecha_apertura")),
            "  Fallo programado: " + fecha_legible(oportunidad.get("fecha_fallo_programado")),
            "  Expediente: " + str(oportunidad.get("url_procedimiento") or "No disponible"),
            "",
        ])
    lineas.extend([
        "La clasificación es orientativa. Verifica el plazo oficial de presentación.",
        "TAPPAD Radar | TAPPAD Consultoría",
    ])
    return {"asunto": asunto, "cuerpo": "\n".join(lineas)}
