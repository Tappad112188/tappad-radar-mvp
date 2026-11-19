# TAPPAD Radar — acta de pre-cierre comercial Mercado Pago
Fecha: 2026-11-18. Rama: desarrollo-registro-proveedores.
**Estado: IMPLEMENTACION DE DESARROLLO; PRODUCCION NO AUTORIZADA.**

## Trabajo completado
1. Worker de reversiones con doble compuerta de activacion, API autenticada,
   transaccion PostgreSQL, rollback e idempotencia.
2. Pruebas PostgreSQL 17 aisladas y pruebas de roles NOLOGIN; pruebas
   de reembolsos, contracargos, duplicados y evidencia inconsistente.
3. Alineacion del orden de bloqueo de reversion con la activacion existente:
   suscripcion -> acceso -> pago; previene inversion evidente de locks.
4. Auditoria de solo lectura en Supabase: RLS, permisos, funcion productiva,
   columnas y constraints. Ningun cambio aplicado a produccion.
5. Preparacion de SQL de migracion para estado 'contracargo', rol de reversion
   NOLOGIN, GRANT y politicas RLS. Archivo NO_APLICAR, no ejecutado.
6. Compuerta estatica de lanzamiento en CI.

## Bloqueantes REALES descubiertos
- La restriccion productiva pagos_tappad_estado_check **NO admite
  'contracargo'**. La prueba en CI usa tablas simplificadas; no sustituye
  una copia fiel del esquema productivo. Requiere migracion revisada.
- La funcion de activacion productiva es SECURITY DEFINER (no INVOKER,
  como describe un documento antiguo). Depende del aislamiento del
  caller privado y no autentica criptograficamente la evidencia JSON.
- El rol tappad_activador_privado no puede iniciar sesion; el nuevo
  tappad_reversion_privada preparado tambien es NOLOGIN. Falta un
  ejecutor alojado con credenciales segregadas y TLS.
- Las politicas RLS y GRANT preparados NO se han probado en una copia
  fiel de Supabase con sus FK, constraints, indices y funciones.
- La integracion de la API Mercado Pago en pruebas es simulada; falta
  comprobacion end-to-end contra un cobro real autorizado, sin crear
  cargos no solicitados.
- Falta validacion de concurrencia simultanea entre activacion y
  reversion en dos conexiones PostgreSQL, con timeouts y reintentos.
- Renovaciones anticipadas siguen en pendiente hasta vencimiento:
  se requiere politica operativa de reintento, observabilidad y alertas.

## Orden de salida a produccion (una sola ventana, con autorizacion)
1. Crear copia fiel temporal de esquema productivo en entorno aislado.
2. Aplicar borrador de reversion y SQL de preparacion NO_APLICAR
   **solo en esa copia**; ejecutar tests de RLS, permisos, concurrencia,
   renovaciones y reversion; registrar resultados.
3. Configurar hosting privado y secretos: token vendedor Mercado Pago,
   seller_id, conexion PostgreSQL TLS, llave Supabase de solo lectura
   para discovery; restringir egress, logs sin secretos, alertas.
4. Revisar/autorizar SQL productivo y despliegue privado.
5. Ejecutar migracion controlada y verificacion posterior; iniciar en
   SOLO_LECTURA y verificar cobros reales existentes sin mutarlos.
6. Con aprobacion separada habilitar escritura, realizar una unica
   prueba integral supervisada, comprobar rollback y monitoreo.
7. Cerrar con acta de resultado, instrucciones de contingencia y
   desactivacion inmediata del worker.

## Intervencion que se requerira del propietario
- Aprobar explicitamente migracion SQL productiva y activacion de
  procesos que puedan suspender accesos comerciales.
- Elegir/autorizar entorno de ejecucion privado (hosting) y su costo.
- Configurar secretos de produccion directamente en gestor de secretos
  privado; NUNCA enviarlos por chat ni incluirlos en GitHub.
- Autorizar una prueba final controlada con pago real existente o
  sandbox; no efectuar un nuevo cargo sin consentimiento especifico.

## Archivos
- conciliar_reversion_privada_postgres.py
- docs/sql_conciliacion_reversion_mercadopago_borrador.sql
- docs/sql_preparacion_reversion_privada_NO_APLICAR.sql
- tests/test_integracion_reversion_postgres_real.py
- tests/test_gate_lanzamiento_comercial.py
- .github/workflows/integracion-postgres-comercial.yml
- .github/workflows/validacion-comercial.yml

## Alcance
Este cierre NO agrega seguimiento documental de licitaciones. La
suscripcion habilita solamente deteccion y alertas de ComprasMX/SECOP.
