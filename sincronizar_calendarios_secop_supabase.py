"""Sincroniza calendarios SECOP validados preliminarmente con registros existentes.
Por defecto solo lectura. --aplicar actualiza fechas; nunca envia correo.
"""
import argparse,json,os
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError

ROOT=Path(__file__).resolve().parent
BASE=ROOT/"documentos_secop_lote"
CAMPOS={"junta_aclaraciones":"fecha_junta_aclaraciones","limite_presentacion_propuestas":"fecha_apertura","fallo_programado":"fecha_fallo_programado"}

def leer(nombre):
    return json.loads((BASE/nombre).read_text(encoding="utf-8-sig"))

def consultar(metodo,params,datos=None):
    url=os.environ["SUPABASE_URL"].rstrip("/")+"/rest/v1/licitaciones?"+urlencode(params)
    key=os.getenv("SUPABASE_ADMIN_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not key:raise SystemExit("Falta SUPABASE_ADMIN_KEY o SUPABASE_SERVICE_ROLE_KEY")
    headers={"apikey":key,"Authorization":"Bearer "+key,"Content-Type":"application/json","Accept":"application/json"}
    if datos is not None:headers["Prefer"]="return=representation"
    req=Request(url,method=metodo,headers=headers,data=json.dumps(datos).encode("utf-8") if datos is not None else None)
    try:
        with urlopen(req,timeout=35) as r:return json.load(r)
    except HTTPError as e:
        raise SystemExit("Error de Supabase HTTP "+str(e.code)+" (sin mostrar credenciales)") from None

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--aplicar",action="store_true",help="Escribir fechas preliminares en registros SECOP existentes")
    p.add_argument("--codigo",default="SIDUM-AI3-CO-E108-2026",help="Numero de procedimiento exacto")
    args=p.parse_args()
    validacion=leer("validacion_automatica_secop.json")
    fichas=leer("fichas_comerciales_secop.json")
    auditoria=leer("revision_modificaciones_secop.json")
    if not os.getenv("SUPABASE_URL"):raise SystemExit("Falta SUPABASE_URL")
    v=next((x for x in validacion.get("resultados",[]) if x.get("referencia")==args.codigo),None)
    f=next((x for x in fichas.get("fichas",[]) if x.get("referencia")==args.codigo),None)
    a=next((x for x in auditoria.get("procedimientos",[]) if f and x.get("codigo")==f.get("codigo")),None)
    if not v or not f or not a:raise SystemExit("BLOQUEADO: expediente ausente de evidencias")
    if v.get("estado")!="APTO_PRELIMINAR" or v.get("errores"):
        raise SystemExit("BLOQUEADO: validacion automatica no apta")
    if a.get("estado")!="SIN_INDICIOS_EN_DOCUMENTOS_CAPTURADOS" or a.get("errores_pendientes"):
        raise SystemExit("BLOQUEADO: auditoria documental con pendientes")
    datos={}
    for etapa,campo in CAMPOS.items():
        e=(f.get("calendario") or {}).get(etapa) or {}
        fecha=e.get("fecha");hora=e.get("hora")
        if not fecha or not hora or v.get("fechas",{}).get(etapa)!=fecha+"T"+hora:
            raise SystemExit("BLOQUEADO: evidencia y validacion no coinciden: "+etapa)
        datos[campo]=fecha+" "+hora+":00"
    datos["validacion_calendario"]="preliminar_documental"
    params={"select":"id,fuente,numero_procedimiento,fecha_junta_aclaraciones,fecha_apertura,fecha_fallo_programado,validacion_calendario","numero_procedimiento":"eq."+args.codigo}
    filas=consultar("GET",params)
    if len(filas)!=1 or filas[0].get("fuente")!="SECOP Coahuila":
        raise SystemExit("BLOQUEADO: no hay un registro SECOP unico")
    actual=filas[0]
    if actual.get("validacion_calendario") not in ("pendiente","preliminar_documental"):
        raise SystemExit("BLOQUEADO: validacion existente diferente")
    for campo in CAMPOS.values():
        existente=actual.get(campo)
        if existente and str(existente).replace("T"," ")[:16]!=datos[campo][:16]:
            raise SystemExit("BLOQUEADO: conflicto con fecha existente "+campo)
    print("PROCEDIMIENTO:",args.codigo,"| ID:",actual["id"])
    for campo in CAMPOS.values():print(campo,":",datos[campo])
    if not args.aplicar:
        print("SIMULACION: sin escrituras Supabase ni correos.")
        return
    filtro={"id":"eq."+str(actual["id"]),"numero_procedimiento":"eq."+args.codigo,
            "validacion_calendario":"eq."+actual["validacion_calendario"],"select":"id,fecha_junta_aclaraciones,fecha_apertura,fecha_fallo_programado,validacion_calendario"}
    resultado=consultar("PATCH",filtro,datos)
    if len(resultado)!=1:raise SystemExit("BLOQUEADO: no se actualizo exactamente un registro")
    confirmado=consultar("GET",params)
    if len(confirmado)!=1 or any(str(confirmado[0].get(k)).replace("T"," ")[:16]!=datos[k][:16] for k in CAMPOS.values()):
        raise SystemExit("ERROR: no se confirmaron todas las fechas")
    print("CONFIRMADO EN SUPABASE: fechas preliminares actualizadas. Sin correos.")

if __name__=="__main__":main()
