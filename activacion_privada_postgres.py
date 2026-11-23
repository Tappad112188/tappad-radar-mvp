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
from politica_renovacion_mercadopago import evaluar_inicio_ciclo


def activar_conexion_privada(pago_id, *, supabase_url, supabase_key,
                            mercadopago_token, postgres_dsn,
                            inicio=None, fin=None, permitir=False,
                            db_opener=urlopen, mp_opener=urlopen,
                            connect=None):
    """No escribe salvo autorización doble y verificacion remota satisfactoria.

    connect es una fabrica de conexiones DB-API, inyectable en pruebas.
    """
    if not permitir or os.environ.get("TAPPAD_HABILITAR_ACTIVACION_PRODUCCION") != "SI":
        return {"aplicacion": "bloqueada", "escrituras": 0}
    if not postgres_dsn:
        raise VerificacionRechazada("conexion_privada_ausente")
    if not os.environ.get("TAPPAD_MERCADOPAGO_SELLER_ID"):
        raise VerificacionRechazada("vendedor_esperado_no_configurado")
    if inicio is not None or fin is not None:
        raise VerificacionRechazada("periodo_no_puede_ser_proporcionado")
    # Verificacion remota ANTES de abrir transaccion.
    evidencia = verificar_pago_desde_supabase(
        pago_id, supabase_url=supabase_url, supabase_key=supabase_key,
        mercadopago_token=mercadopago_token,
        db_opener=db_opener, mp_opener=mp_opener)
    if str(evidencia["evidencia"].get("seller_id") or "") != os.environ["TAPPAD_MERCADOPAGO_SELLER_ID"]:
        raise VerificacionRechazada("vendedor_inesperado")
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
            # Solo un LOGIN dedicado puede asumir el rol privado NOLOGIN.
            cursor.execute("SET LOCAL ROLE tappad_activador_privado")
            cursor.execute("""SELECT current_user, session_user,
                (SELECT rolbypassrls FROM pg_roles WHERE rolname=current_user),
                (SELECT rolcanlogin AND NOT rolsuper AND NOT rolbypassrls FROM pg_roles WHERE rolname=session_user)""")
            identidad = cursor.fetchone()
            if (not identidad or identidad[0] != "tappad_activador_privado"
                    or identidad[1] != "tappad_login_activacion"
                    or identidad[2] is not False or identidad[3] is not True):
                raise VerificacionRechazada("identidad_activacion_no_autorizada")
            # Nunca ejecutar una función SECURITY DEFINER heredada: omite
            # la identidad restringida aunque SET LOCAL ROLE sea correcto.
            cursor.execute("""SELECT prosecdef FROM pg_proc WHERE oid =
                to_regprocedure('tappad_internal.tappad_aplicar_activacion_comercial(bigint,bigint,bigint,timestamptz,timestamptz,jsonb)')""")
            funcion = cursor.fetchone()
            if funcion is None or funcion[0] is not False:
                raise VerificacionRechazada("funcion_activacion_no_invoker")
            cursor.execute("SELECT id FROM public.suscripciones_tappad WHERE id=%s AND cliente_id=%s FOR UPDATE", (evidencia["suscripcion_id"], evidencia["cliente_id"]))
            if cursor.fetchone() is None:
                raise VerificacionRechazada("suscripcion_no_encontrada")
            cursor.execute("SELECT cliente_id FROM public.acceso_comercial_tappad WHERE cliente_id=%s FOR UPDATE", (evidencia["cliente_id"],))
            cursor.fetchone()
            cursor.execute(
                """SELECT p.fecha_pago, pl.periodicidad, CASE WHEN a.estado='prueba' THEN NULL ELSE a.vigente_hasta END, s.estado
                FROM public.pagos_tappad p
                JOIN public.suscripciones_tappad s ON s.id=p.suscripcion_id
                JOIN public.planes_tappad pl ON pl.id=s.plan_id
                LEFT JOIN public.acceso_comercial_tappad a ON a.cliente_id=s.cliente_id
                WHERE p.id=%s AND s.id=%s AND s.cliente_id=%s
                FOR UPDATE OF p""",
                (evidencia["pago_id"], evidencia["suscripcion_id"], evidencia["cliente_id"]))
            ciclo = cursor.fetchone()
            if not ciclo or ciclo[0] is None or ciclo[1] not in ("mensual", "anual"):
                raise VerificacionRechazada("ciclo_no_verificable")
            fecha_pago, periodicidad, vencimiento, estado_suscripcion = ciclo
            if fecha_pago.tzinfo is None:
                raise VerificacionRechazada("fecha_pago_sin_zona")
            ahora = datetime.now(timezone.utc)
            # Solo la decision 'aplicar' permite avanzar a la funcion SQL.
            # Los pagos anticipados y tardios quedan pendientes de conciliacion.
            decision, inicio = evaluar_inicio_ciclo(
                fecha_pago=fecha_pago, vencimiento=vencimiento, ahora=ahora)
            if decision == "revision_tardia" and estado_suscripcion == "prueba" and vencimiento is None:
                decision, inicio = "aplicar", fecha_pago
            if decision != "aplicar":
                motivos = {
                    "fecha_futura": "pago_fuera_de_ventana",
                    "revision_tardia": "pago_fuera_de_ventana",
                    "pendiente_anticipada": "renovacion_anticipada_pendiente",
                    "fecha_invalida": "fecha_pago_sin_zona",
                }
                raise VerificacionRechazada(motivos[decision])
            cursor.execute(
                "select %s::timestamptz + case %s when 'mensual' then interval '1 month' else interval '1 year' end",
                (inicio, periodicidad))
            fin_row = cursor.fetchone()
            if not fin_row or fin_row[0] <= ahora:
                raise VerificacionRechazada("periodo_expirado")
            fin = fin_row[0]
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
