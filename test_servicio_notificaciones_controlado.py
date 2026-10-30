import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from servicio_notificaciones_controlado import ServicioNotificaciones, ReservaExistente


class PruebasServicio(unittest.TestCase):
    def setUp(self):
        self.envio = []
        self.servicio = ServicioNotificaciones(
            "https://ejemplo.supabase.co", "clave_de_prueba",
            transport=lambda *args: self.envio.append(args))
        self.licitacion = {"id": 99, "estatus": "Vigente",
                           "fecha_apertura": "2099-01-01T12:00:00"}

    def test_bloqueado_sin_autorizacion(self):
        resultado = self.servicio.enviar_prueba_controlada(
            1, self.licitacion, "tappadcons@gmail.com", "asunto", "<p>test</p>")
        self.assertEqual(resultado["estado"], "bloqueado")
        self.assertFalse(self.envio)

    def test_bloqueado_destino_externo(self):
        resultado = self.servicio.enviar_prueba_controlada(
            1, self.licitacion, "cliente@example.com", "asunto", "<p>test</p>",
            autorizar=True, modo_prueba=True)
        self.assertEqual(resultado["motivo"], "destinatario_no_autorizado")

    def test_interruptor_apagado(self):
        with patch.object(self.servicio, "configuracion", return_value={"alertas_automaticas_habilitadas": "false"}):
            resultado = self.servicio.enviar_prueba_controlada(
                1, self.licitacion, "tappadcons@gmail.com", "asunto", "<p>test</p>",
                autorizar=True, modo_prueba=True)
        self.assertEqual(resultado["motivo"], "alertas_automaticas_desactivadas")
        self.assertFalse(self.envio)

    def test_reserva_duplicada(self):
        with patch.object(self.servicio, "configuracion", return_value={"alertas_automaticas_habilitadas": "true"}), \
             patch.object(self.servicio, "reservar", side_effect=ReservaExistente()):
            resultado = self.servicio.enviar_prueba_controlada(
                1, self.licitacion, "tappadcons@gmail.com", "asunto", "<p>test</p>",
                autorizar=True, modo_prueba=True)
        self.assertEqual(resultado["motivo"], "duplicado")
        self.assertFalse(self.envio)

    def test_reserva_y_aceptacion(self):
        with patch.object(self.servicio, "configuracion", return_value={"alertas_automaticas_habilitadas": "true"}), \
             patch.object(self.servicio, "reservar", return_value=77), \
             patch.object(self.servicio, "_estado", return_value={"id": 77}) as estados:
            resultado = self.servicio.enviar_prueba_controlada(
                1, self.licitacion, "tappadcons@gmail.com", "asunto", "<p>test</p>",
                autorizar=True, modo_prueba=True)
        self.assertEqual(resultado["estado"], "aceptado_por_smtp")
        self.assertEqual(estados.call_count, 2)
        self.assertEqual(len(self.envio), 1)

    def test_fallo_smtp_sin_reintento(self):
        self.servicio.transport = lambda *args: (_ for _ in ()).throw(TimeoutError())
        with patch.object(self.servicio, "configuracion", return_value={"alertas_automaticas_habilitadas": "true"}), \
             patch.object(self.servicio, "reservar", return_value=77), \
             patch.object(self.servicio, "_estado", return_value={"id": 77}) as estados:
            resultado = self.servicio.enviar_prueba_controlada(
                1, self.licitacion, "tappadcons@gmail.com", "asunto", "<p>test</p>",
                autorizar=True, modo_prueba=True)
        self.assertEqual(resultado["estado"], "revision_manual")
        self.assertEqual(estados.call_count, 2)


if __name__ == "__main__":
    unittest.main()
