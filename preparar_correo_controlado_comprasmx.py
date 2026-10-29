"""Prepara HTML y manifiesto de prueba exclusivamente para ComprasMX; sin envios."""
import hashlib, json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from diagnosticar_vigencia_v4 import consulta
from compuerta_alertas_v3 import evaluar
from plantilla_correo_html import construir_correo_html

BASE=Path(__file__).resolve().parent
DESTINOS={4:"tappadcons@gmail.com"}
CAMPOS="id,fuente,numero_procedimiento,nombre_procedimiento,descripcion,fecha_publicacion,fecha_junta_aclaraciones,fecha_apertura,fecha_fallo_programado,url_procedimiento,estatus,validacion_calendario"

def main():
    plan=json.loads((BASE/"plan_envios_seco_tappad.json").read_text(encoding="utf-8"))
    if plan.get("modo")!="SIMULACION_SIN_ENVIO":raise SystemExit("Plan no autorizado")
    lotes=plan.get("proveedores",[])
    if len(lotes)!=1 or lotes[0].get("cliente_id")!=4:raise SystemExit("Prueba limitada al cliente 4")
    ids=lotes[0].get("licitacion_ids",[])
    if not ids or len(ids)!=len(set(ids)):raise SystemExit("IDs vacios o duplicados")
    clientes=consulta("clientes","id,empresa,correo,activo",{"id":"eq.4","activo":"eq.true"})
    if len(clientes)!=1 or str(clientes[0].get("correo") or "").strip().lower()!=DESTINOS[4]:
        raise SystemExit("Destinatario no autorizado")
    oportunidades=consulta("licitaciones",CAMPOS,{"id":"in.("+",".join(map(str,ids))+")"})
    por_id={l["id"]:l for l in oportunidades}
    if set(por_id)!=set(ids):raise SystemExit("Faltan licitaciones en Supabase")
    historial=consulta("notificaciones_enviadas","cliente_id,licitacion_id,estado",{"cliente_id":"eq.4"})
    ocupados={(r["cliente_id"],r["licitacion_id"]) for r in historial}
    ahora=datetime.now(ZoneInfo("America/Monterrey")).replace(tzinfo=None)
    for lid in ids:
        l=por_id[lid]
        if str(l.get("fuente") or "").strip().casefold()!="comprasmx":raise SystemExit("Fuente no autorizada: "+str(lid))
        ok,motivo=evaluar(l,4,ocupados,ahora)
        if not ok:raise SystemExit("Preflight bloqueado para "+str(lid)+": "+motivo+"; regenerar plan")
    carpeta=BASE/"borradores_gmail_tappad_v3"
    carpeta.mkdir(exist_ok=True)
    archivo=carpeta/"correo_controlado_comprasmx_cliente_4.html"
    html=construir_correo_html(clientes[0]["empresa"],[por_id[lid] for lid in ids])
    if "cid:tappad-logo" not in html:raise SystemExit("Logo CID ausente")
    archivo.write_text(html,encoding="utf-8")
    manifiesto={"modo":"SOLO_PREPARACION","proveedores":[{"cliente_id":4,"licitacion_ids":ids,"html":archivo.name,"sha256_html":hashlib.sha256(html.encode("utf-8")).hexdigest(),"destinatario_configurado":True}],"cantidad_correos":1,"cantidad_oportunidades":len(ids)}
    (BASE/"manifiesto_notificaciones_tappad.json").write_text(json.dumps(manifiesto,ensure_ascii=False,indent=2),encoding="utf-8")
    print("PREPARADO: 1 correo para",DESTINOS[4],"con",len(ids),"oportunidades")
    print("IDs:",ids)
    print("SIN SMTP NI ESCRITURAS SUPABASE. Ejecutar preflight: py motor_entrega_tappad_v2.py")

if __name__=="__main__":main()
