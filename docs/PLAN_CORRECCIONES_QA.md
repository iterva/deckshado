# Plan de corrección — QA 2026-09-16

Este plan sale de [QA_REPORT_2026-09-16.md](QA_REPORT_2026-09-16.md). Cada tarea tiene **archivo**, **cambio propuesto**, **criterio de aceptación** y **cómo verificar**.
Márcalas con `[x]` a medida que las cierres. Las rutas son relativas a `Proyecto-deckshado/`.

**Orden recomendado:** Sprint 1 (rápidos y de alto impacto) → Sprint 2 (backend y reglas) → Sprint 3 (visual y UX) → Sprint 4 (mejoras).

---

## Progreso

| Sprint | Tareas | Hechas |
|---|---|---|
| 1 — Críticos rápidos | 7 | 7 |
| 2 — Backend / reglas | 4 | 4 |
| 3 — Visual / UX | 10 | 10 |
| 4 — Mejoras | 8 | 2 (+2 parciales) |


### Notas de implementación (2026-09-17)

- **2.1** Se resolvió sin cambiar el breakpoint móvil: ≤1400 px el buscador queda como ícono; ≤1200 px los links quedan sólo con ícono (texto accesible + `title`). Medido con sesión a 861, 1024, 1100, 1201, 1280, 1366 y 1440 px: nada fuera de pantalla.
- **2.2** Replica exactamente las reglas del constructor (ban por `card_id` o nombre normalizado, mínimo entre versiones del mismo nombre, sub-formato vacío = toda la banlist del formato). Raza: sólo en frontend (documentado en `DECKBUILDER_CONTEXT.md` §4). Pendiente: `POST /api/decks/my/<id>/entries/` no valida (sin uso en la UI).
- **2.3** El builder valida copias por carta **dentro de cada zona** (no por nombre entre main y side) y exime a *Spiderling*; el servidor aplica esa misma regla para no rechazar mazos que la UI permite. Banlist/[Unique] siguen informativos.
- **3.1** Correcciones con `:host-context(body.light-theme)` y el token `--ui-accent-text` (sin tocar el modo oscuro). Además se corrigió el botón "Crear un mazo" de `/banlist`, invisible en ambos temas por la regla global `.banlist-article a`. Auditoría automática de contraste en `/`, `/cards`, `/decks`, `/banlist`, `/login` y `/builder/new/imp`: sin fallos (queda el botón activo "Nombre" 3.83:1, color de marca). El modo claro de `/riftbound/builder` sigue con problemas (fuera del alcance de 3.1).
- **3.4** Los `aria-label` ya eran correctos en el código actual; sólo se actualizó el texto del estado vacío.
- **3.9** Versión mínima: mensaje + link a Mazos (donde ya existe el modo «Comparar»).
- **4.4 (parcial)** `<h1>` en login/registro y `aria-label` en el buscador de `/cards`. **4.5 (parcial)** `loading="lazy"`/`decoding="async"` en las imágenes de entradas y modales del builder Riftbound.
- **No aplicados a propósito** (requieren decisión/entorno): 4.2, 4.3 (features nuevas), 4.7 (cambiar `DEBUG` por defecto o la vida de los tokens puede romper producción o cerrar sesiones si la variable de entorno no está definida en PythonAnywhere) y 4.8 (mover archivos / `.gitignore`).

---

## Sprint 1 — Críticos rápidos

### [x] 1.1 Búsqueda con `(`, `[`, `?`, `\` devuelve HTTP 500 · 🔴 ALTA
**Archivo:** `backend/cards/views.py` (función `_accent_insensitive`, ~L55; se usa en L134 y L138)

**Causa:** lo que escribe el usuario se usa como regex en `__iregex` sin escapar.

