"""TAPPAD Radar: fichas comerciales preliminares, sin conexiones externas.
Lee fichas_secop_lote_v3.json y produce JSON y TXT para revision humana.
"""
import json,re,unicodedata
from pathlib import Path

BASE=Path(__file__).resolve().parent/"documentos_secop_lote"
ORIGEN=BASE/"fichas_secop_lote_v3.json"
def normalizar(s):
 return "".join(c for c in unicodedata.normalize("NFD",str(s).lower()) if unicodedata.category(c)!="Mn")
def categoria(objeto):
 t=normalizar(objeto)
 reglas=[
  ("seguridad_vigilancia",r"vigilancia|seguridad privada|guardias"),
  ("limpieza_jardineria",r"limpieza|jardineria|aseo"),
  ("obra_hidraulica",r"pozo profundo|agua potable|alcantarillado|saneamiento|perforacion"),
  ("obra_publica_general",r"construccion|rehabilitacion|obra publica"),
  ("tecnologia",r"computo|software|informatic|tecnologia"),
  ("papeleria_oficina",r"papeleria|material de oficina|articulos de oficina"),
 ]
 encontrados=[c for c,p in reglas if re.search(p,t)]
 return encontrados or ["sin_clasificar"]
def extracto(evidencias,patron,transformar=None):
 for item in evidencias:
  fragmento=item.get("fragmento","")
  m=re.search(patron,fragmento,re.I|re.S)
  if m:
   valor=transformar(m) if transformar else m.group(1)
   return {"valor":valor,"estado":"extraido_de_fragmento","fuente":item.get("fuente"),"evidencia":fragmento}
 return {"valor":None,"estado":"pendiente_revision_documental","fuente":None,"evidencia":None}
def campo_fecha(cal,k):
 x=cal.get(k,{})
 return {"fecha":x.get("fecha"),"hora":x.get("hora"),"estado":x.get("estado","no_identificado"),"fuente":x.get("fuente"),"evidencia":x.get("evidencia")}
def fmt(c):
 if not c or not c.get("fecha"):return "No identificado"
 return c["fecha"]+(" "+c["hora"] if c.get("hora") else "")+" ("+c.get("estado","")+")"
def main():
 if not ORIGEN.exists():raise SystemExit("No se encuentra fichas_secop_lote_v3.json; ejecuta primero generar_fichas_secop_v3.py")
 data=json.loads(ORIGEN.read_text(encoding="utf-8-sig"))
 fichas=[];lineas=["TAPPAD RADAR | FICHAS COMERCIALES PRELIMINARES","Solo revision interna; no publicar ni enviar sin validacion",""]
 for f in data.get("fichas",[]):
  e=f.get("requisitos_y_costos_evidencia",{})
  costo=extracto(e.get("costo_bases",[]),r"costo\s+de\s+las\s+bases\s*:\s*\$\s*([\d,]+(?:\.\d{2})?)")
  capital=extracto(e.get("capital_contable",[]),r"capital\s+contable\s+m[ií]nimo\s+del\s+(\d+(?:\.\d+)?\s*%)")
  if capital["valor"] is None:
   capital=extracto(e.get("capital_contable",[]),r"capital\s+contable\s+m[ií]nimo\s+(?:requerido\s+)?(?:del?\s+)?(\d+(?:\.\d+)?\s*%)")
  padron=bool(e.get("registro_proveedores"))
  gar=extracto(e.get("garantia_seriedad",[]),r"(?:por|equivalente\s+al|m[ií]nimo\s+del)\s+(\d+(?:\.\d+)?\s*%)")
  # No inferir porcentajes de fragmentos truncados.
  req={
   "costo_bases_mxn":costo,
   "capital_contable_porcentaje":capital,
   "garantia_seriedad_porcentaje":gar,
   "padron_proveedores":{"valor":"Mencionado en bases" if padron else None,"estado":"requiere_revision" if padron else "no_identificado","evidencias":e.get("registro_proveedores",[])[:2]},
   "garantia_cumplimiento":{"estado":"mencionada_revisar_condiciones" if e.get("garantia_cumplimiento") else "no_identificada","evidencias":e.get("garantia_cumplimiento",[])[:2]},
   "experiencia":{"estado":"mencionada_revisar_condiciones" if e.get("experiencia") else "no_identificada","evidencias":e.get("experiencia",[])[:2]}
  }
  calendario={k:campo_fecha(f.get("calendario",{}),k) for k in ("visita_obra","junta_aclaraciones","limite_presentacion_propuestas","fallo_programado","inicio_servicio_obra","terminacion_servicio_obra")}
  ficha={"codigo":f.get("codigo"),"referencia":f.get("referencia"),"objeto":f.get("objeto"),"publicacion":f.get("publicacion"),"estatus_portal":f.get("estatus"),"categorias_sugeridas":categoria(f.get("objeto","")),"clasificacion":"automatica_pendiente_revision","calendario":calendario,"condiciones":req,"documentos":f.get("documentos",[]),"estado_publicacion":"NO_PUBLICAR_PENDIENTE_VALIDACION"}
  fichas.append(ficha)
  lineas.extend(["="*65,f'{ficha["codigo"]} | {ficha["referencia"]}',ficha["objeto"] or "",f'Categorias sugeridas: {", ".join(ficha["categorias_sugeridas"])}',f'Costo bases (MXN): {costo["valor"] or "No identificado"}',f'Capital contable: {capital["valor"] or "No identificado"}',f'Garantia seriedad: {gar["valor"] or "No identificado"}',f'Padron: {"Mencionado, verificar vigencia y requisitos" if padron else "No identificado"}'])
  for k,v in calendario.items():lineas.append(k+": "+fmt(v))
  lineas.extend(["Estado: PENDIENTE DE VALIDACION",""])
 salida={"origen":"fichas_secop_lote_v3.json","fecha_consulta":data.get("fecha_consulta"),"uso":"revision_interna","fichas":fichas}
 j=BASE/"fichas_comerciales_secop.json";t=BASE/"fichas_comerciales_secop.txt"
 j.write_text(json.dumps(salida,ensure_ascii=False,indent=2),encoding="utf-8")
 t.write_text("\n".join(lineas),encoding="utf-8")
 print("Fichas comerciales:",len(fichas))
 for f in fichas:
  print(f["codigo"],"->",", ".join(f["categorias_sugeridas"]),"| costo bases:",f["condiciones"]["costo_bases_mxn"]["valor"] or "no identificado")
 print("JSON:",j)
 print("Resumen legible:",t)
 print("No se ha enviado correo ni modificado Supabase.")
if __name__=="__main__":main()
