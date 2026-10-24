"""TAPPAD Radar: compuerta de autorización. Sin SMTP ni escrituras a Supabase.
Solo autoriza candidatos con calendario validado, apertura futura, enlace y sin envio previo.
La autorización NO equivale a enviar: requiere otro proceso con reserva atomica.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

ESTADOS_VALIDOS = {"verificado"}
ESTADOS_TERMINALES = {"cancelada","cancelado","concluida","concluido","desierta","adjudicada","adjudicado"}

def evaluar(licitacion, cliente_id, enviados, ahora=None):
    """Devuelve (autorizada, motivo); enviados: pares (cliente_id, licitacion_id)."""
    if ahora is None:
        ahora = datetime.now(ZoneInfo("America/Monterrey")).replace(tzinfo=None)
    if str(licitacion.get("validacion_calendario") or "").strip().lower() not in ESTADOS_VALIDOS:
        return False, "calendario_no_verificado"
    if str(licitacion.get("estatus") or "").strip().lower() in ESTADOS_TERMINALES:
        return False, "procedimiento_cerrado"
    if (cliente_id, licitacion.get("id")) in enviados:
        return False, "ya_notificada"
    fecha = licitacion.get("fecha_apertura")
    if not fecha:
        return False, "sin_fecha_apertura"
    try:
        apertura = datetime.fromisoformat(str(fecha).replace("Z","+00:00"))
        if apertura.tzinfo is not None:
            apertura = apertura.astimezone(ZoneInfo("America/Monterrey")).replace(tzinfo=None)
    except (ValueError, TypeError, OverflowError):
        return False, "fecha_invalida"
    if apertura <= ahora:
        return False, "plazo_vencido"
    if not str(licitacion.get("url_procedimiento") or "").startswith("https://"):
        return False, "sin_enlace_procedimiento"
    return True, "candidata_para_reserva_atomica"

def agrupar(candidatos, enviados, ahora=None):
    """candidatos: iterable de (cliente_id, licitacion). Sin efectos externos."""
    grupos, bloqueos = {}, {}
    for cliente_id, licitacion in candidatos:
        ok, motivo = evaluar(licitacion, cliente_id, enviados, ahora)
        if ok:
            grupos.setdefault(cliente_id, []).append(licitacion)
        else:
            bloqueos[motivo] = bloqueos.get(motivo, 0) + 1
    return grupos, bloqueos

def autoprueba():
    base={"id":123,"validacion_calendario":"verificado","estatus":"Vigente",
          "fecha_apertura":"2099-11-06T10:00:00","url_procedimiento":"https://ejemplo.test/123"}
    ahora=datetime(2026,10,24,10,0)
    assert evaluar(base,1,set(),ahora)[0]
    for cambios, motivo in [
        ({"validacion_calendario":"pendiente"},"calendario_no_verificado"),
        ({"fecha_apertura":None},"sin_fecha_apertura"),
        ({"fecha_apertura":"2020-01-01"},"plazo_vencido"),
        ({"url_procedimiento":None},"sin_enlace_procedimiento"),
        ({"estatus":"cancelada"},"procedimiento_cerrado"),
    ]:
        assert evaluar({**base,**cambios},1,set(),ahora)==(False,motivo)
    assert evaluar(base,1,{(1,123)},ahora)==(False,"ya_notificada")
    grupos,bloqueos=agrupar([(1,base),(1,{**base,"id":124,"validacion_calendario":"pendiente"})],set(),ahora)
    assert len(grupos[1])==1 and bloqueos=={"calendario_no_verificado":1}
    print("7 pruebas de compuerta superadas. SOLO LECTURA; NO ENVIA CORREOS.")

if __name__=="__main__":
    autoprueba()
