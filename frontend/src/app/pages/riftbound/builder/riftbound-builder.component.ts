import {
  AfterViewInit,
  Component,
  ElementRef,
  HostListener,
  OnDestroy,
  OnInit,
  ViewChild,
  computed,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { RiftboundService } from '../../../services/riftbound.service';
import {
  RiftboundCard, RiftboundCardLite, RiftboundDeck, RiftboundDeckEntry,
  RiftboundZone, RIFTBOUND_ZONE_RULES, RIFTBOUND_ZONE_LABELS, RiftboundColor,
} from '../../../models/riftbound';
import { TcgPriceComponent } from '../../../components/tcg-price/tcg-price.component';
import { IconComponent } from '../../../components/icon/icon.component';

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

const COLORS: { code: RiftboundColor; label: string; hex: string }[] = [
  { code: 'fury',  label: 'Fury',  hex: '#f87171' },
  { code: 'calm',  label: 'Calm',  hex: '#34d399' },
  { code: 'mind',  label: 'Mind',  hex: '#38bdf8' },
  { code: 'body',  label: 'Body',  hex: '#fb923c' },
  { code: 'chaos', label: 'Chaos', hex: '#c084fc' },
  { code: 'order', label: 'Order', hex: '#f472b6' },
];

const TYPES = [
  { code: 'unit', label: 'Unidad' },
  { code: 'spell', label: 'Hechizo' },
  { code: 'champion', label: 'Champion' },
  { code: 'legend', label: 'Legend' },
  { code: 'gear', label: 'Gear' },
  { code: 'battlefield', label: 'Battlefield' },
  { code: 'rune', label: 'Runa' },
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
      <div class="card-browser" [class.mobile-hidden]="activeMobileTab() === 'deck'">
        <div class="browser-head">
          <div class="browser-title-wrap">
            <h2>Cartas Riftbound</h2>
            <span class="format-badge">{{ totalCount() }} disponibles</span>
          </div>
        </div>

        <div class="browser-filters">
          <div class="search-row">
            <div class="search-modes" role="tablist" aria-label="Modo de búsqueda">
              <button type="button" role="tab"
                      [class.active]="searchMode === 'name'"
                      (click)="setMode('name')"
                      title="Buscar por nombre o número">Nombre</button>
              <button type="button" role="tab"
                      [class.active]="searchMode === 'ability'"
                      (click)="setMode('ability')"
                      title="Buscar dentro del texto de habilidad">Habilidad</button>
              <button type="button" role="tab"
                      [class.active]="searchMode === 'all'"
                      (click)="setMode('all')"
                      title="Buscar en nombre y habilidad">Todo</button>
            </div>
            <div class="search-input-row">
              <app-icon name="search" [size]="15" class="search-input-icon"></app-icon>
              <input
                type="search"
                [(ngModel)]="searchQuery"
                (ngModelChange)="onSearchInput()"
                [placeholder]="searchMode === 'ability' ? 'Buscar habilidad…' : (searchMode === 'all' ? 'Buscar nombre o habilidad…' : 'Buscar nombre o número…')" />
              <button class="search-btn" (click)="reload()" title="Buscar">
                <app-icon name="search" [size]="14"></app-icon>
              </button>
            </div>
          </div>

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

          <div class="filter-row">
            <div class="multi-filter">
              <label class="filter-label">Set</label>
              <select [(ngModel)]="setFilter" (ngModelChange)="page.set(1); reload()">
                <option value="">Todos los sets</option>
                @for (s of sets(); track s.code) {
                  <option [value]="s.code">{{ s.code }} — {{ s.name }}</option>
                }
              </select>
            </div>

            <div class="multi-filter">
              <label class="filter-label">Energía</label>
              <select [(ngModel)]="energyFilter" (ngModelChange)="page.set(1); reload()">
                <option [ngValue]="null">Cualquiera</option>
                @for (n of [0,1,2,3,4,5,6,7,8]; track n) {
                  <option [ngValue]="n">{{ n }}</option>
                }
              </select>
            </div>

            <div class="multi-filter">
              <label class="filter-label">Rareza</label>
              <select [(ngModel)]="rarityFilter" (ngModelChange)="page.set(1); reload()">
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

        @if (loading()) {
          <p class="muted">Cargando…</p>
        }

        <div class="available-cards" #availableCardsEl>
          @for (card of displayedResults(); track card.id) {
            <div class="mini-card"
                 [class.in-deck]="getQuantityInDeck(card.id) > 0"
                 [class.maxed]="getQuantityInDeck(card.id) >= getMaxCopies(card)"
                 [class.banned]="isBanned(card)"
                 [class.limited]="banStatus(card) === 'limited' || banStatus(card) === 'restricted'">
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
                    <app-icon name="ban" [size]="11"></app-icon>
                  </span>
                } @else if (banStatus(card)) {
                  <span class="ban-badge ban-badge-limited" title="Limitada en Standard">
                    <app-icon name="shield-alert" [size]="11"></app-icon>
                  </span>
                }
              </div>
              <div class="mini-info">
                <span class="mini-name">{{ card.name }}</span>
                <div class="mini-type-row">
                  <span class="mini-type">{{ typeLabel(card.card_type) }}</span>
                  @if (card.energy !== null && card.energy !== undefined) {
                    <span class="stat-pill cost" title="Energía">{{ card.energy }}</span>
                  }
                  @if (card.might !== null && card.might !== undefined) {
                    <span class="stat-pill damage" title="Fuerza">{{ card.might }}</span>
                  }
                </div>
                <span class="mini-num">{{ card.card_number }}</span>
              </div>
              <div class="actions-column">
                <!-- M (main) -->
                <div class="mini-actions main-actions"
                     [class.hidden]="!canShowMainSide(card)">
                  <span class="zone-label main-label">M</span>
                  @if (getQuantityInZone(card.id, 'main') > 0) {
                    <button class="circle-btn remove" (click)="decZone(card, 'main')">−</button>
                    <span class="mini-qty">{{ getQuantityInZone(card.id, 'main') }}</span>
                  }
                  <button class="circle-btn add"
                          (click)="addToZone(card, 'main')"
                          [disabled]="zoneCount('main') >= rules.main || getNameCount(card.name) >= getMaxCopies(card)">+</button>
                </div>

                <!-- S (side) -->
                <div class="mini-actions side-actions"
                     [class.hidden]="!canShowMainSide(card)">
                  <span class="zone-label side-label">S</span>
                  @if (getQuantityInZone(card.id, 'side') > 0) {
                    <button class="circle-btn remove" (click)="decZone(card, 'side')">−</button>
                    <span class="mini-qty">{{ getQuantityInZone(card.id, 'side') }}</span>
                  }
                  <button class="circle-btn add"
                          (click)="addToZone(card, 'side')"
                          [disabled]="zoneCount('side') >= rules.side || getNameCount(card.name) >= getMaxCopies(card)">+</button>
                </div>

                <!-- Otras zonas (rune/champion/bg) -->
                @for (z of extraZonesFor(card); track z) {
                  <div class="mini-actions auto-actions">
                    <span class="zone-label auto-label">{{ zoneLetter(z) }}</span>
                    @if (getQuantityInZone(card.id, z) > 0) {
                      <button class="circle-btn remove" (click)="decZone(card, z)">−</button>
                      <span class="mini-qty">{{ getQuantityInZone(card.id, z) }}</span>
                    }
                    <button class="circle-btn add"
                            (click)="addToZone(card, z)"
                            [disabled]="!canAddToAuto(card, z)">+</button>
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
            <h2>{{ deckId() ? 'Editar Mazo' : 'Nuevo Mazo' }}</h2>
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

        <div class="deck-form-grid">
          <div class="form-group">
            <label>Nombre del mazo</label>
            <input type="text" [(ngModel)]="deckName" placeholder="Mi mazo Riftbound" />
          </div>

          <div class="form-group">
            <label>Descripción (opcional)</label>
            <input type="text" [(ngModel)]="description" placeholder="Descripción..." />
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
                  <img [src]="img" [alt]="e.card.name" (error)="onCardImageError(e.card, $event)" />
                } @else {
                  <div class="entry-img-fallback">{{ e.card.card_number }}</div>
                }
                <div class="entry-info">
                  <span class="entry-name">{{ e.card.name }}</span>
                  <span class="entry-meta">
                    {{ e.card.card_number }}
                    @if (e.card.energy !== null && e.card.energy !== undefined) { · Energía: {{ e.card.energy }} }
                  </span>
                </div>
                <div class="entry-controls">
                  <button class="ctrl-btn" (click)="dec(e)">−</button>
                  <span class="entry-qty">{{ e.quantity }}</span>
                  <button class="ctrl-btn" (click)="inc(e)"
                          [disabled]="e.quantity >= maxCopiesForEntry(e)">+</button>
                  <button class="ctrl-btn remove" (click)="remove(e)">✕</button>
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
                            <img [src]="img" [alt]="e.card.name" (error)="onCardImageError(e.card, $event)" />
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
                <h3 class="preview-title">{{ c.name }}</h3>
                <p class="muted">{{ c.card_number }} · {{ c.set?.name || c.set?.code || '—' }}</p>
                <div class="preview-meta-badges">
                  @if (c.card_type) { <span class="stat-badge">{{ c.card_type }}</span> }
                  @if (c.rarity) { <span class="stat-badge rarity">{{ c.rarity }}</span> }
                  @if (c.variant) { <span class="stat-badge">{{ c.variant }}</span> }
                  @for (col of c.colors; track col) { <span class="stat-badge" [style.color]="col">{{ col }}</span> }
                  @for (st of c.subtypes; track st) { <span class="stat-badge">{{ st }}</span> }
                </div>
                <div class="preview-stats-row">
                  @if (c.energy != null) { <div class="stat-item"><span class="stat-label">Energy</span><span class="stat-val">{{ c.energy }}</span></div> }
                  @if (c.power != null) { <div class="stat-item"><span class="stat-label">Power</span><span class="stat-val">{{ c.power }}</span></div> }
                  @if (c.might != null) { <div class="stat-item"><span class="stat-label">Might</span><span class="stat-val">{{ c.might }}</span></div> }
                </div>
                @if (c.description) {
                  <div class="preview-ability-box">
                    <span class="ability-title">Descripción</span>
                    <p class="ability-text">{{ c.description }}</p>
                  </div>
                }
                <app-tcg-price [cardName]="c.name" [compact]="false" [showLink]="true"></app-tcg-price>
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
          <input type="search" [ngModel]="legendPickerSearch()" (ngModelChange)="legendPickerSearch.set($event)"
                 placeholder="Buscar por nombre…" class="lp-search" style="width: 100%; padding: 0.5rem; margin-bottom: 1rem; background: rgba(18,18,23,0.8); border: 1px solid var(--ui-border); border-radius: 6px; color: #fff;" />
          <div class="lp-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 0.75rem; max-height: 60vh; overflow-y: auto;">
            @for (L of filteredLegends(); track L.id) {
              <button type="button" class="lp-card" (click)="chooseLegend(L)" style="background: rgba(24,24,27,0.7); border: 1px solid var(--ui-border); border-radius: 8px; padding: 0.5rem; cursor: pointer; color: #fff; text-align: center;">
                @if (cardImageUrl(L); as img) {
                  <img [src]="img" [alt]="L.name" style="width: 100%; border-radius: 4px;" (error)="onCardImageError(L, $event)" />
                } @else {
                  <div class="lp-img-fallback">{{ L.card_number }}</div>
                }
                <div class="lp-name" style="font-size: 0.78rem; font-weight: 600; margin-top: 0.25rem;">{{ L.name }}</div>
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
          <input type="search" [ngModel]="championUnitPickerSearch()" (ngModelChange)="championUnitPickerSearch.set($event)"
                 placeholder="Buscar por nombre…" class="lp-search" style="width: 100%; padding: 0.5rem; margin-bottom: 1rem; background: rgba(18,18,23,0.8); border: 1px solid var(--ui-border); border-radius: 6px; color: #fff;" />
          <div class="lp-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 0.75rem; max-height: 60vh; overflow-y: auto;">
            @for (U of filteredChampionUnits(); track U.id) {
              <button type="button" class="lp-card" (click)="chooseChampionUnit(U)" style="background: rgba(24,24,27,0.7); border: 1px solid var(--ui-border); border-radius: 8px; padding: 0.5rem; cursor: pointer; color: #fff; text-align: center;">
                @if (cardImageUrl(U); as img) {
                  <img [src]="img" [alt]="U.name" style="width: 100%; border-radius: 4px;" (error)="onCardImageError(U, $event)" />
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

    .builder-layout {
      display: grid; grid-template-columns: 65% 35%; gap: 1.25rem;
      height: calc(100vh - 60px); max-width: 1700px; margin: 0 auto;
      padding: 1rem 1.5rem; overflow: hidden; box-sizing: border-box;
    }
    @media (max-width: 960px) {
      .builder-layout { display: block; height: auto; padding: 0.75rem; }
      .mobile-builder-switcher { display: flex; }
      .mobile-hidden { display: none !important; }
    }

    .card-browser, .deck-panel {
      display: flex; flex-direction: column; height: 100%; min-height: 0;
      background: rgba(24, 24, 27, 0.45); border: 1px solid var(--ui-border);
      border-radius: 12px; padding: 1.2rem; overflow-y: auto; box-sizing: border-box;
      backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
    }

    .browser-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.85rem; }
    .browser-title-wrap h2 { font-size: 1.05rem; font-weight: 700; color: #ffffff; margin: 0; }
    .format-badge { font-size: 0.75rem; color: #06b6d4; font-weight: 500; }

    .browser-filters { display: flex; flex-direction: column; gap: 0.55rem; margin-bottom: 1rem; }
    .search-row { display: flex; flex-direction: column; gap: 0.5rem; }
    .search-modes {
      display: flex; background: rgba(18, 18, 23, 0.6); border: 1px solid var(--ui-border);
      border-radius: 6px; padding: 2px; gap: 2px;
    }
    .search-modes button {
      flex: 1; padding: 0.3rem 0.4rem; border: none; background: transparent;
      color: var(--ui-text-muted); border-radius: 4px; font-size: 0.78rem; cursor: pointer;
    }
    .search-modes button.active { background: #06b6d4; color: #09090b; font-weight: 600; }

    .search-input-row { position: relative; display: flex; align-items: center; gap: 0.4rem; }
    .search-input-icon { position: absolute; left: 0.75rem; color: var(--ui-text-muted); }
    .search-input-row input {
      flex: 1; padding: 0.5rem 0.75rem 0.5rem 2.2rem; background: rgba(18, 18, 23, 0.8);
      border: 1px solid var(--ui-border); border-radius: 8px; color: #ffffff; font-size: 0.85rem; outline: none;
    }
    .search-input-row input:focus { border-color: #06b6d4; box-shadow: 0 0 10px rgba(6, 182, 212, 0.2); }
    .search-btn {
      padding: 0.5rem 0.75rem; background: #06b6d4; color: #09090b; border: none;
      border-radius: 8px; cursor: pointer; font-weight: 600; display: flex; align-items: center;
    }

    .type-chips { display: flex; flex-wrap: wrap; gap: 0.35rem; }
    .type-chip-btn {
      padding: 0.28rem 0.6rem; background: rgba(39, 39, 42, 0.3); border: 1px solid var(--ui-border);
      border-radius: 6px; color: var(--ui-text-secondary); font-size: 0.75rem; cursor: pointer;
    }
    .type-chip-btn.active { background: rgba(6, 182, 212, 0.15); border-color: #06b6d4; color: #06b6d4; font-weight: 600; }

    .filter-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem; }
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

    .available-cards { display: flex; flex-direction: column; gap: 0.45rem; flex: 1; overflow-y: auto; }
    .mini-card {
      display: flex; align-items: center; gap: 0.65rem; padding: 0.4rem 0.6rem;
      background: rgba(18, 18, 23, 0.6); border: 1px solid var(--ui-border); border-radius: 8px;
      position: relative;
    }
    .mini-card:hover { border-color: rgba(255, 255, 255, 0.2); background: rgba(24, 24, 27, 0.85); }
    .mini-card.in-deck { border-color: rgba(6, 182, 212, 0.4); background: rgba(6, 182, 212, 0.08); }

    .img-wrapper {
      position: relative; width: 38px; height: 52px; border-radius: 4px; overflow: hidden;
      flex-shrink: 0; background: #121217; border: 1px solid var(--ui-border); cursor: pointer;
    }
    .img-wrapper img { width: 100%; height: 100%; object-fit: cover; }
    .eye-btn {
      position: absolute; inset: 0; background: rgba(0, 0, 0, 0.6); border: none;
      color: #ffffff; display: flex; align-items: center; justify-content: center;
      opacity: 0; cursor: pointer; transition: opacity 0.15s ease;
    }
    .img-wrapper:hover .eye-btn { opacity: 1; }

    .mini-info { flex: 1; min-width: 0; }
    .mini-name { font-size: 0.82rem; font-weight: 600; color: #ffffff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .mini-type-row { display: flex; align-items: center; gap: 0.35rem; margin-top: 2px; }
    .mini-type { font-size: 0.72rem; color: var(--ui-text-muted); }
    .mini-num { font-size: 0.65rem; color: var(--ui-text-muted); }

    .stat-pill {
      padding: 1px 5px; border-radius: 4px; font-size: 0.68rem; font-weight: 700; line-height: 1;
    }
    .stat-pill.cost { background: rgba(6, 182, 212, 0.15); color: #06b6d4; border: 1px solid rgba(6, 182, 212, 0.3); }
    .stat-pill.damage { background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); }

    .actions-column { display: flex; flex-direction: column; gap: 0.25rem; flex-shrink: 0; }
    .mini-actions { display: flex; align-items: center; gap: 0.25rem; }
    .zone-label { font-size: 0.65rem; font-weight: 700; width: 10px; color: var(--ui-text-muted); }
    .mini-qty { font-size: 0.75rem; font-weight: 700; color: #06b6d4; min-width: 12px; text-align: center; }

    .circle-btn {
      width: 22px; height: 22px; border-radius: 50%; border: 1px solid var(--ui-border);
      background: rgba(39, 39, 42, 0.6); color: #ffffff; font-size: 0.75rem; font-weight: 700;
      display: flex; align-items: center; justify-content: center; cursor: pointer;
    }
    .circle-btn.add:hover:not(:disabled) { background: #06b6d4; border-color: #06b6d4; color: #09090b; }
    .circle-btn.remove:hover { background: #ef4444; border-color: #ef4444; color: #ffffff; }

    /* Deck Panel & Cards */
    .deck-header {
      display: flex; justify-content: space-between; align-items: center;
      padding-bottom: 0.85rem; border-bottom: 1px solid var(--ui-border); margin-bottom: 1rem;
    }
    .deck-header-info { display: flex; align-items: center; gap: 0.75rem; }
    .deck-header-info h2 { font-size: 1.15rem; font-weight: 700; color: #ffffff; margin: 0; }
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

    .deck-form-grid {
      display: grid; grid-template-columns: 1fr 1fr auto; gap: 0.75rem; align-items: flex-end; margin-bottom: 1rem;
    }
    .form-group label { display: block; font-size: 0.72rem; color: var(--ui-text-muted); margin-bottom: 2px; }
    .form-group input {
      width: 100%; padding: 0.45rem 0.75rem; background: rgba(18, 18, 23, 0.8);
      border: 1px solid var(--ui-border); border-radius: 6px; color: #ffffff; font-size: 0.85rem; outline: none;
    }
    .checkbox-label { display: flex; align-items: center; gap: 0.35rem; font-size: 0.78rem; color: var(--ui-text-secondary); }

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
    .deck-entry img { width: 32px; height: 44px; border-radius: 4px; object-fit: cover; border: 1px solid var(--ui-border); }
    .entry-info { flex: 1; min-width: 0; }
    .entry-name { font-size: 0.84rem; font-weight: 600; color: #ffffff; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .entry-meta { font-size: 0.72rem; color: var(--ui-text-muted); }
    .entry-controls { display: flex; align-items: center; gap: 0.3rem; }
    .entry-qty { font-size: 0.82rem; font-weight: 700; color: #06b6d4; min-width: 14px; text-align: center; }

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
    .dp-head, .modal-head { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--ui-border); padding-bottom: 0.85rem; margin-bottom: 1rem; }
    .dp-head h2, .modal-head h3 { font-size: 1.15rem; font-weight: 700; color: #ffffff; margin: 0; display: flex; align-items: center; gap: 0.4rem; }
    .dp-close, .modal-close, .preview-close {
      background: rgba(39, 39, 42, 0.5); border: 1px solid var(--ui-border); border-radius: 6px;
      color: var(--ui-text-muted); cursor: pointer; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;
    }
  `],
})
export class RiftboundBuilderComponent implements OnInit, AfterViewInit, OnDestroy {
  private rb = inject(RiftboundService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

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
  isPublic = true;
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
  selectedColors = signal(new Set<RiftboundColor>());

  results = signal<RiftboundCardLite[]>([]);
  hasMore = signal(false);

  /** Cartas mostradas en el listado: oculta los demás legends cuando ya hay
   *  uno seleccionado (un mazo solo puede tener 1 Champion Legend). */
  displayedResults = computed<RiftboundCardLite[]>(() => {
    const list = this.results();
    const L = this.chosenLegend();
    if (!L) return list;
    return list.filter(c => c.card_type !== 'legend' || c.id === L.id);
  });
  loading = signal(false);
  page = signal(1);
  totalCount = signal(0);
  // Debe coincidir con DRF PAGE_SIZE (backend/backend/settings.py).
  pageSize = 20;
  totalPages = computed(() => Math.max(1, Math.ceil(this.totalCount() / this.pageSize)));
  private cardsSentinelRef?: ElementRef<HTMLElement>;
  private cardsObserver?: IntersectionObserver;
  private contentScrollEl: HTMLElement | null = null;
  @ViewChild('availableCardsEl') availableCardsRef?: ElementRef<HTMLElement>;

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

  @HostListener('window:resize')
  onWindowResize() { this.tryInfiniteScrollFallback(); }

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
    this.rb.listCards({ type: 'legend', lite: true, page: 1 }).subscribe({
      next: (resp) => {
        // Cargar todas las páginas (hay ~66 legends)
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
          this.rb.listCards({ type: 'legend', lite: true, page: p }).subscribe({
            next: (r) => { all.push(...(r.results as RiftboundCardLite[])); fetchPage(p + 1); },
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
    this.tryInfiniteScrollFallback();
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
        setTimeout(() => {
          this.setupCardsObserver();
          this.tryInfiniteScrollFallback();
        });
      },
      error: () => this.loading.set(false),
    });
  }

  private setupCardsObserver() {
    if (typeof IntersectionObserver === 'undefined') return;
    this.cardsObserver?.disconnect();
    const sentinel = this.cardsSentinelRef?.nativeElement;
    if (!sentinel) return;
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
  }

  private attachContentScrollListener() {
    this.detachContentScrollListener();
    const el = this.availableCardsRef?.nativeElement
      ?? document.querySelector('.available-cards') as HTMLElement | null;
    if (!el) return;
    this.contentScrollEl = el;
    this.contentScrollEl.addEventListener('scroll', this.onContentScroll, { passive: true });
  }

  private detachContentScrollListener() {
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
    const container = this.contentScrollEl ?? this.availableCardsRef?.nativeElement;
    if (!container) return false;
    return container.scrollTop + container.clientHeight >= container.scrollHeight - offset;
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
      this.isPublic = draft.isPublic ?? true;
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
    this.isPublic = true;
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
    this.cardsObserver?.disconnect();
    this.detachContentScrollListener();
    if (this.hasDraftContent()) this.saveDraft();
  }

  @HostListener('window:beforeunload')
  onBeforeUnload() {
    if (this.hasDraftContent()) this.saveDraft();
  }

  // ── Save ──
  save() {
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
        this.errors.set([err?.error?.detail || 'Error al guardar.']);
      },
    });
  }
}
