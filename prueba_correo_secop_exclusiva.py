"""Prueba SECOP exclusiva: vista HTML y envio Gmail limitado a dos cuentas.
Por defecto solo genera HTML; --enviar envia el correo de prueba.
No consulta ComprasMX, no modifica Supabase ni ejecuta Chromium.
"""
import argparse,html,json,os,smtplib
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from email.message import EmailMessage

ROOT=Path(__file__).resolve().parent
SALIDA=ROOT/"documentos_secop_lote"/"vista_previa_correo_secop.html"
DESTINATARIOS=("tappadcons@gmail.com","gerardotapia112188@gmail.com")
IDS=("secop-coahuila:ai3-co-e100-2026","secop-coahuila:ai3-co-e101-2026")
def obtener(uid):
 base=os.environ.get("SUPABASE_URL")
 key=os.environ.get("SUPABASE_ADMIN_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
 if not base or not key:raise SystemExit("Faltan variables SUPABASE_URL / SUPABASE_ADMIN_KEY")
 params=urlencode({"select":"uuid_procedimiento,numero_procedimiento,nombre_procedimiento,fecha_publicacion,fecha_junta_aclaraciones,fecha_apertura,fecha_fallo_programado,url_bases,documentos_disponibles,validacion_calendario,estatus,fuente","uuid_procedimiento":"eq."+uid})
 req=Request(base.rstrip("/")+"/rest/v1/licitaciones?"+params,headers={"apikey":key,"Authorization":"Bearer "+key})
 with urlopen(req,timeout=40) as response:rows=json.load(response)
 if len(rows)!=1:raise SystemExit("No se encontro expediente unico: "+uid)
 return rows[0]
def esc(v):return html.escape(str(v or ""),quote=True)
def fecha(v):return esc(str(v).replace("T"," ")[:16]) if v else "No identificada; revisar bases oficiales"
def ficha(r):
 if r.get("fuente")!="SECOP Coahuila" or r.get("estatus")!="Vigente":raise SystemExit("Fuente o estatus inesperado")
 url=r.get("url_bases") or ""
 if not url.startswith("https://www.sefincoahuila.gob.mx/sistemas/Secop/Procedimiento/GetFile/"):
  raise SystemExit("Sin URL oficial de bases: "+r["uuid_procedimiento"])
 docs=r.get("documentos_disponibles") or []
 anexos=[d for d in docs if d.get("tipo")=="bases_y_anexos" and str(d.get("url","")).startswith("https://www.sefincoahuila.gob.mx/sistemas/Secop/Procedimiento/GetFile/")]
 botones='<a style="display:inline-block;padding:11px 15px;margin:8px 8px 8px 0;background:#163e69;color:white;text-decoration:none;border-radius:6px" href="'+esc(url)+'">Consultar bases PDF</a>'
 for d in anexos:botones+='<a style="display:inline-block;padding:11px 15px;margin:8px 8px 8px 0;background:#e8edf4;color:#163e69;text-decoration:none;border-radius:6px" href="'+esc(d["url"])+'">Consultar bases y anexos ZIP (enlace no verificado independientemente)</a>'
 campos=(("Publicación / fecha de identificación",r.get("fecha_publicacion")),("Junta de aclaraciones",r.get("fecha_junta_aclaraciones")),("Presentación y apertura / límite de propuestas",r.get("fecha_apertura")),("Fallo programado",r.get("fecha_fallo_programado")))
 filas="".join("<tr><th style='text-align:left;padding:8px;border-bottom:1px solid #ddd'>"+esc(k)+"</th><td style='padding:8px;border-bottom:1px solid #ddd'>"+fecha(v)+"</td></tr>" for k,v in campos)
 return "<section style='padding:20px;background:#fff;border:1px solid #dce3ea;margin:16px 0;border-radius:8px'><h2>"+esc(r["numero_procedimiento"])+"</h2><p>"+esc(r.get("nombre_procedimiento"))+"</p><table style='width:100%'>"+filas+"</table><p style='font-size:12px;color:#526579'>Fechas de junta, apertura y fallo contrastadas con las bases de estos dos expedientes. La fecha de publicación se muestra conforme al registro del sistema; si no consta expresamente en las bases, corresponde a la primera detección. Los actos pueden modificarse mediante avisos oficiales posteriores.</p>"+botones+"</section>"
def main():
 p=argparse.ArgumentParser();p.add_argument("--enviar",action="store_true");args=p.parse_args()
 rows=[obtener(uid) for uid in IDS]
 cuerpo="<html><body style='font-family:Arial,sans-serif;color:#182b40;background:#f5f7fa;max-width:760px;margin:auto'><header style='background:#163e69;color:white;padding:24px'><h1>TAPPAD Radar</h1><p>PRUEBA INTERNA | Oportunidades SECOP Coahuila | Monitoreo 3 veces al día</p></header>"
 cuerpo+="".join(ficha(r) for r in rows)
 cuerpo+="<footer style='padding:22px'><h3>Asesoria para participar</h3><p>TAPPAD Consultoria puede apoyarte en la preparacion y presentacion de propuestas.</p><p>Esta es una prueba interna. Verifica documentos y fechas oficiales antes de participar. No es notificacion definitiva.</p></footer></body></html>"
 SALIDA.parent.mkdir(exist_ok=True)
 SALIDA.write_text(cuerpo,encoding="utf-8")
 print("SECOP: 2 expedientes | URLs de bases presentes | HTML:",SALIDA)
 print("Destinatarios de prueba:",", ".join(DESTINATARIOS))
 if not args.enviar:
  print("SIMULACION: sin correo enviado. Revisa HTML y usa --enviar para enviar.")
  return
 usuario=os.environ.get("SMTP_USER","").strip()
 clave=os.environ.get("SMTP_APP_PASSWORD","")
 if usuario.lower() not in DESTINATARIOS or not clave:raise SystemExit("Faltan credenciales SMTP o remitente no autorizado; no se envio")
 msg=EmailMessage()
 msg["Subject"]="PRUEBA INTERNA | TAPPAD Radar | 2 licitaciones SECOP Coahuila"
 msg["From"]=usuario;msg["To"]=", ".join(DESTINATARIOS)
 msg.set_content("Prueba interna SECOP Coahuila. Consulta el contenido HTML y los enlaces de bases.")
 msg.add_alternative(cuerpo,subtype="html")
 with smtplib.SMTP("smtp.gmail.com",587,timeout=35) as smtp:
  smtp.ehlo();smtp.starttls();smtp.ehlo();smtp.login(usuario,clave);smtp.send_message(msg)
 print("Gmail acepto el mensaje para las dos cuentas de prueba; no implica entrega o lectura.")
if __name__=="__main__":main()
