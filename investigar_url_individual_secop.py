"""Diagnostico de enlace individual SECOP. Solo lectura, no envia correos.
Ejecutar en Windows con Playwright instalado: py investigar_url_individual_secop.py
"""
import asyncio,json,re
from pathlib import Path
from urllib.parse import urlparse
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parent
URL="https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"
INPUT=ROOT/"secop_hoy_vigentes.json"
OUTPUT=ROOT/"diagnostico_url_individual_secop.json"

async def main():
 if not INPUT.exists():raise SystemExit("Falta secop_hoy_vigentes.json en la misma carpeta")
 data=json.loads(INPUT.read_text(encoding="utf-8-sig"))
 registros=data.get("registros",[])[:3]
 reporte={"nota":"Exploracion tecnica, no confirma enlace permanente","procedimientos":[]}
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=False)
  context=await browser.new_context(accept_downloads=False)
  page=await context.new_page()
  for r in registros:
   ref=r.get("documentos_referencia")
   item={"codigo":r.get("codigo"),"referencia":ref,"url_antes":None,"url_despues":None,"fragmento":None,"historial":[],
         "solicitudes":[],"vinculos":[],"errores":[]}
   reporte["procedimientos"].append(item)
   if not ref:continue
   def request(req):
    if "secop" in req.url.lower() and len(item["solicitudes"])<100:
     item["solicitudes"].append({"metodo":req.method,"url":req.url.split("?")[0],
      "tipo":req.resource_type,"post_data":(req.post_data or "")[:500] if req.method=="POST" else None})
   page.on("request",request)
   try:
    await page.goto(URL,wait_until="domcontentloaded",timeout=60000)
    await page.locator("#CardView_col2 img[alt='[Filtrar]']").click(timeout=20000)
    await page.locator("#CardView_HFFDE_I").wait_for(state="visible",timeout=20000)
    from datetime import datetime
    fecha=datetime.strptime(r["fecha_publicacion"],"%Y-%m-%d").strftime("%d/%m/%Y")
    await page.locator("#CardView_HFFDE_I").fill(fecha)
    await page.locator("#CardView_HFTDE_I").fill(fecha)
    await page.locator("#CardView_DXHFP_TPCFCm1_O").click(timeout=20000)
    await page.locator("#CardView_col2 img[alt='[Filtrado]']").wait_for(state="attached",timeout=20000)
    await page.wait_for_timeout(1200)
    item["url_antes"]=page.url
    item["vinculos"]=await page.get_by_text(ref,exact=True).first.evaluate("""e=>({outerHTML:e.outerHTML.slice(0,1200),parentHTML:e.parentElement?.outerHTML.slice(0,2500)})""")
    await page.get_by_text(ref,exact=True).first.click(timeout=20000)
    await page.get_by_text("Base de Procedimiento",exact=False).first.wait_for(state="visible",timeout=20000)
    await page.wait_for_timeout(900)
    item["url_despues"]=page.url
    item["fragmento"]=await page.evaluate("""()=>({hash:location.hash,historyState:JSON.stringify(history.state)?.slice(0,1000),title:document.title,
      forms:[...document.forms].map(f=>({action:f.action,method:f.method})).slice(0,8),
      scripts:[...document.querySelectorAll('script[src]')].map(s=>s.src).filter(x=>/secop|procedimiento/i.test(x)).slice(0,20)})""")
    # Detectar si el portal expone una URL individual real en atributos, sin inventarla.
    item["atributos_detalle"]=await page.evaluate("""()=>[...document.querySelectorAll('a[href], [data-url], [data-href]')].filter(e=>e.offsetParent!==null).map(e=>({texto:(e.innerText||'').trim().slice(0,90),href:e.getAttribute('href'),dataUrl:e.getAttribute('data-url'),dataHref:e.getAttribute('data-href')})).filter(x=>/procedimiento|detalle|convocatoria/i.test([x.texto,x.href,x.dataUrl,x.dataHref].join(' '))).slice(0,60)""")
    print(ref,":",item["url_despues"],"solicitudes",len(item["solicitudes"]))
   except Exception as e:
    item["errores"].append(str(e)[:400])
    print("ERROR",ref,str(e)[:160])
   finally:page.remove_listener("request",request)
  OUTPUT.write_text(json.dumps(reporte,ensure_ascii=False,indent=2),encoding="utf-8")
  print("Reporte:",OUTPUT)
  input("Presiona ENTER para cerrar el navegador...")
  await browser.close()
if __name__=="__main__":asyncio.run(main())
