"""Simulación programable de alertas; no consulta bases de datos ni envía mensajes."""
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from preparador_alertas import preparar_alertas

ZONA = ZoneInfo("America/Monterrey")


def ejecutar_simulacion(proveedores, licitaciones, coberturas, historial, ahora=None):
    """Devuelve únicamente métricas y referencias, sin datos personales ni correos."""
    ahora = ahora or datetime.now(ZONA)
    resultado = preparar_alertas(proveedores, licitaciones, coberturas, historial, ahora=ahora)
    return {
        "fecha_revision": ahora.isoformat(),
        "modo": "simulacion_sin_envios",
        "proveedores_evaluados": len(proveedores),
        "licitaciones_evaluadas": len(licitaciones),
        "resumen": resultado["resumen"],
        "alertas_preparadas": [
            {"cliente_id": cliente_id, "licitaciones": [o["licitacion_id"] for o in oportunidades]}
            for cliente_id, oportunidades in sorted(resultado["por_proveedor"].items())
        ],
    }


if __name__ == "__main__":
    # Datos exclusivamente ficticios para comprobar la ejecución del programador.
    proveedores = [{"id": 1, "empresa": "Proveedor ficticio", "palabras_clave": "mantenimiento", "activo": True}]
    licitaciones = [{"id": 1001, "numero_procedimiento": "DEMO-1001",
                    "nombre_procedimiento": "Servicio ficticio de mantenimiento",
                    "descripcion": "Mantenimiento", "tipo_contratacion": "servicios",
                    "entidad_federativa": "Coahuila", "estatus": "vigente",
                    "fecha_apertura": "2099-12-31T12:00:00"}]
    print(json.dumps(ejecutar_simulacion(proveedores, licitaciones, {1: [{"estado": "Coahuila"}]}, []), ensure_ascii=False, indent=2))
