"""Prueba local de filtrado SECOP por estatus Vigente (solo lectura).

Ejecutar: py prueba_filtro_vigente_secop.py
No descarga bases, no escribe en Supabase ni envía correos.
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

URL = "https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"
SALIDA = Path(__file__).with_name("resultado_filtro_vigente_secop.json")

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        page = await browser.new_page(accept_downloads=False)
        try:
            response = await page.goto(URL, wait_until="domcontentloaded", timeout=45000)
            await page.locator("#CardView_col3 img[alt='[Filtrar]']").click(timeout=15000)
            opcion = page.locator("#CardView_HFListBox_LBI3T0")
            await opcion.wait_for(state="visible", timeout=15000)
            await opcion.click()
            await page.wait_for_timeout(3500)
            tarjetas = await page.locator("td[id^='CardView_DXDataCard']").all_inner_texts()
            estados = []
            for tarjeta in tarjetas:
                for linea in tarjeta.splitlines():
                    if linea.strip().startswith("Estatus:"):
                        estados.append(linea.strip())
                        break
            resultado = {
                "http_inicial": response.status if response else None,
                "url_final": page.url,
                "tarjetas_visibles": len(tarjetas),
                "estados_detectados": estados,
                "solo_vigentes": bool(estados) and all(e == "Estatus: Vigente" for e in estados),
                "sin_resultados": len(tarjetas) == 0,
            }
            SALIDA.write_text(json.dumps(resultado,ensure_ascii=False,indent=2),encoding="utf-8")
            print(json.dumps(resultado,ensure_ascii=False,indent=2))
            print("Reporte:",SALIDA)
            input("Pulsa ENTER para cerrar Chromium...")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
