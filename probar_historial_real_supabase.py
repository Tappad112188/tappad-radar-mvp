"""Prueba sin escritura del historial persistente en Supabase.
Lee los registros de notificaciones y verifica el motor original.
No envia correos ni modifica tablas.
"""
import json,os,sys
from urllib.request import Request,urlopen
from urllib.parse import urlencode
from control_notificaciones import separar_notificaciones

def obtener_historial():
 base=os.environ.get("SUPABASE_URL","").rstrip("/")
 clave=os.environ.get("SUPABASE_ADMIN_KEY","")
 if not base.startswith("https://") or not clave:
  raise RuntimeError("Faltan SUPABASE_URL y SUPABASE_ADMIN_KEY en el entorno.")
 url=base+"/rest/v1/notificaciones_enviadas?"+urlencode({"select":"cliente_id,licitacion_id,estado","limit":1000})
 req=Request(url,headers={"apikey":clave,"Authorization":"Bearer "+clave,"Accept":"application/json"})
 with urlopen(req,timeout=20) as respuesta:
  return json.load(respuesta)
def main():
 historial=obtener_historial()
 if not historial:
  print("No hay historial; prueba sin registros.")
  return
 if len(historial)>=1000:
  raise RuntimeError("El historial supera el limite de lectura. Se requiere paginacion antes de produccion.")
 primer=historial[0]
 candidata={"cliente_id":primer["cliente_id"],"licitacion_id":primer["licitacion_id"]}
 resultado=separar_notificaciones([candidata],historial)
 print("Registros historicos leidos:",len(historial))
 print("Estados:",{e:sum(x["estado"]==e for x in historial) for e in sorted({x["estado"] for x in historial})})
 print("Registro existente retenido:",len(resultado["retenidas"])==1)
 assert len(resultado["retenidas"])==1,"El historial real no fue respetado"
 print("PRUEBA APROBADA. Sin escrituras ni correos.")
if __name__=="__main__":
 try:main()
 except Exception as e:
  print("ERROR:",str(e),file=sys.stderr)
  sys.exit(1)
