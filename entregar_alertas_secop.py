"""Entrega SECOP controlada. Por defecto solo preflight; --enviar-real requiere habilitacion explicita.
No modifica codigo ni workflows de ComprasMX.
"""
import argparse, json, os, smtplib, ssl, html
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from zoneinfo import ZoneInfo
from motor_alertas_secop import consultar, coincide, PERMITIDOS

ROOT=Path(__file__).resolve().parent
LOGO=ROOT/"assets"/"logo_tappad.png"
MARCA=ROOT/"documentos_secop_lote"/"envios_secop"
REMITENTE="tappadcons@gmail.com"

def api(metodo,tabla,params=None,datos=None):
    from urllib.request import Request,urlopen
    from urllib.parse import urlencode
    base=os.environ["SUPABASE_URL"].rstrip("/")
    clave=os.getenv("SUPABASE_ADMIN_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not clave:raise SystemExit("Falta credencial Supabase")
    url=base+"/rest/v1/"+tabla+("?"+urlencode(params) if params else "")
    headers={"apikey":clave,"Authorization":"Bearer "+clave,"Content-Type":"application/json","Accept":"application/json"}
    if datos is not None:headers["Prefer"]="return=representation"
    req=Request(url,headers=headers,method=metodo,data=json.dumps(datos).encode() if datos is not None else None)
    with urlopen(req,timeout=35) as r:
        body=r.read()
        return json.loads(body) if body else None

def actualizar(cid,lid,estado,detalle=None):
    datos={"estado":estado,"ultimo_error":detalle,"actualizado_en":datetime.now(ZoneInfo("UTC")).isoformat()}
    if estado=="enviado":datos["enviado_en"]=datetime.now(ZoneInfo("UTC")).isoformat()
    resultado=api("PATCH","notificaciones_enviadas",
        {"cliente_id":"eq."+str(cid),"licitacion_id":"eq."+str(lid),"estado":"eq.procesando"},
        datos)
    if not isinstance(resultado,list) or len(resultado)!=1:
        raise RuntimeError("Estado de notificacion no confirmado: requiere conciliacion")

def fmt(x):
    if not x:return "Fecha no disponible, verificar informacion oficial"
    return datetime.fromisoformat(str(x).replace("Z","+00:00")).strftime("%d/%m/%Y, %H:%M")

def mensaje_html(l,hits):
    campos=[
        ("Descripción del procedimiento",l.get("nombre_procedimiento") or l.get("descripcion") or ""),
        ("Número de procedimiento",l["numero_procedimiento"]),
        ("Fecha de publicación",fmt(l.get("fecha_publicacion"))),
        ("Fecha de Junta de aclaraciones",fmt(l.get("fecha_junta_aclaraciones"))),
        ("Fecha de apertura de proposiciones",fmt(l.get("fecha_apertura"))),
        ("Fecha de fallo programado",fmt(l.get("fecha_fallo_programado"))),
        ("Coincidencia comercial",", ".join(hits))]
    filas="".join("<tr><td style='padding:10px;border-bottom:1px solid #ddd'><b>"+html.escape(k)+"</b></td><td style='padding:10px;border-bottom:1px solid #ddd'>"+html.escape(str(v))+"</td></tr>" for k,v in campos)
    cuerpo="<html><body style='font-family:Arial,sans-serif;color:#15243a'><img src='cid:tappad-logo' alt='TAPPAD' width='180' style='display:block;max-width:180px;height:auto'><h2>TAPPAD Radar</h2><p>Nueva oportunidad en SECOP Coahuila</p><table>"+filas+"</table><p>Fechas preliminares extraídas de documentos; verificar modificaciones oficiales posteriores.</p><p>TAPPAD Consultoría ofrece asesoría para participar.</p></body></html>"
    return cuerpo, "\n".join(k+": "+str(v) for k,v in campos)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--fecha",help="Fecha de publicacion AAAA-MM-DD; por defecto hoy")
    p.add_argument("--enviar-real",action="store_true",help="Reservar y enviar correos autorizados")
    args=p.parse_args()
    ahora=datetime.now(ZoneInfo("America/Monterrey"))
    fecha=args.fecha or ahora.date().isoformat()
    datetime.strptime(fecha,"%Y-%m-%d")
    lic=consultar("licitaciones",{
        "select":"id,numero_procedimiento,nombre_procedimiento,descripcion,fecha_publicacion,fecha_junta_aclaraciones,fecha_apertura,fecha_fallo_programado,validacion_calendario,fuente,estatus",
        "fuente":"eq.SECOP Coahuila","validacion_calendario":"eq.preliminar_documental",
        "fecha_publicacion":"gte."+fecha+"T00:00:00",
        "and":"(fecha_publicacion.lt."+fecha+"T23:59:59.999999,fecha_apertura.gt."+ahora.strftime("%Y-%m-%dT%H:%M:%S")+")",
        "limit":"1000"})
    clientes=consultar("clientes",{"select":"id,empresa,correo,palabras_clave,activo","activo":"eq.true","limit":"1000"})
    ocupados=consultar("notificaciones_enviadas",{"select":"cliente_id,licitacion_id,estado","limit":"10000"})
    ocup={(int(x["cliente_id"]),int(x["licitacion_id"])) for x in ocupados}
    tareas=[]
    for l in lic:
        if str(l.get("estatus") or "").casefold()!="vigente":continue
        desc=" ".join((l.get("nombre_procedimiento") or "",l.get("descripcion") or ""))
        for c in clientes:
            if (c["id"],l["id"]) in ocup:continue
            hits=list(dict.fromkeys(k.strip() for k in (c.get("palabras_clave") or "").split(",") if coincide(k,desc)))
            if not hits:continue
            destino=(c.get("correo") or "").strip().casefold()
            tareas.append((c,l,hits,destino))
    print("SECOP PREFLIGHT | fecha:",fecha,"| licitaciones:",len(lic),"| clientes activos:",len(clientes),"| pendientes:",len(tareas))
    for c,l,hits,destino in tareas:
        print("CANDIDATA",l["numero_procedimiento"],"| cliente",c["id"],"|",destino,"|",", ".join(hits))
    if not args.enviar_real:
        print("SIMULACION: sin correos ni escrituras Supabase.")
        return
    if os.getenv("TAPPAD_SECOP_ENVIO_REAL")!="SI":
        raise SystemExit("Envio SECOP bloqueado: falta TAPPAD_SECOP_ENVIO_REAL=SI")
    if any(destino not in PERMITIDOS for _,_,_,destino in tareas):
        raise SystemExit("Envio bloqueado: cliente activo fuera de lista cerrada de prueba")
    if not LOGO.is_file():raise SystemExit("Falta assets/logo_tappad.png")
    clave=os.getenv("SMTP_APP_PASSWORD") or os.getenv("GMAIL_APP_PASSWORD") or os.getenv("SMTP_PASSWORD")
    if not clave:raise SystemExit("Falta contrasena de aplicacion Gmail en entorno")
    if os.getenv("SMTP_USER",REMITENTE).casefold()!=REMITENTE:
        raise SystemExit("Remitente no autorizado")
    config=consultar("configuracion_operativa_tappad",{"select":"clave,valor","clave":"eq.alertas_automaticas_habilitadas"})
    if not config or str(config[0]["valor"]).strip().lower()!="true":
        raise SystemExit("Interruptor global de alertas desactivado")
    MARCA.mkdir(parents=True,exist_ok=True)
    for c,l,hits,destino in tareas:
        cid,lid=c["id"],l["id"]
        marker=MARCA/(str(cid)+"_"+str(lid)+".json")
        if marker.exists():
            print("BLOQUEADO: marca local existente",cid,lid)
            continue
        # Reserva atomica compartida con ComprasMX. Nunca se reintenta un estado procesando/error.
        reservado=api("POST","rpc/tappad_reservar_lote",datos={"p_cliente":cid,"p_licitaciones":[lid]})
        if reservado is not True:
            print("RESERVA NO AUTORIZADA:",cid,lid)
            continue
        cuerpo,plano=mensaje_html(l,hits)
        mensaje=EmailMessage()
        mensaje["From"]=REMITENTE
        mensaje["To"]=destino
        mensaje["Subject"]="TAPPAD Radar | SECOP Coahuila | "+l["numero_procedimiento"]
        mensaje.set_content(plano+"\n\nFechas preliminares; verificar modificaciones oficiales.")
        mensaje.add_alternative(cuerpo,subtype="html")
        mensaje.get_payload()[-1].add_related(LOGO.read_bytes(),maintype="image",subtype="png",cid="<tappad-logo>",filename="logo_tappad.png",disposition="inline")
        try:
            with smtplib.SMTP_SSL("smtp.gmail.com",465,context=ssl.create_default_context(),timeout=40) as smtp:
                smtp.login(REMITENTE,clave)
                smtp.send_message(mensaje)
        except Exception as exc:
            actualizar(cid,lid,"error","ENTREGA INCIERTA: "+str(exc)[:180])
            raise SystemExit("SMTP incierto: revisar manualmente, NO reintentar") from exc
        marker.write_text(json.dumps({"cliente_id":cid,"licitacion_id":lid,"smtp":"aceptado","fecha":ahora.isoformat()}),encoding="utf-8")
        actualizar(cid,lid,"enviado")
        print("SMTP ACEPTADO Y REGISTRADO:",cid,lid)
    print("FIN. Aceptacion SMTP no confirma lectura.")

if __name__=="__main__":main()
