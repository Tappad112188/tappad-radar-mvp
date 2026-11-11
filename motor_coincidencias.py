"""Motor inicial de coincidencias para TAPPAD Radar.

No envía correos ni escribe en Supabase. Pensado para pruebas en la rama de desarrollo.
La cobertura estatal se compara solo cuando el expediente declara entidad.
"""
import re
import unicodedata


def normalizar(valor):
    texto = unicodedata.normalize("NFKD", str(valor or "").casefold())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", texto)).strip()


def palabras_proveedor(valor):
    """Acepta términos separados por comas, punto y coma o saltos de línea."""
    vistos = set()
    terminos = []
    for parte in re.split(r"[,;\n]+", valor or ""):
        termino = normalizar(parte)
        if len(termino) >= 3 and termino not in vistos:
            vistos.add(termino)
            terminos.append(termino)
    return terminos


def coincide_estado(entidad_licitacion, coberturas):
    """No descarta licitaciones sin entidad; las marca para revisión."""
    entidad = normalizar(entidad_licitacion)
    estados = {normalizar(c.get("estado")) for c in coberturas or [] if c.get("estado")}
    if not estados or not entidad:
        return True, "sin_dato_geografico"
    equivalencias = {
        "coahuila": "coahuila", "coahuila de zaragoza": "coahuila",
        "ciudad de mexico": "cdmx", "cdmx": "cdmx",
        "estado de mexico": "mexico", "mexico": "mexico",
    }
    canon = lambda e: equivalencias.get(e, e)
    return canon(entidad) in {canon(e) for e in estados}, "coincidencia" if canon(entidad) in {canon(e) for e in estados} else "fuera_de_cobertura"


# Términos administrativos demasiado generales para sustentar una coincidencia.
PALABRAS_GENERICAS = frozenset({
    "de", "del", "la", "las", "el", "los", "y", "e", "para", "por", "con",
    "en", "un", "una", "servicio", "servicios", "producto", "productos",
    "material", "materiales", "suministro", "suministros", "adquisicion",
    "adquisiciones", "equipo", "equipos", "general", "generales", "otros",
    "otras", "diversos", "diversas", "articulos", "articulo",
})


def coincidencias_catalogo(texto, preferencias):
    """Coincidencias conservadoras con descripciones SAT/CUCOP.

    Se exige una frase específica o al menos dos términos distintivos
    consecutivos; nunca basta una palabra genérica ni el código aislado.
    """
    hallazgos = []
    for pref in preferencias or []:
        if pref.get("activo") is False:
            continue
        origen = str(pref.get("origen") or pref.get("sistema") or "").upper()
        if origen not in ("SAT", "CUCOP", "MANUAL"):
            continue
        descripcion = normalizar(pref.get("descripcion"))
        if not descripcion:
            continue
        distintivas = [t for t in descripcion.split() if len(t) >= 4 and t not in PALABRAS_GENERICAS]
        if not distintivas:
            continue
        frases = [descripcion]
        if len(distintivas) >= 2:
            frases.append(" ".join(distintivas))
        # Las coincidencias de una sola palabra requieren un término largo
        # y específico, para evitar clasificar licitaciones por "material".
        if len(distintivas) == 1 and len(distintivas[0]) >= 7:
            frases.append(distintivas[0])
        if not any(" " + frase + " " in texto for frase in frases):
            continue
        hallazgos.append({
            "origen": origen,
            "clave": pref.get("clave"),
            "descripcion": pref.get("descripcion"),
        })
    return hallazgos


def evaluar_licitacion(proveedor, licitacion, coberturas, preferencias=None):
    """Retorna resultado explicable; sin coincidencia no genera alerta."""
    campos = ("nombre_procedimiento", "descripcion", "tipo_contratacion")
    texto = " ".join(normalizar(licitacion.get(campo)) for campo in campos)
    texto = f" {texto} "
    encontrados = [t for t in palabras_proveedor(proveedor.get("palabras_clave")) if f" {t} " in texto]
    claves_catalogo = coincidencias_catalogo(texto, preferencias)
    dentro, motivo = coincide_estado(licitacion.get("entidad_federativa"), coberturas)
    categoria = ("dentro_de_cobertura" if dentro and motivo == "coincidencia" else
                 "cobertura_sin_definir" if dentro else "fuera_de_cobertura")
    return {
        "coincide": bool(encontrados or claves_catalogo) and dentro,
        "coincidencia_tematica": bool(encontrados or claves_catalogo),
        "categoria": categoria,
        "terminos": encontrados + [h["descripcion"] for h in claves_catalogo],
        "claves_catalogo": claves_catalogo,
        "cobertura": motivo,
        "cliente_id": proveedor.get("id"),
        "licitacion_id": licitacion.get("id"),
    }


def generar_coincidencias(proveedores, licitaciones, coberturas_por_cliente, incluir_fuera_de_cobertura=False, preferencias_por_cliente=None):
    """Devuelve coincidencias temáticas; fuera de cobertura solo si se solicita.

    Las oportunidades fuera de cobertura son exploratorias, no alertas automáticas.
    """
    resultados = []
    preferencias_por_cliente = preferencias_por_cliente or {}
    for proveedor in proveedores:
        if proveedor.get("activo") is False:
            continue
        for licitacion in licitaciones:
            resultado = evaluar_licitacion(
                proveedor, licitacion, coberturas_por_cliente.get(proveedor.get("id"), []),
                preferencias_por_cliente.get(proveedor.get("id"), [])
            )
            if resultado["coincidencia_tematica"] and (resultado["coincide"] or incluir_fuera_de_cobertura):
                resultados.append(resultado)
    return resultados
