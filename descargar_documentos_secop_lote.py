"""TAPPAD Radar: descarga documentos de los procedimientos SECOP ya filtrados.
Solo lectura; no modifica bases de datos ni envía correos.
Uso: py descargar_documentos_secop_lote.py
"""
import asyncio, json, re, urllib.request, urllib.error
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright

BASE=Path(__file__).resolve().parent
ENTRADA=BASE/"secop_hoy_vigentes.json"
SALIDA=BASE/"documentos_secop_lote"
URL="https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"

def verificar_bases_sin_sesion(url):
 """GET anonimo limitado a 1024 bytes; no reutiliza cookies de Chromium."""
 p=urlparse(str(url or ""))
 if (p.scheme!="https" or p.hostname!="www.sefincoahuila.gob.mx"
     or not re.fullmatch(r"/sistemas/Secop/Procedimiento/GetFile/\d+",p.path,re.I)
     or p.query or p.fragment):
  return {"estado":"url_no_permitida"}
 solicitud=urllib.request.Request(url,headers={"Range":"bytes=0-1023","User-Agent":"Mozilla/5.0"},method="GET")
 try:
  with urllib.request.urlopen(solicitud,timeout=25) as respuesta:
   cabecera=respuesta.headers.get("Content-Disposition","").lower()
   tipo=respuesta.headers.get("Content-Type","").lower()
   firma=respuesta.read(1024)
   archivo=firma.startswith((b"%PDF-",b"PK\\x03\\x04",b"\\xd0\\xcf\\x11\\xe0"))
   return {"estado":"verificado_sin_sesion" if archivo and respuesta.status in (200,206) else "respuesta_no_confirmada",
           "http":respuesta.status,"tipo":tipo,"adjunto":"attachment" in cabecera}
 except Exception as exc:
  return {"estado":"error_verificacion","detalle":str(exc)[:160]}

def nombre_seguro(s):
 return re.sub(r"[^A-Za-z0-9._-]+","_",s).strip("._")[:110] or "archivo"

