"""Diagnostico local de enlaces capturados de SECOP; no modifica datos."""
import json
from pathlib import Path
from urllib.parse import urljoin, urlparse
BASE = "https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"
ORIGEN = Path(__file__).with_name("secop_hoy_vigentes.json")
DESTINO = Path(__file__).with_name("diagnostico_enlaces_secop.json")

def clasificar(enlace):
    href = str(enlace.get("href") or "").strip()
    absoluta = str(enlace.get("url_absoluta") or "").strip()
    onclick = str(enlace.get("onclick") or "").strip()
    url = absoluta or (urljoin(BASE, href) if href and not href.lower().startswith(("javascript:", "#")) else "")
    partes = urlparse(url)
    dominio = (partes.hostname or "").lower()
    oficial = dominio == "sefincoahuila.gob.mx" or dominio.endswith(".sefincoahuila.gob.mx")
    individual = oficial and partes.scheme == "https" and (
        partes.path.rstrip("/").lower() != "/sistemas/secop/convocatoria" or bool(partes.query)
    )
    if onclick or href.lower().startswith("javascript:"):
        estado = "requiere_inspeccion_navegador"
    elif individual:
        estado = "candidato_por_verificar"
    else:
        estado = "no_es_enlace_individual_confirmado"
    return {"texto":enlace.get("texto"),"id":enlace.get("id"),"href":href,
            "url_absoluta":url,"onclick":onclick,"estado":estado}

def main():
    if not ORIGEN.exists():
        raise SystemExit("Falta secop_hoy_vigentes.json junto al script.")
    datos = json.loads(ORIGEN.read_text(encoding="utf-8-sig"))
    salida = {"origen":str(ORIGEN),"nota":"Los candidatos requieren prueba de apertura fuera de sesion; no son enlaces confirmados.",
              "procedimientos":[]}
    for r in datos.get("registros",[]):
        enlaces = [clasificar(e) for e in r.get("enlaces",[])]
        salida["procedimientos"].append({"codigo":r.get("codigo"),"referencia":r.get("documentos_referencia"),
                                          "enlaces":enlaces})
        print(r.get("codigo"),":",len(enlaces),"enlaces;",
              sum(e["estado"]=="candidato_por_verificar" for e in enlaces),"candidatos por verificar")
    DESTINO.write_text(json.dumps(salida,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Reporte:",DESTINO)
    print("No se modifico Supabase ni se enviaron correos.")

if __name__=="__main__":
    main()
