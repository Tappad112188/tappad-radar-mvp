"""Diagnóstico de circuito ComprasMX con giros SAT/CUCOP; sin SMTP ni escrituras."""
from collections import defaultdict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from diagnosticar_vigencia_v4 import consulta
from preparador_alertas import preparar_alertas
from plantilla_correo_html import construir_correo_html

def main():
    hoy=datetime.now(ZoneInfo("America/Monterrey")).date()
    desde=hoy-timedelta(days=2)
    clientes=consulta("clientes","id,empresa,correo,activo,palabras_clave",{"activo":"eq.true"})
    coberturas=consulta("clientes_ubicaciones","cliente_id,estado,municipio")
    preferencias=consulta("clientes_giros_preferencias_tappad","cliente_id,origen,clave,descripcion,activo",{"activo":"eq.true"})
    licitaciones=consulta("licitaciones","id,numero_procedimiento,nombre_procedimiento,descripcion,fuente,entidad_federativa,estatus,fecha_publicacion,fecha_apertura,fecha_junta_aclaraciones,fecha_fallo_programado,url_procedimiento,validacion_calendario")
    historial=consulta("notificaciones_enviadas","cliente_id,licitacion_id,estado")
    cs,ps=defaultdict(list),defaultdict(list)
    for c in coberturas: cs[c["cliente_id"]].append(c)
    for p in preferencias: ps[p["cliente_id"]].append(p)
    recientes=[]
    for l in licitaciones:
        if str(l.get("fuente") or "").strip().casefold()!="comprasmx": continue
        fecha=str(l.get("fecha_publicacion") or "")[:10]
        if fecha and desde.isoformat()<=fecha<=hoy.isoformat(): recientes.append(l)
    resultado=preparar_alertas(clientes,recientes,cs,historial,preferencias_por_cliente=ps)
    print("DIAGNOSTICO COMPRASMX:",len(clientes),"proveedores activos,",len(recientes),"licitaciones recientes,",len(preferencias),"preferencias SAT/CUCOP")
    print("RESUMEN:",resultado["resumen"])
    por_id={l["id"]:l for l in recientes}
    for cid, oportunidades in sorted(resultado["por_proveedor"].items()):
        empresa=next(c["empresa"] for c in clientes if c["id"]==cid)
        html=construir_correo_html(empresa,[{**por_id[o["licitacion_id"]],**o} for o in oportunidades])
        for campo in ("cid:tappad-logo","TAPPAD Consultoría ofrece asesoría","Descripción completa:","Número de procedimiento:","Fecha de publicación:","Fecha de Junta de aclaraciones:","Fecha de apertura de proposiciones:","Fecha de fallo:","Enlace a documentos del procedimiento:"):
            if campo not in html: raise RuntimeError("Plantilla incompleta: "+campo)
        print("HTML PREPARADO: proveedor",cid,"| oportunidades",len(oportunidades))
    print("VALIDACION FINALIZADA: sin SMTP, sin escrituras Supabase, sin activar clientes ficticios.")

if __name__=="__main__": main()
