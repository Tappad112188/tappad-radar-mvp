"""Validación controlada del filtro de fecha y Vigente de SECOP. Solo lectura."""
import asyncio,json,re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright
URL="https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"
OUT=Path(__file__).with_name("resultado_secop_fecha_vigente_v3.json")
async def main():
 hoy=datetime.now(ZoneInfo("America/Monterrey")).strftime("%d/%m/%Y")
 datos={"fecha":hoy,"pasos":[]}
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=False)
  page=await browser.new_page()
  async def estado(nombre):
   await page.wait_for_timeout(900)
   x=await page.evaluate("""() => ({pager:document.querySelector('#CardView_DXPagerBottom')?.innerText?.slice(0,250)||'',popup:!!document.querySelector('#CardView_DXHFP_PW-1')&&getComputedStyle(document.querySelector('#CardView_DXHFP_PW-1')).display!=='none',desde:document.querySelector('#CardView_HFFDE_I')?.value??null,hasta:document.querySelector('#CardView_HFTDE_I')?.value??null,aceptar:!!document.querySelector('#CardView_DXHFP_TPCFCm1_O_I')&&!document.querySelector('#CardView_DXHFP_TPCFCm1_O_I').disabled,tarjetas:[...document.querySelectorAll('[id^="CardView_DXCardLayout"]')].filter(e=>/^CardView_DXCardLayout\\d+_\\d+$/.test(e.id)).slice(0,3).map(e=>e.parentElement?.innerText?.slice(0,650)||'')})""")
   datos["pasos"].append({"paso":nombre,**x})
   print(nombre,repr(x["pager"][:80]),"popup",x["popup"],"aceptar",x["aceptar"])
  try:
   r=await page.goto(URL,wait_until="domcontentloaded",timeout=45000)
   print("HTTP:",r.status if r else "sin respuesta")
   await estado("inicio")
   await page.locator("#CardView_col2 img[alt='[Filtrar]']").click()
   await page.locator("#CardView_HFFDE_I").wait_for(state="visible",timeout=20000)
   await page.locator("#CardView_HFFDE_I").fill(hoy)
   await page.locator("#CardView_HFTDE_I").fill(hoy)
   await estado("ambas_fechas")
   aceptar=page.locator("#CardView_DXHFP_TPCFCm1_O")
   await aceptar.click(timeout=12000)
   await estado("fecha_aplicada")
   await page.locator("#CardView_col3 img[alt='[Filtrar]']").click(timeout=15000)
   await page.locator("#CardView_HFListBox_LBI3T0").wait_for(state="visible",timeout=20000)
   await page.locator("#CardView_HFListBox_LBI3T0").click(timeout=12000)
   await estado("fecha_y_vigente")
  except Exception as e:
   datos["error"]=str(e)
   print("Error:",e)
  finally:
   OUT.write_text(json.dumps(datos,ensure_ascii=False,indent=2),encoding="utf-8")
   print("Reporte:",OUT)
   input("Pulsa ENTER para cerrar Chromium...")
   await browser.close()
if __name__=="__main__":asyncio.run(main())
