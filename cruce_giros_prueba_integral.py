"""TAPPAD Radar: revisión integral controlada ComprasMX + SECOP.
Lee Supabase y fichas locales. Nunca envía correo ni modifica la base de datos.
Uso: py cruce_giros_prueba_integral.py --historico-prueba
"""
import argparse
import html
import json
import os
import re
import unicodedata
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from preparar_prueba_integral_tappad import ROOT, SECOP, consulta_comprasmx, ficha_comprasmx, ficha_secop

SALIDA = ROOT / "documentos_secop_lote"
PERMITIDOS = {"tappadcons@gmail.com", "gerardotapia112188@gmail.com"}
NO_IDENTIFICADA = "No fue posible identificar esta fecha; revisar directamente las bases oficiales del procedimiento."

# Expresiones deliberadamente específicas: se evitan términos genéricos como
# "servicios", "equipo", "mantenimiento" o "seguridad" aislados.
PATRONES = {
 1: [r"material(?:es)? de limpieza", r"detergentes?", r"desinfectantes?", r"jabon(?:es)?"],
 2: [r"papeleria", r"utiles de escritorio", r"articulos de oficina"],
 3: [r"equipos? de computo", r"computadoras?", r"software", r"seguridad informatica", r"infraestructura tecnologica", r"servicios? (?:de )?tecnologias? de la informacion"],
 4: [r"mobiliario", r"muebles de oficina"],
 5: [r"medicamentos?", r"farmaceutic"],
 6: [r"material(?:es)? medic", r"material(?:es)? hospitalari", r"insumos? medic", r"material(?:es)? de laboratorio"],
 7: [r"equipos? medic", r"equipos? de laboratorio", r"equipamiento de laboratorio"],
 8: [r"servicios? de limpieza", r"limpieza integral", r"jardineria", r"servicios? de aseo"],
 9: [r"servicios? de vigilancia", r"seguridad privada", r"guardias? de seguridad"],
 10: [r"mantenimiento de inmuebles", r"mantenimiento de edificios", r"rehabilitacion de inmuebles"],
 11: [r"mantenimiento (?:de )?vehicul", r"reparacion de vehicul", r"servicio mecanico automotriz"],
 12: [r"aire acondicionado", r"climatizacion", r"\bhvac\b"],
 13: [r"obra publica", r"construccion", r"rehabilitacion de (?:obra|cancha|plaza|vialidad)", r"colector sanitario", r"pozos? profundos?", r"agua potable", r"alcantarillado", r"infraestructura hidraulica"],
 14: [r"material electrico", r"iluminacion", r"luminarias"],
 15: [r"ferreteria", r"herramientas", r"malla ciclonica"],
 16: [r"uniformes?", r"vestuario"],
 17: [r"alimentos?", r"abarrotes", r"despensas?"],
 18: [r"capacitacion", r"cursos? de formacion", r"servicios? de formacion"],
 19: [r"consultoria", r"asesoria", r"servicios? profesionales"],
 20: [r"servicios? de transporte", r"servicios? de logistica", r"adquisicion de vehiculos", r"adquisicion de automoviles"],
}
# Si una palabra clave no figura en el objeto no genera coincidencia por sí sola.
# Solo refuerza el motivo de una coincidencia ya sustentada por un giro.
def normalizar(valor):
 t = unicodedata.normalize("NFD", str(valor or "").casefold())
 return re.sub(r"\s+", " ", "".join(c for c in t if unicodedata.category(c) != "Mn")).strip()

