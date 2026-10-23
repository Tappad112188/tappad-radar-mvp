"""Diagnóstico de estado de filtros SECOP tras Aceptar y al abrir Estatus.
Solo lectura: no modifica bases ni envía correos.
"""
import asyncio,json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright
URL="https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"
OUT=Path(__file__).with_name("diagnostico_filtros_secop_v4.json")
JS="""() => {
const p=document.querySelector('#CardView_DXHFP_PW-1');
const popup=!!p&&getComputedStyle(p).display!=='none';
return {
 popup,popup_texto:popup?(p.innerText||'').slice(0,1700):'',
 pager:document.querySelector('#CardView_DXPagerBottom')?.innerText?.slice(0,300)||'',
 fecha_desde:document.querySelector('#CardView_HFFDE_I')?.value??null,
 fecha_hasta:document.querySelector('#CardView_HFTDE_I')?.value??null,
 opciones:[...(p?.querySelectorAll('tr,li,[id*="HFListBox"],[id*="HFList"]')||[])].filter(e=>/Vigente|Adjudicado|Cancelado|Anulado/i.test(e.innerText||'')).slice(-25).map(e=>({id:e.id,texto:(e.innerText||'').slice(0,120),html:e.outerHTML.slice(0,500)})),
 filtros:[...document.querySelectorAll('#CardView_col2,#CardView_col3')].map(e=>({id:e.id,html:e.outerHTML.slice(0,900)})),
 tarjetas:[...document.querySelectorAll('[id^="CardView_DXCardLayout"]')].filter(e=>/^CardView_DXCardLayout\\d+_\\d+$/.test(e.id)).slice(0,4).map(e=>e.parentElement?.innerText?.slice(0,600)||'')
}}"""
async def main():
 hoy=datetime.now(ZoneInfo("America/Monterrey")).strftime("%d/%m/%Y")
 data={"fecha":hoy,"pasos":[]}
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(headless=False)
  page=await browser.new_page()
  async def capturar(nombre):
   await page.wait_for_timeout(1400)
   d=await page.evaluate(JS)
   data["pasos"].append({"paso":nombre,**d})
   print(nombre,"popup:",d["popup"],"pager:",d["pager"][:90],"opciones:",len(d["opciones"]))
  try:
   response=await page.goto(URL,wait_until="domcontentloaded",timeout=45000)
   print("HTTP:",response.status if response else None)
   await capturar("inicio")
   await page.locator("#CardView_col2 img[alt='[Filtrar]']").click()
   await page.locator("#CardView_HFFDE_I").wait_for(state="visible",timeout=20000)
   await page.locator("#CardView_HFFDE_I").fill(hoy)
   await page.locator("#CardView_HFTDE_I").fill(hoy)
   await capturar("fechas_introducidas")
   await page.locator("#CardView_DXHFP_TPCFCm1_O").click(timeout=12000)
   await page.wait_for_timeout(4000)
   await capturar("despues_aceptar_4s")
   await page.locator("#CardView_col3 img[alt='[Filtrar]']").click(timeout=12000)
   await page.locator("#CardView_DXHFP_PW-1").wait_for(state="visible",timeout=15000)
   await page.wait_for_timeout(3500)
   await capturar("menu_estatus_abierto_3s")
  except Exception as e:
   data["error"]=str(e)
   print("Error:",e)
  finally:
   OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
   print("Reporte:",OUT)
   input("Pulsa ENTER para cerrar Chromium...")
   await browser.close()
if __name__=="__main__":asyncio.run(main())
