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

type ViewMode = 'grid' | 'list' | 'stats';
type Orientation = 'vertical' | 'horizontal';

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

@Component({
  selector: 'app-riftbound-deck-view',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  template: `
    @if (loading()) {
      <p class="loading">Cargando mazo…</p>
    } @else if (deck(); as d) {
      <div class="container" [class.is-presentation]="presentationMode()">
        <a routerLink="/riftbound/decks" class="back-link">← Volver a mazos</a>

        <!-- Hero -->
        <div class="deck-hero" [class.with-cover]="!!d.cover_card_data?.image">
          @if (d.cover_card_data?.image; as img) {
            <div class="hero-bg" [style.background-image]="'url(' + img + ')'"></div>
          }
          <div class="hero-overlay"></div>
          <div class="hero-content">
            @if (d.cover_card_data?.image; as img) {
              <img class="hero-cover" [src]="img" [alt]="d.cover_card_data?.name || ''" />
            } @else {
              <div class="hero-cover hero-cover-empty">⚔️</div>
            }
            <div class="hero-info">
              <h1 class="page-title">{{ d.name }}</h1>
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

        <!-- Action bar -->
        <div class="action-bar">
          <div class="seg-control" role="tablist" aria-label="Modo de visualización">
            <button type="button" class="seg-btn" [class.active]="viewMode() === 'grid'"
                    (click)="setViewMode('grid')" role="tab">🃏 Cartas</button>
            <button type="button" class="seg-btn" [class.active]="viewMode() === 'list'"
                    (click)="setViewMode('list')" role="tab">📋 Lista</button>
            <button type="button" class="seg-btn" [class.active]="viewMode() === 'stats'"
                    (click)="setViewMode('stats')" role="tab">📊 Stats</button>
          </div>

          <div class="action-spacer"></div>

          <button class="action-btn" (click)="shareDeck()" title="Copiar enlace">📤 Compartir</button>
          <button class="action-btn" (click)="togglePresentation()" title="Presentación (F)">
            {{ presentationMode() ? '✕ Salir' : '🔍 Presentación' }}
          </button>

          <div class="more-menu-wrap">
            <button class="action-btn" (click)="toggleMoreMenu($event)" aria-haspopup="menu"
                    [attr.aria-expanded]="showMoreMenu()">⋯ Más</button>
            @if (showMoreMenu()) {
              <div class="more-menu" role="menu" (click)="$event.stopPropagation()">
                <button role="menuitem" (click)="exportText(); showMoreMenu.set(false)">📝 Copiar texto</button>
                <button role="menuitem" (click)="exportJson(); showMoreMenu.set(false)">💾 Exportar JSON</button>
                <button role="menuitem" (click)="exportImage(); showMoreMenu.set(false)">🖼 Descargar imagen</button>
                <button role="menuitem" (click)="copyImageToClipboard(); showMoreMenu.set(false)">📋 Copiar imagen</button>
                <div class="more-divider"></div>
                <label class="more-select" (click)="$event.stopPropagation()">
                  <span>Orientación:</span>
                  <select [ngModel]="orientation()" (ngModelChange)="setOrientation($event)">
                    <option value="vertical">Vertical</option>
                    <option value="horizontal">Horizontal</option>
                  </select>
                </label>
              </div>
            }
          </div>

          @if (isOwner()) {
            <button class="action-btn" (click)="toggleVisibility()" [disabled]="togglingVisibility()">
              {{ d.is_public ? '🔓 Privado' : '🌐 Público' }}
            </button>
            <button class="action-btn accent" (click)="editDeck()">✏️ Editar</button>
            <button class="action-btn danger" (click)="deleteDeck()">🗑 Eliminar</button>
          }
        </div>

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
        <div #deckContent class="deck-export-area" [class.export-horizontal]="orientation() === 'horizontal'" [attr.data-orientation]="orientation()">

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
                                    @if (e.card_data?.image) {
                                      <img class="entry-thumb" [src]="e.card_data?.image" [alt]="e.card_data?.name || ''" />
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
              <!-- Grid (default) -->
              @for (z of zones; track z) {
                @let isSide = z === 'side';
                @let entries = entriesByZone(z);
                @if (entries.length) {
                  <section class="zone-section" [class.collapsed]="isSide && !sideOpen()">
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
                      <div class="card-grid">
                        @for (e of entries; track e.id || e.card) {
                          @let bs = getBanStatus(e);
                          <button type="button"
                                  class="card-stack"
                                  [class.qty-2]="e.quantity === 2"
                                  [class.qty-3]="e.quantity >= 3"
                                  [class.banned]="bs?.status === 'banned'"
                                  (click)="openPreview(e)"
                                  [title]="e.card_data?.name || ''">
                            @if (e.quantity >= 3 && e.card_data?.image) {
                              <img class="shadow s3" [src]="e.card_data?.image" aria-hidden="true" />
                            }
                            @if (e.quantity >= 2 && e.card_data?.image) {
                              <img class="shadow s2" [src]="e.card_data?.image" aria-hidden="true" />
                            }
                            @if (e.card_data?.image) {
                              <img class="top" [src]="e.card_data?.image" [alt]="e.card_data?.name || ''" />
                            } @else {
                              <div class="top placeholder">{{ e.card_data?.card_number }}</div>
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
                              <span class="cover-star"
                                    [class.is-cover]="d.cover_card === e.card_data?.id"
                                    role="button"
                                    tabindex="0"
                                    (click)="toggleCover($event, e)"
                                    (keydown.enter)="toggleCover($event, e)"
                                    [title]="d.cover_card === e.card_data?.id ? 'Portada actual (clic para quitar)' : 'Fijar como portada del mazo'">
                                {{ d.cover_card === e.card_data?.id ? '★' : '☆' }}
                              </span>
                            }
                            @if (d.cover_card === e.card_data?.id) {
                              <span class="cover-badge" title="Portada del mazo">★</span>
                            }
                            <span class="card-name">{{ e.card_data?.name }}</span>
                          </button>
                        }
                      </div>
                    }
                  </section>
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
                @if (c.image) { <img class="preview-img" [src]="c.image" [alt]="c.name" /> }
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
                      @else { ⚠️ Limitada a {{ pbs.max_copies ?? 1 }} copia(s) }
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
                  </div>
                </div>
              </div>
            } @else {
              @if (pe.card_data?.image) {
                <img class="preview-img" [src]="pe.card_data?.image" [alt]="pe.card_data?.name || ''" />
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
    .page-title {
      margin: 0 0 .65rem; font-size: 1.9rem; line-height: 1.15;
      color: #fff; text-shadow: 0 2px 8px rgba(0,0,0,.6);
      font-weight: 700; word-break: break-word;
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
      .page-title { font-size: 1.5rem; }
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
      display: grid; gap: 1.5rem 1.1rem;
      grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    }
    .card-stack {
      position: relative; aspect-ratio: 63/88; padding: 0;
      background: transparent; border: none; cursor: pointer;
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
    .shadow.s2 { transform: translate(6px, 6px); filter: brightness(.6); z-index: 0; }
    .shadow.s3 { transform: translate(12px, 12px); filter: brightness(.4); z-index: -1; }
    .card-stack .top { z-index: 1; }
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
    .card-stack.qty-2, .card-stack.qty-3 { margin-right: 14px; margin-bottom: 14px; }

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
      background: rgba(0,0,0,.55); border: 1px solid rgba(200,155,60,.55);
      color: #c8c8da; border-radius: 50%; font-size: 1rem; line-height: 1;
      cursor: pointer; transition: all .15s; opacity: 0;
    }
    .card-stack:hover .cover-star,
    .cover-star.is-cover { opacity: 1; }
    .cover-star:hover { background: #e94560; color: #0f0f23; }
    .cover-star.is-cover { background: linear-gradient(135deg, #e94560, #ff6b7d); color: #0f0f23; border-color: #ff6b7d; }
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

    /* More menu select */
    .more-divider { height: 1px; background: #2a3a4a; margin: .35rem 0; }
    .more-select {
      display: flex; align-items: center; justify-content: space-between;
      gap: .5rem; padding: .45rem .75rem; color: #c8c8da; font-size: .88rem;
    }
    .more-select select {
      background: #16213e; color: #fff; border: 1px solid #2a3a4a;
      border-radius: 6px; padding: .25rem .45rem; font-family: inherit;
    }

    /* Horizontal export orientation: cards in tighter rows */
    #deckContent.export-horizontal .card-grid {
      grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
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
  exporting = signal(false);
  shareToast = signal(false);
  toastMsg = signal('Enlace copiado');
  orientation = signal<Orientation>('vertical');
  settingCover = signal(false);

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

  ngOnInit() {
    // Restaurar viewMode
    try {
      const saved = localStorage.getItem('rb-deck-view:mode') as ViewMode | null;
      if (saved === 'grid' || saved === 'list' || saved === 'stats') this.viewMode.set(saved);
      const so = localStorage.getItem('rb-deck-view:orientation') as Orientation | null;
      if (so === 'vertical' || so === 'horizontal') this.orientation.set(so);
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
    return this.deck()?.entries.filter(e => e.zone === z) ?? [];
  }

  countZone(z: RiftboundZone): number {
    return this.entriesByZone(z).reduce((s, e) => s + e.quantity, 0);
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

  // ── Cover card (owner) ──
  toggleCover(ev: Event, e: RiftboundDeckEntry) {
    ev.preventDefault();
    ev.stopPropagation();
    const d = this.deck();
    const cardId = e.card_data?.id;
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
    return `×${b.max_copies ?? 1}`;
  }
  banTooltip(b: RiftboundBanlistEntry): string {
    if (b.status === 'banned') return 'Baneada';
    return `Limitada a ${b.max_copies ?? 1} copia(s)`;
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
    this.showMoreMenu.set(!this.showMoreMenu());
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
    const el = this.deckContent?.nativeElement;
    if (!el || this.exporting()) return;
    this.exporting.set(true);
    try {
      await this.waitForImages(el);
      const html2canvas = (await import('html2canvas')).default;
      const canvas = await html2canvas(el, {
        backgroundColor: '#0a0a1e',
        useCORS: true, allowTaint: true, scale: 2,
        windowWidth: el.scrollWidth, windowHeight: el.scrollHeight,
      });
      const link = document.createElement('a');
      link.download = `${this.deck()?.name || 'mazo'}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    } catch (e) {
      console.error('Error exportando imagen:', e);
    } finally {
      this.exporting.set(false);
    }
  }

  async copyImageToClipboard() {
    const el = this.deckContent?.nativeElement;
    if (!el || this.exporting()) return;
    const navAny = navigator as Navigator & { clipboard?: { write?: (items: ClipboardItem[]) => Promise<void> } };
    if (!navAny.clipboard?.write || typeof (window as Window & typeof globalThis & { ClipboardItem?: typeof ClipboardItem }).ClipboardItem === 'undefined') {
      return this.exportImage();
    }
    this.exporting.set(true);
    try {
      await this.waitForImages(el);
      const html2canvas = (await import('html2canvas')).default;
      const canvas = await html2canvas(el, {
        backgroundColor: '#0a0a1e',
        useCORS: true, allowTaint: true, scale: 2,
        windowWidth: el.scrollWidth, windowHeight: el.scrollHeight,
      });
      const blob: Blob | null = await new Promise(res => canvas.toBlob(b => res(b), 'image/png'));
      if (blob) {
        await navAny.clipboard.write([new ClipboardItem({ 'image/png': blob })]);
        this.fireToast('Imagen copiada');
      }
    } catch (e) {
      console.error('Error copiando imagen:', e);
    } finally {
      this.exporting.set(false);
    }
  }

  private waitForImages(el: HTMLElement): Promise<void[]> {
    const imgs = Array.from(el.querySelectorAll('img')) as HTMLImageElement[];
    return Promise.all(imgs.map(img => {
      if (img.complete && img.naturalWidth > 0) return Promise.resolve();
      return new Promise<void>(resolve => {
        img.onload = () => resolve();
        img.onerror = () => resolve();
        img.loading = 'eager';
        const src = img.src; img.src = ''; img.src = src;
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
