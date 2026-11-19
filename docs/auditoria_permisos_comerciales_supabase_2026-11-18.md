# Auditoría de permisos comerciales — 18 noviembre 2026

**Estado:** solo lectura de Supabase productivo. No desplegar ni habilitar reversiones todavía.

## Evidencia verificada en Supabase
- RLS habilitado en public.pagos_tappad, public.suscripciones_tappad,
  public.acceso_comercial_tappad y public.activaciones_comerciales_tappad.
- anon y authenticated sin UPDATE sobre pagos ni acceso; sin USAGE en
  tappad_internal.
- service_role posee BYPASSRLS y UPDATE en pagos, pero no UPDATE en acceso
  comercial (según privilegios efectivos consultados).
- tappad_activador_privado es NOLOGIN, sin SUPERUSER ni BYPASSRLS;
  tiene USAGE en tappad_internal, pero no UPDATE directo en pagos ni acceso.
- La función existente tappad_internal.tappad_aplicar_activacion_comercial
  es SECURITY DEFINER, con search_path vacío y EXECUTE limitado a postgres
  y tappad_activador_privado. Su código comprueba referencias de pago,
  suscripción, periodo, plan y estado, pero acepta evidencia JSON del llamador:
  el origen confiable depende totalmente del worker privado.
- La función tappad_internal.conciliar_reversion_pago todavía **no existe**
  en producción. No se han aplicado los borradores SQL.
- El advisor de seguridad reportó 13 tablas RLS sin políticas (INFO) y
  protección contra contraseñas filtradas deshabilitada (WARN). Las tablas
  sin políticas no equivalen automáticamente a acceso público; revisar
  según necesidades de lectura.

## Bloqueantes de despliegue
1. Aprobar un rol ejecutor dedicado con LOGIN solo en infraestructura privada,
   sin BYPASSRLS ni acceso de frontend; documentar credenciales/rotación.
2. Definir políticas RLS y GRANT mínimos para que SECURITY INVOKER pueda
   bloquear suscripciones y pagos, escribir auditoría y suspender acceso.
   Probar exactamente con el rol real en una copia aislada, sin modificar producción.
3. Revisar dependencia de SECURITY DEFINER de activación; no conceder EXECUTE
   a usuarios públicos ni aceptar evidencia arbitraria de clientes.
4. Confirmar que el worker de reversiones no queda expuesto por HTTP,
   webhook ni credenciales de servicio del navegador.
5. Revisar concurrencia entre activación y reversión con locks consistentes.
6. Ejecutar una sola prueba integral de punta a punta y obtener autorización
   expresa antes de aplicar cambios productivos.

Referencia de seguridad Supabase:
https://supabase.com/docs/guides/database/database-linter?lint=0008_rls_enabled_no_policy
https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection
