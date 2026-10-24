"""TAPPAD Radar: descarga documentos de los procedimientos SECOP ya filtrados.
Solo lectura; no modifica bases de datos ni envía correos.
Uso: py descargar_documentos_secop_lote.py
"""
import asyncio, json, re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright

BASE=Path(__file__).resolve().parent
ENTRADA=BASE/"secop_hoy_vigentes.json"
SALIDA=BASE/"documentos_secop_lote"
URL="https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"

def nombre_seguro(s):
 return re.sub(r"[^A-Za-z0-9._-]+","_",s).strip("._")[:110] or "archivo"

async def main():
 if not ENTRADA.exists():
  print("ERROR: No existe",ENTRADA)
  return
 data=json.loads(ENTRADA.read_text(encoding="utf-8-sig"))
 hoy=datetime.now(ZoneInfo("America/Monterrey")).date().isoformat()
 registros=[r for r in data.get("registros",[]) if r.get("fecha_publicacion")==data.get("fecha_consulta") and r.get("estatus","").casefold()=="vigente"]
 if not data.get("filtros_aplicados") or data.get("errores") or not registros:
  print("ERROR: El archivo no contiene procedimientos válidos y filtrados.")
  return
 if data.get("fecha_consulta")!=hoy:
  print("AVISO: Archivo de fecha",data.get("fecha_consulta"),"y hoy es",hoy,". Se usarán solo los registros del archivo.")
 SALIDA.mkdir(exist_ok=True)
 reporte={"fecha_fuente":data.get("fecha_consulta"),"procedimientos":[],"errores":[]}
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(headless=False)
  context=await browser.new_context(accept_downloads=True)
  page=await context.new_page()
  try:
   for r in registros:
    codigo=r["codigo"]
    item={"codigo":codigo,"referencia":r.get("documentos_referencia"),"archivos":[],"enlaces_documentos":[],"url_bases_candidata":None,"estado_enlace":"pendiente_verificacion_externa","errores":[]}
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
     bases=[e for e in item["enlaces_documentos"] if "BASES" in e["texto"].upper()]
     if len(bases)==1:
      item["url_bases_candidata"]=bases[0]["url"]
      item["estado_enlace"]="capturado_pendiente_verificacion_externa"
     elif len(bases)>1:
      item["errores"].append("Multiples enlaces de bases: requieren revision")
     else:
      item["errores"].append("No se encontro enlace oficial de bases")
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
     if not controles:item["errores"].append("No se encontraron controles de bases/anexos/resumen")
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
   input("Pulsa ENTER para cerrar Chromium...")
   await browser.close()
if __name__=="__main__":asyncio.run(main())
