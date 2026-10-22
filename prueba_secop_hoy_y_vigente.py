"""Prueba de filtro Hoy + Vigente en SECOP Coahuila; sin escrituras externas."""
import asyncio, json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright

URL="https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"
OUT=Path(__file__).with_name("resultado_filtro_hoy_vigente_secop.json")
async def main():
 fecha=datetime.now(ZoneInfo("America/Monterrey")).strftime("%d/%m/%Y")
 resultado={"fecha_esperada":fecha,"pasos":[]}
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(headless=False)
  page=await browser.new_page()
  try:
   r=await page.goto(URL,wait_until="domcontentloaded",timeout=45000)
   if not r or r.status!=200:raise RuntimeError("HTTP distinto de 200")
   await page.locator("#CardView_col2 img[alt='[Filtrar]']").click(timeout=15000)
   await page.locator("#CardView_HFFDE_I").wait_for(state="visible",timeout=20000)
   await page.locator("#CardView_DXHFP_PWC-1").get_by_text("Hoy",exact=True).first.click(timeout=10000)
   await page.wait_for_timeout(500)
   fechas=await page.evaluate("""() => Object.fromEntries(['CardView_HFFDE_I','CardView_HFTDE_I'].map(id=>[id,document.getElementById(id)?.value??null]))""")
   resultado["fechas_tras_hoy"]=fechas
   print("Fechas seleccionadas:",fechas)
   popup=page.locator("#CardView_DXHFP_PW-1")
   if await popup.is_visible():
    aceptar=page.locator("#CardView_DXHFP_TPCFCm1_O_I")
    if await aceptar.is_enabled():await aceptar.click(timeout=10000)
   await page.wait_for_timeout(1200)
   resultado["resumen_tras_fecha"]=await page.locator("#CardView_DXPagerBottom").inner_text()
   print("Después de Hoy:",resultado["resumen_tras_fecha"].strip()[:200])
   await page.locator("#CardView_col3 img[alt='[Filtrar]']").click(timeout=15000)
   await page.locator("#CardView_HFListBox_LBI3T0").wait_for(state="visible",timeout=20000)
   await page.locator("#CardView_HFListBox_LBI3T0").click(timeout=10000)
   await page.wait_for_timeout(1200)
   resultado["resumen_tras_ambos"]=await page.locator("#CardView_DXPagerBottom").inner_text()
   resultado["muestra_tarjetas"]=await page.locator("[id^='CardView_DXCardLayout']").evaluate_all("""es=>es.filter(e=>/^CardView_DXCardLayout\\d+_\\d+$/.test(e.id)).slice(0,12).map(e=>({id:e.id,texto:e.innerText.slice(0,700)}))""")
   print("Después de Hoy + Vigente:",resultado["resumen_tras_ambos"].strip()[:250])
  except Exception as e:
   resultado["error"]=str(e)
   print("Error:",e)
  finally:
   OUT.write_text(json.dumps(resultado,ensure_ascii=False,indent=2),encoding="utf-8")
   print("Reporte:",OUT)
   input("Pulsa ENTER para cerrar Chromium...")
   await browser.close()
if __name__=="__main__":asyncio.run(main())