**Cambio:**
```python
import re

def _accent_insensitive(text: str) -> str:
    """Convert search text to a regex pattern that matches with or without accents."""
    nfkd = unicodedata.normalize('NFKD', text.lower())
    stripped = ''.join(c for c in nfkd if not unicodedata.combining(c))
    # Escapar cada carácter ANTES de expandir acentos: evita 500 con ( [ ? \ * y que "." matchee todo
    return ''.join(_ACCENT_MAP.get(c, re.escape(c)) for c in stripped)
```
> Ojo: revisa que los valores de `_ACCENT_MAP` sean clases tipo `[aáàä]` (regex válidas). No hay que escaparlas: lo que se escapa es el carácter original cuando no está en el mapa.

**Test** (agregar en `backend/cards/tests.py`):
```python
def test_search_with_regex_special_chars_does_not_500(self):
    for q in ["(", "[", "?", "\\", "a**", "Espada ("]:
        r = self.client.get("/api/cards/", {"search": q})
        self.assertEqual(r.status_code, 200, q)
        r = self.client.get("/api/cards/", {"ability_search": q})
        self.assertEqual(r.status_code, 200, q)

def test_search_dot_is_literal(self):
    r = self.client.get("/api/cards/", {"search": "."})
    self.assertLess(r.json()["count"], Card.objects.count())
```

**Aceptación:**
- `GET /api/cards/?search=(` responde 200.
- `search=.` ya no devuelve las 2395 cartas.
- `dragon` sigue encontrando "Dragón".

**Verificar:**
```bash
curl -s -o /dev/null -w "%{http_code}\n" "http://localhost:8000/api/cards/?search=%28"
```

---

### [x] 1.2 Título de pestaña con mojibake `Mazos â€” ShadowForge` · 🟠 MEDIA
**Archivo:** `frontend/src/app/pages/deck-list/deck-list.component.ts:149`

**Cambio:**
```ts
this.titleService.setTitle('Mazos públicos | ShadowForge');
```
**Extra:** buscar otros casos de mojibake y confirmar que no quede ninguno.
```bash
grep -rn "â€\|Ã©\|Ã±\|Ã³" frontend/src
```
**Aceptación:** la pestaña de `/decks` muestra el texto correcto.

---

### [x] 1.3 `/profile` y `/profile/edit` accesibles sin sesión · 🟠 MEDIA
**Síntoma:** sin sesión se ve un perfil vacío ("—") con el botón "Cerrar Sesión".

**Cambio:** crear un guard reutilizable y aplicarlo en las rutas.

`frontend/src/app/guards/auth.guard.ts` (nuevo):
```ts
import { CanActivateFn, Router } from '@angular/router';
import { inject } from '@angular/core';
import { AuthService } from '../services/auth.service';

export const authGuard: CanActivateFn = (_route, state) => {
  const auth = inject(AuthService);
  const router = inject(Router);
  if (auth.isLoggedIn()) return true; // ajustar al nombre real del signal/método en AuthService
  return router.createUrlTree(['/login'], { queryParams: { returnUrl: state.url } });
};
```
`frontend/src/app/app.routes.ts`: agregar `canActivate: [authGuard]` a:
- `profile`
- `profile/edit`
- (opcional, para ordenar) `builder`, `builder/new/:format`, `builder/:id`, `carpeta`, `riftbound/carpeta`, que hoy redirigen desde el componente.

**Aceptación:** sin sesión, `/profile` redirige a `/login?returnUrl=/profile`, y tras iniciar sesión vuelve a `/profile`.

---

### [x] 1.4 Builder Riftbound sin sesión muestra el error crudo del servidor · 🟠 MEDIA
**Archivo:** `frontend/src/app/pages/riftbound/builder/riftbound-builder.component.ts` (`save()`, ~L2389)

**Síntoma:** al pulsar "Crear mazo" sin sesión aparece *"Las credenciales de autenticación no se proveyeron."*

