"""Piloto SECOP E107: vista previa por defecto, SMTP solo con --enviar.
No altera notificaciones de produccion ni envia a alias del proveedor ficticio.
"""
import argparse,html,json,os,smtplib,ssl
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parent
SALIDA=ROOT/"documentos_secop_lote"
CODIGO="SIDUM-AI3-CO-E107-2026"
DESTINATARIO="gerardotapia112188@gmail.com"
REMITENTE="tappadcons@gmail.com"

def consulta(tabla,params):
    base=os.environ.get("SUPABASE_URL")
    key=os.getenv("SUPABASE_ADMIN_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not base or not key:raise SystemExit("Faltan credenciales Supabase en entorno")
    url=base.rstrip("/")+"/rest/v1/"+tabla+"?"+urlencode(params)
    req=Request(url,headers={"apikey":key,"Authorization":"Bearer "+key,"Accept":"application/json"})
    with urlopen(req,timeout=35) as r:return json.load(r)

def fecha(x,solo_dia=False):
    if not x:return "No disponible"
    dt=datetime.fromisoformat(str(x).replace("Z","+00:00"))
    return dt.strftime("%d/%m/%Y" if solo_dia else "%d/%m/%Y, %H:%M h")

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--enviar",action="store_true",help="Enviar una sola prueba SMTP al correo autorizado")
    args=p.parse_args()
    lic=consulta("licitaciones",{"id":"eq.2753","numero_procedimiento":"eq."+CODIGO,"select":"id,numero_procedimiento,nombre_procedimiento,fecha_publicacion,fecha_junta_aclaraciones,fecha_apertura,fecha_fallo_programado,validacion_calendario,fuente,estatus"})
    # Perfil comercial simulado solo para este ensayo: sin activar clientes reales.
    cli=[{"id":"simulado-e107","empresa":"[PRUEBA] Pavimentacion y obra vial","correo":"sin-destinatario","palabras_clave":"pavimentación, calle, obra vial","activo":False}]
    if len(lic)!=1 or len(cli)!=1:raise SystemExit("BLOQUEADO: registros no unicos")
    l,c=lic[0],cli[0]
    if l["fuente"]!="SECOP Coahuila" or l["validacion_calendario"]!="preliminar_documental" or c["activo"] is not False:
        raise SystemExit("BLOQUEADO: fuente, validacion o proveedor ficticio invalidos")
    if c["correo"]==DESTINATARIO:raise SystemExit("BLOQUEADO: el piloto no debe suplantar la cuenta del proveedor")
    ahora=datetime.now(ZoneInfo("America/Monterrey")).replace(tzinfo=None)
    apertura=datetime.fromisoformat(str(l["fecha_apertura"]).replace("Z","+00:00"))
    if apertura.tzinfo:apertura=apertura.astimezone(ZoneInfo("America/Monterrey")).replace(tzinfo=None)
    if apertura<=ahora:raise SystemExit("BLOQUEADO: apertura vencida")
    descripcion=l["nombre_procedimiento"] or ""
    claves=[x.strip() for x in (c["palabras_clave"] or "").split(",") if x.strip()]
    coincidencias=[x for x in claves if x.casefold() in descripcion.casefold()]
    if not coincidencias:raise SystemExit("BLOQUEADO: sin coincidencia comercial")
    asunto="TAPPAD Radar | PRUEBA SECOP | "+CODIGO
    campos=[
        ("Descripcion del procedimiento",descripcion),
        ("Numero de procedimiento",CODIGO),
        ("Fecha de publicacion",fecha(l["fecha_publicacion"],True)),
        ("Junta de aclaraciones",fecha(l["fecha_junta_aclaraciones"])),
        ("Presentacion y apertura de propuestas",fecha(l["fecha_apertura"])),
        ("Fallo programado",fecha(l["fecha_fallo_programado"])),
        ("Coincidencia con giro",", ".join(coincidencias))]
    texto="TAPPAD RADAR — PRUEBA CONTROLADA SECOP\n\n"+"\n".join(k+": "+str(v) for k,v in campos)+"\n\nFechas documentales preliminares. Verificar modificaciones oficiales posteriores.\nTAPPAD Consultoria ofrece asesoria para participar.\nSin enlaces a bases.\n"
    filas="".join("<tr><th style='text-align:left;padding:9px;border-bottom:1px solid #ddd'>"+html.escape(k)+"</th><td style='padding:9px;border-bottom:1px solid #ddd'>"+html.escape(str(v))+"</td></tr>" for k,v in campos)
    cuerpo="<html><body style='font-family:Arial,sans-serif;color:#15243a'><h2>TAPPAD RADAR</h2><p><b>PRUEBA CONTROLADA — Alerta SECOP Coahuila</b></p><table>"+filas+"</table><p>Fechas documentales preliminares. Verificar modificaciones oficiales posteriores.</p><p>TAPPAD Consultoría ofrece asesoría para participar.</p></body></html>"
    SALIDA.mkdir(exist_ok=True)
    (SALIDA/"vista_previa_alerta_secop_e107.html").write_text(cuerpo,encoding="utf-8")
    print("COINCIDENCIAS:",", ".join(coincidencias))
    print("DESTINATARIO AUTORIZADO:",DESTINATARIO)
    print("VISTA PREVIA:",SALIDA/"vista_previa_alerta_secop_e107.html")
    if not args.enviar:
        print("SIMULACION: sin envio SMTP, sin escrituras Supabase.")
        return
    marca=SALIDA/"piloto_secop_e107_enviado.json"
    if marca.exists():raise SystemExit("BLOQUEADO: ya existe constancia local de envio; no duplicar")
    password=os.getenv("GMAIL_APP_PASSWORD") or os.getenv("SMTP_PASSWORD")
    if not password:raise SystemExit("Falta GMAIL_APP_PASSWORD o SMTP_PASSWORD")
    mensaje=EmailMessage()
    mensaje["From"]=REMITENTE;mensaje["To"]=DESTINATARIO;mensaje["Subject"]=asunto
    mensaje.set_content(texto);mensaje.add_alternative(cuerpo,subtype="html")
    with smtplib.SMTP_SSL("smtp.gmail.com",465,context=ssl.create_default_context(),timeout=40) as servidor:
        servidor.login(REMITENTE,password)
        servidor.send_message(mensaje)
    marca.write_text(json.dumps({"procedimiento":CODIGO,"destinatario":DESTINATARIO,"fecha":datetime.now(ZoneInfo("America/Monterrey")).isoformat(),"smtp":"aceptado"},indent=2),encoding="utf-8")
    print("Gmail acepto el mensaje. Entrega en bandeja pendiente de comprobacion.")

if __name__=="__main__":main()
