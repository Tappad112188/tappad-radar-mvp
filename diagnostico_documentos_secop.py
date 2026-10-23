"""Diagnóstico de descarga de documentos de un expediente SECOP Coahuila.
SOLO LECTURA. Abre el expediente LPN-CO-E099-2026, registra solicitudes y
descargas sin acceder a servicios privados ni enviar datos a terceros.
"""
import asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright
URL="https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"
CODIGO="LPN-CO-E099-2026"
ID="OtherDocumentsHyperLink_16086_16008"
BASE=Path(__file__).resolve().parent
OUT=BASE/"diagnostico_documentos_secop.json"
DESC=BASE/"descargas_prueba_secop"
async def main():
 reporte={"codigo":CODIGO,"referencia_documental":"SIDUM-LPN-CO-E099-2026","acciones":[],"descargas":[],"paginas_nuevas":[],"solicitudes":[]}
 DESC.mkdir(exist_ok=True)
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(headless=False)
  context=await browser.new_context(accept_downloads=True)
  page=await context.new_page()
  def on_download(d):
   reporte["descargas"].append({"nombre":d.suggested_filename,"url":d.url})
   async def guardar():
    try:
     destino=DESC/Path(d.suggested_filename).name
     if destino.exists():destino=DESC/("copia_"+destino.name)
     await d.save_as(destino)
     reporte["descargas"][-1]["archivo"]=str(destino)
    except Exception as e:reporte["descargas"][-1]["error"]=str(e)
   tareas.append(asyncio.create_task(guardar()))
  def on_page(p):
   reporte["paginas_nuevas"].append({"url_inicial":p.url})
   async def leer():
    try:
     await p.wait_for_load_state("domcontentloaded",timeout=12000)
     reporte["paginas_nuevas"][-1]["url_final"]=p.url
     reporte["paginas_nuevas"][-1]["titulo"]=await p.title()
    except Exception as e:reporte["paginas_nuevas"][-1]["error"]=str(e)
   tareas.append(asyncio.create_task(leer()))
  tareas=[]
  context.on("download",on_download)
  context.on("page",on_page)
  page.on("request",lambda req:reporte["solicitudes"].append({"metodo":req.method,"url":req.url.split("?")[0][:220]}) if req.resource_type in ("document","xhr","fetch") and len(reporte["solicitudes"])<80 else None)
  try:
   r=await page.goto(URL,wait_until="domcontentloaded",timeout=45000)
   if not r or r.status!=200:raise RuntimeError("SECOP no respondió HTTP 200")
   await page.locator("#CardView_col2 img[alt='[Filtrar]']").click(timeout=15000)
   await page.locator("#CardView_HFFDE_I").wait_for(state="visible",timeout=20000)
   await page.locator("#CardView_HFFDE_I").fill("22/10/2026")
   await page.locator("#CardView_HFTDE_I").fill("22/10/2026")
   await page.locator("#CardView_DXHFP_TPCFCm1_O").click(timeout=15000)
   await page.locator("#CardView_col2 img[alt='[Filtrado]']").wait_for(state="attached",timeout=20000)
   await page.wait_for_timeout(1600)
   texto=await page.locator("body").inner_text()
   if CODIGO not in texto:raise RuntimeError("No aparece el procedimiento esperado; no se pulsará ningún documento")
   link=page.locator("#"+ID)
   await link.wait_for(state="visible",timeout=15000)
   reporte["acciones"].append({"paso":"antes_de_clic","texto":(await link.inner_text()).strip(),"html":(await link.evaluate("(e)=>e.outerHTML"))[:1500]})
   await link.click(timeout=15000)
   await page.wait_for_timeout(5000)
   reporte["acciones"].append({"paso":"despues_de_clic","url":page.url,"texto_visible":(await page.locator("body").inner_text())[-1800:]})
   if tareas:await asyncio.gather(*tareas,return_exceptions=True)
  except Exception as e:
   reporte["error"]=str(e)
   print("Error:",e)
  finally:
   OUT.write_text(json.dumps(reporte,ensure_ascii=False,indent=2),encoding="utf-8")
   print("Diagnóstico:",OUT)
   print("Descargas:",len(reporte["descargas"]),"Pestañas nuevas:",len(reporte["paginas_nuevas"]))
   input("Pulsa ENTER para cerrar Chromium...")
   await browser.close()
if __name__=="__main__":asyncio.run(main())
