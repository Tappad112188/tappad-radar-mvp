/**
 * TAPPAD Radar: selector de giros SAT/CUCOP + captura manual.
 * Requiere un cliente Supabase autenticado (anon/publishable key, NUNCA service_role).
 * Las políticas RLS restringen las preferencias al cliente propietario.
 */
export function crearServicioGiros(supabase, clienteId) {
  if (!supabase || !Number.isSafeInteger(Number(clienteId)) || Number(clienteId) <= 0) {
    throw new Error("Cliente y sesión Supabase requeridos");
  }
  const id = Number(clienteId);
  const normalizar = s => String(s ?? "").trim();
  const validarTexto = s => {
    const t = normalizar(s);
    if (t.length < 3 || t.length > 300) throw new Error("El giro debe tener entre 3 y 300 caracteres");
    return t;
  };
  async function buscar(consulta, { limite = 30, sistema = null } = {}) {
    const q = normalizar(consulta);
    if (q.length < 2) return [];
    if (!Number.isInteger(limite) || limite < 1 || limite > 100) throw new Error("Límite inválido");
    // Escapar comodines de PostgREST para evitar filtros inesperados.
    const seguro = q.replace(/[%,()]/g, " ").trim();
    if (seguro.length < 2) return [];
    let query = supabase.from("catalogos_oficiales_tappad")
      .select("sistema,clave,descripcion,version")
      .in("sistema", ["SAT", "CUCOP"])
      .ilike("descripcion", `%${seguro}%`)
      .order("descripcion", { ascending: true }).limit(limite);
    if (sistema) {
      if (!["SAT", "CUCOP"].includes(sistema)) throw new Error("Sistema inválido");
      query = query.eq("sistema", sistema);
    }
    const { data, error } = await query;
    if (error) throw error;
    return data ?? [];
  }
  async function seleccionados() {
    const { data, error } = await supabase.from("clientes_giros_preferencias_tappad")
      .select("id,origen,clave,version,descripcion,activo")
      .eq("cliente_id", id).eq("activo", true).order("creado_en", { ascending: false });
    if (error) throw error;
    return data ?? [];
  }
  async function agregarCatalogo(item) {
    if (!["SAT", "CUCOP"].includes(item.sistema)) throw new Error("Catálogo inválido");
    const clave = normalizar(item.clave), version = normalizar(item.version);
    if (!clave || !version) throw new Error("Clave y versión requeridas");
    // Releer el registro oficial: no confiar en una descripción manipulada por el navegador.
    const { data: registro, error: err } = await supabase.from("catalogos_oficiales_tappad")
      .select("descripcion").eq("sistema", item.sistema).eq("clave", clave)
      .eq("version", version).single();
    if (err) throw err;
    const { data, error } = await supabase.from("clientes_giros_preferencias_tappad")
      .insert({ cliente_id: id, origen: item.sistema, clave, version, descripcion: registro.descripcion })
      .select("id").single();
    if (error) throw error;
    return data;
  }
  async function agregarManual(descripcion) {
    const { data, error } = await supabase.from("clientes_giros_preferencias_tappad")
      .insert({ cliente_id: id, origen: "MANUAL", clave: null, version: null, descripcion: validarTexto(descripcion) })
      .select("id").single();
    if (error) throw error;
    return data;
  }
  async function quitar(preferenciaId) {
    const { error } = await supabase.from("clientes_giros_preferencias_tappad")
      .update({ activo: false }).eq("cliente_id", id).eq("id", preferenciaId);
    if (error) throw error;
  }
  return { buscar, seleccionados, agregarCatalogo, agregarManual, quitar };
}
