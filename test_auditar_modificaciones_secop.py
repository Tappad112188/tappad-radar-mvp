import unittest
import tempfile
import zipfile
from pathlib import Path
from auditar_modificaciones_secop import auditar_procedimiento, generar

class AuditoriaModificacionesTests(unittest.TestCase):
    def test_detecta_acta(self):
        r = auditar_procedimiento({"codigo": "ABC", "enlaces_documentos": [{"texto": "Acta de aclaraciones", "url": "https://ejemplo.test/acta"}]})
        self.assertEqual(r["estado"], "POSIBLE_MODIFICACION_REVISAR")
        self.assertEqual(len(r["documentos_potencialmente_modificatorios"]), 1)

    def test_sin_indicios_no_equivale_a_validacion(self):
        r = auditar_procedimiento({"codigo": "ABC", "enlaces_documentos": []})
        self.assertEqual(r["estado"], "SIN_INDICIOS_EN_DOCUMENTOS_CAPTURADOS")
        self.assertFalse(r["fechas_oficialmente_validadas"])

    def test_error_descarga_no_es_aprobacion(self):
        r = auditar_procedimiento({"codigo": "ABC", "errores": ["No se capturaron descargas"]})
        self.assertEqual(r["estado"], "COBERTURA_INCOMPLETA_REVISAR")

    def test_pdf_duplicado_en_zip_conserva_advertencia(self):
        with tempfile.TemporaryDirectory() as carpeta:
            pdf = Path(carpeta) / "BASES.pdf"
            pdf.write_bytes(b"bases oficiales")
            paquete = Path(carpeta) / "BASES Y ANEXOS.zip"
            with zipfile.ZipFile(paquete, "w") as z:
                z.writestr("BASES.pdf", b"bases oficiales")
            resultado = auditar_procedimiento({
                "codigo": "ABC",
                "archivos": [{"nombre": pdf.name, "ruta": str(pdf)}, {"nombre": paquete.name, "ruta": str(paquete)}],
                "errores": ["Multiples enlaces de bases: requieren revision"],
            })
            self.assertTrue(resultado["bases_duplicadas_confirmadas"])
            self.assertEqual(resultado["estado"], "COBERTURA_INCOMPLETA_REVISAR")
            self.assertEqual(len(resultado["errores_pendientes"]), 1)

    def test_no_envia_ni_escribe(self):
        r = generar({"procedimientos": [{"codigo": "ABC"}]})
        self.assertFalse(r["notificaciones_habilitadas"])
        self.assertFalse(r["escrituras_supabase"])

if __name__ == "__main__":
    unittest.main()
