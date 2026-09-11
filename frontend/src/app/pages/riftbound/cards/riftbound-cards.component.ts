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
import { RiftboundService } from '../../../services/riftbound.service';
import { RiftboundCard, RiftboundCardLite, RiftboundColor } from '../../../models/riftbound';
import { TcgPriceComponent } from '../../../components/tcg-price/tcg-price.component';
import { IconComponent } from '../../../components/icon/icon.component';

const COLORS: { code: RiftboundColor; label: string; hex: string }[] = [
  { code: 'fury',  label: 'Fury',  hex: '#e94560' },
  { code: 'calm',  label: 'Calm',  hex: '#4caf50' },
  { code: 'mind',  label: 'Mind',  hex: '#3aa6ff' },
  { code: 'body',  label: 'Body',  hex: '#ff9a3c' },
  { code: 'chaos', label: 'Chaos', hex: '#9c5dff' },
  { code: 'order', label: 'Order', hex: '#ff6b7d' },
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

const RARITIES = [
  { code: 'common', label: 'Common' },
  { code: 'uncommon', label: 'Uncommon' },
  { code: 'rare', label: 'Rare' },
  { code: 'epic', label: 'Epic' },
  { code: 'legendary', label: 'Legendary' },
  { code: 'champion', label: 'Champion' },
  { code: 'promo', label: 'Promo' },
];

@Component({
  selector: 'app-riftbound-cards',
  standalone: true,
  imports: [CommonModule, FormsModule, TcgPriceComponent, IconComponent],
  template: `
    <div class="rb-cards-page">
      <!-- Header -->
      <header class="page-head">
        <div class="head-left">
          <h1><app-icon name="library" [size]="22"></app-icon> Catálogo Riftbound</h1>
          <span class="count-pill">{{ totalCount() }} cartas</span>
        </div>
      </header>

      <!-- Filters container -->
      <div class="filters-card">
        <!-- Search row -->
        <div class="search-row">
          <div class="search-input-wrap">
            <app-icon name="search" [size]="15"></app-icon>
            <input type="search"
                   [(ngModel)]="searchQuery"
                   (ngModelChange)="onSearchInput()"
                   [placeholder]="searchMode === 'ability' ? 'Buscar en texto de habilidad…' : (searchMode === 'all' ? 'Buscar nombre o habilidad…' : 'Buscar por nombre o número…')" />
            @if (searchQuery) {
              <button class="clear-btn" (click)="searchQuery=''; reset()" title="Limpiar"><app-icon name="x" [size]="14"></app-icon></button>
            }
          </div>

          <div class="search-modes" role="tablist" aria-label="Modo de búsqueda">
            <button type="button" role="tab"
                    [class.active]="searchMode === 'name'"
                    (click)="setMode('name')">Nombre</button>
            <button type="button" role="tab"
                    [class.active]="searchMode === 'ability'"
                    (click)="setMode('ability')">Habilidad</button>
            <button type="button" role="tab"
                    [class.active]="searchMode === 'all'"
                    (click)="setMode('all')">Todo</button>
          </div>

          @if (hasActiveFilter()) {
            <button class="clear-all-btn" (click)="clearAll()" title="Limpiar filtros">
              <app-icon name="refresh-cw" [size]="13"></app-icon>
              <span>Limpiar</span>
            </button>
          }
        </div>

        <!-- Type chips -->
        <div class="type-chips">
          <button class="chip" [class.active]="!typeFilter" (click)="setType('')">Todos los tipos</button>
          @for (t of types; track t.code) {
            <button class="chip"
                    [class.active]="typeFilter === t.code"
                    (click)="setType(t.code)">{{ t.label }}</button>
          }
        </div>

        <!-- Selects row -->
        <div class="filter-row">
          <div class="filter-group">
            <select [(ngModel)]="setFilter" (ngModelChange)="reset()">
              <option value="">Todos los sets</option>
              @for (s of sets(); track s.code) {
                <option [value]="s.code">{{ s.code }} — {{ s.name }}</option>
              }
            </select>
          </div>

          <div class="filter-group">
            <select [(ngModel)]="energyFilter" (ngModelChange)="reset()">
              <option [ngValue]="null">Cualquier energía</option>
              @for (n of [0,1,2,3,4,5,6,7,8]; track n) {
                <option [ngValue]="n">Energía: {{ n }}</option>
              }
            </select>
          </div>

          <div class="filter-group">
            <select [(ngModel)]="rarityFilter" (ngModelChange)="reset()">
              <option value="">Todas las rarezas</option>
              @for (r of rarities; track r.code) {
                <option [value]="r.code">{{ r.label }}</option>
              }
            </select>
          </div>
        </div>

        <!-- Domains row -->
        <div class="color-row">
          <span class="color-row-label">Dominios:</span>
          @for (c of colors; track c.code) {
            <button class="color-chip"
                    [class.active]="selectedColors().has(c.code)"
                    [style.--c]="c.hex"
                    (click)="toggleColor(c.code)">
              <span class="color-dot"></span>
              {{ c.label }}
            </button>
          }
        </div>
      </div>

      <!-- Loading state -->
      @if (loading() && cards().length === 0) {
        <div class="loading-state">
          <app-icon name="refresh-cw" [size]="18"></app-icon>
          <span>Cargando cartas...</span>
        </div>
      }

      <!-- Grid -->
      <div class="card-grid">
        @for (card of cards(); track card.id) {
          <button type="button" class="rb-card" (click)="openCard(card.card_number)">
            <div class="rb-card-img-wrap">
              @if (cardImageUrl(card); as imgUrl) {
                <img [src]="imgUrl" [alt]="card.name" loading="lazy" decoding="async"
                     (error)="onCardImageError(card, $event)" />
              } @else {
                <div class="rb-card-placeholder">{{ card.name }}</div>
              }
              <div class="hover-overlay">
                <app-icon name="eye" [size]="20"></app-icon>
              </div>
            </div>
            <div class="rb-card-meta">
              <strong>{{ card.name }}</strong>
              <div class="card-submeta">
                <span class="card-num">{{ card.card_number }}</span>
                @if (card.card_type) {
                  <span class="card-type-chip">{{ card.card_type }}</span>
                }
              </div>
              @if (card.description) {
                <p class="rb-card-ability">{{ card.description }}</p>
              }
              <app-tcg-price [cardName]="card.name" [compact]="true" [showLink]="true"></app-tcg-price>
            </div>
          </button>
        }
      </div>

      <!-- Detail Modal -->
      @if (modalOpen()) {
        <div class="rb-modal-overlay" (click)="closeCard()">
          <div class="rb-modal" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
            <button class="rb-modal-close" (click)="closeCard()" aria-label="Cerrar">
              <app-icon name="x" [size]="16"></app-icon>
            </button>
            @if (modalLoading()) {
              <div class="loading-state" style="padding: 4rem;">
                <app-icon name="refresh-cw" [size]="20"></app-icon>
                <span>Cargando detalles…</span>
              </div>
            } @else if (selectedCard(); as c) {
              <div class="rb-modal-layout">
                <div class="rb-modal-art">
                  @if (cardImageUrl(c); as imgUrl) {
                    <img class="rb-modal-img" [src]="imgUrl" [alt]="c.name"
                         (error)="onCardImageError(c, $event)" />
                  }
                </div>
                <div class="rb-modal-info">
                  <p class="card-edition-text">
                    <app-icon name="layers" [size]="12"></app-icon>
                    {{ c.card_number }} · {{ c.set?.name || c.set?.code || '—' }}
                  </p>
                  <h2>{{ c.name }}</h2>

                  <div class="badges">
                    @if (c.card_type) { <span class="badge">{{ c.card_type }}</span> }
                    @if (c.rarity) { <span class="badge badge-rarity">{{ c.rarity }}</span> }
                    @if (c.variant) { <span class="badge">{{ c.variant }}</span> }
                    @for (col of c.colors; track col) { <span class="badge color">{{ col }}</span> }
                    @for (st of c.subtypes; track st) { <span class="badge">{{ st }}</span> }
                  </div>

                  <div class="stats-row">
                    @if (c.energy != null) {
                      <div class="stat-pill stat-energy">
                        <app-icon name="zap" [size]="13"></app-icon>
                        <span class="stat-label">Energía</span>
                        <span class="stat-val">{{ c.energy }}</span>
                      </div>
                    }
                    @if (c.power != null) {
                      <div class="stat-pill stat-power">
                        <app-icon name="swords" [size]="13"></app-icon>
                        <span class="stat-label">Power</span>
                        <span class="stat-val">{{ c.power }}</span>
                      </div>
                    }
                    @if (c.might != null) {
                      <div class="stat-pill stat-might">
                        <app-icon name="shield" [size]="13"></app-icon>
                        <span class="stat-label">Might</span>
                        <span class="stat-val">{{ c.might }}</span>
                      </div>
                    }
                  </div>

                  @if (c.description) {
                    <div class="ability-block">
                      <h4><app-icon name="sparkles" [size]="13"></app-icon> Habilidad</h4>
                      <p class="desc">{{ c.description }}</p>
                    </div>
                  }

                  <div class="market-section">
                    <app-tcg-price [cardName]="c.name" [compact]="false" [showLink]="true"></app-tcg-price>
                  </div>
                </div>
              </div>
            } @else {
              <p class="muted center" style="padding:3rem">Carta no encontrada.</p>
            }
          </div>
        </div>
      }

      @if (!loading() && cards().length === 0) {
        <div class="empty-state">
          <app-icon name="library" [size]="32"></app-icon>
          <p>Sin resultados con los filtros actuales.</p>
        </div>
      }

      @if (hasMore()) {
        <div #cardsSentinel class="infinite-sentinel" aria-hidden="true"></div>
      }
      @if (loading() && cards().length > 0) {
        <p class="status-more"><app-icon name="refresh-cw" [size]="14"></app-icon> Cargando más cartas...</p>
      }
      @if (!hasMore() && !loading() && cards().length > 0) {
        <p class="status-end">— Fin del catálogo Riftbound —</p>
      }
    </div>
  `,
  styles: [`
    .rb-cards-page {
      max-width: 1400px;
      margin: 0 auto;
      padding: 1.25rem 1.5rem;
    }

    .page-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 1.25rem;

      .head-left {
        display: flex;
        align-items: center;
        gap: 0.75rem;

        h1 {
          margin: 0;
          font-size: 1.3rem;
          font-weight: 700;
          color: #ffffff;
          display: flex;
          align-items: center;
          gap: 0.5rem;
          letter-spacing: -0.02em;

          app-icon { color: var(--ui-accent, #06b6d4); }
        }

        .count-pill {
          font-size: 0.8rem;
          color: var(--ui-text-muted);
          background: rgba(255, 255, 255, 0.04);
          padding: 0.2rem 0.6rem;
          border-radius: 999px;
          border: 1px solid var(--ui-border);
        }
      }
    }

    .filters-card {
      display: flex;
      flex-direction: column;
      gap: 0.75rem;
      margin-bottom: 1.5rem;
    }

    .search-row {
      display: flex;
      gap: 0.6rem;
      flex-wrap: wrap;
      align-items: center;

      .search-input-wrap {
        flex: 1 1 240px;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0 0.75rem;
        background: var(--ui-surface);
        border: 1px solid var(--ui-border);
        border-radius: 8px;
        transition: border-color 0.15s ease;

        &:focus-within {
          border-color: var(--ui-accent, #06b6d4);
        }

        app-icon { color: var(--ui-text-muted); flex-shrink: 0; }

        input {
          flex: 1;
          border: none;
          background: transparent;
          color: #ffffff;
          font-size: 0.875rem;
          padding: 0.6rem 0;
          outline: none;

          &::placeholder { color: var(--ui-text-muted); }
        }

        .clear-btn {
          background: none;
          border: none;
          color: var(--ui-text-muted);
          cursor: pointer;
          display: flex;
          align-items: center;
          padding: 2px;
          &:hover { color: #fff; }
        }
      }

      .search-modes {
        display: flex;
        background: var(--ui-surface);
        border: 1px solid var(--ui-border);
        border-radius: 8px;
        overflow: hidden;

        button {
          padding: 0.55rem 0.85rem;
          background: transparent;
          border: none;
          color: var(--ui-text-muted);
          font-size: 0.8rem;
          cursor: pointer;
          transition: all 0.15s ease;

          &.active {
            background: rgba(6, 182, 212, 0.15);
            color: var(--ui-accent, #06b6d4);
            font-weight: 600;
          }

          &:hover:not(.active) {
            color: #ffffff;
          }
        }
      }

      .clear-all-btn {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.55rem 0.85rem;
        background: var(--ui-surface);
        border: 1px solid var(--ui-border);
        border-radius: 8px;
        color: var(--ui-text-muted);
        font-size: 0.8rem;
        cursor: pointer;
        transition: all 0.15s ease;

        &:hover {
          border-color: #ef4444;
          color: #ef4444;
        }
      }
    }

    .type-chips {
      display: flex;
      gap: 0.4rem;
      flex-wrap: wrap;

      .chip {
        padding: 0.35rem 0.75rem;
        border-radius: 999px;
        border: 1px solid var(--ui-border);
        background: var(--ui-surface);
        color: var(--ui-text-muted);
        font-size: 0.78rem;
        cursor: pointer;
        transition: all 0.15s ease;

        &:hover {
          border-color: rgba(255, 255, 255, 0.2);
          color: #ffffff;
        }

        &.active {
          background: rgba(6, 182, 212, 0.12);
          border-color: var(--ui-accent, #06b6d4);
          color: var(--ui-accent, #06b6d4);
          font-weight: 600;
        }
      }
    }

    .filter-row {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
      gap: 0.6rem;

      select {
        width: 100%;
        padding: 0.55rem 0.75rem;
        border-radius: 8px;
        border: 1px solid var(--ui-border);
        background: var(--ui-surface);
        color: var(--ui-text-muted);
        font-size: 0.82rem;
        cursor: pointer;
        outline: none;
        transition: border-color 0.15s ease;

        &:focus { border-color: var(--ui-accent, #06b6d4); }
        option { background: #18181b; }
      }
    }

    .color-row {
      display: flex;
      align-items: center;
      gap: 0.45rem;
      flex-wrap: wrap;

      .color-row-label {
        font-size: 0.78rem;
        color: var(--ui-text-muted);
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-right: 0.2rem;
      }

      .color-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.3rem 0.65rem;
        border-radius: 999px;
        border: 1px solid var(--ui-border);
        background: var(--ui-surface);
        color: var(--ui-text-muted);
        font-size: 0.78rem;
        cursor: pointer;
        transition: all 0.15s ease;

        .color-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: var(--c);
        }

        &.active {
          border-color: var(--c);
          background: color-mix(in srgb, var(--c) 15%, var(--ui-surface));
          color: #ffffff;
          font-weight: 600;
        }

        &:hover:not(.active) {
          border-color: rgba(255, 255, 255, 0.2);
          color: #ffffff;
        }
      }
    }

    .loading-state {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
      padding: 3rem 1rem;
      color: var(--ui-text-muted);
      font-size: 0.9rem;
    }

    .empty-state {
      text-align: center;
      padding: 3.5rem 1rem;
      color: var(--ui-text-muted);

      app-icon {
        color: rgba(255, 255, 255, 0.1);
        display: block;
        margin: 0 auto 0.75rem;
      }
    }

    .card-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(175px, 1fr));
      gap: 0.85rem;
      margin-bottom: 2rem;

      @media (max-width: 480px) {
        grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
        gap: 0.55rem;
      }
    }

    .rb-card {
      display: flex;
      flex-direction: column;
      background: var(--ui-surface);
      border: 1px solid var(--ui-border);
      border-radius: 12px;
      overflow: hidden;
      cursor: pointer;
      text-align: left;
      color: inherit;
      padding: 0;
      transition: all 0.15s ease;

      &:hover {
        border-color: var(--ui-accent, #06b6d4);
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(0, 0, 0, 0.35);

        .hover-overlay { opacity: 1; }
        .rb-card-img-wrap img { transform: scale(1.04); }
      }

      .rb-card-img-wrap {
        position: relative;
        width: 100%;
        aspect-ratio: 3 / 4;
        overflow: hidden;
        background: #09090b;

        img {
          width: 100%;
          height: 100%;
          object-fit: cover;
          display: block;
          transition: transform 0.2s ease;
        }

        .rb-card-placeholder {
          width: 100%;
          height: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 0.5rem;
          text-align: center;
          font-size: 0.8rem;
          color: var(--ui-text-muted);
        }

        .hover-overlay {
          position: absolute;
          inset: 0;
          background: rgba(0, 0, 0, 0.5);
          display: flex;
          align-items: center;
          justify-content: center;
          color: #ffffff;
          opacity: 0;
          transition: opacity 0.15s ease;
        }
      }

      .rb-card-meta {
        padding: 0.6rem 0.75rem;
        display: flex;
        flex-direction: column;
        gap: 0.25rem;

        strong {
          font-size: 0.82rem;
          font-weight: 600;
          color: #ffffff;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .card-submeta {
          display: flex;
          align-items: center;
          justify-content: space-between;
          font-size: 0.7rem;
          color: var(--ui-text-muted);

          .card-type-chip {
            background: rgba(255, 255, 255, 0.05);
            padding: 0.1rem 0.4rem;
            border-radius: 4px;
          }
        }

        .rb-card-ability {
          font-size: 0.72rem;
          color: var(--ui-text-muted);
          line-height: 1.4;
          margin: 0.2rem 0 0;
          display: -webkit-box;
          -webkit-line-clamp: 2;
          line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
      }
    }

    /* Modal */
    .rb-modal-overlay {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.8);
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      z-index: 1000;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 1.5rem;
      animation: fadeIn 0.15s ease;
    }

    .rb-modal {
      position: relative;
      background: #1a1c23;
      border: 1px solid var(--ui-border);
      border-radius: 20px;
      max-width: 820px;
      width: 100%;
      max-height: 90vh;
      overflow-y: auto;
      box-shadow: 0 24px 80px rgba(0, 0, 0, 0.6);
      animation: slideUp 0.2s ease;

      .rb-modal-close {
        position: absolute;
        top: 0.75rem;
        right: 0.75rem;
        width: 32px;
        height: 32px;
        border-radius: 8px;
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid var(--ui-border);
        color: var(--ui-text-muted);
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        z-index: 10;
        transition: all 0.15s ease;

        &:hover {
          background: rgba(239, 68, 68, 0.15);
          border-color: #ef4444;
          color: #ef4444;
        }
      }

      .rb-modal-layout {
        display: flex;
        flex-direction: row;
        gap: 1.5rem;
        padding: 1.5rem;

        @media (max-width: 768px) {
          flex-direction: column;
          padding: 1.25rem;
        }

        .rb-modal-art {
          flex: 0 0 42%;
          display: flex;

          img {
            width: 100%;
            height: auto;
            max-height: 65vh;
            border-radius: 12px;
            object-fit: contain;
            background: #09090b;
            border: 1px solid var(--ui-border);
            margin: auto;
          }

          @media (max-width: 768px) {
            flex: 0 0 auto;

            img {
              max-height: 40vh;
            }
          }
        }

        .rb-modal-info {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: 0.6rem;
          min-width: 0;

          h2 {
            margin: 0;
            font-size: 1.3rem;
            font-weight: 700;
            color: #ffffff;
            letter-spacing: -0.01em;
            padding-right: 2rem;
          }

          .card-edition-text {
            margin: 0;
            font-size: 0.75rem;
            color: var(--ui-text-muted);
            display: flex;
            align-items: center;
            gap: 0.35rem;
          }

          .badges {
            display: flex;
            flex-wrap: wrap;
            gap: 0.35rem;

            .badge {
              font-size: 0.72rem;
              padding: 0.2rem 0.55rem;
              border-radius: 999px;
              background: rgba(255, 255, 255, 0.06);
              border: 1px solid var(--ui-border);
              color: var(--ui-text-muted);

              &.badge-rarity {
                background: rgba(6, 182, 212, 0.12);
                border-color: rgba(6, 182, 212, 0.3);
                color: var(--ui-accent, #06b6d4);
                font-weight: 600;
              }

              &.color {
                background: rgba(233, 69, 96, 0.1);
                border-color: rgba(233, 69, 96, 0.3);
              }
            }
          }

          .stats-row {
            display: flex;
            gap: 0.5rem;
            flex-wrap: wrap;

            .stat-pill {
              display: flex;
              align-items: center;
              gap: 0.4rem;
              padding: 0.4rem 0.75rem;
              background: rgba(255, 255, 255, 0.05);
              border: 1px solid var(--ui-border);
              border-radius: 999px;

              app-icon { flex-shrink: 0; }

              .stat-label {
                font-size: 0.72rem;
                color: var(--ui-text-muted);
                font-weight: 600;
              }

              .stat-val {
                font-size: 0.85rem;
                font-weight: 700;
                color: #ffffff;
              }

              &.stat-energy app-icon { color: #f2c744; }
              &.stat-power app-icon { color: #e94560; }
              &.stat-might app-icon { color: #3aa6ff; }
            }
          }

          .ability-block {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--ui-border);
            border-radius: 10px;
            padding: 0.75rem 0.9rem;

            h4 {
              margin: 0 0 0.35rem;
              font-size: 0.78rem;
              color: var(--ui-accent, #06b6d4);
              display: flex;
              align-items: center;
              gap: 0.35rem;
              text-transform: uppercase;
              letter-spacing: 0.04em;
            }

            .desc {
              margin: 0;
              white-space: pre-wrap;
              font-size: 0.85rem;
              color: #e2e8f0;
              line-height: 1.55;
            }
          }

          .market-section {
            margin-top: 0.2rem;
          }
        }
      }
    }

    .infinite-sentinel { height: 1px; }

    .status-more, .status-end {
      text-align: center;
      padding: 1rem;
      font-size: 0.8rem;
      color: var(--ui-text-muted);
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.4rem;
    }

    .status-end { opacity: 0.5; }

    @keyframes fadeIn {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    @keyframes slideUp {
      from { transform: translateY(12px); opacity: 0; }
      to { transform: translateY(0); opacity: 1; }
    }
  `],
})
export class RiftboundCardsComponent implements OnInit, AfterViewInit, OnDestroy {
  private rb = inject(RiftboundService);
  private brokenImageUrlsByCard = new Map<string, Set<string>>();
  private imageFallbackNonce = signal(0);

  readonly colors = COLORS;
  readonly types = TYPES;
  readonly rarities = RARITIES;
  // Debe coincidir con DRF PAGE_SIZE (backend/backend/settings.py).
  // Si no coincide, totalPages se calcula mal y quedan cartas inaccesibles.
  readonly pageSize = 20;

  searchQuery = '';
  searchMode: 'name' | 'ability' | 'all' = 'name';
  typeFilter = '';
  setFilter = '';
  rarityFilter = '';
  energyFilter: number | null = null;
  selectedColors = signal(new Set<RiftboundColor>());

  cards = signal<RiftboundCardLite[]>([]);
  hasMore = signal(false);
  sets = signal<{ code: string; name: string }[]>([]);
  loading = signal(false);
  modalOpen = signal(false);
  modalLoading = signal(false);
  selectedCard = signal<RiftboundCard | null>(null);
  page = signal(1);
  totalCount = signal(0);
  totalPages = computed(() => Math.max(1, Math.ceil(this.totalCount() / this.pageSize)));
  private cardsSentinelRef?: ElementRef<HTMLElement>;
  private cardsObserver?: IntersectionObserver;
  private contentScrollEl: HTMLElement | null = null;

  @ViewChild('cardsSentinel')
  set cardsSentinelSetter(el: ElementRef<HTMLElement> | undefined) {
    this.cardsSentinelRef = el;
    this.setupCardsObserver();
  }

  hasActiveFilter = computed(() =>
    !!(this.searchQuery || this.typeFilter || this.setFilter ||
       this.rarityFilter || this.energyFilter !== null || this.selectedColors().size));

  private searchTimer: ReturnType<typeof setTimeout> | null = null;

  private cardImageKey(card: RiftboundCardLite | RiftboundCard): string {
    return String(card.id ?? card.card_number ?? card.name ?? 'unknown');
  }

  private toHttps(url: string | null | undefined): string {
    const value = (url || '').trim();
    if (!value) return '';
    return value.startsWith('http://') ? `https://${value.slice(7)}` : value;
  }

  private imageUrlVariants(url: string | null | undefined): string[] {
    const raw = (url || '').trim();
    if (!raw) return [];
    const https = this.toHttps(raw);
    return raw === https ? [raw] : [raw, https];
  }

  private cloudinaryFetchVariants(url: string | null | undefined): string[] {
    const variants = this.imageUrlVariants(url);
    if (!variants.length) return [];
    return variants.map((candidate) =>
      `https://res.cloudinary.com/daobfx9yb/image/fetch/f_auto,q_auto/${encodeURIComponent(candidate)}`
    );
  }

  private candidateImageUrls(card: RiftboundCardLite | RiftboundCard): string[] {
    const candidates = [
      ...this.imageUrlVariants(card.cdn_image_url),
      ...this.cloudinaryFetchVariants(card.image_url),
      ...this.cloudinaryFetchVariants(card.image_url_small),
      ...this.cloudinaryFetchVariants(card.image),
      ...this.imageUrlVariants(card.image_url),
      ...this.imageUrlVariants(card.image_url_small),
      ...this.imageUrlVariants(card.image),
    ].filter(Boolean);

    return Array.from(new Set(candidates));
  }

  cardImageUrl(card: RiftboundCardLite | RiftboundCard | null | undefined): string {
    this.imageFallbackNonce();
    if (!card) return '';

    const broken = this.brokenImageUrlsByCard.get(this.cardImageKey(card));
    for (const url of this.candidateImageUrls(card)) {
      if (!broken?.has(url)) return url;
    }
    return '';
  }

  onCardImageError(card: RiftboundCardLite | RiftboundCard | null | undefined, event: Event) {
    if (!card) return;
    const img = event.target as HTMLImageElement | null;
    const failedUrls = [img?.currentSrc, img?.src]
      .map((url) => (url || '').trim())
      .filter(Boolean);
    if (!failedUrls.length) return;

    const key = this.cardImageKey(card);
    let broken = this.brokenImageUrlsByCard.get(key);
    if (!broken) {
      broken = new Set<string>();
      this.brokenImageUrlsByCard.set(key, broken);
    }

    let changed = false;
    for (const url of failedUrls) {
      if (!broken.has(url)) {
        broken.add(url);
        changed = true;
      }
    }

    if (changed) this.imageFallbackNonce.update((value) => value + 1);
  }

  ngOnInit() {
    this.rb.listSets().subscribe({
      next: (sets: any) => {
        const arr = Array.isArray(sets) ? sets : (sets?.results ?? []);
        this.sets.set(arr.map((s: any) => ({ code: s.code, name: s.name })));
      },
    });
    this.reload();
  }

  ngAfterViewInit() {
    this.setupCardsObserver();
    this.attachContentScrollListener();
    this.tryInfiniteScrollFallback();
  }

  ngOnDestroy() {
    this.cardsObserver?.disconnect();
    this.detachContentScrollListener();
    if (this.searchTimer) clearTimeout(this.searchTimer);
    document.body.style.overflow = '';
  }

  setType(t: string) { this.typeFilter = t; this.reset(); }

  setMode(m: 'name' | 'ability' | 'all') {
    if (this.searchMode === m) return;
    this.searchMode = m;
    if (this.searchQuery) this.reset();
  }

  toggleColor(c: RiftboundColor) {
    const set = new Set(this.selectedColors());
    if (set.has(c)) set.delete(c); else set.add(c);
    this.selectedColors.set(set);
    this.reset();
  }

  onSearchInput() {
    if (this.searchTimer) clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => this.reset(), 300);
  }

  clearAll() {
    this.searchQuery = '';
    this.typeFilter = '';
    this.setFilter = '';
    this.rarityFilter = '';
    this.energyFilter = null;
    this.selectedColors.set(new Set());
    this.reset();
  }

  reset() {
    this.reload();
  }

  reload() {
    this.page.set(1);
    this.cards.set([]);
    this.hasMore.set(false);
    this.fetchCardsPage();
  }

  loadMoreCards() {
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
      excludeBattlefields: this.selectedColors().size > 0 && this.typeFilter !== 'battlefield',
      page: this.page(),
      pageSize: this.pageSize,
      lite: true,
    }).subscribe({
      next: (resp) => {
        if (append) {
          this.cards.update(curr => [...curr, ...(resp.results as RiftboundCardLite[])]);
        } else {
          this.cards.set(resp.results as RiftboundCardLite[]);
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
    this.cardsObserver = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          this.loadMoreCards();
          break;
        }
      }
    }, { rootMargin: '320px 0px' });
    this.cardsObserver.observe(sentinel);
  }

  private attachContentScrollListener() {
    this.detachContentScrollListener();
    const el = document.querySelector('main.content') as HTMLElement | null;
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

  @HostListener('window:scroll')
  onWindowScroll() { this.tryInfiniteScrollFallback(); }

  @HostListener('window:resize')
  onWindowResize() { this.tryInfiniteScrollFallback(); }

  private tryInfiniteScrollFallback() {
    if (!this.isNearPageBottom()) return;
    this.loadMoreCards();
  }

  private isNearPageBottom(offset = 900): boolean {
    const container = this.contentScrollEl;
    if (container && container.scrollHeight > container.clientHeight) {
      return container.scrollTop + container.clientHeight >= container.scrollHeight - 420;
    }
    const doc = document.documentElement;
    const body = document.body;
    const scrollTop = window.scrollY || doc.scrollTop || 0;
    const viewport = window.innerHeight || doc.clientHeight || 0;
    const fullHeight = Math.max(doc.scrollHeight, body?.scrollHeight || 0);
    return scrollTop + viewport >= fullHeight - offset;
  }

  openCard(cardNumber: string) {
    this.modalOpen.set(true);
    this.modalLoading.set(true);
    this.selectedCard.set(null);
    document.body.style.overflow = 'hidden';
    this.rb.getCard(cardNumber).subscribe({
      next: (c) => { this.selectedCard.set(c); this.modalLoading.set(false); },
      error: () => this.modalLoading.set(false),
    });
  }

  closeCard() {
    this.modalOpen.set(false);
    this.selectedCard.set(null);
    document.body.style.overflow = '';
  }

  @HostListener('document:keydown.escape')
  onEsc() { if (this.modalOpen()) this.closeCard(); }
}
