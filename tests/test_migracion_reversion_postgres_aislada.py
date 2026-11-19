"""Prueba de migracion comercial sobre PostgreSQL efimero; nunca Supabase productivo."""
import os
import unittest
from pathlib import Path

try:
    import psycopg
except ImportError:
    psycopg = None

ROOT = Path(__file__).resolve().parents[1]
DSN = os.getenv("TAPPAD_TEST_POSTGRES_DSN")


@unittest.skipUnless(DSN and psycopg, "Requiere PostgreSQL efimero y psycopg")
class MigracionReversionAislada(unittest.TestCase):
    def test_migracion_rls_roles_y_funcion(self):
        with psycopg.connect(DSN) as conn:
            db = conn.execute("select current_database()").fetchone()[0]
            if db != "tappad_ci_pruebas":
                raise RuntimeError("Prohibido ejecutar fuera de tappad_ci_pruebas")
            conn.execute("create schema if not exists ci_migracion")
            for role in ("anon", "authenticated"):
                conn.execute(f"""DO $r$ BEGIN
                    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='{role}')
                    THEN CREATE ROLE {role} NOLOGIN; END IF;
                END $r$""")
            # Tablas con nombres y columnas comerciales; sin datos reales.
            conn.execute("""CREATE TABLE public.suscripciones_tappad (
                id bigint primary key, cliente_id bigint not null,
                proveedor_cobro text, referencia_externa text, estado text not null)""")
            conn.execute("""CREATE TABLE public.pagos_tappad (
                id bigint primary key,
                suscripcion_id bigint not null references public.suscripciones_tappad(id),
                proveedor_cobro text, referencia_externa text, estado text not null,
                CONSTRAINT pagos_tappad_estado_check CHECK (
                  estado IN ('pendiente','pagado','fallido','reembolsado','cancelado')))""")
            conn.execute("""CREATE TABLE public.acceso_comercial_tappad (
                cliente_id bigint primary key, suscripcion_id bigint,
                estado text not null, vigente_hasta timestamptz,
                actualizado_en timestamptz not null)""")
            conn.execute("""CREATE TABLE public.activaciones_comerciales_tappad (
                id bigint primary key, cliente_id bigint not null,
                suscripcion_id bigint not null, pago_id bigint not null,
                estado text not null, periodo_inicio timestamptz,
                periodo_fin timestamptz)""")
            for table in ("suscripciones_tappad", "pagos_tappad",
                          "acceso_comercial_tappad", "activaciones_comerciales_tappad"):
                conn.execute("ALTER TABLE public." + table + " ENABLE ROW LEVEL SECURITY")
            conn.execute((ROOT / "docs/sql_conciliacion_reversion_mercadopago_borrador.sql")
                         .read_text(encoding="utf-8"))
            conn.commit()
            conn.execute((ROOT / "docs/sql_preparacion_reversion_privada_NO_APLICAR.sql")
                         .read_text(encoding="utf-8"))
            definition = conn.execute("""SELECT pg_get_constraintdef(oid)
                FROM pg_constraint WHERE conrelid='public.pagos_tappad'::regclass
                  AND conname='pagos_tappad_estado_check'""").fetchone()[0]
            self.assertIn("contracargo", definition)
            role = conn.execute("""SELECT rolcanlogin,rolbypassrls
                FROM pg_roles WHERE rolname='tappad_reversion_privada'""").fetchone()
            self.assertEqual(role, (False, False))
            signature = "tappad_internal.conciliar_reversion_pago(bigint,bigint,text,jsonb)"
            for role_name in ("anon", "authenticated"):
                self.assertFalse(conn.execute(
                    "SELECT has_function_privilege(%s,%s,'EXECUTE')",
                    (role_name, signature)).fetchone()[0])
            self.assertTrue(conn.execute(
                "SELECT has_function_privilege('tappad_reversion_privada',%s,'EXECUTE')",
                (signature,)).fetchone()[0])
            self.assertTrue(conn.execute("""SELECT relrowsecurity
                FROM pg_class WHERE oid='tappad_internal.auditoria_estados_mercadopago'::regclass""").fetchone()[0])
            self.assertFalse(conn.execute("""SELECT has_column_privilege(
                'tappad_reversion_privada','public.pagos_tappad','referencia_externa','UPDATE')""").fetchone()[0])


if __name__ == "__main__":
    unittest.main()
