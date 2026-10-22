"""Prueba corregida: fecha local del día y estatus Vigente en SECOP Coahuila.
Solo lectura; no envía correos ni modifica bases de datos.
"""
import asyncio, json, re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright

URL="https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"
OUT=Path(__file__).with_name("resultado_filtro_hoy_vigente_secop_v2.json")
EXTRAER="""cards=>cards.map(card=>{
 const x={};
 for(const item of card.querySelectorAll('[id^="CardView_DXCardLayout"]')){
  if(!/^CardView_DXCardLayout\\d+_\\d+$/.test(item.id))continue;
  const c=item.querySelector('[id$="_Cap"]');
  const key=(c?.textContent||'').replace(/:\\s*$/,'').trim();
  const val=item.querySelector('td.dxflNestedControlCell_SoftOrange');
  if(key&&val)x[key]=(val.innerText||'').trim();
 }
 return x;
})"""
async def main():
 hoy=datetime.now(ZoneInfo("America/Monterrey")).strftime("%d/%m/%Y")
 reporte={"fecha_solicitada":hoy,"filtro":"Hoy + Vigente","pasos":[]}
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(headless=False)
  page=await browser.new_page()
  try:
   response=await page.goto(URL,wait_until="domcontentloaded",timeout=45000)
   if not response or response.status!=200:raise RuntimeError("SECOP no respondió HTTP 200")
   await page.locator("#CardView_col2 img[alt='[Filtrar]']").click(timeout=15000)
   for sel in ("#CardView_HFFDE_I","#CardView_HFTDE_I"):
    campo=page.locator(sel)
    await campo.wait_for(state="visible",timeout=20000)
    await campo.fill(hoy)
    await campo.press("Tab")
    await page.wait_for_timeout(250)
   reporte["fechas_escritas"]={s:await page.locator(s).input_value() for s in ("#CardView_HFFDE_I","#CardView_HFTDE_I")}
   print("Fechas:",reporte["fechas_escritas"])
   await page.locator("#CardView_DXHFP_TPCFCm1_O_I").click(timeout=15000)
   await page.wait_for_timeout(1400)
   reporte["resumen_tras_fecha"]=await page.locator("#CardView_DXPagerBottom").inner_text()
   print("Después de fecha:",reporte["resumen_tras_fecha"].strip()[:180])
   await page.locator("#CardView_col3 img[alt='[Filtrar]']").click(timeout=15000)
   await page.locator("#CardView_HFListBox_LBI3T0").wait_for(state="visible",timeout=20000)
   await page.locator("#CardView_HFListBox_LBI3T0").click(timeout=15000)
   await page.wait_for_timeout(1300)
   reporte["resumen_tras_ambos"]=await page.locator("#CardView_DXPagerBottom").inner_text()
   summary=re.search(r"Página\\s+\\d+\\s+de\\s+(\\d+)\\s+\\((\\d+)\\s+elementos\\)",reporte["resumen_tras_ambos"],re.I)
   paginas=int(summary.group(1)) if summary else 1
   if paginas>100:raise RuntimeError("Paginación excesiva")
   registros=[]
   for n in range(1,paginas+1):
    if n>1:
     await page.locator(f"#CardView_DXPagerBottom a.dxp-num[onclick*=\\\"'PN{n-1}'\\\"]").click(timeout=15000)
     await page.wait_for_function("(x)=>document.querySelector('#CardView_DXPagerBottom .dxp-current')?.textContent?.trim()===String(x)",arg=n,timeout=20000)
    for x in await page.locator("td[id^='CardView_DXDataCard']").evaluate_all(EXTRAER):
     registros.append({"codigo":(x.get("Código") or "").strip(),"fecha":(x.get("Fecha de Publicación") or "").strip(),"estatus":(x.get("Estatus") or "").strip(),"descripcion":(x.get("Descripción") or "").strip()})
   reporte["registros_recibidos"]=registros
   reporte["total_recibido"]=len(registros)
   reporte["registros_validos"]=[x for x in registros if x["fecha"]==hoy and x["estatus"].casefold()=="vigente"]
   reporte["filtros_confirmados"]=len(reporte["registros_validos"])==len(registros) and (not summary or len(registros)==int(summary.group(2)))
   print("Total:",len(registros),"válidos:",len(reporte["registros_validos"]))
   print("Filtros consistentes:",reporte["filtros_confirmados"])
  except Exception as e:
   reporte["error"]=str(e)
   print("Error:",e)
  finally:
   OUT.write_text(json.dumps(reporte,ensure_ascii=False,indent=2),encoding="utf-8")
   print("Reporte:",OUT)
   input("Pulsa ENTER para cerrar Chromium...")
   await browser.close()
if __name__=="__main__":asyncio.run(main())
