"""Cruce controlado de giros y alertas de prueba de TAPPAD Radar.
Requiere fichas SECOP locales actuales y consulta Supabase; no usa muestras antiguas.
Por defecto solo genera HTML y JSON. --enviar envía únicamente a dos cuentas permitidas.
"""
import argparse
import html
import json
import os
import re
import smtplib
import unicodedata
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from preparar_prueba_integral_tappad import ROOT, SECOP, consulta_comprasmx, ficha_comprasmx, ficha_secop

PERMITIDOS = {"tappadcons@gmail.com", "gerardotapia112188@gmail.com"}
SALIDA = ROOT / "documentos_secop_lote"
PATRONES = {
 1:r"material(?:es)? de limpieza|detergente|desinfectante|jabon",
 2:r"papeleria|articulos de oficina|utiles de escritorio",
 3:r"computo|computadora|software|informatica|tecnolog|equipo tecnologico|seguridad informatica",
 4:r"mobiliario|muebles de oficina",
 5:r"medicamento|farmaceutic",
 6:r"material medico|material hospitalario|insumo medico|material de laboratorio",
 7:r"equipo medico|equipo de laboratorio|equipamiento de laboratorio",
 8:r"servicio de limpieza|limpieza integral|jardineria|aseo",
 9:r"vigilancia|seguridad privada|guardias de seguridad",
 10:r"mantenimiento de inmuebles|mantenimiento de edificios|rehabilitacion de inmuebles",
 11:r"mantenimiento vehicular|mantenimiento de vehiculos|reparacion de vehiculos",
 12:r"aire acondicionado|climatizacion|hvac",
 13:r"obra publica|construccion|rehabilitacion de (?:obra|cancha|plaza)|colector sanitario|pozo profundo|agua potable|alcantarillado",
 14:r"material electrico|iluminacion|luminarias",
 15:r"ferreteria|herramientas|malla ciclonica",
 16:r"uniformes|vestuario",
 17:r"alimentos|abarrotes|despensa",
 18:r"capacitacion|cursos|formacion",
 19:r"consultoria|asesoria|servicios profesionales",
 20:r"transporte|logistica|vehiculos|automoviles",
}
def normalizar(t):
 return "".join(c for c in unicodedata.normalize("NFD",str(t or "").lower()) if unicodedata.category(c)!="Mn")
