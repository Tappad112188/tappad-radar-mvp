"""Investiga el boton Detalles de SECOP sin descargar archivos ni escribir datos.
Uso: py investigar_detalles_secop.py
"""
import asyncio,json
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
ROOT=Path(__file__).resolve().parent
INPUT=ROOT/"secop_hoy_vigentes.json"
OUTPUT=ROOT/"diagnostico_detalles_secop.json"
URL="https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"
async def main():
 data=json.loads(INPUT.read_text(encoding="utf-8-sig"))
 reporte={"procedimientos":[]}
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=False)
  context=await browser.new_context(accept_downloads=False)
  page=await context.new_page()
  for r in data.get("registros",[])[:3]:
   ref=r.get("documentos_referencia")
   item={"referencia":ref,"codigo":r.get("codigo"),"url_antes":None,"url_despues":None,"detalles":[],"solicitudes":[],"popups":[],"errores":[]}
   reporte["procedimientos"].append(item)
   if not ref:continue
   def request(req):
    if req.resource_type in ("xhr","fetch","document") and len(item["solicitudes"])<40:
     item["solicitudes"].append({"metodo":req.method,"url":req.url.split("?")[0],"post_data":(req.post_data or "")[:800] if req.method=="POST" else None})
   page.on("request",request)
   def popup(pg):item["popups"].append(pg.url)
   context.on("page",popup)
   try:
    await page.goto(URL,wait_until="domcontentloaded",timeout=60000)
    await page.locator("#CardView_col2 img[alt='[Filtrar]']").click(timeout=20000)
    await page.locator("#CardView_HFFDE_I").wait_for(state="visible",timeout=20000)
    fecha=datetime.strptime(r["fecha_publicacion"],"%Y-%m-%d").strftime("%d/%m/%Y")
    await page.locator("#CardView_HFFDE_I").fill(fecha)
    await page.locator("#CardView_HFTDE_I").fill(fecha)
    await page.locator("#CardView_DXHFP_TPCFCm1_O").click(timeout=20000)
    await page.locator("#CardView_col2 img[alt='[Filtrado]']").wait_for(state="attached",timeout=20000)
    await page.wait_for_timeout(1200)
    target=page.get_by_text(ref,exact=True).first
    await target.wait_for(state="visible",timeout=20000)
    # Captura los botones Detalles del renglon o tarjeta del procedimiento, sin asumir cual corresponde.
    item["detalles"]=await target.evaluate("""e=>{let n=e;const a=[];for(let i=0;i<6&&n;i++,n=n.parentElement){a.push({nivel:i,html:n.outerHTML.slice(0,3500),detalles:[...n.querySelectorAll('a')].filter(x=>(x.innerText||'').trim()==='Detalles').map(x=>({id:x.id,onclick:x.getAttribute('onclick'),href:x.getAttribute('href')}))});}return a}""")
    item["url_antes"]=page.url
    # Clic al primer Detalles dentro del ancestro mas proximo que lo contenga.
    clicked=False
    for d in item["detalles"]:
     if d["detalles"]:
      selector=d["detalles"][0].get("id")
      if selector:
       await page.locator("[id='"+selector+"']").click(timeout=15000)
       clicked=True
       break
    if clicked:
     await page.wait_for_timeout(1700)
     item["url_despues"]=page.url
     item["pagina_visible"]=await page.evaluate("""()=>({titulo:document.title,texto:document.body.innerText.slice(-3000),hash:location.hash})""")
    else:item["errores"].append("No se encontro boton Detalles dentro de los ancestros")
    print(ref,"clic",clicked,"URL",item["url_despues"])
   except Exception as e:item["errores"].append(str(e)[:400])
   finally:
    page.remove_listener("request",request)
    context.remove_listener("page",popup)
  OUTPUT.write_text(json.dumps(reporte,ensure_ascii=False,indent=2),encoding="utf-8")
  print("Resultado:",OUTPUT)
  input("Presiona ENTER para cerrar Chromium...")
  await browser.close()
if __name__=="__main__":asyncio.run(main())
