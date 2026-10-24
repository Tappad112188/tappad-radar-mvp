"""SECOP Coahuila -> formato de importacion de licitaciones Supabase.
Prepara JSON para revision. No conecta ni escribe en Supabase.
Solo incluye datos verificados de las fichas y conserva su estado pendiente.
"""
import json
from pathlib import Path
BASE=Path(__file__).resolve().parent/"documentos_secop_lote"
ENTRADA=BASE/"fichas_comerciales_secop.json"
SALIDA=BASE/"secop_importacion_pendiente_revision.json"
REPORTE_ENLACES=BASE/"reporte_descargas.json"
def fecha(evento):
 if not isinstance(evento,dict) or not evento.get("fecha"):return None
 return evento["fecha"]+("T"+evento["hora"]+":00" if evento.get("hora") else "")
def adaptar(f):
 codigo=f.get("codigo") or f.get("referencia")
 if not codigo:raise ValueError("Ficha sin codigo ni referencia")
 calendario=f.get("calendario") or {}
 return {
  "uuid_procedimiento":"secop-coahuila:"+str(codigo).strip().lower(),
  "fuente":"SECOP Coahuila",
  "numero_procedimiento":f.get("referencia") or codigo,
  "cod_expediente":codigo,
  "nombre_procedimiento":f.get("objeto"),
  "descripcion":f.get("objeto"),
  "entidad_federativa":"Coahuila",
  "estatus":f.get("estatus_portal"),
  "fecha_publicacion":f.get("publicacion"),
  "fecha_junta_aclaraciones":fecha(calendario.get("junta_aclaraciones")),
  "fecha_apertura":fecha(calendario.get("limite_presentacion_propuestas")),
  "fecha_fallo_programado":fecha(calendario.get("fallo_programado")),
  "url_procedimiento":f.get("url_procedimiento"),
 }
def incorporar_enlaces(registros):
 """Asocia enlaces anonimos verificados; no confirma el calendario."""
 if not REPORTE_ENLACES.exists():
  return "Sin reporte_descargas.json: enlaces sin asociar"
 datos=json.loads(REPORTE_ENLACES.read_text(encoding="utf-8-sig"))
 por_codigo={str(x.get("codigo")):x for x in datos.get("procedimientos",[])}
 for registro in registros:
  item=por_codigo.get(str(registro["cod_expediente"]))
  if not item:continue
  bases=item.get("bases_verificadas") or []
  verificadas=[b for b in bases if b.get("estado")=="verificado_sin_sesion"]
  registro["documentos_bases_verificados"]=[{"url":b.get("url"),"texto":b.get("texto")} for b in verificadas]
  if len(bases)==1 and len(verificadas)==1 and item.get("estado_enlace")=="verificado_sin_sesion":
   registro["url_procedimiento"]=verificadas[0]["url"]
   registro["tipo_enlace"]="descarga_directa_bases"
  elif len(bases)>1:
   registro["revision_enlace"]="multiples_bases_no_seleccionar_automaticamente"
 return "Enlaces asociados; calendario pendiente de revision"

def main():
 if not ENTRADA.exists():raise SystemExit("No se encontro fichas_comerciales_secop.json")
 datos=json.loads(ENTRADA.read_text(encoding="utf-8-sig"))
 registros=[adaptar(f) for f in datos.get("fichas",[])]
 aviso_enlaces=incorporar_enlaces(registros)
 ids=[r["uuid_procedimiento"] for r in registros]
 if len(ids)!=len(set(ids)):raise ValueError("Hay procedimientos duplicados en el lote")
 salida={"estado":"PENDIENTE_VALIDACION_OFICIAL_NO_IMPORTAR_AUTOMATICAMENTE",
 "advertencia":"Las fechas documentales aun requieren validacion oficial. El campo fecha_fallo no se utiliza para representar un fallo programado.",
 "total":len(registros),"aviso_enlaces":aviso_enlaces,"registros":registros}
 SALIDA.write_text(json.dumps(salida,ensure_ascii=False,indent=2),encoding="utf-8")
 print("Procedimientos SECOP preparados:",len(registros))
 for r in registros:print(r["uuid_procedimiento"],"|",r["numero_procedimiento"])
 print("Archivo de revision:",SALIDA)
 print("Campos calendario: publicacion, junta, apertura y fallo programado.")
 print("Enlaces:",aviso_enlaces)
 print("No se ha importado nada a Supabase. Fechas pendientes de validacion.")
if __name__=="__main__":main()
