"""Prueba aislada con perfiles ficticios y cuatro procedimientos reales del 13/11. Sin escrituras comerciales."""
import json, os, smtplib, ssl
from pathlib import Path
from plantilla_correo_html import construir_correo_html
from urllib.request import Request,urlopen
from urllib.parse import urlencode
from email.message import EmailMessage

CASOS={1:{"correo":"gerardotapia112188@gmail.com","comprasmx":"IA-87-I80-828003998-N-26-2026","secop":"UTC-LPN-CA-E003-2026","terminos":("bomba sumergible","transporte")},
       4:{"correo":"tappadcons@gmail.com","comprasmx":"LA-86-ZJ1-927004005-N-150-2026","secop":"DGA01-LPN-CA-E054-2026","terminos":("medicamentos genéricos","ambientación")}}
def get(table,params):
    base=os.environ["SUPABASE_URL"].rstrip("/")
    key=os.environ["SUPABASE_ADMIN_KEY"]
    url=base+"/rest/v1/"+table+"?"+urlencode(params)
    req=Request(url,headers={"apikey":key,"Authorization":"Bearer "+key})
    with urlopen(req,timeout=25) as response:
        return json.loads(response.read())
def main():
    if os.getenv("TAPPAD_PRUEBA_AISLADA")!="SI": raise SystemExit("Prueba deshabilitada")
    if os.getenv("SMTP_USER","").casefold()!="tappadcons@gmail.com": raise SystemExit("Remitente no autorizado")
    correos=[]
    for cid,caso in CASOS.items():
        clientes=get("clientes",{"select":"id,correo,palabras_clave,activo","id":"eq."+str(cid)})
        if len(clientes)!=1 or not clientes[0]["activo"] or clientes[0]["correo"].casefold()!=caso["correo"]:
            raise SystemExit("Cliente/destino no autorizado")
        # Los giros son exclusivos de los dos perfiles ficticios de esta ejecucion.
        # No se alteran palabras_clave, giros ni suscripciones de clientes reales.
        claves=", ".join(caso["terminos"]).casefold()
        if not all(t in claves for t in caso["terminos"]): raise SystemExit("Giros ficticios invalidos")
        print("PERFIL FICTICIO",cid,"| GIROS:",", ".join(caso["terminos"]))
        items=[]
        for fuente,numero,termino in (("ComprasMX",caso["comprasmx"],caso["terminos"][0]),("SECOP Coahuila",caso["secop"],caso["terminos"][1])):
            rows=get("licitaciones",{"select":"id,fuente,numero_procedimiento,nombre_procedimiento,descripcion,fecha_publicacion,fecha_junta_aclaraciones,fecha_apertura,fecha_fallo_programado,url_procedimiento,url_bases,url_convocatoria,documentos_disponibles,validacion_calendario","numero_procedimiento":"eq."+numero,"fuente":"eq."+fuente})
            if len(rows)!=1: raise SystemExit("Procedimiento no unico: "+numero)
            lic=rows[0]
            texto=" ".join(str(lic.get(x) or "") for x in ("nombre_procedimiento","descripcion")).casefold()
            if termino not in texto: raise SystemExit("Coincidencia no comprobada: "+numero)
            if str(lic["fecha_publicacion"])[:10]!="2026-11-13": raise SystemExit("Fecha de publicacion inesperada")
            items.append((lic,termino))
        oportunidades=[]
        for lic,termino in items:
            lic=dict(lic)
            lic["terminos"]=[termino]
            oportunidades.append(lic)
        contenido=construir_correo_html("Proveedor ficticio "+str(cid),oportunidades)
        campos=("cid:tappad-logo","Fecha de publicación:","Fecha de Junta de aclaraciones:",
                "Fecha de apertura de proposiciones:","Fecha de fallo:",
                "TAPPAD Consultoría ofrece asesoría")
        if not all(c in contenido for c in campos):
            raise SystemExit("Plantilla corporativa incompleta")
        for lic in oportunidades:
            if lic["fuente"]=="SECOP Coahuila" and lic.get("validacion_calendario") not in ("preliminar_documental","verificado"):
                raise SystemExit("Calendario SECOP sin validacion documental")
        logo=Path(__file__).resolve().parent/"assets"/"logo_tappad.png"
        if not logo.is_file() or not logo.read_bytes().startswith(b"\\x89PNG\\r\\n\\x1a\\n"):
            raise SystemExit("Logo PNG no disponible o invalido")
        msg=EmailMessage()
        msg["From"]=os.environ["SMTP_USER"];msg["To"]=caso["correo"]
        msg["Subject"]="[PRUEBA AISLADA] TAPPAD Radar | SECOP + ComprasMX | proveedor "+str(cid)
        msg.set_content("Prueba aislada de TAPPAD Radar. Consulte la version HTML para fechas, documentos y asesoria.")
        msg.add_alternative(contenido,subtype="html")
        msg.get_payload()[-1].add_related(logo.read_bytes(),maintype="image",subtype="png",cid="<tappad-logo>",filename="logo_tappad.png",disposition="inline")
        correos.append(msg)
    print("PREVALIDACION OK: 2 clientes, 4 coincidencias reales, 2 buzones cerrados")
    if os.getenv("TAPPAD_PRUEBA_ENVIAR")!="SI":
        print("SIMULACION: no se envia")
        return
    with smtplib.SMTP_SSL("smtp.gmail.com",465,context=ssl.create_default_context(),timeout=35) as smtp:
        smtp.login(os.environ["SMTP_USER"],os.environ["SMTP_APP_PASSWORD"])
        for msg in correos:
            smtp.send_message(msg)
            print("SMTP aceptado para:",msg["To"])
    print("Prueba aislada completada. No se modificaron pagos, accesos ni historial.")
if __name__=="__main__":main()
