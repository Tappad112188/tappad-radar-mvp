"""Preparacion de evidencia auditable para conciliacion privada.

No persiste registros ni autoriza cambios de acceso. La evidencia procede
exclusivamente de una consulta remota vinculada a registros locales.
"""
from datetime import datetime, timezone
from verificar_pago_mercadopago_servidor import VerificacionRechazada

DECISIONES = frozenset({
    "pago_aprobado_sujeto_a_conciliacion",
    "revision_revocacion_pago",
    "revision_pago_no_aprobado",
    "revision_suscripcion_no_renovable",
    "revision_estado_pago_desconocido",
    "revision_estado_suscripcion_desconocido",
})


def preparar_evidencia_estado(auditoria, *, ahora=None):
    if not isinstance(auditoria, dict) or auditoria.get("modo") != "SOLO_LECTURA":
        raise VerificacionRechazada("auditoria_no_confiable")
    if auditoria.get("decision") not in DECISIONES:
        raise VerificacionRechazada("decision_no_admisible")
    pago = auditoria.get("pago_id_local")
    suscripcion = auditoria.get("suscripcion_id_local")
    if type(pago) is not int or pago <= 0 or type(suscripcion) is not int or suscripcion <= 0:
        raise VerificacionRechazada("identificadores_locales_invalidos")
    instante = ahora or datetime.now(timezone.utc)
    if instante.tzinfo is None or instante.utcoffset() is None:
        raise VerificacionRechazada("fecha_auditoria_invalida")
    return {
        "pago_id": pago,
        "suscripcion_id": suscripcion,
        "decision": auditoria["decision"],
        "verificado_en": instante.isoformat(),
        "origen": "consulta_directa_mercadopago",
        "requiere_conciliacion_privada": True,
        "aplica_cambios": False,
    }
