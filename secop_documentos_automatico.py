"""SECOP: descarga documental y extracción de calendario sin intervención humana.
Opera solo sobre registros filtrados hoy. No envía correos.
"""
import argparse
import asyncio
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parent
URL = "https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"
CARPETA = ROOT / "documentos_secop_automaticos"
MAX_BYTES = 35_000_000

async def main():
    p = argparse.ArgumentParser()
    p.add_argument("--reporte", default=str(ROOT / "secop_vigentes_hoy.json"))
    p.add_argument("--salida", default=str(ROOT / "secop_calendarios_automaticos.json"))
    args = p.parse_args()
    data = json.loads(Path(args.reporte).read_text(encoding="utf-8"))
    hoy = datetime.now(ZoneInfo("America/Monterrey")).date().isoformat()
    if data.get("fecha_consulta") != hoy or not data.get("filtros_servidor_confirmados"):
        raise SystemExit("Reporte SECOP no validado para hoy")
    CARPETA.mkdir(exist_ok=True)
    resultados = []
    async def aplicar_filtros():
        response = await page.goto(URL, wait_until="domcontentloaded", timeout=45000)
        if not response or response.status != 200:
            raise RuntimeError("SECOP no respondió HTTP 200")
        for selector in ("#CardView_HFFDE_I", "#CardView_HFTDE_I"):
            await page.locator(selector).fill(datetime.fromisoformat(hoy).strftime("%d/%m/%Y"))
            await page.locator(selector).press("Tab")
            await page.wait_for_timeout(1000)
        await page.locator("#CardView_col3 img[alt='[Filtrar]']").click(timeout=15000)
        await page.locator("#CardView_HFListBox_LBI3T0").click(timeout=15000)
        await page.wait_for_timeout(1800)
    async def localizar(codigo):
        resumen = await page.locator("#CardView_DXPagerBottom .dxp-summary").inner_text()
        match = re.search(r"de\s+(\d+)\s+\(", resumen)
        paginas = int(match.group(1)) if match else 1
        for numero in range(1, paginas + 1):
            tarjeta = page.locator("td[id^='CardView_DXDataCard']").filter(has_text=codigo)
            if await tarjeta.count() == 1:
                return tarjeta
            if numero < paginas:
                selector = "#CardView_DXPagerBottom a.dxp-num[onclick*=\"'PN" + str(numero) + "'\"]"
                await page.locator(selector).click(timeout=15000)
                await page.wait_for_timeout(900)
        return None
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        try:
            await aplicar_filtros()
            for registro in data.get("registros", []):
                codigo = registro["codigo"]
                resultado = {"codigo": codigo, "documentos": [], "calendario": {}, "estado": "pendiente_revision", "errores": []}
                try:
                    # Rebuscar la tarjeta por su código, sin depender de IDs de otro expediente.
                    await aplicar_filtros()
                    tarjeta = await localizar(codigo)
                    if tarjeta is None:
                        resultado["errores"].append("Tarjeta no visible o ambigua; paginación pendiente")
                        resultados.append(resultado)
                        continue
                    enlace = tarjeta.locator("a[id^='OtherDocumentsHyperLink_']")
                    if await enlace.count() != 1:
                        resultado["errores"].append("Enlace de documentos no identificado")
                        resultados.append(resultado)
                        continue
                    await enlace.click(timeout=15000)
                    await page.get_by_text("Base de Procedimiento", exact=False).first.wait_for(timeout=15000)
                    links = await page.locator("a[href*='GetFile/']").evaluate_all(
                        """els => els.map(a => ({url:a.href,texto:(a.innerText||a.title||'').trim()}))"""
                    )
                    # Preferir archivo ZIP de bases y anexos, no documentos de otro procedimiento.
                    candidatos = [x for x in links if re.search(r"bases|anexos", x["texto"], re.I)]
                    if not candidatos:
                        resultado["errores"].append("Sin enlace inequívoco de bases o anexos")
                    else:
                        # Se analiza solo el primer ZIP que contenga bases coincidentes.
                        for enlace_archivo in candidatos[:5]:
                            try:
                                respuesta = await context.request.get(enlace_archivo["url"], timeout=45000)
                                if not respuesta.ok:
                                    continue
                                body = await respuesta.body()
                                if len(body) > MAX_BYTES:
                                    continue
                                if body[:4] != b"PK\\x03\\x04":
                                    continue
                                destino = CARPETA / (re.sub(r"[^a-zA-Z0-9_-]", "_", codigo) + ".zip")
                                destino.write_bytes(body)
                                resultado["documentos"].append({"url": enlace_archivo["url"], "ruta": str(destino)})
                                proc = subprocess.run(
                                    [sys.executable, str(ROOT / "extraer_calendario_secop_v2.py"), str(destino)],
                                    capture_output=True, text=True, timeout=120
                                )
                                if proc.returncode:
                                    resultado["errores"].append("Error de lectura documental: " + proc.stderr[-250:])
                                    continue
                                calendario = json.loads(destino.with_name(destino.stem + "_calendario_v2.json").read_text(encoding="utf-8"))
                                for origen, destino_campo in (
                                    ("junta_aclaraciones", "fecha_junta_aclaraciones"),
                                    ("presentacion_apertura", "fecha_apertura"),
                                    ("fallo_programado", "fecha_fallo_programado")
                                ):
                                    v = calendario.get("calendario", {}).get(origen, {})
                                    if v.get("fecha") and v.get("hora") and not v.get("candidatos"):
                                        resultado["calendario"][destino_campo] = v["fecha"] + "T" + v["hora"] + ":00"
                                resultado["estado"] = ("completo" if len(resultado["calendario"]) == 3 else "pendiente_revision")
                                break
                            except Exception as exc:
                                resultado["errores"].append(str(exc)[:200])
                except Exception as exc:
                    resultado["errores"].append(str(exc)[:250])
                resultados.append(resultado)
        finally:
            await browser.close()
    Path(args.salida).write_text(json.dumps({"fecha_consulta": hoy, "resultados": resultados}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Calendarios completos:", sum(r["estado"] == "completo" for r in resultados), "de", len(resultados))
    print("Reporte:", args.salida)

if __name__ == "__main__":
    asyncio.run(main())
