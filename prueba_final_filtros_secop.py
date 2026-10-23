"""Prueba final SECOP: fecha de hoy y Vigente, con espera por actualización.
No escribe en bases de datos ni envía correos.
"""
import asyncio,json,re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright
URL="https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"
OUT=Path(__file__).with_name("resultado_final_filtros_secop.json")
async def main():
 hoy=datetime.now(ZoneInfo("America/Monterrey")).strftime("%d/%m/%Y")
 reporte={"fecha_consulta":hoy,"pasos":[]}
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(headless=False)
  page=await browser.new_page()
  async def captura(nombre):
   await page.wait_for_timeout(1200)
   d=await page.evaluate("""() => ({paginacion:document.querySelector('#CardView_DXPagerBottom')?.innerText?.slice(0,250)||'',tarjetas:[...document.querySelectorAll('[id^="CardView_DXCardLayout"]')].filter(e=>/^CardView_DXCardLayout\\d+_\\d+$/.test(e.id)).slice(0,10).map(e=>e.parentElement?.innerText?.slice(0,1100)||''),filtro_fecha:document.querySelector('#CardView_col2 img[alt="[Filtrado]"]')!==null,filtro_estatus:document.querySelector('#CardView_col3 img[alt="[Filtrado]"]')!==null})""")
   reporte["pasos"].append({"paso":nombre,**d})
   print(nombre,"paginación:",repr(d["paginacion"][:110]),"tarjetas:",len(d["tarjetas"]),"filtros:",d["filtro_fecha"],d["filtro_estatus"])
  try:
   response=await page.goto(URL,wait_until="domcontentloaded",timeout=45000)
   if not response or response.status!=200:raise RuntimeError("Respuesta HTTP no válida")
   await captura("inicio")
   await page.locator("#CardView_col2 img[alt='[Filtrar]']").click()
   await page.locator("#CardView_HFFDE_I").wait_for(state="visible",timeout=20000)
   await page.locator("#CardView_HFFDE_I").fill(hoy)
   await page.locator("#CardView_HFTDE_I").fill(hoy)
   await page.locator("#CardView_DXHFP_TPCFCm1_O").click(timeout=15000)
   await page.locator("#CardView_col2 img[alt='[Filtrado]']").wait_for(state="attached",timeout=20000)
   await captura("fecha_aplicada")
   await page.locator("#CardView_col3 img[alt='[Filtrar]']").click(timeout=15000)
   vigente=page.locator("#CardView_HFListBox_LBI3T0")
   await vigente.wait_for(state="visible",timeout=25000)
   await vigente.click(timeout=15000)
   await page.locator("#CardView_col3 img[alt='[Filtrado]']").wait_for(state="attached",timeout=20000)
   await captura("fecha_y_vigente_aplicados")
   reporte["filtros_activos"]=reporte["pasos"][-1]["filtro_fecha"] and reporte["pasos"][-1]["filtro_estatus"]
  except Exception as e:
   reporte["error"]=str(e)
   print("Error:",e)
  finally:
   OUT.write_text(json.dumps(reporte,ensure_ascii=False,indent=2),encoding="utf-8")
   print("Reporte:",OUT)
   input("Pulsa ENTER para cerrar Chromium...")
   await browser.close()
if __name__=="__main__":asyncio.run(main())
