"""Worker privado de activacion: sin endpoint publico y apagado por defecto.

Audita pagos productivos y solo activa con doble autorizacion explicita.
No acepta cliente, suscripcion, fechas o evidencia del navegador.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from conciliador_pagos_pendientes_lectura import pendientes
from conexion_segura_mercadopago_supabase import verificar_pago_desde_supabase
from activacion_privada_postgres import activar_conexion_privada
from verificar_pago_mercadopago_servidor import VerificacionRechazada


def ejecutar(*, supabase_url, supabase_key, mercadopago_token,
            postgres_dsn=None, activar=False, confirmacion=None,
            listar=pendientes, verificar=verificar_pago_desde_supabase,
            aplicar=activar_conexion_privada):
    autorizado = (activar and confirmacion == "ACTIVAR" and
                  os.getenv("TAPPAD_HABILITAR_ACTIVACION_PRODUCCION") == "SI")
    if activar and not autorizado:
        raise VerificacionRechazada("activacion_no_autorizada")
    if autorizado and (not postgres_dsn or not os.getenv("TAPPAD_MERCADOPAGO_SELLER_ID")):
        raise VerificacionRechazada("credenciales_privadas_incompletas")
    ids = listar(supabase_url=supabase_url, supabase_key=supabase_key)
    if len(ids) != len(set(ids)) or any(type(i) is not int or i <= 0 for i in ids):
        raise VerificacionRechazada("lote_de_pagos_invalido")
    resultados=[]
    for pago_id in ids:
        try:
            evidencia=verificar(pago_id,supabase_url=supabase_url,
                supabase_key=supabase_key,mercadopago_token=mercadopago_token)
            vendedor=str(evidencia["evidencia"].get("seller_id") or "")
            esperado=os.getenv("TAPPAD_MERCADOPAGO_SELLER_ID")
            if not esperado or vendedor != esperado:
                raise VerificacionRechazada("vendedor_no_verificado")
            if autorizado:
                resultado=aplicar(pago_id,supabase_url=supabase_url,
                    supabase_key=supabase_key,mercadopago_token=mercadopago_token,
                    postgres_dsn=postgres_dsn,permitir=True)
                estado=resultado["aplicacion"]
            else:
                estado="verificado_sin_activar"
            resultados.append({"pago_id":pago_id,"estado":estado})
        except (VerificacionRechazada,KeyError,ValueError) as exc:
            resultados.append({"pago_id":pago_id,"estado":"bloqueado",
                               "motivo":str(exc) if isinstance(exc,VerificacionRechazada) else "evidencia_invalida"})
        # Fallos de red/BD inesperados se propagan: no continuar a ciegas.
    return {"modo":"ACTIVACION_PRIVADA" if autorizado else "SOLO_LECTURA",
            "fecha":datetime.now(timezone.utc).isoformat(),
            "pagos_revisados":len(ids),"resultados":resultados}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--activar",action="store_true")
    parser.add_argument("--confirmar",default="")
    args=parser.parse_args()
    variables=("TAPPAD_SUPABASE_URL","TAPPAD_SUPABASE_SERVICE_ROLE_KEY",
               "TAPPAD_MERCADOPAGO_PROD_ACCESS_TOKEN")
    faltantes=[v for v in variables if not os.getenv(v)]
    if faltantes:
        raise SystemExit("Faltan secretos: "+", ".join(faltantes))
    resultado=ejecutar(supabase_url=os.environ[variables[0]],
        supabase_key=os.environ[variables[1]],
        mercadopago_token=os.environ[variables[2]],
        postgres_dsn=os.getenv("TAPPAD_POSTGRES_DSN"),
        activar=args.activar,confirmacion=args.confirmar)
    print(json.dumps(resultado,ensure_ascii=False))
    if any(x["estado"]=="bloqueado" for x in resultado["resultados"]):
        return 2
    return 0


if __name__=="__main__":
    sys.exit(main())
