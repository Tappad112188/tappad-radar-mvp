"""Diagnostico SECOP: comprueba integridad de los expedientes existentes.
Solo lectura de Supabase; no cambia estados ni envia mensajes.
"""
import os, json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

def main():
    base=os.environ["SUPABASE_URL"].rstrip("/")
    key=os.environ["SUPABASE_ADMIN_KEY"]
    params=urlencode({"select":"id,numero_procedimiento,cod_expediente,fecha_publicacion,fecha_junta_aclaraciones,fecha_apertura,fecha_fallo_programado,url_bases,url_convocatoria,validacion_calendario,documentos_disponibles","fuente":"eq.SECOP Coahuila","order":"id.asc"})
    req=Request(base+"/rest/v1/licitaciones?"+params,headers={"apikey":key,"Authorization":"Bearer "+key})
    with urlopen(req,timeout=30) as resp: registros=json.load(resp)
    print("PROCEDIMIENTOS SECOP:",len(registros))
    for r in registros:
        docs=r.get("documentos_disponibles")
        print("ID:",r["id"],"| referencia:",r["numero_procedimiento"],"| expediente:",r["cod_expediente"])
        print("  fechas: junta=",bool(r.get("fecha_junta_aclaraciones")),"apertura=",bool(r.get("fecha_apertura")),"fallo=",bool(r.get("fecha_fallo_programado")))
        print("  bases vinculadas:",bool(r.get("url_bases")),"| convocatoria:",bool(r.get("url_convocatoria")),"| documentos:",len(docs) if isinstance(docs,list) else 0,"| validacion:",r.get("validacion_calendario"))
    print("DIAGNOSTICO COMPLETADO: sin escrituras, sin correos.")

if __name__=="__main__": main()
