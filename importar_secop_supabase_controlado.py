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
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--importar",action="store_true")
    args=p.parse_args()
    if not LOTE.exists():raise SystemExit("Falta lote SECOP local")
    lote=json.loads(LOTE.read_text(encoding="utf-8-sig"))
    registros=lote.get("registros") or []
    if not registros:raise SystemExit("Lote vacio: sin cambios")
    ids=set()
    nuevos=[]
    for original in registros:
        uid=original.get("uuid_procedimiento")
        if not isinstance(uid,str) or not uid.startswith("secop-coahuila:") or uid in ids:
            raise SystemExit("Identificador SECOP invalido o duplicado")
        ids.add(uid)
        if original.get("fuente")!="SECOP Coahuila" or not original.get("cod_expediente") or not original.get("nombre_procedimiento"):
            raise SystemExit("Ficha incompleta: "+uid)
        if str(original.get("estatus") or "").strip().casefold()!="vigente":
            raise SystemExit("Estatus no Vigente en lote: "+uid)
        encontrado=api("GET",{"select":"id,uuid_procedimiento","uuid_procedimiento":"eq."+uid})
        if encontrado:
            print("EXISTENTE (sin actualizar):",uid)
            continue
        registro={k:v for k,v in original.items() if k in CAMPOS and v is not None}
        registro["validacion_calendario"]="pendiente"
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
