import os, unittest, json, threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import psycopg

DSN=os.getenv("TAPPAD_TEST_POSTGRES_DSN")
ROOT=Path(__file__).resolve().parents[1]/"docs"

@unittest.skipUnless(DSN,"PostgreSQL aislado requerido")
class ConcurrenciaPiloto(unittest.TestCase):
    def test_registro_y_activacion_simultaneos(self):
        with psycopg.connect(DSN) as c:
            self.assertEqual(c.execute("select current_database()").fetchone()[0],"tappad_ci_pruebas")
            for role in ("anon","authenticated","service_role","tappad_activador_privado","tappad_login_activacion"):
                c.execute("DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname='"+role+"') THEN CREATE ROLE "+role+" NOLOGIN; END IF; END $$")
            c.execute("GRANT tappad_activador_privado TO tappad_login_activacion")
            c.execute("""CREATE SCHEMA tappad_internal;
            CREATE TABLE public.planes_tappad(id bigint primary key, activo boolean, periodicidad text, precio_mxn numeric);
            CREATE TABLE public.suscripciones_tappad(id bigint primary key, cliente_id bigint, plan_id bigint, proveedor_cobro text, referencia_externa text, estado text, fin_periodo timestamptz, actualizado_en timestamptz);
            CREATE TABLE public.pagos_tappad(id bigint generated always as identity primary key, suscripcion_id bigint, proveedor_cobro text, referencia_externa text, estado text, monto_mxn numeric, fecha_pago timestamptz, unique(proveedor_cobro,referencia_externa));
            CREATE TABLE public.acceso_comercial_tappad(cliente_id bigint primary key, suscripcion_id bigint, estado text, origen text, habilitado_desde timestamptz, vigente_hasta timestamptz, ultima_verificacion timestamptz, actualizado_en timestamptz);
            CREATE TABLE public.activaciones_comerciales_tappad(id bigint generated always as identity primary key, cliente_id bigint, suscripcion_id bigint, pago_id bigint unique, periodo_inicio timestamptz, periodo_fin timestamptz, estado text, evidencia_proveedor jsonb);
            INSERT INTO public.planes_tappad VALUES(1,false,'mensual',449);
            INSERT INTO public.suscripciones_tappad VALUES(5,4,1,'mercadopago_produccion','dbc554730f1141a48cf73881a4e9eb96','pendiente',null,null);""")
            for table in ("planes","suscripciones","pagos","acceso_comercial","activaciones_comerciales"):
                name=table+"_tappad"
                c.execute("ALTER TABLE public."+name+" ENABLE ROW LEVEL SECURITY")
                if table!="activaciones_comerciales":
                    c.execute("GRANT SELECT ON public."+name+" TO tappad_activador_privado")
                    c.execute("CREATE POLICY lectura ON public."+name+" FOR SELECT TO tappad_activador_privado USING (true)")
            c.execute((ROOT/"sql_migracion_activacion_invoker_PENDIENTE_VALIDACION.sql").read_text())
            c.execute((ROOT/"sql_activacion_exclusiva_piloto.sql").read_text())
            c.commit()
            c.execute((ROOT/"sql_registro_pago_piloto.sql").read_text())
            c.execute("ALTER TABLE public.pagos_tappad ADD CONSTRAINT pagos_tappad_estado_check CHECK (estado IN ('pendiente','pagado','fallido','reembolsado','cancelado'))")
            c.execute((ROOT/"sql_conciliacion_reversion_mercadopago_borrador.sql").read_text())
            c.commit()
            c.execute((ROOT/"sql_preparacion_reversion_privada_NO_APLICAR.sql").read_text())
            fecha,fin=c.execute("SELECT now()-interval '1 minute',now()-interval '1 minute'+interval '1 month'").fetchone()
        def carrera(fn):
            barrier=threading.Barrier(2)
            def worker():
                with psycopg.connect(DSN) as c:
                    c.execute("SET SESSION AUTHORIZATION tappad_login_activacion")
                    c.execute("SET LOCAL ROLE tappad_activador_privado")
                    c.execute("SET LOCAL statement_timeout='10s'")
                    barrier.wait(timeout=10)
                    return fn(c)
            with ThreadPoolExecutor(max_workers=2) as pool:
                fs=[pool.submit(worker) for _ in range(2)]
                return [f.result(timeout=20) for f in fs]
        ids=carrera(lambda c:c.execute("SELECT tappad_internal.registrar_pago_piloto(%s,%s)",("123456789",fecha)).fetchone()[0])
        self.assertEqual(ids[0],ids[1])
        ev=json.dumps(dict(verificacion_remota="confirmada",entorno="produccion",seller_id="11",payment_id="123456789",preapproval_id="dbc554730f1141a48cf73881a4e9eb96"))
        results=carrera(lambda c:c.execute("SELECT tappad_internal.tappad_aplicar_activacion_comercial(4,5,%s,%s,%s,%s::jsonb)",(ids[0],fecha,fin,ev)).fetchone()[0])
        self.assertEqual(sorted(results),[False,True])
        with psycopg.connect(DSN) as c:
            self.assertEqual(c.execute("SELECT count(*) FROM public.pagos_tappad").fetchone()[0],1)
            self.assertEqual(c.execute("SELECT count(*) FROM public.activaciones_comerciales_tappad").fetchone()[0],1)
            self.assertEqual(c.execute("SELECT estado,vigente_hasta FROM public.acceso_comercial_tappad WHERE cliente_id=4").fetchone(),("habilitado",fin))

        # Ejecutar las funciones reales bajo roles privados distintos.
        # Forzar ambos ordenes de adquisicion del lock de suscripcion.
        for remoto,estado in (("refunded","reembolsado"),("charged_back","contracargo")):
            for primero in ("activacion","reversion"):
                with self.subTest(remoto=remoto,primero=primero):
                    with psycopg.connect(DSN) as c:
                        c.execute("DELETE FROM tappad_internal.auditoria_estados_mercadopago")
                        c.execute("DELETE FROM public.activaciones_comerciales_tappad")
                        c.execute("DELETE FROM public.acceso_comercial_tappad")
                        c.execute("UPDATE public.suscripciones_tappad SET estado='pendiente',fin_periodo=NULL WHERE id=5")
                        c.execute("UPDATE public.pagos_tappad SET estado='pagado' WHERE id=%s",(ids[0],))
                    locked=threading.Event()
                    ready=threading.Event()
                    def ejecutar(tipo):
                        with psycopg.connect(DSN) as c:
                            rol="tappad_activador_privado" if tipo=="activacion" else "tappad_reversion_privada"
                            c.execute("SET LOCAL ROLE "+rol)
                            c.execute("SET LOCAL statement_timeout='10s'")
                            if tipo==primero:
                                c.execute("SELECT id FROM public.suscripciones_tappad WHERE id=5 FOR UPDATE")
                                locked.set()
                                if not ready.wait(5): raise RuntimeError("segundo worker ausente")
                            else:
                                if not locked.wait(5): raise RuntimeError("primer lock ausente")
                                ready.set()
                            if tipo=="activacion":
                                return c.execute("SELECT tappad_internal.tappad_aplicar_activacion_comercial(4,5,%s,%s,%s,%s::jsonb)",(ids[0],fecha,fin,ev)).fetchone()[0]
                            evidencia=json.loads(ev)
                            evidencia["origen"]="consulta_directa_mercadopago"
                            return c.execute("SELECT tappad_internal.conciliar_reversion_pago(%s,5,%s,%s::jsonb)",(ids[0],remoto,json.dumps(evidencia))).fetchone()[0]
                    with ThreadPoolExecutor(max_workers=2) as pool:
                        a=pool.submit(ejecutar,"activacion")
                        b=pool.submit(ejecutar,"reversion")
                        self.assertEqual(a.result(timeout=20),primero=="activacion")
                        self.assertTrue(b.result(timeout=20))
                    with psycopg.connect(DSN) as c:
                        self.assertEqual(c.execute("SELECT estado FROM public.pagos_tappad WHERE id=%s",(ids[0],)).fetchone()[0],estado)
                        self.assertEqual(c.execute("SELECT count(*) FROM tappad_internal.auditoria_estados_mercadopago").fetchone()[0],1)
                        self.assertEqual(c.execute("SELECT count(*) FROM public.acceso_comercial_tappad WHERE estado='habilitado'").fetchone()[0],0)
                        self.assertEqual(c.execute("SELECT count(*) FROM public.activaciones_comerciales_tappad").fetchone()[0],int(primero=="activacion"))
