"""Extractor SECOP Coahuila, primera página filtrada por Vigente.

Lectura exclusiva. No descarga bases, no escribe en Supabase ni envía correos.
Ejecutar: py extractor_secop_vigentes_v2.py
"""
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

URL = "https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"
SALIDA = Path(__file__).with_name("secop_vigentes_v2.json")
CAMPOS = {
    "estatus": 2,
    "descripcion": 3,
    "codigo": 4,
    "fecha_publicacion_original": 5,
    "documentos_referencia": 6,
}

def limpio(s):
    return re.sub(r"\s+", " ", s or "").strip()

def fecha_normalizada(s):
    try:
        fecha = datetime.strptime(s, "%d/%m/%Y")
        return fecha.date().isoformat() if fecha.year >= 2000 else None
    except (ValueError, TypeError):
        return None

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        page = await browser.new_page(accept_downloads=False)
        try:
            respuesta = await page.goto(URL, wait_until="domcontentloaded", timeout=45000)
            if not respuesta or respuesta.status != 200:
                raise RuntimeError("SECOP no respondió HTTP 200")
            await page.locator("#CardView_col3 img[alt='[Filtrar]']").click(timeout=15000)
            await page.locator("#CardView_HFListBox_LBI3T0").click(timeout=15000)
            await page.wait_for_timeout(3500)
            datos = await page.locator("td[id^='CardView_DXDataCard']").evaluate_all("""cards => cards.map((card, i) => {
                const items = [...card.querySelectorAll('[id^="CardView_DXCardLayout"]')]
                    .filter(e => /^CardView_DXCardLayout\\d+_\\d+$/.test(e.id));
                const result = {};
                for (const item of items) {
                    const caption = item.querySelector('[id$="_Cap"]');
                    const label = (caption?.textContent || '').replace(/:\\s*$/, '').trim();
                    const cell = item.querySelector('td.dxflNestedControlCell_SoftOrange');
                    if (label && cell) result[label] = (cell.innerText || '').trim();
                }
                result._enlaces = [...card.querySelectorAll('a')].map(a => ({
                    texto: (a.innerText || '').trim(), id: a.id || '', href: a.getAttribute('href') || ''
                }));
                return result;
            })""")
            registros = []
            for item in datos:
                fecha = limpio(item.get("Fecha de Publicación"))
                registro = {
                    "estatus": limpio(item.get("Estatus")),
                    "descripcion": limpio(item.get("Descripción")),
                    "codigo": limpio(item.get("Código")),
                    "fecha_publicacion_original": fecha,
                    "fecha_publicacion": fecha_normalizada(fecha),
                    "documentos_referencia": limpio(item.get("Documentos de Procedimiento")),
                    "enlaces": item.get("_enlaces", []),
                }
                registro["fecha_requiere_revision"] = registro["fecha_publicacion"] is None
                registros.append(registro)
            solo_vigentes = bool(registros) and all(r["estatus"].casefold() == "vigente" for r in registros)
            resultado = {
                "fuente": URL,
                "alcance": "primera página de resultados filtrados",
                "cantidad": len(registros),
                "solo_vigentes": solo_vigentes,
                "campos_completos": sum(bool(r["estatus"] and r["descripcion"] and r["codigo"]) for r in registros),
                "registros": registros,
            }
            SALIDA.write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
            print("Registros:",len(registros),"| Solo vigentes:",solo_vigentes,
                  "| Campos principales completos:",resultado["campos_completos"])
            print("Archivo:", SALIDA)
            input("Pulsa ENTER para cerrar Chromium...")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
