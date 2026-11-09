"""Pruebas locales sin red ni escritura para auditoria diaria SECOP."""
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse
from zoneinfo import ZoneInfo
import auditar_secop_supabase_diario as mod

class Respuesta(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *args): self.close()

class AuditoriaSecopTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name)
        self.hoy=datetime.now(ZoneInfo("America/Monterrey")).date().isoformat()
        self.uid1="secop-coahuila:prueba-existente"
        self.uid2="secop-coahuila:prueba-nuevo"
        self.ext=root/"secop_hoy_vigentes.json"
        self.lote=root/"lote.json"
        self.reporte=root/"reporte.json"
        self.patches=[patch.object(mod,"EXTRACCION",self.ext),patch.object(mod,"LOTE",self.lote),
                      patch.object(mod,"REPORTE",self.reporte)]
        for p in self.patches: p.start();self.addCleanup(p.stop)
        self.fuente={"fecha_consulta":self.hoy,"filtros_aplicados":True,"coincide_total":True,
                     "registros":[{"codigo":"PRUEBA-EXISTENTE","fecha_publicacion":self.hoy,"estatus":"Vigente"},
                                  {"codigo":"PRUEBA-NUEVO","fecha_publicacion":self.hoy,"estatus":"Vigente"}]}
        self.preparados=[{"uuid_procedimiento":self.uid1,"cod_expediente":"PRUEBA-EXISTENTE",
                          "fuente":"SECOP Coahuila","estatus":"Vigente","fecha_publicacion":self.hoy},
                         {"uuid_procedimiento":self.uid2,"cod_expediente":"PRUEBA-NUEVO",
                          "fuente":"SECOP Coahuila","estatus":"Vigente","fecha_publicacion":self.hoy}]
        self.guardar()

    def guardar(self):
        self.ext.write_text(json.dumps(self.fuente),encoding="utf-8")
        self.lote.write_text(json.dumps({"estado":"PENDIENTE_VALIDACION_OFICIAL_NO_IMPORTAR_AUTOMATICAMENTE",
                                        "registros":self.preparados}),encoding="utf-8")

    def test_identifica_existente_y_nuevo(self):
        def responder(req,timeout=25):
            uid=parse_qs(urlparse(req.full_url).query)["uuid_procedimiento"][0][3:]
            return Respuesta(json.dumps([{"uuid_procedimiento":uid}] if uid==self.uid1 else []).encode())
        with patch.dict(os.environ,{"SUPABASE_URL":"https://example.supabase.co",
                                    "SUPABASE_ADMIN_KEY":"clave-ficticia"}),patch.object(mod,"urlopen",side_effect=responder):
            with redirect_stdout(io.StringIO()):mod.main()
        resultado=json.loads(self.reporte.read_text(encoding="utf-8"))
        self.assertEqual(resultado["existentes"],[self.uid1])
        self.assertEqual(resultado["nuevos"],[self.uid2])
        self.assertFalse(resultado["importacion_habilitada"])
        self.assertFalse(resultado["notificaciones_habilitadas"])

    def test_rechaza_fecha_incorrecta(self):
        self.fuente["fecha_consulta"]="2020-01-01"
        self.guardar()
        with self.assertRaises(SystemExit):mod.main()
        self.assertFalse(self.reporte.exists())

    def test_rechaza_lote_incompleto(self):
        self.preparados.pop()
        self.guardar()
        with self.assertRaises(SystemExit):mod.main()
        self.assertFalse(self.reporte.exists())

    def test_sin_credenciales_no_consulta(self):
        with patch.dict(os.environ,{"SUPABASE_URL":"","SUPABASE_ADMIN_KEY":"","SUPABASE_SERVICE_ROLE_KEY":""}):
            with patch.object(mod,"urlopen",side_effect=AssertionError("No debe llamar API")):
                with redirect_stdout(io.StringIO()):mod.main()
        resultado=json.loads(self.reporte.read_text(encoding="utf-8"))
        self.assertEqual(resultado["consulta_supabase"],"no_realizada_faltan_variables")
        self.assertFalse(resultado["importacion_habilitada"])

if __name__=="__main__":
    unittest.main(verbosity=2)
