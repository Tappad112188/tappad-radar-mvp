"""TAPPAD Radar: completar SOLO calendarios de ComprasMX existentes en Supabase.
Modo predeterminado: diagnostico SIN escrituras. --aplicar habilita PATCH.
No crea licitaciones, no toca SECOP, no envia correos.
"""
import argparse,csv,json,os,re,shutil,tempfile,urllib.request,urllib.parse
from collections import Counter
from datetime import datetime
from pathlib import Path
from tappad_importador_automatico import CSV_URL,UUID_RE

CAMPOS={
 "fecha_publicacion":"Fecha publicación",
 "fecha_junta_aclaraciones":"Fecha y hora junta de aclaraciones",
 "fecha_apertura":"Fecha apertura",
 "fecha_fallo_programado":"Fecha de fallo",
}
def solicitar(url,key,method="GET",data=None):
    cab={"apikey":key,"Authorization":"Bearer "+key,"Accept":"application/json"}
    if data is not None: cab.update({"Content-Type":"application/json","Prefer":"return=minimal"})
    pet=urllib.request.Request(url,data=json.dumps(data).encode() if data is not None else None,headers=cab,method=method)
    with urllib.request.urlopen(pet,timeout=60) as resp:
        return json.load(resp) if method=="GET" else None

def normalizar_fecha(valor):
    if not valor or not valor.strip(): return None
    try: return datetime.fromisoformat(valor.strip()).strftime("%Y-%m-%dT%H:%M:%S")
    except ValueError: return None

def main():
    p=argparse.ArgumentParser(description="Sincroniza solo las cuatro fechas de licitaciones ComprasMX existentes")
    p.add_argument("--aplicar",action="store_true",help="Aplicar cambios; sin esta opcion solo diagnostica")
    p.add_argument("--max-cambios",type=int,default=49,help="Limite de procedimientos modificables por ejecucion")
    a=p.parse_args()
    base=os.environ.get("SUPABASE_URL","").rstrip("/")
    key=os.environ.get("SUPABASE_ADMIN_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not base or not key: p.error("Faltan SUPABASE_URL o SUPABASE_ADMIN_KEY")
    existentes={}
    offset=0
    while True:
        qs=urllib.parse.urlencode({"select":"uuid_procedimiento,numero_procedimiento,fecha_publicacion,fecha_junta_aclaraciones,fecha_apertura,fecha_fallo_programado","fuente":"eq.ComprasMX","limit":500,"offset":offset})
        lote=solicitar(base+"/rest/v1/licitaciones?"+qs,key)
        for x in lote:
            if x.get("uuid_procedimiento"): existentes[x["uuid_procedimiento"].lower()]=x
        if len(lote)<500: break
        offset+=500
    print("Registros ComprasMX existentes en Supabase:",len(existentes))
    encontrados={}
    with tempfile.TemporaryDirectory() as d:
        ruta=Path(d)/"comprasmx.csv"
        req=urllib.request.Request(CSV_URL,headers={"User-Agent":"TAPPAD-Radar/1.0"})
        with urllib.request.urlopen(req,timeout=180) as resp,ruta.open("wb") as out: shutil.copyfileobj(resp,out)
        if ruta.stat().st_size<1000: raise RuntimeError("CSV incompleto")
        with ruta.open(encoding="latin1",newline="") as f:
            lector=csv.DictReader(f)
            faltantes=set(CAMPOS.values())-set(lector.fieldnames or [])
            if faltantes: raise RuntimeError("Columnas ausentes: "+str(faltantes))
            for fila in lector:
                match=UUID_RE.search(fila.get("Dirección del anuncio") or "")
                if not match: continue
                uuid=match.group(1).lower()
                if uuid in existentes:
                    # Si existen varias filas del mismo UUID, conservar el último valor no vacío de cada campo.
                    registro=encontrados.setdefault(uuid,{})
                    for campo,columna in CAMPOS.items():
                        valor=normalizar_fecha(fila.get(columna))
                        if valor: registro[campo]=valor
    cambios=[]; conteo=Counter(); sin_fuente=0
    for uuid,actual in existentes.items():
        nuevo=encontrados.get(uuid)
        if not nuevo:
            sin_fuente+=1; continue
        diferencia={}
        for campo,valor in nuevo.items():
            previo=normalizar_fecha(str(actual.get(campo) or "").replace("T"," "))
            if valor!=previo:
                diferencia[campo]=valor; conteo[campo]+=1
        if diferencia: cambios.append((uuid,actual.get("numero_procedimiento"),diferencia))
    print("UUID encontrados en CSV:",len(encontrados),"| Sin coincidencia:",sin_fuente)
    print("Procedimientos con cambios:",len(cambios))
    print("Cambios por campo:",dict(conteo))
    for uuid,numero,dif in cambios[:12]:
        print(" -",numero or uuid,":",", ".join(dif))
    if not a.aplicar:
        print("MODO DIAGNOSTICO: cero escrituras. Para aplicar despues: --aplicar")
        return
    if a.max_cambios < 0 or len(cambios)>a.max_cambios:
        raise SystemExit("SINCRONIZACION BLOQUEADA: "+str(len(cambios))+" cambios superan el limite "+str(a.max_cambios))
    aplicados=0
    for uuid,numero,dif in cambios:
        qs=urllib.parse.urlencode({"uuid_procedimiento":"eq."+uuid,"fuente":"eq.ComprasMX"})
        solicitar(base+"/rest/v1/licitaciones?"+qs,key,"PATCH",dif)
        aplicados+=1
        if aplicados%100==0: print("Actualizados:",aplicados)
    print("ACTUALIZACION COMPLETADA:",aplicados,"registros; cero altas; cero correos.")
if __name__=="__main__": main()
