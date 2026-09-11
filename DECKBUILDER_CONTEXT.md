# Contexto: Constructor de Mazos (MyL y Riftbound)

> Documento de referencia técnica sobre cómo está implementado el deck builder de cada juego en este proyecto. Generado a partir de una exploración del código en `backend/` y `frontend/`.

## Idea general

Son **dos dominios de datos totalmente separados**, sin campo `game` compartido ni tabla `Card` unificada:

- **MyL (Mitos y Leyendas)**: apps Django `cards` (catálogo) + `decks` (mazos).
- **Riftbound**: todo autocontenido en la app Django `riftbound` (catálogo, mazos, banlist, colección, tienda).

Cita textual de `backend/riftbound/models.py` (líneas 1-6):
> "Mantenidos completamente separados de los modelos `cards` / `decks` (Mitos y Leyendas) para no acoplar dos juegos con reglas distintas."

---

## 1. MyL (Mitos y Leyendas)

### 1.1 Ubicación del código

**Backend**
- Catálogo: `backend/cards/models.py` — `Format`, `Season`, `Edition` (L4-50), `Race`, `CardType`, `Rarity`, `Keyword`, `Card` (L97-125), `BanlistEntry` (L128-161).
- Mazos: `backend/decks/models.py` — `Deck` (L5-31), `DeckEntry` (L34-44), `DeckChangeLog`, `DeckLike`, `DeckSnapshot`, `DeckComment`.
- Vistas de cartas: `backend/cards/views.py` (`CardListView`, L67-209).
- Vistas de mazo: `backend/decks/views.py` (CRUD, likes, comments, snapshots, sugerencias, import/export — 499 líneas).
- Serializers: `backend/decks/serializers.py` (`DeckCreateSerializer.validate`, L109-151 — única validación server-side).
- URLs: `backend/decks/urls.py`, `backend/cards/urls.py`.

**Frontend (Angular)**
- Constructor: `frontend/src/app/pages/deck-builder/deck-builder.component.ts` (2305 líneas) + `.html`/`.scss`.
- Listado/detalle: `pages/deck-list`, `pages/deck-view`, `pages/compare-decks`.
- Servicio: `frontend/src/app/services/deck.service.ts`.

### 1.2 Reglas de construcción

**Importante**: casi toda la validación de reglas de MyL vive en el **frontend**. El backend solo valida coherencia formato-edición al crear/editar el mazo; no revalida tamaño, copias, banlist ni raza.

- **Tamaño del mazo principal: 50 cartas** (límite duro en `addCard()`, L1071).
- **Sideboard: máx. 15 cartas** (`addToSide()`, L1130).
- **Copias máximas**: 3 por defecto, 1 si la carta es "Única" (`getMaxCopies()`, L842-847; unicidad = `ability` empieza con "Única", anotado por el backend en `cards/views.py:87-91`).
- **Copias efectivas cruzando variantes/reimpresiones**: se agrupan por nombre normalizado sin acentos/puntuación (`normalizeName()`, L38-48) y se toma el mínimo de copias permitidas entre versiones (`getEffectiveMaxCopies()`, L854-868).
- **Banlist por formato + sub-formato** (`loadBanlist()`, L709-722; modelo `BanlistEntry`): estados `banned`, `limited_1`, `limited_2`. Endpoint: `GET /api/cards/banlist/`.
- **Restricción racial** (mazos "racial", L896-997):
  - Solo los **Aliados** están restringidos por raza; Oro/Arma/Talismán/Tótem siempre permitidos.
  - Raza **"Dream"**: cualquier aliado sin restricción.
  - Raza **"Tótem"**: solo aliados sin raza.
  - **Arquetipos multi-raza** hardcodeados (`escMultiRace`, L898-903): culto-tenebris (sombra+oni), vigilantes-etéreos (eterno+faerie), gremio-paladín (caballero+sacerdote), clan-desafiante (dragón+guerrero).
  - Razas por **texto de habilidad** ("Luz"/"Oscuridad" al inicio de la primera línea, L922-930).
  - **Máx. 4 aliados sin raza** en mazos raciales (`racelessAllyLimit`, L904).
  - Misma lógica duplicada en backend para filtrar catálogo (no para validar guardado): `cards/views.py:174-204`.
