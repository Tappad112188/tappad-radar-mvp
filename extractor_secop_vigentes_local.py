"""SECOP Coahuila: extraer la primera página filtrada por Vigente.

Solo lectura. No descarga documentos, no escribe en Supabase, no envía correos.
Ejecutar: py extractor_secop_vigentes_local.py
"""
import asyncio
import json
import re
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright

URL = "https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"
SALIDA = Path(__file__).with_name("secop_vigentes_primera_pagina.json")

def limpiar(valor):
    return re.sub(r"\\s+", " ", valor or "").strip()

def fecha_valida(valor):
    try:
        return datetime.strptime(valor, "%d/%m/%Y").year >= 2000
    except (ValueError, TypeError):
        return False

async def main():
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        page = await browser.new_page(accept_downloads=False)
        try:
            respuesta = await page.goto(URL, wait_until="domcontentloaded", timeout=45000)
            if not respuesta or respuesta.status != 200:
                raise RuntimeError("SECOP no respondió con HTTP 200")
            await page.locator("#CardView_col3 img[alt='[Filtrar]']").click(timeout=15000)
            await page.locator("#CardView_HFListBox_LBI3T0").click(timeout=15000)
            await page.wait_for_timeout(3500)
            datos = await page.locator("td[id^='CardView_DXDataCard']").evaluate_all("""cards => cards.map(card => {
                const campo = n => {
                    const root = card.querySelector('[id$="_' + n + '"]');
                    if (!root) return '';
                    const value = root.querySelector('.dxflNestedControlCell_SoftOrange');
                    return (value ? value.innerText : root.innerText).trim();
                };
                return {
                    texto: card.innerText,
                    enlace_documentos: [...card.querySelectorAll('a')].map(a => ({
                        texto: (a.innerText || '').trim(),
                        href: a.getAttribute('href') || '',
                        id: a.id || ''
                    }))
                };
            })""")
            registros = []
            for card in datos:
                texto = card["texto"]
                def campo(nombre):
                    match = re.search(r"(?:^|\\n)" + re.escape(nombre) + r":\\s*(.*?)(?=\\n(?:Estatus|Descripción|Código|Fecha de Publicación|Documentos de Procedimiento):|$)", texto, re.I | re.S)
                    return limpiar(match.group(1)) if match else ""
                estado = campo("Estatus")
                fecha = campo("Fecha de Publicación")
                documentos = campo("Documentos de Procedimiento")
                registros.append({
                    "estatus": estado,
                    "descripcion": campo("Descripción"),
                    "codigo": campo("Código"),
                    "fecha_publicacion": fecha if fecha_valida(fecha) else None,
                    "fecha_publicacion_original": fecha,
                    "fecha_requiere_revision": not fecha_valida(fecha),
                    "documentos_referencia": documentos,
                    "enlaces": card["enlace_documentos"],
                })
            solo_vigentes = bool(registros) and all(limpiar(r["estatus"]).casefold() == "vigente" for r in registros)
            reporte = {
                "fuente": URL,
                "alcance": "solo primera página de resultados filtrados",
                "registros": registros,
                "cantidad": len(registros),
                "solo_vigentes": solo_vigentes,
                "fecha_extraccion_local": datetime.now().isoformat(timespec="seconds")
            }
            SALIDA.write_text(json.dumps(reporte,ensure_ascii=False,indent=2),encoding="utf-8")
            print("Registros:",len(registros),"| Todos vigentes:",solo_vigentes)
            print("Fechas a revisar:",sum(r["fecha_requiere_revision"] for r in registros))
            print("Archivo:",SALIDA)
            input("Pulsa ENTER para cerrar Chromium...")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
