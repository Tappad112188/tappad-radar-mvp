"""Pruebas aisladas de reporte documental SECOP."""
import unittest
from revisar_calendarios_secop import generar, revisar_ficha


class RevisionCalendariosTests(unittest.TestCase):
    def test_evidencia_completa_sigue_pendiente(self):
        ficha = {"codigo": "ABC", "calendario": {"junta_aclaraciones": {
            "fecha": "2026-11-12", "hora": "11:00",
            "evidencia": "Junta de aclaraciones: 12/11/2026 11:00 horas",
            "fuente": "bases.pdf pagina 4", "estado": "candidato_documental"
        }}}
        r = revisar_ficha(ficha)
        self.assertEqual(r["eventos"]["junta_aclaraciones"]["estado_validacion"], "PENDIENTE_REVISION_HUMANA")
        self.assertFalse(r["apto_para_notificacion_con_fechas"])

    def test_sin_evidencia_se_marca_incompleto(self):
        r = revisar_ficha({"codigo": "ABC", "calendario": {
            "fallo_programado": {"fecha": "2026-11-20", "hora": "12:00"}
        }})
        self.assertEqual(r["eventos"]["fallo_programado"]["estado_validacion"], "INCOMPLETO_REVISAR_BASES")

    def test_no_habilita_correos_ni_escrituras(self):
        r = generar({"fecha_consulta": "2026-11-09", "fichas": [{"codigo": "ABC"}]})
        self.assertEqual(r["total"], 1)
        self.assertFalse(r["notificaciones_habilitadas"])
        self.assertFalse(r["escrituras_supabase"])
        self.assertEqual(r["estado"], "SOLO_REVISION_SIN_PUBLICACION")


if __name__ == "__main__":
    unittest.main(verbosity=2)
