# Plan de Testing — Deckshadow (MyL + Riftbound)

> Generado tras analizar `backend/` (Django/DRF) y `frontend/` (Angular) y la suite de tests existente.
> Complementa `DECKBUILDER_CONTEXT.md`. Objetivo: asegurar el funcionamiento del sistema completo,
> priorizando las zonas con más riesgo y menos cobertura actual.

## 0. Estado actual (línea base)

- Backend: 8 archivos `tests.py` / `test_tcg.py`, ~845 líneas antes de esta sesión.
  Cubren: banlist, búsqueda de cartas, CDN de imágenes, ediciones activas, admin de ediciones,
  visibilidad/likes/comentarios de mazos MyL, comando `fix_deck_entries_by_name`, upsert de colección Riftbound.
- **Añadido en esta sesión** (ver abajo, sección 6): 16 tests de `riftbound/validation.py`
  (0% cobertura previa pese a ser "el único validador server-side de reglas de todo el proyecto")
  y 4 tests de regresión que documentan el gap de validación server-side en mazos MyL.
- Frontend: solo 7 `*.spec.ts` en todo `frontend/src/app` (services de auth/deck/theme, 2 pipes, admin,
  `app.spec.ts`). **`deck-builder.component.ts` (2305 líneas) y `riftbound-builder.component.ts`
  (2120 líneas) — donde vive casi toda la lógica de reglas del juego — tienen 0% cobertura.**
- No hay tests E2E (Cypress/Playwright) ni tests de contrato API↔frontend.
- `teams/tests.py` y `users/tests.py` son stubs vacíos (3 líneas, boilerplate de Django).

## 1. Prioridades (orden sugerido de ejecución)

1. **Riftbound `validation.py`** — hecho en esta sesión (16 tests).
2. **Gap de reglas server-side en MyL** — documentado con 4 tests de regresión en esta sesión;
   decidir si se cierra (añadir validación en `DeckCreateSerializer`) o se acepta el riesgo.
3. **Lógica pura de `deck-builder.component.ts`** (frontend, MyL): `normalizeName`,
   `getMaxCopies`/`getEffectiveMaxCopies`, `isCardAllowedByFormat`, `formatViolations`,
   restricción racial (`escMultiRace`, aliados sin raza, Luz/Oscuridad).
4. **Lógica pura de `riftbound-builder.component.ts`**: `getMaxCopies`, `canAddToAuto`/`addToZone`,
   `isChampionUnitCandidate`.
5. **Permisos y ownership** en todos los ViewSets (quién puede editar/borrar qué).
6. **Import/export de mazos MyL** (`import_deck`, tope de 200 cartas, resolución por `myl_id`).
7. **Colección/wishlist/tienda de Riftbound y `carpeta`** (flujos de negocio con dinero/inventario:
   `RiftboundStoreOrder`, `RiftboundStorePermission`).
8. **E2E de los flujos críticos** (crear cuenta → construir mazo → guardar → hacerlo público → verlo).

---

## 2. Backend — por app

### 2.1 `cards` (catálogo MyL)
Ya cubierto: banlist (filtros, unicidad, consistencia status/max_copies), búsqueda insensible a
acento/mayúsculas, prioridad de CDN de imagen, filtrado por edición activa, toggle de ediciones (admin).

**Casos a añadir:**
- Filtrado combinado `fmt` + `sub` (VCR: excluir "Monumento", solo rarezas promo/real/vasallo/cortesano) —
  la lógica está duplicada en `cards/views.py:147-172`, verificar que ambas copias (frontend/backend)
  concuerden con un mismo fixture.
- Filtrado por raza incluyendo los arquetipos multi-raza hardcodeados (`escMultiRace`) — si existe
  endpoint server-side equivalente (`cards/views.py:174-204`), testear los 4 combos: culto-tenebris,
  vigilantes-etéreos, gremio-paladín, clan-desafiante.
- Rotación de temporada (`seasons`, solo formato Imperio): una edición marcada "rotada" no debe aparecer
  en `/api/cards/` para ese formato aunque `active=True`.
- Paginación: página fuera de rango, `page_size` inválido.
- Endpoints `/editions/`, `/formats/`, `/races/`, `/rarities/`, `/types/`, `/by-format/<code>/`:
  al menos un test de "shape" (campos esperados) por endpoint — hoy no existen.
- `BanlistEntry` con `card=None` (carta no encontrada en catálogo, solo `card_name` libre) — ¿se sigue
  filtrando bien por nombre?

