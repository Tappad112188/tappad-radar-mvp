"""Diagnostico explicable de filtros ComprasMX. Solo consultas; sin SMTP ni escrituras."""
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo
from diagnosticar_vigencia_v4 import consulta
from generar_manifiesto_comprasmx_automatico import seleccionar_recientes
from motor_coincidencias import evaluar_licitacion
from validador_plazo_oficial import validar_envio_oportunidad
from priorizador_alertas import priorizar_oportunidad

PILOTOS={1:"gerardotapia112188@gmail.com",4:"tappadcons@gmail.com"}

def main():
    hoy=datetime.now(ZoneInfo("America/Monterrey")).date()
    ahora=datetime.now(ZoneInfo("America/Monterrey"))
    clientes=consulta("clientes","id,empresa,correo,activo,palabras_clave",{"activo":"eq.true"})
    licitaciones=consulta("licitaciones","id,numero_procedimiento,nombre_procedimiento,descripcion,tipo_contratacion,fuente,entidad_federativa,estatus,fecha_publicacion,fecha_registro,fecha_apertura,validacion_calendario")
    ubicaciones=consulta("clientes_ubicaciones","cliente_id,estado,municipio")
    preferencias=consulta("clientes_giros_preferencias_tappad","cliente_id,origen,clave,descripcion,activo",{"activo":"eq.true"})
    historial=consulta("notificaciones_enviadas","cliente_id,licitacion_id,estado")
    recientes=seleccionar_recientes(licitaciones,hoy)
    ubic={cid:[u for u in ubicaciones if u["cliente_id"]==cid] for cid in PILOTOS}
    prefs={cid:[p for p in preferencias if p["cliente_id"]==cid] for cid in PILOTOS}
    ocupados={(n["cliente_id"],n["licitacion_id"]) for n in historial}
    print("VENTANA | fecha:",hoy,"| recientes:",len(recientes),"| ComprasMX total:",sum(str(x.get("fuente") or "").casefold()=="comprasmx" for x in licitaciones))
    for c in clientes:
        cid=c["id"]
        if cid not in PILOTOS:
            continue
        if str(c.get("correo") or "").strip().casefold()!=PILOTOS[cid]:
            print("CLIENTE",cid,"BLOQUEADO: correo fuera de piloto")
            continue
        conteos=Counter()
        ejemplos={}
        for lic in recientes:
            resultado=evaluar_licitacion(c,lic,ubic[cid],prefs[cid])
            if not resultado["coincidencia_tematica"]:
                motivo="sin_coincidencia_tematica"
            elif resultado["categoria"]!="dentro_de_cobertura":
                motivo="cobertura_"+resultado["categoria"]
            else:
                prioridad=priorizar_oportunidad(resultado,lic,ahora=ahora)
                decision=validar_envio_oportunidad({**prioridad,"fecha_apertura":lic.get("fecha_apertura"),"estatus":lic.get("estatus")},ahora=ahora)
                if not decision["autorizada"]:
                    motivo="plazo_o_estatus_"+decision["motivo"]
                elif (cid,lic["id"]) in ocupados:
                    motivo="notificacion_existente"
                else:
                    motivo="candidata_pendiente_de_compuerta_final"
            conteos[motivo]+=1
            if motivo not in ejemplos:
                ejemplos[motivo]=str(lic.get("numero_procedimiento") or lic.get("id"))
        print("CLIENTE",cid,"| recientes evaluadas:",len(recientes))
        for motivo,cantidad in sorted(conteos.items()):
            print(" ",motivo,":",cantidad,"| ejemplo:",ejemplos[motivo])
    print("SOLO LECTURA: sin SMTP ni escrituras en Supabase")

if __name__=="__main__":
    main()
