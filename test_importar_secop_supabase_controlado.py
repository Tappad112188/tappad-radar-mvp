"""Pruebas aisladas del importador SECOP: nunca escriben en Supabase."""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
import importar_secop_supabase_controlado as mod

class ImportadorTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.lote=Path(self.tmp.name)/"documentos_secop_lote"/"secop_importacion_pendiente_revision.json"
        self.lote.parent.mkdir()
        p=patch.object(mod,"LOTE",self.lote)
        p.start()
        self.addCleanup(p.stop)
        self.uid="secop-coahuila:prueba-001"
        self.registro={"uuid_procedimiento":self.uid,"fuente":"SECOP Coahuila",
                       "cod_expediente":"PRUEBA-001","nombre_procedimiento":"Procedimiento de prueba",
                       "estatus":"Vigente","fecha_publicacion":"2026-11-09"}
        self.guardar("PENDIENTE_VALIDACION_OFICIAL_NO_IMPORTAR_AUTOMATICAMENTE")

    def guardar(self,estado,registros=None):
        self.lote.write_text(json.dumps({"estado":estado,"registros":self.registro if False else
            ([self.registro] if registros is None else registros)}),encoding="utf-8")

    def ejecutar(self,*args):
        with patch("sys.argv",["importar_secop_supabase_controlado.py",*args]):
            with redirect_stdout(io.StringIO()) as salida:
                mod.main()
            return salida.getvalue()

    def test_simulacion_existente_no_escribe(self):
        with patch.object(mod,"api",return_value=[{"id":1122,"uuid_procedimiento":self.uid}]) as api:
            with patch.object(mod,"urlopen",side_effect=AssertionError("No escribir")):
                salida=self.ejecutar()
        self.assertIn("EXISTENTE",salida)
        self.assertIn("SIMULACION",salida)
        self.assertEqual(api.call_count,1)

    def test_simulacion_nuevo_no_escribe(self):
        with patch.object(mod,"api",return_value=[]):
            with patch.object(mod,"urlopen",side_effect=AssertionError("No escribir")):
                salida=self.ejecutar()
        self.assertIn("NUEVO:",salida)
        self.assertIn("sin escrituras",salida)

    def test_importar_pendiente_sin_autorizacion_bloqueado(self):
        with patch.object(mod,"api",side_effect=AssertionError("No consultar")):
            with self.assertRaises(SystemExit) as e:self.ejecutar("--importar")
        self.assertIn("BLOQUEADA",str(e.exception))

    def test_importar_pendiente_sin_extraccion_bloqueado(self):
        with patch.object(mod,"api",side_effect=AssertionError("No consultar")):
            with self.assertRaises(SystemExit) as e:self.ejecutar("--importar","--registrar_pendientes")
        self.assertIn("Falta evidencia",str(e.exception))

    def test_rechaza_duplicados(self):
        self.guardar("VALIDADO_PARA_IMPORTACION",[self.registro,self.registro])
        with patch.object(mod,"api",side_effect=AssertionError("No consultar")):
            with self.assertRaises(SystemExit) as e:self.ejecutar()
        self.assertIn("duplicado",str(e.exception))

if __name__=="__main__":
    unittest.main(verbosity=2)
