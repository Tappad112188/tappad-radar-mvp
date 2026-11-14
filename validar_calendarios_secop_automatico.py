"""Valida evidencia local SECOP sin redes, Supabase ni SMTP."""
import json
import hashlib
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

BASE=Path(__file__).resolve().parent/"documentos_secop_lote"
ETAPAS=("junta_aclaraciones","limite_presentacion_propuestas","fallo_programado")
PALABRAS={"junta_aclaraciones":("JUNTA DE ACLARACIONES",),"limite_presentacion_propuestas":("PRESENTACI", "APERTURA"),"fallo_programado":("FALLO",)}

def leer(nombre):
    return json.loads((BASE/nombre).read_text(encoding="utf-8-sig"))

def evidencia_documental(f, etapa, fuente):
    """PDF: página identificada. DOCX: documento íntegro y hash SHA256 cotejado."""
    if "BASES" not in fuente.upper():
        return False, "origen sin identificacion de bases"
    if "PÁGINA" in fuente.upper() or "PAGINA" in fuente.upper():
        return True, None
    if "DOCUMENTO WORD" not in fuente.upper():
        return False, "origen documental sin pagina ni Word verificable"
    docs = f.get("documentos") or []
    candidatos = [d for d in docs if str(d.get("nombre") or "").lower().endswith(".docx")
                  and str(d.get("nombre")) in fuente and not d.get("error")]
    if len(candidatos) != 1:
        return False, "documento Word no identificable de forma unica"
    doc = candidatos[0]
    codigo = str(f.get("codigo") or "")
    if not codigo or "/" in codigo or "\\\\" in codigo or ".." in codigo:
        return False, "codigo de carpeta no seguro"
    carpeta = BASE / codigo
    ruta = carpeta / doc["nombre"]
    if not ruta.is_file() or not ruta.resolve().is_relative_to(carpeta.resolve()):
        return False, "archivo Word original no encontrado"
    if hashlib.sha256(ruta.read_bytes()).hexdigest() != doc.get("sha256"):
        return False, "hash del documento Word no coincide"
    return True, None

def validar(f, auditoria):
    codigo=f.get("codigo")
    errores=[]
    eventos={}
    for etapa in ETAPAS:
        e=(f.get("calendario") or {}).get(etapa) or {}
        fecha,hora=e.get("fecha"),e.get("hora")
        try:
            instante=datetime.fromisoformat(str(fecha)+"T"+str(hora))
            if instante.strftime("%Y-%m-%d")!=fecha or instante.strftime("%H:%M")!=hora:
                raise ValueError("formato")
        except (ValueError,TypeError):
            errores.append(etapa+": fecha u hora invalida")
            continue
        fuente=str(e.get("fuente") or "")
        evidencia=str(e.get("evidencia") or "")
        ok_origen, detalle_origen = evidencia_documental(f, etapa, fuente)
        if not ok_origen:
            errores.append(etapa+": "+detalle_origen)
        if not all(k in evidencia.upper() for k in PALABRAS[etapa]):
            errores.append(etapa+": evidencia sin encabezado esperado")
        if e.get("alternativas") or e.get("estado")!="candidato_documental":
            errores.append(etapa+": alternativas o estado ambiguo")
        eventos[etapa]=instante
    if len(eventos)==3:
        if not eventos[ETAPAS[0]] < eventos[ETAPAS[1]] < eventos[ETAPAS[2]]:
            errores.append("orden cronologico inconsistente")
        ahora=datetime.now(ZoneInfo("America/Monterrey")).replace(tzinfo=None)
        if eventos["limite_presentacion_propuestas"]<=ahora:
            errores.append("plazo de presentacion vencido")
    if not auditoria:
        errores.append("sin auditoria de modificaciones")
    else:
        if auditoria.get("estado")!="SIN_INDICIOS_EN_DOCUMENTOS_CAPTURADOS":
            errores.append("auditoria documental no limpia")
        if auditoria.get("errores_pendientes") or auditoria.get("documentos_potencialmente_modificatorios"):
            errores.append("documentos o errores pendientes")
    return {"codigo":codigo,"referencia":f.get("referencia"),"estado":"APTO_PRELIMINAR" if not errores else "BLOQUEADO",
            "errores":errores,"fechas":{k:v.isoformat(timespec="minutes") for k,v in eventos.items()},
            "nota":"Apto preliminar no acredita ausencia de modificaciones posteriores ni autoriza SMTP."}

def main():
    fichas=leer("fichas_comerciales_secop.json")
    revisiones=leer("revision_modificaciones_secop.json")
    auditorias={x.get("codigo"):x for x in revisiones.get("procedimientos",[])}
    resultados=[validar(f,auditorias.get(f.get("codigo"))) for f in fichas.get("fichas",[])]
    salida={"fecha_consulta":fichas.get("fecha_consulta"),"resultados":resultados,
            "escrituras_supabase":False,"envios_habilitados":False}
    (BASE/"validacion_automatica_secop.json").write_text(json.dumps(salida,ensure_ascii=False,indent=2),encoding="utf-8")
    for x in resultados:
        print(x["referencia"],"|",x["estado"],"|","; ".join(x["errores"]) or "evidencia documental coherente")
    print("Sin cambios Supabase ni correos.")

if __name__=="__main__":
    main()
