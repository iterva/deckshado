import {
  AfterViewInit,
  Component,
  ElementRef,
  HostListener,
  Injector,
  NgZone,
  OnDestroy,
  OnInit,
  ViewChild,
  afterNextRender,
  computed,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { RiftboundService } from '../../../services/riftbound.service';
import { AuthService } from '../../../services/auth.service';
import { ConfirmDialogService } from '../../../services/confirm-dialog.service';
import {
  RiftboundCard, RiftboundCardLite, RiftboundDeck, RiftboundDeckEntry,
  RiftboundZone, RIFTBOUND_ZONE_RULES, RIFTBOUND_ZONE_LABELS, RiftboundColor,
  RIFTBOUND_COLORS,
} from '../../../models/riftbound';
import { TcgPriceComponent } from '../../../components/tcg-price/tcg-price.component';
import { IconComponent } from '../../../components/icon/icon.component';
import { CardZoom } from '../../../services/card-zoom';

interface BuilderEntry {
  card: RiftboundCardLite;
  quantity: number;
  zone: RiftboundZone;
}

type CardImageLike = {
  id?: number | null;
  card_number?: string | null;
  image?: string | null;
  cdn_image_url?: string | null;
  image_url?: string | null;
  image_url_small?: string | null;
};

const COLORS: { code: RiftboundColor; label: string; hex: string }[] = RIFTBOUND_COLORS;

const TYPES = [
  { code: 'unit', label: 'Unidad' },
  { code: 'spell', label: 'Hechizo' },
  { code: 'champion', label: 'Champion' },
  { code: 'legend', label: 'Legend' },
  { code: 'gear', label: 'Gear' },
  { code: 'battlefield', label: 'Battlefield' },
  { code: 'rune', label: 'Runa' },
  { code: 'other', label: 'Otro' },
];

const ZONE_TARGETS: Record<RiftboundZone, RiftboundZone | 'auto'> = {
  main: 'main', side: 'side', rune: 'rune', champion: 'champion', bg: 'bg',
};

/** Orden por tipo para organizar el mazo: unidad → hechizo → equipo → resto. */
const TYPE_ORDER: Record<string, number> = {
  unit: 1, spell: 2, gear: 3,
  champion: 4, legend: 5, rune: 6, battlefield: 7,
};
function typeRank(t?: string): number {
  return TYPE_ORDER[(t ?? '').toLowerCase()] ?? 99;
}

@Component({
  selector: 'app-riftbound-builder',
  standalone: true,
  imports: [CommonModule, FormsModule, TcgPriceComponent, IconComponent],
  template: `
    <!-- Mobile View Switcher (Fixed Bottom Tab Bar) -->
    <div class="mobile-builder-switcher" role="tablist" aria-label="Vista del constructor">
      <button
        type="button"
        class="mb-tab"
        [class.active]="activeMobileTab() === 'browser'"
        (click)="setMobileTab('browser')"
      >
        <app-icon name="library" [size]="16"></app-icon>
        <span>Explorar Cartas</span>
      </button>
      <button
        type="button"
        class="mb-tab"
        [class.active]="activeMobileTab() === 'deck'"
        (click)="setMobileTab('deck')"
      >
        <app-icon name="layers" [size]="16"></app-icon>
        <span>Mazo Activo ({{ totalEntries() }})</span>
      </button>
    </div>

    <div class="builder-layout" [attr.data-mobile-tab]="activeMobileTab()">
      <!-- ══════════════════════════════════════════════════════ -->
      <!-- LEFT PANEL (65%): Card Browser                        -->
      <!-- ══════════════════════════════════════════════════════ -->
      <div class="card-browser" [class.mobile-hidden]="activeMobileTab() === 'deck'" [class.filters-modal-open]="filtersOpen()">
        <div class="browser-head">
          <div class="browser-title-wrap">
            <h2>Cartas Riftbound</h2>
            <span class="format-badge">{{ totalCount() }} disponibles</span>
          </div>
        </div>

        <div class="browser-filters">
          <div class="search-row">
            <div class="search-input-row">
              <select class="search-mode-select" aria-label="Modo de búsqueda" title="Dónde buscar"
                      [ngModel]="searchMode" (ngModelChange)="setMode($event)">
                <option value="name">Nombre</option>
                <option value="ability">Habilidad</option>
                <option value="all">Todo</option>
              </select>
              <div class="search-field">
                <app-icon name="search" [size]="15" class="search-input-icon"></app-icon>
                <input
                type="search"
                aria-label="Buscar cartas"
                [(ngModel)]="searchQuery"
                (ngModelChange)="onSearchInput()"
                [placeholder]="searchMode === 'ability' ? 'Buscar habilidad…' : (searchMode === 'all' ? 'Buscar nombre o habilidad…' : 'Buscar nombre o número…')" />
              </div>
              <button class="search-btn" (click)="reload()" title="Buscar">
                <app-icon name="search" [size]="14"></app-icon>
              </button>
              <button type="button" class="filters-toggle-btn" [class.active]="filtersOpen()"
                      (click)="filtersOpen.set(!filtersOpen())"
                      [attr.aria-expanded]="filtersOpen()" aria-label="Mostrar filtros">
                <app-icon name="filter" [size]="14"></app-icon>
                <span class="ft-text">Filtros</span>
                @if (activeFilterCount() > 0) { <span class="filter-badge">{{ activeFilterCount() }}</span> }
              </button>
              <div class="zoom-controls" role="group" aria-label="Tamaño de las cartas">
                <button type="button" class="zoom-btn" (click)="zoomCards(-1)"
                        [disabled]="!cardZoom.canZoomOut()"
                        aria-label="Achicar cartas (más por fila)" title="Achicar cartas">
                  <app-icon name="zoom-out" [size]="15"></app-icon>
                </button>
                <button type="button" class="zoom-btn" (click)="zoomCards(1)"
                        [disabled]="!cardZoom.canZoomIn()"
                        aria-label="Agrandar cartas (menos por fila)" title="Agrandar cartas">
                  <app-icon name="zoom-in" [size]="15"></app-icon>
                </button>
              </div>
            </div>
          </div>

          @if (filtersOpen()) {
            <div class="filters-backdrop" (click)="filtersOpen.set(false)"></div>
            <div class="filters-panel" role="dialog" aria-label="Filtros de cartas">
              <div class="filters-panel-head">
                <h3>Filtros</h3>
                <button type="button" class="close-btn" (click)="filtersOpen.set(false)" aria-label="Cerrar filtros">✕</button>
              </div>
              <div class="filters-panel-body">
                <div class="filter-group">
                  <label class="filter-label">Tipo de carta</label>
                  <div class="type-chips" role="group" aria-label="Filtrar por tipo">
                    <button type="button"
                            class="type-chip-btn"
                            [class.active]="!typeFilter"
                            (click)="setType('')">Todos</button>
                    @for (t of types; track t.code) {
                      <button type="button"
                              class="type-chip-btn"
                              [class.active]="typeFilter === t.code"
                              (click)="setType(t.code)">{{ t.label }}</button>
                    }
                  </div>
                </div>

                <div class="filter-group">
                  <label class="filter-label">Colores</label>
                  <div class="color-row">
                    @for (c of colors; track c.code) {
                      <button type="button"
                              class="color-chip"
                              [class.active]="selectedColors().has(c.code)"
                              [style.--c]="c.hex"
                              (click)="toggleColor(c.code)">{{ c.label }}</button>
                    }
                    @if (selectedColors().size > 0) {
                      <button type="button" class="clear-colors" (click)="clearColors()">Limpiar</button>
                    }
                  </div>
                </div>

                <div class="filter-group">
                  <label class="filter-label">Set / Rareza</label>
                  <div class="filter-row">
                    <div class="multi-filter">
                      <label class="filter-label">Set</label>
                      <select aria-label="Filtrar por set" [(ngModel)]="setFilter" (ngModelChange)="page.set(1); reload()">
                        <option value="">Todos los sets</option>
                        @for (s of sets(); track s.code) {
                          <option [value]="s.code">{{ s.code }} — {{ s.name }}</option>
                        }
                      </select>
                    </div>

                    <div class="multi-filter">
                      <label class="filter-label">Rareza</label>
                      <select aria-label="Filtrar por rareza" [(ngModel)]="rarityFilter" (ngModelChange)="page.set(1); reload()">
                        <option value="">Todas</option>
                        <option value="common">Common</option>
                        <option value="uncommon">Uncommon</option>
                        <option value="rare">Rare</option>
                        <option value="epic">Epic</option>
                        <option value="legendary">Legendary</option>
                        <option value="champion">Champion</option>
                        <option value="promo">Promo</option>
                      </select>
                    </div>
                  </div>
                </div>

                <div class="filter-group">
                  <label class="filter-label">Estadísticas</label>
                  <div class="filter-row stats-row">
                    <div class="multi-filter">
                      <label class="filter-label">Energía</label>
                      <select aria-label="Filtrar por energía" [(ngModel)]="energyFilter" (ngModelChange)="page.set(1); reload()">
                        <option [ngValue]="null">Cualquiera</option>
                        @for (n of energyBins; track n) {
                          <option [ngValue]="n">{{ n }}</option>
                        }
                      </select>
                    </div>
                    <div class="multi-filter">
                      <label class="filter-label">Power</label>
                      <select aria-label="Filtrar por poder" [(ngModel)]="powerFilter" (ngModelChange)="page.set(1); reload()">
                        <option [ngValue]="null">Cualquiera</option>
                        @for (n of statBins; track n) {
                          <option [ngValue]="n">{{ n }}</option>
                        }
                      </select>
                    </div>
                    <div class="multi-filter">
                      <label class="filter-label">Might</label>
                      <select aria-label="Filtrar por fuerza" [(ngModel)]="mightFilter" (ngModelChange)="page.set(1); reload()">
                        <option [ngValue]="null">Cualquiera</option>
                        @for (n of statBins; track n) {
                          <option [ngValue]="n">{{ n }}</option>
                        }
                      </select>
                    </div>
                  </div>
                </div>
              </div>
              <div class="filters-panel-actions">
                <button type="button" class="btn-clear-all" (click)="clearAllFilters()">Limpiar filtros</button>
                <button type="button" class="btn-apply-all" (click)="filtersOpen.set(false)">Aplicar</button>
              </div>
            </div>
          }
        </div>

        @if (loading()) {
          <p class="muted">Cargando…</p>
        }

        <div class="available-cards" #availableCardsEl
             [class.fixed-columns]="cardZoom.columns() !== null"
             [class.dense-selectors]="cardZoom.isMobile() && (cardZoom.columns() ?? 0) >= 4"
             [class.no-selectors]="cardZoom.isMobile() && (cardZoom.columns() ?? 0) >= 8"
             [style.--card-columns]="cardZoom.columns()">
          @for (card of displayedResults(); track card.id) {
            <div class="mini-card"
                 [class.in-deck]="getQuantityInDeck(card.id) > 0"
                 [class.maxed]="getQuantityInDeck(card.id) >= getMaxCopies(card)"
                 [class.banned]="isBanned(card)"
                 [class.limited]="banStatus(card) === 'limited' || banStatus(card) === 'restricted'"
                 [title]="card.name">
              <div class="img-wrapper" (click)="openPreview(card)">
                @if (cardImageUrl(card); as img) {
                  <img [src]="img" [alt]="card.name" loading="lazy" decoding="async"
                       (error)="onCardImageError(card, $event)" />
                } @else {
                  <div class="img-placeholder">{{ card.card_number }}</div>
                }
                <button type="button" class="eye-btn" aria-label="Ver detalle">
                  <app-icon name="eye" [size]="13"></app-icon>
                </button>
                @if (isBanned(card)) {
                  <span class="ban-badge ban-badge-banned" title="Prohibida en Standard">
                    <app-icon name="ban" [size]="10"></app-icon>
                  </span>
                } @else if (banStatus(card)) {
                  <span class="ban-badge ban-badge-limited" title="Limitada en Standard">
                    <app-icon name="shield-alert" [size]="10"></app-icon>
                  </span>
                }

                <div class="hover-info">
                  <span class="hi-name">{{ card.name }}</span>
                  <div class="hi-meta">
                    <span class="hi-type">{{ typeLabel(card.card_type) }}</span>
                    @if (card.energy !== null && card.energy !== undefined) {
                      <span class="stat-pill cost" title="Energía">{{ card.energy }}</span>
                    }
                    @if (card.might !== null && card.might !== undefined) {
                      <span class="stat-pill damage" title="Fuerza">{{ card.might }}</span>
                    }
                  </div>
                  <span class="hi-num">{{ card.card_number }}</span>
                </div>
              </div>

              <!-- Selectores fuera de .img-wrapper: así el óvalo expandido no se
                   recorta contra el borde redondeado/overflow de la imagen. -->
              <div class="zone-selectors">
                <!-- S (side) — esquina inferior izquierda -->
                @if (canShowMainSide(card)) {
                  <div class="floating-selector zone-side"
                       [class.expanded]="isExpanded(card.id, 'side')"
                       [class.filled]="getQuantityInZone(card.id, 'side') > 0"
                       (click)="$event.stopPropagation()">
                    <button type="button" class="fs-trigger"
                            (click)="toggleSelector(card.id, 'side', $event)"
                            [attr.aria-expanded]="isExpanded(card.id, 'side')"
                            [attr.aria-label]="'Sideboard: ' + getQuantityInZone(card.id, 'side') + ' copias'"
                    >{{ getQuantityInZone(card.id, 'side') > 0 ? getQuantityInZone(card.id, 'side') : 'S' }}</button>
                    <div class="fs-controls">
                      <button type="button" class="fs-tag" (click)="toggleSelector(card.id, 'side', $event)"
                              aria-label="Cerrar selector de side">S</button>
                      <button type="button" class="fs-op minus" (click)="decZone(card, 'side')"
                              [disabled]="getQuantityInZone(card.id, 'side') === 0" aria-label="Quitar del side">−</button>
                      <span class="fs-count" aria-live="polite">{{ getQuantityInZone(card.id, 'side') }}</span>
                      <button type="button" class="fs-op plus" (click)="addToZone(card, 'side')"
                              [disabled]="zoneCount('side') >= rules.side || getNameCount(card.name) >= getMaxCopies(card)"
                              aria-label="Agregar al side">+</button>
                    </div>
                  </div>
                }

                <!-- Zonas dedicadas (rune/champion/battlefield) para cartas sin main/side -->
                @for (z of extraZonesFor(card); track z) {
                  <div class="floating-selector" [class]="'zone-' + z"
                       [class.expanded]="isExpanded(card.id, z)"
                       [class.filled]="getQuantityInZone(card.id, z) > 0"
                       (click)="$event.stopPropagation()">
                    <button type="button" class="fs-trigger"
                            (click)="toggleSelector(card.id, z, $event)"
                            [attr.aria-expanded]="isExpanded(card.id, z)"
                            [attr.aria-label]="labels[z] + ': ' + getQuantityInZone(card.id, z) + ' copias'"
                    >{{ getQuantityInZone(card.id, z) > 0 ? getQuantityInZone(card.id, z) : zoneLetter(z) }}</button>
                    <div class="fs-controls">
                      <button type="button" class="fs-tag" (click)="toggleSelector(card.id, z, $event)"
                              aria-label="Cerrar selector">{{ zoneLetter(z) }}</button>
                      <button type="button" class="fs-op minus" (click)="decZone(card, z)"
                              [disabled]="getQuantityInZone(card.id, z) === 0" aria-label="Quitar">−</button>
                      <span class="fs-count" aria-live="polite">{{ getQuantityInZone(card.id, z) }}</span>
                      <button type="button" class="fs-op plus" (click)="addToZone(card, z)"
                              [disabled]="!canAddToAuto(card, z)" aria-label="Agregar">+</button>
                    </div>
                  </div>
                }

                <!-- M (main) — esquina inferior derecha -->
                @if (canShowMainSide(card)) {
                  <div class="floating-selector zone-main"
                       [class.expanded]="isExpanded(card.id, 'main')"
                       [class.filled]="getQuantityInZone(card.id, 'main') > 0"
                       (click)="$event.stopPropagation()">
                    <button type="button" class="fs-trigger"
                            (click)="toggleSelector(card.id, 'main', $event)"
                            [attr.aria-expanded]="isExpanded(card.id, 'main')"
                            [attr.aria-label]="'Mazo principal: ' + getQuantityInZone(card.id, 'main') + ' copias'"
                    >{{ getQuantityInZone(card.id, 'main') > 0 ? getQuantityInZone(card.id, 'main') : 'M' }}</button>
                    <div class="fs-controls">
                      <button type="button" class="fs-tag" (click)="toggleSelector(card.id, 'main', $event)"
                              aria-label="Cerrar selector de mazo principal">M</button>
                      <button type="button" class="fs-op minus" (click)="decZone(card, 'main')"
                              [disabled]="getQuantityInZone(card.id, 'main') === 0" aria-label="Quitar del mazo principal">−</button>
                      <span class="fs-count" aria-live="polite">{{ getQuantityInZone(card.id, 'main') }}</span>
                      <button type="button" class="fs-op plus" (click)="addToZone(card, 'main')"
                              [disabled]="zoneCount('main') >= rules.main || getNameCount(card.name) >= getMaxCopies(card)"
                              aria-label="Agregar al mazo principal">+</button>
                    </div>
                  </div>
                }
              </div>
            </div>
          }
        </div>

        @if (!loading() && displayedResults().length === 0) {
          <p class="muted center">Sin resultados.</p>
        }

        @if (hasMore()) {
          <div #cardsSentinel class="infinite-sentinel" aria-hidden="true"></div>
        }
        @if (loading() && displayedResults().length > 0) {
          <p class="muted center">Cargando más...</p>
        }
        @if (!hasMore() && !loading() && displayedResults().length > 0) {
          <p class="muted center" style="margin-top: .9rem;">— Fin de cartas —</p>
        }
      </div>

      <!-- ══════════════════════════════════════════════════════ -->
      <!-- RIGHT PANEL (35%): Deck Panel                          -->
      <!-- ══════════════════════════════════════════════════════ -->
      <div class="deck-panel" [class.mobile-visible]="showDeckPanel()" [class.mobile-hidden]="activeMobileTab() === 'browser'">
        <div class="deck-header">
          <div class="deck-header-info">
            <h1>{{ deckId() ? 'Editar Mazo' : 'Nuevo Mazo' }}</h1>
            <span class="legal-badge ok">Riftbound Standard</span>
          </div>

          <div class="deck-header-actions">
            @if (!deckId() && totalEntries() > 0) {
              <button class="icon-btn" (click)="discardDraft()" title="Descartar borrador local" aria-label="Descartar borrador">
                <app-icon name="trash-2" [size]="16"></app-icon>
              </button>
            }
            <button class="icon-btn" (click)="openDeckPreview()" [disabled]="totalEntries() === 0" title="Previsualizar mazo">
              <app-icon name="eye" [size]="16"></app-icon>
            </button>
          </div>
        </div>

        <div class="deck-panel-scroll">
        <!-- Champion Legend del mazo -->
        <div class="legend-banner" [class.empty]="!chosenLegend()">
          @if (chosenLegend(); as L) {
            <img [src]="cardImageUrl(L)" [alt]="L.name" class="legend-img"
                 (error)="onCardImageError(L, $event)" />
            <div class="legend-info">
              <span class="legend-tag">CHAMPION LEGEND</span>
              <strong>{{ L.name }}</strong>
              <div class="legend-colors">
                @for (c of (L.colors || []); track c) {
                  <span class="color-dot" [style.background]="colorHex(c)" [title]="c"></span>
                }
              </div>
            </div>
            <div class="legend-actions">
              <button class="legend-btn" (click)="changeLegend()">Cambiar</button>
              <button class="legend-btn"
                      [class.locked]="lockColorsToLegend()"
                      (click)="toggleLockColors()"
                      [title]="lockColorsToLegend() ? 'Filtros bloqueados a colores del legend' : 'Filtros libres'">
                <app-icon [name]="lockColorsToLegend() ? 'shield' : 'shield-alert'" [size]="12"></app-icon>
                {{ lockColorsToLegend() ? 'Colores' : 'Libres' }}
              </button>
            </div>
          } @else {
            <button class="choose-legend-btn" (click)="openLegendPicker()">
              <app-icon name="star-fill" [size]="16"></app-icon>
              <span>Elige tu Champion Legend</span>
            </button>
          }
        </div>

        <!-- Champion Unit designado -->
        @if (chosenLegend()) {
          <div class="legend-banner cu-banner" [class.empty]="!championUnitData()">
            @if (championUnitData(); as U) {
              <img [src]="cardImageUrl(U)" [alt]="U.name" class="legend-img"
                   (error)="onCardImageError(U, $event)" />
              <div class="legend-info">
                <span class="legend-tag cu-tag">CHAMPION UNIT</span>
                <strong>{{ U.name }}</strong>
                <span class="cu-num">{{ U.card_number }}</span>
              </div>
              <div class="legend-actions">
                <button class="legend-btn" (click)="changeChampionUnit()">Cambiar</button>
                <button class="legend-btn" (click)="clearChampionUnit()" title="Quitar designación">✕</button>
              </div>
            } @else {
              <button class="choose-legend-btn cu-choose" (click)="openChampionUnitPicker()">
                <app-icon name="swords" [size]="16"></app-icon>
                <span>Elige tu Champion Unit @if (championName(); as cn) { ({{ cn }}) }</span>
              </button>
            }
          </div>
        }

        <div class="deck-info-box">
          <div class="form-group floating">
            <label for="rb-deck-name">Nombre del mazo (Título)</label>
            <input id="rb-deck-name" type="text" [(ngModel)]="deckName" placeholder="Ej: Jinx agresivo" />
          </div>

          <div class="form-group floating">
            <label for="rb-deck-description">Descripción (opcional)</label>
            <textarea id="rb-deck-description" rows="3" [(ngModel)]="description" placeholder="Breve descripción (opcional)..."></textarea>
          </div>

          <label class="checkbox-label">
            <input type="checkbox" [(ngModel)]="isPublic" />
            <span>Mazo público</span>
          </label>
        </div>

        <!-- Resumen / progreso -->
        <div class="zones-summary">
          @for (z of zones; track z) {
            <div class="zone-pill" [class.ok]="isZoneOk(z)" [class.bad]="!isZoneOk(z) && zoneCount(z) > 0">
              <span class="zp-label">{{ zoneShortLabel(z) }}</span>
              <span class="zp-count">{{ zoneCount(z) }}/{{ rules[z] }}</span>
            </div>
          }
        </div>

        <!-- Curva de coste (energía del main) -->
        <div class="cost-curve-panel">
          <span class="curve-title">
            <app-icon name="bar-chart-3" [size]="14"></app-icon> Curva de Energía
          </span>
          <div class="cost-curve-bars">
            @for (c of energyBins; track c) {
              <div class="cost-bar" [class.empty]="energyDist()[c] === 0">
                <span class="cost-bar-count">{{ energyDist()[c] || '' }}</span>
                <div class="cost-bar-fill-wrap">
                  <div class="cost-bar-fill"
                       [style.height]="(energyDist()[c] / maxEnergyCount() * 100) + '%'"></div>
                </div>
                <span class="cost-bar-label">{{ c === 8 ? '8+' : c }}</span>
              </div>
            }
          </div>
        </div>

        <!-- Distribución por color -->
        @if (colorDist(); as cd) {
          @if (cd.total > 0) {
            <div class="color-dist">
              <span class="cd-title">Dominios</span>
              <div class="cd-bars">
                @for (c of colors; track c.code) {
                  @if (cd.counts[c.code]) {
                    <span class="cd-pill" [style.--c]="c.hex">
                      {{ c.label }}: <strong>{{ cd.counts[c.code] }}</strong>
                    </span>
                  }
                }
              </div>
            </div>
          }
        }

        <!-- Zonas con sus cartas -->
        @for (z of zones; track z) {
          <div class="zone-section" [class.empty]="entries()[z].length === 0">
            <div class="zone-section-head">
              <span class="zs-title">{{ labels[z] }}</span>
              <span class="zs-count" [class.ok]="isZoneOk(z)">
                {{ zoneCount(z) }}/{{ rules[z] }}
              </span>
            </div>
            @if (entries()[z].length === 0) {
              <p class="zone-empty">Vacío. Añade cartas desde el catálogo.</p>
            }
            @for (e of entries()[z]; track e.card.id) {
              <div class="deck-entry" [class.is-cover]="coverCardId() === e.card.id">
                <button type="button"
                        class="cover-star"
                        [class.active]="coverCardId() === e.card.id"
                        (click)="toggleCover(e.card.id)"
                        [title]="coverCardId() === e.card.id ? 'Portada actual (clic para quitar)' : 'Marcar como portada del mazo'">
                  <app-icon [name]="coverCardId() === e.card.id ? 'star-fill' : 'star'" [size]="14"></app-icon>
                </button>
                @if (cardImageUrl(e.card); as img) {
                  <img [src]="img" [alt]="e.card.name" loading="lazy" decoding="async" (error)="onCardImageError(e.card, $event)" />
                } @else {
                  <div class="entry-img-fallback">{{ e.card.card_number }}</div>
                }
                <div class="entry-info">
                  <span class="entry-name">{{ e.card.name }}</span>
                  <div class="entry-meta-row">
                    <span class="entry-meta">
                      {{ e.card.card_number }}
                      @if (e.card.energy !== null && e.card.energy !== undefined) { · Energía: {{ e.card.energy }} }
                    </span>
                    <div class="entry-controls">
                      <button class="ctrl-btn" (click)="dec(e)" aria-label="Quitar una copia">−</button>
                      <span class="entry-qty">{{ e.quantity }}</span>
                      <button class="ctrl-btn" (click)="inc(e)"
                              [disabled]="e.quantity >= maxCopiesForEntry(e)" aria-label="Añadir una copia">+</button>
                      <button class="ctrl-btn remove" (click)="remove(e)" aria-label="Eliminar carta del mazo">
                        <app-icon name="trash-2" [size]="13"></app-icon>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            }
          </div>
        }

        @if (errors().length) {
          <div class="errors-box">
            <strong>Hay problemas:</strong>
            <ul>
              @for (err of errors(); track err) { <li>{{ err }}</li> }
            </ul>
          </div>
        }
        </div><!-- /deck-panel-scroll -->

        <div class="action-row">
          <button type="button" class="preview-deck-btn"
                  (click)="openDeckPreview()"
                  [disabled]="totalEntries() === 0">
            <app-icon name="eye" [size]="16"></app-icon>
            <span>Previsualizar</span>
          </button>

          <button class="save-btn" (click)="save()" [disabled]="saving()">
            {{ saving() ? 'Guardando…' : (deckId() ? 'Guardar cambios' : 'Crear mazo') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Modal vista previa del mazo (estilo galería) -->
    @if (showDeckPreview()) {
      <div class="modal-overlay" (click)="closeDeckPreview()">
        <div class="deck-preview-box" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
          <div class="dp-head">
            <div>
              <h2>{{ deckName || 'Mazo Riftbound' }}</h2>
              <p class="muted">{{ totalEntries() }} cartas · {{ deckId() ? 'Editando' : 'Borrador' }}</p>
            </div>
            <button class="dp-close" (click)="closeDeckPreview()" aria-label="Cerrar">
              <app-icon name="x" [size]="18"></app-icon>
            </button>
          </div>
          <div class="dp-body">
            @for (z of zones; track z) {
              @if (entries()[z].length > 0) {
                <section class="dp-section">
                  <h3 class="dp-section-title">
                    {{ labels[z] }}
                    <span class="dp-section-count">{{ zoneCount(z) }}/{{ rules[z] }}</span>
                  </h3>
                  <div class="dp-grid">
                    @for (e of sortedEntries(z); track e.card.id) {
                      <div class="dp-card">
                        <div class="dp-img-wrap">
                          @if (cardImageUrl(e.card); as img) {
                            <img [src]="img" [alt]="e.card.name" loading="lazy" decoding="async" (error)="onCardImageError(e.card, $event)" />
                          } @else {
                            <div class="dp-img-fallback">{{ e.card.card_number }}</div>
                          }
                          <span class="dp-qty"
                                [class.is-single]="e.quantity === 1 && (z === 'champion' || z === 'bg')">
                            @if (e.quantity === 1 && (z === 'champion' || z === 'bg')) {
                              ★
                            } @else {
                              ×{{ e.quantity }}
                            }
                          </span>
                        </div>
                        <div class="dp-name">{{ e.card.name }}</div>
                      </div>
                    }
                  </div>
                </section>
              }
            }
            @if (totalEntries() === 0) {
              <p class="muted center" style="padding:2rem">El mazo está vacío.</p>
            }
          </div>
        </div>
      </div>
    }

    <!-- Modal preview -->
    @if (previewCard(); as pc) {
      <div class="preview-overlay" (click)="closePreview()">
        <div class="preview-panel" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
          <button class="preview-close" (click)="closePreview()" aria-label="Cerrar">
            <app-icon name="x" [size]="18"></app-icon>
          </button>
          @if (previewLoading()) {
            <p class="muted" style="padding:3rem;text-align:center">Cargando…</p>
          } @else if (previewDetail(); as c) {
            <div class="preview-layout">
              <div class="preview-art-col">
                @if (cardImageUrl(c); as img) {
                  <img class="preview-card-img" [src]="img" [alt]="c.name" (error)="onCardImageError(c, $event)" />
                }
              </div>
              <div class="preview-info-col">
                <p class="muted">{{ c.card_number }} · {{ c.set?.name || c.set?.code || '—' }}</p>
                <h3 class="preview-title">{{ c.name }}</h3>
                <div class="preview-meta-badges">
                  @if (c.card_type) { <span class="stat-badge">{{ c.card_type }}</span> }
                  @if (c.rarity) { <span class="stat-badge rarity">{{ c.rarity }}</span> }
                  @if (c.variant) { <span class="stat-badge">{{ c.variant }}</span> }
                  @for (col of c.colors; track col) { <span class="stat-badge" [style.color]="col">{{ col }}</span> }
                  @for (st of c.subtypes; track st) { <span class="stat-badge">{{ st }}</span> }
                </div>
                <div class="preview-stats-row">
                  @if (c.energy != null) {
                    <div class="stat-item stat-energy">
                      <app-icon name="zap" [size]="13"></app-icon>
                      <span class="stat-label">Energy</span>
                      <span class="stat-val">{{ c.energy }}</span>
                    </div>
                  }
                  @if (c.power != null) {
                    <div class="stat-item stat-power">
                      <app-icon name="swords" [size]="13"></app-icon>
                      <span class="stat-label">Power</span>
                      <span class="stat-val">{{ c.power }}</span>
                    </div>
                  }
                  @if (c.might != null) {
                    <div class="stat-item stat-might">
                      <app-icon name="shield" [size]="13"></app-icon>
                      <span class="stat-label">Might</span>
                      <span class="stat-val">{{ c.might }}</span>
                    </div>
                  }
                </div>
                @if (c.description) {
                  <div class="preview-ability-box">
                    <span class="ability-title">Descripción</span>
                    <p class="ability-text">{{ c.description }}</p>
                  </div>
                }
                <div class="preview-market-section">
                  <app-tcg-price [cardName]="c.name" [compact]="false" [showLink]="true"></app-tcg-price>
                </div>
              </div>
            </div>
          }
        </div>
      </div>
    }

    <!-- Modal Legend Picker -->
    @if (showLegendPicker()) {
      <div class="modal-overlay" (click)="closeLegendPicker()">
        <div class="modal legend-picker-box" (click)="$event.stopPropagation()">
          <div class="modal-head">
            <h3><app-icon name="star-fill" [size]="18"></app-icon> Elige tu Champion Legend</h3>
            <button type="button" class="modal-close" (click)="closeLegendPicker()" aria-label="Cerrar">
              <app-icon name="x" [size]="18"></app-icon>
            </button>
          </div>
          <p class="muted" style="margin-bottom: 0.75rem;">Las cartas se filtrarán automáticamente por los colores del legend.</p>
          <input type="search" aria-label="Buscar legend" [ngModel]="legendPickerSearch()" (ngModelChange)="legendPickerSearch.set($event)"
                 placeholder="Buscar por nombre…" class="lp-search" style="width: 100%; padding: 0.5rem; margin-bottom: 1rem; background: rgba(18,18,23,0.8); border: 1px solid var(--ui-border); border-radius: 6px; color: #fff;" />
          <div class="lp-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 0.75rem; max-height: 60vh; overflow-y: auto;">
            @for (L of filteredLegends(); track L.id) {
              <button type="button" class="lp-card" (click)="chooseLegend(L)" style="background: rgba(24,24,27,0.7); border: 1px solid var(--ui-border); border-radius: 8px; padding: 0.5rem; cursor: pointer; color: #fff; text-align: center;">
                @if (cardImageUrl(L); as img) {
                  <img [src]="img" [alt]="L.name" loading="lazy" decoding="async" width="250" height="350" style="width: 100%; height: auto; aspect-ratio: 5 / 7; object-fit: cover; border-radius: 4px; background: rgba(255,255,255,0.06);" (error)="onCardImageError(L, $event)" />
                } @else {
                  <div class="lp-img-fallback">{{ L.card_number }}</div>
                }
                <div class="lp-name" style="font-size: 0.78rem; font-weight: 600; margin-top: 0.25rem;">{{ L.name }}</div>
                <div class="lp-code" style="font-size: 0.68rem; opacity: 0.7;">{{ L.card_number }}</div>
              </button>
            }
          </div>
        </div>
      </div>
    }

    <!-- Modal Champion Unit Picker -->
    @if (showChampionUnitPicker()) {
      <div class="modal-overlay" (click)="closeChampionUnitPicker()">
        <div class="modal legend-picker-box" (click)="$event.stopPropagation()">
          <div class="modal-head">
            <h3><app-icon name="swords" [size]="18"></app-icon> Elige tu Champion Unit</h3>
            <button type="button" class="modal-close" (click)="closeChampionUnitPicker()" aria-label="Cerrar">
              <app-icon name="x" [size]="18"></app-icon>
            </button>
          </div>
          <input type="search" aria-label="Buscar campeón" [ngModel]="championUnitPickerSearch()" (ngModelChange)="championUnitPickerSearch.set($event)"
                 placeholder="Buscar por nombre…" class="lp-search" style="width: 100%; padding: 0.5rem; margin-bottom: 1rem; background: rgba(18,18,23,0.8); border: 1px solid var(--ui-border); border-radius: 6px; color: #fff;" />
          <div class="lp-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 0.75rem; max-height: 60vh; overflow-y: auto;">
            @for (U of filteredChampionUnits(); track U.id) {
              <button type="button" class="lp-card" (click)="chooseChampionUnit(U)" style="background: rgba(24,24,27,0.7); border: 1px solid var(--ui-border); border-radius: 8px; padding: 0.5rem; cursor: pointer; color: #fff; text-align: center;">
                @if (cardImageUrl(U); as img) {
                  <img [src]="img" [alt]="U.name" loading="lazy" decoding="async" style="width: 100%; border-radius: 4px;" (error)="onCardImageError(U, $event)" />
                } @else {
                  <div class="lp-img-fallback">{{ U.card_number }}</div>
                }
                <div class="lp-name" style="font-size: 0.78rem; font-weight: 600; margin-top: 0.25rem;">{{ U.name }}</div>
              </button>
            }
          </div>
        </div>
      </div>
    }
  `,
  styles: [`
    :host { display: block; min-height: calc(100vh - 60px); }

    .mobile-builder-switcher {
      display: none; position: sticky; top: 56px; z-index: 50;
      background: rgba(9, 9, 11, 0.95); backdrop-filter: blur(16px);
      border-bottom: 1px solid var(--ui-border); padding: 0.5rem 0.75rem; gap: 0.5rem;
    }
    .mb-tab {
      flex: 1; display: flex; align-items: center; justify-content: center; gap: 0.45rem;
      padding: 0.5rem 0.75rem; border-radius: 8px; background: rgba(24, 24, 27, 0.6);
      border: 1px solid var(--ui-border); color: var(--ui-text-secondary); font-size: 0.8rem; font-weight: 500;
      cursor: pointer; transition: all 0.15s ease;
    }
    .mb-tab.active {
      background: rgba(6, 182, 212, 0.15); border-color: #06b6d4; color: #06b6d4; font-weight: 600;
    }

    /* Mismo reparto que el constructor MYL: panel del mazo acotado y el
       catálogo se queda con el resto para que quepan más columnas. */
    .builder-layout {
      display: grid; grid-template-columns: minmax(0, 1fr) clamp(320px, 30vw, 460px); gap: 1rem;
      height: calc(100vh - 60px); max-width: 1800px; margin: 0 auto;
      padding: 0.75rem 1rem; overflow: hidden; box-sizing: border-box;
    }

    .card-browser, .deck-panel {
      display: flex; flex-direction: column; height: 100%; min-height: 0;
      background: rgba(24, 24, 27, 0.45); border: 1px solid var(--ui-border);
      border-radius: 12px; padding: 0.9rem 1rem; overflow-y: auto; box-sizing: border-box;
      backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
    }

    .browser-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.6rem; }
    .browser-title-wrap h2 { font-size: 1.05rem; font-weight: 700; color: #ffffff; margin: 0; }
    .format-badge { font-size: 0.75rem; color: #06b6d4; font-weight: 500; }

    .browser-filters { position: relative; display: flex; flex-direction: column; gap: 0.55rem; margin-bottom: 0.75rem; }
    .search-row { display: flex; flex-direction: column; gap: 0.5rem; }
    .search-input-row { display: flex; align-items: center; gap: 0.4rem; }
    .search-mode-select {
      flex-shrink: 0; padding: 0.5rem 0.6rem; background: rgba(18, 18, 23, 0.8);
      border: 1px solid var(--ui-border); border-radius: 8px; color: var(--ui-text-secondary);
      font-size: 0.8rem; font-weight: 600; font-family: inherit; outline: none; cursor: pointer;
    }
    .search-mode-select:focus { border-color: #06b6d4; }
    .search-field { position: relative; flex: 1; min-width: 0; display: flex; align-items: center; }
    .search-input-icon { position: absolute; left: 0.75rem; color: var(--ui-text-muted); pointer-events: none; }
    .search-input-row input {
      flex: 1; min-width: 0; width: 100%; padding: 0.5rem 0.75rem 0.5rem 2.2rem; background: rgba(18, 18, 23, 0.8);
      border: 1px solid var(--ui-border); border-radius: 8px; color: #ffffff; font-size: 0.85rem; outline: none;
    }
    .search-input-row input:focus { border-color: #06b6d4; box-shadow: 0 0 10px rgba(6, 182, 212, 0.2); }
    .search-btn {
      flex-shrink: 0; padding: 0.5rem 0.75rem; background: #06b6d4; color: #09090b; border: none;
      border-radius: 8px; cursor: pointer; font-weight: 600; display: flex; align-items: center;
    }

    .filters-toggle-btn {
      flex-shrink: 0; position: relative; display: inline-flex; align-items: center; gap: 0.35rem;
      padding: 0.5rem 0.75rem; background: rgba(18, 18, 23, 0.8); border: 1px solid var(--ui-border);
      border-radius: 8px; color: var(--ui-text-secondary); font-size: 0.78rem; font-weight: 600; cursor: pointer;
    }
    .filters-toggle-btn:hover { border-color: rgba(255, 255, 255, 0.3); }

    /* Lupa: cartas por fila (solo escritorio; en móvil se oculta). */
    .zoom-controls {
      flex-shrink: 0; display: inline-flex; border: 1px solid var(--ui-border);
      border-radius: 8px; overflow: hidden;
    }
    .zoom-btn {
      display: inline-flex; align-items: center; justify-content: center; width: 34px; height: 34px;
      background: rgba(18, 18, 23, 0.8); border: none; color: var(--ui-text-secondary); cursor: pointer;
      transition: all 0.15s ease;
    }
    .zoom-btn + .zoom-btn { border-left: 1px solid var(--ui-border); }
    .zoom-btn:hover:not(:disabled) { color: #06b6d4; background: rgba(6, 182, 212, 0.1); }
    .zoom-btn:focus-visible { outline: 2px solid #06b6d4; outline-offset: -2px; }
    .zoom-btn:disabled { opacity: 0.35; cursor: not-allowed; }
    .filters-toggle-btn.active { border-color: #06b6d4; color: #06b6d4; background: rgba(6, 182, 212, 0.1); }
    .filter-badge {
      position: absolute; top: -6px; right: -6px;
      min-width: 16px; height: 16px; padding: 0 3px; border-radius: 8px;
      background: #06b6d4; color: #09090b; font-size: 0.65rem; font-weight: 700;
      display: flex; align-items: center; justify-content: center;
    }

    .filters-backdrop { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.5); z-index: 1100; }
    .filters-panel {
      position: absolute; top: 100%; right: 0; z-index: 1101; margin-top: 0.3rem;
      width: min(420px, 92vw); max-height: 70vh; overflow-y: auto;
      background: #121217; border: 1px solid var(--ui-border); border-radius: 12px;
      box-shadow: 0 12px 32px rgba(0, 0, 0, 0.5);
    }
    .filters-panel-head {
      display: flex; align-items: center; justify-content: space-between;
      padding: 0.8rem 0.9rem; border-bottom: 1px solid var(--ui-border);
    }
    .filters-panel-head h3 { margin: 0; color: #fff; font-size: 0.95rem; }
    .filters-panel-head .close-btn { background: none; border: none; color: var(--ui-text-muted); font-size: 1rem; cursor: pointer; }
    .filters-panel-body { padding: 0.8rem 0.9rem; display: flex; flex-direction: column; gap: 0.8rem; }
    .filter-group { display: flex; flex-direction: column; gap: 0.4rem; }
    .filter-group + .filter-group { padding-top: 0.8rem; border-top: 1px dashed var(--ui-border); }
    .filters-panel-actions {
      display: flex; gap: 0.5rem; padding: 0.8rem 0.9rem; border-top: 1px solid var(--ui-border);
    }
    .btn-clear-all, .btn-apply-all {
      flex: 1 1 0; padding: 0.5rem; border-radius: 8px; font-size: 0.82rem; font-weight: 600; cursor: pointer;
    }
    .btn-clear-all { background: transparent; border: 1px solid var(--ui-border); color: var(--ui-text-secondary); }
    .btn-apply-all { background: #06b6d4; border: none; color: #09090b; }

    .type-chips { display: flex; flex-wrap: wrap; gap: 0.35rem; }
    .type-chip-btn {
      padding: 0.28rem 0.6rem; background: rgba(39, 39, 42, 0.3); border: 1px solid var(--ui-border);
      border-radius: 6px; color: var(--ui-text-secondary); font-size: 0.75rem; cursor: pointer;
    }
    .type-chip-btn.active { background: rgba(6, 182, 212, 0.15); border-color: #06b6d4; color: #06b6d4; font-weight: 600; }

    .filter-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(100px, 1fr)); gap: 0.5rem; }
    .filter-label { display: block; font-size: 0.68rem; color: var(--ui-text-muted); text-transform: uppercase; margin-bottom: 2px; }
    .filter-row select {
      width: 100%; padding: 0.35rem 0.5rem; background: rgba(18, 18, 23, 0.8);
      border: 1px solid var(--ui-border); border-radius: 6px; color: #ffffff; font-size: 0.75rem; outline: none;
    }

    .color-row { display: flex; gap: 0.35rem; flex-wrap: wrap; align-items: center; }
    .color-chip {
      padding: 0.2rem 0.55rem; border: 1px solid var(--c); border-radius: 999px;
      background: transparent; color: var(--c); font-size: 0.72rem; font-weight: 600; cursor: pointer;
    }
    .color-chip.active { background: var(--c); color: #09090b; }
    .clear-colors { background: none; border: none; color: #06b6d4; font-size: 0.75rem; cursor: pointer; }

    .available-cards {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(118px, 1fr));
      gap: 0.5rem; align-content: start; flex: 1; overflow-y: auto;
    }
    /* Lupa: más específico que el @media móvil, así que manda en ambos modos. */
    .available-cards.fixed-columns { grid-template-columns: repeat(var(--card-columns), minmax(0, 1fr)); }
    @media (max-width: 960px) {
      .available-cards.fixed-columns { gap: 0.4rem; }
      /* Muchas cartas por fila en móvil: selectores S/M chicos, y ocultos desde 8 por fila
         (se agrega desde el detalle tocando la carta). */
      .available-cards.dense-selectors .floating-selector:not(.expanded) { height: 24px; min-width: 24px; width: 24px; }
      .available-cards.dense-selectors .floating-selector:not(.expanded) .fs-trigger { font-size: 0.68rem; }
      .available-cards.no-selectors .floating-selector { display: none; }
    }
    /* Sin overflow:hidden aquí a propósito: en un grid-item, overflow != visible
       fuerza su "automatic minimum size" a 0 en el eje de bloque, y la fila del
       grid colapsa a ~0px aunque el contenido tenga aspect-ratio. El recorte
       (overflow/border-radius) vive en .img-wrapper en su lugar. */
    .mini-card {
      position: relative; border-radius: 8px;
      background: #121217; border: 1px solid var(--ui-border);
      transition: border-color 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease;
    }
    .mini-card:hover { border-color: rgba(255, 255, 255, 0.25); transform: translateY(-2px); box-shadow: 0 8px 18px rgba(0, 0, 0, 0.35); }
    .mini-card.in-deck { border-color: rgba(6, 182, 212, 0.55); box-shadow: 0 0 0 1px rgba(6, 182, 212, 0.45); }
    .mini-card.banned { opacity: 0.45; filter: grayscale(0.6); }

    .img-wrapper {
      position: relative; width: 100%; aspect-ratio: 2.5 / 3.5;
      border-radius: 7px; overflow: hidden; background: #121217; cursor: pointer;
    }
    .img-wrapper img { width: 100%; height: 100%; object-fit: cover; display: block; }
    .img-placeholder {
      width: 100%; height: 100%; display: flex; align-items: center; justify-content: center;
      font-size: 0.7rem; color: var(--ui-text-muted); background: #1a1a1f; text-align: center; padding: 0.3rem;
    }
    .img-wrapper::after {
      content: ''; position: absolute; inset: auto 0 0 0; height: 55%;
      background: linear-gradient(to top, rgba(0, 0, 0, 0.85), transparent); pointer-events: none;
    }
    .eye-btn {
      position: absolute; top: 4px; right: 4px; width: 22px; height: 22px; border-radius: 50%;
      background: rgba(0, 0, 0, 0.6); border: none;
      color: #ffffff; display: flex; align-items: center; justify-content: center;
      opacity: 0; cursor: pointer; transition: opacity 0.15s ease; z-index: 3;
    }
    .img-wrapper:hover .eye-btn { opacity: 1; }

    .hover-info {
      position: absolute; inset: 0 0 auto 0; padding: 0.35rem 0.4rem;
      background: linear-gradient(to bottom, rgba(0, 0, 0, 0.85), transparent);
      opacity: 0; transition: opacity 0.15s ease; pointer-events: none; z-index: 2;
    }
    .img-wrapper:hover .hover-info { opacity: 1; }
    .hi-name {
      display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
      font-size: 0.72rem; font-weight: 700; color: #ffffff; line-height: 1.2;
    }
    .hi-meta { display: flex; align-items: center; gap: 0.3rem; margin-top: 0.2rem; }
    .hi-type { font-size: 0.62rem; color: #d4d4d8; }
    .hi-num { display: block; font-size: 0.6rem; color: #d4d4d8; margin-top: 0.15rem; }

    .stat-pill {
      padding: 0 4px; border-radius: 4px; font-size: 0.6rem; font-weight: 700; line-height: 1.3;
    }
    .stat-pill.cost { background: rgba(6, 182, 212, 0.2); color: #22d3ee; }
    .stat-pill.damage { background: rgba(239, 68, 68, 0.2); color: #f87171; }

    .ban-badge {
      position: absolute; top: 4px; left: 4px; font-size: 0.6rem; font-weight: 700; padding: 2px 4px;
      border-radius: 4px; display: inline-flex; align-items: center; gap: 2px; z-index: 3;
    }
    .ban-badge-banned { background: rgba(239, 68, 68, 0.25); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.5); }
    .ban-badge-limited { background: rgba(245, 158, 11, 0.25); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.5); }

    /* ── Selectores flotantes de zona (M / S / R / C / B) ──
       Cada selector se posiciona de forma independiente (absolute, anclado a su
       propia esquina) en vez de ser hijos de un flex row: así, al expandirse uno,
       NO empuja/saca al otro fuera de la carta (bug de flexbox con overflow). */
    .zone-selectors {
      position: absolute; inset: 0;
      pointer-events: none;
    }
    .zone-selectors .floating-selector { pointer-events: auto; }
    .floating-selector {
      position: absolute; bottom: 6px; height: 28px; min-width: 28px; border-radius: 999px;
      background: rgba(15, 15, 18, 0.88); border: 1px solid var(--ui-border);
      display: flex; align-items: center; overflow: hidden; width: 28px;
      transition: width 0.2s cubic-bezier(0.4, 0, 0.2, 1), border-color 0.15s ease, background 0.15s ease;
      /* El colapsado va SIEMPRE por encima del expandido: la carta es angosta y el
         óvalo abierto puede tapar el círculo opuesto; así queda visible y clicable
         para poder cambiar de selector (p. ej. S <-> M) con un solo toque. */
      z-index: 6;
    }
    .floating-selector.zone-side { left: 6px; --zc: #f59e0b; }
    .floating-selector.zone-main { right: 6px; --zc: #06b6d4; }
    /* Zonas dedicadas (rune/champion/battlefield): normalmente aparecen solas
       (sin S/M), así que van centradas. En el raro caso de coexistir varias
       (cartas sin clasificar) se reparten un poco para no quedar 100% superpuestas. */
    .floating-selector.zone-rune { left: 50%; transform: translateX(-50%); --zc: #8b5cf6; }
    .floating-selector.zone-champion { left: 35%; transform: translateX(-50%); --zc: #ec4899; }
    .floating-selector.zone-bg { left: 65%; transform: translateX(-50%); --zc: #22c55e; }
    .floating-selector.filled { border-color: var(--zc); background: color-mix(in srgb, var(--zc) 30%, rgba(15, 15, 18, 0.9)); }
    .floating-selector.expanded { width: 98px; background: rgba(9, 9, 11, 0.96); border-color: var(--zc); z-index: 4; }
    .floating-selector.zone-rune.expanded,
    .floating-selector.zone-champion.expanded,
    .floating-selector.zone-bg.expanded { left: 50%; transform: translateX(-50%); }

    .fs-trigger {
      position: absolute; inset: 0; width: 100%; height: 100%; min-width: 0; min-height: 0;
      margin: 0; padding: 0; border: none; background: transparent;
      color: #ffffff; font-size: 0.76rem; font-weight: 800; line-height: 1; font-family: inherit; cursor: pointer;
      appearance: none; -webkit-appearance: none;
      display: flex; align-items: center; justify-content: center; text-align: center;
      opacity: 1; transition: opacity 0.15s ease;
    }
    .floating-selector.expanded .fs-trigger { opacity: 0; pointer-events: none; }

    .fs-controls {
      display: flex; align-items: center; gap: 4px; padding: 0 5px; width: 100%;
      opacity: 0; pointer-events: none; transition: opacity 0.15s ease 0.05s; white-space: nowrap;
    }
    .floating-selector.expanded .fs-controls { opacity: 1; pointer-events: auto; }

    .fs-tag {
      font: inherit; padding: 0; border: none; background: transparent; cursor: pointer; line-height: 1;
      font-size: 0.66rem; font-weight: 800; color: var(--zc); width: 14px; flex-shrink: 0;
    }
    .fs-op {
      width: 20px; height: 20px; border-radius: 50%; border: 1px solid var(--ui-border);
      background: rgba(255, 255, 255, 0.08); color: #ffffff; font-size: 0.78rem; font-weight: 700;
      line-height: 1; display: flex; align-items: center; justify-content: center; cursor: pointer;
      flex-shrink: 0; transition: all 0.15s ease;
    }
    .fs-op:hover:not(:disabled) { background: var(--zc); border-color: var(--zc); color: #09090b; }
    .fs-op:disabled { opacity: 0.3; cursor: not-allowed; }
    .fs-count { font-size: 0.78rem; font-weight: 800; color: #ffffff; min-width: 13px; text-align: center; flex-shrink: 0; }

    /* Responsive: en móvil el panel de cartas ocupa todo el ancho (ver @media 960px
       más abajo), así que agrandamos un poco más las cartas y los círculos táctiles. */
    @media (max-width: 960px) {
      .available-cards { grid-template-columns: repeat(auto-fill, minmax(112px, 1fr)); gap: 0.7rem; }
      .floating-selector { height: 32px; min-width: 32px; width: 32px; }
      .floating-selector.expanded { width: 110px; }
      .fs-trigger { font-size: 0.82rem; }
      .fs-op { width: 22px; height: 22px; font-size: 0.82rem; }
      .fs-tag { font-size: 0.7rem; width: 12px; }
      .fs-count { font-size: 0.82rem; }
    }

    /* Deck Panel & Cards */
    .deck-header {
      display: flex; justify-content: space-between; align-items: center;
      padding-bottom: 0.85rem; border-bottom: 1px solid var(--ui-border); margin-bottom: 1rem;
    }
    .deck-header-info { display: flex; align-items: center; gap: 0.75rem; }
    .deck-header-info h1, .deck-header-info h2 { font-size: 1.15rem; font-weight: 700; color: #ffffff; margin: 0; }
    .legal-badge {
      font-size: 0.72rem; font-weight: 600; padding: 0.2rem 0.55rem; border-radius: 999px;
      background: rgba(6, 182, 212, 0.15); color: #06b6d4; border: 1px solid rgba(6, 182, 212, 0.3);
    }
    .deck-header-actions { display: flex; gap: 0.35rem; }
    .icon-btn {
      width: 32px; height: 32px; border-radius: 6px; background: rgba(39, 39, 42, 0.4);
      border: 1px solid var(--ui-border); color: var(--ui-text-secondary); display: flex;
      align-items: center; justify-content: center; cursor: pointer;
    }
    .icon-btn:hover:not(:disabled) { border-color: #06b6d4; color: #06b6d4; background: rgba(6, 182, 212, 0.15); }

    .legend-banner {
      display: flex; align-items: center; gap: 0.75rem; padding: 0.6rem 0.85rem;
      background: rgba(18, 18, 23, 0.7); border: 1px solid var(--ui-border); border-radius: 8px;
      margin-bottom: 0.85rem;
    }
    .choose-legend-btn {
      width: 100%; padding: 0.6rem 1rem; background: rgba(6, 182, 212, 0.15); border: 1px dashed #06b6d4;
      border-radius: 8px; color: #06b6d4; font-weight: 600; font-size: 0.85rem; cursor: pointer;
      display: flex; align-items: center; justify-content: center; gap: 0.45rem;
    }
    .legend-img { width: 44px; height: 60px; object-fit: cover; border-radius: 4px; border: 1px solid var(--ui-border); }
    .legend-info { flex: 1; min-width: 0; }
    .legend-tag { font-size: 0.62rem; font-weight: 700; color: #06b6d4; letter-spacing: 0.05em; }
    .legend-info strong { display: block; font-size: 0.88rem; color: #ffffff; }
    .legend-actions { display: flex; gap: 0.35rem; }
    .legend-btn {
      padding: 0.25rem 0.5rem; background: rgba(39, 39, 42, 0.5); border: 1px solid var(--ui-border);
      border-radius: 4px; color: var(--ui-text-secondary); font-size: 0.72rem; cursor: pointer;
      display: inline-flex; align-items: center; gap: 0.3rem;
    }

    .deck-info-box {
      position: relative;
      border: 1px solid rgba(6, 182, 212, 0.4);
      border-radius: 12px;
      padding: 1.35rem 1rem 1rem;
      margin-bottom: 1rem;
      background: rgba(18, 18, 23, 0.5);
    }
    .form-group.floating {
      position: relative;
      margin-bottom: 0.9rem;

      &:last-of-type { margin-bottom: 0.75rem; }
    }
    .form-group.floating label {
      position: absolute;
      top: -0.65rem;
      left: 0.7rem;
      padding: 0 0.4rem;
      background: #121217;
      border-radius: 4px;
      font-size: 0.7rem;
      color: var(--ui-text-muted);
    }
    .form-group.floating input,
    .form-group.floating textarea {
      width: 100%; padding: 0.6rem 0.75rem; background: rgba(18, 18, 23, 0.8);
      border: 1px solid var(--ui-border); border-radius: 8px; color: #ffffff; font-size: 0.85rem; outline: none;
      font-family: inherit;
      box-sizing: border-box;

      &:focus { border-color: #06b6d4; }
    }
    .form-group.floating textarea {
      resize: vertical;
      min-height: 4.5rem;
      line-height: 1.4;
    }
    .checkbox-label { display: flex; align-items: center; gap: 0.35rem; font-size: 0.78rem; color: var(--ui-text-secondary); }

    @media (max-width: 720px) {
      .deck-info-box { padding: 1.35rem 0.85rem 0.85rem; }
    }

    .zones-summary { display: flex; gap: 0.4rem; flex-wrap: wrap; margin-bottom: 1rem; }
    .zone-pill {
      padding: 0.25rem 0.6rem; border-radius: 999px; background: rgba(18, 18, 23, 0.6);
      border: 1px solid var(--ui-border); font-size: 0.75rem; color: var(--ui-text-muted);
    }
    .zone-pill.ok { border-color: rgba(16, 185, 129, 0.4); color: #10b981; }

    .cost-curve-panel {
      background: rgba(18, 18, 23, 0.5); border: 1px solid var(--ui-border); border-radius: 8px;
      padding: 0.75rem 1rem; margin-bottom: 1.25rem;
    }
    .curve-title {
      font-size: 0.78rem; font-weight: 700; color: #06b6d4; text-transform: uppercase;
      display: inline-flex; align-items: center; gap: 0.35rem; margin-bottom: 0.5rem;
    }
    .cost-curve-bars { display: flex; align-items: flex-end; gap: 0.5rem; height: 60px; }
    .cost-bar { flex: 1; display: flex; flex-direction: column; align-items: center; height: 100%; }
    .cost-bar-count { font-size: 0.65rem; color: var(--ui-text-muted); margin-bottom: 2px; }
    .cost-bar-fill-wrap {
      flex: 1; width: 100%; max-width: 28px; display: flex; align-items: flex-end;
      background: rgba(39, 39, 42, 0.2); border-radius: 3px; overflow: hidden;
    }
    .cost-bar-fill { width: 100%; background: #06b6d4; border-radius: 3px 3px 0 0; min-height: 2px; }
    .cost-bar-label { font-size: 0.65rem; color: var(--ui-text-secondary); margin-top: 2px; }

    .zone-section { margin-bottom: 1rem; }
    .zone-section-head {
      display: flex; justify-content: space-between; align-items: center;
      padding-bottom: 0.3rem; border-bottom: 1px solid var(--ui-border); margin-bottom: 0.4rem;
    }
    .zs-title { font-size: 0.78rem; font-weight: 700; color: #06b6d4; text-transform: uppercase; }
    .zs-count { font-size: 0.74rem; color: var(--ui-text-muted); }
    .zs-count.ok { color: #10b981; }

    .deck-entry {
      display: flex; align-items: center; gap: 0.65rem; padding: 0.35rem 0.6rem;
      background: rgba(18, 18, 23, 0.6); border: 1px solid var(--ui-border); border-radius: 8px;
      margin-bottom: 0.35rem;
    }
    .cover-star { background: none; border: none; color: var(--ui-text-muted); cursor: pointer; padding: 2px; }
    .cover-star.active { color: #f59e0b; }
    .deck-entry img { width: 32px; height: 44px; border-radius: 4px; object-fit: cover; border: 1px solid var(--ui-border); flex-shrink: 0; }
    .entry-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
    .entry-name {
      display: block; width: 100%;
      font-size: 0.84rem; font-weight: 600; color: #ffffff;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .entry-meta-row { display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; }
    .entry-meta {
      flex: 1; min-width: 0; font-size: 0.72rem; color: var(--ui-text-muted);
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    // Nota: el sitio fuerza min-height: 40px en todo boton (styles.scss, regla de
    // accesibilidad WCAG AA). Por eso el grupo va horizontal (no flechitas apiladas:
    // 2 botones de 40px apilados se veian como un circulo roto).
    .entry-controls {
      display: flex; align-items: stretch; flex-shrink: 0;
      background: rgba(39, 39, 42, 0.5); border: 1px solid var(--ui-border); border-radius: 10px;
      overflow: hidden;
    }
    .entry-qty {
      display: flex; align-items: center; justify-content: center;
      font-size: 0.82rem; font-weight: 700; color: #06b6d4; min-width: 20px; padding: 0 2px;
    }
    .ctrl-btn {
      width: 28px; flex-shrink: 0;
      display: flex; align-items: center; justify-content: center;
      background: transparent; border: none;
      color: #ffffff; font-size: 0.85rem; font-weight: 700; line-height: 1;
      cursor: pointer; transition: all 0.15s ease;

      &:hover:not(:disabled) { background: rgba(6, 182, 212, 0.2); color: #06b6d4; }
      &:disabled { opacity: 0.35; cursor: not-allowed; }

      &.remove {
        color: var(--ui-text-muted); border-left: 1px solid var(--ui-border);
        &:hover { background: rgba(220, 53, 69, 0.15); color: #ff6b6b; }
      }
    }

    .action-row {
      display: flex; gap: 0.5rem; margin-top: 1rem; padding-top: 0.85rem; border-top: 1px solid var(--ui-border);
    }
    .preview-deck-btn {
      flex: 1; padding: 0.55rem 1rem; background: rgba(39, 39, 42, 0.4); border: 1px solid var(--ui-border);
      border-radius: 8px; color: var(--ui-text-secondary); font-weight: 600; cursor: pointer;
      display: flex; align-items: center; justify-content: center; gap: 0.4rem;
    }
    .save-btn {
      flex: 2; padding: 0.55rem 1rem; background: #06b6d4; border: none; border-radius: 8px;
      color: #09090b; font-weight: 700; font-size: 0.9rem; cursor: pointer;
    }

    /* Modal styles */
    .modal-overlay, .preview-overlay {
      position: fixed; inset: 0; background: rgba(0, 0, 0, 0.75); backdrop-filter: blur(12px);
      z-index: 500; display: flex; align-items: center; justify-content: center; padding: 1rem;
    }
    .preview-panel, .deck-preview-box, .modal {
      position: relative; width: min(92vw, 760px); max-height: 88vh; background: rgba(18, 18, 23, 0.98);
      border: 1px solid var(--ui-border); border-radius: 16px; box-shadow: 0 24px 48px rgba(0, 0, 0, 0.8);
      padding: 1.5rem; overflow-y: auto;
    }
    .preview-panel { width: min(94vw, 900px); background: #1a1c23; }
    .preview-panel .preview-layout {
      display: flex; flex-direction: row; gap: 1.5rem; align-items: flex-start;
    }
    @media (max-width: 768px) {
      .preview-panel .preview-layout { flex-direction: column; }
    }
    .preview-art-col { flex: 0 0 42%; display: flex; }
    @media (max-width: 768px) {
      .preview-art-col { flex: 0 0 auto; width: min(78vw, 340px); align-self: center; }
    }
    .preview-card-img {
      width: 100%; height: auto; max-height: 65vh; border-radius: 10px;
      object-fit: contain; background: rgba(12, 12, 16, 0.6);
      border: 1px solid var(--ui-border); display: block; margin: auto;
    }
    @media (max-width: 768px) {
      .preview-card-img { max-height: 55vh; }
    }
    .preview-info-col { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 0.5rem; }
    .preview-title { font-size: 1.2rem; font-weight: 700; color: #ffffff; margin: 0; }
    .preview-meta-badges { display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0.3rem 0; }
    .preview-meta-badges .stat-badge {
      padding: 2px 8px; border-radius: 4px; font-size: 0.72rem; font-weight: 600;
      background: rgba(39, 39, 42, 0.5); border: 1px solid var(--ui-border); color: var(--ui-text-secondary);
    }
    .preview-meta-badges .stat-badge.rarity { border-color: #06b6d4; color: #06b6d4; }
    .preview-stats-row {
      display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.35rem;
    }
    .stat-item {
      display: flex; align-items: center; gap: 0.4rem;
      background: rgba(255, 255, 255, 0.05); border: 1px solid var(--ui-border); border-radius: 999px;
      padding: 0.4rem 0.75rem;

      app-icon { flex-shrink: 0; }
    }
    .stat-item.stat-energy app-icon { color: #f2c744; }
    .stat-item.stat-power app-icon { color: #e94560; }
    .stat-item.stat-might app-icon { color: #3aa6ff; }
    .stat-label { font-size: 0.72rem; color: var(--ui-text-muted); font-weight: 600; }
    .stat-val { font-size: 0.85rem; font-weight: 700; color: #ffffff; }
    .preview-ability-box {
      background: rgba(255, 255, 255, 0.03); border: 1px solid var(--ui-border); border-radius: 10px;
      padding: 0.75rem 0.9rem;
    }
    .ability-title {
      display: block; font-size: 0.7rem; font-weight: 700; color: #06b6d4;
      text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.25rem;
    }
    .ability-text { font-size: 0.85rem; line-height: 1.55; color: #e2e8f0; margin: 0; white-space: pre-wrap; }
    .preview-market-section { margin-top: 0.1rem; }
    .dp-head, .modal-head { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--ui-border); padding-bottom: 0.85rem; margin-bottom: 1rem; }
    .dp-head h2, .modal-head h3 { font-size: 1.15rem; font-weight: 700; color: #ffffff; margin: 0; display: flex; align-items: center; gap: 0.4rem; }
    .dp-close, .modal-close, .preview-close {
      background: rgba(39, 39, 42, 0.5); border: 1px solid var(--ui-border); border-radius: 6px;
      color: var(--ui-text-muted); cursor: pointer; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;
    }

    /* Kept last in the stylesheet on purpose: these overrides share selector
       specificity with their base rules above (e.g. .filters-panel), so source
       order is what makes them win the cascade at narrow widths. */
    @media (max-width: 960px) {
      .builder-layout { display: block; height: auto; padding: 0.75rem; }
      .mobile-builder-switcher { display: flex; }
      .mobile-hidden { display: none !important; }
      .filters-toggle-btn .ft-text { display: none; }
      .filters-panel {
        position: fixed; inset: 0; top: 0; right: 0; margin-top: 0;
        width: 100%; max-height: 100%; border-radius: 0;
      }
      .filters-panel-actions { position: sticky; bottom: 0; background: #121217; }
      /* backdrop-filter on .card-browser creates a containing block for our
         position:fixed backdrop/panel, pinning them to the (scrolled) card-browser
         box instead of the viewport. Drop it while the modal is open so inset:0
         resolves against the real viewport. */
      .card-browser.filters-modal-open { backdrop-filter: none; -webkit-backdrop-filter: none; }
    }
  `],
})
export class RiftboundBuilderComponent implements OnInit, AfterViewInit, OnDestroy {
  private rb = inject(RiftboundService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private auth = inject(AuthService);
  private dialog = inject(ConfirmDialogService);
  private injector = inject(Injector);
  private zone = inject(NgZone);

  readonly zones: RiftboundZone[] = ['main', 'side', 'rune', 'champion', 'bg'];
  readonly rules = RIFTBOUND_ZONE_RULES;
  readonly labels = RIFTBOUND_ZONE_LABELS;
  readonly colors = COLORS;
  readonly types = TYPES;
  readonly energyBins = [0, 1, 2, 3, 4, 5, 6, 7, 8];

  // Deck state
  deckId = signal<number | null>(null);
  deckName = 'Nuevo mazo Riftbound';
  description = '';
  isPublic = false;
  coverCardId = signal<number | null>(null);
  saving = signal(false);
  errors = signal<string[]>([]);
  private brokenImageUrlsByKey = new Map<string, Set<string>>();
  private imageFallbackNonce = signal(0);

  // Responsive & Mobile
  activeMobileTab = signal<'browser' | 'deck'>('browser');
  showDeckPanel = signal(false);

  setMobileTab(tab: 'browser' | 'deck') {
    this.activeMobileTab.set(tab);
    this.showDeckPanel.set(tab === 'deck');
  }

  // Browser state
  searchQuery = '';
  searchMode: 'name' | 'ability' | 'all' = 'name';
  typeFilter = '';
  setFilter = '';
  rarityFilter = '';
  energyFilter: number | null = null;
  powerFilter: number | null = null;
  mightFilter: number | null = null;
  selectedColors = signal(new Set<RiftboundColor>());
  filtersOpen = signal(false);
  readonly statBins = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

  activeFilterCount(): number {
    let n = 0;
    if (this.typeFilter) n++;
    if (this.setFilter) n++;
    if (this.rarityFilter) n++;
    if (this.energyFilter != null) n++;
    if (this.powerFilter != null) n++;
    if (this.mightFilter != null) n++;
    if (this.selectedColors().size > 0) n++;
    return n;
  }

  clearAllFilters() {
    this.typeFilter = '';
    this.setFilter = '';
    this.rarityFilter = '';
    this.energyFilter = null;
    this.powerFilter = null;
    this.mightFilter = null;
    this.selectedColors.set(new Set());
    this.page.set(1);
    this.reload();
  }

  results = signal<RiftboundCardLite[]>([]);
  hasMore = signal(false);

  /** Selector de zona expandido en el catálogo (solo uno a la vez en toda la pantalla). */
  expandedCardId = signal<number | null>(null);
  expandedZone = signal<RiftboundZone | null>(null);

  toggleSelector(cardId: number, zone: RiftboundZone, event?: Event) {
    event?.stopPropagation();
    if (this.expandedCardId() === cardId && this.expandedZone() === zone) {
      this.collapseSelector();
    } else {
      this.expandedCardId.set(cardId);
      this.expandedZone.set(zone);
    }
  }

  isExpanded(cardId: number, zone: RiftboundZone): boolean {
    return this.expandedCardId() === cardId && this.expandedZone() === zone;
  }

  collapseSelector() {
    this.expandedCardId.set(null);
    this.expandedZone.set(null);
  }

  @HostListener('document:click')
  onDocumentClickCollapseSelector() {
    if (this.expandedCardId() !== null) this.collapseSelector();
  }

  @HostListener('document:keydown.escape')
  onEscapeCollapseSelector() {
    if (this.expandedCardId() !== null) this.collapseSelector();
  }

  /** Cartas mostradas en el listado: oculta los demás legends cuando ya hay
   *  uno seleccionado (un mazo solo puede tener 1 Champion Legend). */
  displayedResults = computed<RiftboundCardLite[]>(() => {
    const list = this.results();
    const L = this.chosenLegend();
    if (!L) return list;
    return list.filter(c => c.card_type !== 'legend' || c.id === L.id);
  });
  loading = signal(false);

  /** Lupa del catálogo: cartas por fila (escritorio 9→4, móvil 10→1). */
  readonly cardZoom = new CardZoom('rbBuilder.cardColumns');

  page = signal(1);
  totalCount = signal(0);
  // Debe coincidir con DRF PAGE_SIZE (backend/backend/settings.py).
  pageSize = 20;
  totalPages = computed(() => Math.max(1, Math.ceil(this.totalCount() / this.pageSize)));
  private cardsSentinelRef?: ElementRef<HTMLElement>;
  private cardsObserver?: IntersectionObserver;
  private observedSentinel?: HTMLElement;
  private contentScrollEl: HTMLElement | null = null;
  @ViewChild('availableCardsEl') availableCardsRef?: ElementRef<HTMLElement>;
  private gridResizeObserver?: ResizeObserver;

  @ViewChild('cardsSentinel')
  set cardsSentinelSetter(el: ElementRef<HTMLElement> | undefined) {
    this.cardsSentinelRef = el;
    this.setupCardsObserver();
  }

  sets = signal<{ code: string; name: string }[]>([]);

  // Banlist (formato Standard)
  banlist = signal<Map<string, { status: string; max_copies: number }>>(new Map());

  // Champion-first wizard
  legendOptions = signal<RiftboundCardLite[]>([]);
  showLegendPicker = signal(false);
  legendPickerSearch = signal('');
  /** Si está activo, los filtros de colores quedan bloqueados a los del legend. */
  lockColorsToLegend = signal(true);

  // Champion Unit (unidad designada con el mismo tag que el legend)
  championUnitId = signal<number | null>(null);
  championUnitData = signal<RiftboundCardLite | null>(null);
  championUnitOptions = signal<RiftboundCardLite[]>([]);
  showChampionUnitPicker = signal(false);
  championUnitPickerSearch = signal('');
  loadingChampionUnits = signal(false);

  // Deck entries
  entries = signal<Record<RiftboundZone, BuilderEntry[]>>({
    main: [], side: [], rune: [], champion: [], bg: [],
  });

  // UI state
  showDeckPreview = signal(false);
  previewCard = signal<RiftboundCardLite | null>(null);
  previewDetail = signal<RiftboundCard | null>(null);
  previewLoading = signal(false);

  private searchTimer: ReturnType<typeof setTimeout> | null = null;

  @HostListener('window:scroll')
  onWindowScroll() { this.tryInfiniteScrollFallback(); }

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.deckId.set(+id);
      this.rb.getDeck(+id).subscribe({ next: (deck) => this.loadFromDeck(deck) });
    } else {
      // Mazo nuevo: intentar restaurar borrador local
      this.restoreDraft();
    }
    this.rb.listSets().subscribe({
      next: (sets: any) => {
        const arr = Array.isArray(sets) ? sets : (sets?.results ?? []);
        this.sets.set(arr.map((s: any) => ({ code: s.code, name: s.name })));
      },
    });
    // Cargar banlist Standard
    this.rb.listBanlist('standard').subscribe({
      next: (resp: any) => {
        const map = new Map<string, { status: string; max_copies: number }>();
        for (const e of (resp?.results ?? [])) {
          if (e.card_number) {
            map.set(e.card_number, { status: e.status, max_copies: e.max_copies ?? 0 });
          }
        }
        this.banlist.set(map);
      },
    });
    // Cargar todos los Champion Legends para el wizard
    // Una sola página grande (hay ~170 legends); el bucle solo pide más si el
    // backend limita el tamaño (QA #2 M7).
    const LEGEND_PAGE_SIZE = 250;
    this.rb.listCards({ type: 'legend', lite: true, page: 1, pageSize: LEGEND_PAGE_SIZE }).subscribe({
      next: (resp) => {
        const all = (resp.results as RiftboundCardLite[]).slice();
        const total = resp.count;
        const fetchPage = (p: number) => {
          if (all.length >= total) {
            this.legendOptions.set(all);
            // Si entras a un mazo nuevo y no hay legend en zona champion, abrir picker
            if (!this.deckId() && this.entries().champion.length === 0) {
              this.showLegendPicker.set(true);
            }
            return;
          }
          this.rb.listCards({ type: 'legend', lite: true, page: p, pageSize: LEGEND_PAGE_SIZE }).subscribe({
            next: (r) => {
              const batch = r.results as RiftboundCardLite[];
              if (!batch.length) { this.legendOptions.set(all); return; }
              all.push(...batch);
              fetchPage(p + 1);
            },
          });
        };
        fetchPage(2);
      },
    });
    this.reload();
  }

  ngAfterViewInit() {
    this.setupCardsObserver();
    this.attachContentScrollListener();
    this.observeGridSize();
  }

  /**
   * Re-chequea si faltan cartas cuando el grid aparece o cambia de tamaño (carga
   * inicial, panel que se muestra tras elegir legend, resize, pestaña móvil). La
   * verificación tras cada página no alcanza: en la primera el panel puede no estar
   * visible todavía y nada volvía a mirar.
   */
  private observeGridSize() {
    const grid = this.availableCardsRef?.nativeElement;
    if (!grid || typeof ResizeObserver === 'undefined') return;
    this.gridResizeObserver?.disconnect();
    // ResizeObserver no está parcheado por zone.js: volver a la zona para que la
    // carga dispare detección de cambios.
    this.gridResizeObserver = new ResizeObserver(() => this.zone.run(() => {
      if (!this.loading() && this.isSentinelInView()) this.loadMoreResults();
    }));
    this.gridResizeObserver.observe(grid);
  }

  loadFromDeck(deck: RiftboundDeck) {
    this.deckName = deck.name;
    this.description = deck.description ?? '';
    this.isPublic = deck.is_public ?? true;
    this.coverCardId.set(deck.cover_card ?? null);
    const map: Record<RiftboundZone, BuilderEntry[]> = {
      main: [], side: [], rune: [], champion: [], bg: [],
    };
    for (const e of deck.entries ?? []) {
      if (e.card_data) {
        map[e.zone].push({ card: e.card_data as RiftboundCardLite, quantity: e.quantity, zone: e.zone });
      }
    }
    this.sortAllZonesInPlace(map);
    this.entries.set(map);

    // Champion unit + opciones
    this.championUnitId.set(deck.champion_unit ?? null);
    this.championUnitData.set(deck.champion_unit_data ?? null);
    const legend = map.champion[0]?.card;
    if (legend) {
      // Si el candado está cerrado, aplicar colores del legend como filtro
      if (this.lockColorsToLegend()) {
        const cs = (legend as any).colors as RiftboundColor[] | undefined;
        this.selectedColors.set(new Set(cs ?? []));
        this.reload();
      }
      this.loadChampionUnitsForLegend(legend);
    }
  }

  // ── Búsqueda / filtros ──
  onSearchInput() {
    if (this.searchTimer) clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => { this.page.set(1); this.reload(); }, 300);
  }

  setType(t: string) {
    this.typeFilter = t;
    this.page.set(1);
    this.reload();
  }

  setMode(m: 'name' | 'ability' | 'all') {
    if (this.searchMode === m) return;
    this.searchMode = m;
    if (this.searchQuery) { this.page.set(1); this.reload(); }
  }

  toggleColor(c: RiftboundColor) {
    const set = new Set(this.selectedColors());
    if (set.has(c)) set.delete(c); else set.add(c);
    this.selectedColors.set(set);
    this.page.set(1);
    this.reload();
  }

  clearColors() {
    this.selectedColors.set(new Set());
    this.page.set(1);
    this.reload();
  }

  reload() {
    this.page.set(1);
    this.results.set([]);
    this.hasMore.set(false);
    this.fetchCardsPage();
  }

  loadMoreResults() {
    if (this.loading() || !this.hasMore()) return;
    this.page.update(p => p + 1);
    this.fetchCardsPage(true);
  }

  private fetchCardsPage(append = false) {
    this.loading.set(true);
    this.rb.listCards({
      search: this.searchQuery || undefined,
      searchMode: this.searchMode,
      type: this.typeFilter || undefined,
      set: this.setFilter || undefined,
      rarity: this.rarityFilter || undefined,
      energy: this.energyFilter ?? undefined,
      power: this.powerFilter ?? undefined,
      might: this.mightFilter ?? undefined,
      colors: [...this.selectedColors()],
      page: this.page(),
      pageSize: this.pageSize,
      lite: true,
    }).subscribe({
      next: (resp) => {
        if (append) {
          this.results.update(curr => [...curr, ...(resp.results as RiftboundCardLite[])]);
        } else {
          this.results.set(resp.results as RiftboundCardLite[]);
        }
        this.totalCount.set(resp.count);
        this.hasMore.set(!!resp.next);
        this.loading.set(false);
        // Nota: NO llamamos tryInfiniteScrollFallback() aqui. isNearBottom() da true
        // apenas el panel no tiene contenido suficiente para desbordar (comun en la
        // primera pagina), asi que llamarlo tras cada fetch encadenaba cargas hasta
        // traer todo el catalogo sin que el usuario bajara el scroll. El fallback solo
        // debe correr en respuesta a un scroll real del usuario (ver onContentScroll).
        // afterNextRender y no setTimeout: con eventCoalescing Angular pinta en el
        // siguiente frame, así que un setTimeout(0) medía el DOM sin las cartas nuevas.
        afterNextRender(() => {
          this.setupCardsObserver();
          // El observer solo avisa cuando el centinela ENTRA en vista. Si tras esta
          // página las cartas aún no llenan el panel no hay cambio que reportar y la
          // carga se detenía: se sigue cargando mientras falte llenar la vista.
          if (this.isSentinelInView()) this.loadMoreResults();
        }, { injector: this.injector });
      },
      error: () => this.loading.set(false),
    });
  }

  /**
   * ¿Hace falta otra página para llenar la vista? Ojo: el centinela está FUERA del
   * grid, y el grid scrollea por dentro, así que el centinela queda siempre pegado
   * al borde inferior del panel: medir su posición daba "visible" para siempre y se
   * traía todo el catálogo. Por eso se mira el scroll del propio grid.
   */
  private isSentinelInView(margin = 200): boolean {
    const grid = this.availableCardsRef?.nativeElement;
    // offsetParent null = oculto (p. ej. pestaña "Mazo" en móvil): no cargar.
    if (!grid || grid.offsetParent === null || !this.hasMore()) return false;
    if (grid.scrollHeight > grid.clientHeight + 1) {
      // El grid ya scrollea: cargar solo cerca del final de su scroll.
      return grid.scrollTop + grid.clientHeight >= grid.scrollHeight - margin;
    }
    // Sin scroll propio: o las cartas aún no llenan el panel, o el layout es apilado
    // (scrollea la página). En ambos casos basta con que su borde inferior se vea.
    return grid.getBoundingClientRect().bottom <= window.innerHeight + margin;
  }

  private setupCardsObserver() {
    if (typeof IntersectionObserver === 'undefined') return;
    const sentinel = this.cardsSentinelRef?.nativeElement;
    if (!sentinel) {
      this.cardsObserver?.disconnect();
      this.observedSentinel = undefined;
      return;
    }
    // El nodo centinela persiste mientras hasMore() siga en true (mismo @if), así que
    // reconectar el observer en cada página recreaba el "fire" inicial de IntersectionObserver
    // sobre un nodo que ya estaba visible, encadenando cargas hasta traer todo el catálogo.
    if (this.cardsObserver && this.observedSentinel === sentinel) return;
    this.cardsObserver?.disconnect();
    const root = this.availableCardsRef?.nativeElement ?? null;
    this.cardsObserver = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          this.loadMoreResults();
          break;
        }
      }
    }, { root, rootMargin: '200px 0px' });
    this.cardsObserver.observe(sentinel);
    this.observedSentinel = sentinel;
  }

  private attachContentScrollListener() {
    this.detachContentScrollListener();
    const el = this.availableCardsRef?.nativeElement
      ?? document.querySelector('.available-cards') as HTMLElement | null;
    if (!el) return;
    this.contentScrollEl = el;
    this.contentScrollEl.addEventListener('scroll', this.onContentScroll, { passive: true });
    // El scroll de <body> no burbujea a window (solo lo hace el "scrolling element"
    // del documento), y en esta app es <body> quien tiene overflow-y:auto real, no
    // <html>. Sin este listener, el scroll del usuario nunca disparaba la carga.
    document.body.addEventListener('scroll', this.onContentScroll, { passive: true });
  }

  private detachContentScrollListener() {
    document.body.removeEventListener('scroll', this.onContentScroll);
    if (!this.contentScrollEl) return;
    this.contentScrollEl.removeEventListener('scroll', this.onContentScroll);
    this.contentScrollEl = null;
  }

  private onContentScroll = () => {
    this.tryInfiniteScrollFallback();
  };

  private tryInfiniteScrollFallback() {
    if (!this.isNearBottom()) return;
    this.loadMoreResults();
  }

  private isNearBottom(offset = 300): boolean {
    const panel = this.contentScrollEl ?? this.availableCardsRef?.nativeElement;
    if (panel && panel.scrollHeight > panel.clientHeight + 1) {
      return panel.scrollTop + panel.clientHeight >= panel.scrollHeight - offset;
    }
    // El panel de cartas no tiene scroll propio en este layout (p. ej. modo apilado /
    // móvil, donde .available-cards crece con el contenido en vez de scrollear
    // internamente): en ese caso lo que se desplaza es <body> (esta app le pone
    // overflow-y:auto explícito a body, NO a <html>, así que document.scrollingElement
    // no sirve aquí).
    const body = document.body;
    if (body.scrollHeight > body.clientHeight + 1) {
      return body.scrollTop + body.clientHeight >= body.scrollHeight - offset;
    }
    return false;
  }

  // ── Helpers de zona ──
  zoneCount(z: RiftboundZone): number {
    return this.entries()[z].reduce((s, e) => s + e.quantity, 0);
  }

  /**
   * Entradas de una zona ordenadas por tipo (unidad → hechizo → equipo → resto)
   * y luego por nombre. Devuelve una copia, no muta el signal.
   */
  sortedEntries(z: RiftboundZone): BuilderEntry[] {
    return [...this.entries()[z]].sort(this.entryComparator);
  }

  /** Comparador compartido: tipo (unidad → hechizo → equipo → resto). Estable: preserva orden de inserción dentro del mismo tipo. */
  private entryComparator(a: BuilderEntry, b: BuilderEntry): number {
    return typeRank(a.card.card_type) - typeRank(b.card.card_type);
  }

  /** Ordena en sitio el mapa de entries (se usa al entrar al builder). */
  private sortAllZonesInPlace(map: Record<RiftboundZone, BuilderEntry[]>) {
    for (const z of this.zones) map[z].sort(this.entryComparator);
  }

  totalEntries = computed(() => {
    const e = this.entries();
    return Object.values(e).reduce(
      (sum, list) => sum + list.reduce((s, x) => s + x.quantity, 0),
      0,
    );
  });

  isZoneOk(z: RiftboundZone): boolean {
    const count = this.zoneCount(z);
    const rule = this.rules[z];
    if (z === 'main') return count === rule;
    if (z === 'side') return count === 0 || count === rule;
    if (z === 'bg') {
      if (count !== rule) return false;
      const ids = this.entries()[z].flatMap(e => Array(e.quantity).fill(e.card.id));
      return new Set(ids).size === ids.length;
    }
    return count === rule;
  }

  zoneShortLabel(z: RiftboundZone): string {
    return ({ main: 'Main', side: 'Side', rune: 'Rune', champion: 'Champ', bg: 'BF' } as const)[z];
  }

  zoneLetter(z: RiftboundZone): string {
    return ({ main: 'M', side: 'S', rune: 'R', champion: 'C', bg: 'B' } as const)[z];
  }

  typeLabel(t: string): string {
    return this.types.find(x => x.code === t)?.label ?? t;
  }

  private cardImageKey(card: CardImageLike | null | undefined): string {
    if (!card) return '';
    return String(card.id ?? card.card_number ?? card.image ?? 'unknown');
  }

  private normalizeImageUrl(url: string | null | undefined): string {
    const value = (url ?? '').trim();
    if (!value) return '';
    if (value.startsWith('http://')) return `https://${value.slice(7)}`;
    return value;
  }

  private candidateImageUrls(card: CardImageLike | null | undefined): string[] {
    if (!card) return [];
    const urls = [card.image, card.cdn_image_url, card.image_url, card.image_url_small]
      .map((url) => this.normalizeImageUrl(url))
      .filter(Boolean);
    return Array.from(new Set(urls));
  }

  cardImageUrl(card: CardImageLike | null | undefined): string {
    this.imageFallbackNonce();
    const candidates = this.candidateImageUrls(card);
    if (!candidates.length) return '';

    const key = this.cardImageKey(card);
    const broken = this.brokenImageUrlsByKey.get(key);
    for (const url of candidates) {
      if (!broken?.has(url)) return url;
    }

    return candidates[0];
  }

  onCardImageError(card: CardImageLike | null | undefined, event: Event) {
    if (!card) return;
    const key = this.cardImageKey(card);
    if (!key) return;

    let broken = this.brokenImageUrlsByKey.get(key);
    if (!broken) {
      broken = new Set<string>();
      this.brokenImageUrlsByKey.set(key, broken);
    }

    const img = event.target as HTMLImageElement | null;
    const failed = [img?.currentSrc, img?.src]
      .map((url) => this.normalizeImageUrl(url))
      .filter(Boolean);

    let changed = false;
    for (const url of failed) {
      if (!broken.has(url)) {
        broken.add(url);
        changed = true;
      }
    }

    if (changed) this.imageFallbackNonce.update((value) => value + 1);
  }

  autoZoneOf(c: RiftboundCardLite): RiftboundZone {
    if (c.card_type === 'rune') return 'rune';
    if (c.card_type === 'legend') return 'champion';
    if (c.card_type === 'battlefield') return 'bg';
    return 'main';
  }

  /**
   * Zonas extra (más allá de Main/Side) que se muestran como botones en la
   * mini-card. Para tipos conocidos derivamos de `autoZoneOf`. Para `other`
   * (data del scraper sin clasificar bien) ofrecemos las 3 zonas especiales
   * para que el usuario pueda colocar manualmente Champion Legend / Battlefield / Runa.
   */
  extraZonesFor(c: RiftboundCardLite): RiftboundZone[] {
    if (c.card_type === 'other') return ['champion', 'bg', 'rune'];
    const z = this.autoZoneOf(c);
    return (z === 'main' || z === 'side') ? [] : [z];
  }

  canShowMainSide(c: RiftboundCardLite): boolean {
    // Cualquier carta que NO tenga zona dedicada (runa/battlefield/legend)
    // puede ir al main o sideboard. Eso incluye unit/spell/gear/champion y
    // cualquier tipo no reconocido (`other`, etc.).
    return !['rune', 'battlefield', 'legend'].includes(c.card_type);
  }

  // ── Conteos de copias ──
  getQuantityInZone(cardId: number, z: RiftboundZone): number {
    return this.entries()[z].find(e => e.card.id === cardId)?.quantity ?? 0;
  }

  getQuantityInDeck(cardId: number): number {
    return this.zones.reduce((s, z) => s + this.getQuantityInZone(cardId, z), 0);
  }

  /** Cuenta copias por NOMBRE (en cualquier zona excepto rune/bg). */
  getNameCount(name: string): number {
    let n = 0;
    for (const z of this.zones) {
      for (const e of this.entries()[z]) {
        if (e.card.name === name) n += e.quantity;
      }
    }
    return n;
  }

  getMaxCopies(c: RiftboundCardLite): number {
    // Banlist: 'banned' = 0 copias, 'limited' = max_copies (típicamente 1)
    const ban = c.card_number ? this.banlist().get(c.card_number) : undefined;
    if (ban) {
      if (ban.status === 'banned') return 0;
      if (ban.status === 'limited' || ban.status === 'restricted') return ban.max_copies ?? 1;
    }
    if (c.name === 'Spiderling') return 50; // override hardcodeado para la carta Spiderling (que es una unidad que tiene la posibilidad de jugarse por la cantidad de copias que quieras, pero el límite de la zona main es 40, así que no hay problema).
    if (c.card_type === 'battlefield') return 1;
    if (c.card_type === 'legend') return 1;
    if (c.card_type === 'rune') return this.rules.rune;
    return 3;
  }

  isBanned(c: RiftboundCardLite): boolean {
    const ban = c.card_number ? this.banlist().get(c.card_number) : undefined;
    return ban?.status === 'banned';
  }

  banStatus(c: RiftboundCardLite): string | null {
    const ban = c.card_number ? this.banlist().get(c.card_number) : undefined;
    return ban?.status ?? null;
  }

  maxCopiesForEntry(e: BuilderEntry): number {
    if (e.card.name === 'Spiderling') return 50; // ejemplo de override hardcodeado para la carta Spiderling (que es una unidad que tiene la posibilidad de jugarse por la cantidad de copias que quieras, pero el límite de la zona main es 40, así que no hay problema).
    if (e.zone === 'bg') return 1;
    if (e.zone === 'champion') return 1;
    if (e.zone === 'rune') return this.rules.rune;
    return 3;
  }

  canAddToAuto(c: RiftboundCardLite, z: RiftboundZone): boolean {
    const total = this.zoneCount(z);
    if (z === 'rune' && total >= this.rules.rune) return false;
    if (z === 'champion' && total >= this.rules.champion) return false;
    if (z === 'bg') {
      if (total >= this.rules.bg) return false;
      // todos distintos
      if (this.getQuantityInZone(c.id, 'bg') >= 1) return false;
    }
    return this.getNameCount(c.name) < this.getMaxCopies(c);
  }

  // ── Mutadores ──
  addToZone(c: RiftboundCardLite, z: RiftboundZone) {
    // Límite duro de tamaño de zona (main: 40, side: 10, etc.).
    if (z === 'main' && this.zoneCount('main') >= this.rules.main) return;
    if (z === 'side' && this.zoneCount('side') >= this.rules.side) return;
    const list = [...this.entries()[z]];
    const existing = list.find(e => e.card.id === c.id);
    // Máximo por zona (champion/bg = 1), si no aplica límite por carta.
    const max = (z === 'champion' || z === 'bg') ? 1 : this.getMaxCopies(c);
    // Una carta prohibida (max === 0) no debe poder agregarse ni como primera
    // copia: antes este chequeo solo corría para `existing`, así que una
    // carta banned sin copias previas en la zona se agregaba igual (la UI lo
    // tapa deshabilitando el botón, pero el método en sí no se defendía).
    if (max <= 0) return;
    if (existing) {
      if (existing.quantity >= max) return;
      existing.quantity += 1;
    } else {
      list.push({ card: c, quantity: 1, zone: z });
    }
    this.entries.set({ ...this.entries(), [z]: list });
  }

  decZone(c: RiftboundCardLite, z: RiftboundZone) {
    const list = this.entries()[z]
      .map(e => e.card.id === c.id ? { ...e, quantity: e.quantity - 1 } : e)
      .filter(e => e.quantity > 0);
    this.entries.set({ ...this.entries(), [z]: list });
    if (this.getQuantityInZone(c.id, z) === 0 && this.expandedCardId() === c.id && this.expandedZone() === z) {
      this.collapseSelector();
    }
  }

  inc(e: BuilderEntry) {
    const max = this.maxCopiesForEntry(e);
    if (e.quantity >= max) return;
    // Respeta el tamaño máximo de la zona (main: 40, side: 10, …).
    if (e.zone === 'main' && this.zoneCount('main') >= this.rules.main) return;
    if (e.zone === 'side' && this.zoneCount('side') >= this.rules.side) return;
    e.quantity += 1;
    this.entries.set({ ...this.entries() });
  }

  dec(e: BuilderEntry) {
    if (e.quantity > 1) {
      e.quantity -= 1;
      this.entries.set({ ...this.entries() });
    } else {
      this.remove(e);
    }
  }

  remove(e: BuilderEntry) {
    const list = this.entries()[e.zone].filter(x => x.card.id !== e.card.id);
    this.entries.set({ ...this.entries(), [e.zone]: list });
  }

  // ── Stats ──
  energyDist = computed(() => {
    const dist: Record<number, number> = {};
    for (const c of this.energyBins) dist[c] = 0;
    for (const e of this.entries().main) {
      const en = e.card.energy ?? null;
      if (en === null || en === undefined) continue;
      const bucket = en >= 8 ? 8 : en;
      dist[bucket] = (dist[bucket] ?? 0) + e.quantity;
    }
    return dist;
  });

  maxEnergyCount = computed(() => Math.max(1, ...Object.values(this.energyDist())));

  colorDist = computed(() => {
    const counts: Record<string, number> = {};
    let total = 0;
    for (const z of ['main', 'side'] as RiftboundZone[]) {
      for (const e of this.entries()[z]) {
        const cs = (e.card as any).colors as string[] | undefined;
        if (!cs?.length) continue;
        for (const c of cs) {
          counts[c] = (counts[c] ?? 0) + e.quantity;
          total += e.quantity;
        }
      }
    }
    return { counts, total };
  });

  typeDist = computed(() => {
    const counts: Record<string, number> = { unit: 0, spell: 0, gear: 0 };
    let total = 0;
    for (const z of ['main', 'side'] as RiftboundZone[]) {
      for (const e of this.entries()[z]) {
        const t = (e.card.card_type ?? '').toLowerCase();
        if (t in counts) {
          counts[t] += e.quantity;
          total += e.quantity;
        }
      }
    }
    return { counts, total };
  });

  // ── Preview ──
  openPreview(c: RiftboundCardLite) {
    this.previewCard.set(c);
    this.previewDetail.set(null);
    if (!c.card_number) return;
    this.previewLoading.set(true);
    this.rb.getCard(c.card_number).subscribe({
      next: (full) => { this.previewDetail.set(full); this.previewLoading.set(false); },
      error: () => this.previewLoading.set(false),
    });
  }
  /** +1 agranda las cartas (menos por fila), -1 las achica (más por fila). */
  zoomCards(direction: 1 | -1) {
    this.cardZoom.zoom(direction, () => this.currentAutoColumns());
    // Con cartas más chicas puede quedar espacio libre: seguir cargando si hace falta.
    afterNextRender(() => { if (this.isSentinelInView()) this.loadMoreResults(); }, { injector: this.injector });
  }

  private currentAutoColumns(): number {
    const grid = this.availableCardsRef?.nativeElement;
    if (!grid) return this.cardZoom.levels()[0];
    return getComputedStyle(grid).gridTemplateColumns.split(' ').filter(Boolean).length;
  }

  closePreview() {
    this.previewCard.set(null);
    this.previewDetail.set(null);
    this.previewLoading.set(false);
  }

  openDeckPreview() {
    if (this.totalEntries() === 0) return;
    this.showDeckPreview.set(true);
  }
  closeDeckPreview() { this.showDeckPreview.set(false); }

  toggleCover(cardId: number) {
    this.coverCardId.set(this.coverCardId() === cardId ? null : cardId);
  }

  // ── Champion-first wizard ──
  /** Legend actualmente seleccionado (o null si no hay). */
  chosenLegend = computed<RiftboundCardLite | null>(() => {
    return this.entries().champion[0]?.card ?? null;
  });

  /** Filtra los legends por búsqueda. */
  filteredLegends = computed(() => {
    const q = this.legendPickerSearch().trim().toLowerCase();
    const list = this.legendOptions();
    if (!q) return list;
    return list.filter(l =>
      l.name.toLowerCase().includes(q) ||
      l.card_number.toLowerCase().includes(q),
    );
  });

  openLegendPicker() {
    this.legendPickerSearch.set('');
    this.showLegendPicker.set(true);
  }
  closeLegendPicker() { this.showLegendPicker.set(false); }

  chooseLegend(legend: RiftboundCardLite) {
    // Vacía la zona champion y coloca el nuevo legend
    this.entries.set({ ...this.entries(), champion: [{ card: legend, quantity: 1, zone: 'champion' }] });
    // Auto-aplica colores del legend como filtro (si está bloqueado)
    if (this.lockColorsToLegend()) {
      const cs = (legend as any).colors as RiftboundColor[] | undefined;
      this.selectedColors.set(new Set(cs ?? []));
    }
    this.showLegendPicker.set(false);
    this.page.set(1);
    // Si cambia el legend, descartamos el champion unit anterior (subtype distinto)
    this.championUnitId.set(null);
    this.championUnitData.set(null);
    this.championUnitOptions.set([]);
    this.loadChampionUnitsForLegend(legend);
    this.reload();
  }

  changeLegend() {
    this.openLegendPicker();
  }

  // ── Champion Unit ──
  private readonly NON_CHAMPION_TAGS = new Set([
    'champion unit', 'champion legend', 'legend', 'unit', 'signature',
  ]);

  private championKeyFromLegend(legend: RiftboundCardLite | null): string | null {
    if (!legend) return null;
    const rawTags = (legend.subtypes || [])
      .map(t => (t || '').trim())
      .filter(Boolean);

    // Prioriza un tag que aparezca en el nombre del legend (evita escoger region/faccion).
    const lowerName = (legend.name || '').toLowerCase();
    const nameMatchedTag = rawTags.find(t => {
      const tl = t.toLowerCase();
      return lowerName.startsWith(`${tl} -`)
        || lowerName.startsWith(`${tl},`)
        || lowerName === tl;
    });
    if (nameMatchedTag) return nameMatchedTag;

    const specificTag = rawTags.find(t => !this.NON_CHAMPION_TAGS.has(t.toLowerCase()));
    if (specificTag) return specificTag;

    // Fallback por nombre para datos legacy sin subtypes útiles.
    const name = (legend.name || '').trim();
    if (!name) return null;
    const [head] = name.split(/[-,]/);
    const parsed = (head || '').trim();
    return parsed || null;
  }

  private isChampionUnitCandidate(card: RiftboundCardLite, championKey: string): boolean {
    const key = championKey.toLowerCase();
    const subtypes = (card.subtypes || []).map(s => (s || '').toLowerCase());
    const hasChampionTag = subtypes.includes(key);
    const hasChampionUnitTag = subtypes.includes('champion unit');
    const name = (card.name || '').toLowerCase();
    const startsWithChampionName = name.startsWith(`${key},`) || name.startsWith(`${key} -`);

    // Las fuentes oficiales pueden omitir subtipos en unidades de campeón
    // (por ejemplo, Akali). El nombre del campeón es un respaldo válido.
    return (hasChampionTag && hasChampionUnitTag) || startsWithChampionName;
  }

  /** Tag del champion derivado del legend (subtypes -> fallback nombre). */
  championName = computed<string | null>(() => {
    return this.championKeyFromLegend(this.chosenLegend());
  });

  /** Filtra champion units por tag compartido con legend + tag/patrón de Champion Unit. */
  filteredChampionUnits = computed(() => {
    const q = this.championUnitPickerSearch().trim().toLowerCase();
    const champion = this.championName();
    let list = this.championUnitOptions();
    if (champion) {
      list = list.filter(u => this.isChampionUnitCandidate(u, champion));
    }
    if (!q) return list;
    return list.filter(u =>
      u.name.toLowerCase().includes(q) ||
      u.card_number.toLowerCase().includes(q),
    );
  });

  /** Carga units cuyo subtype contiene el tag del champion. */
  private loadChampionUnitsForLegend(legend: RiftboundCardLite) {
    const championKey = this.championKeyFromLegend(legend);
    if (!championKey) {
      this.championUnitOptions.set([]);
      this.loadingChampionUnits.set(false);
      return;
    }
    this.loadingChampionUnits.set(true);

    const fetchUnits = (
      opts: { subtype?: string; search?: string; searchMode?: 'name' | 'ability' | 'all' },
      done: (cards: RiftboundCardLite[]) => void,
    ) => {
      const all: RiftboundCardLite[] = [];
      const fetchPage = (p: number) => {
        this.rb.listCards({ type: 'unit', lite: true, page: p, ...opts }).subscribe({
          next: (resp) => {
            all.push(...(resp.results as RiftboundCardLite[]));
            if (resp.next) fetchPage(p + 1);
            else done(all);
          },
          error: () => done([]),
        });
      };
      fetchPage(1);
    };

    fetchUnits({ subtype: championKey }, (bySubtype) => {
      const validBySubtype = bySubtype.filter(u => this.isChampionUnitCandidate(u, championKey));
      if (validBySubtype.length > 0) {
        this.championUnitOptions.set(validBySubtype);
        this.loadingChampionUnits.set(false);
        return;
      }

      if (bySubtype.length > 0) {
        // Si hubo match de subtype pero ninguno califica como Champion Unit,
        // intentamos por búsqueda nominal para cubrir datos no normalizados.
      }

      fetchUnits({ search: championKey, searchMode: 'name' }, (byName) => {
        const validByName = byName.filter(u => this.isChampionUnitCandidate(u, championKey));
        this.championUnitOptions.set(validByName);
        this.loadingChampionUnits.set(false);
      });
    });
  }

  openChampionUnitPicker() {
    if (!this.chosenLegend()) return;
    this.championUnitPickerSearch.set('');
    // Si todavía no hemos cargado las opciones, hazlo ahora
    if (this.championUnitOptions().length === 0 && !this.loadingChampionUnits()) {
      const L = this.chosenLegend();
      if (L) this.loadChampionUnitsForLegend(L);
    }
    this.showChampionUnitPicker.set(true);
  }
  closeChampionUnitPicker() { this.showChampionUnitPicker.set(false); }

  chooseChampionUnit(unit: RiftboundCardLite) {
    this.championUnitId.set(unit.id);
    this.championUnitData.set(unit);
    // Asegura que la unidad esté en el main deck (1 copia mínimo)
    const current = this.entries();
    const existing = current.main.find(e => e.card.id === unit.id);
    if (!existing) {
      this.entries.set({
        ...current,
        main: [...current.main, { card: unit, quantity: 1, zone: 'main' }],
      });
    }
    this.showChampionUnitPicker.set(false);
  }

  clearChampionUnit() {
    this.championUnitId.set(null);
    this.championUnitData.set(null);
  }

  changeChampionUnit() { this.openChampionUnitPicker(); }

  toggleLockColors() {
    this.lockColorsToLegend.update(v => !v);
    if (this.lockColorsToLegend()) {
      const legend = this.chosenLegend();
      if (legend) {
        const cs = (legend as any).colors as RiftboundColor[] | undefined;
        this.selectedColors.set(new Set(cs ?? []));
        this.reload();
      }
    }
  }

  colorHex(code: string): string {
    return this.colors.find(c => c.code === code)?.hex ?? '#888';
  }

  // ── Borrador en localStorage ──
  /** Clave de localStorage para borradores de mazos nuevos. */
  private readonly DRAFT_KEY = 'riftbound:builder:draft:v1';

  /** Guarda el estado actual (solo para mazos nuevos, no para edicion). */
  saveDraft() {
    if (this.deckId()) return; // editando uno existente: no guardamos borrador
    try {
      const entries = this.entries();
      const flat: { card_id: number; quantity: number; zone: RiftboundZone }[] = [];
      for (const z of this.zones) {
        for (const e of entries[z]) {
          flat.push({ card_id: e.card.id, quantity: e.quantity, zone: z });
        }
      }
      // Snapshot de las cartas (para reconstruir entries sin volver a pedir al backend).
      const cardSnapshots: Record<number, RiftboundCardLite> = {};
      for (const z of this.zones) {
        for (const e of entries[z]) cardSnapshots[e.card.id] = e.card;
      }
      const cu = this.championUnitData();
      if (cu) cardSnapshots[cu.id] = cu;

      const draft = {
        savedAt: Date.now(),
        deckName: this.deckName,
        description: this.description,
        isPublic: this.isPublic,
        coverCardId: this.coverCardId(),
        championUnitId: this.championUnitId(),
        entries: flat,
        cardSnapshots,
      };
      localStorage.setItem(this.DRAFT_KEY, JSON.stringify(draft));
    } catch {
      // localStorage lleno o no disponible: ignorar silenciosamente.
    }
  }

  /** Restaura un borrador previo si existe. Devuelve true si lo aplico. */
  restoreDraft(): boolean {
    try {
      const raw = localStorage.getItem(this.DRAFT_KEY);
      if (!raw) return false;
      const draft = JSON.parse(raw);
      if (!draft || typeof draft !== 'object') return false;

      this.deckName = draft.deckName ?? this.deckName;
      this.description = draft.description ?? '';
      this.isPublic = draft.isPublic ?? false;
      this.coverCardId.set(draft.coverCardId ?? null);
      this.championUnitId.set(draft.championUnitId ?? null);

      const snapshots: Record<number, RiftboundCardLite> = draft.cardSnapshots ?? {};
      const map: Record<RiftboundZone, BuilderEntry[]> = {
        main: [], side: [], rune: [], champion: [], bg: [],
      };
      for (const e of (draft.entries ?? []) as { card_id: number; quantity: number; zone: RiftboundZone }[]) {
        const card = snapshots[e.card_id];
        if (card && map[e.zone]) {
          map[e.zone].push({ card, quantity: e.quantity, zone: e.zone });
        }
      }
      this.sortAllZonesInPlace(map);
      this.entries.set(map);

      // Champion unit data desde snapshots
      const cuId = this.championUnitId();
      if (cuId && snapshots[cuId]) this.championUnitData.set(snapshots[cuId]);

      // Si el borrador tenia legend, recargar opciones de champion units
      const legend = map.champion[0]?.card;
      if (legend) this.loadChampionUnitsForLegend(legend);

      return true;
    } catch {
      return false;
    }
  }

  /** Borra el borrador de localStorage. */
  clearDraft() {
    try { localStorage.removeItem(this.DRAFT_KEY); } catch { /* noop */ }
  }

  /** Descarta el borrador y limpia el formulario. */
  discardDraft() {
    if (!confirm('¿Descartar el borrador actual? Se perdera lo que tengas sin guardar.')) return;
    this.clearDraft();
    this.deckName = 'Nuevo mazo Riftbound';
    this.description = '';
    this.isPublic = false;
    this.coverCardId.set(null);
    this.championUnitId.set(null);
    this.championUnitData.set(null);
    this.championUnitOptions.set([]);
    this.entries.set({ main: [], side: [], rune: [], champion: [], bg: [] });
    this.errors.set([]);
  }

  /** ¿Hay algun contenido digno de guardar? */
  private hasDraftContent(): boolean {
    if (this.deckId()) return false;
    const e = this.entries();
    for (const z of this.zones) if (e[z].length > 0) return true;
    if (this.championUnitId()) return true;
    if ((this.deckName || '').trim() && this.deckName !== 'Nuevo mazo Riftbound') return true;
    if ((this.description || '').trim()) return true;
    return false;
  }

  ngOnDestroy() {
    this.cardZoom.destroy();
    this.gridResizeObserver?.disconnect();
    this.cardsObserver?.disconnect();
    this.detachContentScrollListener();
    if (this.hasDraftContent()) this.saveDraft();
  }

  @HostListener('window:beforeunload')
  onBeforeUnload() {
    if (this.hasDraftContent()) this.saveDraft();
  }

  // ── Save ──
  async save() {
    if (!this.auth.isAuthenticated()) {
      // Conservamos lo armado: el builder restaura el borrador al volver del login.
      this.saveDraft();
      this.errors.set(['Inicia sesión para guardar tu mazo. Tu borrador quedará guardado.']);
      this.router.navigate(['/login'], { queryParams: { returnUrl: this.router.url } });
      return;
    }
    const badZones = this.zones.filter(z => !this.isZoneOk(z));
    if (this.isPublic && badZones.length) {
      const detail = badZones.map(z => `${this.labels[z]} ${this.zoneCount(z)}/${this.rules[z]}`).join(', ');
      const choice = await this.dialog.open({
        title: 'Mazo incompleto',
        message: `Tu mazo aún no cumple las reglas (${detail}). ¿Quieres publicarlo igual o guardarlo como privado hasta completarlo?`,
        actions: [
          { value: 'back', label: 'Volver', style: 'secondary' },
          { value: 'private', label: 'Guardar privado', style: 'secondary' },
          { value: 'public', label: 'Publicar igual', style: 'primary' },
        ],
      });
      if (choice === null || choice === 'back') return;
      if (choice === 'private') this.isPublic = false;
    }
    this.saving.set(true);
    this.errors.set([]);
    const flat: Partial<RiftboundDeckEntry>[] = [];
    for (const z of this.zones) {
      for (const e of this.entries()[z]) {
        flat.push({ card: e.card.id, quantity: e.quantity, zone: z });
      }
    }
    const payload: Partial<RiftboundDeck> = {
      name: this.deckName,
      description: this.description,
      is_public: this.isPublic,
      cover_card: this.coverCardId() as any,
      champion_unit: this.championUnitId() as any,
      entries: flat as RiftboundDeckEntry[],
    };
    const obs = this.deckId()
      ? this.rb.updateDeck(this.deckId()!, payload)
      : this.rb.createDeck(payload);
    obs.subscribe({
      next: (deck) => {
        this.saving.set(false);
        // El mazo se guarda aunque este incompleto: la validacion es solo informativa.
        // Marcamos como persistido (deckId no nulo) para que ngOnDestroy no
        // vuelva a guardar el borrador al navegar fuera del builder.
        this.deckId.set(deck.id);
        this.clearDraft();
        this.router.navigate(['/riftbound/decks', deck.id]);
      },
      error: (err) => {
        this.saving.set(false);
        if (err?.status === 401) {
          this.errors.set(['Tu sesión expiró. Inicia sesión nuevamente para guardar.']);
        } else if (err?.status === 400 && Array.isArray(err?.error?.entries)) {
          this.errors.set(err.error.entries);
        } else {
          this.errors.set([err?.error?.detail || 'Error al guardar.']);
        }
      },
    });
  }
}
