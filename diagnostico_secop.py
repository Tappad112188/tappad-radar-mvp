"""Diagnóstico público y no invasivo de acceso a SECOP Coahuila.

Solo realiza solicitudes GET al portal público. No evita restricciones,
no descarga bases de pago ni escribe en Supabase.
"""
import json
import urllib.error
import urllib.request

URLS = [
    "https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria",
    "https://www.sefincoahuila.gob.mx/sistemas/Secop/",
]


def diagnosticar(url, timeout=20):
    request = urllib.request.Request(url, headers={"User-Agent": "TAPPAD-Radar/1.0 (consulta publica)"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            contenido = response.read(50000)
            return {"url": url, "http": response.status, "bytes_muestra": len(contenido),
                    "tipo": response.headers.get("Content-Type", "")}
    except urllib.error.HTTPError as error:
        return {"url": url, "http": error.code, "estado": "acceso_no_disponible"}
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return {"url": url, "estado": "error_conexion", "tipo_error": type(error).__name__}


if __name__ == "__main__":
    print(json.dumps([diagnosticar(url) for url in URLS], ensure_ascii=False, indent=2))
