"""Extractor SECOP Coahuila: fecha local de hoy + Vigente. SOLO LECTURA.
Ejecutar en Windows: py extractor_secop_hoy_vigentes.py
No modifica Supabase, Airtable ni envía correos.
"""
import asyncio, json, re, os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright

URL="https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"
SALIDA=Path(__file__).with_name("secop_hoy_vigentes.json")
EXTRAER="""cards => cards.map(card => {
 const result={};
 for(const item of card.querySelectorAll('[id^="CardView_DXCardLayout"]')){
  if(!/^CardView_DXCardLayout\\d+_\\d+$/.test(item.id))continue;
  const cap=item.querySelector('[id$="_Cap"]');
  const label=(cap?.textContent||'').replace(/:\\s*$/,'').trim();
  const cell=item.querySelector('td.dxflNestedControlCell_SoftOrange');
  if(label&&cell)result[label]=(cell.innerText||'').trim();
 }
 result._enlaces=[...card.querySelectorAll('a')].map(a=>({texto:(a.innerText||'').trim(),id:a.id||'',href:a.getAttribute('href')||'',url_absoluta:a.href||'',onclick:a.getAttribute('onclick')||'',target:a.getAttribute('target')||''}));
 return result;
})"""
def limpio(s):return re.sub(r"\s+"," ",s or "").strip()
def fecha_iso(s):
 try:
  d=datetime.strptime(s,"%d/%m/%Y").date()
  return d.isoformat() if d.year>=2000 else None
 except (ValueError,TypeError):return None

async def main():
 hoy=datetime.now(ZoneInfo("America/Monterrey")).date()
 hoy_texto=hoy.strftime("%d/%m/%Y")
 reporte={"fuente":URL,"fecha_consulta":hoy.isoformat(),"filtros_aplicados":False,"registros":[],"errores":[]}
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(headless=os.environ.get('TAPPAD_HEADLESS', '0') == '1')
  page=await browser.new_page(accept_downloads=False)
  try:
   response=await page.goto(URL,wait_until="domcontentloaded",timeout=45000)
   if not response or response.status!=200:raise RuntimeError("SECOP no respondió HTTP 200")
   await page.locator("#CardView_col2 img[alt='[Filtrar]']").click(timeout=15000)
   await page.locator("#CardView_HFFDE_I").wait_for(state="visible",timeout=20000)
   await page.locator("#CardView_HFFDE_I").fill(hoy_texto)
   await page.locator("#CardView_HFTDE_I").fill(hoy_texto)
   await page.locator("#CardView_DXHFP_TPCFCm1_O").click(timeout=15000)
   await page.locator("#CardView_col2 img[alt='[Filtrado]']").wait_for(state="attached",timeout=20000)
   await page.locator("#CardView_col3 img[alt='[Filtrar]']").click(timeout=15000)
   vigente=page.locator("#CardView_HFListBox_LBI3T0")
   await vigente.wait_for(state="visible",timeout=25000)
   await vigente.click(timeout=15000)
   await page.locator("#CardView_col3 img[alt='[Filtrado]']").wait_for(state="attached",timeout=20000)
   await page.wait_for_timeout(1600)
   reporte["filtros_aplicados"]=True
   summary=page.locator("#CardView_DXPagerBottom .dxp-summary")
   if await summary.count() and await summary.is_visible():
    texto=limpio(await summary.inner_text())
    match=re.search(r"Página\s+\d+\s+de\s+(\d+)\s+\((\d+)\s+elementos\)",texto,re.I)
    if not match:raise RuntimeError("Paginación inesperada: "+texto)
    paginas,total_reportado=map(int,match.groups())
   else:
    paginas=1
    total_reportado=None
   if paginas>100:raise RuntimeError("Más de 100 páginas; detener por seguridad")
   registros=[]
   for n in range(1,paginas+1):
    if n>1:
     await page.locator(f'#CardView_DXPagerBottom a.dxp-num[onclick*="\'PN{n-1}\'"]').click(timeout=15000)
     await page.wait_for_function("(x)=>document.querySelector('#CardView_DXPagerBottom .dxp-current')?.textContent?.trim()===String(x)",arg=n,timeout=20000)
    items=await page.locator("td[id^='CardView_DXDataCard']").evaluate_all(EXTRAER)
    for item in items:
     fecha=limpio(item.get("Fecha de Publicación"))
     r={"codigo":limpio(item.get("Código")),"estatus":limpio(item.get("Estatus")),"descripcion":limpio(item.get("Descripción")),"fecha_publicacion_original":fecha,"fecha_publicacion":fecha_iso(fecha),"documentos_referencia":limpio(item.get("Documentos de Procedimiento")),"enlaces":item.get("_enlaces",[]),"url_procedimiento":None,"estado_enlace":"pendiente_identificar_enlace_individual"}
     registros.append(r)
   validos=[r for r in registros if r["fecha_publicacion"]==hoy.isoformat() and r["estatus"].casefold()=="vigente" and r["codigo"]]
   rechazados=[r for r in registros if r not in validos]
   unicos={r["codigo"]:r for r in validos}
   reporte.update({"total_reportado":total_reportado,"total_extraido":len(registros),"total_validos":len(validos),"total_unicos":len(unicos),"total_rechazados":len(rechazados),"registros":list(unicos.values()),"rechazados":rechazados,"coincide_total":total_reportado is None or len(registros)==total_reportado})
   if rechazados:reporte["errores"].append("SECOP devolvió registros que no cumplen fecha, Vigente o código")
   if not reporte["coincide_total"]:reporte["errores"].append("Total extraído no coincide con paginación")
   print("Procedimientos de hoy y Vigente:",len(unicos),"| Rechazados:",len(rechazados))
  except Exception as e:
   reporte["error"]=str(e)
   print("Error:",e)
  finally:
   SALIDA.write_text(json.dumps(reporte,ensure_ascii=False,indent=2),encoding="utf-8")
   print("Reporte:",SALIDA)
   await browser.close()
 if reporte.get("error") or reporte.get("errores"):
  raise SystemExit("ERROR: Extraccion SECOP incompleta; revisar reporte antes de continuar.")
if __name__=="__main__":asyncio.run(main())
