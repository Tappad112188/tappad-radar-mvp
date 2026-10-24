"""Inspeccion de navegacion real SECOP en Windows (solo lectura).
Usa el listado ya extraido y registra URL, ventanas y descargas tras pulsar
el enlace de documentos de cada procedimiento. No escribe en Supabase.
"""
import asyncio, json, re
from pathlib import Path
from playwright.async_api import async_playwright

BASE=Path(__file__).resolve().parent
ENTRADA=BASE/"secop_hoy_vigentes.json"
SALIDA=BASE/"diagnostico_navegacion_secop.json"
PORTAL="https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"

async def main():
 if not ENTRADA.exists():
  print("ERROR: No existe",ENTRADA)
  return
 datos=json.loads(ENTRADA.read_text(encoding="utf-8-sig"))
 registros=datos.get("registros",[])
 if not registros:
  print("ERROR: El archivo no contiene registros")
  return
 reporte={"portal":PORTAL,"procedimientos":[],"nota":"Diagnostico tecnico, ninguna URL se considera verificada automaticamente"}
 async with async_playwright() as pw:
  navegador=await pw.chromium.launch(headless=False)
  contexto=await navegador.new_context(accept_downloads=True)
  pagina=await contexto.new_page()
  try:
   for r in registros:
    codigo=r.get("codigo")
    referencia=r.get("documentos_referencia")
    item={"codigo":codigo,"referencia":referencia,"url_antes":None,"url_despues":None,"ventanas_nuevas":[],"solicitudes":[],"errores":[]}
    reporte["procedimientos"].append(item)
    if not referencia or not r.get("fecha_publicacion"):
     item["errores"].append("Falta referencia o fecha");continue
    try:
     resp=await pagina.goto(PORTAL,wait_until="domcontentloaded",timeout=60000)
     if not resp or resp.status!=200:raise RuntimeError("Portal sin HTTP 200")
     fecha_iso=r["fecha_publicacion"]
     dd,mm,aaaa=fecha_iso[8:10],fecha_iso[5:7],fecha_iso[:4]
     fecha=f"{dd}/{mm}/{aaaa}"
     await pagina.locator("#CardView_col2 img[alt='[Filtrar]']").click(timeout=20000)
     await pagina.locator("#CardView_HFFDE_I").wait_for(state="visible",timeout=20000)
     await pagina.locator("#CardView_HFFDE_I").fill(fecha)
     await pagina.locator("#CardView_HFTDE_I").fill(fecha)
     await pagina.locator("#CardView_DXHFP_TPCFCm1_O").click(timeout=20000)
     await pagina.locator("#CardView_col2 img[alt='[Filtrado]']").wait_for(state="attached",timeout=20000)
     await pagina.wait_for_timeout(1000)
     enlace=pagina.get_by_text(referencia,exact=True).first
     await enlace.wait_for(state="visible",timeout=20000)
     item["url_antes"]=pagina.url
     anteriores=set(contexto.pages)
     async def capturar_solicitud(request):
      if request.is_navigation_request():
       item["solicitudes"].append({"metodo":request.method,"url":request.url})
     def solicitud(request):
      if request.is_navigation_request():
       item["solicitudes"].append({"metodo":request.method,"url":request.url})
     pagina.on("request",solicitud)
     try:
      await enlace.click(timeout=20000)
      await pagina.wait_for_timeout(1800)
      item["url_despues"]=pagina.url
      for nueva in contexto.pages:
       if nueva not in anteriores:
        item["ventanas_nuevas"].append(nueva.url)
      item["titulo_vista"]= (await pagina.title())[:150]
      item["enlaces_visibles"]=await pagina.evaluate("""() => [...document.querySelectorAll('a[href]')].filter(a=>a.offsetParent!==null).slice(0,30).map(a=>({texto:(a.innerText||'').trim().slice(0,80),href:a.href}))""")
     finally:
      pagina.remove_listener("request",solicitud)
     print(codigo,"| antes:",item["url_antes"],"| despues:",item["url_despues"],"| ventanas:",len(item["ventanas_nuevas"]))
    except Exception as e:
     item["errores"].append(str(e)[:350])
     print(codigo,"ERROR:",str(e)[:160])
  finally:
   SALIDA.write_text(json.dumps(reporte,ensure_ascii=False,indent=2),encoding="utf-8")
   print("Reporte:",SALIDA)
   print("Solo lectura: no se enviaron correos ni se modifico Supabase.")
   input("Pulsa ENTER para cerrar Chromium...")
   await navegador.close()

if __name__=="__main__":
 asyncio.run(main())
