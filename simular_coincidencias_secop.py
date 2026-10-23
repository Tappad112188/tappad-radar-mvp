"""TAPPAD Radar - simulador local de coincidencias por giro.
No usa red, no modifica Airtable/Supabase ni envia correos.
"""
import json,re,unicodedata
from pathlib import Path
BASE=Path(__file__).resolve().parent/"documentos_secop_lote"
ENTRADA=BASE/"fichas_comerciales_secop.json"
SALIDA=BASE/"simulacion_coincidencias_secop.json"
PROVEEDORES=[
 {"nombre":"HOSPICLEAN SA DE CV","especialidad":"Servicios integrales de laboratorio clínico","tipo":"registrado_airtable"},
 {"nombre":"EJEMPLO - Empresa de limpieza","especialidad":"Limpieza y jardinería de inmuebles","tipo":"simulado"},
 {"nombre":"EJEMPLO - Empresa de vigilancia","especialidad":"Seguridad y vigilancia privada","tipo":"simulado"},
 {"nombre":"EJEMPLO - Contratista hidráulico","especialidad":"Construcción de pozos profundos y obras de agua potable","tipo":"simulado"}
]
REGLAS={
 "limpieza_jardineria":r"limpieza|jardineria|aseo|intendencia",
 "seguridad_vigilancia":r"vigilancia|seguridad privada|guardias|custodia",
 "obra_hidraulica":r"pozos? profundos?|agua potable|perforacion|obras? hidraulicas?|saneamiento|alcantarillado",
 "obra_publica_general":r"construccion|obra publica|contratista|rehabilitacion",
 "laboratorio_clinico":r"laboratorio clinico|analisis clinicos|reactivos clinicos",
}
def norm(s):
 return "".join(c for c in unicodedata.normalize("NFD",str(s).lower()) if unicodedata.category(c)!="Mn")
def giros(s):
 t=norm(s)
 return sorted(k for k,p in REGLAS.items() if re.search(p,t))
def main():
 if not ENTRADA.exists():raise SystemExit("Falta documentos_secop_lote/fichas_comerciales_secop.json")
 datos=json.loads(ENTRADA.read_text(encoding="utf-8-sig"))
 resultados=[]
 for p in PROVEEDORES:
  pg=giros(p["especialidad"]);coincidencias=[]
  for f in datos.get("fichas",[]):
   fg=f.get("categorias_sugeridas",[])
   comunes=sorted(set(pg)&set(fg))
   if not comunes:continue
   c=f.get("calendario",{})
   coincidencias.append({"codigo":f.get("codigo"),"referencia":f.get("referencia"),"objeto":f.get("objeto"),"giros_coincidentes":comunes,"publicacion":f.get("publicacion"),"junta_aclaraciones":c.get("junta_aclaraciones"),"presentacion_apertura":c.get("limite_presentacion_propuestas"),"fallo_programado":c.get("fallo_programado"),"estado":"coincidencia_por_giro_no_confirma_elegibilidad"})
  resultados.append({"proveedor":p["nombre"],"tipo":p["tipo"],"especialidad":p["especialidad"],"giros_detectados":pg,"coincidencias":coincidencias})
 SALIDA.write_text(json.dumps({"modo":"simulacion_sin_envios","proveedores":resultados},ensure_ascii=False,indent=2),encoding="utf-8")
 for p in resultados:
  print(p["proveedor"],"->",len(p["coincidencias"]),"coincidencia(s)")
  for f in p["coincidencias"]:print("  ",f["codigo"],"|",",".join(f["giros_coincidentes"]))
 print("Resultado:",SALIDA)
 print("Sin escrituras en bases de datos ni correos.")
if __name__=="__main__":main()
