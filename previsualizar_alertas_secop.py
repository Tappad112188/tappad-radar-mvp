"""TAPPAD Radar: vista previa de alertas, sin envio de correos."""
import json
from pathlib import Path
BASE=Path(__file__).resolve().parent/"documentos_secop_lote"
ORIGEN=BASE/"simulacion_coincidencias_secop.json"
SALIDA=BASE/"vista_previa_alertas_secop.txt"
def fecha(evento):
 if not evento or not evento.get("fecha"):return "No identificada"
 return evento["fecha"]+(" a las "+evento["hora"] if evento.get("hora") else "")
def main():
 if not ORIGEN.exists():raise SystemExit("Falta simulacion_coincidencias_secop.json")
 d=json.loads(ORIGEN.read_text(encoding="utf-8-sig"))
 partes=["TAPPAD RADAR - VISTA PREVIA DE ALERTAS","SIMULACION INTERNA: NO ENVIADO",""]
 n=0
 for p in d.get("proveedores",[]):
  for f in p.get("coincidencias",[]):
   n+=1
   partes.extend(["="*72,"PARA: "+p["proveedor"],"ASUNTO: TAPPAD Radar | Nueva licitacion de tu giro | "+f["codigo"],"","Se identifico una oportunidad relacionada con tu actividad:","",f.get("objeto") or "Objeto no identificado","Procedimiento: "+str(f.get("referencia") or f.get("codigo")),"Fecha de publicacion: "+str(f.get("publicacion") or "No identificada"),"Junta de aclaraciones: "+fecha(f.get("junta_aclaraciones")),"Presentacion y apertura de propuestas (fecha limite): "+fecha(f.get("presentacion_apertura")),"Fallo programado: "+fecha(f.get("fallo_programado")),"","Si deseas apoyo para revisar las bases y preparar tu propuesta, solicita asesoria a TAPPAD Consultoria.","","Aviso: Coincidencia por giro; no acredita cumplimiento de requisitos. Las fechas pueden modificarse mediante avisos oficiales.",""])
 SALIDA.write_text("\n".join(partes),encoding="utf-8")
 print("Alertas simuladas:",n)
 print("Archivo:",SALIDA)
 print("No se envio ningun correo ni se modificaron bases de datos.")
if __name__=="__main__":main()
