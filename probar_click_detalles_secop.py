"""Comprueba el efecto del boton Detalles en cada tarjeta de SECOP.
No descarga archivos, no modifica registros. Uso: py probar_click_detalles_secop.py
"""
import asyncio,json
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
BASE=Path(__file__).resolve().parent
URL="https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"
async def main():
 data=json.loads((BASE/"secop_hoy_vigentes.json").read_text(encoding="utf-8-sig"))
 out={"procedimientos":[]}
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=False)
  context=await browser.new_context(accept_downloads=False)
  page=await context.new_page()
  for r in data.get("registros",[])[:3]:
   ref=r.get("documentos_referencia")
   item={"referencia":ref,"codigo":r.get("codigo"),"url_antes":None,"url_despues":None,"nuevas_paginas":[],"solicitudes":[],"estado_despues":None,"errores":[]}
   out["procedimientos"].append(item)
   def req(q):
    if q.resource_type in ("xhr","fetch","document") and len(item["solicitudes"])<25:
     item["solicitudes"].append({"metodo":q.method,"url":q.url.split("?")[0],"post_data":(q.post_data or "")[:1000] if q.method=="POST" else None})
   def newpage(pg):item["nuevas_paginas"].append(pg.url)
   page.on("request",req);context.on("page",newpage)
   try:
    await page.goto(URL,wait_until="domcontentloaded",timeout=60000)
    await page.locator("#CardView_col2 img[alt='[Filtrar]']").click(timeout=20000)
    await page.locator("#CardView_HFFDE_I").wait_for(state="visible",timeout=20000)
    fecha=datetime.strptime(r["fecha_publicacion"],"%Y-%m-%d").strftime("%d/%m/%Y")
    await page.locator("#CardView_HFFDE_I").fill(fecha)
    await page.locator("#CardView_HFTDE_I").fill(fecha)
    await page.locator("#CardView_DXHFP_TPCFCm1_O").click(timeout=20000)
    await page.locator("#CardView_col2 img[alt='[Filtrado]']").wait_for(state="attached",timeout=20000)
    target=page.get_by_text(ref,exact=True).first
    await target.wait_for(state="visible",timeout=20000)
    cardid=await target.evaluate("""e=>e.closest('td.dxcvCard_SoftOrange')?.id||null""")
    item["tarjeta"]=cardid
    if not cardid:raise RuntimeError("No se identifico la tarjeta exacta")
    boton=page.locator("[id='"+cardid+"'] a.dxcvCommandItem_SoftOrange").filter(has_text="Detalles")
    if await boton.count()!=1:raise RuntimeError("Boton Detalles no es unico para esta tarjeta")
    item["url_antes"]=page.url
    await boton.click(timeout=15000)
    await page.wait_for_timeout(2000)
    item["url_despues"]=page.url
    item["estado_despues"]=await page.evaluate("""()=>({hash:location.hash,historyState:history.state,
      titulo:document.title,links:[...document.querySelectorAll('a[href]')].filter(e=>e.getClientRects().length).map(e=>({texto:(e.innerText||'').slice(0,90),href:e.getAttribute('href')})).filter(x=>/detalle|procedimiento|convocatoria/i.test(x.texto+' '+x.href)).slice(0,20),
      texto:document.body.innerText.slice(-1700)})""")
    print(ref,"tarjeta",cardid,"url",item["url_despues"])
   except Exception as e:item["errores"].append(str(e)[:500])
   finally:page.remove_listener("request",req);context.remove_listener("page",newpage)
  dest=BASE/"diagnostico_click_detalles_secop.json"
  dest.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
  print("Archivo:",dest)
  await browser.close()
if __name__=="__main__":asyncio.run(main())
