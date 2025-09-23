# Bloque-A-Cart-Pricing-Checkout.pdf

> Documento convertido automáticamente de PDF a Markdown
> Archivo original: Bloque-A-Cart-Pricing-Checkout.pdf
> Método de extracción: pdfplumber

---


## Página 1

Bloque A — Cart + Pricing + Checkout
1) Objetivo
Dejar operativo el carrito con precios y checkout mínimo POS: agregar/editar/borrar ítems,
recalcular totales con pricing y confirmar venta vía API.
2) Alcance / Fuera de alcance
Incluye: CartStore, integración con /catalog/pricing, POST /pos/sale, toasts/errores base.
No incluye: métodos de pago avanzados, impresión, modo offline completo.
3) Pre-requisitos
Branch: feat/cart-pricing-checkout
ENV: VITE_API_BASE=https://…/api
Flags (opcional): FEATURE_PRICING_ENGINE=true
4) APIs (método, ruta, auth, ejemplos)
A. Pricing
POST /catalog/pricing (Auth: Bearer, rol: vendedor)
Request:
{
"items":[{"product_id":101,"qty":2},{"product_id":202,"qty":1}],
"segment":"POS"
}
Response:
{
"items":[
{"product_id":101,"qty":2,"unit_price":120.00,"discount":10.00,"total":230.00},
{"product_id":202,"qty":1,"unit_price":80.00,"discount":0,"total":80.00}
],
"subtotal":310.00,
"discounts_total":10.00,
"total":300.00
}
Errores esperados: 400 input inválido, 401 auth, 409 sin stock (si valida stock aquí).
B. POS Sale
POST /pos/sale (Auth: Bearer, rol: vendedor)
Request:
{
"customer_id": null,
"items":[
{"product_id":101,"qty":2,"unit_price":120.00},
{"product_id":202,"qty":1,"unit_price":80.00}
],
"payments":[{"method":"cash","amount":300.00}],
"notes":""
}
Response:
{
"sale_id":"d9a…",
"number":"POS-000123",
"total":300.00,

## Página 2

"change":0.00,
"created_at":"2025-09-23T12:34:56Z"
}
Errores esperados: 409 sin stock, 422 validación, 500 genérico.
5) Tipos/Interfaces (FE) — TS
CartItem: { product_id:number; name:string; unit_price:number; qty:number; discount?:number;
total?:number; }
PricingRequest: { items:{product_id:number; qty:number;}[]; segment?:string; }
PricingItem: { product_id:number; qty:number; unit_price:number; discount:number; total:number; }
PricingResponse: { items:PricingItem[]; subtotal:number; discounts_total:number; total:number; }
SalePayment: { method:'cash'|'card'|'account'; amount:number; }
SaleRequest: { customer_id:number|null; items:CartItem[]; payments:SalePayment[]; notes?:string; }
SaleResponse: { sale_id:string; number:string; total:number; change:number; created_at:string; }
6) UI y Rutas
POSView.vue: SearchBar (ya existe), CartPanel (nuevo), SummaryCard (nuevo), botón Confirmar.
SalesDetail.vue: mostrará número de venta (impresión se suma en otro bloque).
7) Estado/Stores
cart.ts (Pinia):
state { items: CartItem[] }
getters { subtotal, discounts, total }
actions { add, updateQty, remove, clear, reprice }
Persistencia: localStorage.
8) Reglas de negocio
Sin stock negativo (manejar 409).
FEFO lo resuelve backend; si llega metadato, mostrar aviso informativo.
Checkout atómico: si falla, NO vaciar carrito.
9) Edge cases & errores
409 stock: toast “Sin stock disponible” y bloquear confirmación.
401: redirigir a login.
Timeout/500 en pricing: mantener último pricing válido y avisar “No se actualizó precios”.
10) Tareas (todas ≤2 h, con DoD y tests)
T1 — CartStore (≤2 h)
DoD: CRUD ítems; totales correctos; persistencia; sin warnings en consola.
Tests: add/update/remove; reload conserva carrito; totales correctos.
T2 — CartPanel (≤2 h)
DoD: lista ítems; +/- qty; borrar; subtotales en vivo.
Tests: cambiar qty recalcula; borrar actualiza total.
T3 — Integración Pricing (≤2 h)
DoD: cart.reprice() llama /catalog/pricing; refleja descuentos/total; manejo de errores con
toast.
Tests: caso sin descuentos vs. con combo; 400/500 muestran toast.
T4 — Summary + Confirmar (≤2 h)
DoD: muestra subtotal/desc/total; botón deshabilitado si carrito vacío; spinner en acción.
Tests: total 0 deshabilita; total >0 habilita; loader visible durante submit.

## Página 3

T5 — Checkout (≤2 h)
DoD: POST /pos/sale; éxito → muestra número y vacía carrito; errores 409/422/500 mantienen
carrito y muestran toast.
Tests: éxito vacía; 409 mantiene; evitar doble submit.
T6 — Errores/Toasts/Loaders (≤2 h)
DoD: interceptor muestra 401/500; botones con estado loading; toasts consistentes.
Tests: forzar 500 → toast; no hay doble acción durante loading.
11) QA rápido (manual)
1. Login.
2. Buscar A y B.
3. Agregar A×2, B×1.
4. Ver subtotal.
5. Reprice → total cambia (descuento simulado).
6. Confirmar → sale OK, número visible, carrito vacío.
7. Repetir forzando 409 → toast y carrito intacto.
12) Telemetría y logs
Incluir X-Request-ID si está disponible.
Log de acciones: add_to_cart, pricing_applied, checkout_ok|fail.
13) Entregables
PR: feat/cart-pricing-checkout.
2 screenshots (Carrito/Summary, Confirmación OK).
Video 30–60s mostrando el flujo.
14) Prompts IA útiles
Store: Crea un Pinia store cart (TS) con estado/getters/actions, persistencia localStorage y
tests Vitest para add/update/remove.
Pricing: Hook usePricing que reciba CartItem[], llame /catalog/pricing y aplique respuesta al
store con manejo de 400/500.
Checkout: Función checkout(cart, payments) que haga POST /pos/sale, maneje 409/422/500, evite
doble submit y devuelva SaleResponse.
15) Checklist de PR
[ ] Build OK / Lint OK
[ ] Tests del store (add/update/remove/reprice)
[ ] Manejo de 409 probado
[ ] ENV documentado en README
[ ] Video + screenshots adjuntos
O11CE — Bloque A (Cart + Pricing + Checkout)

