-- BORRADOR NO APLICADO. Ejecutar solo tras auditoria de seguridad y aprobacion.
-- Conciliacion privada de reembolso/contracargo: transaccion atomica e idempotente.
-- El caller privado debe verificar en Mercado Pago identidad, vendedor, estado
-- remoto y vinculo pago/suscripcion inmediatamente antes de invocar.
-- No es un endpoint de webhook ni un RPC del esquema public.

create schema if not exists tappad_internal;

create table if not exists tappad_internal.auditoria_estados_mercadopago (
  id bigint generated always as identity primary key,
  pago_id bigint not null references public.pagos_tappad(id),
  suscripcion_id bigint not null references public.suscripciones_tappad(id),
  estado_anterior text not null,
  estado_nuevo text not null,
  motivo text not null check (motivo in ('refunded','charged_back')),
  evidencia jsonb not null,
  registrado_en timestamptz not null default transaction_timestamp(),
  unique (pago_id, estado_nuevo)
);

revoke all on schema tappad_internal from public, anon, authenticated;
revoke all on tappad_internal.auditoria_estados_mercadopago from public, anon, authenticated;

create or replace function tappad_internal.conciliar_reversion_pago(
  p_pago_id bigint,
  p_suscripcion_id bigint,
  p_estado_remoto text,
  p_evidencia jsonb
) returns boolean
language plpgsql
security invoker
set search_path = pg_catalog
as $$
declare
  v_pago public.pagos_tappad%rowtype;
  v_sub public.suscripciones_tappad%rowtype;
  v_estado text;
  v_cliente bigint;
  v_acceso public.acceso_comercial_tappad%rowtype;
  v_activaciones_actuales bigint;
begin
  if p_estado_remoto is null
     or p_estado_remoto not in ('refunded','charged_back')
     or p_evidencia is null
     or jsonb_typeof(p_evidencia) <> 'object'
     or p_evidencia->>'origen' <> 'consulta_directa_mercadopago'
     or nullif(btrim(p_evidencia->>'payment_id'),'') is null
     or nullif(btrim(p_evidencia->>'preapproval_id'),'') is null
     or nullif(btrim(p_evidencia->>'seller_id'),'') is null then
    raise exception 'evidencia_de_reversion_invalida';
  end if;
  select * into strict v_sub from public.suscripciones_tappad
    where id=p_suscripcion_id for update;
  select * into strict v_pago from public.pagos_tappad
    where id=p_pago_id and suscripcion_id=p_suscripcion_id for update;
  if v_sub.proveedor_cobro <> 'mercadopago_produccion'
     or v_pago.proveedor_cobro <> 'mercadopago_produccion'
     or v_pago.referencia_externa is distinct from p_evidencia->>'payment_id'
     or v_sub.referencia_externa is distinct from p_evidencia->>'preapproval_id'
     or v_pago.estado not in ('pagado','reembolsado','contracargo') then
    raise exception 'relacion_comercial_invalida';
  end if;
  -- La prueba de seller_id contra el token del vendedor ocurre en el worker
  -- privado, nunca se acepta seller_id del navegador o del webhook.
  v_estado := case p_estado_remoto when 'refunded' then 'reembolsado'
                                 else 'contracargo' end;
  if v_pago.estado in ('reembolsado','contracargo') then
    if v_pago.estado <> v_estado then
      raise exception 'transicion_conflictiva';
    end if;
    return false;
  end if;
  update public.pagos_tappad set estado=v_estado where id=p_pago_id;
  insert into tappad_internal.auditoria_estados_mercadopago
    (pago_id,suscripcion_id,estado_anterior,estado_nuevo,motivo,evidencia)
  values (p_pago_id,p_suscripcion_id,v_pago.estado,v_estado,p_estado_remoto,p_evidencia);
  -- Suspender solamente si el acceso actual se sustenta en ESTE pago.
  -- No invalidar automaticamente periodos posteriores respaldados por otro cobro.
  select s.cliente_id into v_cliente from public.suscripciones_tappad s
    where s.id=p_suscripcion_id;
  -- Serializar el acceso con otras operaciones concurrentes.
  select * into v_acceso from public.acceso_comercial_tappad a
    where a.cliente_id=v_cliente and a.suscripcion_id=p_suscripcion_id
    for update;
  if found and v_acceso.estado='habilitado' then
    select count(*) into v_activaciones_actuales
      from public.activaciones_comerciales_tappad x
     where x.cliente_id=v_cliente and x.suscripcion_id=p_suscripcion_id
       and x.estado='aplicada'
       and x.periodo_fin=v_acceso.vigente_hasta;
    if v_activaciones_actuales=1 and exists (
      select 1 from public.activaciones_comerciales_tappad x
       where x.pago_id=p_pago_id and x.cliente_id=v_cliente
         and x.suscripcion_id=p_suscripcion_id and x.estado='aplicada'
         and x.periodo_fin=v_acceso.vigente_hasta
         and x.periodo_inicio<=transaction_timestamp()
         and x.periodo_fin>transaction_timestamp()
    ) then
      update public.acceso_comercial_tappad
         set estado='suspendido', actualizado_en=transaction_timestamp()
       where cliente_id=v_cliente and suscripcion_id=p_suscripcion_id
         and estado='habilitado';
    end if;
  end if;
  return true;
end;
$$;

revoke all on function tappad_internal.conciliar_reversion_pago(bigint,bigint,text,jsonb)
  from public, anon, authenticated;
-- Pendiente: GRANT EXECUTE exclusivamente al rol privado con LOGIN y permisos
-- minimos de SELECT/UPDATE/INSERT sobre las tablas requeridas. No habilitar
-- sin revisar concurrencia, evidencia, seller_id, RLS y casos de pagos multiples.
