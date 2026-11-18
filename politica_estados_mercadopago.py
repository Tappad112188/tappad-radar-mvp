"""Clasificacion conservadora de eventos de cobro; no escribe ni revoca acceso.

Los estados deben proceder de consultas autenticadas a la API de Mercado Pago,
nunca del cuerpo de un webhook. La salida es una decision para reconciliacion
privada posterior, NO una orden de actualizar Supabase.
"""


def clasificar_estado_remoto(*, estado_pago, estado_suscripcion,
                            vinculo_verificado, vendedor_verificado):
    if vinculo_verificado is not True or vendedor_verificado is not True:
        return "bloquear_evidencia_insuficiente"
    if estado_pago in ("refunded", "charged_back"):
        return "revision_revocacion_pago"
    if estado_pago in ("cancelled", "rejected"):
        return "revision_pago_no_aprobado"
    if estado_pago != "approved":
        return "revision_estado_pago_desconocido"
    if estado_suscripcion == "authorized":
        return "pago_aprobado_sujeto_a_conciliacion"
    if estado_suscripcion in ("cancelled", "paused"):
        return "revision_suscripcion_no_renovable"
    return "revision_estado_suscripcion_desconocido"
