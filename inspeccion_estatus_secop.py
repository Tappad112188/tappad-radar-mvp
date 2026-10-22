"""Inspección del filtro Estatus SECOP desde Windows; solo lectura.

Ejecutar: py inspeccion_estatus_secop.py
En Chromium abrir únicamente el filtro Estatus, sin seleccionar ni aplicar.
Pulsar ENTER en CMD para generar diagnostico_estatus_secop.json.
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

URL = "https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"
SALIDA = Path(__file__).with_name("diagnostico_estatus_secop.json")

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        page = await browser.new_page(accept_downloads=False)
        try:
            await page.goto(URL, wait_until="domcontentloaded", timeout=45000)
            print("Abre SOLAMENTE el filtro Estatus y deja sus opciones desplegadas.")
            input("Cuando veas las opciones de Estatus, pulsa ENTER aquí...")
            data = await page.evaluate("""() => {
                const vis = e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length);
                const corto = s => (s || '').replace(/\\s+/g,' ').trim().slice(0,120);
                const nodes = [...document.querySelectorAll('input,select,button,label,[role="option"],[role="listbox"],[role="checkbox"],li')];
                return nodes.filter(vis).slice(0,120).map(e => ({
                    tag:e.tagName.toLowerCase(), id:e.id || '',
                    tipo:e.getAttribute('type') || '', nombre:e.getAttribute('name') || '',
                    rol:e.getAttribute('role') || '', texto:corto(e.innerText || e.getAttribute('aria-label')),
                    clase:corto(typeof e.className === 'string' ? e.className : '')
                }));
            }""")
            SALIDA.write_text(json.dumps({"url":page.url,"elementos":data},ensure_ascii=False,indent=2),encoding="utf-8")
            print("Archivo:", SALIDA, "| elementos visibles:", len(data))
            input("Pulsa ENTER para cerrar el navegador...")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
