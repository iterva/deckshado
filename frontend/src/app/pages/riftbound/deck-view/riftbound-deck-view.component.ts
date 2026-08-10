import {
  Component, OnInit, computed, inject, signal,
  HostListener, ElementRef, ViewChild, ChangeDetectorRef,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { Title, Meta } from '@angular/platform-browser';
import { RiftboundService } from '../../../services/riftbound.service';
import { AuthService } from '../../../services/auth.service';
import {
  RiftboundDeck, RiftboundDeckEntry, RiftboundBanlistEntry,
  RIFTBOUND_ZONE_LABELS, RiftboundZone, RiftboundColor, RiftboundCard,
} from '../../../models/riftbound';
import { TcgPriceComponent } from '../../../components/tcg-price/tcg-price.component';

type ViewMode = 'grid' | 'list' | 'stats';
type Orientation = 'vertical' | 'horizontal';
type StackOrientation = 'down' | 'up' | 'left' | 'right' | 'center';
type CardImageLike = {
  id?: number | null;
  card_number?: string | null;
  image?: string | null;
  cdn_image_url?: string | null;
  image_url?: string | null;
  image_url_small?: string | null;
};

const COLOR_HEX: Record<RiftboundColor, string> = {
  fury: '#e94560', calm: '#4caf50', mind: '#3aa6ff',
  body: '#ff9a3c', chaos: '#9c5dff', order: '#ff6b7d', neutral: '#888',
};
const COLOR_LABEL: Record<RiftboundColor, string> = {
  fury: 'Fury', calm: 'Calm', mind: 'Mind',
  body: 'Body', chaos: 'Chaos', order: 'Order', neutral: 'Neutral',
};
const TYPE_LABEL: Record<string, string> = {
  unit: 'Unidad', spell: 'Hechizo', gear: 'Equipo', legend: 'Legend',
  rune: 'Runa', battlefield: 'Battlefield', champion: 'Champion', other: 'Otro',
};
const TYPE_COLOR: Record<string, string> = {
  unit: '#4ade80', spell: '#60a5fa', gear: '#fbbf24', legend: '#c89b3c',
  rune: '#c084fc', battlefield: '#fb7185', champion: '#ffbd39', other: '#888',
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
  selector: 'app-riftbound-deck-view',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, TcgPriceComponent],
  template: `
    @if (loading()) {
      <p class="loading">Cargando mazo…</p>
    } @else if (deck(); as d) {
      <div class="container" [class.is-presentation]="presentationMode()">
        <a routerLink="/riftbound/decks" class="back-link">← Volver a mazos</a>

        <!-- Hero -->
        <div class="deck-hero" [class.with-cover]="!!cardImageUrl(d.cover_card_data)">
          @if (cardImageUrl(d.cover_card_data); as img) {
            <div class="hero-bg" [style.background-image]="'url(' + img + ')'"></div>
          }
          <div class="hero-overlay"></div>
          <div class="hero-content">
            @if (cardImageUrl(d.cover_card_data); as img) {
              <img class="hero-cover" [src]="img" [alt]="d.cover_card_data?.name || ''"
                   (error)="onCardImageError(d.cover_card_data, $event)" />
            } @else {
              <div class="hero-cover hero-cover-empty">⚔️</div>
            }
            <div class="hero-info">
              <h1 class="deck-title">{{ d.name }}</h1>
              <div class="deck-chips">
                <span class="chip chip-owner">👤 {{ d.owner_username }}</span>
                @for (col of d.primary_colors; track col) {
                  <span class="chip chip-color" [style.--c]="hex(col)">
                    <span class="dot"></span>{{ label(col) }}
                  </span>
                }
                <span class="chip chip-cards">📚 {{ totalCards() }}</span>
                <span class="chip" [class.chip-public]="d.is_public" [class.chip-private]="!d.is_public">
                  {{ d.is_public ? '🌐 Público' : '🔒 Privado' }}
                </span>
                <span class="chip chip-time" [title]="d.updated_at">
                  🕒 {{ formatDate(d.updated_at) }}
                </span>
              </div>
              @if (d.description) {
                <p class="hero-description">{{ d.description }}</p>
              }
            </div>
          </div>
        </div>

        <!-- Barra social (likes/comentarios/compartir/clonar) -->
        <div class="social-bar">
          <button class="social-btn" disabled title="Próximamente: me gusta">
            <i class="bi bi-heart"></i><span>0</span>
          </button>
          <button class="social-btn" disabled title="Próximamente: comentarios">
            <i class="bi bi-chat-dots"></i><span>0</span>
          </button>
          <button class="social-btn" (click)="shareDeck()" title="Copiar enlace">
            <i class="bi bi-share"></i>
          </button>
          <button class="social-btn" (click)="copyDeckJson()" title="Copiar mazo (JSON)">
            <i class="bi bi-clipboard-plus"></i>
          </button>
        </div>

        <!-- Action bar -->
        <div class="action-bar">
          <div class="seg-control" role="tablist" aria-label="Modo de visualización">
            <button type="button" class="seg-btn" [class.active]="viewMode() === 'grid'"
                    (click)="setViewMode('grid')" role="tab" title="Vista cartas">
              <i class="bi bi-grid-3x3-gap-fill"></i><span>Cartas</span>
            </button>
            <button type="button" class="seg-btn" [class.active]="viewMode() === 'list'"
                    (click)="setViewMode('list')" role="tab" title="Vista listado">
              <i class="bi bi-list-ul"></i><span>Lista</span>
            </button>
            <button type="button" class="seg-btn" [class.active]="viewMode() === 'stats'"
                    (click)="setViewMode('stats')" role="tab" title="Estadísticas">
              <i class="bi bi-bar-chart-fill"></i><span>Stats</span>
            </button>
          </div>

          <div class="action-spacer"></div>

          <div class="orient-menu-wrap" (click)="$event.stopPropagation()">
            <button class="action-btn" (click)="toggleStackOrientationMenu($event)"
                    aria-haspopup="menu" [attr.aria-expanded]="showStackOrientationMenu()"
                    title="Orientación de apilado">
              <i class="bi"
                 [class.bi-arrow-up-square-fill]="stackOrientation() === 'up'"
                 [class.bi-arrow-down-square-fill]="stackOrientation() === 'down'"
                 [class.bi-arrow-left-square-fill]="stackOrientation() === 'left'"
                 [class.bi-arrow-right-square-fill]="stackOrientation() === 'right'"
                 [class.bi-square-fill]="stackOrientation() === 'center'"></i>
              <span>Orientación</span>
            </button>
            @if (showStackOrientationMenu()) {
              <div class="orient-menu" role="menu" aria-label="Orientación de cartas">
                <button role="menuitemradio" [attr.aria-checked]="stackOrientation() === 'center'"
                        [class.active]="stackOrientation() === 'center'" (click)="setStackOrientation('center')">
                  <i class="bi bi-square-fill"></i> Centro
                </button>
                <button role="menuitemradio" [attr.aria-checked]="stackOrientation() === 'up'"
                        [class.active]="stackOrientation() === 'up'" (click)="setStackOrientation('up')">
                  <i class="bi bi-arrow-up-square-fill"></i> Hacia arriba
                </button>
                <button role="menuitemradio" [attr.aria-checked]="stackOrientation() === 'down'"
                        [class.active]="stackOrientation() === 'down'" (click)="setStackOrientation('down')">
                  <i class="bi bi-arrow-down-square-fill"></i> Hacia abajo
                </button>
                <button role="menuitemradio" [attr.aria-checked]="stackOrientation() === 'left'"
                        [class.active]="stackOrientation() === 'left'" (click)="setStackOrientation('left')">
                  <i class="bi bi-arrow-left-square-fill"></i> Hacia la izquierda
                </button>
                <button role="menuitemradio" [attr.aria-checked]="stackOrientation() === 'right'"
                        [class.active]="stackOrientation() === 'right'" (click)="setStackOrientation('right')">
                  <i class="bi bi-arrow-right-square-fill"></i> Hacia la derecha
                </button>
              </div>
            }
          </div>

          <button class="action-btn" (click)="openExportOptionsModal($event)" [attr.aria-expanded]="showExportOptionsModal()"
                  title="Opciones de imagen">
            <i class="bi bi-sliders2"></i><span>Imagen</span>
          </button>

          <button class="action-btn" (click)="openHandTest()" title="Probar mano de apertura">
            <i class="bi bi-hand-index"></i><span>Probar mano</span>
          </button>

          @if (isOwner()) {
            <button class="action-btn" (click)="toggleVisibility()" [disabled]="togglingVisibility()"
                    [title]="d.is_public ? 'Hacer privado' : 'Hacer público'">
              <i class="bi" [class.bi-globe]="d.is_public" [class.bi-lock-fill]="!d.is_public"></i>
              <span>{{ d.is_public ? 'Hacer privado' : 'Hacer público' }}</span>
            </button>
            <button class="action-btn accent" (click)="editDeck()" title="Editar mazo">
              <i class="bi bi-pencil-square"></i><span>Editar</span>
            </button>
          }

          <button class="action-btn" (click)="togglePresentation()" title="Modo presentación (F)">
            <i class="bi" [class.bi-fullscreen]="!presentationMode()" [class.bi-fullscreen-exit]="presentationMode()"></i>
          </button>

          <div class="more-menu-wrap" (click)="$event.stopPropagation()">
            <button class="action-btn" (click)="toggleMoreMenu($event)" aria-haspopup="menu"
                    [attr.aria-expanded]="showMoreMenu()" title="Más opciones">
              <i class="bi bi-three-dots-vertical"></i>
            </button>
            @if (showMoreMenu()) {
              <div class="more-menu" role="menu" (click)="$event.stopPropagation()">
                <button role="menuitem" (click)="exportText(); showMoreMenu.set(false)">
                  <i class="bi bi-file-text"></i> Copiar como texto
                </button>
                <button role="menuitem" (click)="openExportOptionsModal($event); showMoreMenu.set(false)">
                  <i class="bi bi-camera"></i> Exportar imagen...
                </button>
                <button role="menuitem" (click)="exportJson(); showMoreMenu.set(false)">
                  <i class="bi bi-filetype-json"></i> Descargar JSON
                </button>
                @if (isOwner()) {
                  <div class="more-divider"></div>
                  <button role="menuitem" class="danger" (click)="deleteDeck(); showMoreMenu.set(false)">
                    <i class="bi bi-trash3"></i> Eliminar mazo
                  </button>
                }
              </div>
            }
          </div>
        </div>

        @if (showExportOptionsModal()) {
          <div class="export-modal-overlay" (click)="closeExportOptionsModal()">
            <div class="export-modal" role="dialog" aria-modal="true" aria-label="Opciones para generar imagen" (click)="$event.stopPropagation()">
              <div class="export-modal-head">
                <h3>Exportar imagen</h3>
                <button type="button" class="export-modal-close" (click)="closeExportOptionsModal()" aria-label="Cerrar">
                  <i class="bi bi-x-lg"></i>
                </button>
              </div>

              <div class="export-modal-body">
                <div class="export-opt-section">
                  <span class="export-opt-title">Formato</span>
                  <div class="export-opt-row two">
                    <button type="button" class="opt-chip" [class.active]="orientation() === 'horizontal'" (click)="setOrientation('horizontal')">
                      <i class="bi bi-arrows-angle-expand"></i> Horizontal
                    </button>
                    <button type="button" class="opt-chip" [class.active]="orientation() === 'vertical'" (click)="setOrientation('vertical')">
                      <i class="bi bi-arrows-angle-contract"></i> Vertical
                    </button>
                  </div>
                </div>

                <div class="export-opt-section">
                  <span class="export-opt-title">Apilado de cartas</span>
                  <div class="export-opt-row two">
                    <button type="button" class="opt-chip" [class.active]="stackOrientation() === 'up'" (click)="setStackOrientation('up')">
                      <i class="bi bi-arrow-up-square-fill"></i> Arriba
                    </button>
                    <button type="button" class="opt-chip" [class.active]="stackOrientation() === 'down'" (click)="setStackOrientation('down')">
                      <i class="bi bi-arrow-down-square-fill"></i> Abajo
                    </button>
                    <button type="button" class="opt-chip" [class.active]="stackOrientation() === 'left'" (click)="setStackOrientation('left')">
                      <i class="bi bi-arrow-left-square-fill"></i> Izquierda
                    </button>
                    <button type="button" class="opt-chip" [class.active]="stackOrientation() === 'right'" (click)="setStackOrientation('right')">
                      <i class="bi bi-arrow-right-square-fill"></i> Derecha
                    </button>
                    <button type="button" class="opt-chip" [class.active]="stackOrientation() === 'center'" (click)="setStackOrientation('center')">
                      <i class="bi bi-square-fill"></i> Centro
                    </button>
                  </div>
                </div>
              </div>

              <div class="export-modal-foot">
                <button type="button" class="export-foot-btn" (click)="closeExportOptionsModal()">Cancelar</button>
                <button type="button" class="export-foot-btn primary" [disabled]="exporting()" (click)="generateExportPreview()">
                  <i class="bi bi-camera"></i>
                  {{ exporting() ? 'Generando...' : 'Generar preview' }}
                </button>
              </div>
            </div>
          </div>
        }

        @if (showExportPreviewModal()) {
          <div class="export-preview-overlay" (click)="closeExportPreview()">
            <div class="export-preview-modal" role="dialog" aria-modal="true" aria-label="Preview de exportación" (click)="$event.stopPropagation()">
              <div class="export-preview-head">
                <h3>Preview</h3>
                <button type="button" class="export-preview-close" (click)="closeExportPreview()" aria-label="Cerrar preview">
                  <i class="bi bi-x-lg"></i>
                </button>
              </div>
              <p class="export-preview-subtitle">Revisa la imagen antes de descargarla.</p>
              <button type="button" class="export-preview-back" (click)="backToExportOptions()">
                ← Volver a opciones
              </button>

              @if (exportPreviewDataUrl(); as previewUrl) {
                <div class="export-preview-frame">
                  <img [src]="previewUrl" alt="Preview exportado del mazo" />
                </div>
                <div class="export-preview-actions">
                  <button type="button" class="preview-action-btn" (click)="copyExportPreviewToClipboard()">
                    <i class="bi bi-clipboard-check"></i> Copiar
                  </button>
                  <button type="button" class="preview-action-btn primary" (click)="downloadExportPreview()">
                    <i class="bi bi-download"></i> Descargar
                  </button>
                </div>
              }
            </div>
          </div>
        }

        <!-- Errores de validación arriba -->
        @if (validationErrors().length) {
          <div class="errors-box">
            <strong>⚠ Mazo inválido:</strong>
            <ul>
              @for (err of validationErrors(); track err) { <li>{{ err }}</li> }
            </ul>
          </div>
        }

        <!-- Área exportable -->
           <div #deckContent class="deck-export-area"
             [class.export-horizontal]="orientation() === 'horizontal'"
             [class.export-vertical]="orientation() === 'vertical'"
             [class.export-capture]="captureMode()"
             [class.capture-horizontal]="captureMode() && orientation() === 'horizontal'"
             [class.capture-vertical]="captureMode() && orientation() === 'vertical'"
             [attr.data-orientation]="orientation()"
             [attr.data-stack-orientation]="stackOrientation()">

          @switch (viewMode()) {

            @case ('stats') {
              <section class="stats-view">

                <!-- Curva de energía -->
                <div class="stats-card">
                  <h3>⚡ Curva de Energía</h3>
                  @if (hasAnyCost()) {
                    <div class="cost-curve">
                      @for (b of costCurve(); track b.label) {
                        <div class="cc-col" [class.is-avg]="b.label === avgCostBucket()">
                          <span class="cc-count">{{ b.count }}</span>
                          <div class="cc-bar-wrap">
                            <div class="cc-bar" [style.height.%]="b.pct"></div>
                          </div>
                          <span class="cc-label">{{ b.label }}</span>
                        </div>
                      }
                    </div>
                    <p class="muted small">Promedio (excluye runas/legend/BF): <strong>{{ avgCost() }}</strong></p>
                  } @else {
                    <p class="muted">Sin cartas con coste de energía.</p>
                  }
                </div>

                <!-- Distribución de tipos -->
                <div class="stats-card">
                  <h3>🧩 Distribución por tipo</h3>
                  @if (typeDistribution().length) {
                    <div class="dist-list">
                      @for (t of typeDistribution(); track t.type) {
                        <div class="dist-row">
                          <span class="dist-name">{{ t.label }}</span>
                          <div class="dist-bar-wrap">
                            <div class="dist-bar" [style.width.%]="t.pct" [style.background]="t.color"></div>
                          </div>
                          <span class="dist-num">{{ t.count }} ({{ t.pct }}%)</span>
                        </div>
                      }
                    </div>
                  } @else { <p class="muted">Sin datos.</p> }
                </div>

                <!-- Distribución de colores -->
                <div class="stats-card">
                  <h3>🎨 Distribución por color (Main + Side)</h3>
                  @if (colorDistribution().length) {
                    <div class="dist-list">
                      @for (c of colorDistribution(); track c.code) {
                        <div class="dist-row">
                          <span class="dist-name" [style.color]="c.hex">
                            <span class="dot" [style.background]="c.hex"></span>{{ c.label }}
                          </span>
                          <div class="dist-bar-wrap">
                            <div class="dist-bar" [style.width.%]="c.pct" [style.background]="c.hex"></div>
                          </div>
                          <span class="dist-num">{{ c.count }} ({{ c.pct }}%)</span>
                        </div>
                      }
                    </div>
                  } @else { <p class="muted">Sin datos.</p> }
                </div>

                <!-- Probabilidades de robo -->
                <div class="stats-card">
                  <h3>🎲 Probabilidad en mano inicial (4 cartas, mazo principal)</h3>
                  @if (drawProbabilities().length) {
                    <table class="prob-table">
                      <thead>
                        <tr><th>Carta</th><th>Copias</th><th>P(≥1)</th></tr>
                      </thead>
                      <tbody>
                        @for (p of drawProbabilities(); track p.name) {
                          <tr>
                            <td>{{ p.name }}</td>
                            <td class="num">×{{ p.qty }}</td>
                            <td class="num">
                              <span class="prob-pill" [style.--p]="p.pct + '%'">{{ p.pct }}%</span>
                            </td>
                          </tr>
                        }
                      </tbody>
                    </table>
                  } @else { <p class="muted">Mazo principal vacío.</p> }
                </div>

              </section>
            }

            @case ('list') {
              <section class="list-view">
                @for (z of zones; track z) {
                  @let isSide = z === 'side';
                  @let entries = entriesByZone(z);
                  @if (entries.length) {
                    <div class="list-zone" [class.collapsed]="isSide && !sideOpen()">
                      <h2 class="zone-title"
                          [class.is-toggle]="isSide"
                          (click)="isSide && sideOpen.set(!sideOpen())">
                        <span class="zone-name">{{ labels[z] }}</span>
                        <span class="zone-count">{{ countZone(z) }}</span>
                        @if (isSide) {
                          <span class="side-caret">{{ sideOpen() ? '▾' : '▸' }}</span>
                        }
                      </h2>
                      @if (!isSide || sideOpen()) {
                        <table class="entries-table">
                          <thead>
                            <tr><th class="w-qty">#</th><th>Carta</th><th>Tipo</th><th class="num">⚡</th><th class="num">⚔️</th><th></th></tr>
                          </thead>
                          <tbody>
                            @for (e of entries; track e.id || e.card) {
                              @let bs = getBanStatus(e);
                              <tr class="entry-row" (click)="openPreview(e)" [class.banned]="bs?.status === 'banned'">
                                <td class="w-qty">×{{ e.quantity }}</td>
                                <td>
                                  <div class="entry-name">
                                    @if (cardImageUrl(e.card_data); as img) {
                                      <img class="entry-thumb" [src]="img" [alt]="e.card_data?.name || ''"
                                           (error)="onCardImageError(e.card_data, $event)" />
                                    }
                                    <span>{{ e.card_data?.name }}</span>
                                    @if (bs) {
                                      <span class="ban-badge" [class.ban-banned]="bs.status === 'banned'"
                                            [class.ban-limited]="bs.status !== 'banned'"
                                            [title]="banTooltip(bs)">{{ banShort(bs) }}</span>
                                    }
                                  </div>
                                </td>
                                <td>{{ typeLabel(e.card_data?.card_type) }}</td>
                                <td class="num">{{ e.card_data?.energy ?? '—' }}</td>
                                <td class="num">{{ e.card_data?.might ?? '—' }}</td>
                                <td class="num muted small">{{ e.card_data?.card_number }}</td>
                              </tr>
                            }
                          </tbody>
                        </table>
                      }
                    </div>
                  }
                }
              </section>
            }

            @default {
              @if (captureMode() && orientation() === 'horizontal') {
                @let coverCard = exportCoverCardData();
                @let runeEntries = entriesByZone('rune');
                @let battlefieldEntries = entriesByZone('bg');
                @let unitEntries = exportMainEntriesByType('unit');
                @let spellEntries = exportMainEntriesByType('spell');
                @let gearEntries = exportMainEntriesByType('gear');
                @let otherMainEntries = exportMainEntriesByType('other');
                @let sideEntries = entriesByZone('side');

                <section class="rb-export-layout">
                  <div class="rb-export-top-line" aria-hidden="true"></div>

                  <header class="rb-export-head">
                    <div class="rb-export-head-main">
                      @if (cardImageUrl(coverCard); as coverImg) {
                        <img class="rb-export-cover" [src]="coverImg" [alt]="d.name"
                             (error)="onCardImageError(coverCard, $event)" />
                      } @else {
                        <div class="rb-export-cover rb-export-cover-empty">LEGEND</div>
                      }

                      <div class="rb-export-copy">
                        <p class="rb-export-kicker">STANDARD · {{ totalCards() }} CARDS</p>
                        <h2 class="rb-export-title">{{ d.name }}</h2>
                        <p class="rb-export-date">{{ formatExportDate(d.updated_at) }}</p>
                      </div>
                    </div>

                    <div class="rb-export-brand">
                      @if (exportQrDataUrl(); as qrUrl) {
                        <img class="rb-export-qr-image" [src]="qrUrl" alt="QR del mazo" />
                      } @else {
                        <div class="rb-export-qr-fallback" aria-hidden="true">SF</div>
                      }
                      <div class="rb-export-brand-mark">shadowforge</div>
                      <p class="rb-export-url">{{ exportDeckPathLabel() }}</p>
                    </div>
                  </header>

                  <div class="rb-export-zone-grid" [attr.data-stack-orientation]="stackOrientation()">
                    @if (runeEntries.length) {
                      <section class="rb-export-zone zone-runes">
                        <h3 class="rb-export-zone-title">Runes <span>{{ sumEntryQuantity(runeEntries) }}</span></h3>
                        <div class="card-grid" [attr.data-stack-orientation]="stackOrientation()">
                          @for (e of runeEntries; track e.id || e.card) {
                            <div class="card-stack" [class.qty-2]="e.quantity === 2" [class.qty-3]="e.quantity >= 3"
                                 [title]="e.card_data?.name || ''">
                              @if (e.quantity >= 3 && cardImageUrl(e.card_data); as img) {
                                <img class="shadow s3" [src]="img" aria-hidden="true" (error)="onCardImageError(e.card_data, $event)" />
                              }
                              @if (e.quantity >= 2 && cardImageUrl(e.card_data); as img) {
                                <img class="shadow s2" [src]="img" aria-hidden="true" (error)="onCardImageError(e.card_data, $event)" />
                              }
                              @if (cardImageUrl(e.card_data); as img) {
                                <img class="top" [src]="img" [alt]="e.card_data?.name || ''" (error)="onCardImageError(e.card_data, $event)" />
                              } @else {
                                <div class="top placeholder">{{ e.card_data?.card_number || 'SIN IMG' }}</div>
                              }
                              @if (e.quantity > 1) {
                                <span class="qty-badge">×{{ e.quantity }}</span>
                              }
                            </div>
                          }
                        </div>
                      </section>
                    }

                    @if (battlefieldEntries.length) {
                      <section class="rb-export-zone zone-battlefields">
                        <h3 class="rb-export-zone-title">Battlefields <span>{{ sumEntryQuantity(battlefieldEntries) }}</span></h3>
                        <div class="card-grid" [attr.data-stack-orientation]="stackOrientation()">
                          @for (e of battlefieldEntries; track e.id || e.card) {
                            <div class="card-stack" [class.qty-2]="e.quantity === 2" [class.qty-3]="e.quantity >= 3"
                                 [title]="e.card_data?.name || ''">
                              @if (e.quantity >= 3 && cardImageUrl(e.card_data); as img) {
                                <img class="shadow s3" [src]="img" aria-hidden="true" (error)="onCardImageError(e.card_data, $event)" />
                              }
                              @if (e.quantity >= 2 && cardImageUrl(e.card_data); as img) {
                                <img class="shadow s2" [src]="img" aria-hidden="true" (error)="onCardImageError(e.card_data, $event)" />
                              }
                              @if (cardImageUrl(e.card_data); as img) {
                                <img class="top" [src]="img" [alt]="e.card_data?.name || ''" (error)="onCardImageError(e.card_data, $event)" />
                              } @else {
                                <div class="top placeholder">{{ e.card_data?.card_number || 'SIN IMG' }}</div>
                              }
                              @if (e.quantity > 1) {
                                <span class="qty-badge">×{{ e.quantity }}</span>
                              }
                            </div>
                          }
                        </div>
                      </section>
                    }

                    @if (unitEntries.length) {
                      <section class="rb-export-zone zone-units">
                        <h3 class="rb-export-zone-title">Units <span>{{ sumEntryQuantity(unitEntries) }}</span></h3>
                        <div class="card-grid" [attr.data-stack-orientation]="stackOrientation()">
                          @for (e of unitEntries; track e.id || e.card) {
                            <div class="card-stack" [class.qty-2]="e.quantity === 2" [class.qty-3]="e.quantity >= 3"
                                 [title]="e.card_data?.name || ''">
                              @if (e.quantity >= 3 && cardImageUrl(e.card_data); as img) {
                                <img class="shadow s3" [src]="img" aria-hidden="true" (error)="onCardImageError(e.card_data, $event)" />
                              }
                              @if (e.quantity >= 2 && cardImageUrl(e.card_data); as img) {
                                <img class="shadow s2" [src]="img" aria-hidden="true" (error)="onCardImageError(e.card_data, $event)" />
                              }
                              @if (cardImageUrl(e.card_data); as img) {
                                <img class="top" [src]="img" [alt]="e.card_data?.name || ''" (error)="onCardImageError(e.card_data, $event)" />
                              } @else {
                                <div class="top placeholder">{{ e.card_data?.card_number || 'SIN IMG' }}</div>
                              }
                              @if (e.quantity > 1) {
                                <span class="qty-badge">×{{ e.quantity }}</span>
                              }
                            </div>
                          }
                        </div>
                      </section>
                    }

                    @if (spellEntries.length) {
                      <section class="rb-export-zone zone-spells">
                        <h3 class="rb-export-zone-title">Spells <span>{{ sumEntryQuantity(spellEntries) }}</span></h3>
                        <div class="card-grid" [attr.data-stack-orientation]="stackOrientation()">
                          @for (e of spellEntries; track e.id || e.card) {
                            <div class="card-stack" [class.qty-2]="e.quantity === 2" [class.qty-3]="e.quantity >= 3"
                                 [title]="e.card_data?.name || ''">
                              @if (e.quantity >= 3 && cardImageUrl(e.card_data); as img) {
                                <img class="shadow s3" [src]="img" aria-hidden="true" (error)="onCardImageError(e.card_data, $event)" />
                              }
                              @if (e.quantity >= 2 && cardImageUrl(e.card_data); as img) {
                                <img class="shadow s2" [src]="img" aria-hidden="true" (error)="onCardImageError(e.card_data, $event)" />
                              }
                              @if (cardImageUrl(e.card_data); as img) {
                                <img class="top" [src]="img" [alt]="e.card_data?.name || ''" (error)="onCardImageError(e.card_data, $event)" />
                              } @else {
                                <div class="top placeholder">{{ e.card_data?.card_number || 'SIN IMG' }}</div>
                              }
                              @if (e.quantity > 1) {
                                <span class="qty-badge">×{{ e.quantity }}</span>
                              }
                            </div>
                          }
                        </div>
                      </section>
                    }

                    @if (gearEntries.length) {
                      <section class="rb-export-zone zone-gear">
                        <h3 class="rb-export-zone-title">Gear <span>{{ sumEntryQuantity(gearEntries) }}</span></h3>
                        <div class="card-grid" [attr.data-stack-orientation]="stackOrientation()">
                          @for (e of gearEntries; track e.id || e.card) {
                            <div class="card-stack" [class.qty-2]="e.quantity === 2" [class.qty-3]="e.quantity >= 3"
                                 [title]="e.card_data?.name || ''">
                              @if (e.quantity >= 3 && cardImageUrl(e.card_data); as img) {
                                <img class="shadow s3" [src]="img" aria-hidden="true" (error)="onCardImageError(e.card_data, $event)" />
                              }
                              @if (e.quantity >= 2 && cardImageUrl(e.card_data); as img) {
                                <img class="shadow s2" [src]="img" aria-hidden="true" (error)="onCardImageError(e.card_data, $event)" />
                              }
                              @if (cardImageUrl(e.card_data); as img) {
                                <img class="top" [src]="img" [alt]="e.card_data?.name || ''" (error)="onCardImageError(e.card_data, $event)" />
                              } @else {
                                <div class="top placeholder">{{ e.card_data?.card_number || 'SIN IMG' }}</div>
                              }
                              @if (e.quantity > 1) {
                                <span class="qty-badge">×{{ e.quantity }}</span>
                              }
                            </div>
                          }
                        </div>
                      </section>
                    }

                    @if (otherMainEntries.length) {
                      <section class="rb-export-zone zone-other">
                        <h3 class="rb-export-zone-title">Other Main <span>{{ sumEntryQuantity(otherMainEntries) }}</span></h3>
                        <div class="card-grid" [attr.data-stack-orientation]="stackOrientation()">
                          @for (e of otherMainEntries; track e.id || e.card) {
                            <div class="card-stack" [class.qty-2]="e.quantity === 2" [class.qty-3]="e.quantity >= 3"
                                 [title]="e.card_data?.name || ''">
                              @if (e.quantity >= 3 && cardImageUrl(e.card_data); as img) {
                                <img class="shadow s3" [src]="img" aria-hidden="true" (error)="onCardImageError(e.card_data, $event)" />
                              }
                              @if (e.quantity >= 2 && cardImageUrl(e.card_data); as img) {
                                <img class="shadow s2" [src]="img" aria-hidden="true" (error)="onCardImageError(e.card_data, $event)" />
                              }
                              @if (cardImageUrl(e.card_data); as img) {
                                <img class="top" [src]="img" [alt]="e.card_data?.name || ''" (error)="onCardImageError(e.card_data, $event)" />
                              } @else {
                                <div class="top placeholder">{{ e.card_data?.card_number || 'SIN IMG' }}</div>
                              }
                              @if (e.quantity > 1) {
                                <span class="qty-badge">×{{ e.quantity }}</span>
                              }
                            </div>
                          }
                        </div>
                      </section>
                    }

                    @if (sideEntries.length) {
                      <section class="rb-export-zone zone-side-deck">
                        <h3 class="rb-export-zone-title">Side Deck <span>{{ sumEntryQuantity(sideEntries) }}</span></h3>
                        <div class="card-grid" [attr.data-stack-orientation]="stackOrientation()">
                          @for (e of sideEntries; track e.id || e.card) {
                            <div class="card-stack" [class.qty-2]="e.quantity === 2" [class.qty-3]="e.quantity >= 3"
                                 [title]="e.card_data?.name || ''">
                              @if (e.quantity >= 3 && cardImageUrl(e.card_data); as img) {
                                <img class="shadow s3" [src]="img" aria-hidden="true" (error)="onCardImageError(e.card_data, $event)" />
                              }
                              @if (e.quantity >= 2 && cardImageUrl(e.card_data); as img) {
                                <img class="shadow s2" [src]="img" aria-hidden="true" (error)="onCardImageError(e.card_data, $event)" />
                              }
                              @if (cardImageUrl(e.card_data); as img) {
                                <img class="top" [src]="img" [alt]="e.card_data?.name || ''" (error)="onCardImageError(e.card_data, $event)" />
                              } @else {
                                <div class="top placeholder">{{ e.card_data?.card_number || 'SIN IMG' }}</div>
                              }
                              @if (e.quantity > 1) {
                                <span class="qty-badge">×{{ e.quantity }}</span>
                              }
                            </div>
                          }
                        </div>
                      </section>
                    }
                  </div>

                  <footer class="rb-export-summary">{{ exportSummaryLine() }}</footer>
                </section>
              } @else {
                <!-- Grid (default) -->
                @for (z of zones; track z) {
                  @let isSide = z === 'side';
                  @let entries = entriesByZone(z);
                  @if (entries.length) {
                    <section class="zone-section" [class.collapsed]="isSide && !sideOpen()" [class.side-zone]="isSide" [attr.data-zone]="z">
                      <h2 class="zone-title"
                          [class.is-toggle]="isSide"
                          (click)="isSide && sideOpen.set(!sideOpen())">
                        <span class="zone-name">{{ labels[z] }}</span>
                        <span class="zone-count">{{ countZone(z) }}</span>
                        @if (isSide) {
                          <span class="side-caret">{{ sideOpen() ? '▾' : '▸' }}</span>
                        }
                      </h2>
                      @if (!isSide || sideOpen()) {
                        <div class="card-grid" [attr.data-stack-orientation]="stackOrientation()">
                          @for (e of entries; track e.id || e.card) {
                            @let bs = getBanStatus(e);
                             <div class="card-stack"
                               role="button"
                               tabindex="0"
                               [class.qty-2]="e.quantity === 2"
                               [class.qty-3]="e.quantity >= 3"
                               [class.banned]="bs?.status === 'banned'"
                               (click)="openPreview(e)"
                               (keydown.enter)="openPreview(e)"
                               (keydown.space)="onCardStackSpace($event, e)"
                               [title]="e.card_data?.name || ''">
                              @if (e.quantity >= 3 && cardImageUrl(e.card_data); as img) {
                                <img class="shadow s3" [src]="img" aria-hidden="true"
                                     (error)="onCardImageError(e.card_data, $event)" />
                              }
                              @if (e.quantity >= 2 && cardImageUrl(e.card_data); as img) {
                                <img class="shadow s2" [src]="img" aria-hidden="true"
                                     (error)="onCardImageError(e.card_data, $event)" />
                              }
                              @if (cardImageUrl(e.card_data); as img) {
                                <img class="top" [src]="img" [alt]="e.card_data?.name || ''"
                                     (error)="onCardImageError(e.card_data, $event)" />
                              } @else {
                                <div class="top placeholder">{{ e.card_data?.card_number || 'SIN IMG' }}</div>
                              }
                              @if (e.quantity > 1) {
                                <span class="qty-badge">×{{ e.quantity }}</span>
                              }
                              @if (bs) {
                                <span class="ban-overlay" [class.ban-banned]="bs.status === 'banned'"
                                      [class.ban-limited]="bs.status !== 'banned'"
                                      [title]="banTooltip(bs)">{{ banShort(bs) }}</span>
                              }
                              @if (isOwner() && e.card_data?.id) {
                                <button type="button"
                                        class="cover-star"
                                        [class.is-cover]="d.cover_card === e.card_data?.id"
                                        (click)="toggleCover($event, e)"
                                        [title]="d.cover_card === e.card_data?.id ? 'Portada actual (clic para quitar)' : 'Fijar como portada del mazo'">
                                  {{ d.cover_card === e.card_data?.id ? '★' : '☆' }}
                                </button>
                              }
                              @if (d.cover_card === e.card_data?.id) {
                                <span class="cover-badge" title="Portada del mazo">★</span>
                              }
                              <span class="card-name">{{ e.card_data?.name }}</span>
                            </div>
                          }
                        </div>
                      }
                    </section>
                  }
                }
              }
            }

          }

        </div>
      </div>

      <!-- FAB salir presentación -->
      @if (presentationMode()) {
        <button class="exit-presentation-fab" (click)="togglePresentation()" title="Salir (Esc)">✕</button>
      }

      <!-- Modal preview -->
      @if (previewEntry(); as pe) {
        <div class="preview-overlay" (click)="closePreview()">
          <div class="preview-box" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
            <button class="preview-close" (click)="closePreview()" aria-label="Cerrar">✕</button>
            @if (previewLoading()) {
              <p class="muted" style="padding:3rem;text-align:center">Cargando…</p>
            } @else if (previewDetail(); as c) {
              <div class="preview-layout">
                @if (cardImageUrl(c); as img) {
                  <img class="preview-img" [src]="img" [alt]="c.name" (error)="onCardImageError(c, $event)" />
                }
                <div class="preview-info">
                  <h2>{{ c.name }}</h2>
                  <p class="muted">
                    <button type="button" class="copy-cn" (click)="copyText(c.card_number, 'Código copiado')" title="Copiar código">{{ c.card_number }}</button>
                    · {{ c.set?.name || c.set?.code || '—' }}
                  </p>
                  @let pbs = getBanStatusByCardId(c.id);
                  @if (pbs) {
                    <div class="preview-ban" [class.ban-banned]="pbs.status === 'banned'"
                                              [class.ban-limited]="pbs.status !== 'banned'">
                      @if (pbs.status === 'banned') { ⛔ Baneada en Standard }
                      @else { ⚠️ Limitada a {{ pbs.max_copies }} copia(s) }
                    </div>
                  }
                  <div class="preview-badges">
                    @if (c.card_type) { <span class="pv-badge">{{ typeLabel(c.card_type) }}</span> }
                    @if (c.rarity) { <span class="pv-badge">{{ c.rarity }}</span> }
                    @for (col of c.colors; track col) {
                      <span class="pv-badge color" [style.background]="hex(col) + '20'" [style.borderColor]="hex(col) + '80'">
                        {{ label(col) }}
                      </span>
                    }
                    @for (st of c.subtypes; track st) { <span class="pv-badge">{{ st }}</span> }
                  </div>
                  <div class="preview-stats">
                    @if (c.energy != null) { <div><span>Energy</span><strong>{{ c.energy }}</strong></div> }
                    @if (c.power != null) { <div><span>Power</span><strong>{{ c.power }}</strong></div> }
                    @if (c.might != null) { <div><span>Might</span><strong>{{ c.might }}</strong></div> }
                  </div>
                  @if (c.description) {
                    <h3>Descripción</h3>
                    <pre class="preview-desc">{{ c.description }}</pre>
                  } @else {
                    <p class="muted" style="margin-top:1rem">Esta carta no tiene texto.</p>
                  }
                  <div class="preview-actions">
                    <a class="action-btn" [routerLink]="['/riftbound/cards', c.card_number]" (click)="closePreview()">🔎 Ver en explorador</a>
                    <button class="action-btn" (click)="copyText(deepLinkUrl(c.id), 'Enlace de la carta copiado')">🔗 Copiar enlace</button>
                    @if (isOwner()) {
                      <button class="action-btn"
                              (click)="toggleCoverByCardId(c.id)"
                              [disabled]="settingCover()">
                        {{ deck()?.cover_card === c.id ? '⭐ Quitar portada' : '⭐ Usar como portada' }}
                      </button>
                    }
                  </div>
                  <app-tcg-price [cardName]="c.name" [compact]="false" [showLink]="true"></app-tcg-price>
                </div>
              </div>
            } @else {
              @if (cardImageUrl(pe.card_data); as img) {
                <img class="preview-img" [src]="img" [alt]="pe.card_data?.name || ''"
                     (error)="onCardImageError(pe.card_data, $event)" />
              }
              <h3>{{ pe.card_data?.name }} <small>{{ pe.card_data?.card_number }}</small></h3>
            }
          </div>
        </div>
      }

      <!-- Toast de compartir / copiar -->
      @if (shareToast()) {
        <div class="share-toast" role="status">✓ {{ toastMsg() }}</div>
      }

      <!-- Modal Probar mano -->
      @if (showHandModal()) {
        <div class="preview-overlay" (click)="closeHandModal()">
          <div class="preview-box hand-box" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
            <button class="preview-close" (click)="closeHandModal()" aria-label="Cerrar">✕</button>
            <h2 style="margin:.25rem 0 1rem">🎴 Mano de apertura ({{ handSize }} cartas)</h2>
            @if (!handCards().length) {
              <p class="muted">El mazo principal está vacío.</p>
            } @else {
              <div class="hand-grid">
                @for (e of handCards(); track $index) {
                  @if (cardImageUrl(e.card_data); as img) {
                    <img class="hand-card" [src]="img" [alt]="e.card_data?.name || ''" [title]="e.card_data?.name || ''"
                         (error)="onCardImageError(e.card_data, $event)" />
                  } @else {
                    <div class="hand-card placeholder">{{ e.card_data?.card_number }}</div>
                  }
                }
              </div>
            }
            <div class="hand-actions">
              <button class="action-btn" (click)="drawHand()" [disabled]="!handCards().length">
                <i class="bi bi-arrow-clockwise"></i><span>Otra mano</span>
              </button>
              <button class="action-btn accent" (click)="closeHandModal()">
                <i class="bi bi-check2"></i><span>Cerrar</span>
              </button>
            </div>
          </div>
        </div>
      }

      <!-- Overlay de exportación -->
      @if (exporting()) {
        <div class="exporting-overlay">
          <div class="exporting-box">
            <div class="spinner"></div>
            <p>Generando imagen…</p>
          </div>
        </div>
      }
    } @else {
      <p class="loading">Mazo no encontrado.</p>
    }
  `,
  styles: [`
    .container { max-width: 1200px; margin: 0 auto; padding: 1.25rem 1rem 3rem; }
    @media (max-width: 600px) { .container { padding: 0.85rem 0.6rem 2rem; } }
    .loading { color: #888; text-align: center; padding: 3rem; }
    .back-link { display: inline-block; opacity: .8; margin-bottom: 1rem; text-decoration: none; color: #c8c8da; }
    .back-link:hover { opacity: 1; color: #e94560; }
    .muted { opacity: .65; }
    .small { font-size: .8rem; }
    .num { text-align: right; font-variant-numeric: tabular-nums; }

    /* Hero */
    .deck-hero {
      position: relative; border-radius: 14px; overflow: hidden;
      background: linear-gradient(135deg, #111827 0%, #1a1a2e 100%);
      border: 1px solid #2a2a4a; min-height: 220px; margin-bottom: 1.25rem;
    }
    .hero-bg {
      position: absolute; inset: 0;
      background-size: cover; background-position: center 22%;
      filter: blur(28px) saturate(1.2); opacity: .55; transform: scale(1.15);
    }
    .hero-overlay {
      position: absolute; inset: 0;
      background: linear-gradient(180deg, rgba(10,20,40,.55) 0%, rgba(10,20,40,.92) 100%);
    }
    .hero-content {
      position: relative; z-index: 1; display: flex; gap: 1.25rem;
      padding: 1.25rem; align-items: stretch;
    }
    .hero-cover {
      width: 180px; height: 252px; object-fit: cover; object-position: center 25%;
      border-radius: 10px; border: 1px solid #e9456066; flex-shrink: 0;
      box-shadow: 0 10px 30px rgba(0,0,0,.5);
    }
    .hero-cover-empty {
      display: grid; place-items: center; background: #16213e;
      color: #2a2a4a; font-size: 3.2rem;
    }
    .hero-info { display: flex; flex-direction: column; min-width: 0; flex: 1; }
    .deck-title {
      margin: 0 0 .65rem; font-size: 1.9rem; line-height: 1.15;
      color: #fff; text-shadow: 0 2px 8px rgba(0,0,0,.6);
      font-weight: 700; word-break: break-word;
      background: none !important;
      -webkit-text-fill-color: #fff !important;
      -webkit-background-clip: border-box !important;
      background-clip: border-box !important;
    }
    .deck-chips { display: flex; flex-wrap: wrap; gap: .4rem; margin-bottom: .6rem; }
    .chip {
      display: inline-flex; align-items: center; gap: .3rem;
      padding: .25rem .65rem; border-radius: 999px;
      background: rgba(22,33,62,.7); border: 1px solid #2a3a4a;
      color: #e0e0e0; font-size: .8rem; backdrop-filter: blur(4px);
    }
    .chip-color {
      border-color: color-mix(in srgb, var(--c) 50%, transparent);
      background: color-mix(in srgb, var(--c) 14%, rgba(22,33,62,.7));
      color: var(--c); font-weight: 600;
    }
    .chip-color .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--c); }
    .chip-public { color: #4ade80; border-color: #4ade8055; }
    .chip-private { color: #888; }
    .chip-cards { color: #ffbd39; }
    .hero-description {
      color: #d0d0e0; font-size: .92rem; line-height: 1.5;
      margin: .3rem 0 0; padding-left: .7rem; border-left: 3px solid #e94560;
      white-space: pre-wrap; max-height: 6em; overflow: hidden;
    }

    @media (max-width: 720px) {
      .hero-content { flex-direction: column; align-items: flex-start; }
      .hero-cover { width: 140px; height: 196px; }
      .deck-title { font-size: 1.5rem; }
    }

    /* Action bar */
    .action-bar {
      display: flex; gap: .5rem; align-items: center; flex-wrap: wrap;
      padding: .45rem .6rem; margin-bottom: 1rem;
      background: #111827; border: 1px solid #1e3a4a; border-radius: 12px;
    }
    .action-spacer { flex: 1; }
    .action-btn {
      padding: .5rem .85rem; border-radius: 9px; cursor: pointer;
      background: transparent; border: 1px solid #2a3a4a; color: #b0b8c4;
      font-family: inherit; font-size: .88rem;
      display: inline-flex; align-items: center; gap: .35rem;
      transition: all .15s; text-decoration: none;
    }
    .action-btn:hover:not(:disabled) { background: #1e2d3d; border-color: #3a5a6a; color: #e0e0e0; }
    .action-btn.accent { color: #4fc3f7; border-color: rgba(79,195,247,0.4); background: transparent; }
    .action-btn.accent:hover { background: rgba(79,195,247,0.12); border-color: #4fc3f7; color: #4fc3f7; filter: none; }
    .action-btn.danger { color: #d97a7a; border-color: rgba(220,53,69,.4); }
    .action-btn.danger:hover { background: rgba(220,53,69,.14); border-color: #dc3545; color: #fff; }
    .action-btn:disabled { opacity: .5; cursor: not-allowed; }

    /* Seg control */
    .seg-control {
      display: inline-flex; padding: 2px; border-radius: 10px;
      background: #0f1923; border: 1px solid #2a3a4a;
    }
    .seg-btn {
      padding: .38rem .85rem; border-radius: 8px; cursor: pointer;
      background: transparent; border: none; color: #8899aa;
      font-family: inherit; font-size: .85rem; transition: all .15s;
    }
    .seg-btn:hover { color: #e0e0e0; }
    .seg-btn.active {
      background: #2a8a8a; color: #fff; font-weight: 600;
      box-shadow: 0 1px 3px rgba(0,0,0,.3);
    }

    /* More menu */
    .more-menu-wrap { position: relative; }
    .more-menu {
      position: absolute; top: calc(100% + 6px); right: 0; z-index: 50;
      min-width: 200px; background: #1a1a2e; border: 1px solid #2a3a4a;
      border-radius: 10px; padding: .35rem; box-shadow: 0 12px 30px rgba(0,0,0,.5);
      display: flex; flex-direction: column;
    }
    .more-menu button {
      text-align: left; padding: .55rem .8rem; background: transparent;
      border: none; color: #e0e0e0; font-family: inherit; font-size: .85rem;
      border-radius: 6px; cursor: pointer;
    }
    .more-menu button:hover { background: #2a2a4a; color: #fff; }

    .orient-menu-wrap { position: relative; }
    .orient-menu {
      position: absolute; top: calc(100% + 6px); left: 0; z-index: 60;
      min-width: 220px; background: #0f1923; border: 1px solid #2a3a4a;
      border-radius: 10px; padding: .35rem; box-shadow: 0 12px 30px rgba(0,0,0,.6);
    }
    .orient-menu button {
      display: flex; align-items: center; gap: .55rem; width: 100%;
      padding: .5rem .65rem; border: 0; border-radius: 7px;
      background: transparent; color: #c0c8d4; text-align: left; font-size: .84rem;
      cursor: pointer;
    }
    .orient-menu button i { width: 16px; color: #8ea1b6; }
    .orient-menu button:hover {
      background: rgba(79,195,247,.12); color: #fff;
    }
    .orient-menu button:hover i { color: #8bd9ff; }
    .orient-menu button.active {
      background: rgba(79,195,247,.2); color: #fff; font-weight: 600;
    }
    .orient-menu button.active i { color: #8bd9ff; }

    .export-modal-overlay {
      position: fixed; inset: 0; z-index: 1400;
      background: rgba(6,10,16,.74);
      display: flex; align-items: center; justify-content: center;
      padding: 1rem;
    }
    .export-modal {
      width: min(680px, 96vw);
      max-height: 90vh;
      overflow: auto;
      border-radius: 14px;
      border: 1px solid #31495d;
      background: #0f1923;
      box-shadow: 0 20px 50px rgba(0,0,0,.65);
    }
    .export-modal-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: .9rem .95rem .75rem;
      border-bottom: 1px solid #263d52;
    }
    .export-modal-head h3 {
      margin: 0;
      color: #e8f3ff;
      font-size: 1.2rem;
      font-weight: 700;
    }
    .export-modal-close {
      width: 34px;
      height: 34px;
      border-radius: 8px;
      border: 1px solid #31495d;
      background: #13202e;
      color: #cfe1f1;
      cursor: pointer;
    }
    .export-modal-body {
      padding: .9rem .95rem;
      display: flex;
      flex-direction: column;
      gap: .9rem;
    }
    .export-opt-section {
      padding: .7rem;
      border-radius: 10px;
      border: 1px solid #2c455c;
      background: rgba(19,32,46,.45);
    }
    .export-opt-title {
      display: block;
      color: #d8e6f6;
      font-size: .86rem;
      font-weight: 700;
      margin-bottom: .55rem;
    }
    .export-opt-row {
      display: grid;
      gap: .5rem;
    }
    .export-opt-row.two {
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
    }
    .opt-chip {
      height: 38px;
      border-radius: 9px;
      border: 1px solid #2f4760;
      background: #141f2b;
      color: #dbe8f5;
      font-size: .84rem;
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: .4rem;
      cursor: pointer;
    }
    .opt-chip.active {
      background: #d3a84a;
      border-color: #d3a84a;
      color: #1a1a1a;
    }
    .export-modal-foot {
      display: flex;
      justify-content: flex-end;
      gap: .5rem;
      padding: .8rem .95rem 1rem;
      border-top: 1px solid #263d52;
    }
    .export-foot-btn {
      min-width: 132px;
      height: 40px;
      border-radius: 9px;
      border: 1px solid #2f4760;
      background: #141f2b;
      color: #dbe8f5;
      font-size: .86rem;
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: .45rem;
      cursor: pointer;
    }
    .export-foot-btn.primary {
      background: #d3a84a;
      border-color: #d3a84a;
      color: #1a1a1a;
    }
    .export-foot-btn:disabled {
      opacity: .55;
      cursor: not-allowed;
    }

    .export-preview-overlay {
      position: fixed;
      inset: 0;
      z-index: 1450;
      background: rgba(6,10,16,.78);
      backdrop-filter: blur(2px);
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1rem;
    }
    .export-preview-modal {
      width: min(1000px, 97vw);
      max-height: 92vh;
      overflow: auto;
      border-radius: 14px;
      border: 1px solid #31495d;
      background: #0f1923;
      box-shadow: 0 20px 50px rgba(0,0,0,.65);
      padding: .95rem;
    }
    .export-preview-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .export-preview-head h3 {
      margin: 0;
      color: #e8f3ff;
      font-size: 1.45rem;
      font-weight: 700;
    }
    .export-preview-close {
      width: 34px;
      height: 34px;
      border-radius: 8px;
      border: 1px solid #31495d;
      background: #13202e;
      color: #cfe1f1;
      cursor: pointer;
    }
    .export-preview-subtitle {
      margin: .35rem 0 .55rem;
      color: #a9bacd;
      font-size: .95rem;
    }
    .export-preview-back {
      border: 0;
      background: transparent;
      color: #bfcfdf;
      font-size: .95rem;
      margin-bottom: .7rem;
      cursor: pointer;
      padding: 0;
    }
    .export-preview-frame {
      border: 1px solid #22384d;
      border-radius: 10px;
      background: #0b141d;
      padding: .5rem;
      overflow: auto;
      max-height: 68vh;
      display: flex;
      justify-content: center;
    }
    .export-preview-frame img {
      width: 100%;
      min-width: 0;
      max-width: 100%;
      height: auto;
      border-radius: 8px;
      display: block;
    }
    .export-preview-actions {
      margin-top: .75rem;
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: .55rem;
    }
    .preview-action-btn {
      height: 46px;
      border-radius: 9px;
      border: 1px solid #2f4760;
      background: #141f2b;
      color: #dbe8f5;
      font-size: .92rem;
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: .5rem;
      cursor: pointer;
    }
    .preview-action-btn.primary {
      background: #d3a84a;
      border-color: #d3a84a;
      color: #1a1a1a;
    }

    /* Errors */
    .errors-box {
      margin: 1.25rem 0; padding: .85rem 1rem;
      background: rgba(233,69,96,.1); border: 1px solid #e9456066;
      border-radius: 8px; color: #ffb8c1;
    }
    .errors-box ul { margin: .35rem 0 0; padding-left: 1.25rem; }

    /* Zona */
    .zone-section { margin-bottom: 1.75rem; }
    .zone-title {
      display: flex; align-items: center; gap: .65rem; margin: 0 0 .85rem;
      padding-bottom: .4rem; border-bottom: 1px solid #2a2a4a;
      color: #fff; font-size: 1.15rem;
    }
    .zone-title.is-toggle { cursor: pointer; user-select: none; }
    .zone-title.is-toggle:hover { color: #ff6b7d; }
    .zone-name { font-weight: 700; }
    .zone-count {
      background: #16213e; color: #ffbd39; padding: .12rem .55rem;
      border-radius: 999px; font-size: .8rem; font-weight: 600;
    }
    .side-caret { margin-left: auto; opacity: .7; }

    /* Card grid (stacks) */
    .card-grid {
      --stack-top-x: 0px;
      --stack-top-y: 0px;
      --stack-s2-x: 6px;
      --stack-s2-y: 6px;
      --stack-s3-x: 12px;
      --stack-s3-y: 12px;

      display: grid; gap: 1.5rem 1.1rem;
      grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    }
    .card-grid[data-stack-orientation='up'] {
      --stack-top-x: 0px;
      --stack-top-y: 12px;
      --stack-s2-x: 0px;
      --stack-s2-y: 6px;
      --stack-s3-x: 0px;
      --stack-s3-y: 0px;
    }
    .card-grid[data-stack-orientation='left'] {
      --stack-top-x: 12px;
      --stack-top-y: 0px;
      --stack-s2-x: 6px;
      --stack-s2-y: 0px;
      --stack-s3-x: 0px;
      --stack-s3-y: 0px;
    }
    .card-grid[data-stack-orientation='right'] {
      --stack-top-x: 0px;
      --stack-top-y: 0px;
      --stack-s2-x: 6px;
      --stack-s2-y: 0px;
      --stack-s3-x: 12px;
      --stack-s3-y: 0px;
    }
    .card-grid[data-stack-orientation='center'] {
      --stack-top-x: 0px;
      --stack-top-y: 0px;
      --stack-s2-x: 0px;
      --stack-s2-y: 0px;
      --stack-s3-x: 0px;
      --stack-s3-y: 0px;
    }
    .card-grid[data-stack-orientation='center'] .card-stack .shadow { display: none; }
    .card-stack {
      position: relative; aspect-ratio: 63/88; padding: 0;
      background: transparent; border: none; cursor: pointer;
      width: 100%;
      max-width: 150px;
      justify-self: center;
      transition: transform .15s; outline: none;
    }
    .card-stack:hover { transform: translateY(-4px); }
    .card-stack:focus-visible { outline: 2px solid #e94560; outline-offset: 4px; border-radius: 6px; }
    .card-stack .top, .card-stack .shadow {
      position: absolute; inset: 0; width: 100%; height: 100%;
      object-fit: cover; border-radius: 6px;
      box-shadow: 0 4px 14px rgba(0,0,0,.4);
    }
    .card-stack.banned .top { filter: grayscale(.8) brightness(.6); }
    .card-stack .placeholder {
      display: grid; place-items: center;
      background: #16213e; color: #c8c8da; padding: 1rem; text-align: center;
    }
    .shadow.s2 { transform: translate(var(--stack-s2-x), var(--stack-s2-y)); filter: brightness(.6); z-index: 0; }
    .shadow.s3 { transform: translate(var(--stack-s3-x), var(--stack-s3-y)); filter: brightness(.4); z-index: -1; }
    .card-stack .top { z-index: 1; transform: translate(var(--stack-top-x), var(--stack-top-y)); }
    .qty-badge {
      position: absolute; top: 6px; left: 6px; z-index: 3;
      background: linear-gradient(135deg, #e94560 0%, #ff6b7d 100%);
      color: #0f0f23; font-weight: 800; font-size: .82rem;
      padding: .15rem .5rem; border-radius: 999px;
      box-shadow: 0 2px 8px rgba(0,0,0,.5);
    }
    .ban-overlay {
      position: absolute; top: 6px; right: 6px; z-index: 3;
      padding: .15rem .5rem; border-radius: 999px;
      font-weight: 800; font-size: .72rem;
      box-shadow: 0 2px 8px rgba(0,0,0,.5);
    }
    .ban-overlay.ban-banned { background: #dc3545; color: #fff; }
    .ban-overlay.ban-limited { background: #f59e0b; color: #1a1a2e; }
    .card-name {
      position: absolute; left: 0; right: 0; bottom: -1.35rem;
      text-align: center; font-size: .75rem; color: #c8c8da;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .card-stack.qty-2, .card-stack.qty-3 { margin: 9px; }

    /* List view */
    .list-view .list-zone { margin-bottom: 1.5rem; }
    .entries-table {
      width: 100%; border-collapse: collapse; font-size: .9rem;
      background: #111827; border: 1px solid #2a2a4a; border-radius: 8px; overflow: hidden;
    }
    .entries-table th, .entries-table td { padding: .55rem .75rem; text-align: left; }
    .entries-table thead th {
      background: #1a1a2e; color: #e94560; font-weight: 700;
      border-bottom: 1px solid #2a2a4a;
    }
    .entries-table .w-qty { width: 64px; text-align: center; font-weight: 700; color: #ffbd39; }
    .entries-table tbody tr { border-top: 1px solid #1f1f3a; cursor: pointer; transition: background .12s; }
    .entries-table tbody tr:hover { background: #1a1a2e; }
    .entries-table tr.banned { opacity: .55; }
    .entry-name { display: flex; align-items: center; gap: .55rem; }
    .entry-thumb { width: 32px; height: 44px; object-fit: cover; border-radius: 3px; flex-shrink: 0; }
    .ban-badge {
      padding: .1rem .45rem; border-radius: 999px; font-size: .7rem; font-weight: 700;
    }
    .ban-badge.ban-banned { background: #dc3545; color: #fff; }
    .ban-badge.ban-limited { background: #f59e0b; color: #1a1a2e; }

    /* Stats */
    .stats-view { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
    @media (max-width: 820px) { .stats-view { grid-template-columns: 1fr; } }
    .stats-card {
      background: #111827; border: 1px solid #2a2a4a; border-radius: 12px;
      padding: 1rem 1.1rem;
    }
    .stats-card h3 { margin: 0 0 .85rem; color: #fff; font-size: 1.05rem; }
    .cost-curve {
      display: grid; grid-template-columns: repeat(8, 1fr); gap: .35rem; align-items: end;
      height: 180px;
    }
    .cc-col { display: flex; flex-direction: column; align-items: center; justify-content: flex-end; gap: .25rem; height: 100%; }
    .cc-count { font-size: .75rem; color: #ffbd39; font-weight: 700; min-height: 1rem; }
    .cc-bar-wrap { width: 100%; height: 100%; display: flex; align-items: flex-end; background: rgba(40,40,80,.25); border-radius: 4px; overflow: hidden; }
    .cc-bar {
      width: 100%; min-height: 2px;
      background: linear-gradient(180deg, #ff6b7d 0%, #e94560 100%);
      border-radius: 4px 4px 0 0; transition: height .25s;
    }
    .cc-col.is-avg .cc-bar { background: linear-gradient(180deg, #e94560 0%, #9c5dff 100%); }
    .cc-label { font-size: .78rem; color: #c8c8da; font-weight: 600; }

    .dist-list { display: flex; flex-direction: column; gap: .45rem; }
    .dist-row {
      display: grid; grid-template-columns: 110px 1fr 80px;
      gap: .65rem; align-items: center; font-size: .85rem;
    }
    .dist-name { color: #c8c8da; display: inline-flex; align-items: center; gap: .35rem; }
    .dist-name .dot { width: 9px; height: 9px; border-radius: 50%; }
    .dist-bar-wrap { background: rgba(40,40,80,.35); border-radius: 4px; height: 12px; overflow: hidden; }
    .dist-bar { height: 100%; transition: width .25s; }
    .dist-num { color: #fff; font-weight: 600; text-align: right; font-variant-numeric: tabular-nums; }

    .prob-table { width: 100%; border-collapse: collapse; font-size: .85rem; }
    .prob-table th, .prob-table td { padding: .35rem .45rem; border-bottom: 1px solid #1f1f3a; }
    .prob-table th { color: #e94560; text-align: left; }
    .prob-table .num { text-align: right; }
    .prob-pill {
      display: inline-block; padding: .15rem .55rem; border-radius: 999px;
      background: linear-gradient(90deg, rgba(74,222,128,.25) var(--p), rgba(40,40,80,.35) var(--p));
      color: #fff; font-weight: 700; font-size: .78rem;
    }

    /* Modal */
    .preview-overlay {
      position: fixed; inset: 0; z-index: 1000;
      background: rgba(0,0,0,.78); display: grid; place-items: center;
      padding: 1rem; backdrop-filter: blur(3px);
    }
    .preview-box {
      position: relative; max-width: 1000px; width: 100%; max-height: 92vh; overflow: auto;
      background: #0f0f23; border: 1px solid #e94560; border-radius: 12px;
      padding: 1.5rem; color: #e0e0e0; box-shadow: 0 20px 60px rgba(0,0,0,.5);
    }
    .preview-close {
      position: absolute; top: .6rem; right: .6rem;
      width: 36px; height: 36px; border-radius: 50%;
      background: #16213e; border: 1px solid #2a3a4a; color: #c8c8da;
      cursor: pointer; font-size: 1rem; display: grid; place-items: center;
      transition: all .15s; z-index: 2;
    }
    .preview-close:hover { background: #e94560; border-color: #e94560; color: #fff; }
    .preview-layout { display: grid; gap: 1.5rem; grid-template-columns: minmax(220px, 360px) 1fr; }
    .preview-img { width: 100%; border-radius: .75rem; align-self: start; }
    .preview-info h2 { margin: 0 0 .25rem; font-size: 1.6rem; color: #fff; }
    .preview-info h3 { margin: 1rem 0 .25rem; color: #fff; font-size: 1.05rem; }
    .preview-badges { display: flex; gap: .35rem; flex-wrap: wrap; margin: .75rem 0; }
    .pv-badge { padding: .25rem .55rem; border-radius: .35rem; border: 1px solid #2a3a4a; font-size: .8rem; background: #16213e; }
    .pv-badge.color { background: #e9456020; border-color: #e9456050; }
    .preview-stats { display: flex; gap: .65rem; margin: 1rem 0; flex-wrap: wrap; }
    .preview-stats > div { display: flex; flex-direction: column; align-items: center; padding: .5rem 1rem; border: 1px solid #2a3a4a; border-radius: .5rem; min-width: 70px; background: #16213e; }
    .preview-stats span { opacity: .7; font-size: .8rem; }
    .preview-stats strong { font-size: 1.4rem; color: #fff; }
    .preview-desc { white-space: pre-wrap; font-family: inherit; line-height: 1.55; margin: 0; font-size: .92rem; }
    @media (max-width: 720px) { .preview-layout { grid-template-columns: 1fr; } .preview-box { padding: 1rem; } }

    /* Share toast */
    .share-toast {
      position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%);
      background: linear-gradient(135deg, #4ade80 0%, #22c55e 100%);
      color: #0f0f23; font-weight: 700; padding: .7rem 1.2rem;
      border-radius: 999px; box-shadow: 0 10px 28px rgba(0,0,0,.45);
      z-index: 1100; animation: fadeUp .25s ease-out;
    }
    @keyframes fadeUp {
      from { opacity: 0; transform: translate(-50%, 12px); }
      to { opacity: 1; transform: translate(-50%, 0); }
    }

    /* Exporting overlay */
    .exporting-overlay {
      position: fixed; inset: 0; z-index: 1200;
      background: rgba(0,0,0,.7); display: grid; place-items: center;
    }
    .exporting-box {
      background: #111827; border: 1px solid #e94560; border-radius: 10px;
      padding: 1.5rem 2rem; text-align: center; color: #fff;
    }
    .spinner {
      width: 36px; height: 36px; margin: 0 auto .75rem;
      border: 3px solid #2a2a4a; border-top-color: #e94560;
      border-radius: 50%; animation: spin .8s linear infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }

    /* Presentation mode */
    .container.is-presentation .back-link,
    .container.is-presentation .action-bar { display: none !important; }
    .container.is-presentation { max-width: none; padding-top: .5rem; }

    .exit-presentation-fab {
      position: fixed; top: 14px; right: 14px; z-index: 1100;
      width: 42px; height: 42px; border-radius: 50%;
      background: #111827; border: 1px solid #e94560; color: #ff6b7d;
      font-size: 1.1rem; cursor: pointer;
      box-shadow: 0 6px 20px rgba(0,0,0,.5);
      transition: all .15s;
    }
    .exit-presentation-fab:hover { background: #e94560; color: #0f0f23; }

    /* Cover star (owner) */
    .cover-star {
      position: absolute; top: 6px; left: 6px; z-index: 3;
      width: 28px; height: 28px; display: grid; place-items: center;
      padding: 0;
      background: rgba(0,0,0,.55); border: 1px solid rgba(200,155,60,.55);
      color: #c8c8da; border-radius: 50%; font-size: 1rem; line-height: 1;
      cursor: pointer; transition: all .15s; opacity: 0; pointer-events: none;
    }
    .card-stack:hover .cover-star,
    .card-stack:focus-within .cover-star,
    .cover-star.is-cover { opacity: 1; pointer-events: auto; }
    .cover-star:hover { background: #e94560; color: #0f0f23; }
    .cover-star.is-cover { background: linear-gradient(135deg, #e94560, #ff6b7d); color: #0f0f23; border-color: #ff6b7d; }
    @media (hover: none) and (pointer: coarse) {
      .cover-star { opacity: 0; pointer-events: none; }
    }
    .cover-badge {
      position: absolute; top: 6px; right: 6px; z-index: 3;
      width: 22px; height: 22px; display: grid; place-items: center;
      background: linear-gradient(135deg, #e94560, #ff6b7d);
      color: #0f0f23; border-radius: 50%; font-size: .85rem; font-weight: 700;
      box-shadow: 0 2px 8px rgba(200,155,60,.5);
    }

    /* Preview extras */
    .preview-ban {
      margin: .25rem 0 .5rem; padding: .4rem .65rem; border-radius: 6px;
      font-size: .85rem; font-weight: 600; border: 1px solid;
    }
    .preview-ban.ban-banned { background: rgba(220,53,69,.15); color: #ff8a8a; border-color: #5a2230; }
    .preview-ban.ban-limited { background: rgba(255,189,57,.12); color: #ffd070; border-color: #6b5b2a; }
    .preview-actions { display: flex; gap: .5rem; flex-wrap: wrap; margin-top: 1rem; }
    .copy-cn {
      background: none; border: none; padding: 0; color: inherit;
      font: inherit; cursor: pointer; text-decoration: underline dotted;
    }
    .copy-cn:hover { color: #e94560; }

    /* More menu */
    .more-divider { height: 1px; background: #2a3a4a; margin: .35rem 0; }

    /* Export capture (always desktop layout) */
    .deck-export-area.export-capture {
      position: fixed;
      left: -10000px;
      top: 0;
      z-index: -1;
      background: #0a1628;
      padding: 1rem;
      box-sizing: border-box;
      border-radius: 0;
    }
    .deck-export-area.export-capture.capture-horizontal {
      width: 1680px;
      display: grid;
      grid-template-columns: repeat(12, minmax(0, 1fr));
      gap: .7rem .8rem;
      align-items: start;
    }

    .deck-export-area.export-capture.capture-horizontal .rb-export-layout {
      grid-column: 1 / -1;
      display: flex;
      flex-direction: column;
      gap: .6rem;
      min-height: 100%;
    }
    .deck-export-area.export-capture.capture-horizontal .rb-export-top-line {
      height: 6px;
      border-radius: 999px;
      background: linear-gradient(90deg, #d04f45 0%, #ea6d4f 35%, #a04a7a 70%, #6d5ecf 100%);
      opacity: .9;
    }
    .deck-export-area.export-capture.capture-horizontal .rb-export-head {
      display: flex;
      justify-content: space-between;
      gap: .8rem;
      padding-bottom: .55rem;
      border-bottom: 1px solid rgba(200,214,229,.28);
    }
    .deck-export-area.export-capture.capture-horizontal .rb-export-head-main {
      display: flex;
      align-items: stretch;
      gap: .8rem;
      min-width: 0;
      flex: 1;
    }
    .deck-export-area.export-capture.capture-horizontal .rb-export-cover {
      width: 88px;
      height: 124px;
      border-radius: 9px;
      object-fit: cover;
      border: 1px solid rgba(200,214,229,.3);
      box-shadow: 0 8px 24px rgba(0,0,0,.35);
      flex-shrink: 0;
    }
    .deck-export-area.export-capture.capture-horizontal .rb-export-cover-empty {
      display: grid;
      place-items: center;
      background: linear-gradient(140deg, #253045, #101a2b);
      color: #f0d080;
      font-size: .72rem;
      letter-spacing: .08em;
      font-weight: 700;
    }
    .deck-export-area.export-capture.capture-horizontal .rb-export-copy {
      min-width: 0;
      display: flex;
      flex-direction: column;
      justify-content: center;
      gap: .2rem;
    }
    .deck-export-area.export-capture.capture-horizontal .rb-export-kicker {
      margin: 0;
      color: #c7d5e8;
      font-size: .72rem;
      letter-spacing: .18em;
      text-transform: uppercase;
      font-weight: 700;
    }
    .deck-export-area.export-capture.capture-horizontal .rb-export-title {
      margin: 0;
      font-size: 2.05rem;
      line-height: 1.08;
      font-weight: 800;
      color: #f8fbff;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .deck-export-area.export-capture.capture-horizontal .rb-export-date {
      margin: 0;
      color: #c7d5e8;
      font-size: .95rem;
      font-weight: 500;
    }
    .deck-export-area.export-capture.capture-horizontal .rb-export-brand {
      min-width: 300px;
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      justify-content: flex-end;
      gap: .45rem;
    }
    .deck-export-area.export-capture.capture-horizontal .rb-export-qr-image,
    .deck-export-area.export-capture.capture-horizontal .rb-export-qr-fallback {
      width: 108px;
      height: 108px;
      border-radius: 10px;
      border: 3px solid #ebeff4;
      box-shadow: 0 10px 30px rgba(0,0,0,.28);
      overflow: hidden;
    }
    .deck-export-area.export-capture.capture-horizontal .rb-export-qr-image {
      background: #ffffff;
      object-fit: cover;
    }
    .deck-export-area.export-capture.capture-horizontal .rb-export-qr-fallback {
      display: grid;
      place-items: center;
      background: linear-gradient(135deg, #ffffff, #d8e2ef);
      color: #1b2738;
      font-size: 1.55rem;
      font-weight: 800;
      letter-spacing: .05em;
    }
    .deck-export-area.export-capture.capture-horizontal .rb-export-brand-mark {
      color: #f6bf57;
      font-weight: 800;
      font-size: 1.65rem;
      letter-spacing: -.01em;
      text-transform: lowercase;
    }
    .deck-export-area.export-capture.capture-horizontal .rb-export-url {
      margin: 0;
      max-width: 100%;
      color: #9db3ca;
      font-size: .78rem;
      text-align: right;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .deck-export-area.export-capture.capture-horizontal .rb-export-zone-grid {
      display: grid;
      grid-template-columns: repeat(12, minmax(0, 1fr));
      gap: .55rem;
      align-items: start;
      flex: 1;
    }
    .deck-export-area.export-capture.capture-horizontal .rb-export-zone {
      padding: .45rem;
      border-radius: 10px;
      border: 1px solid rgba(200,214,229,.2);
      background: rgba(8,15,25,.45);
      min-width: 0;
    }
    .deck-export-area.export-capture.capture-horizontal .rb-export-zone-title {
      display: flex;
      align-items: center;
      gap: .4rem;
      justify-content: space-between;
      margin: 0 0 .35rem;
      color: #f8fbff;
      font-size: .95rem;
      line-height: 1;
      font-weight: 700;
    }
    .deck-export-area.export-capture.capture-horizontal .rb-export-zone-title span {
      color: #f6bf57;
      font-size: .92rem;
      font-weight: 800;
    }
    .deck-export-area.export-capture.capture-horizontal .zone-runes { grid-column: span 2; }
    .deck-export-area.export-capture.capture-horizontal .zone-battlefields { grid-column: span 4; }
    .deck-export-area.export-capture.capture-horizontal .zone-units { grid-column: span 6; }
    .deck-export-area.export-capture.capture-horizontal .zone-spells { grid-column: span 8; }
    .deck-export-area.export-capture.capture-horizontal .zone-gear { grid-column: span 4; }
    .deck-export-area.export-capture.capture-horizontal .zone-other { grid-column: span 4; }
    .deck-export-area.export-capture.capture-horizontal .zone-side-deck {
      grid-column: 1 / -1;
    }
    .deck-export-area.export-capture.capture-horizontal .zone-runes .card-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .deck-export-area.export-capture.capture-horizontal .zone-battlefields .card-grid {
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }
    .deck-export-area.export-capture.capture-horizontal .zone-units .card-grid {
      grid-template-columns: repeat(7, minmax(0, 1fr));
    }
    .deck-export-area.export-capture.capture-horizontal .zone-spells .card-grid {
      grid-template-columns: repeat(8, minmax(0, 1fr));
    }
    .deck-export-area.export-capture.capture-horizontal .zone-gear .card-grid,
    .deck-export-area.export-capture.capture-horizontal .zone-other .card-grid {
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }
    .deck-export-area.export-capture.capture-horizontal .zone-side-deck .card-grid {
      grid-template-columns: repeat(11, minmax(0, 1fr));
    }
    .deck-export-area.export-capture.capture-horizontal .rb-export-zone .card-grid {
      gap: .82rem .55rem;
    }
    .deck-export-area.export-capture.capture-horizontal .rb-export-zone .card-stack {
      max-width: none;
    }
    .deck-export-area.export-capture.capture-horizontal .rb-export-summary {
      border-top: 1px solid rgba(200,214,229,.24);
      padding-top: .5rem;
      color: #c7d5e8;
      font-size: .85rem;
      font-weight: 600;
      letter-spacing: .01em;
    }

    .deck-export-area.export-capture.capture-vertical {
      width: 1140px;
    }
    .deck-export-area.export-capture .zone-section {
      margin-bottom: .55rem;
    }
    .deck-export-area.export-capture.capture-horizontal .zone-section {
      margin: 0;
      padding: .5rem;
      border: 1px solid rgba(200,214,229,.2);
      border-radius: 10px;
      background: rgba(8,15,25,.45);
    }
    .deck-export-area.export-capture.capture-horizontal .zone-section[data-zone='champion'] {
      order: 1;
      grid-column: span 3;
    }
    .deck-export-area.export-capture.capture-horizontal .zone-section[data-zone='rune'] {
      order: 2;
      grid-column: span 4;
    }
    .deck-export-area.export-capture.capture-horizontal .zone-section[data-zone='bg'] {
      order: 3;
      grid-column: span 5;
    }
    .deck-export-area.export-capture.capture-horizontal .zone-section[data-zone='main'] {
      order: 4;
      grid-column: span 9;
    }
    .deck-export-area.export-capture.capture-horizontal .zone-section[data-zone='side'] {
      order: 5;
      grid-column: span 3;
    }
    .deck-export-area.export-capture .zone-section.side-zone {
      margin-top: 1.2rem;
      padding-top: .9rem;
      border-top: 1px solid rgba(200,214,229,.5);
    }
    .deck-export-area.export-capture.capture-horizontal .zone-section.side-zone {
      margin-top: 0;
      padding-top: 0;
      border-top: 0;
    }
    .deck-export-area.export-capture .zone-section.side-zone .zone-title {
      color: #dce8f6;
      border-bottom-color: rgba(200,214,229,.35);
    }
    .deck-export-area.export-capture .zone-title {
      color: #eaf2ff;
      margin-bottom: .45rem;
      font-size: .95rem;
    }
    .deck-export-area.export-capture .card-grid {
      --stack-top-x: 0px;
      --stack-top-y: 0px;
      --stack-s2-x: 12px;
      --stack-s2-y: 12px;
      --stack-s3-x: 24px;
      --stack-s3-y: 24px;

      gap: 1.35rem 1rem;
      align-items: start;
    }
    .deck-export-area.export-capture .card-grid[data-stack-orientation='up'] {
      --stack-top-x: 0px;
      --stack-top-y: 24px;
      --stack-s2-x: 0px;
      --stack-s2-y: 12px;
      --stack-s3-x: 0px;
      --stack-s3-y: 0px;
    }
    .deck-export-area.export-capture .card-grid[data-stack-orientation='left'] {
      --stack-top-x: 24px;
      --stack-top-y: 0px;
      --stack-s2-x: 12px;
      --stack-s2-y: 0px;
      --stack-s3-x: 0px;
      --stack-s3-y: 0px;
    }
    .deck-export-area.export-capture .card-grid[data-stack-orientation='right'] {
      --stack-top-x: 0px;
      --stack-top-y: 0px;
      --stack-s2-x: 12px;
      --stack-s2-y: 0px;
      --stack-s3-x: 24px;
      --stack-s3-y: 0px;
    }
    .deck-export-area.export-capture .card-grid[data-stack-orientation='center'] {
      --stack-top-x: 0px;
      --stack-top-y: 0px;
      --stack-s2-x: 0px;
      --stack-s2-y: 0px;
      --stack-s3-x: 0px;
      --stack-s3-y: 0px;
    }
    .deck-export-area.export-capture.capture-horizontal .card-grid {
      grid-template-columns: repeat(8, minmax(0, 1fr));
    }
    .deck-export-area.export-capture.capture-vertical .card-grid {
      grid-template-columns: repeat(5, minmax(0, 1fr));
    }
    .deck-export-area.export-capture.capture-horizontal .zone-section[data-zone='champion'] .card-grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
    .deck-export-area.export-capture.capture-horizontal .zone-section[data-zone='rune'] .card-grid,
    .deck-export-area.export-capture.capture-horizontal .zone-section[data-zone='bg'] .card-grid {
      grid-template-columns: repeat(4, minmax(0, 1fr));
    }
    .deck-export-area.export-capture.capture-horizontal .zone-section[data-zone='main'] .card-grid {
      grid-template-columns: repeat(8, minmax(0, 1fr));
    }
    .deck-export-area.export-capture.capture-horizontal .zone-section[data-zone='side'] .card-grid {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
    .deck-export-area.export-capture .card-stack {
      width: 100%;
      max-width: none;
      margin-inline: 0;
    }
    .deck-export-area.export-capture .card-stack .top,
    .deck-export-area.export-capture .card-stack .shadow {
      object-fit: contain;
      background: #0b141d;
      border: 1px solid #1f3550;
      border-radius: 10px;
    }
    .deck-export-area.export-capture .card-stack .placeholder {
      border: 1px solid #1f3550;
      border-radius: 10px;
      color: #d5e2f0;
      font-size: .72rem;
      text-align: center;
      padding: .35rem;
    }
    .deck-export-area.export-capture .card-stack .shadow {
      display: none;
    }
    .deck-export-area.export-capture .card-stack.qty-2,
    .deck-export-area.export-capture .card-stack.qty-3 {
      margin: 0;
    }
    .deck-export-area.export-capture .card-stack .qty-badge {
      font-size: .86rem;
      padding: .12rem .44rem;
    }
    .deck-export-area.export-capture .card-name {
      display: none;
    }

    /* Social bar (likes / comentarios / compartir / clonar) */
    .social-bar {
      display: flex; gap: .4rem; margin-bottom: .7rem;
    }
    .social-btn {
      display: inline-flex; align-items: center; gap: .4rem;
      padding: .42rem .85rem; background: #111827; border: 1px solid #2a3a4a;
      color: #9ba3b4; border-radius: 999px; font-size: .85rem;
      cursor: pointer; transition: all .15s;
    }
    .social-btn i { font-size: .95rem; }
    .social-btn:hover:not(:disabled) { background: #1e2d3d; color: #e0e0e0; border-color: #3a5a6a; }
    .social-btn:disabled { opacity: .5; cursor: not-allowed; }
    .social-btn.liked { color: #e94560; border-color: rgba(233,69,96,.5); background: rgba(233,69,96,.12); }
    .container.is-presentation .social-bar { display: none !important; }

    /* Hand test modal */
    .hand-box { max-width: 920px; }
    .hand-grid {
      display: grid; gap: .75rem;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      margin-bottom: 1rem;
    }
    .hand-card {
      width: 100%; aspect-ratio: 5/7; object-fit: cover;
      border-radius: 8px; border: 1px solid #2a3a4a;
      box-shadow: 0 6px 18px rgba(0,0,0,.4);
    }
    .hand-card.placeholder {
      display: grid; place-items: center; background: #16213e;
      color: #6b7a8a; font-size: .85rem; text-align: center; padding: .5rem;
    }
    .hand-actions { display: flex; gap: .5rem; justify-content: flex-end; flex-wrap: wrap; }

    @media (max-width: 880px) {
      .card-grid {
        grid-template-columns: repeat(auto-fill, minmax(118px, 1fr));
        gap: 1.25rem .75rem;
      }
      .card-stack {
        max-width: 118px;
      }
      .export-preview-actions {
        grid-template-columns: 1fr;
      }
      .export-modal {
        width: min(460px, 95vw);
      }
      .action-btn span {
        display: none;
      }
    }

    @media (max-width: 640px) {
      .zone-section {
        margin-bottom: 1.45rem;
      }
      .card-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 1.35rem .7rem;
      }
      .card-stack {
        width: 100%;
        max-width: none;
      }
      /* En móvil ocultamos sombras de apilado para que todas las cartas se perciban del mismo tamaño. */
      .card-stack .shadow {
        display: none;
      }
      .card-stack.qty-2,
      .card-stack.qty-3 {
        margin: 0;
      }

      .export-preview-modal {
        width: min(96vw, 560px);
        max-height: 90vh;
        padding: .75rem;
      }
      .export-preview-head h3 {
        font-size: 1.2rem;
      }
      .export-preview-subtitle {
        font-size: .9rem;
        margin-bottom: .45rem;
      }
      .export-preview-back {
        font-size: .9rem;
        margin-bottom: .55rem;
      }
      .export-preview-frame {
        padding: .35rem;
        max-height: 60vh;
        overflow: hidden;
      }
      .export-preview-frame img {
        width: auto;
        max-width: 100%;
        max-height: 54vh;
        margin-inline: auto;
        object-fit: contain;
      }
    }
  `],
})
export class RiftboundDeckViewComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private rb = inject(RiftboundService);
  private auth = inject(AuthService);
  private titleSvc = inject(Title);
  private metaSvc = inject(Meta);
  private cdr = inject(ChangeDetectorRef);
  private brokenImageUrlsByKey = new Map<string, Set<string>>();
  private imageFallbackNonce = signal(0);
  private exportSafeImageMode = signal(false);
  private readonly stackOrientationStorageKey = 'rb-deck-view:stack-orientation';

  @ViewChild('deckContent') deckContent?: ElementRef<HTMLElement>;

  deck = signal<RiftboundDeck | null>(null);
  loading = signal(true);
  togglingVisibility = signal(false);
  previewEntry = signal<RiftboundDeckEntry | null>(null);
  previewDetail = signal<RiftboundCard | null>(null);
  previewLoading = signal(false);

  viewMode = signal<ViewMode>('grid');
  sideOpen = signal(true);
  presentationMode = signal(false);
  showMoreMenu = signal(false);
  showStackOrientationMenu = signal(false);
  showExportOptionsModal = signal(false);
  showExportPreviewModal = signal(false);
  exportPreviewDataUrl = signal<string | null>(null);
  exportQrDataUrl = signal<string | null>(null);
  exporting = signal(false);
  captureMode = signal(false);
  shareToast = signal(false);
  toastMsg = signal('Enlace copiado');
  orientation = signal<Orientation>('vertical');
  stackOrientation = signal<StackOrientation>('down');
  settingCover = signal(false);

  // Hand test (mulligan)
  showHandModal = signal(false);
  handCards = signal<RiftboundDeckEntry[]>([]);

  /** Banlist indexada por id de carta. */
  private banlistByCardId = new Map<number, RiftboundBanlistEntry>();

  readonly zones: RiftboundZone[] = ['champion', 'main', 'side', 'rune', 'bg'];
  readonly labels = RIFTBOUND_ZONE_LABELS;

  isOwner = computed(() => {
    const u = this.auth.user();
    const d = this.deck();
    return !!u && !!d && u.username === d.owner_username;
  });

  totalCards = computed(() =>
    (this.deck()?.entries ?? []).reduce((s, e) => s + e.quantity, 0));

  validationErrors = computed(() => this.deck()?.validation?.errors ?? []);

  hex(c: RiftboundColor): string { return COLOR_HEX[c] ?? '#888'; }
  label(c: RiftboundColor): string { return COLOR_LABEL[c] ?? c; }
  typeLabel(t?: string): string { return TYPE_LABEL[t ?? ''] ?? (t ?? '—'); }

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
    const urls = [card.cdn_image_url, card.image_url, card.image_url_small, card.image]
      .map((url) => this.normalizeImageUrl(url))
      .filter(Boolean);
    const withRiotVariants = urls.flatMap((url) => [url, ...this.riotImageVariants(url)]);
    return Array.from(new Set(withRiotVariants));
  }

  private riotImageVariants(url: string | null | undefined): string[] {
    const value = this.normalizeImageUrl(url);
    if (!value) return [];
    try {
      const parsed = new URL(value, window.location.origin);
      const host = parsed.hostname.toLowerCase();
      if (!host.endsWith('.rgpub.io')) return [];
      if (!parsed.search) return [];
      const withoutQuery = `${parsed.origin}${parsed.pathname}`;
      return [withoutQuery];
    } catch {
      return [];
    }
  }

  private cloudinaryFetchVariants(url: string | null | undefined): string[] {
    const value = this.normalizeImageUrl(url);
    if (!value) return [];
    const lower = value.toLowerCase();
    if (lower.startsWith('data:') || lower.startsWith('blob:')) return [];
    if (lower.includes('res.cloudinary.com/')) return [];
    return [`https://res.cloudinary.com/daobfx9yb/image/fetch/f_auto,q_auto/${encodeURIComponent(value)}`];
  }

  private isExportSafeImageUrl(url: string): boolean {
    const value = this.normalizeImageUrl(url);
    if (!value) return false;
    if (value.startsWith('data:') || value.startsWith('blob:')) return true;
    try {
      const parsed = new URL(value, window.location.origin);
      if (parsed.origin === window.location.origin) return true;
      const host = parsed.hostname.toLowerCase();
      return host.endsWith('.imagekit.io')
        || host.endsWith('res.cloudinary.com')
        || host.endsWith('.rgpub.io')
        || host.endsWith('.r2.dev')
        || host.endsWith('.r2.cloudflarestorage.com');
    } catch {
      return false;
    }
  }

  private prioritizedImageCandidates(candidates: string[]): string[] {
    if (!this.exportSafeImageMode()) return candidates;
    const expanded = candidates.flatMap((url) => [url, ...this.cloudinaryFetchVariants(url)]);
    const safe = expanded.filter((url) => this.isExportSafeImageUrl(url));
    return Array.from(new Set(safe));
  }

  cardImageUrl(card: CardImageLike | null | undefined): string {
    this.imageFallbackNonce();
    const candidates = this.prioritizedImageCandidates(this.candidateImageUrls(card));
    if (!candidates.length) return '';

    const key = this.cardImageKey(card);
    const broken = this.brokenImageUrlsByKey.get(key);
    for (const url of candidates) {
      if (!broken?.has(url)) return url;
    }

    // Si todas las URLs candidatas ya fallaron, devolvemos vacío para renderizar
    // el placeholder y evitar celdas negras/vacías en la exportación.
    return '';
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

  ngOnInit() {
    // Restaurar viewMode
    try {
      const saved = localStorage.getItem('rb-deck-view:mode') as ViewMode | null;
      if (saved === 'grid' || saved === 'list' || saved === 'stats') this.viewMode.set(saved);
      const so = localStorage.getItem('rb-deck-view:orientation') as Orientation | null;
      if (so === 'vertical' || so === 'horizontal') this.orientation.set(so);
      const stack = localStorage.getItem(this.stackOrientationStorageKey) as StackOrientation | null;
      if (this.isValidStackOrientation(stack)) this.stackOrientation.set(stack);
    } catch { /* noop */ }

    const id = +this.route.snapshot.paramMap.get('id')!;
    if (!id) { this.loading.set(false); return; }
    this.rb.getDeck(id).subscribe({
      next: (d) => {
        this.deck.set(d);
        this.loading.set(false);
        // SEO
        this.titleSvc.setTitle(`${d.name} — Riftbound · ShadowForge`);
        this.metaSvc.updateTag({
          name: 'description',
          content: `Mazo Riftbound «${d.name}» por ${d.owner_username} · ${this.totalCards()} cartas`,
        });
        this.loadBanlist();
        // Deep-link ?card=ID
        const cardParam = this.route.snapshot.queryParamMap.get('card');
        if (cardParam) {
          const cid = Number(cardParam);
          const target = d.entries.find(e => (e.card_data?.id ?? e.card) === cid);
          if (target) this.openPreview(target, /*skipNav*/ true);
        }
      },
      error: () => this.loading.set(false),
    });
  }

  private loadBanlist() {
    this.rb.listBanlist('standard').subscribe({
      next: (resp) => {
        this.banlistByCardId.clear();
        for (const e of (resp.results ?? [])) {
          if (e.card) this.banlistByCardId.set(e.card, e);
        }
        this.cdr.detectChanges();
      },
      error: () => { /* sin banlist, sin badges */ },
    });
  }

  entriesByZone(z: RiftboundZone): RiftboundDeckEntry[] {
    const list = this.deck()?.entries.filter(e => e.zone === z) ?? [];
    // Orden: tipo (unidad → hechizo → equipo → resto) → cantidad desc (3,2,1) → nombre.
    return [...list].sort((a, b) => {
      const ra = typeRank(a.card_data?.card_type);
      const rb = typeRank(b.card_data?.card_type);
      if (ra !== rb) return ra - rb;
      if (b.quantity !== a.quantity) return b.quantity - a.quantity;
      return (a.card_data?.name ?? '').localeCompare(b.card_data?.name ?? '');
    });
  }

  countZone(z: RiftboundZone): number {
    return this.entriesByZone(z).reduce((s, e) => s + e.quantity, 0);
  }

  exportCoverCardData(): CardImageLike | null {
    const d = this.deck();
    if (!d) return null;
    if (d.cover_card_data) return d.cover_card_data;

    const championCard = this.entriesByZone('champion')[0]?.card_data;
    if (championCard) return championCard;

    return this.entriesByZone('main')[0]?.card_data ?? null;
  }

  exportMainEntriesByType(type: 'unit' | 'spell' | 'gear' | 'other'): RiftboundDeckEntry[] {
    const main = this.entriesByZone('main');
    const known = new Set(['unit', 'spell', 'gear']);

    if (type === 'other') {
      return main.filter((entry) => !known.has((entry.card_data?.card_type ?? '').toLowerCase()));
    }

    return main.filter((entry) => (entry.card_data?.card_type ?? '').toLowerCase() === type);
  }

  sumEntryQuantity(entries: RiftboundDeckEntry[]): number {
    return entries.reduce((sum, entry) => sum + entry.quantity, 0);
  }

  formatExportDate(value: string): string {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    }).format(date);
  }

  exportDeckPathLabel(): string {
    try {
      const url = new URL(window.location.href);
      const host = url.hostname.replace(/^www\./i, '');
      return `${host}${url.pathname}`;
    } catch {
      return 'shadow-forge-deck.vercel.app';
    }
  }

  private exportDeckShareUrl(): string {
    const d = this.deck();
    const origin = window.location.origin;
    if (d?.id) return `${origin}/riftbound/decks/${d.id}`;
    try {
      const url = new URL(window.location.href);
      url.search = '';
      url.hash = '';
      return url.toString();
    } catch {
      return window.location.href;
    }
  }

  private async ensureExportQrDataUrl(): Promise<void> {
    const shareUrl = this.exportDeckShareUrl();
    if (!shareUrl) {
      this.exportQrDataUrl.set(null);
      return;
    }

    try {
      const qrModule = await import('qrcode');
      const anyModule = qrModule as any;
      const toDataURL = anyModule?.toDataURL ?? anyModule?.default?.toDataURL;
      if (typeof toDataURL !== 'function') {
        this.exportQrDataUrl.set(null);
        return;
      }

      const qrDataUrl = await toDataURL(shareUrl, {
        errorCorrectionLevel: 'M',
        margin: 1,
        scale: 5,
        color: {
          dark: '#111111',
          light: '#ffffff',
        },
      });
      this.exportQrDataUrl.set(qrDataUrl);
    } catch (error) {
      console.error('No se pudo generar QR para exportación:', error);
      this.exportQrDataUrl.set(null);
    }
  }

  exportSummaryLine(): string {
    const summary = [
      `${this.countZone('champion')} Legend`,
      `${this.countZone('rune')} Runes`,
      `${this.countZone('bg')} Battlefields`,
      `${this.sumEntryQuantity(this.exportMainEntriesByType('unit'))} Units`,
      `${this.sumEntryQuantity(this.exportMainEntriesByType('spell'))} Spells`,
      `${this.sumEntryQuantity(this.exportMainEntriesByType('gear'))} Gear`,
    ];
    const sideCount = this.countZone('side');
    if (sideCount > 0) summary.push(`${sideCount} Side Deck`);
    return summary.join(' · ');
  }

  formatDate(s: string): string {
    if (!s) return '';
    const d = new Date(s);
    const diff = (Date.now() - +d) / 1000;
    if (diff < 60) return 'hace un momento';
    if (diff < 3600) return `hace ${Math.floor(diff/60)} min`;
    if (diff < 86400) return `hace ${Math.floor(diff/3600)} h`;
    if (diff < 86400 * 7) return `hace ${Math.floor(diff/86400)} d`;
    return d.toLocaleDateString('es-CL');
  }

  // ── View mode persistido ──
  setViewMode(m: ViewMode) {
    this.viewMode.set(m);
    try { localStorage.setItem('rb-deck-view:mode', m); } catch { /* noop */ }
  }

  setOrientation(o: Orientation) {
    this.orientation.set(o);
    try { localStorage.setItem('rb-deck-view:orientation', o); } catch { /* noop */ }
  }

  toggleStackOrientationMenu(e?: Event) {
    e?.stopPropagation();
    this.showMoreMenu.set(false);
    this.showExportOptionsModal.set(false);
    this.showStackOrientationMenu.set(!this.showStackOrientationMenu());
  }

  setStackOrientation(o: StackOrientation) {
    if (!this.isValidStackOrientation(o)) return;
    this.stackOrientation.set(o);
    this.showStackOrientationMenu.set(false);
    try { localStorage.setItem(this.stackOrientationStorageKey, o); } catch { /* noop */ }
  }

  openExportOptionsModal(e?: Event) {
    e?.stopPropagation();
    this.showMoreMenu.set(false);
    this.showStackOrientationMenu.set(false);
    this.showExportPreviewModal.set(false);
    this.showExportOptionsModal.set(true);
  }

  closeExportOptionsModal() {
    this.showExportOptionsModal.set(false);
  }

  backToExportOptions() {
    this.showExportPreviewModal.set(false);
    this.showExportOptionsModal.set(true);
  }

  closeExportPreview() {
    this.showExportPreviewModal.set(false);
  }

  // ── Cover card (owner) ──
  toggleCover(ev: Event, e: RiftboundDeckEntry) {
    ev.preventDefault();
    ev.stopPropagation();
    const cardId = e.card_data?.id;
    if (!cardId) return;
    this.toggleCoverByCardId(cardId);
  }

  toggleCoverByCardId(cardId: number) {
    const d = this.deck();
    if (!d || !this.isOwner() || !cardId || this.settingCover()) return;
    const isCurrent = d.cover_card === cardId;
    const newCover = isCurrent ? null : cardId;
    this.settingCover.set(true);
    this.rb.patchDeck(d.id, { cover_card: newCover } as Partial<RiftboundDeck>).subscribe({
      next: (updated) => {
        this.deck.set(updated);
        this.settingCover.set(false);
        this.fireToast(isCurrent ? 'Portada quitada' : 'Portada actualizada');
      },
      error: () => {
        this.settingCover.set(false);
        this.fireToast('No se pudo actualizar la portada');
      },
    });
  }

  onCardStackSpace(ev: Event, e: RiftboundDeckEntry) {
    ev.preventDefault();
    this.openPreview(e);
  }

  // ── Helpers preview ──
  getBanStatusByCardId(cid: number): RiftboundBanlistEntry | null {
    return this.banlistByCardId.get(cid) ?? null;
  }

  deepLinkUrl(cardId: number): string {
    const url = new URL(window.location.href);
    url.searchParams.set('card', String(cardId));
    return url.toString();
  }

  copyText(text: string, msg = 'Copiado') {
    try {
      navigator.clipboard.writeText(text).then(() => this.fireToast(msg));
    } catch { /* noop */ }
  }

  // ── Banlist ──
  getBanStatus(e: RiftboundDeckEntry): RiftboundBanlistEntry | null {
    const cid = e.card_data?.id ?? e.card;
    return this.banlistByCardId.get(cid) ?? null;
  }
  banShort(b: RiftboundBanlistEntry): string {
    if (b.status === 'banned') return 'BAN';
    return `×${b.max_copies}`;
  }
  banTooltip(b: RiftboundBanlistEntry): string {
    if (b.status === 'banned') return 'Baneada';
    return `Limitada a ${b.max_copies} copia(s)`;
  }

  // ── Acciones owner ──
  editDeck() {
    const d = this.deck();
    if (d) this.router.navigate(['/riftbound/builder', d.id]);
  }

  toggleVisibility() {
    const d = this.deck();
    if (!d || this.togglingVisibility()) return;
    this.togglingVisibility.set(true);
    this.rb.patchDeck(d.id, { is_public: !d.is_public }).subscribe({
      next: (updated) => { this.deck.set(updated); this.togglingVisibility.set(false); },
      error: () => this.togglingVisibility.set(false),
    });
  }

  deleteDeck() {
    const d = this.deck();
    if (!d) return;
    if (!confirm('¿Eliminar este mazo? Esta acción no se puede deshacer.')) return;
    this.rb.deleteDeck(d.id).subscribe({
      next: () => this.router.navigate(['/riftbound/decks']),
    });
  }

  // ── Compartir ──
  shareDeck() {
    const url = window.location.href;
    const d = this.deck();
    const title = d ? `${d.name} · Riftbound · ShadowForge` : 'Riftbound · ShadowForge';
    const nav = navigator as Navigator & { share?: (data: ShareData) => Promise<void> };
    if (nav.share) {
      nav.share({ title, text: title, url }).catch(() => { /* user cancel */ });
      return;
    }
    navigator.clipboard.writeText(url).then(() => this.fireToast('Enlace copiado'));
  }

  private fireToast(msg: string, ms = 2000) {
    this.toastMsg.set(msg);
    this.shareToast.set(true);
    setTimeout(() => this.shareToast.set(false), ms);
  }

  // ── More menu ──
  toggleMoreMenu(e?: Event) {
    e?.stopPropagation();
    this.showStackOrientationMenu.set(false);
    this.showExportOptionsModal.set(false);
    this.showMoreMenu.set(!this.showMoreMenu());
  }

  // ── Probar mano (mulligan) ──
  /** Tamaño de mano para Riftbound (mano de apertura). */
  readonly handSize = 5;
  openHandTest() {
    this.drawHand();
    this.showHandModal.set(true);
  }
  drawHand() {
    // Pool: cartas del main deck (no runas, no champion, no battlefield, no side)
    const pool: RiftboundDeckEntry[] = [];
    for (const e of this.entriesByZone('main')) {
      for (let i = 0; i < e.quantity; i++) pool.push(e);
    }
    // Shuffle (Fisher-Yates)
    for (let i = pool.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [pool[i], pool[j]] = [pool[j], pool[i]];
    }
    this.handCards.set(pool.slice(0, this.handSize));
  }
  closeHandModal() {
    this.showHandModal.set(false);
    this.handCards.set([]);
  }

  // ── Copiar JSON al portapapeles ──
  copyDeckJson() {
    const d = this.deck();
    if (!d) return;
    const payload = {
      version: 1,
      app: 'shadowforge-riftbound',
      name: d.name,
      entries: d.entries.map(e => ({
        card_number: e.card_data?.card_number,
        name: e.card_data?.name,
        zone: e.zone,
        quantity: e.quantity,
      })),
    };
    navigator.clipboard.writeText(JSON.stringify(payload, null, 2))
      .then(() => this.fireToast('Mazo copiado (JSON)'));
  }

  // ── Exportaciones ──
  exportText() {
    const d = this.deck();
    if (!d) return;
    let txt = `// ${d.name}\n// Riftbound\n\n`;
    for (const z of this.zones) {
      const entries = this.entriesByZone(z);
      if (!entries.length) continue;
      txt += `// ${this.labels[z]} (${this.countZone(z)})\n`;
      for (const e of entries) {
        txt += `${e.quantity}x ${e.card_data?.name ?? e.card_data?.card_number ?? ''}\n`;
      }
      txt += '\n';
    }
    navigator.clipboard.writeText(txt.trim()).then(() => this.fireToast('Texto copiado'));
  }

  exportJson() {
    const d = this.deck();
    if (!d) return;
    const payload = {
      version: 1,
      app: 'shadowforge-riftbound',
      name: d.name,
      description: d.description,
      cover_card: d.cover_card_data?.card_number ?? null,
      primary_colors: d.primary_colors,
      entries: d.entries.map(e => ({
        card_number: e.card_data?.card_number,
        name: e.card_data?.name,
        zone: e.zone,
        quantity: e.quantity,
      })),
      exported_at: new Date().toISOString(),
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const safe = d.name.replace(/[^\w\-]+/g, '_').slice(0, 60) || 'mazo';
    a.download = `${safe}.riftbound.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  async exportImage() {
    const canvas = await this.renderExportCanvas();
    if (!canvas) return;
    const link = document.createElement('a');
    link.download = `${this.deck()?.name || 'mazo'}.png`;
    link.href = canvas.toDataURL('image/png');
    link.click();
  }

  async copyImageToClipboard() {
    if (this.exporting()) return;
    const navAny = navigator as Navigator & { clipboard?: { write?: (items: ClipboardItem[]) => Promise<void> } };
    if (!navAny.clipboard?.write || typeof (window as Window & typeof globalThis & { ClipboardItem?: typeof ClipboardItem }).ClipboardItem === 'undefined') {
      return this.exportImage();
    }

    const canvas = await this.renderExportCanvas();
    if (!canvas) return;
    try {
      const blob: Blob | null = await new Promise(res => canvas.toBlob(b => res(b), 'image/png'));
      if (blob) {
        await navAny.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
        this.fireToast('Imagen copiada');
      }
    } catch (e) {
      console.error('Error copiando imagen:', e);
    }
  }

  async generateExportPreview() {
    const canvas = await this.renderExportCanvas();
    if (!canvas) return;
    this.exportPreviewDataUrl.set(canvas.toDataURL('image/png'));
    this.showExportOptionsModal.set(false);
    this.showExportPreviewModal.set(true);
    this.cdr.detectChanges();
  }

  downloadExportPreview() {
    const dataUrl = this.exportPreviewDataUrl();
    if (!dataUrl) return;
    const link = document.createElement('a');
    link.download = `${this.deck()?.name || 'mazo'}.png`;
    link.href = dataUrl;
    link.click();
  }

  async copyExportPreviewToClipboard() {
    const dataUrl = this.exportPreviewDataUrl();
    if (!dataUrl) return;
    if (!('clipboard' in navigator) || !(navigator.clipboard as any).write) {
      this.downloadExportPreview();
      return;
    }
    try {
      const response = await fetch(dataUrl);
      const blob = await response.blob();
      await (navigator.clipboard as any).write([
        new (window as any).ClipboardItem({ 'image/png': blob }),
      ]);
      this.fireToast('Imagen copiada');
    } catch (e) {
      console.error('Error copiando preview al portapapeles:', e);
    }
  }

  private async renderExportCanvas(): Promise<HTMLCanvasElement | null> {
    const el = this.deckContent?.nativeElement;
    if (!el || this.exporting()) return null;

    const previousViewMode = this.viewMode();
    const previousSideOpen = this.sideOpen();

    this.exporting.set(true);
    this.exportSafeImageMode.set(true);
    this.captureMode.set(true);
    this.sideOpen.set(true);
    if (previousViewMode !== 'grid') this.viewMode.set('grid');

    try {
      if (this.orientation() === 'horizontal') {
        await this.ensureExportQrDataUrl();
      } else {
        this.exportQrDataUrl.set(null);
      }
      this.cdr.detectChanges();
      await this.nextRenderTick();
      await this.waitForImages(el);
      await this.nextRenderTick();

      const targetWidth = this.orientation() === 'horizontal' ? 1680 : 1140;
      const targetHeight = this.orientation() === 'horizontal' ? 945 : 1520;
      const html2canvas = (await import('html2canvas')).default;
      const sourceCanvas = await html2canvas(el, {
        backgroundColor: '#0a1628',
        useCORS: true,
        allowTaint: false,
        scale: 2,
        width: targetWidth,
        height: el.scrollHeight,
        windowWidth: targetWidth,
        windowHeight: el.scrollHeight,
      });

      const outputCanvas = document.createElement('canvas');
      outputCanvas.width = targetWidth * 2;
      outputCanvas.height = targetHeight * 2;
      const ctx = outputCanvas.getContext('2d');
      if (!ctx) return sourceCanvas;

      ctx.fillStyle = '#0a1628';
      ctx.fillRect(0, 0, outputCanvas.width, outputCanvas.height);
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'high';

      const fitScale = Math.min(
        outputCanvas.width / sourceCanvas.width,
        outputCanvas.height / sourceCanvas.height,
      );
      const drawWidth = Math.round(sourceCanvas.width * fitScale);
      const drawHeight = Math.round(sourceCanvas.height * fitScale);
      const offsetX = Math.floor((outputCanvas.width - drawWidth) / 2);
      const offsetY = Math.floor((outputCanvas.height - drawHeight) / 2);
      ctx.drawImage(sourceCanvas, offsetX, offsetY, drawWidth, drawHeight);

      return outputCanvas;
    } catch (e) {
      console.error('Error generando imagen exportable:', e);
      return null;
    } finally {
      this.captureMode.set(false);
      this.sideOpen.set(previousSideOpen);
      if (previousViewMode !== this.viewMode()) this.viewMode.set(previousViewMode);
      this.exportQrDataUrl.set(null);
      this.exportSafeImageMode.set(false);
      this.exporting.set(false);
      this.cdr.detectChanges();
    }
  }

  private nextRenderTick(): Promise<void> {
    return new Promise<void>((resolve) => requestAnimationFrame(() => resolve()));
  }

  private waitForImages(el: HTMLElement): Promise<void[]> {
    const imgs = Array.from(el.querySelectorAll('img')) as HTMLImageElement[];
    return Promise.all(imgs.map(img => {
      if (img.complete) return Promise.resolve();
      img.loading = 'eager';
      return new Promise<void>(resolve => {
        img.addEventListener('load', () => resolve(), { once: true });
        img.addEventListener('error', () => resolve(), { once: true });
      });
    }));
  }

  // ── Presentación ──
  togglePresentation() {
    this.presentationMode.set(!this.presentationMode());
    document.body.classList.toggle('riftbound-deck-presentation', this.presentationMode());
  }

  @HostListener('document:keydown', ['$event'])
  onKeydown(ev: KeyboardEvent) {
    if (ev.key === 'Escape') {
      if (this.previewEntry()) { this.closePreview(); return; }
      if (this.showExportPreviewModal()) { this.closeExportPreview(); return; }
      if (this.showHandModal()) { this.closeHandModal(); return; }
      if (this.showStackOrientationMenu()) { this.showStackOrientationMenu.set(false); return; }
      if (this.showExportOptionsModal()) { this.showExportOptionsModal.set(false); return; }
      if (this.showMoreMenu()) { this.showMoreMenu.set(false); return; }
      if (this.presentationMode()) { this.togglePresentation(); return; }
    }
    if ((ev.key === 'f' || ev.key === 'F') && !this.previewEntry() && !this.isTyping(ev.target)) {
      this.togglePresentation();
    }
  }

  @HostListener('document:click')
  onDocClick() {
    if (this.showMoreMenu()) this.showMoreMenu.set(false);
    if (this.showStackOrientationMenu()) this.showStackOrientationMenu.set(false);
  }

  private isValidStackOrientation(value: unknown): value is StackOrientation {
    return value === 'down' || value === 'up' || value === 'left' || value === 'right' || value === 'center';
  }

  private isTyping(t: EventTarget | null): boolean {
    if (!t) return false;
    const el = t as HTMLElement;
    const tag = (el.tagName || '').toLowerCase();
    return tag === 'input' || tag === 'textarea' || el.isContentEditable;
  }

  // ── Preview (con deep-link) ──
  openPreview(e: RiftboundDeckEntry, skipNav = false) {
    this.previewEntry.set(e);
    this.previewDetail.set(null);
    if (!skipNav) {
      const cid = e.card_data?.id ?? e.card;
      this.router.navigate([], {
        relativeTo: this.route,
        queryParams: { card: cid },
        queryParamsHandling: 'merge',
        replaceUrl: true,
      });
    }
    const cn = e.card_data?.card_number;
    if (!cn) return;
    this.previewLoading.set(true);
    this.rb.getCard(cn).subscribe({
      next: (c) => { this.previewDetail.set(c); this.previewLoading.set(false); },
      error: () => this.previewLoading.set(false),
    });
  }

  closePreview() {
    this.previewEntry.set(null);
    this.previewDetail.set(null);
    this.previewLoading.set(false);
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { card: null },
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });
  }

  // ── Stats ──
  /** Buckets 0..6, 7+ de energía sobre el mazo principal (excluye runas/legend/BF). */
  costCurve = computed(() => {
    const buckets = [0, 0, 0, 0, 0, 0, 0, 0];
    for (const e of this.entriesByZone('main')) {
      const en = e.card_data?.energy;
      if (en == null || !Number.isFinite(en)) continue;
      const idx = en >= 7 ? 7 : Math.max(0, Math.min(7, Math.floor(en)));
      buckets[idx] += e.quantity;
    }
    const max = Math.max(1, ...buckets);
    return buckets.map((count, i) => ({
      label: i === 7 ? '7+' : String(i),
      count,
      pct: Math.round((count / max) * 100),
    }));
  });

  hasAnyCost = computed(() => this.costCurve().some(b => b.count > 0));

  avgCost = computed(() => {
    let sum = 0, n = 0;
    for (const e of this.entriesByZone('main')) {
      const en = e.card_data?.energy;
      if (en == null || !Number.isFinite(en)) continue;
      sum += en * e.quantity;
      n += e.quantity;
    }
    return n === 0 ? 0 : Math.round((sum / n) * 10) / 10;
  });

  avgCostBucket = computed(() => {
    const a = this.avgCost();
    if (!Number.isFinite(a) || a <= 0) return '';
    const idx = a >= 7 ? 7 : Math.max(0, Math.min(7, Math.round(a)));
    return idx === 7 ? '7+' : String(idx);
  });

  /** Distribución por tipo (todas las zonas) */
  typeDistribution = computed(() => {
    const map = new Map<string, number>();
    for (const e of (this.deck()?.entries ?? [])) {
      const t = e.card_data?.card_type ?? 'other';
      map.set(t, (map.get(t) ?? 0) + e.quantity);
    }
    const total = [...map.values()].reduce((s, x) => s + x, 0);
    if (total === 0) return [];
    return [...map.entries()]
      .sort((a, b) => b[1] - a[1])
      .map(([type, count]) => ({
        type,
        label: TYPE_LABEL[type] ?? type,
        count,
        pct: Math.round((count / total) * 100),
        color: TYPE_COLOR[type] ?? '#888',
      }));
  });

  /** Distribución por color de cartas de main + side. */
  colorDistribution = computed(() => {
    const counts: Partial<Record<RiftboundColor, number>> = {};
    let total = 0;
    for (const e of (this.deck()?.entries ?? [])) {
      if (e.zone !== 'main' && e.zone !== 'side') continue;
      for (const c of (e.card_data?.colors ?? [])) {
        counts[c] = (counts[c] ?? 0) + e.quantity;
        total += e.quantity;
      }
    }
    if (total === 0) return [];
    return (Object.keys(counts) as RiftboundColor[])
      .sort((a, b) => (counts[b] ?? 0) - (counts[a] ?? 0))
      .map(c => ({
        code: c,
        label: COLOR_LABEL[c],
        hex: COLOR_HEX[c],
        count: counts[c] ?? 0,
        pct: Math.round(((counts[c] ?? 0) / total) * 100),
      }));
  });

  /** Probabilidad hipergeométrica de robar ≥1 copia en mano inicial (4) del main. */
  drawProbabilities = computed(() => {
    const main = this.entriesByZone('main');
    const N = main.reduce((s, e) => s + e.quantity, 0);
    const n = Math.min(4, N);
    if (N === 0 || n === 0) return [];
    return main.map(e => {
      const K = e.quantity;
      let p0 = 1;
      for (let i = 0; i < n; i++) p0 *= (N - K - i) / (N - i);
      return {
        name: e.card_data?.name ?? e.card_data?.card_number ?? '?',
        qty: K,
        pct: Math.round((1 - Math.max(0, p0)) * 100),
      };
    }).sort((a, b) => b.pct - a.pct);
  });
}