**Cambio** (se mantiene la opción de armar sin cuenta, pero se guía al usuario):
```ts
save() {
  if (!this.auth.isLoggedIn()) {           // inyectar AuthService si no está
    this.saveDraft();                       // conservar lo armado
    this.errors.set(['Inicia sesión para guardar tu mazo. Tu borrador quedará guardado.']);
    this.router.navigate(['/login'], { queryParams: { returnUrl: this.router.url } });
    return;
  }
  // ... resto igual
}
```
Y en el `error:` del subscribe:
```ts
error: (err) => {
  this.saving.set(false);
  const msg = err?.status === 401
    ? 'Tu sesión expiró. Inicia sesión nuevamente para guardar.'
    : (err?.error?.detail || 'Error al guardar.');
  this.errors.set([msg]);
},
```
**Aceptación:**
- Sin sesión, "Crear mazo" lleva a login y al volver el borrador sigue ahí.
- No se muestra ningún texto técnico de DRF.

---

### [x] 1.5 Hero "ShadowForge" cortado en móvil · 🟠 MEDIA
**Archivo:** `frontend/src/app/pages/home/home.component.scss` (~L7, `.hero-title`)

**Cambio:**
```scss
.hero-title {
  font-size: clamp(2rem, 9vw, 3rem);
  overflow-wrap: anywhere;

  .icon { font-size: clamp(1.75rem, 8vw, 2.5rem); }
}
```
**Aceptación:** a 320, 360 y 375 px el título se ve completo (`h1.scrollWidth <= h1.clientWidth`).

---

### [x] 1.6 Atajo "⌘K" en Windows · 🟢 BAJA
**Archivo:** `frontend/src/app/app.html:94`, `app.ts`

**Cambio:**
```ts
// app.ts
readonly searchShortcut = /Mac|iPhone|iPad/.test(navigator.platform || navigator.userAgent) ? '⌘K' : 'Ctrl K';
```
```html
<kbd class="search-kbd">{{ searchShortcut }}</kbd>
```
**Aceptación:** en Windows se ve "Ctrl K" y en Mac "⌘K".

---

### [x] 1.7 Ctrl+K pierde las primeras teclas · 🟢 BAJA
**Archivo:** `frontend/src/app/app.ts` (L106 y L114: `setTimeout(..., 50)`)

**Causa:** el foco llega 50 ms tarde y lo que se escribe antes se pierde.

**Cambio:** enfocar apenas se renderice el input, sin demora fija:
```ts
// opción A: autofocus en el template
<input #globalSearchInput autofocus ... />

// opción B: afterNextRender (Angular 17+)
openSearch() {
  this.searchOpen.set(true);
  afterNextRender(() => this.globalSearchInput?.nativeElement?.focus(), { injector: this.injector });
}
```
**Aceptación:** con Ctrl+K y tipeo inmediato de "vampiro" se capturan las 7 letras.

---

## Sprint 2 — Backend / reglas

### [x] 2.1 Header con sesión: botones fuera de pantalla entre 861 y ~1350 px · 🔴 ALTA
**Archivo:** `frontend/src/app/app.scss` (`.navbar-links` L59, `.navbar-actions` L278, breakpoint único L655 a 860 px)

**Medido:** con sesión, el navbar mide 1348 px.
- A 1280 px quedan ocultos Tema y Cambio de juego.
- A 1024 px quedan ocultos además Notificaciones, **Menú de usuario (cerrar sesión)** y Recarga.

**Cambio** (dos niveles):
```scss
// 1) Laptop: ocultar etiquetas de texto de los links, dejar sólo iconos
@media (max-width: 1400px) {
  .navbar-links a .label,            // ajustar al selector real del texto del link
  .cmd-search-bar .search-placeholder,
  .cmd-search-bar .search-kbd { display: none; }
  .cmd-search-bar { min-width: 0; padding-inline: .6rem; }
  .navbar-links a { padding-inline: .5rem; }
}

// 2) Tablet horizontal: pasar a nav móvil antes de que se rompa
@media (max-width: 1100px) {
  .navbar .navbar-links { display: none; }
  // habilitar bottom-nav / menú hamburguesa igual que en <=860px
}
```
> Alternativa más limpia: dejar en el header sólo Cartas · Mazos · Constructor · Carpeta y agrupar Tiendas, Banlist, Wordle y Equipos en un menú "Más ▾".