def api(tabla, params):
 base=os.getenv("SUPABASE_URL","").rstrip("/")
 key=os.getenv("SUPABASE_ADMIN_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
 if not base or not key: raise RuntimeError("Faltan credenciales Supabase")
 req=Request(base+"/rest/v1/"+tabla+"?"+urlencode(params),headers={"apikey":key,"Authorization":"Bearer "+key})
 with urlopen(req,timeout=40) as r:return json.load(r)
def perfiles():
 clientes=api("clientes",{"select":"id,empresa,correo,palabras_clave,activo,correos_prueba","limit":1000})
 enlaces=api("clientes_giros",{"select":"cliente_id,giro_id","limit":5000})
 por_cliente={}
 for x in enlaces:por_cliente.setdefault(x["cliente_id"],set()).add(int(x["giro_id"]))
 return [dict(c,giros=por_cliente.get(c["id"],set())) for c in clientes if c["empresa"].startswith("[PRUEBA]") or c["correo"] in PERMITIDOS]
def coincidencias(f,cliente):
 texto=normalizar(f.get("objeto"))
 giros=[g for g in cliente["giros"] if g in PATRONES and re.search(PATRONES[g],texto)]
 claves=[normalizar(p.strip()) for p in (cliente.get("palabras_clave") or "").split(",") if len(p.strip())>=5]
 palabras=[p for p in claves if p in texto]
 # El perfil debe tener una coincidencia verificable; las palabras clave no reemplazan el giro.
 return giros, palabras
def render_ficha(f,giros,palabras):
 esc=lambda v:html.escape(str(v or "No identificada"))
 fechas=[("Publicación",f["publicacion"]),("Junta de aclaraciones",f["junta"]),("Presentación y apertura",f["apertura"]),("Fallo programado",f["fallo"])]
 filas="".join("<tr><th>"+esc(k)+"</th><td>"+esc(v)+"</td></tr>" for k,v in fechas)
 faltantes=[k for k,v in fechas if not v or v=="No identificada"]
 aviso=("<p><strong>Atención:</strong> no fue posible identificar "+esc(", ".join(faltantes))+". Es necesario revisar las bases oficiales del procedimiento.</p>") if faltantes else ""
 enlace=f.get("url")
 link='<p><a href="'+esc(enlace)+'">Consultar procedimiento oficial</a></p>' if enlace and str(enlace).startswith("https://") else ""
 return "<section style='border:1px solid #ddd;padding:16px;margin:14px 0'><h3>"+esc(f["numero"])+"</h3><p>"+esc(f["fuente"])+" — "+esc(f["objeto"])+"</p><table>"+filas+"</table>"+aviso+link+"</section>"
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--enviar",action="store_true")
 p.add_argument("--historico-prueba",action="store_true")
 args=p.parse_args()
 if not SECOP.exists():raise SystemExit("Faltan fichas SECOP actuales")
 data=json.loads(SECOP.read_text(encoding="utf-8-sig"))
 hoy=datetime.now().date().isoformat()
 if data.get("fecha_consulta")!=hoy and not args.historico_prueba:
  raise SystemExit("Fichas SECOP no son del día de hoy. Usa --historico-prueba para simulación histórica")
 historico=data.get("fecha_consulta")!=hoy
 if historico:print("SIMULACIÓN HISTÓRICA SECOP:",data.get("fecha_consulta"),"No son publicaciones de hoy")
 remotas,error=consulta_comprasmx()
 if error:raise SystemExit("ComprasMX no actualizado: "+error)
 fichas=[ficha_secop(f) for f in data.get("fichas",[])]+[ficha_comprasmx(f) for f in remotas[:100]]
 if not fichas:raise SystemExit("No hay oportunidades para analizar")
 salida=[]
 mensajes=[]
 for cliente in perfiles():
  elegidas=[]
  for f in fichas:
   giros,claves=coincidencias(f,cliente)
   if giros:elegidas.append((f,giros,claves))
  destino=cliente.get("correo","").lower().strip()
  if destino not in PERMITIDOS:
   destinos=[x.lower().strip() for x in cliente.get("correos_prueba",[]) if x.lower().strip() in PERMITIDOS]
  else:destinos=[destino]
  salida.append({"cliente_id":cliente["id"],"empresa":cliente["empresa"],"giros":sorted(cliente["giros"]),"coincidencias":len(elegidas),"destinos_prueba":destinos,"procedimientos":[{"fuente":f["fuente"],"numero":f["numero"],"giros_coincidentes":g} for f,g,_ in elegidas]})
  if not elegidas or not destinos:continue
  cuerpo="<html><body style='font-family:Arial;color:#18324a'><h2>TAPPAD Radar — prueba de coincidencias</h2><p>Perfil: "+html.escape(cliente["empresa"])+"</p>"
  if historico:cuerpo+="<p><strong>SIMULACIÓN HISTÓRICA:</strong> expedientes SECOP de "+html.escape(str(data.get("fecha_consulta")))+". No representan publicaciones nuevas de hoy.</p>"
  cuerpo+="".join(render_ficha(f,g,c) for f,g,c in elegidas)
  cuerpo+="<p>TAPPAD Consultoría puede asesorarte para participar en estos procedimientos.</p><small>PRUEBA INTERNA. Verifica siempre las bases y los calendarios oficiales.</small></body></html>"
  ruta=SALIDA/("alerta_prueba_cliente_"+str(cliente["id"])+".html")
  ruta.write_text(cuerpo,encoding="utf-8")
  mensajes.append((cliente,destinos,cuerpo))
 reporte=SALIDA/"cruce_giros_prueba_integral.json"
 reporte.write_text(json.dumps({"fecha_prueba":hoy,"fecha_fichas_secop":data.get("fecha_consulta"),"modo_historico":historico,"comprasmx_consultadas":len(remotas[:100]),"secop_consultadas":len(data.get("fichas",[])),"perfiles":salida,"correos_preparados":len(mensajes),"correos_enviados":0},ensure_ascii=False,indent=2),encoding="utf-8")
 print("Cruce realizado. Perfiles:",len(salida),"| correos preparados:",len(mensajes),"| reporte:",reporte)
 if args.enviar and historico:raise SystemExit("Envío bloqueado: datos SECOP históricos; solo simulación")
 if not args.enviar:
  print("SIMULACIÓN: sin correos. Revisar HTML individuales y JSON. Para enviar usar --enviar.")
  return
 usuario=os.getenv("SMTP_USER","").lower().strip()
 clave=os.getenv("SMTP_APP_PASSWORD")
 if usuario not in PERMITIDOS or not clave:raise SystemExit("SMTP de prueba no configurado")
 with smtplib.SMTP("smtp.gmail.com",587,timeout=35) as smtp:
  smtp.ehlo();smtp.starttls();smtp.ehlo();smtp.login(usuario,clave)
  for cliente,destinos,cuerpo in mensajes:
   msg=EmailMessage()
   msg["Subject"]="PRUEBA TAPPAD Radar | "+cliente["empresa"]
   msg["From"]=usuario
   msg["To"]=", ".join(destinos)
   msg.set_content("Prueba de coincidencias de giros TAPPAD Radar. Consultar HTML.")
   msg.add_alternative(cuerpo,subtype="html")
   smtp.send_message(msg)
   print("Gmail aceptó alerta de prueba:",cliente["id"],"a",", ".join(destinos))
 print("No se notificaron destinatarios fuera de las dos cuentas autorizadas.")
if __name__=="__main__":main()
