"""Ejecutor privado de reversiones. Apagado por defecto; no expone HTTP.

Consulta filas desde PostgreSQL bajo bloqueo, comprueba estado remoto mediante
API autenticada de Mercado Pago y aplica SQL en la misma transaccion.
No recibe evidencia, referencias ni estados del navegador/webhook.
"""
import json
import os
from auditar_estados_remotos_mercadopago import auditar_estado_remoto
from verificar_pago_mercadopago_servidor import VerificacionRechazada


def conciliar_reversion_privada(pago_id, *, postgres_dsn, token, seller_id,
                               permitir=False, connect=None,
                               auditar=auditar_estado_remoto):
    if not permitir or os.getenv("TAPPAD_HABILITAR_REVERSION_PRODUCCION") != "SI":
        return {"estado": "bloqueado", "escrituras": 0}
    if type(pago_id) is not int or pago_id <= 0:
        raise VerificacionRechazada("pago_id_invalido")
    if not postgres_dsn or not token or not seller_id:
        raise VerificacionRechazada("credenciales_privadas_incompletas")
    if connect is None:
        try:
            import psycopg
        except ImportError as exc:
            raise VerificacionRechazada("psycopg_requerido") from exc
        connect = psycopg.connect
    with connect(postgres_dsn) as conn:
        with conn.cursor() as cursor:
            # Mismo orden de bloqueo que el SQL de conciliacion: suscripcion, pago.
            # La consulta inicial no bloquea: el ID se obtiene exclusivamente del
            # registro local, nunca de un webhook sin verificar.
            cursor.execute(
                "SELECT suscripcion_id FROM public.pagos_tappad WHERE id=%s",
                (pago_id,))
            row = cursor.fetchone()
            if row is None:
                raise VerificacionRechazada("pago_no_encontrado")
            sid_local = row[0]
            cursor.execute(
                """SELECT id, proveedor_cobro, referencia_externa
                   FROM public.suscripciones_tappad WHERE id=%s FOR UPDATE""",
                (sid_local,))
            subrow = cursor.fetchone()
            cursor.execute(
                """SELECT id, suscripcion_id, proveedor_cobro, referencia_externa
                   FROM public.pagos_tappad WHERE id=%s AND suscripcion_id=%s
                   FOR UPDATE""",
                (pago_id, sid_local))
            payrow = cursor.fetchone()
            if subrow is None or payrow is None:
                raise VerificacionRechazada("relacion_local_invalida")
            sub = dict(zip(("id", "proveedor_cobro", "referencia_externa"), subrow))
            pay = dict(zip(("id", "suscripcion_id", "proveedor_cobro",
                            "referencia_externa"), payrow))
            resultado = auditar(sub, pay, token=token, seller_id_esperado=seller_id)
            if resultado.get("decision") != "revision_revocacion_pago":
                return {"estado": "sin_reversion_confirmada", "escrituras": 0}
            estado = resultado.get("estado_pago_remoto")
            evidencia = resultado.get("evidencia")
            if estado not in ("refunded", "charged_back") or not isinstance(evidencia, dict):
                raise VerificacionRechazada("evidencia_de_reversion_incompleta")
            if (evidencia.get("seller_id") != str(seller_id)
                or evidencia.get("payment_id") != pay["referencia_externa"]
                or evidencia.get("preapproval_id") != sub["referencia_externa"]):
                raise VerificacionRechazada("evidencia_no_coincide")
            cursor.execute(
                """SELECT tappad_internal.conciliar_reversion_pago(
                   %s,%s,%s,%s::jsonb)""",
                (pago_id, sid_local, estado, json.dumps(evidencia)))
            applied = cursor.fetchone()
            if applied is None or type(applied[0]) is not bool:
                raise VerificacionRechazada("resultado_sql_invalido")
            return {"estado": "aplicada" if applied[0] else "ya_conciliada",
                    "escrituras": 1 if applied[0] else 0}


if __name__ == "__main__":
    raise SystemExit("Solo modulo privado; no ejecutar con credenciales de produccion.")