- **Restricción por formato/edición** (`isCardAllowedByFormat()`, L999-1015):
  - Formato `esc` (Escuelas Elementales): whitelist fija de ediciones (`escEditionSlugs`, L162-167; duplicada en backend `decks/serializers.py:6-18`).
  - Formatos `pb`/`pe` (Primer Bloque/Primera Era): restringen por "grupo de edición" (`pbEditionGroups`, L169-182).
  - `formatViolations` (L1024-1038) detecta cartas fuera de formato; el guardado (`saveDeck()`, L1472) **se bloquea** si hay violaciones pendientes.
- **Rotación de temporada** (solo formato Imperio, `seasons`, L156-159): excluye ediciones completas de la búsqueda.
- **Sub-formato VCR** (Vasallo/Cortesano/Real): filtra rarezas a `promo, real, vasallo, cortesano` y excluye tipo "Monumento" (`ngOnInit`, L320-325; también server-side en `cards/views.py:147-172`).
- **Oro inicial**: elegible solo si tipo="Oro" y su habilidad contiene "oro inicial" (`isEligibleStartingGold()`, L1276-1280). Se persiste como FK `starting_gold` en `Deck`; se limpia solo si se quita del mazo (`removeCard()`, L1106-1108).
- **Validación al guardar** (`saveDeck()`, L1454-1532): exige nombre no vacío y ≥1 carta; bloquea si hay `formatViolations`. **No** revalida 50/15, banlist ni raza en este punto (confía en que la UI ya lo impidió).

### 1.3 Modelos de datos

`backend/cards/models.py`:
- `Card` (L97-125): `myl_id`, `edid`, `slug`, `name`, `edition` (FK), `rarity` (FK), `race` (FK, nullable), `card_type` (FK: Oro/Aliado/Arma/Talismán/Tótem/Monumento), `cost`, `damage`, `ability`, `flavour`, 3 campos de imagen (ImageKit/Cloudinary/custom).
- No hay `is_gold` ni `is_legendary` como columnas: se derivan de `card_type.slug` y de `ability` respectivamente.
- `BanlistEntry` (L128-161): `card_name`, `card` (FK opcional), `format_code`, `sub_format`, `status`, `max_copies`.

`backend/decks/models.py`:
- `Deck` (L5-31): `owner`, `name`, `description`, `format` (string, default `"imp"`), `sub_format` (default `"racial"`), `race` (string libre), `pb_edition`, `is_public`, `shared_with_team`, `starting_gold` (FK Card), `cover_card` (FK Card).
- `DeckEntry` (L34-44): `deck`, `card` (FK), `quantity`, `is_sideboard` (booleano). `unique_together = (deck, card, is_sideboard)`.
- `DeckSnapshot`: guarda JSON completo del mazo para rollback.

### 1.4 Endpoints de API

`backend/decks/urls.py`:

| Ruta | Vista | Función |
|---|---|---|
| `GET /public/` | `PublicDeckListView` | mazos públicos |
| `GET/POST /my/` | `MyDeckListView` | listar/crear propios |
| `GET/PUT/PATCH/DELETE /my/<id>/` | `DeckDetailView` | detalle/edición/borrado |
| `POST/DELETE /my/<id>/entries/` | `deck_entry_view` | añadir/quitar carta |
| `GET /my/<id>/changelog/` | `deck_changelog_view` | historial |
| `POST/DELETE /my/<id>/cover/` | `deck_cover_view` | portada |
| `GET/POST /my/<id>/snapshots/` | `deck_snapshots_view` | versiones |
| `POST /snapshots/<id>/restore/` | `restore_snapshot` | rollback |
| `GET /my/<id>/suggestions/` | `card_suggestions` | sugerencias por formato+raza |
| `POST /import/` | `import_deck` (L415-498) | importar JSON, resuelve `myl_id`, tope 200 cartas |
| `POST /public/<id>/like/`, `GET/POST /public/<id>/comments/` | social |

`backend/cards/urls.py`: `GET /api/cards/`, `/banlist/`, `/editions/`, `/formats/`, `/races/`, `/rarities/`, `/types/`, `/by-format/<code>/`.

