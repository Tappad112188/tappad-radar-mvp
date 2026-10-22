"""Prueba de navegación pública SECOP Coahuila con Playwright.

No inicia sesión, no descarga documentos, no modifica bases de datos.
Guarda únicamente diagnóstico de navegación sin datos personales.
"""
import asyncio
import json
from urllib.parse import urlparse
from playwright.async_api import async_playwright

URL = "https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"

async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page(accept_downloads=False)
        try:
            response = await page.goto(URL, wait_until="domcontentloaded", timeout=45000)
            await page.wait_for_timeout(2500)
            print(json.dumps({
                "http_inicial": response.status if response else None,
                "url_final": page.url,
                "dominio_final": urlparse(page.url).netloc,
                "titulo": (await page.title())[:120],
                "formularios": await page.locator("form").count(),
                "tablas": await page.locator("table").count(),
                "selectores": await page.locator("select").count(),
                "enlaces": await page.locator("a").count(),
                "campos_fecha": await page.locator('input[type="date"]').count(),
            }, ensure_ascii=False))
        except Exception as exc:
            print(json.dumps({"estado": "error", "tipo": type(exc).__name__,
                              "detalle": str(exc)[:250]}, ensure_ascii=False))
            raise
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
