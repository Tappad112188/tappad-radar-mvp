"""Preparación de alertas por revisión de ComprasMX.

No envía mensajes ni modifica registros. Las oportunidades candidatas
requieren validación del plazo oficial antes de su notificación real.
"""
from control_notificaciones import separar_notificaciones
from motor_coincidencias import generar_coincidencias
from priorizador_alertas import priorizar_oportunidad


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
        prioridad = priorizar_oportunidad(coincidencia, licitacion, ahora=ahora)
        if prioridad["categoria_alerta"] != "candidata_revision":
            continue
        candidatas.append({
            "cliente_id": coincidencia["cliente_id"],
            "licitacion_id": coincidencia["licitacion_id"],
            "terminos": coincidencia["terminos"],
            "numero_procedimiento": licitacion.get("numero_procedimiento"),
            "nombre_procedimiento": licitacion.get("nombre_procedimiento"),
            "url_procedimiento": licitacion.get("url_procedimiento"),
            "fecha_apertura": licitacion.get("fecha_apertura"),
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
    }


def vista_previa_correo(empresa, oportunidades):
    """Devuelve asunto y cuerpo de texto sin realizar envío."""
    asunto = "TAPPAD Radar | Nuevas oportunidades para " + str(empresa)
    lineas = [
        "Hola, " + str(empresa) + ":",
        "",
        "TAPPAD Radar identificó oportunidades potencialmente relevantes para tu empresa.",
        "Revisa los expedientes oficiales antes de participar:",
        "",
    ]
    for oportunidad in oportunidades:
        lineas.extend([
            "- " + str(oportunidad.get("numero_procedimiento") or "Sin número"),
            "  " + str(oportunidad.get("nombre_procedimiento") or "Sin título"),
            "  Coincidencia: " + ", ".join(oportunidad.get("terminos") or []),
            "  Apertura estimada: " + str(oportunidad.get("fecha_apertura") or "No disponible"),
            "  Expediente: " + str(oportunidad.get("url_procedimiento") or "No disponible"),
            "",
        ])
    lineas.extend([
        "La clasificación es orientativa. Verifica el plazo oficial de presentación.",
        "TAPPAD Radar | TAPPAD Consultoría",
    ])
    return {"asunto": asunto, "cuerpo": "\n".join(lineas)}
