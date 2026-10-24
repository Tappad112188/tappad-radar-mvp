"""Vista previa local de fichas SECOP. No publica ni escribe en Supabase."""
import json, html, re
from pathlib import Path
ROOT=Path(__file__).resolve().parent
SOURCE=ROOT/"documentos_secop_lote"/"secop_importacion_pendiente_revision.json"
OUT=ROOT/"vista_previa_fichas_secop"
PORTAL="https://www.sefincoahuila.gob.mx/sistemas/Secop/Convocatoria"
def esc(value):
    return html.escape(str(value if value is not None else "Pendiente de verificar"),quote=True)
def ficha(record):
    numero=record["numero_procedimiento"]
    codigo=record["cod_expediente"]
    campos={"Procedimiento":numero,"Codigo SECOP":codigo,"Dependencia":record.get("nombre_dependencia"),"Publicacion":record.get("fecha_publicacion"),"Junta de aclaraciones":record.get("fecha_junta_aclaraciones"),"Presentacion y apertura":record.get("fecha_apertura"),"Fallo programado":record.get("fecha_fallo_programado")}
    filas="".join("<dt><b>"+esc(k)+"</b></dt><dd>"+esc(v)+"</dd>" for k,v in campos.items())
    return ('<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>'+esc(numero)+' | TAPPAD Radar</title><style>body{font-family:Arial;background:#f1f5f7;color:#18384b}main{max-width:750px;margin:35px auto;padding:30px;background:white;border-radius:12px}dt{margin-top:14px}dd{margin:5px 0 0}a{color:#116b59}</style><main><p><b>TAPPAD Radar · SECOP Coahuila</b></p><h1>'+esc(record.get("nombre_procedimiento"))+'</h1><dl>'+filas+'</dl><h2>Consultar documentos oficiales</h2><p>Abre el portal SECOP, busca el codigo <b>'+esc(codigo)+'</b> o el procedimiento <b>'+esc(numero)+'</b> y selecciona Documentos de Procedimiento.</p><p><a href="'+PORTAL+'" target="_blank" rel="noopener noreferrer">Abrir portal oficial SECOP</a></p><p><small>Esta ficha es informativa; verifica vigencia, fechas y modificaciones en la convocatoria oficial. El enlace lleva al portal, no directamente al expediente.</small></p></main></html>')
def main():
    data=json.loads(SOURCE.read_text(encoding="utf-8-sig"))
    if data.get("estado")!="PENDIENTE_VALIDACION_OFICIAL_NO_IMPORTAR_AUTOMATICAMENTE":
        raise ValueError("Estado de revision inesperado")
    OUT.mkdir(exist_ok=True)
    manifest=[]
    for r in data.get("registros",[]):
        nombre=re.sub("[^a-z0-9-]","-",r["numero_procedimiento"].lower())+".html"
        (OUT/nombre).write_text(ficha(r),encoding="utf-8")
        manifest.append({"numero":r["numero_procedimiento"],"archivo":nombre,"url_publica":None,"estado":"vista_previa_local"})
    (OUT/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Fichas locales:",len(manifest),"Directorio:",OUT)
if __name__=="__main__":
    main()