def api(tabla, parametros):
 base = os.getenv("SUPABASE_URL", "").rstrip("/")
 clave = os.getenv("SUPABASE_ADMIN_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
 if not base or not clave:
  raise RuntimeError("Faltan SUPABASE_URL y SUPABASE_ADMIN_KEY/SUPABASE_SERVICE_ROLE_KEY")
 url = base + "/rest/v1/" + tabla + "?" + urlencode(parametros)
 peticion = Request(url, headers={"apikey": clave, "Authorization": "Bearer " + clave})
 with urlopen(peticion, timeout=40) as respuesta:
  return json.load(respuesta)

def perfiles():
 clientes = api("clientes", {"select":"id,empresa,correo,palabras_clave,activo,correos_prueba", "limit":1000})
 relaciones = api("clientes_giros", {"select":"cliente_id,giro_id", "limit":5000})
 catalogo = api("giros_comerciales", {"select":"id,nombre,activo", "limit":1000})
 nombres = {int(g["id"]):g["nombre"] for g in catalogo if g.get("activo") is not False}
 por_cliente = defaultdict(set)
 for r in relaciones:
  gid = int(r["giro_id"])
  if gid in nombres: por_cliente[r["cliente_id"]].add(gid)
 salida = []
 for c in clientes:
  if not (str(c.get("empresa") or "").startswith("[PRUEBA]") or str(c.get("correo") or "").casefold() in PERMITIDOS):
   continue
  c["giros"] = sorted(por_cliente[c["id"]])
  c["nombres_giros"] = {g:nombres[g] for g in c["giros"]}
  salida.append(c)
 return salida

def motivo(ficha, cliente):
 objeto = normalizar(ficha.get("objeto"))
 giros = []
 evidencias = []
 for giro in cliente["giros"]:
  patrones = PATRONES.get(giro, [])
  encontrados = [m.group(0) for patron in patrones for m in [re.search(patron, objeto)] if m]
  if encontrados:
   giros.append(giro)
   evidencias.append({"giro_id":giro,"giro":cliente["nombres_giros"][giro],"frases_objeto":sorted(set(encontrados))})
 claves = [normalizar(x) for x in str(cliente.get("palabras_clave") or "").split(",")]
 claves = sorted(set(x for x in claves if len(x)>=5 and x in objeto))
 return giros, evidencias, claves

def fecha_real(valor):
 if not valor or normalizar(valor) in ("no identificada", "none", "null"):
  return None
 try:
  return datetime.fromisoformat(str(valor).replace("Z","+00:00")).date()
 except ValueError:
  return None

def estado_plazo(ficha, hoy):
 apertura = fecha_real(ficha.get("apertura"))
 if apertura and apertura < hoy: return "PLAZO_VENCIDO"
 if apertura and apertura >= hoy: return "PLAZO_NO_VENCIDO_SEGUN_FECHA_REGISTRADA_NO_VERIFICADO"
 return "PLAZO_NO_IDENTIFICADO"

def ficha_html(ficha, coincidencia):
 esc = lambda v: html.escape(str(v if v not in (None,"","No identificada") else NO_IDENTIFICADA))
 fechas = [("Publicación",ficha.get("publicacion")),("Junta de aclaraciones",ficha.get("junta")),("Límite de presentación y apertura",ficha.get("apertura")),("Fallo programado",ficha.get("fallo"))]
 tabla = "".join("<tr><th>"+html.escape(nombre)+"</th><td>"+esc(valor)+"</td></tr>" for nombre,valor in fechas)
 url = ficha.get("url")
 enlace = '<a href="'+html.escape(url,quote=True)+'">Ver procedimiento</a>' if isinstance(url,str) and url.startswith("https://") else "Enlace individual no disponible"
 return ("<article><h3>"+esc(ficha.get("numero"))+"</h3><p><strong>"+esc(ficha.get("fuente"))+"</strong> — "+esc(ficha.get("objeto"))+"</p>"
         "<p>Giros: "+esc(", ".join(e["giro"] for e in coincidencia["evidencias"]))+"</p>"
         "<p>Estado del plazo: "+esc(coincidencia["estado_plazo"])+"</p><table>"+tabla+"</table><p>"+enlace+"</p></article>")

def main():
 parser = argparse.ArgumentParser()
 parser.add_argument("--historico-prueba", action="store_true", help="Permite revisar fichas SECOP anteriores, siempre sin enviar correos")
 parser.add_argument("--enviar", action="store_true", help="No disponible: bloqueo preventivo de envíos")
 args = parser.parse_args()
 if args.enviar:
  raise SystemExit("ENVÍO BLOQUEADO: esta versión es solo de revisión. No se enviaron correos.")
 if not SECOP.exists():
  raise SystemExit("Faltan fichas comerciales SECOP locales.")
 secop = json.loads(SECOP.read_text(encoding="utf-8-sig"))
 hoy = date.today()
 fecha_secop = secop.get("fecha_consulta")
 historico = fecha_secop != hoy.isoformat()
 if historico and not args.historico_prueba:
  raise SystemExit("Las fichas SECOP son anteriores. Para revisión sin envío usa --historico-prueba.")
 remotas, error = consulta_comprasmx()
 if error: raise SystemExit("No se pudo consultar ComprasMX en Supabase: "+error)
 compras = remotas[:100]
 # Se conserva el estado de la fuente. No se interpreta una consulta a Supabase
 # como descarga fresca del CSV ni como validación de vigencia.
 fichas = []
 for origen, originales, convertir in (("SECOP Coahuila",secop.get("fichas",[]),ficha_secop),("ComprasMX",compras,ficha_comprasmx)):
  for registro in originales:
   ficha = convertir(registro)
   ficha["origen_datos"] = "FICHAS_LOCALES_HISTORICAS" if origen=="SECOP Coahuila" and historico else ("FICHAS_LOCALES" if origen=="SECOP Coahuila" else "SUPABASE_SIN_VERIFICACION_CSV_ACTUAL")
   ficha["estatus_fuente"] = registro.get("estatus") or registro.get("estatus_portal") or "NO_INFORMADO"
   fichas.append(ficha)
 unicas = {}
 for f in fichas:
  clave = (normalizar(f["fuente"]),normalizar(f.get("numero")))
  if clave[1]: unicas[clave] = f
 fichas = list(unicas.values())
 clientes = perfiles()
 resultados = []
 agrupados = defaultdict(dict)
 for cliente in clientes:
  destinos = []
  correo = str(cliente.get("correo") or "").strip().casefold()
  if correo in PERMITIDOS: destinos = [correo]
  else: destinos = [str(x).strip().casefold() for x in (cliente.get("correos_prueba") or []) if str(x).strip().casefold() in PERMITIDOS]
  destinos = sorted(set(destinos))
  matches = []
  for ficha in fichas:
   giros, evidencias, claves = motivo(ficha, cliente)
   if not giros: continue
   coincidencia = {
    "fuente":ficha["fuente"],"numero":ficha["numero"],"objeto":ficha.get("objeto"),
    "giros_coincidentes":giros,"evidencias":evidencias,"palabras_clave_en_objeto":claves,
    "calendario":{"publicacion":ficha.get("publicacion"),"junta_aclaraciones":ficha.get("junta"),"limite_presentacion_apertura":ficha.get("apertura"),"fallo_programado":ficha.get("fallo")},
    "estado_plazo":estado_plazo(ficha,hoy),"estatus_fuente":ficha["estatus_fuente"],"origen_datos":ficha["origen_datos"],
    "url_procedimiento":ficha.get("url"),
    "requiere_validacion_oficial":True
   }
   matches.append(coincidencia)
   for destino in destinos:
    clave = (normalizar(ficha["fuente"]),normalizar(ficha.get("numero")))
    entrada = agrupados[destino].setdefault(clave,{"ficha":ficha,"perfiles":[]})
    entrada["perfiles"].append({"cliente_id":cliente["id"],"empresa":cliente["empresa"],"coincidencia":coincidencia})
  resultados.append({"cliente_id":cliente["id"],"empresa":cliente["empresa"],"giros":cliente["giros"],"nombres_giros":cliente["nombres_giros"],"coincidencias":len(matches),"destinos_prueba":destinos,"procedimientos":matches})
 SALIDA.mkdir(parents=True,exist_ok=True)
 resumen_destinos = []
 for destino, procedimientos in sorted(agrupados.items()):
  elementos = list(procedimientos.values())
  contenido = ['<!doctype html><html lang="es"><meta charset="utf-8"><title>Vista previa TAPPAD Radar</title><body style="font-family:Arial;max-width:850px;margin:auto;color:#18324a"><h1>TAPPAD Radar — vista previa</h1><p><strong>SIMULACIÓN INTERNA. NO ES UNA ALERTA DE OPORTUNIDADES VIGENTES.</strong> Verifica fechas y bases oficiales. No se enviaron correos.</p>']
  for elemento in elementos:
   perfiles_texto = ", ".join(p["empresa"] for p in elemento["perfiles"])
   contenido.append("<p>Perfiles asociados: "+html.escape(perfiles_texto)+"</p>")
   contenido.append(ficha_html(elemento["ficha"],elemento["perfiles"][0]["coincidencia"]))
  contenido.append("</body></html>")
  nombre = "vista_previa_destino_"+("tappadcons" if destino=="tappadcons@gmail.com" else "gerardotapia")+".html"
  ruta = SALIDA/nombre
  ruta.write_text("\n".join(contenido),encoding="utf-8")
  resumen_destinos.append({"correo_prueba":destino,"procedimientos_unicos":len(elementos),"perfiles_asociados":sorted(set(p["empresa"] for e in elementos for p in e["perfiles"])),"archivo_html":str(ruta)})
 reporte = {
  "fecha_prueba":hoy.isoformat(),"fecha_fichas_secop":fecha_secop,"modo_historico":historico,
  "origen_comprasmx":"Supabase: consulta de registros, NO descarga CSV fresca ni verificación de vigencia",
  "comprasmx_consultadas":len(compras),"secop_consultadas":len(secop.get("fichas",[])),
  "perfiles":resultados,"destinatarios_consolidados":resumen_destinos,
  "correos_preparados_para_envio":0,"correos_enviados":0,
  "observaciones":["La coincidencia por giro es una preclasificación; verificar objeto, bases y requisitos.","Los plazos no se consideran oficialmente vigentes por este reporte.","La vista previa se consolida por destinatario y procedimiento para evitar duplicados."]
 }
 ruta = SALIDA/"cruce_giros_prueba_integral.json"
 ruta.write_text(json.dumps(reporte,ensure_ascii=False,indent=2),encoding="utf-8")
 print("Revisión completada | ComprasMX:",len(compras),"| SECOP:",len(secop.get("fichas",[])),"| perfiles:",len(resultados))
 print("Destinatarios de vista previa:",len(resumen_destinos),"| correos enviados: 0")
 print("Reporte:",ruta)
 for d in resumen_destinos: print("Vista previa:",d["archivo_html"],"| procedimientos únicos:",d["procedimientos_unicos"])
 print("No se modificó Supabase ni se enviaron correos.")

if __name__ == "__main__":
 main()