**No existe** un endpoint `/decks/<id>/validate/` para MyL (a diferencia de Riftbound).

---

## 2. Riftbound

### 2.1 Ubicación del código

**Backend** (todo en `backend/riftbound/`):
- `models.py` (563 líneas): catálogo (`RiftboundSet`, `RiftboundCard`), banlist (`RiftboundFormat`, `RiftboundBanlistEntry`), mazos (`RiftboundDeck`, `RiftboundDeckEntry`), colección/wishlist, tienda, iconografía.
- `validation.py` (136 líneas): validador de reglas de mazo, en endpoint dedicado.
- `views.py`: `RiftboundDeckViewSet` (L443-485), acción custom `validate`.
- `urls.py`: `DefaultRouter`, prefijo `/api/riftbound/`.

**Frontend**
- Constructor: `frontend/src/app/pages/riftbound/builder/riftbound-builder.component.ts` (2120 líneas).
- Vista de mazo: `pages/riftbound/deck-view/riftbound-deck-view.component.ts`.
- Listado: `pages/riftbound/decks/riftbound-decks.component.ts`.
- Banlist: `pages/riftbound/banlist/riftbound-banlist.component.ts`.
- Modelos TS: `frontend/src/app/models/riftbound.ts` (`RIFTBOUND_ZONE_RULES` L308-314, `RIFTBOUND_ZONE_LABELS` L316-322).
- Servicio: `frontend/src/app/services/riftbound.service.ts`.

### 2.2 Reglas de construcción

Riftbound tiene un **validador de backend dedicado**, documentado en docstrings (`models.py:1-16`, `validation.py:1-10`), fuente citada: "Deckbuilding Primer + Core Rules de Riot".

- **Main Deck: exactamente 40 cartas** (`RULES_EXACT[ZONE_MAIN] = 40`, `validation.py:26`). *Nota de inconsistencia*: el comentario en `models.py:9` dice "mínimo 40 (recomendado 40)", pero el validador lo trata como exacto; `RULES_MIN` está vacío, así que ninguna zona se valida realmente como mínimo.
- **Rune Deck: exactamente 12 runas**, exentas del límite de 3 copias.
- **Champion Legend: exactamente 1 carta**, aparte del main deck.
- **Battlefields: exactamente 3 cartas, todas distintas** (chequeo de duplicados, L83-85).
- **Sideboard**: opcional en casual; si se usa, debe ser exactamente 10 (warning, no error, L87-93).
- **Máximo 3 copias por carta** (`MAX_COPIES_DEFAULT = 3`), salvo:
  - Cartas con keyword `[Unique]` en la descripción → máx. 1 (L96-101, 118-123).
  - Cartas en banlist (`RiftboundBanlistEntry`): `banned` (0) o `limited_1`/`limited_2` con `max_copies` explícito.
  - El **Chosen Champion**: su copia inicial en juego ya cuenta hacia el límite de 3.

`validate_riftbound_deck(deck)` (`validation.py:42-135`) devuelve `{valid, errors, warnings, counts, rules}`, expuesto en `GET /api/riftbound/decks/<id>/validate/` (público, `AllowAny`).

**Diferencia clave de UX vs MyL**: el guardado **no bloquea** aunque el mazo esté incompleto. Cita textual (`riftbound-builder.component.ts:2107`):
> "El mazo se guarda aunque este incompleto: la validacion es solo informativa."

`save()` (L2084-2119) no llama a `/validate/` antes de guardar; ese endpoint se usa en otra vista (p. ej. `riftbound-deck-view`) para mostrar legalidad ya guardada, no como gate.

