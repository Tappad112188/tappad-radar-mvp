"""Prueba aislada de TAPPAD Radar: cuatro clientes ficticios, cuatro expedientes.
No modifica Supabase ni el historial de notificaciones. SMTP solo con --enviar.
"""
import argparse
import json
import os
import smtplib
from email.message import EmailMessage
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from motor_coincidencias import generar_coincidencias
from preparador_alertas import preparar_alertas, vista_previa_correo

CLIENTES = (18, 19, 20, 21)
EXPEDIENTES = (
    "SIDS-AI3-CO-E029-2026",
    "LA-09-J0U-009J0U996-N-28-2026",
    "LA-38-91A-03891A003-I-39-2026",
    "LA-64-O87-905040987-N-29-2026",
)
DESTINOS = {
    18: "tappadcons@gmail.com",
    19: "gerardotapia112188@gmail.com",
    20: "tappadcons@gmail.com",
    21: "gerardotapia112188@gmail.com",
}
PERMITIDOS = frozenset(DESTINOS.values())


def consultar(tabla, filtro, columnas="*"):
    url = os.environ["SUPABASE_URL"].rstrip("/") + "/rest/v1/" + tabla + "?" + urlencode({"select": columnas}) + "&" + filtro
    clave = os.environ["SUPABASE_ADMIN_KEY"]
    req = Request(url, headers={"apikey": clave, "Authorization": "Bearer " + clave})
    with urlopen(req, timeout=30) as response:
        return json.load(response)


def ejecutar(enviar=False):
    clientes = consultar("clientes", "id=in.(18,19,20,21)")
    licitaciones = consultar("licitaciones", "numero_procedimiento=in.(" + ",".join(EXPEDIENTES) + ")")
    coberturas = consultar("clientes_ubicaciones", "cliente_id=in.(18,19,20,21)")
    preferencias = consultar("clientes_giros_preferencias_tappad", "cliente_id=in.(18,19,20,21)&activo=eq.true")
    if {c["id"] for c in clientes} != set(CLIENTES) or {l["numero_procedimiento"] for l in licitaciones} != set(EXPEDIENTES):
        raise RuntimeError("Faltan registros esperados: envío bloqueado")
    for c in clientes:
        if c.get("activo") is not False or not str(c.get("empresa", "")).startswith("[PRUEBA]"):
            raise RuntimeError("El cliente no es ficticio e inactivo: envío bloqueado")
        if c.get("correos_prueba") != [DESTINOS[c["id"]]]:
            raise RuntimeError("Destinatario no coincide con lista autorizada")
    for l in licitaciones:
        if str(l.get("fecha_publicacion", ""))[:10] != "2026-11-10":
            raise RuntimeError("Fecha de publicación distinta a la muestra autorizada")
    cobertura = {id: [x for x in coberturas if x["cliente_id"] == id] for id in CLIENTES}
    prefs = {id: [x for x in preferencias if x["cliente_id"] == id] for id in CLIENTES}
    simulados = [{**c, "activo": True} for c in clientes]  # Solo memoria.
    hallazgos = generar_coincidencias(simulados, licitaciones, cobertura, preferencias_por_cliente=prefs)
    print("Coincidencias reales del motor:", len(hallazgos))
    for h in hallazgos:
        l = next(x for x in licitaciones if x["id"] == h["licitacion_id"])
        print("  Cliente", h["cliente_id"], "->", l["numero_procedimiento"], "|", ",".join(h["terminos"]))
    if len(hallazgos) != 4 or {h["cliente_id"] for h in hallazgos} != set(CLIENTES):
        raise RuntimeError("Matriz de coincidencias inesperada; envío bloqueado")
    # Reutilizar el preparador con proveedores activados solo en memoria.
    preparado = preparar_alertas(simulados, licitaciones, cobertura, [], preferencias_por_cliente=prefs)
    print("Preparador de alertas:", json.dumps(preparado["resumen"], ensure_ascii=False))
    # SECOP no se fuerza: solo enviar si el preparador lo considera apto.
    por_cliente = preparado["por_proveedor"]
    mensajes = []
    for c in sorted(clientes, key=lambda x: x["id"]):
        oportunidades = por_cliente.get(c["id"], [])
        if not oportunidades:
            print("RETENIDA / SIN ALERTA:", c["id"])
            continue
        vista = vista_previa_correo(c["empresa"], oportunidades)
        msg = EmailMessage()
        msg["To"] = DESTINOS[c["id"]]
        msg["Subject"] = "[PRUEBA CONTROLADA] " + vista["asunto"]
        msg.set_content("SIMULACIÓN INTERNA. NO ES UNA NOTIFICACIÓN COMERCIAL.\n\n" + vista["cuerpo"])
        mensajes.append(msg)
        print("PREVISTA:", c["id"], DESTINOS[c["id"]], len(oportunidades), "licitación(es)")
    if not enviar:
        print("VISTA PREVIA: 0 correos enviados. Ejecutar --enviar para envío controlado.")
        return
    if not mensajes:
        raise RuntimeError("No hay mensajes aptos para envío")
    usuario = os.environ.get("SMTP_USER", "").strip().lower()
    clave = os.environ.get("SMTP_APP_PASSWORD", "")
    if usuario != "tappadcons@gmail.com" or not clave:
        raise RuntimeError("Faltan credenciales SMTP válidas en el entorno; no se enviaron correos")
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=40) as smtp:
        smtp.starttls()
        smtp.login(usuario, clave)
        for msg in mensajes:
            if msg["To"] not in PERMITIDOS:
                raise RuntimeError("Destinatario no autorizado")
            msg["From"] = usuario
            smtp.send_message(msg, from_addr=usuario, to_addrs=[msg["To"]])
            print("SMTP ACEPTADO:", msg["To"], msg["Subject"])
    print("Finalizado sin escrituras en Supabase. Aceptación SMTP no garantiza entrega.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--enviar", action="store_true")
    args = parser.parse_args()
    ejecutar(enviar=args.enviar)