Si los links no tienen un `<span class="label">`, hay que envolver el texto en `app.html`.

**Aceptación:** a 1024, 1100, 1280, 1366 y 1440 px, con y sin sesión:
```js
document.querySelector('.navbar').scrollWidth <= document.documentElement.clientWidth
```
y el menú de usuario siempre se puede pulsar.

**Verificar** (en consola, por cada ancho):
```js
[...document.querySelectorAll('.navbar button, .navbar a')]
  .filter(b => b.getBoundingClientRect().right > innerWidth)
  .map(b => b.getAttribute('aria-label') || b.innerText)   // debe ser []
```

---

### [x] 2.2 La API de MyL acepta mazos que rompen las reglas · 🔴 ALTA
**Archivo:** `backend/decks/serializers.py` → `DeckCreateSerializer.validate()` (~L109)

**Reproducido:** `POST /api/decks/my/` aceptó un mazo **público** con 60 copias de una carta.

**Criterio:** validar en el servidor **sólo los límites duros**, que nunca son válidos (ni siquiera en un borrador). Que el mazo esté incompleto (<50) se sigue permitiendo.

**Cambio** (agregar a `validate`, después de la validación de formato):
```python
from collections import defaultdict
import unicodedata, re
from cards.models import BanlistEntry

MAIN_MAX, SIDE_MAX, DEFAULT_COPIES = 50, 15, 3

def _norm(name: str) -> str:
    n = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", n)

# dentro de validate():
main_total = sum(e["quantity"] for e in entries_data if not e.get("is_sideboard"))
side_total = sum(e["quantity"] for e in entries_data if e.get("is_sideboard"))
errors = []
if main_total > MAIN_MAX:
    errors.append(f"El mazo principal tiene {main_total} cartas (máximo {MAIN_MAX}).")
if side_total > SIDE_MAX:
    errors.append(f"El sidedeck tiene {side_total} cartas (máximo {SIDE_MAX}).")

sub_format = attrs.get("sub_format") or getattr(self.instance, "sub_format", "racial")
ban = {
    _norm(b.card_name): b
    for b in BanlistEntry.objects.filter(format_code=current_fmt, sub_format=sub_format)
}

copies = defaultdict(int)   # por nombre normalizado, sumando main + side y variantes
names = {}
unique = set()
for e in entries_data:
    card = e["card"]
    key = _norm(card.name)
    copies[key] += e["quantity"]
    names[key] = card.name
    if (card.ability or "").strip().lower().startswith("única"):
        unique.add(key)

for key, qty in copies.items():
    limit = 1 if key in unique else DEFAULT_COPIES
    b = ban.get(key)
    if b:
        limit = min(limit, b.max_copies)   # 0 = baneada
    if qty > limit:
        errors.append(
            f"'{names[key]}' está baneada." if limit == 0
            else f"'{names[key]}': {qty} copias (máximo {limit})."
        )

if errors:
    raise serializers.ValidationError({"entries": errors})
```
**Además:**
- [x] `DeckEntrySerializer`: `quantity` con `min_value=1` (hoy acepta 0).
- [x] `create()`/`update()` dentro de `transaction.atomic()` para que un error a mitad de camino no deje el mazo sin entradas.
- [x] Revisar que la restricción racial del frontend (`isCardAllowedByRace`) se replique aquí, o documentar por qué no.

**Tests** (en `backend/decks/tests_rule_gap.py`):
- 4 copias de una carta normal → 400
- 2 copias de una "Única" → 400
- 51 en main → 400; 16 en side → 400
- 1 copia de una baneada → 400
- mazo de 10 cartas válido → 201 (los borradores siguen funcionando)

