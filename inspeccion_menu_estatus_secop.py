"""Inspección focalizada del menú Estatus de SECOP Coahuila.

Abre el filtro Estatus en Chromium, vuelve a CMD y pulsa ENTER.
Genera JSON con texto y HTML limitado de elementos cercanos al menú,
sin cookies, credenciales, solicitudes de red ni datos de formularios.
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

URL = "https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"
SALIDA = Path(__file__).with_name("diagnostico_menu_estatus_secop.json")

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        page = await browser.new_page(accept_downloads=False)
        try:
            await page.goto(URL, wait_until="domcontentloaded", timeout=45000)
            print("Abre el filtro ESTATUS y deja visible su menú.")
            input("Con el menú abierto, pulsa ENTER en esta ventana CMD...")
            resultado = await page.evaluate("""() => {
              const visible = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
              const corto = s => (s || '').replace(/\\s+/g, ' ').trim().slice(0, 250);
              const candidatos = [...document.querySelectorAll('div,span,td,a,label,input')].filter(visible)
                .filter(e => /vigente|adjudicado|desierto|estatus|aplicar|apply|filter/i.test(e.innerText || e.textContent || ''))
                .filter(e => (e.innerText || '').length < 400)
                .slice(0, 60).map(e => ({
                  tag:e.tagName.toLowerCase(), id:e.id || '',
                  clase:corto(typeof e.className === 'string' ? e.className : ''),
                  texto:corto(e.innerText), html:e.outerHTML.slice(0, 550)
                }));
              const menus = [...document.querySelectorAll('[id*="HF"],[id*="Popup"],[class*="dxpc"],[class*="dxhfp"]')]
                .filter(visible).slice(0, 60).map(e => ({
                  tag:e.tagName.toLowerCase(), id:e.id || '',
                  clase:corto(typeof e.className === 'string' ? e.className : ''),
                  texto:corto(e.innerText)
                }));
              return {candidatos,menus};
            }""")
            SALIDA.write_text(json.dumps(resultado,ensure_ascii=False,indent=2),encoding="utf-8")
            print("Archivo generado:", SALIDA)
            print("Elementos:",len(resultado["candidatos"]),"menús:",len(resultado["menus"]))
            input("Pulsa ENTER para cerrar Chromium...")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
