"""Motor de entrega TAPPAD Radar v1.
Por defecto SOLO simula. Para enviar exige --enviar-real y TAPPAD_ENVIO_REAL=SI.
El envio real requiere SMTP_USER, SMTP_APP_PASSWORD y SUPABASE_ADMIN_KEY.
Los estados procesando/error NO se reintentan automaticamente: conciliacion manual.
"""
import argparse, hashlib, json, os, smtplib
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from diagnosticar_vigencia_v4 import consulta
from compuerta_alertas_v3 import evaluar
from datetime import datetime
from zoneinfo import ZoneInfo

BASE=Path(__file__).resolve().parent
MANIFIESTO=BASE/"manifiesto_notificaciones_tappad.json"
HTML_DIR=BASE/"borradores_gmail_tappad_v3"
LOGO=BASE/"assets/logo_tappad.png"

def api(metodo, tabla, parametros=None, datos=None, prefer=None):
    base=os.environ["SUPABASE_URL"].rstrip("/")
    clave=os.environ.get("SUPABASE_ADMIN_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not clave: raise RuntimeError("Falta clave privada Supabase")
    url=base+"/rest/v1/"+tabla+("?"+urlencode(parametros) if parametros else "")
    headers={"apikey":clave,"Authorization":"Bearer "+clave,"Content-Type":"application/json"}
    if prefer: headers["Prefer"]=prefer
    req=Request(url,data=json.dumps(datos).encode("utf-8") if datos is not None else None,headers=headers,method=metodo)
    try:
        with urlopen(req,timeout=30) as resp:
            cuerpo=resp.read()
            return json.loads(cuerpo) if cuerpo else []
    except HTTPError as e:
        raise RuntimeError("Supabase HTTP "+str(e.code)+": "+e.read().decode("utf-8","replace")[:400]) from e

def actualizar(cliente_id,ids,estado,detalle=None):
    for lid in ids:
        campos={"estado":estado,"ultimo_error":detalle,"actualizado_en":datetime.now(ZoneInfo("UTC")).isoformat()}
        if estado=="enviado": campos["enviado_en"]=datetime.now(ZoneInfo("UTC")).isoformat()
        r=api("PATCH","notificaciones_enviadas",{"cliente_id":"eq."+str(cliente_id),"licitacion_id":"eq."+str(lid),"estado":"eq.procesando"},campos,"return=representation")
        if len(r)!=1: raise RuntimeError("No se pudo confirmar estado para licitacion "+str(lid))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--enviar-real",action="store_true")
    args=p.parse_args()
    manifiesto=json.loads(MANIFIESTO.read_text(encoding="utf-8"))
    if manifiesto.get("modo")!="SOLO_PREPARACION": raise SystemExit("Manifiesto no valido")
    clientes={c["id"]:c for c in consulta("clientes","id,empresa,correo,activo",{"activo":"eq.true"})}
    licitaciones={l["id"]:l for l in consulta("licitaciones","id,fuente,fecha_apertura,estatus,validacion_calendario")}
    registros=consulta("notificaciones_enviadas","cliente_id,licitacion_id,estado")
    ocupados={(r["cliente_id"],r["licitacion_id"]) for r in registros}
    ahora=datetime.now(ZoneInfo("America/Monterrey")).replace(tzinfo=None)
    tareas=[]
    for lote in manifiesto["proveedores"]:
        cid=lote["cliente_id"]; cliente=clientes.get(cid)
        if not cliente: raise SystemExit("Proveedor inactivo o inexistente: "+str(cid))
        destino=str(cliente.get("correo") or "").strip()
        if not destino or "@" not in destino: raise SystemExit("Correo invalido para proveedor "+str(cid))
        ids=lote["licitacion_ids"]
        if len(set(ids))!=len(ids) or not ids: raise SystemExit("Identificadores duplicados/vacios")
        for lid in ids:
            l=licitaciones.get(lid)
            if not l: raise SystemExit("Licitacion no encontrada")
            if str(l.get("fuente") or "").strip().casefold() not in ("comprasmx","secop coahuila"):
                raise SystemExit("Fuente no admitida para licitacion "+str(lid))
            if (cid,lid) in ocupados: raise SystemExit("Notificacion existente: revisar manualmente "+str(cid)+"/"+str(lid))
            ok,motivo=evaluar(l,cid,set(),ahora)
            if not ok: raise SystemExit("Licitacion bloqueada: "+motivo)
        archivo=HTML_DIR/lote["html"]
        if archivo.name!=lote["html"]: raise SystemExit("Ruta HTML no valida")
        contenido=archivo.read_bytes()
        if hashlib.sha256(contenido).hexdigest()!=lote["sha256_html"]: raise SystemExit("HTML modificado")
        if any(str(licitaciones[lid].get("fuente") or "").strip().casefold()=="secop coahuila" and (str(licitaciones[lid].get("validacion_calendario") or "").strip().casefold()!="verificado" or not licitaciones[lid].get("fecha_apertura")) for lid in ids):
            html=contenido.decode("utf-8")
            if "revisar" not in html.casefold() or ("bases" not in html.casefold() and "documento" not in html.casefold()):
                raise SystemExit("Aviso obligatorio de revision documental ausente en HTML SECOP: "+str(cid))
        tareas.append((cid,destino,ids,contenido.decode("utf-8")))
    print("PREFLIGHT:",len(tareas),"correos;",sum(len(t[2]) for t in tareas),"oportunidades")
    if not args.enviar_real:
        print("MODO SEGURO: sin SMTP y sin escrituras Supabase")
        return
    if os.environ.get("TAPPAD_ENVIO_REAL")!="SI": raise SystemExit("Envio real deshabilitado por configuracion")
    if not os.environ.get("SMTP_USER") or not os.environ.get("SMTP_APP_PASSWORD"): raise SystemExit("Faltan secretos SMTP")
    if not LOGO.is_file(): raise SystemExit("Falta logo PNG")
    logo=LOGO.read_bytes()
    for cid,destino,ids,html in tareas:
        # Reserva atomica PostgreSQL: lote completo o ninguna reserva.
        try:
            reservado=api("POST","rpc/tappad_reservar_lote",None,{"p_cliente":cid,"p_licitaciones":ids})
        except Exception as exc:
            raise SystemExit("Reserva atomica rechazada. NO se envia: "+str(exc)) from exc
        if reservado is not True:
            raise SystemExit("Reserva no confirmada. NO se envia.")
        mensaje=EmailMessage()
        mensaje["From"]=os.environ["SMTP_USER"]
        mensaje["To"]=destino
        mensaje["Subject"]="TAPPAD Radar | Nuevas oportunidades"
        mensaje.set_content("Consulta las oportunidades de TAPPAD Radar en la version HTML de este mensaje.")
        mensaje.add_alternative(html,subtype="html")
        mensaje.get_payload()[-1].add_related(logo,maintype="image",subtype="png",cid="<tappad-logo>",filename="logo_tappad.png",disposition="inline")
        try:
            with smtplib.SMTP("smtp.gmail.com",587,timeout=35) as smtp:
                smtp.ehlo();smtp.starttls();smtp.ehlo()
                smtp.login(os.environ["SMTP_USER"],os.environ["SMTP_APP_PASSWORD"])
                smtp.send_message(mensaje)
        except Exception as exc:
            # Puede haber aceptacion SMTP antes del error: NO reintentar automaticamente.
            actualizar(cid,ids,"error","ENTREGA INCIERTA: "+str(exc)[:200])
            raise SystemExit("Envio no confirmado. Requiere conciliacion manual.") from exc
        actualizar(cid,ids,"enviado")
        print("SMTP aceptado y registrado para proveedor",cid,"| oportunidades:",len(ids))
    print("Lote completado. Aceptacion SMTP no equivale a lectura por destinatario.")

if __name__=="__main__": main()
