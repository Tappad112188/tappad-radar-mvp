"""Puente privado de activacion comercial, sin endpoint HTTP.

Flujo: lectura Supabase -> verificacion Mercado Pago -> transaccion PostgreSQL
con conexion dedicada -> funcion en esquema privado. APAGADO por defecto.

IMPORTANTE: la credencial PostgreSQL debe existir solo en un worker confiable,
NO en frontend, GitHub Actions, ni equipo de un cliente.
"""
import os
from datetime import datetime, timezone
from urllib.request import urlopen

from conexion_segura_mercadopago_supabase import verificar_pago_desde_supabase
from verificar_pago_mercadopago_servidor import VerificacionRechazada


def activar_conexion_privada(pago_id, *, supabase_url, supabase_key,
                            mercadopago_token, postgres_dsn,
                            inicio, fin, permitir=False,
                            db_opener=urlopen, mp_opener=urlopen,
                            connect=None):
    """No escribe salvo autorización doble y verificacion remota satisfactoria.

    connect es una fabrica de conexiones DB-API, inyectable en pruebas.
    """
    if not permitir or os.environ.get("TAPPAD_HABILITAR_ACTIVACION_PRODUCCION") != "SI":
        return {"aplicacion": "bloqueada", "escrituras": 0}
    if not postgres_dsn:
        raise VerificacionRechazada("conexion_privada_ausente")
    if not isinstance(inicio, datetime) or not isinstance(fin, datetime):
        raise VerificacionRechazada("periodo_invalido")
    if inicio.tzinfo is None or fin.tzinfo is None or inicio > datetime.now(timezone.utc) or fin <= datetime.now(timezone.utc) or fin <= inicio:
        raise VerificacionRechazada("periodo_invalido")
    # Verificacion remota ANTES de abrir transaccion.
    evidencia = verificar_pago_desde_supabase(
        pago_id, supabase_url=supabase_url, supabase_key=supabase_key,
        mercadopago_token=mercadopago_token,
        db_opener=db_opener, mp_opener=mp_opener)
    if connect is None:
        try:
            import psycopg
        except ImportError as exc:
            raise VerificacionRechazada("instalar_psycopg_en_worker_privado") from exc
        connect = psycopg.connect
    import json
    # El contexto DB-API revierte la transaccion ante cualquier excepcion.
    with connect(postgres_dsn) as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "select tappad_internal.tappad_aplicar_activacion_comercial("
                "%s,%s,%s,%s,%s,%s::jsonb)",
                (evidencia["cliente_id"], evidencia["suscripcion_id"],
                 evidencia["pago_id"], inicio, fin,
                 json.dumps(evidencia["evidencia"])))
            fila = cursor.fetchone()
            if fila is None or fila[0] is not True:
                raise VerificacionRechazada("activacion_rechazada_por_base")
    return {"aplicacion": "aplicada", "pago_id": pago_id}


if __name__ == "__main__":
    raise SystemExit("Modulo privado: no exponer como endpoint publico.")
