"""TAPPAD Radar: operaciones de catálogo para backend confiable.

Este módulo NO es un endpoint público. La identidad/autorización del cliente
debe verificarse en la capa de aplicación antes de invocar guardar_preferencias.
La clave de servicio solo se utiliza en el servidor; nunca en el navegador.
"""
import json
import os
import re
import urllib.parse
import urllib.request
import urllib.error

ORIGENES = {"SAT", "CUCOP", "MANUAL"}

def _request(method, path, payload=None, prefer=None):
    url = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1/" + path
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    headers = {"apikey": key, "Accept": "application/json"}
    if not key.startswith("sb_secret_"):
        headers["Authorization"] = "Bearer " + key
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if prefer:
        headers["Prefer"] = prefer
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as res:
        body = res.read()
        return json.loads(body) if body else []

def buscar_catalogo(termino, sistema=None, limite=25):
    """Busca por código o texto. Solo lectura; máximo 50 resultados."""
    termino = str(termino).strip()
    if len(termino) < 2 or len(termino) > 100:
        raise ValueError("La búsqueda debe tener entre 2 y 100 caracteres")
    if sistema is not None and sistema not in {"SAT", "CUCOP"}:
        raise ValueError("Sistema inválido")
    limite = int(limite)
    if not 1 <= limite <= 50:
        raise ValueError("Límite fuera de rango")
    # Escapar caracteres de filtros PostgREST y de LIKE.
    patron = re.sub(r"([%_*\\])", r"\\\1", termino)
    filtro = f"or=(clave.ilike.*{patron}*,descripcion.ilike.*{patron}*)"
    params = {"select": "sistema,clave,descripcion,version", "limit": str(limite),
              "order": "sistema.asc,descripcion.asc"}
    if sistema:
        params["sistema"] = "eq." + sistema
    ruta = "catalogos_oficiales_tappad?" + urllib.parse.urlencode(params) + "&" + urllib.parse.quote(filtro, safe="=(),.*")
    return _request("GET", ruta)

def preparar_preferencias(cliente_id, selecciones):
    """Valida selección múltiple sin modificar datos."""
    if not isinstance(cliente_id, int) or isinstance(cliente_id, bool) or cliente_id <= 0:
        raise ValueError("cliente_id inválido")
    if not isinstance(selecciones, list) or len(selecciones) > 100:
        raise ValueError("Se permiten hasta 100 actividades")
    resultado, vistos = [], set()
    for item in selecciones:
        if not isinstance(item, dict):
            raise ValueError("Selección inválida")
        origen = str(item.get("origen", "")).upper().strip()
        clave = str(item.get("clave") or "").strip() or None
        descripcion = str(item.get("descripcion") or "").strip()
        version = str(item.get("version") or "").strip() or None
        if origen not in ORIGENES or not 1 <= len(descripcion) <= 500:
            raise ValueError("Origen o descripción inválidos")
        if origen == "MANUAL":
            if clave is not None:
                raise ValueError("Una actividad manual no admite clave")
            version = None
        elif not clave or not version:
            raise ValueError("SAT y CUCOP requieren clave y versión")
        identidad = (origen, clave or descripcion.casefold(), version)
        if identidad in vistos:
            continue
        vistos.add(identidad)
        resultado.append({"cliente_id": cliente_id, "origen": origen,
                          "clave": clave, "version": version,
                          "descripcion": descripcion, "activo": True})
    return resultado

def guardar_preferencias(cliente_id, selecciones):
    """Uso EXCLUSIVO en backend tras autorizar que el usuario administra cliente_id.

    Solo agrega registros; no borra preferencias anteriores. El backend debe
    comprobar además que cada clave/version SAT o CUCOP existe en catálogo.
    """
    registros = preparar_preferencias(cliente_id, selecciones)
    if not registros:
        return []
    # Validar contra catálogo para impedir claves inventadas.
    for r in registros:
        if r["origen"] == "MANUAL":
            continue
        q = urllib.parse.urlencode({"select": "clave", "sistema": "eq." + r["origen"],
            "clave": "eq." + r["clave"], "version": "eq." + r["version"], "limit": "1"})
        if not _request("GET", "catalogos_oficiales_tappad?" + q):
            raise ValueError("Clave no encontrada en catálogo: " + r["origen"] + "/" + r["clave"])
    return _request("POST", "clientes_giros_preferencias_tappad", registros, "return=representation")
