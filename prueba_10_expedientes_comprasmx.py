"""Prueba integral de 10 expedientes ComprasMX: CSV oficial frente a Supabase. Solo lectura."""
import csv, json, os, shutil, tempfile, urllib.request, urllib.parse
from pathlib import Path
from tappad_importador_automatico import CSV_URL, UUID_RE, registro
IDS=(1394,1395,1396,1397,1398,1399,1400,1402,1404,1405)
CAMPOS=(("Descripción del procedimiento","descripcion"),("Número de procedimiento","numero_procedimiento"),("Fecha de publicación","fecha_publicacion"),("Fecha de Junta de aclaraciones","fecha_junta_aclaraciones"),("Fecha de apertura de proposiciones","fecha_apertura"),("Fecha de fallo","fecha_fallo_programado"),("Enlace a documentos del procedimiento","url_procedimiento"))
def main():
    base=os.environ["SUPABASE_URL"].rstrip("/")
    key=os.environ["SUPABASE_ADMIN_KEY"]
    query=urllib.parse.urlencode({"select":"id,uuid_procedimiento,numero_procedimiento,descripcion,fecha_publicacion,fecha_junta_aclaraciones,fecha_apertura,fecha_fallo_programado,url_procedimiento","id":"in.("+",".join(map(str,IDS))+")","fuente":"eq.ComprasMX"})
    req=urllib.request.Request(base+"/rest/v1/licitaciones?"+query,headers={"apikey":key,"Authorization":"Bearer "+key})
    with urllib.request.urlopen(req,timeout=60) as r: existentes=json.load(r)
    if len(existentes)!=len(IDS): raise RuntimeError("No se recuperaron los 10 expedientes de Supabase")
    uuids={str(x["uuid_procedimiento"]).lower():x for x in existentes}
    encontrados={}
    with tempfile.TemporaryDirectory() as d:
        ruta=Path(d)/"comprasmx.csv"
        with urllib.request.urlopen(urllib.request.Request(CSV_URL,headers={"User-Agent":"TAPPAD-Radar/1.0"}),timeout=180) as r,ruta.open("wb") as f: shutil.copyfileobj(r,f)
        with ruta.open(encoding="latin1",newline="") as f:
            reader=csv.DictReader(f)
            for fila in reader:
                m=UUID_RE.search(fila.get("Dirección del anuncio") or "")
                if m and m.group(1).lower() in uuids:
                    item=registro(fila)
                    if item: encontrados[m.group(1).lower()]=item
    print("PRUEBA DE 10 EXPEDIENTES REALES, SIN ESCRITURAS NI CORREOS")
    print("Encontrados en CSV:",len(encontrados),"/",len(IDS))
    resumen={"campos_oficiales":0,"campos_guardados":0,"diferencias":0,"fechas_ausentes_origen":0}
    for x in sorted(existentes,key=lambda z:z["id"]):
        origen=encontrados.get(str(x["uuid_procedimiento"]).lower())
        print("\\nEXPEDIENTE",x["id"],x["numero_procedimiento"])
        if not origen:
            print(" NO ENCONTRADO EN CSV OFICIAL");continue
        for indice,(etiqueta,campo) in enumerate(CAMPOS):
            val=origen.get(campo)
            db=x.get(campo)
            if val:resumen["campos_oficiales"]+=1
            if db:resumen["campos_guardados"]+=1
            if indice in (2,3,4,5) and not val:resumen["fechas_ausentes_origen"]+=1
            if indice in (2,3,4,5) and val and str(db or "").replace("T"," ")[:19]!=str(val).replace("T"," ")[:19]:
                resumen["diferencias"]+=1
            print(" ",etiqueta+":",val or ("Fecha no disponible, verificar enlace" if indice in (2,3,4,5) else "No disponible"))
            if indice in (2,3,4,5):print("   En Supabase:",db or "VACIO")
    print("\\nRESUMEN",json.dumps(resumen,ensure_ascii=False))
    if len(encontrados)!=len(IDS):raise SystemExit("PRUEBA INCOMPLETA: faltan expedientes en CSV")
    print("PRUEBA FINALIZADA. No se modificó Supabase.")
if __name__=="__main__":main()
