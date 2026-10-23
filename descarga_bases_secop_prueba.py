"""Diagnostica y descarga los archivos públicos visibles del expediente SECOP.
Solo lectura; no envía correos ni escribe en Supabase.
"""
import asyncio,json,re
from pathlib import Path
from playwright.async_api import async_playwright
URL="https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"
CODIGO="LPN-CO-E099-2026"
BASE=Path(__file__).resolve().parent
OUT=BASE/"resultado_descarga_bases_secop.json"
DEST=BASE/"documentos_secop_prueba"
async def main():
 DEST.mkdir(exist_ok=True)
 reporte={"codigo":CODIGO,"archivos":[],"controles":[],"errores":[]}
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(headless=False)
  context=await browser.new_context(accept_downloads=True)
  page=await context.new_page()
  tareas=[]
  async def guardar(d):
   try:
    nombre=Path(d.suggested_filename).name
    destino=DEST/nombre
    if destino.exists():destino=DEST/("nuevo_"+nombre)
    await d.save_as(destino)
    reporte["archivos"].append({"nombre":nombre,"ruta":str(destino),"bytes":destino.stat().st_size})
    print("Descargado:",destino)
   except Exception as e:reporte["errores"].append("Descarga: "+str(e))
  context.on("download",lambda d:tareas.append(asyncio.create_task(guardar(d))))
  try:
   response=await page.goto(URL,wait_until="domcontentloaded",timeout=45000)
   if not response or response.status!=200:raise RuntimeError("SECOP no respondió HTTP 200")
   await page.locator("#CardView_col2 img[alt='[Filtrar]']").click()
   await page.locator("#CardView_HFFDE_I").wait_for(state="visible",timeout=20000)
   await page.locator("#CardView_HFFDE_I").fill("22/10/2026")
   await page.locator("#CardView_HFTDE_I").fill("22/10/2026")
   await page.locator("#CardView_DXHFP_TPCFCm1_O").click()
   await page.locator("#CardView_col2 img[alt='[Filtrado]']").wait_for(state="attached",timeout=20000)
   await page.wait_for_timeout(1500)
   if CODIGO not in await page.locator("body").inner_text():raise RuntimeError("Procedimiento no localizado")
   await page.locator("#OtherDocumentsHyperLink_16086_16008").click(timeout=15000)
   await page.get_by_text("Base de Procedimiento",exact=False).first.wait_for(state="visible",timeout=20000)
   await page.wait_for_timeout(1000)
   enlaces=await page.evaluate("""() => [...document.querySelectorAll('a,button,input[type=button]')].filter(e=>{const t=(e.innerText||e.value||e.title||'').trim();return /BASES Y ANEXOS|resumen de conv/i.test(t)}).map(e=>({tag:e.tagName,id:e.id,texto:(e.innerText||e.value||'').trim(),html:e.outerHTML.slice(0,1600)}))""")
   reporte["controles"]=enlaces
   print("Controles documentales:",len(enlaces))
   for e in enlaces:
    if not e["id"]:
     reporte["errores"].append("Control sin ID: "+e["texto"])
     continue
    print("Intentando descarga:",e["texto"])
    try:
     await page.locator("[id='"+e["id"]+"']").click(timeout=12000)
     await page.wait_for_timeout(3500)
    except Exception as err:reporte["errores"].append(e["texto"]+": "+str(err))
   if tareas:await asyncio.gather(*tareas,return_exceptions=True)
  except Exception as e:
   reporte["error"]=str(e)
   print("Error:",e)
  finally:
   OUT.write_text(json.dumps(reporte,ensure_ascii=False,indent=2),encoding="utf-8")
   print("Reporte:",OUT)
   print("Archivos descargados:",len(reporte["archivos"]))
   input("Pulsa ENTER para cerrar Chromium...")
   await browser.close()
if __name__=="__main__":asyncio.run(main())
