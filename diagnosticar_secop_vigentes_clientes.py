"""Diagnostico seguro SECOP: oportunidades previas aun abiertas, sin correos ni escrituras.
Uso: py diagnosticar_secop_vigentes_clientes.py (requiere variables Supabase).
No asume que el estatus historico sea vigente hoy.
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from preparar_plan_controlado_comprasmx import CLIENTES_PRUEBA
from diagnosticar_vigencia_v4 import consulta, norm, contiene, RUBROS, GENERICAS, estado_equivalente, objeto_principal
from compuerta_alertas_v3 import fecha_local
import re

def main():
    clientes=consulta("clientes","id,empresa,correo,activo,palabras_clave",{"activo":"eq.true"})
    giros=consulta("clientes_giros","cliente_id,giro_id")
    ubicaciones=consulta("clientes_ubicaciones","cliente_id,estado,municipio")
    licitaciones=consulta("licitaciones","id,numero_procedimiento,nombre_procedimiento,descripcion,fuente,entidad_federativa,estatus,fecha_publicacion,fecha_apertura,validacion_calendario,url_procedimiento,url_bases",{"fuente":"eq.SECOP Coahuila"})
    historial=consulta("notificaciones_enviadas","cliente_id,licitacion_id,estado")
    ocupados={(r["cliente_id"],r["licitacion_id"]) for r in historial}
    ahora=datetime.now(ZoneInfo("America/Monterrey")).replace(tzinfo=None)
    print("SECOP HISTORICO:",len(licitaciones),"| Consulta:",ahora.isoformat(timespec="minutes"))
    for c in clientes:
        cid=c["id"]
        if cid not in CLIENTES_PRUEBA: continue
        if str(c.get("correo") or "").strip().casefold()!=CLIENTES_PRUEBA[cid]:
            raise SystemExit("Correo de prueba inesperado para cliente "+str(cid))
        gs={r["giro_id"] for r in giros if r["cliente_id"]==cid}
        us=[r for r in ubicaciones if r["cliente_id"]==cid]
        fuertes=[norm(k.strip()) for k in re.split(r"[,;\n]",c.get("palabras_clave") or "") if len(k.strip())>=4 and norm(k.strip()) not in GENERICAS]
        candidatos=[]
        for l in licitaciones:
            if (cid,l["id"]) in ocupados:continue
            apertura=fecha_local(l.get("fecha_apertura"))
            if not apertura or apertura<=ahora:continue
            if norm(l.get("estatus"))!="vigente":continue
            if us and not any(estado_equivalente(u.get("estado"),l.get("entidad_federativa")) for u in us):continue
            texto=norm((l.get("nombre_procedimiento") or "")+" "+(l.get("descripcion") or ""))
            rubros=[g for g in gs if any(contiene(texto,k) for k in RUBROS.get(g,()))]
            objeto=objeto_principal(l)
            if objeto is not None:
                if gs and objeto not in gs:continue
                rubros=[g for g in rubros if g==objeto]
            palabras=[k for k in fuertes if contiene(texto,k)]
            if gs and not rubros:continue
            if fuertes and not palabras and not rubros:continue
            if not rubros and not palabras:continue
            candidatos.append(l)
        print("CLIENTE",cid,"| candidatos historicos pendientes de revalidar:",len(candidatos))
        for l in candidatos:
            print(" ",l["numero_procedimiento"],"| apertura:",l["fecha_apertura"],"| calendario:",l.get("validacion_calendario"),"| enlace bases:",bool(l.get("url_bases")))
    print("DIAGNOSTICO SOLAMENTE. El estatus almacenado no prueba vigencia actual; sin envios ni escrituras.")
if __name__=="__main__":main()
