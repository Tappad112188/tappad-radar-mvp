"""Motor SECOP: simula coincidencias con clientes activos. Nunca envia ni escribe.
Requiere SUPABASE_URL y SUPABASE_ADMIN_KEY; no afecta ComprasMX.
"""
import argparse, html, json, os, re, unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parent
SALIDA=ROOT/"documentos_secop_lote"/"simulacion_alertas_secop.json"
PERMITIDOS={"gerardotapia112188@gmail.com","tappadcons@gmail.com"}

def consultar(tabla, parametros):
    base=os.getenv("SUPABASE_URL")
    clave=os.getenv("SUPABASE_ADMIN_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not base or not clave:
        raise SystemExit("Faltan credenciales Supabase")
    url=base.rstrip("/")+"/rest/v1/"+tabla+"?"+urlencode(parametros)
    req=Request(url,headers={"apikey":clave,"Authorization":"Bearer "+clave,"Accept":"application/json"})
    with urlopen(req,timeout=45) as respuesta:
        return json.load(respuesta)

def normalizar(valor):
    texto=unicodedata.normalize("NFD",str(valor or "").casefold())
    return "".join(c for c in texto if unicodedata.category(c)!="Mn")

def coincide(clave,descripcion):
    clave=normalizar(clave).strip()
    if len(clave)<3:
        return False
    return re.search(r"(?<!\w)"+re.escape(clave)+r"(?!\w)",normalizar(descripcion)) is not None

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--fecha",help="Fecha de publicacion AAAA-MM-DD; por defecto hoy en Coahuila")
    parser.add_argument("--incluir-inactivos",action="store_true",help="Solo diagnostico: incluye clientes inactivos sin habilitar envios")
    args=parser.parse_args()
    hoy=datetime.now(ZoneInfo("America/Monterrey"))
    fecha=args.fecha or hoy.date().isoformat()
    datetime.strptime(fecha,"%Y-%m-%d")
    licitaciones=consultar("licitaciones",{
        "select":"id,numero_procedimiento,nombre_procedimiento,descripcion,fecha_publicacion,fecha_apertura,fecha_junta_aclaraciones,fecha_fallo_programado,validacion_calendario,fuente,estatus",
        "fuente":"eq.SECOP Coahuila","validacion_calendario":"eq.preliminar_documental",
        "fecha_publicacion":"gte."+fecha+"T00:00:00",
        "and":"(fecha_publicacion.lt."+fecha+"T23:59:59.999999,fecha_apertura.gt."+hoy.strftime("%Y-%m-%dT%H:%M:%S")+")",
        "limit":"1000"})
    filtro_clientes={"select":"id,empresa,correo,palabras_clave,activo","limit":"1000"}
    if not args.incluir_inactivos:
        filtro_clientes["activo"]="eq.true"
    clientes=consultar("clientes",filtro_clientes)
    enviados=consultar("notificaciones_enviadas",{"select":"cliente_id,licitacion_id,estado","limit":"10000"})
    ya={(int(n["cliente_id"]),int(n["licitacion_id"])) for n in enviados if n.get("estado") in ("enviado","pendiente","procesando")}
    resultados=[]
    for l in licitaciones:
        if str(l.get("estatus") or "").casefold()!="vigente":
            continue
        descripcion=" ".join((l.get("nombre_procedimiento") or "",l.get("descripcion") or ""))
        for c in clientes:
            claves=[x.strip() for x in (c.get("palabras_clave") or "").split(",") if x.strip()]
            hits=list(dict.fromkeys(x for x in claves if coincide(x,descripcion)))
            if not hits:
                continue
            destino=(c.get("correo") or "").strip().lower()
            estado=("cliente_inactivo" if not c["activo"] else
                    "duplicado" if (c["id"],l["id"]) in ya else
                    "destinatario_no_autorizado" if destino not in PERMITIDOS else "listo_para_revision")
            resultados.append({"cliente_id":c["id"],"empresa":c["empresa"],"destinatario":destino,
                "licitacion_id":l["id"],"procedimiento":l["numero_procedimiento"],
                "coincidencias":hits,"estado":estado})
    SALIDA.parent.mkdir(parents=True,exist_ok=True)
    SALIDA.write_text(json.dumps({"fecha":fecha,"generado_en":hoy.isoformat(),
        "licitaciones_revisadas":len(licitaciones),"clientes_activos":len(clientes),
        "resultados":resultados},ensure_ascii=False,indent=2),encoding="utf-8")
    print("SECOP SIMULACION | fecha:",fecha,"| licitaciones:",len(licitaciones),
          "| clientes activos:",len(clientes),"| coincidencias:",len(resultados))
    for r in resultados:
        print(r["estado"],"|",r["procedimiento"],"| cliente",r["cliente_id"],
              "|",", ".join(r["coincidencias"]))
    print("REPORTE:",SALIDA)
    print("SIN CORREOS. SIN ESCRITURAS SUPABASE.")

if __name__=="__main__":
    main()
