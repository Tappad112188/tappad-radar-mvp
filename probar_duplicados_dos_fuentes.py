"""Prueba de deduplicacion y consolidacion de fuentes de TAPPAD Radar.
Solo simulacion. No accede a red ni modifica bases de datos.
"""
from control_notificaciones import separar_notificaciones

PROVEEDOR="proveedor-prueba-001"
CANDIDATAS=[
 {"cliente_id":PROVEEDOR,"licitacion_id":"comprasmx:IA-PRUEBA-2026","fuente":"ComprasMX","numero_procedimiento":"IA-PRUEBA-2026"},
 {"cliente_id":PROVEEDOR,"licitacion_id":"secop-coahuila:UTC01-2026","fuente":"SECOP Coahuila","numero_procedimiento":"UTC-LPN-CA-E001-2026"},
 {"cliente_id":PROVEEDOR,"licitacion_id":"secop-coahuila:UTC01-2026","fuente":"SECOP Coahuila","numero_procedimiento":"UTC-LPN-CA-E001-2026"},
]
def resumen(resultado):
 return {k:len(resultado[k]) for k in ("nuevas","retenidas","reintentos")}
def verificar(condicion,mensaje):
 if not condicion:raise AssertionError(mensaje)
def main():
 print("TAPPAD RADAR | PRUEBA DE DUPLICADOS Y DOS FUENTES")
 print("Datos ficticios: NO se enviaran correos")
 primero=separar_notificaciones(CANDIDATAS,[])
 print("Primera revision:",resumen(primero))
 verificar(len(primero["nuevas"])==2,"Deben quedar dos oportunidades distintas")
 verificar({x["fuente"] for x in primero["nuevas"]}=={"ComprasMX","SECOP Coahuila"},"Falta alguna fuente")
 por_proveedor={}
 for op in primero["nuevas"]:por_proveedor.setdefault(op["cliente_id"],[]).append(op)
 verificar(len(por_proveedor)==1 and len(por_proveedor[PROVEEDOR])==2,"Debe prepararse un solo correo con dos oportunidades")
 print("Correo consolidado:",len(por_proveedor),"correo(s),",len(por_proveedor[PROVEEDOR]),"oportunidades")
 historial=[{"cliente_id":x["cliente_id"],"licitacion_id":x["licitacion_id"],"estado":"enviado"} for x in primero["nuevas"]]
 segundo=separar_notificaciones(CANDIDATAS,historial)
 print("Segunda revision (ya notificadas):",resumen(segundo))
 verificar(len(segundo["nuevas"])==0 and len(segundo["retenidas"])==2,"No se deben reenviar alertas")
 historial[1]["estado"]="pendiente"
 tercero=separar_notificaciones(CANDIDATAS,historial)
 print("Tercera revision (una pendiente):",resumen(tercero))
 verificar(len(tercero["nuevas"])==0,"Pendiente no debe volver a notificarse")
 historial[1]["estado"]="error"
 cuarto=separar_notificaciones(CANDIDATAS,historial)
 print("Cuarta revision (un error):",resumen(cuarto))
 verificar(len(cuarto["reintentos"])==1 and len(cuarto["nuevas"])==0,"El error debe ir a reintentos, no a novedades")
 print("RESULTADO: TODAS LAS PRUEBAS APROBADAS")
 print("IMPORTANTE: el historial usado es simulado; falta persistirlo en la infraestructura real.")
if __name__=="__main__":main()
