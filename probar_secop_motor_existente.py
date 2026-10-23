"""Adaptador de SECOP Coahuila al esquema existente de ComprasMX.
SOLO PREVISUALIZACION: las fechas documentales aun requieren validacion oficial.
No envia correos, no escribe en bases de datos ni activa automatizaciones.
"""
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from preparador_alertas import preparar_alertas, vista_previa_correo

BASE=Path(__file__).resolve().parent/"documentos_secop_lote"
ENTRADA=BASE/"fichas_comerciales_secop.json"
SALIDA=BASE/"prueba_motor_existente_secop.txt"
PROVEEDORES=[
 {"id":"prueba-limpieza","empresa":"EJEMPLO - Limpieza","palabras_clave":"limpieza, jardineria","activo":True},
 {"id":"prueba-vigilancia","empresa":"EJEMPLO - Vigilancia","palabras_clave":"seguridad, vigilancia","activo":True},
 {"id":"prueba-hidraulica","empresa":"EJEMPLO - Hidraulica","palabras_clave":"pozo profundo, agua potable","activo":True},
 {"id":"prueba-laboratorio","empresa":"EJEMPLO - Laboratorio","palabras_clave":"laboratorio clinico","activo":True}
]
COBERTURAS={p["id"]:[{"estado":"Coahuila"}] for p in PROVEEDORES}
def evento_fecha(evento):
 if not isinstance(evento,dict) or not evento.get("fecha"):return None
 return evento["fecha"]+("T"+evento["hora"]+":00" if evento.get("hora") else "T00:00:00")
def adaptar(f):
 calendario=f.get("calendario") or {}
 return {
  "id":"secop-coahuila:"+str(f.get("codigo") or f.get("referencia")),
  "fuente":"SECOP Coahuila",
  "numero_procedimiento":f.get("referencia") or f.get("codigo"),
  "nombre_procedimiento":f.get("objeto") or "",
  "descripcion":f.get("objeto") or "",
  "tipo_contratacion":"",
  "entidad_federativa":"Coahuila",
  "fecha_publicacion":f.get("publicacion"),
  "fecha_junta_aclaraciones":evento_fecha(calendario.get("junta_aclaraciones")),
  "fecha_apertura":evento_fecha(calendario.get("limite_presentacion_propuestas")),
  "fecha_fallo_programado":evento_fecha(calendario.get("fallo_programado")),
  "estatus":str(f.get("estatus_portal") or "").lower(),
  "url_procedimiento":f.get("url_procedimiento"),
  "estado_validacion":"PENDIENTE_VALIDACION_DOCUMENTAL",
 }
def main():
 if not ENTRADA.exists():raise SystemExit("Falta documentos_secop_lote/fichas_comerciales_secop.json")
 data=json.loads(ENTRADA.read_text(encoding="utf-8-sig"))
 licitaciones=[adaptar(f) for f in data.get("fichas",[])]
 # Fecha fija de la prueba: reproducible y anterior a los actos de apertura.
 ahora=datetime(2026,10,23,9,0,tzinfo=ZoneInfo("America/Monterrey"))
 resultado=preparar_alertas(PROVEEDORES,licitaciones,COBERTURAS,[],ahora=ahora)
 lineas=["PRUEBA DE INTEGRACION CON MOTOR EXISTENTE DE COMPRASMX",
         "NO ENVIAR: FECHAS SECOP PENDIENTES DE VALIDACION OFICIAL",
         "Fecha de simulacion: 2026-10-23 09:00 America/Monterrey",""]
 for p in PROVEEDORES:
  oportunidades=resultado["por_proveedor"].get(p["id"],[])
  lineas.append(p["empresa"]+": "+str(len(oportunidades))+" coincidencia(s)")
  if oportunidades:
   correo=vista_previa_correo(p["empresa"],oportunidades)
   lineas.extend(["ASUNTO: "+correo["asunto"],correo["cuerpo"],""])
 lineas.extend(["RESUMEN: "+json.dumps(resultado["resumen"],ensure_ascii=False),
                "Solo simulacion. No se enviaron correos ni se modificaron datos."])
 SALIDA.write_text("\n".join(lineas),encoding="utf-8")
 for p in PROVEEDORES:
  print(p["empresa"],"->",len(resultado["por_proveedor"].get(p["id"],[])),"coincidencia(s)")
 print("Vista previa:",SALIDA)
 print("AVISO: no apto para envio real sin validar las fechas de SECOP.")
if __name__=="__main__":main()
