export function buildCheckout(plan: { precio_mxn: number; periodicidad: string }, email: string, reference: string) {
  const monthly = plan.periodicidad === "mensual" && Number(plan.precio_mxn) === 449;
  const annual = plan.periodicidad === "anual" && Number(plan.precio_mxn) === 4490;
  if (!monthly && !annual) throw new Error("invalid_plan");
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) throw new Error("invalid_email");
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(reference)) throw new Error("invalid_reference");
  return {reason: monthly ? "TAPPAD Radar mensual" : "TAPPAD Radar anual", external_reference: reference, payer_email: email, auto_recurring: {frequency: monthly ? 1 : 12, frequency_type: "months", transaction_amount: monthly ? 449 : 4490, currency_id: "MXN"}, back_url: "https://tappad112188.github.io/tappad-radar-mvp/", status: "pending"};
}
export function verifyCheckout(remote: any, expected: ReturnType<typeof buildCheckout>, seller: string) {
  const a = remote?.auto_recurring;
  if (!/^[a-zA-Z0-9_-]{1,128}$/.test(remote?.id ?? "") || remote.status !== "pending" || String(remote.collector_id) !== seller || remote.external_reference !== expected.external_reference || !a || Number(a.transaction_amount) !== expected.auto_recurring.transaction_amount || a.currency_id !== "MXN" || a.frequency_type !== "months" || Number(a.frequency) !== expected.auto_recurring.frequency) throw new Error("remote_mismatch");
  const url = new URL(remote.init_point);
  if (url.protocol !== "https:" || !["www.mercadopago.com.mx", "mercadopago.com.mx"].includes(url.hostname) || url.username || url.password || url.port || url.pathname !== "/subscriptions/checkout" || url.searchParams.get("preapproval_id") !== remote.id) throw new Error("invalid_checkout_url");
  return {id: remote.id as string, checkout_url: url.href};
}
