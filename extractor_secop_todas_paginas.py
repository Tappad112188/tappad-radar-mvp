"""Extrae todas las páginas de SECOP Coahuila filtradas por Vigente.

Solo lectura. No descarga documentos, no escribe en Supabase ni envía correos.
Ejecutar: py extractor_secop_todas_paginas.py
"""
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

URL = "https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"
SALIDA = Path(__file__).with_name("secop_vigentes_todas_paginas.json")

def limpio(s):
    return re.sub(r"\s+", " ", s or "").strip()

def fecha_normalizada(s):
    try:
        f = datetime.strptime(s, "%d/%m/%Y")
        return f.date().isoformat() if f.year >= 2000 else None
    except (ValueError, TypeError):
        return None

EXTRAER = """cards => cards.map(card => {
    const result = {};
    for (const item of card.querySelectorAll('[id^="CardView_DXCardLayout"]')) {
        if (!/^CardView_DXCardLayout\\d+_\\d+$/.test(item.id)) continue;
        const caption = item.querySelector('[id$="_Cap"]');
        const label = (caption?.textContent || '').replace(/:\\s*$/, '').trim();
        const cell = item.querySelector('td.dxflNestedControlCell_SoftOrange');
        if (label && cell) result[label] = (cell.innerText || '').trim();
    }
    result._enlaces = [...card.querySelectorAll('a')].map(a => ({
        texto:(a.innerText || '').trim(), id:a.id || '', href:a.getAttribute('href') || ''
    }));
    return result;
})"""

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        page = await browser.new_page(accept_downloads=False)
        try:
            response = await page.goto(URL, wait_until="domcontentloaded", timeout=45000)
            if not response or response.status != 200:
                raise RuntimeError("SECOP no respondió HTTP 200")
            await page.locator("#CardView_col3 img[alt='[Filtrar]']").click(timeout=15000)
            await page.locator("#CardView_HFListBox_LBI3T0").click(timeout=15000)
            await page.wait_for_timeout(2500)
            resumen = limpio(await page.locator("#CardView_DXPagerBottom .dxp-summary").inner_text())
            match = re.search(r"Página\s+\d+\s+de\s+(\d+)\s+\((\d+)\s+elementos\)", resumen, re.I)
            if not match:
                raise RuntimeError("No se pudo leer el total de páginas: " + resumen)
            total_paginas, total_reportado = map(int, match.groups())
            if total_paginas > 100:
                raise RuntimeError("Límite preventivo de 100 páginas excedido")
            registros = []
            errores = []
            for numero in range(1, total_paginas + 1):
                if numero > 1:
                    selector = f"#CardView_DXPagerBottom a.dxp-num[onclick*=\"'PN{numero-1}'\"]"
                    await page.locator(selector).click(timeout=15000)
                    await page.wait_for_function(
                        "(n) => document.querySelector('#CardView_DXPagerBottom .dxp-current')?.textContent?.trim() === String(n)",
                        arg=numero, timeout=20000)
                tarjetas = await page.locator("td[id^='CardView_DXDataCard']").evaluate_all(EXTRAER)
                print(f"Página {numero}/{total_paginas}: {len(tarjetas)} registros")
                for item in tarjetas:
                    fecha = limpio(item.get("Fecha de Publicación"))
                    r = {
                        "pagina": numero,
                        "estatus": limpio(item.get("Estatus")),
                        "descripcion": limpio(item.get("Descripción")),
                        "codigo": limpio(item.get("Código")),
                        "fecha_publicacion_original": fecha,
                        "fecha_publicacion": fecha_normalizada(fecha),
                        "documentos_referencia": limpio(item.get("Documentos de Procedimiento")),
                        "enlaces": item.get("_enlaces", []),
                    }
                    r["fecha_requiere_revision"] = r["fecha_publicacion"] is None
                    if not r["estatus"] or not r["codigo"]:
                        errores.append({"pagina":numero,"registro":r["codigo"],"problema":"campos incompletos"})
                    registros.append(r)
            codigos = [r["codigo"] for r in registros if r["codigo"]]
            reporte = {
                "fuente": URL,
                "alcance": "todas las páginas filtradas por Vigente",
                "paginas": total_paginas,
                "total_reportado_por_secop": total_reportado,
                "total_extraido": len(registros),
                "cantidad_codigos_unicos": len(set(codigos)),
                "cantidad_solo_vigentes": sum(r["estatus"].casefold()=="vigente" for r in registros),
                "coincide_total": len(registros)==total_reportado,
                "fechas_requieren_revision": sum(r["fecha_requiere_revision"] for r in registros),
                "errores": errores,
                "registros": registros,
            }
            SALIDA.write_text(json.dumps(reporte,ensure_ascii=False,indent=2),encoding="utf-8")
            print("Total:",len(registros),"de",total_reportado,"| Vigentes:",reporte["cantidad_solo_vigentes"])
            print("Reporte:",SALIDA)
            input("Pulsa ENTER para cerrar Chromium...")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
