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


def evaluar_licitacion(proveedor, licitacion, coberturas):
    """Retorna resultado explicable; sin coincidencia no genera alerta."""
    campos = ("nombre_procedimiento", "descripcion", "tipo_contratacion")
    texto = " ".join(normalizar(licitacion.get(campo)) for campo in campos)
    texto = f" {texto} "
    encontrados = [t for t in palabras_proveedor(proveedor.get("palabras_clave")) if f" {t} " in texto]
    dentro, motivo = coincide_estado(licitacion.get("entidad_federativa"), coberturas)
    categoria = ("dentro_de_cobertura" if dentro and motivo == "coincidencia" else
                 "cobertura_sin_definir" if dentro else "fuera_de_cobertura")
    return {
        "coincide": bool(encontrados) and dentro,
        "coincidencia_tematica": bool(encontrados),
        "categoria": categoria,
        "terminos": encontrados,
        "cobertura": motivo,
        "cliente_id": proveedor.get("id"),
        "licitacion_id": licitacion.get("id"),
    }


def generar_coincidencias(proveedores, licitaciones, coberturas_por_cliente, incluir_fuera_de_cobertura=False):
    """Devuelve coincidencias temáticas; fuera de cobertura solo si se solicita.

    Las oportunidades fuera de cobertura son exploratorias, no alertas automáticas.
    """
    resultados = []
    for proveedor in proveedores:
        if proveedor.get("activo") is False:
            continue
        for licitacion in licitaciones:
            resultado = evaluar_licitacion(
                proveedor, licitacion, coberturas_por_cliente.get(proveedor.get("id"), [])
            )
            if resultado["coincidencia_tematica"] and (resultado["coincide"] or incluir_fuera_de_cobertura):
                resultados.append(resultado)
    return resultados
