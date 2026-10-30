"""Prueba integral simulada: flujo completo sin red, Supabase real ni Gmail."""
import unittest
from urllib.error import HTTPError
from servicio_notificaciones_controlado import ServicioNotificaciones

class SupabaseSimulado(ServicioNotificaciones):
    def __init__(self, transporte):
        super().__init__("https://simulado.supabase.co", "clave-ficticia", transporte)
        self.registros = {}
        self.eventos = []
        self.habilitado = "false"
        self.siguiente_id = 1

    def _rest(self, metodo, tabla, filtros=None, datos=None, prefer=None):
        self.eventos.append((metodo, tabla))
        if tabla == "configuracion_operativa_tappad":
            return [{"clave": "alertas_automaticas_habilitadas", "valor": self.habilitado}]
        if metodo == "POST":
            clave = (datos["cliente_id"], datos["licitacion_id"])
            if clave in self.registros:
                raise HTTPError("https://simulado.supabase.co", 409, "duplicado", {}, None)
            registro = {**datos, "id": self.siguiente_id}
            self.siguiente_id += 1
            self.registros[clave] = registro
            return [registro.copy()]
        if metodo == "PATCH":
            identificador = int(filtros["id"][3:])
            estado_esperado = filtros["estado"][3:]
            for registro in self.registros.values():
                if registro["id"] == identificador and registro["estado"] == estado_esperado:
                    registro.update(datos)
                    return [registro.copy()]
            return []
        raise AssertionError((metodo, tabla))

class PruebaIntegral(unittest.TestCase):
    def setUp(self):
        self.smtp = []
        self.db = SupabaseSimulado(lambda *args: self.smtp.append(args))
        self.licitacion = {"id": 500, "estatus": "Vigente", "fecha_apertura": "2099-01-01T12:00:00"}

    def enviar(self, destino="tappadcons@gmail.com"):
        return self.db.enviar_prueba_controlada(
            4, self.licitacion, destino, "[PRUEBA] TAPPAD Radar",
            "<p>SIMULACION INTERNA - NO ES ALERTA REAL</p>",
            autorizar=True, modo_prueba=True)

    def test_interruptor_real_desactivado_impide_todo(self):
        resultado = self.enviar()
        self.assertEqual(resultado["motivo"], "alertas_automaticas_desactivadas")
        self.assertFalse(self.db.registros)
        self.assertFalse(self.smtp)

    def test_integral_reserva_estados_duplicado(self):
        self.db.habilitado = "true"  # SOLO EN MEMORIA
        resultado = self.enviar()
        self.assertEqual(resultado["estado"], "aceptado_por_smtp")
        registro = self.db.registros[(4, 500)]
        self.assertEqual(registro["estado"], "enviado")
        self.assertEqual(registro["intentos"], 1)
        self.assertTrue(registro.get("enviado_en"))
        self.assertEqual(len(self.smtp), 1)
        self.assertEqual(self.enviar()["motivo"], "duplicado")
        self.assertEqual(len(self.smtp), 1)

    def test_fallo_smtp_sin_reintento_automatico(self):
        self.db.habilitado = "true"  # SOLO EN MEMORIA
        def falla(*args):
            raise TimeoutError("resultado incierto")
        self.db.transport = falla
        self.assertEqual(self.enviar()["estado"], "revision_manual")
        registro = self.db.registros[(4, 500)]
        self.assertEqual(registro["estado"], "error")
        self.assertEqual(registro["intentos"], 1)
        self.assertEqual(self.enviar()["motivo"], "duplicado")

    def test_bloqueo_destino_ajeno(self):
        self.db.habilitado = "true"
        self.assertEqual(self.enviar("cliente@ejemplo.com")["motivo"], "destinatario_no_autorizado")
        self.assertFalse(self.db.registros)

    def test_bloqueo_vencimiento(self):
        self.db.habilitado = "true"
        self.licitacion["fecha_apertura"] = "2020-01-01T12:00:00"
        self.assertEqual(self.enviar()["motivo"], "plazo_vencido")
        self.assertFalse(self.db.registros)

if __name__ == "__main__":
    unittest.main()