async def main():
 if not ENTRADA.exists():
  print("ERROR: No existe",ENTRADA)
  return
 data=json.loads(ENTRADA.read_text(encoding="utf-8-sig"))
 hoy=datetime.now(ZoneInfo("America/Monterrey")).date().isoformat()
 registros=[r for r in data.get("registros",[]) if r.get("fecha_publicacion")==data.get("fecha_consulta") and r.get("estatus","").strip().casefold()=="vigente"]
 if not data.get("filtros_aplicados") or data.get("errores") or not registros:
  print("ERROR: El archivo no contiene procedimientos válidos y filtrados.")
  return
 if data.get("fecha_consulta")!=hoy:
  raise SystemExit("ERROR: El lote SECOP es de "+str(data.get("fecha_consulta"))+" y hoy es "+hoy+". Ejecuta primero la extracción actualizada.")
 SALIDA.mkdir(exist_ok=True)
 reporte={"fecha_fuente":data.get("fecha_consulta"),"procedimientos":[],"errores":[]}
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(headless=False)
  context=await browser.new_context(accept_downloads=True)
  page=await context.new_page()
  try:
   for r in registros:
    codigo=r["codigo"]
    item={"codigo":codigo,"referencia":r.get("documentos_referencia"),"archivos":[],"enlaces_documentos":[],"bases_verificadas":[],"convocatorias_verificadas":[],"url_bases_candidata":None,"url_convocatoria_candidata":None,"estado_enlace":"pendiente_verificacion_externa","errores":[]}
    reporte["procedimientos"].append(item)
    carpeta=SALIDA/nombre_seguro(codigo)
    carpeta.mkdir(exist_ok=True)
    descargas=[]
    async def guardar(download):
     try:
      nombre=nombre_seguro(download.suggested_filename)
      ruta=carpeta/nombre
      i=2
      while ruta.exists():
       ruta=carpeta/(str(i)+"_"+nombre)
       i+=1
      await download.save_as(ruta)
      item["archivos"].append({"nombre":download.suggested_filename,"ruta":str(ruta),"bytes":ruta.stat().st_size})
      print("  Descargado:",ruta.name)
     except Exception as e:
      item["errores"].append("Descarga: "+str(e))
    def evento(download):
     descargas.append(asyncio.create_task(guardar(download)))
    page.on("download",evento)
    try:
     print("\nProcedimiento:",codigo)
     resp=await page.goto(URL,wait_until="domcontentloaded",timeout=60000)
     if not resp or resp.status!=200: raise RuntimeError("SECOP no respondió HTTP 200")
     # SECOP: aplicar primero estatus Vigente, luego fecha, igual que el extractor.
     await page.locator("#CardView_col3 img[alt='[Filtrar]']").click(timeout=20000)
     opciones=page.locator("[id^='CardView_HFListBox_LBI']:visible")
     await opciones.first.wait_for(state="visible",timeout=20000)
     etiquetas=await opciones.all_inner_texts()
     indices=[i for i,t in enumerate(etiquetas) if t.strip().casefold()=="vigente"]
     if len(indices)!=1: raise RuntimeError("Filtro Vigente ambiguo en descarga: "+repr(etiquetas))
     await opciones.nth(indices[0]).click(timeout=20000)
     await page.locator("#CardView_col3 img[alt='[Filtrado]']").wait_for(state="attached",timeout=20000)
     await page.locator("#CardView_col2 img[alt='[Filtrar]']").click(timeout=20000)
     await page.locator("#CardView_HFFDE_I").wait_for(state="visible",timeout=20000)
     fecha=datetime.strptime(r["fecha_publicacion"],"%Y-%m-%d").strftime("%d/%m/%Y")
     await page.locator("#CardView_HFFDE_I").fill(fecha)
     await page.locator("#CardView_HFTDE_I").fill(fecha)
     await page.locator("#CardView_DXHFP_TPCFCm1_O").click(timeout=20000)
     await page.locator("#CardView_col2 img[alt='[Filtrado]']").wait_for(state="attached",timeout=20000)
     await page.wait_for_timeout(1200)
     ref=r.get("documentos_referencia","")
     # Encontrar referencia por texto en la tabla, evitando IDs efímeros.
     enlace=page.get_by_text(ref,exact=True).first
     await enlace.wait_for(state="visible",timeout=20000)
     await enlace.click(timeout=20000)
     await page.get_by_text("Base de Procedimiento",exact=False).first.wait_for(state="visible",timeout=20000)
     await page.wait_for_timeout(900)
     # En SECOP los documentos aparecen en la misma pagina tras abrir la referencia.
     # Extraer solo URLs oficiales GetFile visibles y clasificar las bases.
     item["enlaces_documentos"]=await page.evaluate("""() => [...document.querySelectorAll('a[href]')].filter(a=>a.offsetParent!==null && /^https:\\/\\/www\\.sefincoahuila\\.gob\\.mx\\/sistemas\\/Secop\\/Procedimiento\\/GetFile\\/\\d+$/i.test(a.href)).map(a=>({texto:(a.innerText||'').trim(),url:a.href}))""")
     bases=[e for e in item["enlaces_documentos"] if "BASES" in e["texto"].upper() or "BASE DE PROCEDIMIENTO" in e["texto"].upper()]
     convocatorias=[e for e in item["enlaces_documentos"] if "CONVOCATORIA" in e["texto"].upper()]
     for convocatoria in convocatorias:
      resultado=await asyncio.to_thread(verificar_bases_sin_sesion,convocatoria["url"])
      item["convocatorias_verificadas"].append({**convocatoria,**resultado})
     if len(convocatorias)==1 and item["convocatorias_verificadas"][0]["estado"]=="verificado_sin_sesion":
      item["url_convocatoria_candidata"]=convocatorias[0]["url"]
     elif len(convocatorias)>1:
      item["errores"].append("Multiples convocatorias: requieren revision")
     for base in bases:
      resultado=await asyncio.to_thread(verificar_bases_sin_sesion,base["url"])
      item["bases_verificadas"].append({**base,**resultado})
     if len(bases)==1 and item["bases_verificadas"][0]["estado"]=="verificado_sin_sesion":
      item["url_bases_candidata"]=bases[0]["url"]
      item["estado_enlace"]="verificado_sin_sesion"
     elif len(bases)>1:
      item["estado_enlace"]="multiples_bases_requiere_revision"
      item["errores"].append("Multiples enlaces de bases: requieren revision")
     elif not bases:
      item["estado_enlace"]="sin_bases"
      item["errores"].append("No se encontro enlace oficial de bases")
     else:
      item["estado_enlace"]="verificacion_fallida"
      item["errores"].append("Enlace de bases no confirmado sin sesion")
     controles=await page.evaluate("""() => [...document.querySelectorAll('a,button,input[type=button]')].filter(e=>{const t=(e.innerText||e.value||e.title||'').trim();return /BASES|ANEXOS|resumen de conv/i.test(t) && e.id && e.offsetParent!==null}).map(e=>({id:e.id,texto:(e.innerText||e.value||e.title||'').trim()}))""")
     vistos=set()
     for control in controles:
      if control["id"] in vistos:continue
      vistos.add(control["id"])
      print("  Documento:",control["texto"][:100])
      try:
       await page.locator('[id="'+control["id"]+'"]').click(timeout=15000)
       await page.wait_for_timeout(2200)
      except Exception as e:item["errores"].append("Control "+control["texto"][:60]+": "+str(e)[:200])
     if not controles:item["errores"].append("No se encontraron controles de bases/anexos/resumen; revisar documentos adicionales de la ficha")
     if descargas:await asyncio.gather(*descargas,return_exceptions=True)
     if not item["archivos"]:item["errores"].append("No se capturaron descargas")
    except Exception as e:
     item["errores"].append(str(e))
     print("  ERROR:",str(e)[:300])
    finally:
     page.remove_listener("download",evento)
     print("  Archivos:",len(item["archivos"]),"| Advertencias:",len(item["errores"]))
  finally:
   destino=SALIDA/"reporte_descargas.json"
   destino.write_text(json.dumps(reporte,ensure_ascii=False,indent=2),encoding="utf-8")
   print("\nReporte:",destino)
   print("TOTAL:",len(reporte["procedimientos"]),"procedimientos,",sum(len(x["archivos"]) for x in reporte["procedimientos"]),"archivos descargados")
   await browser.close()
if __name__=="__main__":asyncio.run(main())
