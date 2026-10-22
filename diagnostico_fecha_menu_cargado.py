"""Inspecciona el menú de fecha tras esperar a que DevExpress termine de cargar.
Solo lectura. No modifica filtros ni Supabase.
"""
import asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright
URL="https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"
OUT=Path(__file__).with_name("diagnostico_fecha_menu_cargado.json")
JS="""() => {
const p=document.querySelector('#CardView_DXHFP_PW-1');
return {popup_visible:!!p && getComputedStyle(p).display!=='none',
 texto:(p?.innerText||'').slice(0,5000),
 contenido_html:(document.querySelector('#CardView_DXHFP_PWC-1')?.innerHTML||'').slice(0,18000),
 controles:[...(p?.querySelectorAll('input,select,button,[role="button"],[id]')||[])].map(e=>({tag:e.tagName,id:e.id,tipo:e.type||'',valor:e.value||'',texto:(e.innerText||'').slice(0,100),html:e.outerHTML.slice(0,650)})).slice(0,100),
 posibles_fechas:[...document.querySelectorAll('[id*="HFF"],[id*="HFT"]')].map(e=>({id:e.id,html:e.outerHTML.slice(0,500)})).slice(0,40)};
}"""
async def main():
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(headless=False)
  page=await browser.new_page()
  try:
   r=await page.goto(URL,wait_until="domcontentloaded",timeout=45000)
   print("HTTP:",r.status if r else "sin respuesta")
   await page.locator("#CardView_col2 img[alt='[Filtrar]']").click(timeout=15000)
   await page.locator("#CardView_DXHFP_PW-1").wait_for(state="visible",timeout=15000)
   for intento in range(15):
    await page.wait_for_timeout(600)
    estado=await page.evaluate(JS)
    if "Cargando" not in estado["texto"] and estado["controles"]:
     break
   datos={"espera_segundos":(intento+1)*0.6,"estado":estado}
   OUT.write_text(json.dumps(datos,ensure_ascii=False,indent=2),encoding="utf-8")
   print("Espera:",datos["espera_segundos"],"segundos")
   print("Texto del filtro:",repr(estado["texto"][:400]))
   print("Controles:",len(estado["controles"]))
   print("Reporte:",OUT)
   input("Pulsa ENTER para cerrar...")
  finally:await browser.close()
if __name__=="__main__":asyncio.run(main())