Reglas replicadas en frontend:
- Constantes de zona (`models.ts:308-314`): `main: 40, side: 10, rune: 12, champion: 1, bg: 3`.
- `getMaxCopies()` (L1583-1595): banlist → override "Spiderling" (copias ilimitadas dentro del límite de 40, comentario L1590) → battlefield/legend → 1 → rune → 12 → default 3.
- `canAddToAuto()`/`addToZone()` (L1615-1643): límites duros por zona al agregar.
- Banlist con estados `banned`, `limited`/`restricted` (nomenclatura distinta a MyL).
- **Champion Unit** (exclusivo de Riftbound, no existe en MyL): unidad del main deck cuyo subtipo/nombre coincide con el Champion Legend; wizard de selección guiada (`isChampionUnitCandidate` L1829-1839, `openChampionUnitPicker`/`loadChampionUnitsForLegend` L1847-1943). Persistida como FK `champion_unit` en `RiftboundDeck`.
- No hay "raza"/facción restrictiva; existen **colores** (`Fury, Calm, Mind, Body, Chaos, Order, Neutral`, `models.py:42-50`) solo para estadísticas visuales, no restringen qué se puede añadir.

### 2.3 Modelos de datos

`backend/riftbound/models.py`:
- `RiftboundCard` (L78-146): `card_number` (id estable, ej. `OGN-001`), `external_id` (UUID del scraper Piltover Archive), `card_type` (choices: champion/legend/unit/spell/gear/battlefield/rune/other), `rarity`, `colors` (JSON list), `energy`/`power`/`might` (stats numéricos), `description` (contiene la keyword `[Unique]`).
- `RiftboundBanlistEntry` (L162-188): `format` (FK, no string libre), `card` (FK obligatoria), `status`, `max_copies`.
- `RiftboundDeck` (L210-238): `owner`, `format` (FK), `cover_card`, `champion_unit` (FK, exclusivo), `primary_colors` (JSON).
- `RiftboundDeckEntry` (L241-251): `deck`, `card`, `quantity`, `zone` (choices: `main/side/rune/champion/bg`). `unique_together = (deck, card, zone)`.

### 2.4 Endpoints de API

Vía `DefaultRouter` (`backend/riftbound/urls.py:25-33`), prefijo `/api/riftbound/`:
- `GET/POST /decks/`, `GET/PUT/PATCH/DELETE /decks/<id>/` (CRUD estándar DRF).
- **`GET /decks/<id>/validate/`** — único endpoint de validación server-side de reglas en todo el proyecto.
- `/cards/`, `/sets/`, `/formats/`, `/banlist/`, `/icons/` (catálogo).
- No hay endpoint de import/export JSON de mazo equivalente al de MyL.

---

## 3. Comparativa UI/UX

| Aspecto | MyL | Riftbound |
|---|---|---|
| Organización de cartas | 2 listas: `deckCards` (main) / `sideCards`, booleano `is_sideboard` | 5 zonas simultáneas: `main/side/rune/champion/bg` |
| Validación | Solo frontend + chequeo mínimo de formato en backend; **guardado bloqueado** si hay `formatViolations` | Endpoint de validación en backend; **guardado NO bloqueado** (informativa) |
| Concepto especial de carta | "Oro inicial" (`starting_gold`) | "Champion Legend" + "Champion Unit" (wizard guiado) |
| Restricción de construcción | Raza/facción (multi-raza ESC, Luz/Oscuridad, límite de aliados sin raza) | Sin restricción de facción; colores solo informativos |
| Banlist | Por `format_code` + `sub_format`, indexada por nombre normalizado | Por `RiftboundFormat` (FK), indexada por `card_number` exacto |
| Import/Export | Export de texto + import JSON vía API (`buildExportText`, `import_deck`) | No se encontró equivalente |
| Angular Signals | Mixto (mayormente propiedades de clase) | Uso extensivo de `signal()`/`computed()` |
| Borrador local | `localStorage`, clave por `deckId+format+subformat+race` | `localStorage`, clave única, guardado en `ngOnDestroy`/`beforeunload` |

---

## 4. Riesgo identificado (no accionado)

El deckbuilder de **MyL** no revalida en el servidor los límites de 50/15 cartas, copias máximas, banlist ni restricción racial al guardar — toda esa lógica vive en el cliente (`deck-builder.component.ts`). Un mazo creado directamente contra `POST /api/decks/my/` (sin pasar por la UI) podría violar cualquiera de esas reglas; solo se valida coherencia de formato/edición (`decks/serializers.py:109-151`).

Riftbound sí ofrece un validador de servidor (`riftbound/validation.py`), pero el frontend lo usa solo de forma informativa y no bloquea el guardado de mazos "ilegales".
