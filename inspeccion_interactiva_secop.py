"""Diagnóstico interactivo local de SECOP. Solo inspección, sin escrituras.

1. Ejecutar: py inspeccion_interactiva_secop.py
2. En Chromium, abrir manualmente filtros y un enlace de documentos.
3. Regresar a CMD y pulsar ENTER para guardar los elementos visibles.
No descarga documentos, no registra tráfico ni credenciales.
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

URL = "https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"
DESTINO = Path(__file__).with_name("diagnostico_secop_interactivo.json")

async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        page = await browser.new_page(accept_downloads=False)
        try:
            await page.goto(URL, wait_until="domcontentloaded", timeout=45000)
            print("En Chromium, abre el filtro Estatus y el filtro Fecha de Publicación.")
            print("No ingreses datos personales ni descargues documentos.")
            input("Cuando los filtros estén abiertos, vuelve aquí y pulsa ENTER...")
            resultado = await page.evaluate("""() => {
              const visible = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
              const corta = s => (s || '').replace(/\\s+/g, ' ').trim().slice(0, 100);
              return {
                campos: [...document.querySelectorAll('input,select,button,[role="combobox"]')]
                  .filter(visible).slice(0, 80).map(e => ({
                    tag: e.tagName.toLowerCase(), tipo: e.type || '',
                    id: e.id || '', nombre: e.getAttribute('name') || '',
                    texto: corta(e.innerText || e.getAttribute('aria-label')),
                    placeholder: corta(e.getAttribute('placeholder')),
                    opciones: e.tagName === 'SELECT'
                      ? [...e.options].slice(0, 25).map(o => corta(o.text)) : undefined
                  })),
                textos_filtros: [...document.querySelectorAll('label,[role="listbox"],[role="option"]')]
                  .filter(visible).slice(0, 60).map(e => ({
                    tag: e.tagName.toLowerCase(), texto: corta(e.innerText),
                    clase: corta(e.className && typeof e.className === 'string' ? e.className : '')
                  }))
              };
            }""")
            resultado["url"] = page.url
            DESTINO.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
            print("Archivo generado:", DESTINO)
            print("Campos:", len(resultado["campos"]), "Controles adicionales:", len(resultado["textos_filtros"]))
            input("Pulsa ENTER para cerrar Chromium...")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
