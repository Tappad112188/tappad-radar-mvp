"""Diagnóstico de controles de fecha de SECOP (solo lectura)."""
import asyncio, json
from pathlib import Path
from playwright.async_api import async_playwright

URL="https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"
OUT=Path(__file__).with_name("diagnostico_filtro_fechas_secop.json")
JS="""() => ({
 encabezados:[...document.querySelectorAll('[id^="CardView_col"],th')].map(e=>({id:e.id,texto:(e.innerText||'').trim().slice(0,120),html:e.outerHTML.slice(0,700)})).filter(x=>x.texto||/fecha|filter|filtr/i.test(x.html)).slice(0,40),
 fechas:[...document.querySelectorAll('[id*="HFF"],[id*="HFT"],[id*="Filter"],[id*="HF"],input')].filter(e=>/fecha|HFF|HFT|Filter|CardView/i.test((e.id||'')+' '+(e.outerHTML||''))).slice(0,90).map(e=>({id:e.id,visible:!!(e.offsetWidth||e.offsetHeight||e.getClientRects().length),html:e.outerHTML.slice(0,650)})),
 iconos:[...document.querySelectorAll('#CardView img[alt],img[alt*="Filtrar"]')].map(e=>({id:e.id,alt:e.alt,parent:e.parentElement?.outerHTML.slice(0,650)})).slice(0,40)
})"""
async def main():
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(headless=False)
  page=await browser.new_page()
  try:
   response=await page.goto(URL,wait_until="domcontentloaded",timeout=45000)
   print("HTTP:",response.status if response else "sin respuesta")
   await page.wait_for_timeout(2000)
   datos={"antes":await page.evaluate(JS),"clics":[]}
   # Probar iconos de filtro de columnas relacionadas con fecha, sin enviar consultas.
   candidatos=await page.locator("[id^='CardView_col']").evaluate_all("""es=>es.map(e=>({id:e.id,texto:(e.innerText||'').trim()}))""")
   for col in candidatos:
    if "fecha" not in col["texto"].lower():continue
    try:
     icon=page.locator("#"+col["id"]+" img[alt='[Filtrar]']")
     if await icon.count():
      await icon.click(timeout=5000)
      await page.wait_for_timeout(700)
      datos["clics"].append({"columna":col,"despues":await page.evaluate(JS)})
      await page.keyboard.press("Escape")
    except Exception as e:
     datos["clics"].append({"columna":col,"error":str(e)[:400]})
   OUT.write_text(json.dumps(datos,ensure_ascii=False,indent=2),encoding="utf-8")
   print("Archivo:",OUT)
   print("Columnas de fecha examinadas:",len(datos["clics"]))
   input("Pulsa ENTER para cerrar...")
  finally:await browser.close()
if __name__=="__main__":asyncio.run(main())
