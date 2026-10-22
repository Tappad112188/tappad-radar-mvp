"""Inspección local de controles SECOP sin descargar documentos ni modificar datos.

Ejecutar en Windows desde la carpeta del archivo:
    py inspeccion_secop_windows.py

El navegador queda visible. El reporte se guarda en un JSON local.
No registra contraseñas, cookies ni valores introducidos en formularios.
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

URL = "https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"
DESTINO = Path(__file__).with_name("diagnostico_controles_secop.json")

async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        page = await browser.new_page(accept_downloads=False)
        try:
            response = await page.goto(URL, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(3000)
            resultado = await page.evaluate("""() => {
              const visible = el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
              const recortar = s => (s || '').replace(/\\s+/g, ' ').trim().slice(0, 140);
              const campos = [...document.querySelectorAll('input,select,button,[role="combobox"]')]
                .filter(visible).slice(0, 100).map(el => ({
                  tag: el.tagName.toLowerCase(),
                  type: el.getAttribute('type') || '',
                  id: el.id || '',
                  name: el.getAttribute('name') || '',
                  placeholder: recortar(el.getAttribute('placeholder')),
                  texto: recortar(el.innerText || el.getAttribute('aria-label')),
                  opciones: el.tagName === 'SELECT'
                    ? [...el.options].slice(0, 25).map(o => recortar(o.text)) : undefined
                }));
              const enlaces = [...document.querySelectorAll('a')].filter(visible).slice(0, 60)
                .map(a => ({texto: recortar(a.innerText), href: a.getAttribute('href') || ''}));
              const marcos = [...document.querySelectorAll('iframe,frame')]
                .map(f => ({tag: f.tagName.toLowerCase(), src: f.getAttribute('src') || ''}));
              return {campos, enlaces, marcos};
            }""")
            resultado["http"] = response.status if response else None
            resultado["url_final"] = page.url
            resultado["titulo"] = await page.title()
            DESTINO.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Inspección completada. Archivo: {DESTINO}")
            print(f"Campos visibles: {len(resultado['campos'])}; enlaces visibles: {len(resultado['enlaces'])}")
            print("No se descargaron bases ni se modificó Supabase.")
            input("Presiona ENTER para cerrar Chromium...")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
