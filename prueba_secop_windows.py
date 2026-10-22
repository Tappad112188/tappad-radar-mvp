"""Prueba local de SECOP Coahuila en Windows, sin escritura ni descargas.

Instalación:
  py -m pip install playwright
  py -m playwright install chromium
Ejecución:
  py prueba_secop_windows.py

Se abre un navegador visible para inspeccionar el portal. No inicia sesión,
no descarga documentos ni modifica Supabase. No intenta evadir bloqueos.
"""
import asyncio
import json
from urllib.parse import urlparse
from playwright.async_api import async_playwright

URL = "https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"

async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=False)
        page = await browser.new_page(accept_downloads=False)
        try:
            response = await page.goto(URL, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(3000)
            titulo = await page.title()
            resultado = {
                "http_inicial": response.status if response else None,
                "dominio": urlparse(page.url).netloc,
                "titulo": titulo[:120],
                "formularios": await page.locator("form").count(),
                "tablas": await page.locator("table").count(),
                "selectores": await page.locator("select").count(),
                "campos_fecha": await page.locator('input[type="date"]').count(),
                "enlaces": await page.locator("a").count(),
                "acceso_restringido": "access denied" in titulo.lower() or "sucuri" in titulo.lower(),
            }
            print("\nRESULTADO SECOP:")
            print(json.dumps(resultado, indent=2, ensure_ascii=False))
            print("\nNo se descargaron documentos ni se modificó Supabase.")
            input("Presiona ENTER para cerrar el navegador...")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
