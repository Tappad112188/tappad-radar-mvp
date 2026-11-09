"""Etapa segura SECOP 21 dias: valida extraccion y prepara lista de revision.
No reutiliza expedientes anteriores ni habilita importacion/envio.
"""
import json
from datetime import datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

BASE=Path(__file__).resolve().parent
ENTRADA=BASE/"secop_ultimas_tres_semanas.json"
SALIDA=BASE/"secop_revision_21_dias.json"
def main():
 hoy=datetime.now(ZoneInfo("America/Monterrey")).date()
 inicio=hoy-timedelta(days=21)
 if not ENTRADA.exists():raise SystemExit("Falta extraccion SECOP 21 dias")
 d=json.loads(ENTRADA.read_text(encoding="utf-8-sig"))
 if (d.get("fecha_consulta")!=hoy.isoformat() or d.get("fecha_inicio")!=inicio.isoformat()
     or d.get("fecha_fin")!=hoy.isoformat() or not d.get("filtros_aplicados")
     or d.get("error") or d.get("errores") or d.get("coincide_total") is False):
  raise SystemExit("Extraccion no validada, desactualizada o fuera de ventana")
 registros=d.get("registros") or []
 if len(registros)!=d.get("total_unicos"):raise SystemExit("Conteo inconsistente")
 vistos=set()
 lista=[]
 for r in registros:
  codigo=str(r.get("codigo") or "").strip()
  fecha=r.get("fecha_publicacion")
  if not codigo or codigo in vistos or not fecha or not inicio.isoformat()<=fecha<=hoy.isoformat() or str(r.get("estatus") or "").strip().casefold()!="vigente":
   raise SystemExit("Registro SECOP invalido o duplicado")
  vistos.add(codigo)
  lista.append({"codigo":codigo,"fecha_publicacion":fecha,"descripcion":r.get("descripcion"),
   "estatus_portal":r.get("estatus"),"fecha_apertura":None,
   "validacion_calendario":"pendiente_revision_bases",
   "habilitado_para_notificacion":False})
 lista.sort(key=lambda x:(x["fecha_publicacion"],x["codigo"]),reverse=True)
 SALIDA.write_text(json.dumps({"fecha_consulta":hoy.isoformat(),"ventana_inicio":inicio.isoformat(),
 "ventana_fin":hoy.isoformat(),"total":len(lista),
 "estado":"SOLO_REVISION_SIN_IMPORTACION_NI_ENVIO","registros":lista},ensure_ascii=False,indent=2),encoding="utf-8")
 print("SECOP EN VENTANA 21 DIAS:",len(lista))
 print("PENDIENTES DE CALENDARIO:",len(lista))
 print("REPORTE:",SALIDA)
 print("SIN IMPORTACION SUPABASE NI ENVIO DE CORREOS.")
if __name__=="__main__":main()
