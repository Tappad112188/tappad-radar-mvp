"""Conciliación piloto: descubrimiento remoto, registro idempotente y activación privada."""
import os
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import urlencode, quote
from verificar_pago_mercadopago_servidor import _get_json, verificar_pago_servidor, VerificacionRechazada
from conexion_segura_mercadopago_supabase import _filas
from activacion_privada_postgres import activar_conexion_privada

def conciliar(*, aplicar=False):
    url=os.environ["TAPPAD_SUPABASE_URL"]
    key=os.environ["TAPPAD_SUPABASE_SERVICE_ROLE_KEY"]
    token=os.environ["TAPPAD_MERCADOPAGO_PROD_ACCESS_TOKEN"]
    seller=os.environ["TAPPAD_MERCADOPAGO_SELLER_ID"]
    sub=_filas(url,key,"suscripciones_tappad",{"select":"*","id":"eq.5","cliente_id":"eq.4","plan_id":"eq.1","proveedor_cobro":"eq.mercadopago_produccion"})
    sid=sub["referencia_externa"]
    if sid!="dbc554730f1141a48cf73881a4e9eb96":
        raise VerificacionRechazada("referencia_piloto_invalida")
    pre=_get_json("/preapproval/"+quote(sid,safe=""),token)
    if str(pre.get("collector_id"))!=seller:
        raise VerificacionRechazada("vendedor_invalido")
    if pre.get("status")!="authorized":
        return {"estado":"esperando_autorizacion","pagos":0}
    rows=_get_json("/authorized_payments/search?"+urlencode({"preapproval_id":sid,"limit":100,"offset":0}),token)["results"]
    if not isinstance(rows,list) or len(rows)>=100:
        raise VerificacionRechazada("paginacion_requiere_revision")
    candidatos=[]
    for row in rows:
        if row.get("status") not in ("processed","approved"):
            continue
        pid=str((row.get("payment") or {}).get("id") or "")
        if not pid.isascii() or not pid.isdigit() or str(row.get("preapproval_id"))!=sid:
            raise VerificacionRechazada("vinculo_invalido")
        remote=_get_json("/v1/payments/"+pid,token)
        if remote.get("status")!="approved":
            continue
        fecha=datetime.fromisoformat(remote["date_approved"].replace("Z","+00:00"))
        if fecha.tzinfo is None or fecha>datetime.now(timezone.utc):
            raise VerificacionRechazada("fecha_invalida")
        pago={"referencia_externa":pid,"suscripcion_id":5,"monto_mxn":449,"estado":"pagado","proveedor_cobro":"mercadopago_produccion","fecha_pago":fecha.isoformat()}
        ev=verificar_pago_servidor(sub,pago,importe_esperado=449,token=token)
        if ev["seller_id"]!=seller:
            raise VerificacionRechazada("vendedor_invalido")
        candidatos.append((fecha,pid))
    if not aplicar:
        return {"estado":"solo_lectura","pagos_verificados":len(candidatos)}
    if os.environ.get("TAPPAD_HABILITAR_CONCILIACION_PILOTO")!="SI":
        raise VerificacionRechazada("conciliacion_bloqueada")
    import psycopg
    dsn=os.environ["TAPPAD_POSTGRES_DSN"]
    for fecha,pid in sorted(set(candidatos)):
        with psycopg.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SET LOCAL ROLE tappad_activador_privado")
                cur.execute("SELECT session_user,current_user")
                if cur.fetchone()!=("tappad_login_activacion","tappad_activador_privado"):
                    raise VerificacionRechazada("identidad_invalida")
                cur.execute("SELECT tappad_internal.registrar_pago_piloto(%s,%s)",(pid,fecha))
                pago_id=cur.fetchone()[0]
                cur.execute("SELECT 1 FROM public.activaciones_comerciales_tappad WHERE pago_id=%s AND estado='aplicada'",(pago_id,))
                if cur.fetchone():
                    continue
        resultado=activar_conexion_privada(pago_id,supabase_url=url,supabase_key=key,mercadopago_token=token,postgres_dsn=dsn,permitir=True)
        if resultado.get("aplicacion")!="aplicada":
            raise VerificacionRechazada("activacion_no_aplicada")
    return {"estado":"conciliado","pagos_verificados":len(candidatos)}

if __name__=="__main__":
    import json,sys
    try:
        print(json.dumps(conciliar(aplicar="--aplicar" in sys.argv)))
    except Exception as exc:
        print("Conciliacion detenida:",type(exc).__name__)
        raise SystemExit(1)
