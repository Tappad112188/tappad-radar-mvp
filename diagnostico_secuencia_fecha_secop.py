"""Diagnóstico controlado del filtro de fechas de SECOP, sin escritura externa."""
import asyncio,json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright

URL="https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"
OUT=Path(__file__).with_name("diagnostico_secuencia_fecha_secop.json")
JS="""() => ({
 popup: (()=>{let e=document.querySelector('#CardView_DXHFP_PW-1');return !!e&&getComputedStyle(e).display!=='none'&&getComputedStyle(e).visibility!=='hidden'})(),
 desde:document.querySelector('#CardView_HFFDE_I')?.value??null,
 hasta:document.querySelector('#CardView_HFTDE_I')?.value??null,
 aceptar_visible:(()=>{let e=document.querySelector('#CardView_DXHFP_TPCFCm1_O_I');return !!e&&!!e.getClientRects().length})(),
 aceptar_disabled:document.querySelector('#CardView_DXHFP_TPCFCm1_O_I')?.disabled??null,
 pager:document.querySelector('#CardView_DXPagerBottom')?.innerText?.slice(0,350)||'',
 tarjetas:[...document.querySelectorAll('[id^="CardView_DXCardLayout"]')].filter(e=>/^CardView_DXCardLayout\\d+_\\d+$/.test(e.id)).slice(0,2).map(e=>e.innerText.slice(0,500))
})"""
async def main():
 hoy=datetime.now(ZoneInfo("America/Monterrey")).strftime("%d/%m/%Y")
 r={"fecha":hoy,"eventos":[]}
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(headless=False)
  page=await browser.new_page()
  try:
   response=await page.goto(URL,wait_until="domcontentloaded",timeout=45000)
   print("HTTP:",response.status if response else "sin respuesta")
   async def guardar(nombre):
    await page.wait_for_timeout(650)
    estado=await page.evaluate(JS)
    r["eventos"].append({"paso":nombre,**estado})
    print(nombre,"popup:",estado["popup"],"desde:",estado["desde"],"hasta:",estado["hasta"],"aceptar_visible:",estado["aceptar_visible"])
   await page.locator("#CardView_col2 img[alt='[Filtrar]']").click()
   await page.locator("#CardView_HFFDE_I").wait_for(state="visible",timeout=20000)
   await guardar("menu_abierto")
   await page.locator("#CardView_HFFDE_I").fill(hoy)
   await guardar("desde_fill")
   await page.locator("#CardView_HFTDE_I").fill(hoy)
   await guardar("hasta_fill_sin_tab")
   boton=page.locator("#CardView_DXHFP_TPCFCm1_O_I")
   if await boton.is_visible() and await boton.is_enabled():
    await boton.click(timeout=8000)
    await guardar("aceptar_click")
   else:
    await page.locator("#CardView_HFTDE_I").press("Tab")
    await guardar("tab_hasta")
   if not (await page.evaluate(JS))["popup"]:
    await page.locator("#CardView_col2 img[alt='[Filtrar]']").click()
    await page.locator("#CardView_HFFDE_I").wait_for(state="visible",timeout=20000)
    await guardar("reabrir_para_verificar")
  except Exception as e:
   r["error"]=str(e)
   print("Error:",e)
  finally:
   OUT.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
   print("Reporte:",OUT)
   input("Pulsa ENTER para cerrar Chromium...")
   await browser.close()
if __name__=="__main__":asyncio.run(main())
