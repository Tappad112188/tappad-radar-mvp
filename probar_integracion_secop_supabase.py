"""Prueba segura de integracion SECOP -> Supabase. Sin escrituras por defecto.
Lee el lote ya generado en Windows; no repite Chromium ni descarga documentos.
Uso: py probar_integracion_secop_supabase.py
"""
import json, os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE=Path(__file__).resolve().parent
LOTE=BASE/"documentos_secop_lote"/"secop_importacion_pendiente_revision.json"
CAMPOS=("uuid_procedimiento","fuente","numero_procedimiento","cod_expediente",
        "nombre_procedimiento","descripcion","entidad_federativa","estatus",
        "fecha_publicacion","fecha_junta_aclaraciones","fecha_apertura",
        "fecha_fallo_programado","url_procedimiento","documentos_disponibles",
        "url_bases","url_convocatoria","documentos_bases_verificados",
        "documentos_convocatorias_verificados")
def consulta(tabla, columnas, filtros=None):
    url=os.environ["SUPABASE_URL"].rstrip("/")+"/rest/v1/"+tabla+"?"+urlencode({"select":columnas,**(filtros or {})})
    clave=os.environ.get("SUPABASE_ADMIN_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not clave: raise SystemExit("Falta clave Supabase para prueba de solo lectura")
    with urlopen(Request(url,headers={"apikey":clave,"Authorization":"Bearer "+clave}),timeout=40) as respuesta:
        return json.load(respuesta)
def main():
    if not LOTE.is_file(): raise SystemExit("No existe el JSON preparado por SECOP; no se inicia una extraccion nueva")
    lote=json.loads(LOTE.read_text(encoding="utf-8-sig"))
    registros=lote.get("registros",[])
    if not isinstance(registros,list): raise SystemExit("Lote sin registros validos")
    ids=[r.get("uuid_procedimiento") for r in registros]
    if not all(ids) or len(ids)!=len(set(ids)): raise SystemExit("UUID faltantes o duplicados")
    existentes=0
    for r in registros:
        if r.get("fuente")!="SECOP Coahuila" or not r.get("cod_expediente"):
            raise SystemExit("Registro ajeno a SECOP o sin expediente")
        encontrado=consulta("licitaciones","id,uuid_procedimiento",{"uuid_procedimiento":"eq."+r["uuid_procedimiento"]})
        if encontrado: existentes+=1
        # No enviar columnas auxiliares del JSON a la tabla licitaciones.
        preparado={k:v for k,v in r.items() if k in CAMPOS and v is not None}
        if not preparado.get("estatus"): raise SystemExit("Registro sin estatus: "+r["uuid_procedimiento"])
    clientes=consulta("clientes","id",{"activo":"eq.true"})
    giros=consulta("clientes_giros","cliente_id,giro_id")
    print("SECOP: total",len(registros),"| ya existentes",existentes,"| nuevos candidatos",len(registros)-existentes)
    print("Proveedores activos",len(clientes),"| relaciones giro-proveedor",len(giros))
    print("PRUEBA DE SOLO LECTURA COMPLETADA. No se importaron expedientes ni se enviaron correos.")
if __name__=="__main__": main()
