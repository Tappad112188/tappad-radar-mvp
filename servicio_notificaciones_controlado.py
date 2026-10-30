"""Servicio de notificaciones TAPPAD: reserva unica, registro y SMTP controlado.

NO se ejecuta automaticamente. No incluye scraping SECOP ni un scheduler.
Los secretos SUPABASE_ADMIN_KEY y SMTP_APP_PASSWORD solo van en servidor privado.
La aceptacion SMTP NO garantiza entrega final. Nunca reintenta automaticamente.
"""
import json
import os
import smtplib
from email.message import EmailMessage
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from control_notificaciones import autorizar_envio_real

DESTINATARIOS_PRUEBA = frozenset({
    "tappadcons@gmail.com", "gerardotapia112188@gmail.com"
})


class ReservaExistente(Exception):
    pass


class ServicioNotificaciones:
    def __init__(self, url, clave, transport=None):
        if not url.startswith("https://") or not clave:
            raise ValueError("Supabase requiere HTTPS y clave administrativa")
        self.url, self.clave, self.transport = url.rstrip("/"), clave, transport

    def _rest(self, metodo, tabla, filtros=None, datos=None, prefer=None):
        destino = self.url + "/rest/v1/" + tabla
        if filtros:
            destino += "?" + urlencode(filtros)
        cab = {"apikey": self.clave, "Authorization": "Bearer " + self.clave,
               "Content-Type": "application/json", "Accept": "application/json"}
        if prefer:
            cab["Prefer"] = prefer
        req = Request(destino, data=json.dumps(datos).encode() if datos is not None else None,
                      headers=cab, method=metodo)
        with urlopen(req, timeout=30) as respuesta:
            contenido = respuesta.read()
        return json.loads(contenido) if contenido else []

    def configuracion(self):
        filas = self._rest("GET", "configuracion_operativa_tappad",
                           {"select": "clave,valor", "clave": "eq.alertas_automaticas_habilitadas"})
        return {f["clave"]: f["valor"] for f in filas}

    def reservar(self, cliente_id, licitacion_id):
        # La restriccion UNIQUE(cliente_id,licitacion_id) decide atomicamente.
        try:
            filas = self._rest("POST", "notificaciones_enviadas", datos={
                "cliente_id": cliente_id, "licitacion_id": licitacion_id,
                "estado": "pendiente", "intentos": 0
            }, prefer="return=representation")
        except HTTPError as exc:
            if exc.code == 409:
                raise ReservaExistente("Notificacion existente; no reenviar") from exc
            raise
        if len(filas) != 1 or filas[0].get("estado") != "pendiente":
            raise RuntimeError("Reserva no confirmada; revisar manualmente")
        return filas[0]["id"]

    def _estado(self, registro_id, estado, intentos, error=None):
        # Si se pierde la respuesta HTTP, NO repetir el SMTP automaticamente.
        filas = self._rest("PATCH", "notificaciones_enviadas",
            {"id": "eq." + str(registro_id), "estado": "eq." + ("pendiente" if estado == "procesando" else "procesando")},
            {"estado": estado, "intentos": intentos, "ultimo_error": error,\n             **({"enviado_en": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()} if estado == "enviado" else {})},
            "return=representation")
        if len(filas) != 1:
            raise RuntimeError("Transicion de estado no confirmada")
        return filas[0]

    def enviar_prueba_controlada(self, cliente_id, licitacion, destino, asunto, html,
                                *, autorizar=False, modo_prueba=False):
        """Requiere autorizacion explicita y solo dos correos de prueba.

        El modo de prueba NO anula el interruptor general de Supabase.
        """
        if not (autorizar and modo_prueba):
            return {"estado": "bloqueado", "motivo": "autorizacion_explicita_requerida"}
        destino = str(destino).strip().lower()
        if destino not in DESTINATARIOS_PRUEBA:
            return {"estado": "bloqueado", "motivo": "destinatario_no_autorizado"}
        config = self.configuracion()
        ok, motivo = autorizar_envio_real(config, licitacion)
        if not ok:
            return {"estado": "bloqueado", "motivo": motivo}
        # Verificacion de historial previa; la reserva UNIQUE es la proteccion final.
        try:
            registro_id = self.reservar(cliente_id, licitacion["id"])
        except ReservaExistente:
            return {"estado": "bloqueado", "motivo": "duplicado"}
        # Una vez reservada, cualquier error es de revision manual.
        self._estado(registro_id, "procesando", 1)
        try:
            if self.transport is None:
                raise RuntimeError("Transporte SMTP no configurado")
            self.transport(destino, asunto, html)
        except Exception as exc:
            try:
                self._estado(registro_id, "error", 1, "SMTP incierto: " + type(exc).__name__)
            except Exception:
                pass
            return {"estado": "revision_manual", "registro_id": registro_id}
        try:
            self._estado(registro_id, "enviado", 1)
        except Exception:
            return {"estado": "revision_manual", "registro_id": registro_id}
        return {"estado": "aceptado_por_smtp", "registro_id": registro_id}


def transporte_gmail(destino, asunto, html):
    usuario = os.environ["SMTP_USER"].strip().lower()
    clave = os.environ["SMTP_APP_PASSWORD"]
    if usuario != "tappadcons@gmail.com" or destino not in DESTINATARIOS_PRUEBA:
        raise ValueError("Remitente o destinatario fuera de la lista de prueba")
    mensaje = EmailMessage()
    mensaje["From"], mensaje["To"], mensaje["Subject"] = usuario, destino, asunto
    mensaje.set_content("Prueba interna TAPPAD Radar. Verifica los expedientes oficiales.")
    mensaje.add_alternative(html, subtype="html")
    with smtplib.SMTP("smtp.gmail.com", 587, timeout=40) as smtp:
        smtp.starttls()
        smtp.login(usuario, clave)
        smtp.send_message(mensaje, from_addr=usuario, to_addrs=[destino])
