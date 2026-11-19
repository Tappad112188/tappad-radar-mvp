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
            # Entidades padre ficticias para reproducir FKs productivas.
            conn.execute("CREATE TABLE public.clientes (id bigint primary key)")
            conn.execute("CREATE TABLE public.planes_tappad (id bigint primary key)")
            conn.execute("INSERT INTO public.clientes (id) VALUES (700)")
            conn.execute("INSERT INTO public.planes_tappad (id) VALUES (1)")
            # Tablas con nombres y columnas comerciales; sin datos reales.
            conn.execute("""CREATE TABLE public.suscripciones_tappad (
                id bigint primary key, cliente_id bigint not null references public.clientes(id) ON DELETE RESTRICT,
                plan_id bigint not null default 1 references public.planes_tappad(id) ON DELETE RESTRICT,
                proveedor_cobro text, referencia_externa text, estado text not null,
                CONSTRAINT suscripciones_tappad_estado_check CHECK
                (estado IN ('pendiente','prueba','activa','vencida','cancelada','suspendida')))""")
            conn.execute("""CREATE TABLE public.pagos_tappad (
                id bigint primary key,
                suscripcion_id bigint not null references public.suscripciones_tappad(id) ON DELETE RESTRICT,
                proveedor_cobro text, referencia_externa text, estado text not null,
                monto_mxn numeric not null default 0 CHECK (monto_mxn >= 0),
                fecha_pago timestamptz, creado_en timestamptz not null default now(),
                UNIQUE (proveedor_cobro,referencia_externa),
                CONSTRAINT pagos_tappad_estado_check CHECK (
                  estado IN ('pendiente','pagado','fallido','reembolsado','cancelado')))""")
            conn.execute("""CREATE TABLE public.acceso_comercial_tappad (
                cliente_id bigint primary key references public.clientes(id),
                suscripcion_id bigint references public.suscripciones_tappad(id),
                estado text not null, vigente_hasta timestamptz,
                origen text not null default 'evaluacion_manual',
                habilitado_desde timestamptz,
                actualizado_en timestamptz not null,
                CONSTRAINT acceso_comercial_tappad_estado_check CHECK
                (estado IN ('sin_verificar','habilitado','suspendido','prueba')),
                CONSTRAINT acceso_comercial_no_habilitar_prueba CHECK
                (estado <> 'habilitado' OR
                (habilitado_desde IS NOT NULL AND vigente_hasta IS NOT NULL)))""")
            conn.execute("""CREATE TABLE public.activaciones_comerciales_tappad (
                id bigint primary key, cliente_id bigint not null references public.clientes(id),
                suscripcion_id bigint not null references public.suscripciones_tappad(id),
                pago_id bigint not null references public.pagos_tappad(id),
                estado text not null, periodo_inicio timestamptz not null,
                periodo_fin timestamptz not null,
                evidencia_proveedor jsonb not null default '{}'::jsonb,
                UNIQUE(pago_id),
                CONSTRAINT activaciones_periodo_valido CHECK(periodo_fin > periodo_inicio),
                CONSTRAINT activaciones_comerciales_tappad_estado_check CHECK
                (estado IN ('pendiente_revision','aplicada','rechazada')))""")
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


            # Ejecutar la funcion con los privilegios reales del rol privado,
            # no como postgres (que omite RLS).
            conn.execute("""INSERT INTO public.suscripciones_tappad
                (id,cliente_id,proveedor_cobro,referencia_externa,estado)
                VALUES (700,700,'mercadopago_produccion','sub-ci-700','activa')""")
            conn.execute("""INSERT INTO public.pagos_tappad
                (id,suscripcion_id,proveedor_cobro,referencia_externa,estado)
                VALUES (700,700,'mercadopago_produccion','pay-ci-700','pagado')""")
            conn.execute("""INSERT INTO public.acceso_comercial_tappad
                (cliente_id,suscripcion_id,estado,vigente_hasta,actualizado_en,habilitado_desde)
                VALUES (700,700,'habilitado',now()+interval '30 days',now(),now()-interval '1 day')""")
            conn.execute("""INSERT INTO public.activaciones_comerciales_tappad
                (id,cliente_id,suscripcion_id,pago_id,estado,periodo_inicio,periodo_fin)
                SELECT 700,700,700,700,'aplicada',now()-interval '1 day',
                       vigente_hasta FROM public.acceso_comercial_tappad
                WHERE cliente_id=700""")
            evidence = '{"origen":"consulta_directa_mercadopago","payment_id":"pay-ci-700","preapproval_id":"sub-ci-700","seller_id":"seller-ci"}'
            conn.execute("SET ROLE tappad_reversion_privada")
            first = conn.execute("""SELECT tappad_internal.conciliar_reversion_pago(
                700,700,'refunded',%s::jsonb)""", (evidence,)).fetchone()[0]
            second = conn.execute("""SELECT tappad_internal.conciliar_reversion_pago(
                700,700,'refunded',%s::jsonb)""", (evidence,)).fetchone()[0]
            self.assertTrue(first)
            self.assertFalse(second)
            conn.execute("RESET ROLE")
            self.assertEqual(conn.execute(
                "SELECT estado FROM public.pagos_tappad WHERE id=700").fetchone()[0],
                "reembolsado")
            self.assertEqual(conn.execute(
                "SELECT estado FROM public.acceso_comercial_tappad WHERE cliente_id=700").fetchone()[0],
                "suspendido")
            self.assertEqual(conn.execute("""SELECT count(*) FROM
                tappad_internal.auditoria_estados_mercadopago WHERE pago_id=700""").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
