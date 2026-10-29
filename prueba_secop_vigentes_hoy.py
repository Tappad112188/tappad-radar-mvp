"""Extractor automatizable: SECOP Coahuila, fecha local de hoy y estatus Vigente.
Solo lectura; no toca Supabase ni envía correos.
"""
import argparse
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright

URL = "https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"
ZONA = ZoneInfo("America/Monterrey")
SALIDA = Path(__file__).with_name("secop_vigentes_hoy.json")
EXTRAER = """cards => cards.map(card => {
 const out = {};
 for(const item of card.querySelectorAll('[id^="CardView_DXCardLayout"]')){
  if(!/^CardView_DXCardLayout\\d+_\\d+$/.test(item.id))continue;
  const cap=item.querySelector('[id$="_Cap"]');
  const key=(cap?.textContent||'').replace(/:\\s*$/,'').trim();
  const val=item.querySelector('td.dxflNestedControlCell_SoftOrange');
  if(key&&val)out[key]=(val.innerText||'').trim();
 }
 out._enlaces=[...card.querySelectorAll('a')].map(a=>({texto:(a.innerText||'').trim(),id:a.id||'',href:a.getAttribute('href')||''}));
 return out;
})"""

async def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--headless",action="store_true",help="Ejecutar sin ventana para GitHub Actions")
 parser.add_argument("--salida",default=str(SALIDA))
 args=parser.parse_args()
 fecha = datetime.now(ZONA).date()
 fecha_web = fecha.strftime("%d/%m/%Y")
 print("Fecha local Coahuila:", fecha_web)
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(headless=args.headless)
  page=await browser.new_page(accept_downloads=False)
  try:
   response=await page.goto(URL,wait_until="domcontentloaded",timeout=45000)
   if not response or response.status!=200:
    raise RuntimeError(f"SECOP HTTP {response.status if response else 'sin respuesta'}; URL final: {page.url}; título: {(await page.title())[:120]}")
   # Los campos son filtros de rango de fecha de DevExpress; comprobar si el servidor los aplica.
   for selector in ("#CardView_HFFDE_I","#CardView_HFTDE_I"):
    campo=page.locator(selector)
    await campo.wait_for(state="visible",timeout=15000)
    await campo.fill(fecha_web)
    await campo.press("Tab")
    await page.wait_for_timeout(1300)
   print("Campos de fecha:",await page.locator("#CardView_HFFDE_I").input_value(),await page.locator("#CardView_HFTDE_I").input_value())
   await page.locator("#CardView_col3 img[alt='[Filtrar]']").click(timeout=15000)
   await page.locator("#CardView_HFListBox_LBI3T0").click(timeout=15000)
   await page.wait_for_timeout(1800)
   resumen=(await page.locator("#CardView_DXPagerBottom .dxp-summary").inner_text()).strip()
   m=re.search(r"Página\s+\d+\s+de\s+(\d+)\s+\((\d+)\s+elementos\)",resumen,re.I)
   if not m:raise RuntimeError("No se pudo interpretar paginación: "+resumen)
   paginas,total=map(int,m.groups())
   if paginas>100:raise RuntimeError("Demasiadas páginas; posible filtro no aplicado")
   registros=[]
   for n in range(1,paginas+1):
    if n>1:
     await page.locator(f"#CardView_DXPagerBottom a.dxp-num[onclick*=\"'PN{n-1}'\"]").click(timeout=15000)
     await page.wait_for_function("(x)=>document.querySelector('#CardView_DXPagerBottom .dxp-current')?.textContent?.trim()===String(x)",arg=n,timeout=20000)
    tarjetas=await page.locator("td[id^='CardView_DXDataCard']").evaluate_all(EXTRAER)
    for item in tarjetas:
     f=(item.get("Fecha de Publicación") or "").strip()
     registros.append({"pagina":n,"codigo":(item.get("Código") or "").strip(),"estatus":(item.get("Estatus") or "").strip(),"descripcion":(item.get("Descripción") or "").strip(),"fecha_publicacion_original":f,"documentos_referencia":(item.get("Documentos de Procedimiento") or "").strip(),"enlaces":item.get("_enlaces",[])})
    print(f"Página {n}/{paginas}: {len(tarjetas)}")
   hoy=[r for r in registros if r["fecha_publicacion_original"]==fecha_web and r["estatus"].casefold()=="vigente"]
   discrepancias=[r["codigo"] for r in registros if r not in hoy]
   reporte={"fecha_consulta":fecha.isoformat(),"filtro_fecha_solicitado":fecha_web,"estatus_solicitado":"Vigente","paginas":paginas,"total_reportado_por_secop":total,"total_devuelto_por_servidor":len(registros),"total_validado_fecha_y_estatus":len(hoy),"filtros_servidor_confirmados":len(discrepancias)==0 and len(registros)==total,"registros_fuera_de_filtro":discrepancias,"registros":hoy}
   if not reporte["filtros_servidor_confirmados"]:
    raise RuntimeError("Filtros SECOP inconsistentes; se cancela la importacion")
   Path(args.salida).write_text(json.dumps(reporte,ensure_ascii=False,indent=2),encoding="utf-8")
   print("Procedimientos vigentes publicados hoy:",len(hoy))
   print("Filtro servidor consistente:",reporte["filtros_servidor_confirmados"])
   print("Archivo:",SALIDA)
   if not args.headless:
    input("Pulsa ENTER para cerrar Chromium...")
  finally:
   await browser.close()

if __name__=="__main__":
 asyncio.run(main())