**Aceptación:** no se puede crear ni editar vía API un mazo que el constructor no permitiría armar.

---

### [x] 2.3 La API de Riftbound acepta 99 copias · 🔴 ALTA
**Archivo:** `backend/riftbound/serializers.py` → `RiftboundDeckSerializer` (L156). Ya existe `riftbound/validation.py` con las reglas.

**Cambio:** agregar un `validate()` con los límites duros (copias y tamaños máximos) y reutilizar las constantes de `validation.py`:
```python
from collections import defaultdict
from django.db import transaction
from .validation import MAX_COPIES_DEFAULT, RULES_EXACT, RULES_OPTIONAL_EXACT

def validate(self, attrs):
    attrs = super().validate(attrs)
    entries = attrs.get("entries")
    if entries is None:
        return attrs
    errors = []
    copies, zone_totals = defaultdict(int), defaultdict(int)
    for e in entries:
        if e["quantity"] < 1:
            errors.append("La cantidad debe ser al menos 1.")
        zone_totals[e["zone"]] += e["quantity"]
        if e["zone"] != "rune":                       # las runas no cuentan para copias
            copies[e["card"].name] += e["quantity"]
    for name, q in copies.items():
        if q > MAX_COPIES_DEFAULT:
            errors.append(f"'{name}': {q} copias (máximo {MAX_COPIES_DEFAULT}).")
    for zone, maxq in {**RULES_EXACT, **RULES_OPTIONAL_EXACT}.items():
        if zone_totals[zone] > maxq:                  # máximo; el mínimo sigue siendo informativo
            errors.append(f"Zona {zone}: {zone_totals[zone]} cartas (máximo {maxq}).")
    if errors:
        raise serializers.ValidationError({"entries": errors})
    return attrs
```
Envolver `create()` y `update()` con `@transaction.atomic`.
> Revisa en `validation.py` cómo cuenta hoy las copias (por `card_id` o por nombre) y usa **la misma** regla en los dos lados.

**Tests:** agregar en `riftbound/tests_validation.py` los casos de 4 copias → 400, 41 en main → 400 y 20 en main → 201.

---

### [x] 2.4 SQLite "database is locked" (500 intermitente) · 🟠 MEDIA
**Archivo:** `backend/backend/settings.py` L166

**Cambio mínimo:**
```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        "OPTIONS": {
            "timeout": 20,
            "transaction_mode": "IMMEDIATE",   # Django 5.1+
            "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;",  # Django 5.1+
        },
    }
}
```
**Largo plazo:** si producción (PythonAnywhere) usa SQLite, evaluar migrar a MySQL, que PythonAnywhere ofrece incluido.

**Aceptación:** con escrituras simultáneas (tests + navegación) no aparecen 500 por lock.

---

## Sprint 3 — Visual / UX

### [x] 3.1 Modo claro: textos ilegibles · 🔴 ALTA
**Causa raíz:** hay colores escritos a mano en SCSS de página, a veces con `!important`, que le ganan a `body.light-theme` en `frontend/src/styles.scss` (L76 y L640).

**Casos medidos y dónde:**

| Página | Elemento | Contraste | Archivo |
|---|---|---|---|
| `/decks` | título "Mazos" `#f2f6ff !important` | 1.04:1 | `pages/deck-list/deck-list.component.scss` L5-13 |
| `/banlist` | `.lead` `#d8d8e0` | 1.26:1 | `pages/banlist-article/banlist-article.component.scss` L37-40 |
| `/banlist` | links `#FFBD39`, tarjetas de stats oscuras | 1.49:1 | mismo archivo |
| Constructor MyL | inputs con fondo `rgb(18,18,23)`, label `#555` | 2.5:1 | `pages/deck-builder/deck-builder.component.scss` |
| `/cards` | chips de tipo y footer `#94A3B8` sobre blanco | 2.56:1 | `card-list` scss + `app.scss` footer |