### 2.2 `decks` (mazos MyL)
Ya cubierto: visibilidad pública/privada, likes (toggle e idempotencia), comentarios (longitud, permisos
de borrado), comando de mantenimiento `fix_deck_entries_by_name`.

**Añadido en esta sesión:** gap de validación server-side (copias, 50 cartas, banlist) — ver `decks/tests_rule_gap.py`.

**Casos a añadir:**
- `DeckEntry` con `quantity=0` o negativo — ¿la API lo rechaza? (`PositiveSmallIntegerField` rechaza
  negativos a nivel DB/serializer, pero `0` es válido para el campo; probar si tiene sentido de negocio).
- `unique_together=(deck, card, is_sideboard)`: intentar crear dos `DeckEntry` iguales vía
  `update()` del serializer (reemplazo completo de entries) y confirmar que nohay `IntegrityError`.
- `starting_gold` / `cover_card` que referencian una `Card` de **otro** formato/edición — ¿se valida?
- `DeckSnapshot` / `restore_snapshot`: guardar, modificar el mazo, restaurar, verificar que las entries
  vuelven al estado exacto del snapshot (incluye sideboard).
- `deck_changelog_view`: verificar que cada `update()` que cambia campos relevantes genera **una sola**
  entrada de changelog (no una por campo) y que cambios irrelevantes (ej. `updated_at`) no generan ruido.
- `card_suggestions`: sugerencias respetan formato + raza + banlist (o documentar si no lo hacen).
- `import_deck` (líneas 415-498 de `decks/views.py`):
  - JSON válido con cartas resueltas por `myl_id` → mazo creado correctamente.
  - `myl_id` inexistente → ¿se ignora la carta, o falla el import completo?
  - Payload con más de 200 cartas → debe truncar o rechazar (documentado como "tope 200").
  - Payload malformado (falta `entries`, tipos incorrectos) → 400, no 500.
- Ownership: usuario B no puede `PATCH`/`DELETE` un mazo de A vía `/my/<id>/` (probar 403/404 explícito,
  hoy solo se prueba lectura en `DeckVisibilityTests`).
- `TeamDeckListView`/`TeamDeckDetailView` (`shared_with_team`): sin tests actualmente — verificar que
  solo miembros del equipo del owner ven mazos compartidos, y que un mazo `shared_with_team=False` no
  aparece ahí aunque sea del mismo equipo.
- `deck_cover_view`: asignar/quitar portada; portada debe pertenecer a una carta que esté en el mazo
  (¿se valida o se puede poner cualquier `Card`?).

### 2.3 `riftbound`
Ya cubierto (previo): upsert/batch-upsert de colección (dedupe por `id`, tolerancia >200 cambios).
**Añadido en esta sesión:** 16 tests de `validate_riftbound_deck` (zonas exactas, duplicados en
battlefields, límite de copias, keyword `[Unique]`, banlist banned/limited, exención de runas,
sideboard opcional, mazo sin `format`).

**Casos a añadir:**
- `RiftboundDeckViewSet.validate` (endpoint `GET /decks/<id>/validate/`): test de integración HTTP
  completo (hoy solo se probó la función `validate_riftbound_deck` de forma unitaria), incluyendo que
  sea `AllowAny` (acceso anónimo a un mazo ajeno — ¿es intencional exponer reglas de mazos privados?).
- `champion_unit`: asignar una unidad cuyo subtipo/nombre NO coincide con el champion legend — ¿se
  rechaza server-side o solo lo evita el wizard del frontend?
- CRUD estándar DRF de `/decks/`: ownership (usuario B no edita mazo de A), `is_public=False` no debe
  aparecer en listados públicos si existieran (revisar si hay endpoint público equivalente a MyL).
- Colección (`RiftboundCollectionEntry`): `quantity` negativa, `is_foil` combinada con condición de
  carta, entradas duplicadas por `(user, card, is_foil, condition)` si esa es la unicidad real.
- Wishlist (`RiftboundWishlistEntry`): sin tests — CRUD básico y ownership.
- Tienda (`RiftboundStoreOrder`, `RiftboundStoreOrderItem`, `RiftboundStorePermission`): **zona de mayor
  riesgo de negocio sin tests** — quién puede crear/aceptar/rechazar una orden, transiciones de estado
  válidas e inválidas, permisos por tienda (`RiftboundStorePermission`).
- `RiftboundBinderProfile` / `store_slug` único: colisión de slugs al crear dos binders con nombres
  que normalizan igual.
- `RiftboundIcon`, `RiftboundSyncState`, `RiftboundOpsRun`: si tienen endpoints admin, al menos smoke test.
- `RiftboundTourProgress`: idempotencia de "marcar paso visto" (doble POST no duplica progreso).

