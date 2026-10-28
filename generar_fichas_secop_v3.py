"""TAPPAD Radar - fichas SECOP desde documentos PDF/DOCX descargados.
Solo lectura: no modifica Supabase ni envía correos.
Uso: py generar_fichas_secop_v3.py
"""
import json, re, unicodedata, zipfile, hashlib
from pathlib import Path
from datetime import datetime
from xml.etree import ElementTree as ET
import pymupdf

ROOT=Path(__file__).resolve().parent
BASE=ROOT/"documentos_secop_lote"
FUENTE=ROOT/"secop_hoy_vigentes.json"
MESES={m:i for i,m in enumerate("enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split(),1)}
MESES["setiembre"]=9
FECHA=re.compile(r"(?<!\d)(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)\s+(?:de|del)\s+(20\d{2})(?!\d)|(?<!\d)(\d{1,2})[/.-](\d{1,2})[/.-](20\d{2})(?!\d)",re.I)
HORA=re.compile(r"(?<!\d)(\d{1,2})\s*[:.]\s*(\d{2})\s*(?:horas|hrs|h)?",re.I)
ETAPAS=[
 ("visita_obra",r"\bvisita\s+(?:al\s+(?:lugar|sitio)|de\s+obra|a\s+la\s+obra)"),
 ("junta_aclaraciones",r"\bjunta\s+de\s+aclaraciones"),
 ("presentacion_apertura",r"(?:presentaci[oó]n\s+(?:de\s+proposiciones\s+y\s+)?apertura|presentaci[oó]n\s+de\s+proposiciones\s+y\s+apertura|apertura\s+de\s+(?:proposiciones|propuestas)|presentaci[oó]n\s+de\s+proposiciones)"),
 ("fallo_programado",r"(?:\bfallo\s*:|\bacto\s+de\s+fallo\s*:|\bfecha\s+(?:del?\s+)?fallo\s*:)"),
 ("inicio_servicio_obra",r"(?:fecha\s+de\s+inicio|inicio\s+de\s+(?:los\s+)?(?:trabajos|servicios|obra))"),
 ("terminacion_servicio_obra",r"(?:fecha\s+de\s+t[eé]rmino|terminaci[oó]n\s+de\s+(?:los\s+)?(?:trabajos|servicios|obra))")
]
EXTRAS={
 "costo_bases":r"(?:costo|precio|importe|venta)\s+(?:de\s+)?(?:las\s+)?bases",
 "capital_contable":r"capital\s+contable",
 "garantia_seriedad":r"(?:garant[ií]a\s+(?:de\s+)?(?:seriedad|sostenimiento)|sostenimiento\s+de\s+ofertas)",
 "garantia_cumplimiento":r"garant[ií]a\s+de\s+cumplimiento",
 "experiencia":r"experiencia\s+(?:m[ií]nima|requerida|en|de)",
 "registro_proveedores":r"(?:padr[oó]n|registro)\s+(?:de\s+)?proveedores"
}
def norm(s):
 return "".join(c for c in unicodedata.normalize("NFD",s.lower()) if unicodedata.category(c)!="Mn")
def docx_texto(p):
 with zipfile.ZipFile(p) as z:
  root=ET.fromstring(z.read("word/document.xml"))
  ns="{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
  return [("documento Word", "\n".join("".join(x.text or "" for x in para.iter(ns+"t")) for para in root.iter(ns+"p")))]
def pdf_texto(p):
 with pymupdf.open(p) as d:return [(f"página {i+1}",pg.get_text()) for i,pg in enumerate(d)]

def documentos_del_procedimiento(carpeta, codigo):
 """Selecciona únicamente bases cuyo nombre interno coincide con el código SECOP.
 No extrae rutas arbitrarias ni mezcla expedientes; conserva los RAR originales.
 """
 import subprocess, tempfile
 encontrados=[]
 for rar in sorted(carpeta.glob("*.rar")):
  try:
   listado=subprocess.run(["tar","-tf",str(rar)],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=90,check=True).stdout.splitlines()
  except (OSError,subprocess.SubprocessError) as e:
   print("ADVERTENCIA RAR:",rar.name,str(e)[:160]);continue
  bases=[x for x in listado if re.search(r"^BASES\\s+",Path(x.replace("\\\\","/")).name,re.I) and Path(x).suffix.lower()==".pdf"]
  validas=[x for x in bases if codigo.casefold() in re.sub(r"\\s+"," ",Path(x).name).casefold()]
  if len(validas)!=1:
   print("ADVERTENCIA: bases no coincidentes o ambiguas en",rar.name,"|",bases)
   continue
  # Extraer solo el miembro seleccionado en un directorio temporal, sin sobrescribir.
  with tempfile.TemporaryDirectory(prefix="tappad_bases_") as temporal:
   nombre=validas[0]
   destino=Path(temporal)/Path(nombre).name
   try:
    with destino.open("wb") as f:
     p=subprocess.run(["tar","-xOf",str(rar),nombre],stdout=f,stderr=subprocess.PIPE,timeout=120,check=True)
    if destino.stat().st_size>30_000_000 or destino.read_bytes()[:5]!=b"%PDF-":
     raise ValueError("PDF inválido o mayor a 30 MB")
    secciones=pdf_texto(destino)
    encontrados.append((rar.name,nombre,secciones,hashlib.sha256(destino.read_bytes()).hexdigest()))
   except (OSError,subprocess.SubprocessError,ValueError) as e:
    print("ADVERTENCIA: no se pudo leer",nombre,str(e)[:160])
 return encontrados

def extraer_fecha(s):
 m=FECHA.search(s)
 if not m:return None,None
 try:
  if m.group(1): d,mes,y=int(m.group(1)),MESES[norm(m.group(2))],int(m.group(3))
  else:d,mes,y=int(m.group(4)),int(m.group(5)),int(m.group(6))
  return datetime(y,mes,d).date().isoformat(),m
 except (ValueError,KeyError):return None,None
def fecha_hora(segmento):
 fecha,m=extraer_fecha(segmento)
 if not fecha:return None,None
 # Hora inmediatamente anterior o posterior a la fecha; no confundir con direcciones o folios.
 alrededor=segmento[max(0,m.start()-65):min(len(segmento),m.end()+65)]
 horas=[]
 for h in HORA.finditer(alrededor):
  hh,mm=int(h.group(1)),int(h.group(2))
  if hh<=23 and mm<=59 and (re.search(r"horas|hrs",alrededor[h.end():h.end()+8],re.I) or re.search(r"horas|hrs",h.group(),re.I)):
   horas.append((abs(h.start()-(m.start()-max(0,m.start()-65))),f"{hh:02d}:{mm:02d}"))
 return fecha,(sorted(horas)[0][1] if horas else None)
# Encabezados de actos: se exige dos puntos para evitar menciones narrativas.
ENCABEZADOS={
 "visita_obra":r"(?:visita\s+(?:al\s+(?:lugar|sitio)|de\s+obra|a\s+la\s+obra)[^:\n]{0,75}:)",
 "junta_aclaraciones":r"junta\s+de\s+aclaraciones\s*:",
 "presentacion_apertura":r"(?:presentacion\s+de\s+proposiciones\s+y\s+apertura\s+de\s+propuestas\s+tecnicas\s+y\s+economicas|presentacion\s+y\s+apertura\s+de\s+propuestas\s+tecnicas\s+y\s+economicas|presentacion\s+de\s+proposiciones\s+y\s+apertura\s+de\s+proposiciones)\s*:",
 "fallo_programado":r"(?:acto\s+de\s+fallo|fallo)\s*:",
 "inicio_servicio_obra":r"(?:fecha\s+de\s+inicio\s+y\s+termino\s+de\s+la\s+obra\s*:|fecha\s+de\s+inicio\s+de\s+(?:los\s+)?trabajos\s*:)",
 "terminacion_servicio_obra":r"(?:terminacion\s+el\s+dia|fecha\s+de\s+terminacion\s*:|fecha\s+de\s+termino\s*:)"
}
def candidatos(secciones,etapa,patron):
 out=[]
 encabezado=ENCABEZADOS.get(etapa,patron)
 for lugar,txt in secciones:
  n=norm(txt)
  for match in list(re.finditer(encabezado,n,re.I))[:40]:
   # Recortar antes del siguiente encabezado oficial; no tomar su fecha.
   ventana=txt[match.end():match.end()+240]
   if etapa=="inicio_servicio_obra":
    corte=re.search(r"terminacion\s+el\s+dia",norm(ventana))
    if corte:ventana=ventana[:corte.start()]
   if etapa in ("junta_aclaraciones","presentacion_apertura"):
    corte=re.search(r"\b(?:4\.[23]\.|5\.\s*fallo|acto\s+de\s+fallo)\s*",norm(ventana))
    if corte:ventana=ventana[:corte.start()]
   fecha,hora=fecha_hora(ventana)
   evidencia=txt[max(0,match.start()-35):min(len(txt),match.end()+240)].strip()
   if fecha:
    out.append({"fecha":fecha,"hora":hora,"ubicacion":lugar,"evidencia":evidencia[:390],"distancia":FECHA.search(ventana).start()})
 return out
def elegir(etapa,lista):
 if not lista:return {"estado":"no_identificado","fecha":None,"hora":None,"evidencia":[]}
 # Priorizar fecha próxima al encabezado y presencia de hora. Conservar evidencias y conflictos.
 lista.sort(key=lambda x:(x["distancia"],x["hora"] is None))
 mejor=lista[0]
 alternativas=sorted(set((x["fecha"],x["hora"]) for x in lista if x["fecha"]!=mejor["fecha"] or x["hora"]!=mejor["hora"]),key=str)
 estado="requiere_revision" if alternativas or not mejor["hora"] and etapa not in ("inicio_servicio_obra","terminacion_servicio_obra") else "candidato_documental"
 return {"estado":estado,"fecha":mejor["fecha"],"hora":mejor["hora"],"fuente":mejor["ubicacion"],"evidencia":mejor["evidencia"],"alternativas":[{"fecha":f,"hora":h} for f,h in alternativas[:6]]}
def main():
 if not FUENTE.exists() or not BASE.exists():
  raise SystemExit("Faltan secop_hoy_vigentes.json o la carpeta documentos_secop_lote")
 origen=json.loads(FUENTE.read_text(encoding="utf-8-sig"))
 salida={"fecha_consulta":origen.get("fecha_consulta"),"estado_general":"pendiente_revision","fichas":[],"politica":"No escribir a base de datos ni enviar correos"}
 for r in origen.get("registros",[]):
  codigo=r["codigo"];carpeta=BASE/re.sub(r"[^A-Za-z0-9._-]+","_",codigo).strip("._")[:110]
  docs=[];vistos=set();secciones=[]
  for p in sorted(carpeta.glob("*")) if carpeta.exists() else []:
   if p.suffix.lower() not in (".pdf",".docx"):continue
   sha=hashlib.sha256(p.read_bytes()).hexdigest()
   if sha in vistos:continue
   vistos.add(sha)
   try:
    sec=pdf_texto(p) if p.suffix.lower()==".pdf" else docx_texto(p)
    secciones.extend([(p.name+" · "+loc,txt) for loc,txt in sec])
    docs.append({"nombre":p.name,"sha256":sha,"secciones":len(sec)})
   except Exception as e:docs.append({"nombre":p.name,"error":str(e)})
  # Los RAR se inspeccionan por código interno; solo las bases coincidentes aportan fechas.
  # No utilizar archivos de otro procedimiento aunque SECOP los muestre juntos.
  for rar,miembro,sec,sha in documentos_del_procedimiento(carpeta,codigo):
   secciones.extend([(rar+" / "+miembro+" · "+loc,txt) for loc,txt in sec])
   docs.append({"nombre":miembro,"archivo_origen":rar,"sha256":sha,"secciones":len(sec),"coincidencia_codigo":"confirmada_por_nombre_interno"})
  eventos={k:elegir(k,candidatos(secciones,k,pat)) for k,pat in ETAPAS}
  apertura=eventos["presentacion_apertura"]
  eventos["limite_presentacion_propuestas"]={**apertura,"criterio":"Misma fecha y hora de presentación y apertura; verificar eventuales modificaciones"}
  extras={}
  for k,pat in EXTRAS.items():
   evid=[]
   for lugar,txt in secciones:
    for m in list(re.finditer(pat,norm(txt),re.I))[:5]:
     evid.append({"fuente":lugar,"fragmento":txt[max(0,m.start()-100):min(len(txt),m.end()+300)].strip()[:400]})
     if len(evid)>=5:break
    if len(evid)>=5:break
   extras[k]=evid
  ficha={"codigo":codigo,"referencia":r.get("documentos_referencia"),"objeto":r.get("descripcion"),"publicacion":r.get("fecha_publicacion"),"estatus":r.get("estatus"),"documentos":docs,"calendario":eventos,"requisitos_y_costos_evidencia":extras,"validacion":"pendiente_revision"}
  salida["fichas"].append(ficha)
  print("\n"+codigo)
  for k,v in eventos.items():
   print(" ",k,":",v.get("fecha") or "sin fecha",v.get("hora") or "", "["+v["estado"]+"]")
 destino=BASE/"fichas_secop_lote_v3.json"
 destino.write_text(json.dumps(salida,ensure_ascii=False,indent=2),encoding="utf-8")
 print("\nFichas generadas:",destino)
 print("Datos candidatos, no publicar sin validar. Sin cambios a Supabase ni correos.")
if __name__=="__main__":main()
