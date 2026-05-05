import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { RiftboundService } from '../../../services/riftbound.service';
import {
  RiftboundCard, RiftboundCardLite, RiftboundDeck, RiftboundDeckEntry,
  RiftboundZone, RIFTBOUND_ZONE_RULES, RIFTBOUND_ZONE_LABELS, RiftboundColor,
} from '../../../models/riftbound';

interface BuilderEntry {
  card: RiftboundCardLite;
  quantity: number;
  zone: RiftboundZone;
}

const COLORS: { code: RiftboundColor; label: string; hex: string }[] = [
  { code: 'fury',  label: 'Fury',  hex: '#e94560' },
  { code: 'calm',  label: 'Calm',  hex: '#4caf50' },
  { code: 'mind',  label: 'Mind',  hex: '#3aa6ff' },
  { code: 'body',  label: 'Body',  hex: '#ff9a3c' },
  { code: 'chaos', label: 'Chaos', hex: '#9c5dff' },
  { code: 'order', label: 'Order', hex: '#ffd23c' },
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

@Component({
  selector: 'app-riftbound-builder',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="builder-layout">
      <!-- ── Card Browser ── -->
      <div class="card-browser">
        <h2>Cartas Riftbound · {{ totalCount() }}</h2>

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
            <input
              type="search"
              [(ngModel)]="searchQuery"
              (ngModelChange)="onSearchInput()"
              [placeholder]="searchMode === 'ability' ? 'Buscar habilidad…' : (searchMode === 'all' ? 'Buscar nombre o habilidad…' : 'Buscar nombre o número…')" />
            <button class="search-btn" (click)="reload()" title="Buscar">🔍</button>
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
              <select [(ngModel)]="setFilter" (ngModelChange)="reload()">
                <option value="">Todos los sets</option>
                @for (s of sets(); track s.code) {
                  <option [value]="s.code">{{ s.code }} — {{ s.name }}</option>
                }
              </select>
            </div>

            <div class="multi-filter">
              <label class="filter-label">Energía</label>
              <select [(ngModel)]="energyFilter" (ngModelChange)="reload()">
                <option [ngValue]="null">Cualquiera</option>
                @for (n of [0,1,2,3,4,5,6,7,8]; track n) {
                  <option [ngValue]="n">{{ n }}</option>
                }
              </select>
            </div>

            <div class="multi-filter">
              <label class="filter-label">Rareza</label>
              <select [(ngModel)]="rarityFilter" (ngModelChange)="reload()">
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

        <div class="available-cards">
          @for (card of results(); track card.id) {
            <div class="mini-card"
                 [class.in-deck]="getQuantityInDeck(card.id) > 0"
                 [class.maxed]="getQuantityInDeck(card.id) >= getMaxCopies(card)"
                 [class.banned]="isBanned(card)"
                 [class.limited]="banStatus(card) === 'limited' || banStatus(card) === 'restricted'">
              <div class="img-wrapper" (click)="openPreview(card)">
                @if (card.image) {
                  <img [src]="card.image" [alt]="card.name" loading="lazy" decoding="async" />
                } @else {
                  <div class="img-placeholder">{{ card.card_number }}</div>
                }
                <span class="eye-icon">👁</span>
                @if (isBanned(card)) {
                  <span class="ban-badge ban-badge-banned" title="Prohibida en Standard">🚫</span>
                } @else if (banStatus(card)) {
                  <span class="ban-badge ban-badge-limited" title="Limitada en Standard">⚠</span>
                }
              </div>
              <div class="mini-info">
                <span class="mini-name">{{ card.name }}</span>
                <span class="mini-type">
                  {{ typeLabel(card.card_type) }}
                  @if (card.energy !== null && card.energy !== undefined) { · ⚡{{ card.energy }} }
                  @if (card.might !== null && card.might !== undefined) { · ⚔️{{ card.might }} }
                </span>
                <span class="mini-num">{{ card.card_number }}</span>
                @if (card.description) {
                  <p class="mini-ability">{{ card.description }}</p>
                }
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
                          [disabled]="getNameCount(card.name) >= getMaxCopies(card)">+</button>
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

        @if (!loading() && results().length === 0) {
          <p class="muted center">Sin resultados.</p>
        }

        @if (totalPages() > 1) {
          <div class="pagination">
            <button class="page-btn" (click)="prev()" [disabled]="page() === 1">←</button>
            <span>{{ page() }} / {{ totalPages() }}</span>
            <button class="page-btn" (click)="next()" [disabled]="page() >= totalPages()">→</button>
          </div>
        }
      </div>

      <!-- ── Deck Panel ── -->
      <div class="deck-panel" [class.mobile-visible]="showDeckPanel()">
        <div class="deck-header">
          <h2>{{ deckId() ? 'Editar Mazo' : 'Nuevo Mazo' }}</h2>
          <button class="mobile-close-btn" (click)="showDeckPanel.set(false)">✕</button>
        </div>

        <!-- Champion Legend del mazo -->
        <div class="legend-banner" [class.empty]="!chosenLegend()">
          @if (chosenLegend(); as L) {
            <img [src]="L.image" [alt]="L.name" class="legend-img" />
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
                {{ lockColorsToLegend() ? '🔒 Colores' : '🔓 Colores' }}
              </button>
            </div>
          } @else {
            <button class="choose-legend-btn" (click)="openLegendPicker()">
              👑 Elige tu Champion Legend
            </button>
          }
        </div>

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
          Mazo público
        </label>

        <!-- Resumen / progreso -->
        <div class="zones-summary">
          @for (z of zones; track z) {
            <div class="zone-pill" [class.ok]="isZoneOk(z)" [class.bad]="!isZoneOk(z) && zoneCount(z) > 0">
              <span class="zp-label">{{ zoneShortLabel(z) }}</span>
              <span class="zp-count">{{ zoneCount(z) }}/{{ rules[z] }}{{ z === 'main' ? '+' : '' }}</span>
            </div>
          }
        </div>

        <!-- Curva de coste (energía del main) -->
        <div class="cost-curve">
          <span class="cost-curve-title">Curva de Energía</span>
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
                {{ zoneCount(z) }}/{{ rules[z] }}{{ z === 'main' ? '+' : '' }}
              </span>
            </div>
            @if (entries()[z].length === 0) {
              <p class="zone-empty">Vacío. Añade cartas desde el catálogo.</p>
            }
            @for (e of entries()[z]; track e.card.id) {
              <div class="deck-entry">
                @if (e.card.image) {
                  <img [src]="e.card.image" [alt]="e.card.name" />
                } @else {
                  <div class="entry-img-fallback">{{ e.card.card_number }}</div>
                }
                <div class="entry-info">
                  <span class="entry-name">{{ e.card.name }}</span>
                  <span class="entry-meta">
                    {{ e.card.card_number }}
                    @if (e.card.energy !== null && e.card.energy !== undefined) { · ⚡{{ e.card.energy }} }
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

        <button class="save-btn" (click)="save()" [disabled]="saving()">
          {{ saving() ? 'Guardando…' : (deckId() ? 'Guardar cambios' : 'Crear mazo') }}
        </button>
      </div>

      <!-- FAB para abrir el panel del mazo en móvil -->
      <button type="button" class="rb-fab" (click)="showDeckPanel.set(true)" aria-label="Abrir mazo">
        <span class="fab-count">{{ totalEntries() }}</span>
        <span class="fab-icon">📚</span>
      </button>
    </div>

    <!-- Modal preview -->
    @if (previewCard(); as pc) {
      <div class="preview-overlay" (click)="closePreview()">
        <div class="preview-box" (click)="$event.stopPropagation()">
          @if (pc.image) {
            <img [src]="pc.image" [alt]="pc.name" />
          }
          <h3>{{ pc.name }} <small>{{ pc.card_number }}</small></h3>
          <button class="preview-close" (click)="closePreview()">✕</button>
        </div>
      </div>
    }

    <!-- Modal Legend Picker -->
    @if (showLegendPicker()) {
      <div class="legend-picker-overlay" (click)="closeLegendPicker()">
        <div class="legend-picker-box" (click)="$event.stopPropagation()">
          <div class="lp-head">
            <h3>👑 Elige tu Champion Legend</h3>
            <p class="muted">Las cartas se filtrarán automáticamente por los colores del legend.</p>
            <input type="search" [(ngModel)]="legendPickerSearch"
                   placeholder="Buscar por nombre…" class="lp-search" />
            @if (chosenLegend()) {
              <button class="lp-skip" (click)="closeLegendPicker()">Mantener actual</button>
            }
          </div>
          <div class="lp-grid">
            @for (L of filteredLegends(); track L.id) {
              <button type="button" class="lp-card" (click)="chooseLegend(L)">
                @if (L.image) {
                  <img [src]="L.image" [alt]="L.name" />
                } @else {
                  <div class="lp-img-fallback">{{ L.card_number }}</div>
                }
                <div class="lp-name">{{ L.name }}</div>
                <div class="lp-colors">
                  @for (c of (L.colors || []); track c) {
                    <span class="color-dot" [style.background]="colorHex(c)"></span>
                  }
                </div>
              </button>
            }
            @if (filteredLegends().length === 0) {
              <p class="muted center">Sin resultados.</p>
            }
          </div>
        </div>
      </div>
    }
  `,
  styles: [`
    .builder-layout {
      display: grid;
      grid-template-columns: 1fr 380px;
      min-height: calc(100vh - 64px);
      max-width: 100%;
    }
    @media (max-width: 900px) { .builder-layout { grid-template-columns: 1fr; } }

    /* Browser */
    .card-browser { padding: 1.25rem; border-right: 1px solid #1e3a4a; min-width: 0; }
    .card-browser h2 {
      font-size: 1.5rem; font-weight: 700; color: #f0e6d2; margin: 0 0 1rem;
      letter-spacing: -.01em;
    }
    .muted { opacity: .65; }
    .center { text-align: center; }

    .browser-filters { margin-bottom: 1rem; display: flex; flex-direction: column; gap: .55rem; }

    .search-row { display: flex; gap: .5rem; align-items: stretch; }
    .search-row input {
      flex: 1; min-width: 0; padding: .55rem .85rem;
      border: 1px solid #2a3a4a; border-radius: 6px;
      background: #0a1428; color: #e0e0e0; outline: none;
      font-size: .95rem;
    }
    .search-row input:focus { border-color: #e94560; }
    .search-modes {
      display: inline-flex; background: #16213e; border: 1px solid #2a2a4a;
      border-radius: 6px; padding: 2px; gap: 2px;
    }
    .search-modes button {
      padding: .35rem .7rem; border: none; background: transparent;
      color: #b0b0c8; border-radius: 4px; font-size: .85rem; cursor: pointer;
      white-space: nowrap; transition: background .15s, color .15s;
    }
    .search-modes button:hover { color: #fff; }
    .search-modes button.active { background: #e94560; color: #fff; font-weight: 600; }
    .search-btn {
      padding: .55rem .9rem; border: 1px solid #e94560; border-radius: 6px;
      background: #e94560; color: #fff; cursor: pointer; font-size: 1rem;
      transition: background .15s;
    }
    .search-btn:hover { background: #c73650; }
    .search-btn:active { transform: scale(.95); }

    .type-chips { display: flex; flex-wrap: wrap; gap: .4rem; }
    .type-chip-btn {
      padding: .3rem .75rem; border: 1px solid #2a3a4a; border-radius: 999px;
      background: #0a1428; color: #c8c8da; font-size: .85rem; cursor: pointer;
      transition: all .15s; white-space: nowrap;
    }
    .type-chip-btn:hover { border-color: #e94560; color: #fff; }
    .type-chip-btn.active { background: #ffbd39; border-color: #ffbd39; color: #1a1a2e; font-weight: 700; }

    .filter-row {
      display: grid; grid-template-columns: repeat(3, 1fr); gap: .5rem;
    }
    @media (max-width: 600px) { .filter-row { grid-template-columns: 1fr 1fr; } }
    .filter-label { display: block; font-size: .7rem; color: #98a2a8; margin-bottom: .15rem; text-transform: uppercase; letter-spacing: .04em; }
    .filter-row select {
      width: 100%; padding: .4rem .6rem;
      border: 1px solid #2a3a4a; border-radius: 6px;
      background: #0a1428; color: #e0e0e0; outline: none;
    }
    .filter-row select:focus { border-color: #c89b3c; }

    .color-row { display: flex; gap: .35rem; flex-wrap: wrap; align-items: center; }
    .color-chip {
      padding: .3rem .65rem; border: 1px solid var(--c); border-radius: 999px;
      background: transparent; color: var(--c); cursor: pointer; font-size: .8rem;
      font-weight: 600;
    }
    .color-chip.active { background: var(--c); color: #0a1428; }
    .clear-colors {
      background: transparent; border: none; color: #c89b3c; cursor: pointer;
      font-size: .8rem; text-decoration: underline;
    }

    /* Cards grid */
    .available-cards {
      display: grid; grid-template-columns: repeat(3, 1fr);
      gap: .5rem; margin-top: 1rem;
    }
    @media (max-width: 1100px) { .available-cards { grid-template-columns: repeat(2, 1fr); } }
    @media (max-width: 600px) { .available-cards { grid-template-columns: 1fr; } }

    .mini-card {
      display: flex; align-items: center; gap: .5rem;
      background: #1a1a2e; border: 1px solid #2a2a4a; border-radius: 6px;
      padding: .35rem; transition: all .15s; position: relative;
      min-width: 0;
    }
    .mini-card:hover { border-color: #e94560; background: #1e1e3a; }
    .mini-card.in-deck { border-color: #ffbd39; background: rgba(255,189,57,.05); }
    .mini-card.maxed .actions-column .add { opacity: .35; cursor: not-allowed; }
    .mini-card.banned { border-color: #e94560; background: rgba(233,69,96,.07); }
    .mini-card.banned .actions-column .add { opacity: .25; cursor: not-allowed; }
    .mini-card.banned .img-wrapper img { filter: grayscale(.6) brightness(.7); }
    .mini-card.limited { border-color: #ff8c42; }
    .ban-badge {
      position: absolute; top: 2px; right: 2px;
      width: 18px; height: 18px; border-radius: 50%;
      display: grid; place-items: center;
      font-size: .7rem; font-weight: 700;
      pointer-events: none;
    }
    .ban-badge-banned { background: #e94560; color: #fff; }
    .ban-badge-limited { background: #ff8c42; color: #fff; }

    .img-wrapper { position: relative; flex-shrink: 0; cursor: zoom-in; }
    .img-wrapper img {
      width: 56px; height: 78px; object-fit: cover; border-radius: 4px;
      background: #16213e;
    }
    .img-placeholder {
      width: 56px; height: 78px; display: grid; place-items: center;
      background: #16213e; border-radius: 4px; font-size: .65rem; text-align: center;
    }
    .eye-icon {
      position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;
      background: rgba(0,0,0,.55); border-radius: 4px; font-size: 1.3rem;
      opacity: 0; transition: opacity .15s;
    }
    .img-wrapper:hover .eye-icon { opacity: 1; }

    .mini-info { flex: 1; min-width: 0; display: flex; flex-direction: column; }
    .mini-name { font-size: .85rem; color: #f0e6d2; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .mini-type { font-size: .7rem; color: #98a2a8; }
    .mini-num { font-size: .65rem; color: #6a7a88; }
    .mini-ability {
      margin: .25rem 0 0; font-size: .68rem; color: #aaa; line-height: 1.35;
      display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
      overflow: hidden;
    }
    @media (max-width: 1400px) { .mini-ability { display: none; } }

    .actions-column { display: flex; flex-direction: column; gap: 2px; flex-shrink: 0; }
    .mini-actions { display: flex; align-items: center; gap: .25rem; min-width: 72px; justify-content: flex-end; }
    .mini-actions.hidden { display: none; }
    .zone-label { font-size: .65rem; font-weight: 700; width: 12px; text-align: right; }
    .main-label { color: #ffbd39; }
    .side-label { color: #2ac5c5; }
    .auto-label { color: #f0e6d2; }
    .side-actions { border-top: 1px solid #333; padding-top: 2px; }

    .circle-btn {
      width: 24px; height: 24px; border-radius: 50%;
      border: 1px solid #444; background: #1a1a2e; color: #ccc;
      font-size: 1rem; line-height: 1; display: flex; align-items: center; justify-content: center;
      cursor: pointer; transition: all .15s;
    }
    .circle-btn.add:hover:not(:disabled) { border-color: #4caf50; color: #4caf50; background: rgba(76,175,80,.1); }
    .circle-btn.remove:hover { border-color: #e94560; color: #e94560; background: rgba(233,69,96,.1); }
    .circle-btn:disabled { opacity: .3; cursor: not-allowed; }

    .mini-qty { font-weight: 700; font-size: .8rem; color: #ffbd39; width: 16px; text-align: center; }

    .pagination { display: flex; gap: 1rem; align-items: center; justify-content: center; margin: 1.25rem 0; color: #98a2a8; }
    .page-btn { padding: .35rem .9rem; border: 1px solid #2a3a4a; background: transparent; color: #c8c8da; border-radius: 4px; cursor: pointer; }
    .page-btn:disabled { opacity: .35; cursor: not-allowed; }

    /* Deck panel */
    .deck-panel {
      padding: 1.25rem; background: #091428; border-left: 1px solid #1e3a4a;
      overflow-y: auto;
    }
    @media (max-width: 900px) {
      .deck-panel {
        position: fixed; inset: 0;
        z-index: 950; transform: translateX(100%); transition: transform .25s ease;
        background: #091428;
      }
      .deck-panel.mobile-visible { transform: translateX(0); }
    }
    .deck-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
    .deck-header h2 { margin: 0; font-size: 1.1rem; color: #f0e6d2; }
    .mobile-close-btn {
      display: none; width: 36px; height: 36px; border-radius: 50%;
      border: 1px solid #2a3a4a; background: #0a1428; color: #c8c8da; cursor: pointer;
    }
    @media (max-width: 900px) { .mobile-close-btn { display: block; } }

    .form-group { margin-bottom: .75rem; }
    .form-group label { display: block; font-size: .75rem; color: #98a2a8; margin-bottom: .25rem; text-transform: uppercase; letter-spacing: .04em; }
    .form-group input {
      width: 100%; padding: .5rem .7rem; border: 1px solid #2a3a4a; border-radius: 6px;
      background: #0a1428; color: #e0e0e0; outline: none;
    }
    .form-group input:focus { border-color: #c89b3c; }

    .checkbox-label { display: flex; align-items: center; gap: .5rem; color: #c8c8da; font-size: .9rem; margin-bottom: 1rem; cursor: pointer; }
    .checkbox-label input { accent-color: #c89b3c; }

    .zones-summary { display: flex; gap: .35rem; flex-wrap: wrap; margin-bottom: .75rem; }
    .zone-pill {
      display: inline-flex; align-items: center; gap: .35rem;
      padding: .25rem .55rem; border-radius: 999px;
      background: #0a1428; border: 1px solid #2a3a4a;
      font-size: .78rem; color: #c8c8da;
    }
    .zone-pill.ok { border-color: #4caf50; color: #4caf50; }
    .zone-pill.bad { border-color: #e94560; color: #e94560; }
    .zp-label { font-weight: 700; }

    .cost-curve {
      background: #0a1428; border: 1px solid #1e3a4a; border-radius: 8px;
      padding: .6rem .7rem .5rem; margin-bottom: .9rem;
    }
    .cost-curve-title { display: block; font-size: .7rem; color: #98a2a8; text-transform: uppercase; letter-spacing: .05em; margin-bottom: .4rem; }
    .cost-curve-bars {
      display: grid; grid-template-columns: repeat(9, 1fr); gap: .25rem;
      align-items: end; height: 80px;
    }
    .cost-bar { display: flex; flex-direction: column; align-items: center; justify-content: flex-end; height: 100%; gap: 2px; }
    .cost-bar-count { font-size: .7rem; color: #c89b3c; font-weight: 600; min-height: .7rem; }
    .cost-bar-fill-wrap { width: 100%; flex: 1; display: flex; align-items: flex-end; background: rgba(30,58,74,.4); border-radius: 3px; }
    .cost-bar-fill { width: 100%; background: linear-gradient(180deg, #f0e6d2 0%, #c89b3c 100%); border-radius: 3px 3px 0 0; transition: height .3s; min-height: 2px; }
    .cost-bar-label { font-size: .7rem; color: #6a7a88; }
    .cost-bar.empty .cost-bar-fill { background: #1e3a4a; opacity: .5; }
    .cost-bar.empty .cost-bar-count { color: transparent; }

    .color-dist { margin-bottom: .9rem; }
    .cd-title { display: block; font-size: .7rem; color: #98a2a8; text-transform: uppercase; letter-spacing: .05em; margin-bottom: .35rem; }
    .cd-bars { display: flex; gap: .35rem; flex-wrap: wrap; }
    .cd-pill { font-size: .75rem; padding: .15rem .5rem; border-radius: 999px; border: 1px solid var(--c); color: var(--c); }
    .cd-pill strong { color: #f0e6d2; }

    .zone-section { margin-bottom: .9rem; padding: .5rem; border: 1px solid #1e3a4a; border-radius: 6px; }
    .zone-section.empty { opacity: .65; }
    .zone-section-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: .35rem; }
    .zs-title { font-weight: 700; color: #f0e6d2; font-size: .9rem; }
    .zs-count { font-size: .8rem; color: #98a2a8; }
    .zs-count.ok { color: #4caf50; }
    .zone-empty { font-size: .75rem; color: #6a7a88; margin: 0; }

    .deck-entry { display: flex; align-items: center; gap: .5rem; padding: .35rem 0; border-bottom: 1px solid #1a2a3a; }
    .deck-entry:last-child { border-bottom: none; }
    .deck-entry img, .entry-img-fallback {
      width: 38px; height: 53px; object-fit: cover; border-radius: 3px; background: #16213e;
      display: grid; place-items: center; font-size: .55rem; text-align: center; color: #c8c8da;
    }
    .entry-info { flex: 1; min-width: 0; }
    .entry-name { display: block; font-size: .8rem; color: #f0e6d2; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .entry-meta { font-size: .7rem; color: #6a7a88; }
    .entry-controls { display: flex; align-items: center; gap: .25rem; }
    .ctrl-btn {
      width: 24px; height: 24px; border-radius: 50%;
      border: 1px solid #2a3a4a; background: #0a1428; color: #c8c8da;
      font-size: .9rem; line-height: 1; display: flex; align-items: center; justify-content: center;
      cursor: pointer;
    }
    .ctrl-btn:hover:not(:disabled) { border-color: #c89b3c; color: #c89b3c; }
    .ctrl-btn.remove:hover { border-color: #e94560; color: #e94560; }
    .ctrl-btn:disabled { opacity: .3; cursor: not-allowed; }
    .entry-qty { font-weight: 700; color: #c89b3c; min-width: 18px; text-align: center; }

    .errors-box {
      background: rgba(233,69,96,.1); border: 1px solid #e94560; color: #ff8b8b;
      padding: .55rem .7rem; border-radius: 6px; font-size: .8rem; margin-bottom: .75rem;
    }
    .errors-box ul { margin: .35rem 0 0 1.1rem; padding: 0; }

    .save-btn {
      width: 100%; padding: .65rem 1rem; border: none; border-radius: 6px;
      background: #c89b3c; color: #0a1428; font-weight: 700; cursor: pointer;
      font-size: 1rem;
    }
    .save-btn:hover:not(:disabled) { background: #d4a84b; }
    .save-btn:disabled { opacity: .55; cursor: not-allowed; }

    /* FAB móvil */
    .rb-fab {
      display: none;
      position: fixed; right: 1rem; bottom: 5.5rem;
      width: 56px; height: 56px; border-radius: 50%;
      background: #c89b3c; color: #0a1428; border: none;
      box-shadow: 0 4px 14px rgba(0,0,0,.35); cursor: pointer; z-index: 920;
      align-items: center; justify-content: center; flex-direction: column;
    }
    @media (max-width: 900px) { .rb-fab { display: flex; } }
    .fab-icon { font-size: 1.4rem; }
    .fab-count {
      position: absolute; top: -4px; right: -4px;
      background: #e94560; color: #fff; border-radius: 999px;
      padding: 1px 6px; font-size: .7rem; font-weight: 700;
    }

    /* Preview modal */
    .preview-overlay {
      position: fixed; inset: 0; z-index: 1000;
      background: rgba(0,0,0,.75); display: grid; place-items: center;
      padding: 1rem;
    }
    .preview-box {
      position: relative; max-width: 360px; background: #0a1428;
      border: 1px solid #c89b3c; border-radius: 10px; padding: 1rem; text-align: center;
    }
    .preview-box img { max-width: 100%; border-radius: 6px; }
    .preview-box h3 { color: #f0e6d2; margin: .5rem 0 0; font-size: 1rem; }
    .preview-box small { color: #98a2a8; font-weight: 400; }
    .preview-close {
      position: absolute; top: .35rem; right: .35rem;
      width: 28px; height: 28px; border-radius: 50%; border: none;
      background: #1e3a4a; color: #c8c8da; cursor: pointer;
    }

    /* Legend banner (en deck-panel) */
    .legend-banner {
      display: flex; align-items: center; gap: .65rem;
      background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
      border: 1px solid #c89b3c; border-radius: 8px;
      padding: .5rem .65rem; margin: 0 0 1rem;
    }
    .legend-banner.empty {
      background: rgba(200, 155, 60, .08);
      border-style: dashed;
      padding: 0;
    }
    .choose-legend-btn {
      width: 100%; padding: .85rem 1rem;
      background: linear-gradient(135deg, #c89b3c 0%, #ffd23c 100%);
      color: #0a1428; border: none; border-radius: 8px;
      font-weight: 700; font-size: 1rem; cursor: pointer;
      letter-spacing: .02em;
      transition: filter .15s, transform .15s;
    }
    .choose-legend-btn:hover { filter: brightness(1.1); transform: translateY(-1px); }
    .legend-img {
      width: 52px; height: 72px; object-fit: cover; border-radius: 4px;
      flex-shrink: 0; background: #16213e;
    }
    .legend-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
    .legend-tag {
      font-size: .6rem; letter-spacing: .08em;
      color: #c89b3c; font-weight: 700;
    }
    .legend-info strong {
      color: #f0e6d2; font-size: .9rem; line-height: 1.1;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .legend-colors { display: flex; gap: 4px; margin-top: 2px; }
    .color-dot {
      display: inline-block; width: 10px; height: 10px; border-radius: 50%;
      border: 1px solid rgba(255,255,255,.3);
    }
    .legend-actions { display: flex; flex-direction: column; gap: 4px; }
    .legend-btn {
      background: #1e3a4a; color: #c8c8da;
      border: 1px solid #2a4a5a; border-radius: 4px;
      padding: .25rem .55rem; font-size: .7rem; cursor: pointer;
      white-space: nowrap;
    }
    .legend-btn:hover { background: #2a4a5a; }
    .legend-btn.locked { background: #c89b3c; color: #0a1428; border-color: #c89b3c; }

    /* Legend Picker modal */
    .legend-picker-overlay {
      position: fixed; inset: 0; z-index: 1100;
      background: rgba(0,0,0,.85); display: grid; place-items: center;
      padding: 1rem; overflow-y: auto;
    }
    .legend-picker-box {
      width: min(900px, 100%); max-height: 90vh; overflow-y: auto;
      background: #0a1428; border: 1px solid #c89b3c;
      border-radius: 10px; padding: 1.25rem;
    }
    .lp-head { display: flex; flex-direction: column; gap: .5rem; margin-bottom: 1rem; }
    .lp-head h3 { color: #f0e6d2; margin: 0; font-size: 1.3rem; }
    .lp-head .muted { color: #98a2a8; font-size: .85rem; margin: 0; }
    .lp-search {
      padding: .55rem .85rem; background: #16213e;
      border: 1px solid #2a3a4a; border-radius: 6px; color: #e0e0e0;
      font-size: .95rem; outline: none;
    }
    .lp-search:focus { border-color: #c89b3c; }
    .lp-skip {
      align-self: flex-start; background: transparent; color: #98a2a8;
      border: 1px solid #2a3a4a; border-radius: 6px;
      padding: .35rem .75rem; font-size: .8rem; cursor: pointer;
    }
    .lp-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
      gap: .65rem;
    }
    .lp-card {
      display: flex; flex-direction: column; align-items: center;
      gap: .35rem; padding: .5rem;
      background: #16213e; border: 1px solid #2a3a4a; border-radius: 8px;
      cursor: pointer; color: inherit; text-align: center;
      transition: border-color .15s, transform .15s;
    }
    .lp-card:hover { border-color: #c89b3c; transform: translateY(-2px); }
    .lp-card img {
      width: 100%; aspect-ratio: 0.72; object-fit: cover; border-radius: 4px;
    }
    .lp-img-fallback {
      width: 100%; aspect-ratio: 0.72; display: grid; place-items: center;
      background: #1e3a4a; border-radius: 4px; color: #98a2a8; font-size: .8rem;
    }
    .lp-name {
      font-size: .8rem; color: #f0e6d2; font-weight: 600; line-height: 1.15;
    }
    .lp-colors { display: flex; gap: 3px; }

    /* Light theme */
    :host-context(body.light-theme) .card-browser h2,
    :host-context(body.light-theme) .deck-header h2,
    :host-context(body.light-theme) .mini-name,
    :host-context(body.light-theme) .zs-title,
    :host-context(body.light-theme) .entry-name { color: #463714; }
    :host-context(body.light-theme) .card-browser { border-right-color: #d4c489; }
    :host-context(body.light-theme) .deck-panel { background: #fbf6e9; border-left-color: #d4c489; }
    :host-context(body.light-theme) .mini-card,
    :host-context(body.light-theme) .zone-section,
    :host-context(body.light-theme) .cost-curve,
    :host-context(body.light-theme) .form-group input,
    :host-context(body.light-theme) .filter-row select,
    :host-context(body.light-theme) .search-row input { background: #ffffff; border-color: #d4c489; color: #2a1f10; }
    :host-context(body.light-theme) .mini-type,
    :host-context(body.light-theme) .entry-meta,
    :host-context(body.light-theme) .filter-label,
    :host-context(body.light-theme) .cd-title,
    :host-context(body.light-theme) .cost-curve-title,
    :host-context(body.light-theme) .zs-count,
    :host-context(body.light-theme) .zone-empty { color: #6a5a3a; }
  `],
})
export class RiftboundBuilderComponent implements OnInit {
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
  saving = signal(false);
  errors = signal<string[]>([]);

  // Browser state
  searchQuery = '';
  searchMode: 'name' | 'ability' | 'all' = 'name';
  typeFilter = '';
  setFilter = '';
  rarityFilter = '';
  energyFilter: number | null = null;
  selectedColors = signal(new Set<RiftboundColor>());

  results = signal<RiftboundCardLite[]>([]);
  loading = signal(false);
  page = signal(1);
  totalCount = signal(0);
  pageSize = 24;
  totalPages = computed(() => Math.max(1, Math.ceil(this.totalCount() / this.pageSize)));

  sets = signal<{ code: string; name: string }[]>([]);

  // Banlist (formato Standard)
  banlist = signal<Map<string, { status: string; max_copies: number }>>(new Map());

  // Champion-first wizard
  legendOptions = signal<RiftboundCardLite[]>([]);
  showLegendPicker = signal(false);
  legendPickerSearch = '';
  /** Si está activo, los filtros de colores quedan bloqueados a los del legend. */
  lockColorsToLegend = signal(true);

  // Deck entries
  entries = signal<Record<RiftboundZone, BuilderEntry[]>>({
    main: [], side: [], rune: [], champion: [], bg: [],
  });

  // UI state
  showDeckPanel = signal(false);
  previewCard = signal<RiftboundCardLite | null>(null);

  private searchTimer: ReturnType<typeof setTimeout> | null = null;

  ngOnInit() {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.deckId.set(+id);
      this.rb.getDeck(+id).subscribe({ next: (deck) => this.loadFromDeck(deck) });
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

  loadFromDeck(deck: RiftboundDeck) {
    this.deckName = deck.name;
    this.description = deck.description ?? '';
    this.isPublic = deck.is_public ?? true;
    const map: Record<RiftboundZone, BuilderEntry[]> = {
      main: [], side: [], rune: [], champion: [], bg: [],
    };
    for (const e of deck.entries ?? []) {
      if (e.card_data) {
        map[e.zone].push({ card: e.card_data as RiftboundCardLite, quantity: e.quantity, zone: e.zone });
      }
    }
    this.entries.set(map);
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
      lite: true,
    }).subscribe({
      next: (resp) => {
        this.results.set(resp.results as RiftboundCardLite[]);
        this.totalCount.set(resp.count);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  prev() { if (this.page() > 1) { this.page.update(p => p - 1); this.reload(); } }
  next() { if (this.page() < this.totalPages()) { this.page.update(p => p + 1); this.reload(); } }

  // ── Helpers de zona ──
  zoneCount(z: RiftboundZone): number {
    return this.entries()[z].reduce((s, e) => s + e.quantity, 0);
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
    if (z === 'main') return count >= rule;
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

  // ── Preview ──
  openPreview(c: RiftboundCardLite) { this.previewCard.set(c); }
  closePreview() { this.previewCard.set(null); }

  // ── Champion-first wizard ──
  /** Legend actualmente seleccionado (o null si no hay). */
  chosenLegend = computed<RiftboundCardLite | null>(() => {
    return this.entries().champion[0]?.card ?? null;
  });

  /** Filtra los legends por búsqueda. */
  filteredLegends = computed(() => {
    const q = this.legendPickerSearch.trim().toLowerCase();
    const list = this.legendOptions();
    if (!q) return list;
    return list.filter(l =>
      l.name.toLowerCase().includes(q) ||
      l.card_number.toLowerCase().includes(q),
    );
  });

  openLegendPicker() {
    this.legendPickerSearch = '';
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
    this.reload();
  }

  changeLegend() {
    this.openLegendPicker();
  }

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
      entries: flat as RiftboundDeckEntry[],
    };
    const obs = this.deckId()
      ? this.rb.updateDeck(this.deckId()!, payload)
      : this.rb.createDeck(payload);
    obs.subscribe({
      next: (deck) => {
        this.saving.set(false);
        if (deck.validation && !deck.validation.valid) {
          this.errors.set(deck.validation.errors);
        }
        if (!this.deckId()) {
          this.deckId.set(deck.id);
          this.router.navigate(['/riftbound/builder', deck.id]);
        }
      },
      error: (err) => {
        this.saving.set(false);
        this.errors.set([err?.error?.detail || 'Error al guardar.']);
      },
    });
  }
}