### 2.4 `carpeta` (colección MyL — 257 líneas de tests ya existentes)
- Revisar cobertura existente y extender con los mismos ejes que Riftbound: permisos de tienda,
  slugs de binder, `accepts_trades`.

### 2.5 `teams` y `users`
- **Ambos son stubs vacíos.** Mínimo viable:
  - `teams`: creación de equipo, invitar/expulsar miembro, quién puede ver/editar `Team.logo`,
    relación con `shared_with_team` de `decks`.
  - `users`: registro, login (JWT), refresh token expirado/inválido, `Notification` (creación,
    marcar leída, no ver notificaciones ajenas), `SocialAccount` (vinculación OAuth si aplica).

### 2.6 Transversal / seguridad
- **Autenticación JWT**: token expirado → 401; token de un usuario borrado → 401, no 500.
- **Permisos por owner** en cada `DetailView`/`ViewSet` de mazos, binders, órdenes de tienda: patrón
  repetido "owner ve todo, otro usuario autenticado no ve nada de lo privado" — vale la pena un
  helper de test compartido (`_auth`, ya existe en `decks/tests.py`, se podría mover a un módulo común).
- **Rate limiting / anti-spam** en comentarios y likes (¿existe? si no, documentarlo como riesgo).
- **Inyección/escape**: nombres de mazo, comentarios y descripciones con HTML/script — confirmar que el
  frontend escapa al renderizar (no es un test de backend, pero vale un test de serializer que el texto
  se guarda tal cual y no se ejecuta nada raro en `admin.py` custom views).
- **Django admin custom views** (`cards-admin-toggle-editions` ya testeado): revisar si hay más vistas
  admin custom sin tests (`grep "def .*_view" backend/*/views.py` fuera de las ya cubiertas).

---

## 3. Frontend — por área

### 3.1 Lógica pura extraíble (la más rentable de testear, hoy en 0%)
Idealmente refactorizar estas funciones a servicios/utilidades puras primero (facilita testear sin
montar el componente completo), pero incluso sobre el componente actual con Angular TestBed:

**`deck-builder.component.ts`:**
- `normalizeName()` — casos: acentos, mayúsculas, puntuación, nombres con paréntesis (reimpresiones).
- `getMaxCopies()` / `getEffectiveMaxCopies()` — carta "Única" (1 copia), variantes cruzadas con
  distinto máximo (debe tomar el mínimo).
- `isCardAllowedByFormat()` — los 3 casos: `esc` (whitelist), `pb`/`pe` (grupos de edición), formato
  normal (coincidencia directa).
- `formatViolations` — detecta violaciones, y `saveDeck()` se bloquea si hay alguna pendiente.
- Restricción racial: Dream (sin restricción), Tótem (solo aliados sin raza), los 4 arquetipos
  multi-raza, detección de Luz/Oscuridad por texto de habilidad, límite de 4 aliados sin raza.
- `isEligibleStartingGold()` — tipo Oro + texto "oro inicial"; se limpia `starting_gold` solo al
  quitar la carta del mazo (no al cambiar de formato, por ejemplo — ¿es correcto?).
- `addCard()`/`addToSide()` — límites duros 50/15, qué pasa exactamente en el límite (50ª carta OK,
  51ª rechazada) y en el borde de copias (3ª OK, 4ª rechazada; 1ª OK, 2ª rechazada si es Única).
- `saveDeck()` — nombre vacío rechazado, mazo con 0 cartas rechazado, bloqueo por `formatViolations`.
- Borrador en `localStorage`: clave compuesta `deckId+format+subformat+race`; verificar que cambiar de
  raza/formato no mezcla el borrador de otro mazo.

**`riftbound-builder.component.ts`:**
- `getMaxCopies()` — orden de prioridad: banlist → override "Spiderling" (ilimitado dentro del main de
  40) → battlefield/legend (1) → rune (12) → default (3). Testear que el orden se respeta cuando varias
  condiciones podrían aplicar.
- `canAddToAuto()`/`addToZone()` — límites duros por zona (main 40, side 10, rune 12, champion 1, bg 3).
- `isChampionUnitCandidate()` / wizard de selección — coincidencia por subtipo/nombre con el legend.
- `save()` — confirmar explícitamente que **no** bloquea aunque el mazo esté incompleto (es
  comportamiento intencional; un test que lo verifique evita que una regresión lo "arregle" sin querer).
- Guardado en `localStorage` en `ngOnDestroy`/`beforeunload` — simular ambos triggers.

