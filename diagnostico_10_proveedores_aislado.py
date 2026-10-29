"""Diagnóstico aislado de 10 clientes de prueba y 10 licitaciones ComprasMX.
Solo lectura. No activa clientes, no escribe en Supabase ni envía correos.
Usa exactamente las funciones de clasificación del motor existente.
"""
from collections import Counter, defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
import re
from diagnosticar_vigencia_v4 import consulta, norm, contiene, RUBROS, GENERICAS, objeto_principal, estado_equivalente

CLIENTES = (7,8,9,10,11,12,13,14,15,16)
LICITACIONES = (1394,1395,1396,1397,1398,1399,1400,1402,1404,1405)

def main():
    clientes = consulta("clientes", "id,empresa,palabras_clave,activo", {"id":"in.("+",".join(map(str,CLIENTES))+")"})
    licitaciones = consulta("licitaciones", "id,numero_procedimiento,nombre_procedimiento,descripcion,fuente,entidad_federativa,estatus,fecha_apertura,validacion_calendario", {"id":"in.("+",".join(map(str,LICITACIONES))+")"})
    print("COBERTURA CALENDARIO DE LAS DIEZ LICITACIONES:")
    for campo in ("fecha_publicacion","fecha_junta_aclaraciones","fecha_apertura","fecha_fallo_programado"):
        print(" ",campo,":",sum(bool(l.get(campo)) for l in licitaciones),"/",len(licitaciones))
    print(" Documentos vinculados:",sum(bool(l.get("documentos_disponibles")) for l in licitaciones),"/",len(licitaciones))
    print(" Calendarios verificados:",sum(norm(l.get("validacion_calendario"))=="verificado" for l in licitaciones),"/",len(licitaciones))
    giros = consulta("clientes_giros","cliente_id,giro_id")
    ubicaciones = consulta("clientes_ubicaciones","cliente_id,estado,municipio")
    notificaciones = consulta("notificaciones_enviadas","cliente_id,licitacion_id,estado")
    gs, us = defaultdict(set),defaultdict(list)
    for g in giros: gs[g["cliente_id"]].add(g["giro_id"])
    for u in ubicaciones: us[u["cliente_id"]].append(u)
    enviados={(n["cliente_id"],n["licitacion_id"]) for n in notificaciones if n["estado"]=="enviado"}
    hoy=datetime.now(ZoneInfo("America/Monterrey")).replace(tzinfo=None)
    conteo=Counter()
    print("MODO PRUEBA AISLADA: 10 CLIENTES, 10 COMPRASMX; SIN CORREOS NI ESCRITURAS")
    print("Clientes recuperados:",len(clientes),"Licitaciones recuperadas:",len(licitaciones))
    for c in sorted(clientes,key=lambda c:c["id"]):
        claves=[norm(x.strip()) for x in re.split(r"[,;\n]",c.get("palabras_clave") or "") if len(x.strip())>=4]
        fuertes=[x for x in claves if x not in GENERICAS]
        print("\nCLIENTE",c["id"],c["empresa"],"| activo=",c["activo"])
        for l in licitaciones:
            motivo=None
            if (c["id"],l["id"]) in enviados: motivo="ya_enviado"
            elif norm(l.get("estatus")) in {"cancelada","cancelado","concluida","concluido","desierta","adjudicada","adjudicado"}: motivo="estatus"
            else:
                apertura=l.get("fecha_apertura")
                if apertura:
                    try:
                        if datetime.fromisoformat(apertura.replace("Z","")) < hoy: motivo="apertura_vencida"
                    except ValueError: motivo="fecha_invalida"
                if not motivo and us[c["id"]] and (not l.get("entidad_federativa") or not any(estado_equivalente(u.get("estado"),l["entidad_federativa"]) for u in us[c["id"]])): motivo="ubicacion"
            texto=norm((l.get("nombre_procedimiento") or "")+" "+(l.get("descripcion") or ""))
            rubros=[g for g in gs[c["id"]] if any(contiene(texto,kw) for kw in RUBROS.get(g,()))]
            objeto=objeto_principal(l)
            if not motivo and objeto is not None and gs[c["id"]] and objeto not in gs[c["id"]]: motivo="objeto_principal"
            if not motivo and objeto is not None: rubros=[g for g in rubros if g==objeto]
            palabras=[x for x in fuertes if contiene(texto,x)]
            if not motivo and gs[c["id"]] and not rubros: motivo="sin_giro"
            if not motivo and fuertes and not palabras and not rubros: motivo="sin_palabras"
            if not motivo and not rubros and not palabras: motivo="sin_coincidencia"
            if motivo: conteo[motivo]+=1; continue
            conteo["coincidencias"]+=1
            verificado=norm(l.get("validacion_calendario"))=="verificado"
            if not verificado: conteo["calendario_pendiente"]+=1
            print("  MATCH",l["numero_procedimiento"],"| giros",rubros,"| calendario",l.get("validacion_calendario"),"| apta_envio",verificado)
    print("\nRESUMEN",dict(conteo))
    print("NO se han enviado correos, activado clientes ni escrito datos.")

if __name__=="__main__": main()
