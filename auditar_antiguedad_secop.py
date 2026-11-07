"""Auditoria local de antiguedad SECOP; solo lectura, sin Supabase ni correos."""
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

RUTA=Path(__file__).with_name("secop_vigentes_actuales.json")
def main():
    d=json.loads(RUTA.read_text(encoding="utf-8-sig"))
    hoy=datetime.now(ZoneInfo("America/Monterrey")).date().isoformat()
    if d.get("fecha_consulta")!=hoy or not d.get("filtros_aplicados") or d.get("error") or d.get("errores") or d.get("coincide_total") is False:
        raise SystemExit("Reporte SECOP no validado o no corresponde a hoy.")
    registros=d.get("registros") or []
    if len(registros)!=d.get("total_unicos"):raise SystemExit("Total de registros inconsistente")
    anios=Counter((r.get("fecha_publicacion") or "SIN FECHA")[:4] for r in registros)
    print("TOTAL MARCADOS VIGENTE EN PORTAL:",len(registros))
    print("PUBLICACIONES POR ANIO:")
    for anio,n in sorted(anios.items()):print(" ",anio,":",n)
    print("NOTA: El JSON del portal no contiene fechas de apertura verificadas.")
    print("NINGUNO de estos registros se considera apto para alerta solo por su estatus.")
    print("SOLO LECTURA. Sin escrituras, sin correos, sin importacion.")
if __name__=="__main__":main()