### 3.2 Servicios (ya hay 2 specs: `auth.service`, `deck.service`)
- `riftbound.service.ts` — sin spec. Cubrir al menos: construcción de URLs/params de los mismos
  endpoints que el backend expone, manejo de errores HTTP (401/403/404/500) propagados a los componentes.
- Interceptores HTTP (si existen, ej. adjuntar JWT, refresh automático) — casos de token expirado
  a mitad de sesión.

### 3.3 Componentes de listado/detalle/social
- `deck-list`, `deck-view`, `compare-decks`, `riftbound-decks`, `riftbound-deck-view`, `riftbound-banlist`:
  smoke tests (renderizan sin error con datos mock) + interacción básica (like, comentar, filtrar).
- `admin.component` ya tiene spec — revisar cobertura real vs. solo boilerplate.

### 3.4 Pipes
- `relative-time.pipe` y `thumbnail.pipe` ya tienen specs — verificar que cubren zonas horarias/edge
  cases (fecha futura, fecha `null`, imagen sin CDN configurado).

---

## 4. Integración / contrato API↔Frontend
- Contract tests o al menos "shape tests": los campos que el frontend espera de cada endpoint
  (`DeckDetailSerializer`, `CardListSerializer`, etc.) siguen presentes tras cualquier refactor de
  serializers. Se puede lograr con un test backend que compare `response.data.keys()` contra una lista
  fija por endpoint.
- Verificar consistencia de las **reglas duplicadas** frontend/backend señaladas en
  `DECKBUILDER_CONTEXT.md` (ESC whitelist de ediciones, grupos PB/PE, filtro racial, filtro VCR): un
  cambio en una copia sin la otra debe ser detectable. Sugerencia: extraer ambas listas a un fixture
  JSON compartido usado por los tests de ambos lados, o al menos un test que las compare literalmente
  si se exporta la constante del backend en algún endpoint de metadata.

## 5. End-to-end (recomendado, no existe hoy)
Herramienta sugerida: Playwright (ya hay Vitest en `frontend/node_modules`, Playwright se integra bien).
Flujos mínimos:
1. Registro → login → crear mazo MyL vacío → agregar cartas hasta 50 → guardar → verlo público.
2. Intentar exceder 50 cartas / 3 copias / carta baneada desde la UI → confirmar que la UI lo impide
   (esto es justamente lo que NO se valida en servidor, por lo que el E2E es la única red de seguridad
   real para el usuario final hasta que se cierre el gap del punto 2.2/6).
3. Construir mazo Riftbound completo (40/12/1/3) → guardar incompleto → ver que no bloquea → completar
   → ver validación en verde.
4. Dar like/comentar un mazo público como otro usuario; borrar el comentario como dueño del mazo.
5. Exportar mazo MyL a texto → importar ese texto/JSON en una cuenta nueva → comparar que el resultado
   es idéntico.

## 6. Tests añadidos en esta sesión

| Archivo | Qué cubre | Resultado |
|---|---|---|
| `backend/riftbound/tests_validation.py` | 16 tests de `validate_riftbound_deck`: mazo legal completo, tamaños exactos de zona (main/rune/champion/bg), sideboard opcional (warning vs error), duplicados en battlefields, límite de 3 copias, keyword `[Unique]`, exención de runas, banlist banned/limited_1, banlist de otro formato no aplica, mazo sin `format` no rompe. | ✅ 16/16 pasan |
| `backend/decks/tests_rule_gap.py` | 4 tests de regresión que documentan que la API de mazos MyL acepta hoy: >3 copias de una carta, >50 cartas en main, una carta en banlist — y confirma que la única validación real (coherencia formato/edición) sigue activa. | ✅ 4/4 pasan (documentan comportamiento actual, no un bug introducido por esta sesión) |

Verificación: `python manage.py test` completo → **75/75 tests pasan** (55 preexistentes + 20 nuevos).

## 7. Decisión pendiente para el usuario

Los tests de `decks/tests_rule_gap.py` **documentan** el riesgo pero no lo corrigen. Si se quiere cerrar
la brecha (recomendado antes de exponer la API públicamente a terceros, o si algún día hay una app
externa que hable con esta API sin pasar por el Angular actual), el siguiente paso sería: mover la
validación de copias/tamaño/banlist/raza de `deck-builder.component.ts` a `DeckCreateSerializer.validate()`
(siguiendo el patrón que ya usa Riftbound en `validation.py`), y luego actualizar estos tests para que
verifiquen el **rechazo** en vez de la aceptación.
