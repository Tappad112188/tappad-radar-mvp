"""Compuerta TAPPAD v3: vigencia por apertura y cuatro fechas.
Solo lectura. No envia mensajes ni actualiza Supabase.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

ZONA = ZoneInfo("America/Monterrey")
CERRADOS={"cancelada","cancelado","concluida","concluido","desierta","adjudicada","adjudicado"}
FECHAS=("fecha_publicacion","fecha_junta_aclaraciones","fecha_apertura","fecha_fallo_programado")

def fecha_local(valor):
    if not valor: return None
    try:
        f=datetime.fromisoformat(str(valor).replace("Z","+00:00"))
        return f.astimezone(ZONA).replace(tzinfo=None) if f.tzinfo else f
    except (ValueError,TypeError,OverflowError): return None

def evaluar(licitacion, cliente_id, enviados, ahora=None):
    ahora=ahora or datetime.now(ZONA).replace(tzinfo=None)
    if str(licitacion.get("estatus") or "").strip().lower() in CERRADOS:
        return False,"procedimiento_cerrado"
    if (cliente_id,licitacion.get("id")) in enviados:
        return False,"ya_notificada"
    apertura=fecha_local(licitacion.get("fecha_apertura"))
    if apertura is None:
        if not str(licitacion.get("fecha_apertura") or "").strip() and str(licitacion.get("fuente") or "").strip().casefold() == "comprasmx":
            return True,"comprasmx_sin_fecha_apertura_publicada"
        return False,"sin_fecha_apertura_valida"
    if apertura<=ahora: return False,"plazo_presentacion_vencido"
    # La verificacion documental no es requisito de coincidencia.
    return True,"vigente_para_previsualizacion"

def fechas_correo(l):
    etiquetas=("Publicacion","Junta de aclaraciones","Presentacion y apertura de propuestas","Fallo programado")
    return [(etiqueta,fecha_local(l.get(campo)).strftime("%d/%m/%Y" if campo=="fecha_publicacion" else "%d/%m/%Y %H:%M") if fecha_local(l.get(campo)) else "No especificada")
            for etiqueta,campo in zip(etiquetas,FECHAS)]

def agrupar(candidatos,enviados,ahora=None):
    grupos,bloqueos={},{}
    for cliente_id,licitacion in candidatos:
        ok,motivo=evaluar(licitacion,cliente_id,enviados,ahora)
        if ok: grupos.setdefault(cliente_id,[]).append(licitacion)
        else: bloqueos[motivo]=bloqueos.get(motivo,0)+1
    return grupos,bloqueos

def autoprueba():
    base={"id":5,"fecha_apertura":"2026-10-24T10:00:00","validacion_calendario":"pendiente","estatus":"Vigente"}
    assert evaluar(base,1,set(),datetime(2026,10,24,9,59))[0]
    assert evaluar(base,1,set(),datetime(2026,10,24,10,0))==(False,"plazo_presentacion_vencido")
    assert evaluar(base,1,set(),datetime(2026,10,24,11,0))==(False,"plazo_presentacion_vencido")
    assert evaluar({**base,"fecha_apertura":None},1,set(),datetime(2026,10,24,9,0))[0] is False
    assert evaluar({**base,"estatus":"cancelada"},1,set(),datetime(2026,10,24,9,0))[0] is False
    assert evaluar(base,1,{(1,5)},datetime(2026,10,24,9,0))[0] is False
    assert len(fechas_correo(base))==4
    assert fechas_correo(base)[0][1]=="No especificada"
    assert len(agrupar([(1,base)],set(),datetime(2026,10,24,9,0))[0][1])==1
    print("9 pruebas superadas. Solo lectura; vigencia por hora de apertura; SIN ENVIOS.")

if __name__=="__main__": autoprueba()
