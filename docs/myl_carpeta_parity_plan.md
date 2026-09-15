# Igualar la Carpeta de MYL a la de Riftbound

## Contexto

La Carpeta de **Riftbound** (`frontend/src/app/pages/riftbound/carpeta/riftbound-carpeta.component.ts`) pasó por un rediseño completo: grilla simplificada con quick-edit, navegación agrupada, gestión de pedidos unificada, stats con gráfico, roles de permisos, sistema de "Carpetas Compartidas", venta rápida desde el catálogo, modal de cancelación propio, notificaciones de pedidos, y una guía interactiva con tours tipo spotlight. La Carpeta de **MYL** (`frontend/src/app/pages/carpeta/carpeta.component.ts`) es una feature paralela y más antigua que nunca recibió ese trabajo — este documento es el mapa para llevarla al mismo nivel.

**Esto es un documento de planificación, no fue implementado.** Antes de ejecutar cualquier fase, hay decisiones de alcance (ver [Decisiones pendientes](#decisiones-pendientes)) que conviene resolver con el usuario, igual que se hizo para Riftbound.

## Estado actual: MYL vs Riftbound

| Aspecto | Riftbound (ya hecho) | MYL (estado actual) |
|---|---|---|
| Arquitectura del componente | Signals + `ChangeDetectionStrategy.OnPush` | **Sin signals, sin OnPush** — lifecycle hooks clásicos, propiedades planas (`carpeta.component.ts`, 1256 líneas + `.html` 1010 líneas + `.scss` 1860 líneas, en 3 archivos separados en vez de inline) |
| Paleta visual | Migrada a tokens `--ui-*` globales | **239 hex hardcodeados** vs. solo 17 usos de `var(--ui-*)` en el `.scss` |
| Tabs | Unificados: Carpeta, Colección, Wishlist, Mercado, **Gestión de Pedidos** (fusiona Pedidos+Historial), Stats, Permisos | `carpeta \| codex \| wishlist \| mercado \| pedidos \| historial \| stats` — **Pedidos e Historial ya están separados en el tipo `Tab`**, igual que Riftbound antes del rediseño |
| Grilla de cartas | Badges + modal "Quick Edit" al tocar la carta | Inputs inline expuestos directamente (el problema original que motivó el rediseño de Riftbound) |
| Navegación superior | 3 grupos con dropdown (Mi Colección / Mercado / Administración) + link "Carpetas Compartidas" | Tabs planos, sin agrupar |
| Cancelar pedido | Modal propio del sistema con campo de motivo | `confirm()` / `alert()` nativos del navegador (líneas 829, 837, 843, 851) |
| Notificaciones de pedidos | `Notification.objects.create(...)` en `riftbound/views.py` al crear/aceptar/cancelar, con links a la pantalla correcta | **No existen** — confirmado por grep, cero llamadas a `Notification.objects.create` en `backend/carpeta/views.py` |
| Colaboración / permisos | Modelo `RiftboundStorePermission` (10 flags granulares), roles predefinidos (Lector/Gestor de Mercado/Administrador), ruta `/riftbound/colaborar` | **No existe ningún modelo de permisos.** `backend/carpeta/models.py` solo tiene `BinderProfile, CollectionEntry, WishlistEntry, StoreOrder, StoreOrderItem`. La única noción "multiusuario" es el `share_token` de `BinderProfile` para ver la tienda/wishlist públicas en modo solo-lectura — no hay colaboradores con acceso de edición |
| Venta rápida desde catálogo | Botón "Vender" en Colección (agrega + marca en venta + abre quick-edit) | No existe |
| Stats | Donut SVG por rareza + widget de valor estimado (usa `stats.total_value` que el backend ya calculaba) | Falta confirmar si `carpeta/views.py` `collection_stats` ya devuelve `total_value`; si no, hay que agregarlo (ver Fase 6) |
| Guía interactiva / tours | `guide-modal` + `TourService` + `TourOverlayComponent` (genéricos, reutilizables) + modelo `RiftboundTourProgress` en backend | No existe ninguna guía. El `TourService`/`TourOverlayComponent` (`frontend/src/app/services/tour.service.ts`, `frontend/src/app/components/tour-overlay/tour-overlay.component.ts`) son genéricos y **no dependen de Riftbound** — se pueden reutilizar tal cual |
| "Mis pedidos" sin pestaña nueva | `target="_blank"` quitado en `riftbound-tienda.component.ts` | `tienda.component.html` (líneas 46 y 115) **todavía tiene `target="_blank"`** en ambos links a `/mis-compras` |
| Motivo de cancelación en historial | Se muestra en `mis-compras.component.ts` (`@if (order.status === 'cancelled' && order.seller_note)`) | **Ya funciona sin cambios**: `mis-compras.component.ts` es compartido por ambos juegos y el modelo `StoreOrder` de MYL ya tiene `seller_note` — solo falta que MYL efectivamente popule ese campo al cancelar (revisar `cancel_store_order` en `carpeta/views.py`) |

## Brecha arquitectónica clave (leer antes de empezar)

A diferencia de Riftbound —que ya usaba signals y OnPush desde antes del rediseño—, **MYL usa el patrón clásico de Angular** (propiedades + `ChangeDetectorRef` manual o CD por defecto, sin `OnPush`). Portar visualmente los patrones de Riftbound (quick-edit modal reactivo, pills, tours con `computed()`) funciona mejor sobre una base de signals. Hay dos caminos:

1. **Migrar `carpeta.component.ts` a signals + OnPush primero**, como fase 0, y luego aplicar el resto del plan sobre esa base (más trabajo inicial, pero consistente con el resto del código nuevo del proyecto y con `frontend/.claude/CLAUDE.md`).
2. **Portar la UI sin migrar el modelo de estado**, adaptando cada patrón a propiedades planas + `ChangeDetectorRef.markForCheck()` manual (como ya hace parte del código MYL). Menos reescritura, pero perpetúa el patrón antiguo y hace más difícil reusar código copiado directamente de Riftbound (que asume signals).

Recomendación: opción 1, migrar a signals primero, dado que ya es el estándar del proyecto (`frontend/.claude/CLAUDE.md` pide signals + OnPush) y porque casi todo el código a portar desde Riftbound está escrito en ese estilo — copiarlo tal cual es más simple si MYL ya usa signals.

## Plan de trabajo por fases

Mismo orden que se siguió en Riftbound; cada fase es independiente y verificable por separado.

### Fase 0 — Migración a signals + OnPush (prerrequisito, ver arriba)
Convertir las propiedades de estado de `carpeta.component.ts` a `signal()`, agregar `ChangeDetectionStrategy.OnPush`, reemplazar los `*ngIf`/`*ngFor` del `.html` por `@if`/`@for` nativos. Es refactor puro, sin cambios de comportamiento — verificar que cada tab siga funcionando igual antes de seguir.

### Fase 1 — Tokens de diseño
MYL ya tiene acceso a los mismos tokens `--ui-*` (son globales, en `frontend/src/styles.scss`). No hace falta un override de acento por juego como el de Riftbound (`.mode-riftbound`) a menos que MYL deba tener su propio color de marca — confirmar cuál es el acento de MYL en el sistema global (`--ui-accent` por defecto es ámbar/dorado, `#f59e0b`, según lo visto en `styles.scss`) y decidir si aplica tal cual o si MYL necesita su propio override como Riftbound.

### Fase 2 — Modal de guía + motor de tours
El `TourService` y `TourOverlayComponent` son genéricos y reutilizables sin cambios (`frontend/src/app/services/tour.service.ts`, `frontend/src/app/components/tour-overlay/tour-overlay.component.ts`). Falta:
- Un `guide-modal` propio para MYL (copiar `riftbound/carpeta/components/guide-modal/guide-modal.component.ts` y adaptar textos/tabs a los de MYL).
- Backend: replicar `RiftboundTourProgress` (modelo + migración) como algo genérico o como `TourProgress` en una app compartida — **no dupliques el modelo por juego**; mejor moverlo a una app común (p. ej. `users` o una nueva `tours`) con un campo `game` para diferenciar Riftbound/MYL, y actualizar `riftbound/views.py` para apuntar al modelo compartido. Si se prefiere no tocar Riftbound, la alternativa más simple (pero con deuda técnica) es crear `carpeta.models.CarpetaTourProgress` calcado del de Riftbound.
- Endpoint equivalente a `GET/POST /api/riftbound/tours/` bajo el namespace de `carpeta`.
- Definir los `data-tour` y `TOUR_STEPS` para las tabs de MYL (Carpeta, Colección, Wishlist, Mercado, Pedidos, Stats — sin Permisos, salvo que se construya la Fase 7 opcional).

### Fase 3 — Quick-edit panel
Mover los inputs inline de la grilla de "Carpeta" y "Mercado" a un modal por tarjeta (mismo patrón: badges de cantidad/en venta en la tarjeta, click abre el modal con Tengo/Precio/En venta/Idioma/Foil/Notas). Revisar primero el modelo `CollectionEntry` de MYL para confirmar que tiene los mismos campos que `RiftboundCollectionEntry` (`price`, `selling_quantity`, `is_foil`, `language`, `notes`, `photo_url`, `photo_url_2`) — si falta alguno, el quick-edit debe omitir ese campo en vez de asumirlo.

### Fase 4 — Navegación consolidada
Agrupar en 3 secciones: Mi Colección (Carpeta, Colección, Wishlist), Mercado, Administración (Pedidos, Stats — y Permisos si se hace la Fase 7). Mismo patrón de dropdown que Riftbound (`tab-group`/`tab-dropdown`, sin librería).

### Fase 5 — Unificar Pedidos + Historial
MYL **ya tiene la separación exacta** que Riftbound tenía antes de unificarse (`pedidos` e `historial` como tabs distintos en el mismo `type Tab`) — este es el port más mecánico de todos. Combinar en una sola tab "Gestión de Pedidos" con pills (Pendientes/Todos/Completados/Cancelados) y tabla compacta, reusando `loadPendingOrders()`/`loadHistoryOrders()` existentes tal como están.

### Fase 6 — Stats con donut + valor estimado
Antes de portar el frontend, verificar en `backend/carpeta/views.py` (`collection_stats`) si ya devuelve `total_value` como hace `riftbound/views.py:953`. Si no, agregarlo (`sum((e.price or 0) * e.quantity for e in entries)`). Reusar el mismo componente de donut SVG puro (o extraerlo a un componente compartido `app-rarity-donut` ya que la lógica es idéntica para ambos juegos — candidato para reducir duplicación en este porting).

### Fase 7 — Permisos y "Carpetas Compartidas" (OPCIONAL, mayor esfuerzo)
Esta es la única fase que **no es un port** sino una feature nueva para MYL: no existe ningún modelo de colaboradores. Si se decide construirla:
- Backend: nuevo modelo `MylStorePermission` (o generalizar `RiftboundStorePermission` a un modelo compartido con `game`/`content_type`) con los mismos ~10 flags granulares, migración, endpoints de workspaces/permisos calcados de `riftbound/views.py` (`riftbound_workspaces`, `riftbound_workspace_permissions`, etc.).
- Frontend: pantalla "Permisos" con roles predefinidos (mismo mapeo Lector/Gestor de Mercado/Administrador), ruta `/carpeta/colaborar` (o el path que se prefiera) análoga a `/riftbound/colaborar`, y el link "Carpetas Compartidas" en la nav.
- Esto es notablemente más trabajo que el resto de las fases porque no hay nada que copiar/adaptar del lado del backend — es diseño nuevo. Confirmar con el usuario si de verdad se quiere colaboración multiusuario en MYL antes de invertir aquí.

### Fase 8 — Repaletización completa
Reemplazar los 239 hex hardcodeados del `.scss` de MYL por los tokens `--ui-*` equivalentes, con el mismo cuidado que en Riftbound: **no tocar** colores semánticos que no son de tema (colores de rareza/facción específicos del juego, si los hay en MYL; colores de peligro en botones destructivos). Dado que aquí no hay problema de "choque de marca" tan claro como el rojo-vs-cian de Riftbound (no vimos qué acento usa MYL hoy), primero identificar el acento actual de MYL y decidir si el objetivo es el ámbar por defecto de `--ui-accent` o un override propio.

### Extras (no numerados como fase, pero parte del alcance)
- **Botón "Vender" en Colección** (MYL): mismo patrón que `sellFromCodex`/`quickSell` de Riftbound — agregar a carpeta si no existe, marcar `selling_quantity` y abrir el quick-edit.
- **Modal de cancelación de pedido**: reemplazar los `confirm()`/`alert()` de `carpeta.component.ts` (líneas 829-851) por un modal con campo de motivo, igual al de Riftbound. Requiere que `cancel_store_order` en el backend acepte y guarde `seller_note` (confirmar si ya lo hace).
- **Notificaciones de pedidos**: agregar `Notification.objects.create(...)` en `carpeta/views.py` al crear pedido (para el vendedor) y al aceptar/cancelar (para el comprador), con links a `/carpeta?tab=pedidos` y `/mis-compras?game=myl&store=<token>` respectivamente — mismo patrón que se corrigió en `riftbound/views.py`. Esto requiere también que `carpeta.component.ts` lea el query param `?tab=` igual que se agregó a `riftbound-carpeta.component.ts` (suscripción a `route.queryParamMap`, no solo `snapshot`).
- **Quitar `target="_blank"`**: en `tienda.component.html` líneas 46 y 115 (los dos links "Mis pedidos"/"Ver mis pedidos").

## Decisiones pendientes

Antes de ejecutar, conviene resolver con el usuario:

1. **¿Migrar a signals primero (Fase 0) o portar sobre el patrón actual?** Recomendación: migrar primero.
2. **¿Se construye la Fase 7 (permisos + Carpetas Compartidas)?** Es la única fase que es feature nueva, no port — mucho más esfuerzo que el resto combinado. Si la respuesta es no, las fases 4 (nav) y 8 simplemente omiten la sección "Administración → Permisos".
3. **¿Modelo de tours compartido o duplicado por juego?** Recomendación: compartido (evita mantener dos copias del mismo modelo/endpoint), pero implica tocar código de Riftbound ya en producción — evaluar riesgo.
4. **¿Acento visual propio para MYL** (como el cian de `.mode-riftbound`) **o usar el ámbar por defecto de `--ui-accent`?** Revisar qué está usando MYL hoy antes de decidir.
5. **Alcance de una sola pasada vs. incremental**: dado que Riftbound se hizo fase por fase con verificación en navegador entre cada una, se recomienda el mismo enfoque acá — no todo de una vez.

## Archivos de referencia (Riftbound → equivalente MYL)

| Riftbound (fuente a copiar/adaptar) | MYL (destino) |
|---|---|
| `frontend/src/app/pages/riftbound/carpeta/riftbound-carpeta.component.ts` | `frontend/src/app/pages/carpeta/carpeta.component.ts` (+ `.html` + `.scss`) |
| `frontend/src/app/pages/riftbound/carpeta/components/guide-modal/guide-modal.component.ts` | crear `frontend/src/app/pages/carpeta/components/guide-modal/guide-modal.component.ts` |
| `frontend/src/app/services/tour.service.ts` | reusar tal cual (ya es genérico) |
| `frontend/src/app/components/tour-overlay/tour-overlay.component.ts` | reusar tal cual (ya es genérico) |
| `frontend/src/app/pages/riftbound/tienda/riftbound-tienda.component.ts` | `frontend/src/app/pages/tienda/tienda.component.ts` (+ `.html`) |
| `frontend/src/app/pages/mis-compras/mis-compras.component.ts` | ya es compartido — sin cambios |
| `backend/riftbound/models.py` (`RiftboundStorePermission`, `RiftboundTourProgress`) | `backend/carpeta/models.py` (agregar equivalentes, o generalizar — ver Decisión 2 y 3) |
| `backend/riftbound/views.py` (`riftbound_workspaces`, `riftbound_tours`, notificaciones en accept/cancel) | `backend/carpeta/views.py` (agregar equivalentes) |
| `backend/riftbound/urls.py` | `backend/carpeta/urls.py` |
| `frontend/src/app/app.routes.ts` (`riftbound/colaborar`) | agregar `carpeta/colaborar` si se hace la Fase 7 |
