"""SECOP Coahuila: inspeccionar paginación del listado Vigente sin escrituras.

Ejecutar: py inspeccion_paginacion_secop.py
Solo lectura: no descarga documentos, no modifica Supabase, no envía correos.
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

URL = "https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"
SALIDA = Path(__file__).with_name("diagnostico_paginacion_secop.json")

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        page = await browser.new_page(accept_downloads=False)
        try:
            await page.goto(URL, wait_until="domcontentloaded", timeout=45000)
            await page.locator("#CardView_col3 img[alt='[Filtrar]']").click(timeout=15000)
            await page.locator("#CardView_HFListBox_LBI3T0").click(timeout=15000)
            await page.wait_for_timeout(3000)
            antes = await page.locator("td[id^='CardView_DXDataCard']").count()
            datos = await page.evaluate("""() => {
              const cards = [...document.querySelectorAll('td[id^="CardView_DXDataCard"]')];
              const links = [...document.querySelectorAll('a')].filter(a => {
                const t = (a.innerText || '').trim();
                return /^\\d+$/.test(t) || /next|siguiente|>|»/i.test(t);
              }).slice(0,40).map(a => ({
                texto:(a.innerText||'').trim(), id:a.id||'',
                href:a.getAttribute('href')||'', outer_html:a.outerHTML.slice(0,450)
              }));
              const pager = [...document.querySelectorAll('[id*="Pager"],[class*="Pager"],[id*="DXPager"]')]
                .filter(e => !!(e.offsetWidth || e.offsetHeight || e.getClientRects().length))
                .slice(0,15).map(e => ({id:e.id||'', texto:(e.innerText||'').trim().slice(0,400), html:e.outerHTML.slice(0,1200)}));
              return {links,pager,primer_registro:(cards[0]?.innerText||'').slice(0,350)};
            }""")
            datos["tarjetas_antes"] = antes
            SALIDA.write_text(json.dumps(datos,ensure_ascii=False,indent=2),encoding="utf-8")
            print("Paginación inspeccionada. Tarjetas:", antes)
            print("Archivo:",SALIDA)
            input("Pulsa ENTER para cerrar Chromium...")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
