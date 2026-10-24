"""Pruebas sin red ni correos del filtro de publicacion SECOP."""
from preparador_alertas import secop_apto_para_alerta

BASE={"fuente":"SECOP Coahuila","url_procedimiento":None,"validacion_calendario":None}
CASOS=[
 ("Sin enlace", BASE,False),
 ("Portada generica", {**BASE,"url_procedimiento":"https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria","validacion_calendario":"confirmada_sin_modificaciones"},False),
 ("Enlace externo", {**BASE,"url_procedimiento":"https://example.com/procedimiento/123","validacion_calendario":"confirmada_sin_modificaciones"},False),
 ("Enlace individual sin validar", {**BASE,"url_procedimiento":"https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria?id=123"},False),
 ("Enlace individual validado", {**BASE,"url_procedimiento":"https://www.sefincoahuila.gob.mx/sistemas/Secop/Detalle?id=123","validacion_calendario":"confirmada_sin_modificaciones"},True),
 ("ComprasMX no cambia", {"fuente":"ComprasMX","url_procedimiento":None},True),
]
for nombre,registro,esperado in CASOS:
 resultado=secop_apto_para_alerta(registro)
 print(nombre,":", "OK" if resultado==esperado else "ERROR", "| habilitado:",resultado)
 assert resultado==esperado,nombre
print("TODAS LAS PRUEBAS APROBADAS. No se enviaron correos.")
