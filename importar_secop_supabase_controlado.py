"""Importacion controlada de lote SECOP existente. Simulacion por defecto.
Ejecutar: py importar_secop_supabase_controlado.py
Escribir: py importar_secop_supabase_controlado.py --importar
No envia correos ni inicia Chromium.
"""
import argparse, json, os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

LOTE=Path(__file__).resolve().parent/"documentos_secop_lote"/"secop_importacion_pendiente_revision.json"
ROOT=LOTE.parent.parent
EXTRACCION=ROOT/"secop_hoy_vigentes.json"
AUDITORIA=LOTE.parent/"auditoria_supabase_secop.json"

CAMPOS={"uuid_procedimiento","fuente","numero_procedimiento","cod_expediente",
"nombre_procedimiento","descripcion","entidad_federativa","estatus",
"fecha_publicacion","fecha_junta_aclaraciones","fecha_apertura",
"fecha_fallo_programado","url_procedimiento","documentos_disponibles",
"url_bases","url_convocatoria","documentos_bases_verificados",
"documentos_convocatorias_verificados"}
def api(metodo,params=None,datos=None):
    clave=os.getenv("SUPABASE_ADMIN_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    base=os.getenv("SUPABASE_URL")
    if not clave or not base: raise SystemExit("Faltan variables Supabase")
    url=base.rstrip("/")+"/rest/v1/licitaciones"+("?" + urlencode(params) if params else "")
    headers={"apikey":clave,"Authorization":"Bearer "+clave,"Content-Type":"application/json"}
    if datos is not None: headers["Prefer"]="return=representation"
    solicitud=Request(url,headers=headers,method=metodo,data=json.dumps(datos).encode() if datos is not None else None)
    with urlopen(solicitud,timeout=40) as respuesta:
        return json.load(respuesta)
def identificador(codigo):
    valor=str(codigo or "").strip().casefold()
    if not valor or valor in {"none", "null"}:
        raise SystemExit("Codigo SECOP vacio")
    return "secop-coahuila:"+valor

def validar_lote(registros):
    if not isinstance(registros,list) or not registros:
        raise SystemExit("Lote vacio o invalido: sin cambios")
    ids=[]
    for r in registros:
        if not isinstance(r,dict):
            raise SystemExit("Registro SECOP invalido")
        uid=identificador(r.get("cod_expediente"))
        if r.get("uuid_procedimiento")!=uid:
            raise SystemExit("UUID no corresponde al codigo SECOP: "+uid)
        if r.get("fuente")!="SECOP Coahuila" or not r.get("nombre_procedimiento"):
            raise SystemExit("Ficha SECOP incompleta: "+uid)
        if str(r.get("estatus") or "").strip().casefold()!="vigente":
            raise SystemExit("Estatus SECOP no vigente: "+uid)
        ids.append(uid)
    if len(ids)!=len(set(ids)):
        raise SystemExit("Identificadores SECOP duplicados")
    return ids

def validar_autorizacion(lote,ids):
    """Falla cerrada antes de cualquier escritura, incluso en ejecucion directa."""
    from datetime import datetime, timezone
    from zoneinfo import ZoneInfo
    hoy=datetime.now(ZoneInfo("America/Monterrey")).date().isoformat()
    if lote.get("estado")!="PENDIENTE_VALIDACION_OFICIAL_NO_IMPORTAR_AUTOMATICAMENTE":
        raise SystemExit("IMPORTACION BLOQUEADA: estado del lote no auditado")
    if not EXTRACCION.is_file() or not AUDITORIA.is_file():
        raise SystemExit("IMPORTACION BLOQUEADA: falta extraccion o auditoria")
    fuente=json.loads(EXTRACCION.read_text(encoding="utf-8-sig"))
    auditoria=json.loads(AUDITORIA.read_text(encoding="utf-8-sig"))
    if (fuente.get("fecha_consulta")!=hoy or fuente.get("filtros_aplicados") is not True
        or fuente.get("error") or fuente.get("errores") or fuente.get("coincide_total") is not True):
        raise SystemExit("IMPORTACION BLOQUEADA: extraccion diaria no validada")
    origen=fuente.get("registros")
    if not isinstance(origen,list) or not origen:
        raise SystemExit("IMPORTACION BLOQUEADA: extraccion vacia")
    codigos=[]
    for r in origen:
        if not isinstance(r,dict) or r.get("fecha_publicacion")!=hoy or str(r.get("estatus") or "").strip().casefold()!="vigente":
            raise SystemExit("IMPORTACION BLOQUEADA: extraccion fuera de fecha o estatus")
        codigos.append(identificador(r.get("codigo")))
    if len(codigos)!=len(set(codigos)) or set(codigos)!=set(ids):
        raise SystemExit("IMPORTACION BLOQUEADA: lote y extraccion no coinciden")
    if any(str(r.get("fecha_publicacion") or "")[:10]!=hoy for r in lote["registros"]):
        raise SystemExit("IMPORTACION BLOQUEADA: publicacion del lote fuera de fecha")
    nuevos=auditoria.get("nuevos")
    existentes=auditoria.get("existentes")
    if (auditoria.get("fecha_consulta")!=hoy
        or auditoria.get("consulta_supabase")!="realizada"
        or auditoria.get("estado")!="SOLO_LECTURA"
        or auditoria.get("importacion_habilitada") is not False
        or auditoria.get("notificaciones_habilitadas") is not False
        or type(auditoria.get("total")) is not int or auditoria["total"]!=len(ids)
        or not isinstance(nuevos,list) or not isinstance(existentes,list)
        or len(nuevos)+len(existentes)!=len(ids)
        or len(set(nuevos+existentes))!=len(ids)
        or set(nuevos+existentes)!=set(ids)):
        raise SystemExit("IMPORTACION BLOQUEADA: auditoria inconsistente")
    # No aceptar un reporte anterior a las evidencias que certifica.
    if AUDITORIA.stat().st_mtime+0.001 < max(LOTE.stat().st_mtime,EXTRACCION.stat().st_mtime):
        raise SystemExit("IMPORTACION BLOQUEADA: auditoria anterior al lote o extraccion")
    if AUDITORIA.stat().st_mtime > datetime.now(timezone.utc).timestamp()+60:
        raise SystemExit("IMPORTACION BLOQUEADA: fecha de auditoria futura")
    return set(nuevos)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--importar",action="store_true")
    p.add_argument("--registrar_pendientes",action="store_true",help="Permite registrar expedientes pendientes, sin habilitar alertas")
    args=p.parse_args()
    if not LOTE.exists():raise SystemExit("Falta lote SECOP local")
    lote=json.loads(LOTE.read_text(encoding="utf-8-sig"))
    # El preparador marca explicitamente los lotes sin validar: nunca importarlos.
    # La simulacion sigue permitida para diagnostico, sin escritura.
    estados_permitidos = {"VALIDADO_PARA_IMPORTACION"}
    if args.registrar_pendientes:
        estados_permitidos.add("PENDIENTE_VALIDACION_OFICIAL_NO_IMPORTAR_AUTOMATICAMENTE")
    if args.importar and lote.get("estado") not in estados_permitidos:
        raise SystemExit("IMPORTACION BLOQUEADA: lote SECOP sin validacion oficial. No se escribio en Supabase.")
    if args.importar and not args.registrar_pendientes:
        raise SystemExit("IMPORTACION BLOQUEADA: requiere --registrar_pendientes y auditoria vigente")
    registros=lote.get("registros") or []
    ids=validar_lote(registros)
    nuevos=[]
    autorizados=None
    if args.importar:
        autorizados=validar_autorizacion(lote,ids)
    for original in registros:
        uid=original["uuid_procedimiento"]
        encontrado=api("GET",{"select":"id,uuid_procedimiento","uuid_procedimiento":"eq."+uid})
        if encontrado:
            print("EXISTENTE (sin actualizar):",uid)
            continue
        registro={k:v for k,v in original.items() if k in CAMPOS and v is not None}
        registro["validacion_calendario"]="pendiente"
        # Las fechas candidatas de PDF no son oficiales hasta su validacion.
        # Se conservan en las fichas locales para revision, no en campos publicables.
        if lote.get("estado") == "PENDIENTE_VALIDACION_OFICIAL_NO_IMPORTAR_AUTOMATICAMENTE":
            for campo in ("fecha_junta_aclaraciones", "fecha_apertura", "fecha_fallo_programado"):
                registro.pop(campo, None)
        if args.importar and uid not in autorizados:
            raise SystemExit("IMPORTACION BLOQUEADA: registro nuevo no autorizado por auditoria: "+uid)
        nuevos.append(registro)
        print("NUEVO:",uid,"| apertura:",registro.get("fecha_apertura") or "no identificada")
    print("RESUMEN: lote",len(registros),"| nuevos",len(nuevos),"| existentes",len(registros)-len(nuevos))
    if not args.importar:
        print("SIMULACION: sin escrituras ni correos. Para importar usar --importar")
        return
    for registro in nuevos:
        uid=registro["uuid_procedimiento"]
        # La restriccion UNIQUE protege ante ejecuciones repetidas.
        clave=os.getenv("SUPABASE_ADMIN_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        base=os.environ["SUPABASE_URL"].rstrip("/")
        url=base+"/rest/v1/licitaciones?on_conflict=uuid_procedimiento"
        req=Request(url,headers={"apikey":clave,"Authorization":"Bearer "+clave,"Content-Type":"application/json","Prefer":"resolution=ignore-duplicates,return=minimal"},method="POST",data=json.dumps([registro]).encode())
        with urlopen(req,timeout=40) as respuesta:
            if respuesta.status not in (200,201,204):raise RuntimeError("Insercion no confirmada: "+uid)
        confirmado=api("GET",{"select":"id","uuid_procedimiento":"eq."+uid})
        if len(confirmado)!=1:raise RuntimeError("No se confirmo insercion: "+uid)
        print("CONFIRMADO:",uid)
    print("IMPORTACION TERMINADA. No se enviaron correos.")
if __name__=="__main__":main()
