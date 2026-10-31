"""TAPPAD Radar: búsqueda SAT/CUCOP y preparación de preferencias.

Módulo exclusivamente de servidor. No incluir claves de servicio en frontend.
El guardado exige un verificador de autorización inyectado por la aplicación.
"""
import json
import os
import urllib.parse
import urllib.request

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
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as response:
        body = response.read()
        return json.loads(body) if body else []


def buscar_catalogo(termino, sistema=None, limite=25):
    """Búsqueda por código o descripción, con parámetros restringidos."""
    termino = str(termino).strip()
    if not 2 <= len(termino) <= 100:
        raise ValueError("La búsqueda debe tener entre 2 y 100 caracteres")
    if any(c in termino for c in ",().*%\\"):
        raise ValueError("La búsqueda contiene caracteres reservados")
    if sistema is not None and sistema not in {"SAT", "CUCOP"}:
        raise ValueError("Sistema inválido")
    limite = int(limite)
    if not 1 <= limite <= 50:
        raise ValueError("Límite fuera de rango")
    params = {"select": "sistema,clave,descripcion,version", "limit": str(limite),
              "order": "sistema.asc,descripcion.asc"}
    if sistema:
        params["sistema"] = "eq." + sistema
    filtro = "or=(clave.ilike.*{0}*,descripcion.ilike.*{0}*)".format(termino)
    ruta = ("catalogos_oficiales_tappad?" + urllib.parse.urlencode(params)
            + "&" + urllib.parse.quote(filtro, safe="=(),.*"))
    return _request("GET", ruta)


def preparar_preferencias(cliente_id, selecciones):
    """Valida y elimina duplicados dentro de la selección recibida."""
    if type(cliente_id) is not int or cliente_id <= 0:
        raise ValueError("cliente_id inválido")
    if not isinstance(selecciones, list) or len(selecciones) > 100:
        raise ValueError("Se permiten hasta 100 actividades")
    resultado, vistos = [], set()
    for item in selecciones:
        if not isinstance(item, dict):
            raise ValueError("Selección inválida")
        origen = str(item.get("origen") or "").strip().upper()
        clave = str(item.get("clave") or "").strip() or None
        descripcion = str(item.get("descripcion") or "").strip()
        version = str(item.get("version") or "").strip() or None
        if origen not in ORIGENES or not 1 <= len(descripcion) <= 500:
            raise ValueError("Origen o descripción inválidos")
        if origen == "MANUAL":
            if clave:
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


def guardar_preferencias(cliente_id, selecciones, *, autorizado):
    """Solo para servidor; autorizado debe ser resultado de verificar la sesión y titularidad.

    Falla cerrado si no se acredita la autorización. No elimina preferencias.
    """
    if autorizado is not True:
        raise PermissionError("Cliente no autorizado")
    registros = preparar_preferencias(cliente_id, selecciones)
    if not registros:
        return []
    for registro in registros:
        if registro["origen"] == "MANUAL":
            continue
        query = urllib.parse.urlencode({
            "select": "clave", "sistema": "eq." + registro["origen"],
            "clave": "eq." + registro["clave"],
            "version": "eq." + registro["version"], "limit": "1"})
        if not _request("GET", "catalogos_oficiales_tappad?" + query):
            raise ValueError("Clave no encontrada en catálogo")
    # Consultar registros existentes para evitar duplicados entre llamadas.
    query = urllib.parse.urlencode({"select": "origen,clave,version,descripcion",
                                    "cliente_id": "eq." + str(cliente_id), "limit": "1000"})
    existentes = _request("GET", "clientes_giros_preferencias_tappad?" + query)
    ids = {(r["origen"], r.get("clave") or r["descripcion"].casefold(), r.get("version"))
           for r in existentes}
    nuevos = [r for r in registros
              if (r["origen"], r["clave"] or r["descripcion"].casefold(), r["version"]) not in ids]
    if not nuevos:
        return []
    return _request("POST", "clientes_giros_preferencias_tappad",
                    nuevos, "return=representation")
