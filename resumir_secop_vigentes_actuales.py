"""Compara extracciones SECOP sin modificar bases ni enviar correos.
Requiere secop_vigentes_actuales.json y opcionalmente secop_hoy_vigentes.json.
"""
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
BASE=Path(__file__).resolve().parent
def leer(nombre):
 p=BASE/nombre
 if not p.exists():raise SystemExit("Falta archivo: "+nombre)
 d=json.loads(p.read_text(encoding="utf-8-sig"))
 if not d.get("filtros_aplicados") or d.get("error") or d.get("errores") or d.get("coincide_total") is False:
  raise SystemExit("Extraccion no validada: "+nombre+"; revisar reporte.")
 return d
def main():
 d=leer("secop_vigentes_actuales.json")
 hoy=datetime.now(ZoneInfo("America/Monterrey")).date().isoformat()
 if d.get("fecha_consulta")!=hoy:raise SystemExit("Extraccion no corresponde al dia actual.")
 regs=d.get("registros") or []
 if len(regs)!=d.get("total_unicos"):raise SystemExit("Conteo inconsistente de SECOP")
 nuevos=[r for r in regs if r.get("fecha_publicacion")==hoy]
 anteriores=[r for r in regs if r.get("fecha_publicacion")!=hoy]
 print("SECOP VIGENTES EN PORTAL:",len(regs))
 print("PUBLICADOS HOY:",len(nuevos))
 print("PUBLICADOS ANTES Y AUN VIGENTES:",len(anteriores))
 print("PRIMEROS CODIGOS VIGENTES:",", ".join(r["codigo"] for r in regs[:10]))
 print("SOLO LECTURA: sin importacion, sin correos, sin escrituras Supabase.")
if __name__=="__main__":main()
