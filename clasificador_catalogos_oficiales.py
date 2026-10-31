"""Clasificador común de SAT, SCIAN y CUCOP; no modifica sistemas externos."""
import re
import unicodedata
from dataclasses import dataclass

SISTEMAS = frozenset({"SAT", "SCIAN", "CUCOP"})

def normalizar(texto):
    texto = unicodedata.normalize("NFKD", str(texto or "").lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()

def clasificar(texto, catalogos, sinonimos=None, minimo=0.55):
    """Devuelve candidatos, NO asignaciones definitivas.

    catalogos: iterable de dict(sistema, clave, descripcion, version, fuente_url)
    sinonimos: dict opcional de (sistema, clave, version) -> lista de expresiones
    """
    consulta = normalizar(texto)
    palabras = set(consulta.split())
    resultados = []
    sinonimos = sinonimos or {}
    if not palabras:
        return resultados
    for item in catalogos:
        sistema = str(item.get("sistema", "")).upper()
        if sistema not in SISTEMAS:
            continue
        clave = str(item.get("clave", "")).strip()
        version = str(item.get("version", "")).strip()
        descripcion = str(item.get("descripcion", "")).strip()
        if not (clave and version and descripcion):
            continue
        frases = [descripcion] + list(sinonimos.get((sistema, clave, version), []))
        mejor = 0.0
        evidencia = None
        for frase in frases:
            normal = normalizar(frase)
            tokens = set(normal.split())
            if not tokens:
                continue
            score = len(tokens & palabras) / len(tokens)
            if normal and normal in consulta:
                score = 1.0
            if score > mejor:
                mejor, evidencia = score, frase
        if mejor >= minimo:
            resultados.append({
                "sistema": sistema, "clave": clave, "version": version,
                "descripcion": descripcion, "confianza_lexica": round(mejor, 3),
                "evidencia": evidencia, "estado": "pendiente_revision",
            })
    return sorted(resultados, key=lambda x: (-x["confianza_lexica"], x["sistema"], x["clave"]))