**Cambio:**
1. Pasar esos colores a variables CSS que ya existen (`--ui-text`, `--ui-text-muted`, `--ui-accent`…) o crearlas en `:root` y `body.light-theme`:
   ```scss
   // deck-list.component.scss
   .myl-page-title {
     color: var(--ui-text);
     -webkit-text-fill-color: currentColor;
     background: none;
   }
   // banlist-article.component.scss
   .lead { color: var(--ui-text-muted); }
   ```
2. Quitar los `!important` innecesarios en SCSS de componentes.
3. Links de acento en modo claro: usar un ámbar oscuro (`#B45309`, contraste ≥4.5 sobre `#f0f2f5`).
4. Buscar otros colores fijos claros:
   ```bash
   grep -rn "#f2f6ff\|#d8d8e0\|#e[0-9a-f]e[0-9a-f]e[0-9a-f]\b" frontend/src/app --include=*.scss
   ```

**Plan B:** si no hay tiempo, ocultar el toggle de modo claro hasta pulirlo.

**Aceptación:**
- En modo claro, `/`, `/cards`, `/decks`, `/banlist` y `/builder/new/imp` no tienen textos con contraste <4.5 (normales) ni <3 (grandes).
- Inputs y tarjetas se ven claros.

---

### [x] 3.2 Catálogo: estado vacío y de error · 🟠 MEDIA
**Archivo:** `frontend/src/app/pages/card-list/card-list.component.{ts,html}`

**Cambio TS:**
```ts
loadError = false;
// en next: this.loadError = false;
// en error:
error: () => { this.loading = false; this.loadError = true; this.hasMore = false; this.cdr.detectChanges(); }

clearFilters() {
  this.search = ''; this.selectedEdition = ''; this.selectedType = '';
  this.selectedRace = ''; this.selectedRarity = '';
  this.reloadCards();
}
```
**Cambio HTML** (debajo de la grilla):
```html
@if (!loading && loadError) {
  <div class="empty-state">
    <p>No pudimos cargar las cartas.</p>
    <button (click)="reloadCards()">Reintentar</button>
  </div>
} @else if (!loading && cards.length === 0) {
  <div class="empty-state">
    <p>No encontramos cartas{{ search ? ' para «' + search + '»' : '' }}.</p>
    <button (click)="clearFilters()">Limpiar filtros</button>
  </div>
}
```
**Aceptación:**
- Al buscar `zzzzqqq` aparece el mensaje con el botón "Limpiar filtros".
- Si la API falla, aparece "Reintentar".

---

### [x] 3.3 Catálogo: respuestas fuera de orden y `page=2` con 0 resultados · 🟠 MEDIA
**Archivo:** `frontend/src/app/pages/card-list/card-list.component.ts` (`loadCards`, L114)

**Causa:** al tipear rápido, las requests anteriores no se cancelan. Una respuesta vieja pisa `cards`, `totalCards` y `hasMore`: el contador queda desfasado y se pide `page=2` de una búsqueda sin resultados.

**Cambio:**
```ts
private cardsSub?: Subscription;

loadCards(append = false) {
  this.cardsSub?.unsubscribe();            // cancela la request previa
  this.loading = true;
  this.cardsSub = this.cardService.getCards({ /* ...igual... */ }).subscribe({ /* ...igual... */ });
}

ngOnDestroy() { this.cardsSub?.unsubscribe(); /* ...lo existente... */ }
```
Aplicar el mismo patrón en `riftbound/cards` y en el catálogo del `deck-builder` si cargan igual.

**Aceptación:**
- Al tipear `dragon` → borrar → `zzzz` rápido, el contador final coincide con la última búsqueda.
- No aparecen 404 de `page=2` en la pestaña Network.

---

### [x] 3.4 Constructor MyL: el "+" no se ve y el `aria-label` está invertido · 🟢 BAJA
**Archivo:** `frontend/src/app/pages/deck-builder/deck-builder.component.html` (L300-358 y L568)

