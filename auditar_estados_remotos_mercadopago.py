"""Auditor remoto de estados de Mercado Pago: solo lectura.

Consulta proveedor con token servidor y vincula IDs a registros locales
cargados por backend. Nunca usa payload de webhook como fuente de verdad.
No modifica Supabase, no cobra ni revoca acceso.
"""
from urllib.request import urlopen
from urllib.parse import quote
from verificar_pago_mercadopago_servidor import _get_json, VerificacionRechazada
from politica_estados_mercadopago import clasificar_estado_remoto


def auditar_estado_remoto(suscripcion, pago_local, *, token, seller_id_esperado,
                         opener=urlopen):
    if not isinstance(suscripcion, dict) or not isinstance(pago_local, dict):
        raise VerificacionRechazada("registros_invalidos")
    if (suscripcion.get("proveedor_cobro") != "mercadopago_produccion"
        or pago_local.get("proveedor_cobro") != "mercadopago_produccion"
        or str(pago_local.get("suscripcion_id")) != str(suscripcion.get("id"))
        or not seller_id_esperado):
        raise VerificacionRechazada("relacion_comercial_invalida")
    sid = str(suscripcion.get("referencia_externa") or "")
    pid = str(pago_local.get("referencia_externa") or "")
    if not sid or not pid or any(
        not x.isascii() or not all(c.isalnum() or c in "-_" for c in x)
        for x in (sid, pid)
    ):
        raise VerificacionRechazada("identificadores_invalidos")
    vendedor = _get_json("/users/me", token, opener=opener)
    if (str(vendedor.get("id") or "") != str(seller_id_esperado)
        or vendedor.get("site_id") != "MLM"
        or "test_user" in (vendedor.get("tags") or [])):
        raise VerificacionRechazada("vendedor_no_verificado")
    sub = _get_json("/preapproval/" + quote(sid, safe=""), token, opener=opener)
    pago = _get_json("/v1/payments/" + quote(pid, safe=""), token, opener=opener)
    if str(sub.get("id") or "") != sid or str(pago.get("id") or "") != pid:
        raise VerificacionRechazada("identidad_remota_inconsistente")
    if str(pago.get("collector_id") or "") != str(seller_id_esperado):
        raise VerificacionRechazada("vendedor_pago_inconsistente")
    if str(pago.get("preapproval_id") or "") != sid:
        # Un pago sin preapproval_id directo necesita la consulta adicional
        # de authorized_payments. No asumir vinculo por coincidencia de IDs.
        raise VerificacionRechazada("vinculo_pago_no_verificable")
    decision = clasificar_estado_remoto(
        estado_pago=pago.get("status"), estado_suscripcion=sub.get("status"),
        vinculo_verificado=True, vendedor_verificado=True)
    return {"pago_id_local": pago_local.get("id"),
            "suscripcion_id_local": suscripcion.get("id"),
            "decision": decision, "modo": "SOLO_LECTURA"}
