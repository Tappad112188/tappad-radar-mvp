"""Pruebas de extremo a extremo simuladas: no acceden a Supabase ni envian correos."""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
import importar_secop_supabase_controlado as mod


class Respuesta:
    status = 201
    def __enter__(self): return self
    def __exit__(self, *args): return False


class FlujoImportadorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        carpeta = Path(self.tmp.name) / "documentos_secop_lote"
        carpeta.mkdir()
        self.lote = carpeta / "secop_importacion_pendiente_revision.json"
        self.uid = "secop-coahuila:prueba-controlada-001"
        registro = {
            "uuid_procedimiento": self.uid,
            "fuente": "SECOP Coahuila",
            "cod_expediente": "PRUEBA-CONTROLADA-001",
            "nombre_procedimiento": "Prueba aislada de registro",
            "estatus": "Vigente",
            "fecha_publicacion": "2026-11-09",
        }
        self.lote.write_text(json.dumps({
            "estado": "VALIDADO_PARA_IMPORTACION",
            "registros": [registro],
        }), encoding="utf-8")
        p = patch.object(mod, "LOTE", self.lote)
        p.start()
        self.addCleanup(p.stop)

    def correr(self):
        with patch("sys.argv", ["importar_secop_supabase_controlado.py", "--importar"]):
            with redirect_stdout(io.StringIO()) as output:
                mod.main()
            return output.getvalue()

    def test_insercion_nueva_y_confirmacion(self):
        def api(metodo, params=None, datos=None):
            if metodo != "GET":
                raise AssertionError("Metodo inesperado")
            return [] if params["select"] == "id,uuid_procedimiento" else [{"id": 90001}]
        with patch.object(mod, "api", side_effect=api) as consulta:
            with patch.object(mod, "urlopen", return_value=Respuesta()) as post:
                with patch.dict("os.environ", {
                    "SUPABASE_URL": "https://example.supabase.co",
                    "SUPABASE_ADMIN_KEY": "clave-de-prueba",
                }):
                    salida = self.correr()
        self.assertEqual(consulta.call_count, 2)
        self.assertEqual(post.call_count, 1)
        solicitud = post.call_args.args[0]
        self.assertEqual(solicitud.get_method(), "POST")
        self.assertEqual(json.loads(solicitud.data)[0]["validacion_calendario"], "pendiente")
        self.assertEqual(json.loads(solicitud.data)[0]["uuid_procedimiento"], self.uid)
        self.assertIn("CONFIRMADO:", salida)
        self.assertIn("No se enviaron correos", salida)

    def test_existente_no_se_sobrescribe(self):
        with patch.object(mod, "api", return_value=[{"id": 90001, "uuid_procedimiento": self.uid}]) as consulta:
            with patch.object(mod, "urlopen", side_effect=AssertionError("No debe insertar")) as post:
                salida = self.correr()
        self.assertEqual(consulta.call_count, 1)
        post.assert_not_called()
        self.assertIn("EXISTENTE (sin actualizar)", salida)

    def test_no_confirma_si_lectura_posterior_falla(self):
        def api(metodo, params=None, datos=None):
            return []
        with patch.object(mod, "api", side_effect=api):
            with patch.object(mod, "urlopen", return_value=Respuesta()):
                with patch.dict("os.environ", {
                    "SUPABASE_URL": "https://example.supabase.co",
                    "SUPABASE_ADMIN_KEY": "clave-de-prueba",
                }):
                    with self.assertRaisesRegex(RuntimeError, "No se confirmo insercion"):
                        self.correr()


if __name__ == "__main__":
    unittest.main(verbosity=2)