**Cambios:**
- `aria-label` dinámico según el estado:
  ```html
  [attr.aria-label]="isSelectorOpen(card.id, 'main') ? 'Cerrar selector de mazo principal' : 'Agregar al mazo principal'"
  ```
  (lo mismo para `side`)
- Texto del estado vacío acorde a la UI real:
  ```html
  <p>Pulsa <strong>M</strong> (mazo) o <strong>S</strong> (side) en una carta del catálogo para agregarla.</p>
  ```
- Opcional: un clic en la imagen de la carta agrega 1 copia al main directamente.

---

### [x] 3.5 Badge "Formato Válido" con 0/50 · 🟢 BAJA
**Archivo:** `deck-builder.component.html` (badge junto a "Nuevo Mazo")

**Cambio:** tres estados.
- `formatViolations.length > 0` → 🔴 "Fuera de formato"
- `totalDeckCards < 50` → 🟡 "Incompleto ({{totalDeckCards}}/50)"
- si no → 🟢 "Formato válido"

---

### [x] 3.6 Aviso al publicar un mazo incompleto · 🟢 BAJA
**Archivo:** `deck-builder.component.ts` (`saveDeck`, ~L1454)

**Cambio:** si `isPublic && totalDeckCards < 50`, pedir confirmación: *"Tu mazo tiene X/50 cartas. ¿Publicarlo igual o guardarlo como privado?"*.

---

### [x] 3.7 Placeholder del catálogo truncado en móvil · 🟢 BAJA
**Archivo:** `card-list.component.html` (input "Buscar por nombre... ( / para enfocar)")

**Cambio:** placeholder corto `Buscar carta…` y la pista `/` sólo en desktop:
```html
[placeholder]="isTouch ? 'Buscar carta…' : 'Buscar por nombre… ( / para enfocar)'"
```
```ts
isTouch = matchMedia('(pointer: coarse)').matches;
```

---

### [x] 3.8 Páginas "no encontrado" sin salida · 🟢 BAJA
**Archivos:** `pages/deck-view/*`, `pages/riftbound/card-detail/*`, `pages/riftbound/deck-view/*`, `app.routes.ts`

**Cambios:**
- [x] Mazo o carta inexistente: tarjeta centrada con ícono, texto y botón "Volver a mazos" / "Ver cartas". Título: `No encontrado | ShadowForge`.
- [x] Crear `pages/not-found` y cambiar `{ path: '**', redirectTo: '' }` por `{ path: '**', title: 'Página no encontrada | ShadowForge', loadComponent: ... }`.

---

### [x] 3.9 `/decks/compare` sin `?ids=` · 🟢 BAJA
**Archivo:** `frontend/src/app/pages/compare-decks/compare-decks.component.ts` L76-84

**Cambio:** en vez de mostrar el error, cargar "Mis mazos" con checkboxes (mínimo 2) y un botón "Comparar" que navegue a `?ids=a,b`. Como mínimo: texto + link "Elige mazos desde Mis mazos".

---

### [x] 3.10 Avatar de Google roto en `/tiendas` · 🟢 BAJA
**Archivo:** `pages/stores-index/*.html` (y `riftbound/tiendas`)

**Cambio:**
```html
@if (store.avatar && !avatarFailed[store.id]) {
  <img [src]="store.avatar" [alt]="store.name" referrerpolicy="no-referrer"
       (error)="avatarFailed[store.id] = true" />
} @else {
  <span class="avatar-fallback">{{ store.name[0] | uppercase }}</span>
}
```
> `referrerpolicy="no-referrer"` suele evitar el 403/429 de `lh3.googleusercontent.com`.

---

## Sprint 4 — Mejoras

