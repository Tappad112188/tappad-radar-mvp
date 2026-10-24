"""Diagnostico de todos los enlaces Detalles y su relacion con tarjetas SECOP.
Solo lectura; no modifica datos ni descarga documentos.
Uso: py localizar_detalles_secop.py
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
  page=await browser.new_page()
  for r in data.get("registros",[])[:3]:
   ref=r.get("documentos_referencia")
   item={"referencia":ref,"url":None,"detalles_globales":[],"estructura_tarjeta":[],"errores":[]}
   out["procedimientos"].append(item)
   try:
    await page.goto(URL,wait_until="domcontentloaded",timeout=60000)
    await page.locator("#CardView_col2 img[alt='[Filtrar]']").click(timeout=20000)
    await page.locator("#CardView_HFFDE_I").wait_for(state="visible",timeout=20000)
    fecha=datetime.strptime(r["fecha_publicacion"],"%Y-%m-%d").strftime("%d/%m/%Y")
    await page.locator("#CardView_HFFDE_I").fill(fecha)
    await page.locator("#CardView_HFTDE_I").fill(fecha)
    await page.locator("#CardView_DXHFP_TPCFCm1_O").click(timeout=20000)
    await page.locator("#CardView_col2 img[alt='[Filtrado]']").wait_for(state="attached",timeout=20000)
    await page.get_by_text(ref,exact=True).first.wait_for(state="visible",timeout=20000)
    item["url"]=page.url
    item["detalles_globales"]=await page.evaluate("""()=>[...document.querySelectorAll('a,button,[role=button]')].filter(e=>(e.innerText||'').trim().toLowerCase()==='detalles').map(e=>({html:e.outerHTML.slice(0,1400),visible:!!e.getClientRects().length,ancestros:(()=>{let a=[],n=e;for(let i=0;i<9&&n;i++,n=n.parentElement)a.push({tag:n.tagName,id:n.id,clase:String(n.className).slice(0,150),texto:(n.innerText||'').slice(0,180)});return a})()})).slice(0,25)""")
    item["estructura_tarjeta"]=await page.get_by_text(ref,exact=True).first.evaluate("""e=>{let a=[],n=e;for(let i=0;i<15&&n;i++,n=n.parentElement){a.push({nivel:i,tag:n.tagName,id:n.id,clase:String(n.className).slice(0,150),texto:(n.innerText||'').slice(0,350),enlaces:[...n.querySelectorAll('a[href]')].slice(0,12).map(x=>({texto:(x.innerText||'').slice(0,60),href:x.getAttribute('href')}))});}return a}""")
    print(ref,":",len(item["detalles_globales"]),"botones Detalles")
   except Exception as e:item["errores"].append(str(e)[:500])
  path=BASE/"diagnostico_estructura_detalles_secop.json"
  path.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
  print("Archivo:",path)
  await browser.close()
if __name__=="__main__":asyncio.run(main())
