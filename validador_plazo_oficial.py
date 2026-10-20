"""Control de autorización de alertas basado en plazo oficial verificado.

La fecha de apertura estimada no equivale a una confirmación de plazo.
Este módulo no consulta portales ni envía mensajes.
"""
from datetime import datetime, timezone


def validar_envio_oportunidad(oportunidad, verificacion=None, ahora=None):
    """Devuelve una decisión conservadora, nunca presume vigencia.

    verificacion debe incluir:
      estado: 'confirmado_abierto' | 'cerrado' | 'sin_verificar'
      fuente_url: URL HTTPS del expediente o documento oficial
      fecha_limite: ISO-8601 con zona horaria explícita
      verificado_en: ISO-8601 con zona horaria explícita
    """
    if oportunidad.get("categoria_alerta") != "candidata_revision":
        return {"autorizada": False, "motivo": "La oportunidad no es candidata a revisión"}
    if not verificacion or verificacion.get("estado") != "confirmado_abierto":
        return {"autorizada": False, "motivo": "Falta confirmar el plazo oficial de presentación"}
    fuente = str(verificacion.get("fuente_url") or "")
    if not fuente.startswith("https://"):
        return {"autorizada": False, "motivo": "Falta enlace HTTPS a la fuente oficial"}
    try:
        limite = datetime.fromisoformat(str(verificacion["fecha_limite"]).replace("Z", "+00:00"))
        revisado = datetime.fromisoformat(str(verificacion["verificado_en"]).replace("Z", "+00:00"))
    except (ValueError, TypeError, KeyError):
        return {"autorizada": False, "motivo": "Fechas de verificación inválidas"}
    if limite.tzinfo is None or revisado.tzinfo is None:
        return {"autorizada": False, "motivo": "Las fechas deben incluir zona horaria"}
    ahora = ahora or datetime.now(timezone.utc)
    if ahora.tzinfo is None:
        return {"autorizada": False, "motivo": "La hora de evaluación debe incluir zona horaria"}
    if revisado > ahora or (ahora - revisado).total_seconds() > 6 * 3600:
        return {"autorizada": False, "motivo": "La verificación oficial requiere actualización"}
    if limite <= ahora:
        return {"autorizada": False, "motivo": "El plazo oficial ya terminó"}
    return {"autorizada": True, "motivo": "Plazo verificado; sujeto a controles de envío y duplicados"}