- [x] **4.1 Títulos uniformes:** usar siempre `Sección | ShadowForge`. Quitar el `setTitle` de `card-list.component.ts:79`, que pisa el título SEO de la ruta, y revisar `deck-view`, `riftbound-deck-view` y `riftbound-home`.
- [ ] **4.2 Portada automática:** si `cover_card` es null, usar el oro inicial o la primera carta del main, tanto en `deck-view` como en las tarjetas de `/decks`.
- [ ] **4.3 Filtros del catálogo en móvil:** a ≤768 px, colapsar los 4 selects en un botón "Filtros (n)" que abra un drawer, igual que el `filter-drawer-btn` del constructor.
- [ ] **4.4 Accesibilidad:**
  - `<h1>` en `/login` y `/register` (hoy usan `h2`).
  - `<label for>` o `aria-label` en los inputs de `/cards`, `/tiendas` y `/riftbound/cards`.
  - Nombre accesible en el botón sin texto de `/banlist`.
  - Tamaño táctil mínimo de 44 px en móvil para botones de `/banlist` y `/riftbound/builder`.
  - Marcar "Más" como activo en el bottom-nav cuando la ruta pertenece a ese menú.
- [ ] **4.5 Rendimiento del builder de Riftbound:** 191 `<img>` y sólo 20 lazy.
  - Agregar `loading="lazy"` y `decoding="async"` a todas.
  - `aspect-ratio: 5 / 7` en el contenedor de carta, para evitar CLS.
  - Evaluar paginar o virtualizar (`@angular/cdk/scrolling`).
- [x] **4.6 Fechas legibles:** en `/banlist`, "Publicado el 2026-05-03" → `{{ date | date:'d \'de\' MMMM \'de\' y':'':'es' }}`.
- [ ] **4.7 Seguridad y config** (`backend/backend/settings.py`):
  - L110: `DEBUG` por defecto `False` → `os.environ.get("DJANGO_DEBUG", "False")`, y definir `DJANGO_DEBUG=True` en local.
  - L219: `ACCESS_TOKEN_LIFETIME` de 7 días a 30–60 min; `REFRESH_TOKEN_LIFETIME` de 365 a 30 días, con `ROTATE_REFRESH_TOKENS=True` y `BLACKLIST_AFTER_ROTATION=True`. El interceptor ya maneja el refresh.
- [ ] **4.8 Limpieza:**
  - Mover `backend/test_tcg.py` a `backend/scripts/tcg_probe.py`, porque hace requests reales a TCGplayer cada vez que corre `manage.py test`.
  - Normalizar nombres de cartas en minúsculas (ej. "colmillo de vampiro") con un script o management command.
  - Inicializar git en la raíz y agregar a `.gitignore`: `tmp_*`, `*_mapping.json`, `cartas por subir*/`, `db.sqlite3`, `.env_*`.

---

## Checklist de regresión (repetir al cerrar cada sprint)

```bash
# Backend
cd Proyecto-deckshado/backend && python manage.py test

# Frontend
cd Proyecto-deckshado/frontend && npx ng test --watch=false && npx ng build
```

**Manual:**
- [ ] `/cards`: buscar `dragon`, `Dragón`, `(`, `zzzz` → resultados correctos, sin 500 y con estado vacío.
- [ ] Constructor MyL: Imperio → Racial → Dragón → agregar 4 copias (se frena en 3) → guardar → vista de mazo.
- [ ] Builder Riftbound sin sesión → "Crear mazo" → redirige a login y el borrador se conserva.
- [ ] Header a 1024, 1280, 1366 y 1440 px con sesión → todos los botones visibles.
- [ ] Modo claro en `/`, `/cards`, `/decks`, `/banlist` y constructor → todo legible.
- [ ] Móvil 375 px: home (título completo), `/cards`, `/banlist`, `/riftbound/builder` → sin scroll horizontal.
- [ ] Sin sesión: `/profile`, `/builder`, `/carpeta` → redirigen a `/login`.
- [ ] API: `POST /api/decks/my/` con 60 copias → 400; `POST /api/riftbound/decks/` con 99 copias → 400.
- [ ] Consola del navegador sin errores rojos al navegar las rutas principales.
