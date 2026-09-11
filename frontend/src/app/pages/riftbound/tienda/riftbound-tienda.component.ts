import {
  Component, OnInit, AfterViewInit, OnDestroy, ChangeDetectionStrategy, ChangeDetectorRef,
  ElementRef, ViewChild, HostListener, inject, signal,
} from '@angular/core';
import { CommonModule, DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { RiftboundService } from '../../../services/riftbound.service';
import { AuthService } from '../../../services/auth.service';
import {
  RiftboundCollectionEntry, RiftboundCardLite, RiftboundPublicBinderProfile,
  RiftboundWishlistEntry, RiftboundStoreOrderCreatePayload,
  RIFTBOUND_COLORS, RIFTBOUND_CARD_TYPES, RiftboundColor,
} from '../../../models/riftbound';
import { ShareImageComponent, ShareImageItem } from '../../../components/share-image/share-image.component';
import { CardPhotoCarouselComponent } from '../../../components/card-photo-carousel/card-photo-carousel.component';
import { TcgPriceComponent } from '../../../components/tcg-price/tcg-price.component';

interface RiftboundCartItem {
  entryId: number;
  cardId: number;
  name: string;
  price: number | null;
  qty: number;
  available: number;
  image: string;
}

@Component({
  selector: 'app-riftbound-tienda',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, DecimalPipe, ShareImageComponent, CardPhotoCarouselComponent, TcgPriceComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
  <div class="tienda-container">
    @if (loading() && !store()) { <div class="loading">Cargando tienda...</div> }
    @if (errorMsg()) {
      <div class="error-state">
        <h2>Tienda no encontrada</h2>
        <p>{{ errorMsg() }}</p>
        <a routerLink="/riftbound/tiendas" class="btn btn-primary">← Ver todas las tiendas</a>
      </div>
    }

    @if (store(); as s) {
      <div class="store-header">
        @if (s.binder_avatar_url || s.user_avatar_url) {
          <img class="store-avatar" [src]="s.binder_avatar_url || s.user_avatar_url" alt="avatar" />
        } @else {
          <div class="store-avatar-placeholder">🏪</div>
        }
        <div class="store-info">
          <h1>{{ s.display_name || s.username }}</h1>
          <p class="store-meta">
            @if (s.city) { <span>📍 {{ s.city }}</span> }
            <span>🌎 {{ s.country }}</span>
            <span>📦 {{ s.selling_count || 0 }} cartas en venta</span>
          </p>
          @if (s.bio) { <p class="store-bio">{{ s.bio }}</p> }
          <div class="contact-row">
            @if (s.whatsapp) {
              <a class="contact-chip wa" [href]="'https://wa.me/' + cleanWa(s.whatsapp)" target="_blank">
                <span class="ci-icon" aria-hidden="true">📱</span><span class="ci-label">WhatsApp</span>
              </a>
            }
            @if (s.instagram) {
              <a class="contact-chip ig" [href]="'https://instagram.com/' + cleanHandle(s.instagram)" target="_blank">
                <span class="ci-icon" aria-hidden="true">📷</span><span class="ci-label">Instagram</span>
              </a>
            }
            @if (s.discord) {
              <span class="contact-chip dc">
                <span class="ci-icon" aria-hidden="true">💬</span><span class="ci-label">{{ s.discord }}</span>
              </span>
            }
            @if (s.email_public) {
              <a class="contact-chip em" [href]="'mailto:' + s.email_public">
                <span class="ci-icon" aria-hidden="true">✉️</span><span class="ci-label">Email</span>
              </a>
            }
            @if (s.accepts_trades) {
              <span class="contact-chip tr">
                <span class="ci-icon" aria-hidden="true">🔄</span><span class="ci-label">Acepta cambios</span>
              </span>
            }
            <a class="contact-chip" routerLink="/mis-compras" [queryParams]="{ game: 'riftbound', store: token }" target="_blank">
              <span class="ci-icon" aria-hidden="true">📦</span><span class="ci-label">Mis pedidos</span>
            </a>
          </div>
          @if (s.payment_methods) { <p class="store-line"><strong>💳 Pago:</strong> {{ s.payment_methods }}</p> }
          @if (s.shipping_info) { <p class="store-line"><strong>🚚 Envío:</strong> {{ s.shipping_info }}</p> }
          <div class="share-row" style="margin-top:.5rem;">
            @if (activeTab() === 'store') {
              <app-share-image
                mode="selling"
                gameLabel="Riftbound"
                [sellerName]="sellerHandle()"
                [contactLine]="shareSellingContactLine()"
                [items]="shareStoreItems()"
                ctaLabel="Imagen tienda"
                filenamePrefix="shadowforge-riftbound"
                footerTagline="ShadowForge · Marketplace TCG">
              </app-share-image>
            }
          </div>
        </div>
      </div>

      <div class="tabs-bar">
        <button class="tab-btn" [class.active]="activeTab() === 'store'" (click)="switchTab('store')"
                [disabled]="s.has_store === false">
          🏪 Tienda
          @if (s.selling_count) { <span class="tab-count">{{ s.selling_count }}</span> }
        </button>
        <button class="tab-btn" [class.active]="activeTab() === 'wishlist'" (click)="switchTab('wishlist')"
                [disabled]="s.has_wishlist === false">
          ❤️ Wishlist
          @if (s.wishlist_count) { <span class="tab-count">{{ s.wishlist_count }}</span> }
        </button>
      </div>

      @if (createdOrderId) {
        <div class="order-success">
          ✅ Pedido #{{ createdOrderId }} creado correctamente. El vendedor ya lo ve en su carpeta.
          <a routerLink="/mis-compras" [queryParams]="{ game: 'riftbound', store: token }" target="_blank">Ver mis pedidos ↗</a>
        </div>
      }

      @if (activeTab() === 'store') {
      <div class="filters-bar">
        <input class="filters-search" type="text" placeholder="Buscar carta..." [(ngModel)]="search" (keyup.enter)="applyFilters()" />
        <button type="button" class="filters-toggle-btn" [class.active]="filtersOpen()"
                (click)="filtersOpen.set(!filtersOpen())"
                [attr.aria-expanded]="filtersOpen()" aria-label="Mostrar filtros">
          <span class="ft-icon" aria-hidden="true">🔽</span>
          <span class="ft-text">Filtros</span>
          @if (activeFilterCount() > 0) { <span class="filter-badge">{{ activeFilterCount() }}</span> }
        </button>
      </div>

      @if (filtersOpen()) {
        <div class="filters-backdrop" (click)="filtersOpen.set(false)"></div>
        <div class="filters-drawer" role="dialog" aria-label="Filtros de la tienda">
          <div class="filters-drawer-head">
            <h3>Filtros</h3>
            <button type="button" class="close-btn" (click)="filtersOpen.set(false)" aria-label="Cerrar filtros">✕</button>
          </div>
          <div class="filters-drawer-body">
            <div class="filter-group">
              <label class="filter-group-label">Tipo de carta</label>
              <select class="sf-type" [(ngModel)]="ftype">
                <option value="">Todos los tipos</option>
                @for (t of cardTypes; track t.code) {
                  <option [value]="t.code">{{ t.label }}</option>
                }
              </select>
            </div>

            <div class="filter-group">
              <label class="filter-group-label">Colores</label>
              <div class="color-chip-row">
                @for (c of riftboundColors; track c.code) {
                  <button type="button" class="color-chip" [class.active]="fcolors().has(c.code)"
                          [style.--c]="c.hex" (click)="toggleColor(c.code)">{{ c.label }}</button>
                }
                @if (fcolors().size > 0) {
                  <button type="button" class="clear-colors" (click)="clearColors()">Limpiar</button>
                }
              </div>
            </div>

            <div class="filter-group">
              <label class="filter-group-label">Estadísticas</label>
              <div class="stats-row">
                <label>Energía<input type="number" min="0" placeholder="—" [(ngModel)]="fenergy" /></label>
                <label>Power<input type="number" min="0" placeholder="—" [(ngModel)]="fpower" /></label>
                <label>Might<input type="number" min="0" placeholder="—" [(ngModel)]="fmight" /></label>
              </div>
            </div>

            <div class="filter-group">
              <label class="filter-group-label">Estado</label>
              <select class="sf-foil" [(ngModel)]="ffoil">
                <option value="">Foil/Normal</option>
                <option value="1">Solo foil</option>
                <option value="0">Solo normal</option>
              </select>
            </div>

            <div class="filter-group">
              <label class="filter-group-label">Precio</label>
              <div class="price-range-row">
                <input type="number" placeholder="Mín." [(ngModel)]="priceMin" min="0" />
                <span aria-hidden="true">—</span>
                <input type="number" placeholder="Máx." [(ngModel)]="priceMax" min="0" />
              </div>
            </div>

            <div class="filter-group">
              <label class="filter-group-label">Ordenar por</label>
              <select class="sf-order" [(ngModel)]="ordering">
                <option value="-price">Precio ↓</option>
                <option value="-id">Más recientes</option>
                <option value="price">Precio ↑</option>
                <option value="card__name">Nombre A-Z</option>
              </select>
            </div>
          </div>
          <div class="filters-drawer-actions">
            <button type="button" class="btn btn-sm" (click)="clearFilters()" [disabled]="loading()">Limpiar filtros</button>
            <button type="button" class="btn btn-sm btn-primary" (click)="applyFilters(); filtersOpen.set(false)" [disabled]="loading()">Aplicar</button>
          </div>
        </div>
      }

      <p class="results-count">{{ count() }} cartas</p>

      <div class="cards-grid">
        @for (e of entries(); track e.id) {
          <div class="store-card" [class.in-cart]="inCart(e.id) > 0">
            <div class="card-image" (click)="openPreview(e.card_data)">
              @if (entryCardImage(e)) {
                <app-card-photo-carousel
                  [cardImage]="entryCardImage(e)"
                  [fallbackUrls]="cardImageFallbacks(e.card_data)"
                  [photos]="[e.photo_url, e.photo_url_2]"
                  [alt]="e.card_data.name"
                  [thumbWidth]="350">
                </app-card-photo-carousel>
              } @else { <div class="img-fallback">{{ e.card_data.card_number }}</div> }
              @if (e.is_foil) { <div class="foil-badge">✨ FOIL</div> }
              @if (inCart(e.id) > 0) {
                <div class="qty-capsule" (click)="$event.stopPropagation()">
                  <button type="button" class="qty-btn qty-btn-minus" (click)="decreaseFromCart(e, $event)" aria-label="Quitar una unidad">−</button>
                  <span class="qty-value">{{ inCart(e.id) }}</span>
                  <button type="button" class="qty-btn qty-btn-plus" (click)="addToCart(e, $event)"
                          [disabled]="inCart(e.id) >= e.selling_quantity" aria-label="Agregar una unidad">+</button>
                </div>
              } @else {
                <button type="button" class="add-fab" (click)="addToCart(e, $event)"
                        [disabled]="e.selling_quantity <= 0" aria-label="Añadir al carrito">
                  <span aria-hidden="true">+</span>
                </button>
              }
            </div>
            <div class="card-body">
              <h4>{{ e.card_data.name }}</h4>
              <span class="card-meta">{{ e.card_data.card_number }} · {{ e.language }}</span>
              <div class="price-row">
                <span class="price">{{ e.price != null ? ('$' + (e.price | number)) : 'Consultar' }}</span>
                <span class="qty">x{{ e.selling_quantity }}</span>
              </div>
              <app-tcg-price [cardName]="e.card_data.name || ''" [compact]="true" [showLink]="false" [showMarketPrice]="false"></app-tcg-price>
            </div>
          </div>
        }
      </div>

      @if (hasMore()) {
        <div #storeSentinel class="infinite-sentinel" aria-hidden="true"></div>
      }
      @if (loading() && entries().length > 0) {
        <div class="loading">Cargando más...</div>
      }
      @if (!hasMore() && !loading() && entries().length > 0) {
        <p class="results-count" style="margin-top: 1rem;">— Fin de la tienda —</p>
      }
      } @else if (activeTab() === 'wishlist') {
        <div class="filter-row">
          <input type="text" placeholder="Buscar en wishlist..." [(ngModel)]="wishlistSearch" (keyup.enter)="reloadWishlist()" />
          <button class="btn btn-sm" (click)="reloadWishlist()">Buscar</button>
          <span style="flex:1"></span>
          <button class="btn btn-sm" (click)="shareWishlistLink()">🔗 Copiar link wishlist</button>
          <button class="btn btn-sm" (click)="shareWishlistWhatsApp()">📱 Compartir</button>
        </div>
        @if (wishlistLoading()) { <div class="loading">Cargando wishlist...</div> }
        @if (!wishlistLoading() && wishlist().length === 0) {
          <div class="empty-state">
            <p>{{ s.display_name || s.username }} no tiene cartas en su wishlist.</p>
          </div>
        }
        <div class="cards-grid">
          @for (w of wishlist(); track w.id) {
            <div class="store-card">
              <div class="card-image" (click)="openPreview(w.card_data)">
                @if (w.card_data.image) {
                  <img [src]="w.card_data.image" [alt]="w.card_data.name" loading="lazy" />
                } @else { <div class="img-fallback">{{ w.card_data.card_number }}</div> }
              </div>
              <div class="card-body">
                <h4>{{ w.card_data.name }}</h4>
                <span class="card-meta">{{ w.card_data.card_number }}</span>
                <div class="price-row">
                  <span class="qty wishlist-qty">❤️ Quiere x{{ w.desired_quantity }}</span>
                </div>
                <app-tcg-price [cardName]="w.card_data.name || ''" [compact]="true" [showLink]="false" [showMarketPrice]="false"></app-tcg-price>
              </div>
            </div>
          }
        </div>
      }
    }

    <!-- Floating cart button -->
    @if (cartCount() > 0) {
      <button class="cart-fab" (click)="showCart.set(true)">
        🛒 {{ cartCount() }} · \${{ cartTotal() | number }}
      </button>
    }

    <!-- Cart modal -->
    @if (showCart()) {
      <div class="modal-overlay" (click)="showCart.set(false)">
        <div class="cart-modal" (click)="$event.stopPropagation()">
          <div class="cart-head">
            <h3>🛒 Tu pedido</h3>
            <button class="close-btn" (click)="showCart.set(false)">✕</button>
          </div>
          @if (cart().length === 0) {
            <p class="empty-cart">Aún no agregas cartas.</p>
          } @else {
            <ul class="cart-list">
              @for (item of cart(); track item.entryId) {
                <li class="cart-item">
                  @if (item.image) { <img class="cart-item-thumb" [src]="item.image" [alt]="item.name" /> }
                  <strong class="cart-item-name">{{ item.name }}</strong>
                  <div class="cart-item-price">
                    <strong>\${{ ((item.price || 0) * item.qty) | number }}</strong>
                    <small>{{ item.price != null ? ('$' + (item.price | number) + ' c/u') : 'Sin precio' }}</small>
                  </div>
                  <div class="cart-item-controls">
                    <div class="cart-qty">
                      <button type="button" (click)="changeCartQty(item, -1)" aria-label="Quitar una unidad">−</button>
                      <span>{{ item.qty }}</span>
                      <button type="button" (click)="changeCartQty(item, 1)" [disabled]="item.qty >= item.available" aria-label="Agregar una unidad">+</button>
                    </div>
                    <button type="button" class="btn-icon" (click)="removeFromCart(item)" title="Quitar" aria-label="Quitar del carrito">🗑️</button>
                  </div>
                </li>
              }
            </ul>
            <div class="cart-total">
              <span>Total estimado:</span>
              <strong>\${{ cartTotal() | number }}</strong>
              @if (cartHasUnpriced()) { <small class="warn">⚠ Hay cartas sin precio, consulta al vendedor.</small> }
            </div>
            <div class="buyer-form">
              <h4>Datos para contacto</h4>
              <div class="buyer-grid">
                <label>
                  <span>Nombre *</span>
                  <input type="text" [(ngModel)]="buyerName" maxlength="100" placeholder="Tu nombre" />
                </label>
                <label>
                  <span>WhatsApp *</span>
                  <input type="text" [(ngModel)]="buyerWhatsapp" maxlength="30" placeholder="+56..." />
                </label>
                <label class="full">
                  <span>Nota (opcional)</span>
                  <textarea rows="2" [(ngModel)]="buyerNote" maxlength="800" placeholder="Ej: retiro en estación central"></textarea>
                </label>
              </div>
              @if (orderError) {
                <p class="order-error">{{ orderError }}</p>
              }
            </div>
            <div class="cart-actions">
              <button class="btn btn-primary" (click)="createOrder()" [disabled]="!canSubmitOrder()">
                {{ orderSubmitting ? '⏳ Creando pedido...' : '✅ Confirmar pedido' }}
              </button>
              @if (store()?.whatsapp) {
                <button class="btn btn-sm" (click)="sendWhatsApp()">📱 WhatsApp</button>
              }
              <button class="btn btn-sm" (click)="copyOrder()">📋 Copiar pedido</button>
              <button class="btn btn-sm" (click)="clearCart()">🗑️ Vaciar</button>
            </div>
          }
        </div>
      </div>
    }

    @if (preview(); as pc) {
      <div class="modal-overlay" (click)="closePreview()">
        <div class="modal" (click)="$event.stopPropagation()">
          <button class="close-btn" (click)="closePreview()">✕</button>
          @if (previewImageUrl(pc); as img) {
            <img [src]="img" [alt]="pc.name" class="detail-image" (error)="onPreviewImageError(pc, $event)" />
          }
          <div class="detail-info">
            <h2>{{ pc.name }}</h2>
            <p class="card-meta">{{ pc.card_number }}</p>
            @if (pc.description) { <p>{{ pc.description }}</p> }
            <app-tcg-price [cardName]="pc.name" [compact]="false" [showLink]="false" [showMarketPrice]="false"></app-tcg-price>
          </div>
        </div>
      </div>
    }
  </div>
  `,
  styles: [`
    :host { display: block; min-height: 100vh; background: #0f0f23; color: #c8c8da; }
    .tienda-container { max-width: 1400px; margin: 0 auto; padding: 1.5rem; }
    @media (max-width: 600px) { .tienda-container { padding: 1rem 0.65rem 2rem; } }
    .loading { padding: 2rem; text-align: center; color: #9ba3b4; }
    .error-state { padding: 3rem 1rem; text-align: center; }
    .error-state h2 { color: #e94560; }

    .store-header {
      display: flex; align-items: flex-start; gap: 1.2rem;
      padding: 1.5rem; margin-bottom: 1.5rem;
      background: linear-gradient(135deg, #16213e, #1a1a2e);
      border: 1px solid #2a3a4a; border-radius: 12px;
    }
    .store-avatar, .store-avatar-placeholder {
      width: 96px; height: 96px; border-radius: 14px;
      border: 2px solid #e94560; flex-shrink: 0;
    }
    .store-avatar { object-fit: cover; }
    .store-avatar-placeholder {
      background: #0f0f23; display: flex; align-items: center; justify-content: center; font-size: 2.6rem;
    }
    .store-info h1 { margin: 0; color: #fff;
      background: linear-gradient(90deg, #e94560, #fff); -webkit-background-clip: text;
      -webkit-text-fill-color: transparent; background-clip: text; }
    .store-meta { display: flex; gap: 1rem; flex-wrap: wrap; color: #9ba3b4; font-size: .9rem; margin: .35rem 0; }
    .store-bio { color: #c8c8da; margin: .35rem 0 .6rem; }
    .store-line { color: #9ba3b4; font-size: .85rem; margin: .2rem 0; }
    .store-line strong { color: #c8c8da; }
    .contact-row { display: flex; gap: .4rem; flex-wrap: wrap; margin: .5rem 0; }
    .contact-chip {
      display: inline-flex; align-items: center; gap: .4rem;
      padding: .35rem .7rem; border-radius: 6px; font-size: .82rem;
      background: #0f0f23; color: #c8c8da; border: 1px solid #2a3a4a;
      text-decoration: none;
    }
    .contact-chip.wa { color: #25d366; border-color: #25d366; }
    .contact-chip.ig { color: #e1306c; border-color: #e1306c; }
    .contact-chip.em { color: #4fc3f7; border-color: #4fc3f7; }
    .contact-chip.tr { color: #c89b3c; border-color: #c89b3c; }
    .contact-chip:hover { background: #16213e; }

    .tabs-bar { display: flex; gap: .5rem; margin: 0 0 1rem; border-bottom: 1px solid #2a3a4a; }
    .tab-btn {
      background: transparent; border: none; color: #9ba3b4;
      padding: .65rem 1.1rem; cursor: pointer; font-weight: 600;
      border-bottom: 2px solid transparent; display: inline-flex; align-items: center; gap: .4rem;
      font-size: .92rem;
    }
    .tab-btn.active { color: #e94560; border-bottom-color: #e94560; }
    .tab-btn:hover:not(:disabled):not(.active) { color: #fff; }
    .tab-btn:disabled { opacity: .4; cursor: not-allowed; }
    .tab-count {
      background: #0f0f23; border: 1px solid #2a3a4a; color: #c8c8da;
      padding: .1rem .45rem; border-radius: 10px; font-size: .75rem;
    }
    .empty-state { padding: 2rem; text-align: center; color: #9ba3b4; }
    .wishlist-qty { color: #ff7e7e !important; }

    /* ── Barra de filtros minimalista: búsqueda + botón "Filtros" ── */
    .filters-bar {
      position: relative;
      display: flex; gap: .6rem; margin-bottom: 1rem;
    }
    .filters-search {
      flex: 1 1 auto; min-width: 0;
      padding: .6rem .8rem; background: #111a2f; color: #c8c8da;
      border: 1px solid #2a3a4a; border-radius: 8px; font-size: .92rem;
    }
    .filters-search:focus { outline: none; border-color: #e94560; }
    .filters-toggle-btn {
      position: relative; flex: 0 0 auto; display: inline-flex; align-items: center; gap: .4rem;
      padding: .6rem 1rem; border-radius: 8px; border: 1px solid #2a3a4a;
      background: #111a2f; color: #c8c8da; font-size: .88rem; font-weight: 600; cursor: pointer;
    }
    .filters-toggle-btn:hover { border-color: #4a5a6a; }
    .filters-toggle-btn.active { border-color: #e94560; color: #e94560; background: rgba(233, 69, 96, .1); }
    .filters-toggle-btn .ft-icon { font-size: .85rem; }
    .filter-badge {
      position: absolute; top: -6px; right: -6px;
      min-width: 16px; height: 16px; padding: 0 3px; border-radius: 8px;
      background: #e94560; color: #fff; font-size: .65rem; font-weight: 700;
      display: flex; align-items: center; justify-content: center;
    }

    /* ── Drawer / dropdown de filtros: glassmorphism (fondo translúcido + blur real) ── */
    .filters-backdrop {
      position: fixed; inset: 0; z-index: 1100;
      background: rgba(0, 0, 0, .5);
      backdrop-filter: blur(4px);
      -webkit-backdrop-filter: blur(4px);
      animation: filters-fade-in .18s ease-out;
    }
    .filters-drawer {
      position: absolute; right: 0; margin-top: -.4rem; z-index: 1101;
      width: min(380px, 92vw); max-height: 75vh; overflow-y: auto;
      background-color: rgba(18, 20, 28, 0.75);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 14px;
      box-shadow: 0 20px 50px rgba(0, 0, 0, .5);
      animation: filters-drawer-in .2s ease-out;
    }
    @keyframes filters-fade-in { from { opacity: 0; } to { opacity: 1; } }
    @keyframes filters-drawer-in {
      from { opacity: 0; transform: translateY(-8px); }
      to { opacity: 1; transform: translateY(0); }
    }
    @keyframes filters-drawer-mobile-in {
      from { opacity: 0; transform: translateY(16px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .filters-drawer-head {
      display: flex; align-items: center; justify-content: space-between;
      padding: .9rem 1rem; border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
    .filters-drawer-head h3 { margin: 0; color: #fff; font-size: 1rem; font-weight: 700; }
    .filters-drawer-head .close-btn {
      background: rgba(255, 255, 255, .06); border: 1px solid rgba(255, 255, 255, .1);
      color: #c8c8da; width: 28px; height: 28px; border-radius: 50%; cursor: pointer;
      transition: background .15s, color .15s;
    }
    .filters-drawer-head .close-btn:hover { background: rgba(233, 69, 96, .18); color: #ff9aa9; }
    .filters-drawer-body { padding: .9rem 1rem; display: flex; flex-direction: column; gap: .9rem; }
    .filter-group { display: flex; flex-direction: column; gap: .4rem; }
    .filter-group + .filter-group { padding-top: .9rem; border-top: 1px solid rgba(255, 255, 255, 0.06); }
    .filter-group-label {
      color: #9ba3b4; font-size: .72rem; font-weight: 700; text-transform: uppercase; letter-spacing: .03em;
    }
    .filter-group input, .filter-group select {
      padding: .5rem .7rem; background: rgba(255, 255, 255, 0.04); color: #e5ebf7;
      border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; font-size: .88rem;
      transition: border-color .15s, background .15s;
    }
    .filter-group input:focus, .filter-group select:focus {
      outline: none; border-color: #e94560; background: rgba(255, 255, 255, 0.06);
    }

    .color-chip-row { display: flex; flex-wrap: wrap; gap: .4rem; align-items: center; }
    .color-chip {
      padding: .3rem .75rem; border-radius: 999px; font-size: .8rem; font-weight: 600;
      background: rgba(255, 255, 255, 0.04); color: var(--c, #c8c8da); border: 1px solid var(--c, rgba(255, 255, 255, 0.14));
      cursor: pointer; transition: background .15s, transform .15s;
    }
    .color-chip:hover { transform: translateY(-1px); }
    .color-chip.active { background: var(--c, #e94560); color: #0f0f23; }
    .clear-colors { background: none; border: none; color: #e94560; font-size: .78rem; cursor: pointer; }

    .stats-row { display: flex; gap: .6rem; flex-wrap: wrap; }
    .stats-row label { flex: 1 1 80px; display: flex; flex-direction: column; gap: .25rem; color: #9ba3b4; font-size: .78rem; }
    .stats-row input { width: 100%; }

    .price-range-row { display: flex; align-items: center; gap: .5rem; color: #9ba3b4; }
    .price-range-row input { flex: 1 1 0; min-width: 0; }

    .filters-drawer-actions {
      display: flex; gap: .5rem; padding: .9rem 1rem;
      border-top: 1px solid rgba(255, 255, 255, 0.08);
    }
    .filters-drawer-actions .btn {
      flex: 1 1 0; text-align: center; border-radius: 8px;
      transition: background .15s, border-color .15s, transform .15s;
    }
    .filters-drawer-actions .btn:not(.btn-primary) {
      background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.12); color: #c8c8da;
    }
    .filters-drawer-actions .btn:not(.btn-primary):hover:not(:disabled) {
      background: rgba(255, 255, 255, 0.08); border-color: rgba(255, 255, 255, 0.22);
    }
    .filters-drawer-actions .btn-primary:hover:not(:disabled) { transform: translateY(-1px); }

    .results-count { color: #9ba3b4; font-size: .9rem; margin-bottom: 1rem; }

    .cards-grid {
      display: grid; gap: 1rem;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    }
    .store-card { background: #16213e; border: 1px solid #2a3a4a; border-radius: 10px; overflow: hidden; }
    .store-card.in-cart { border-color: #25d366; box-shadow: inset 0 0 0 1px rgba(37, 211, 102, .35); }
    .card-image { position: relative; aspect-ratio: 5/7; background: #0f0f23; cursor: pointer; overflow: hidden; }
    .card-image img { width: 100%; height: 100%; object-fit: cover; transition: transform .2s; }
    .card-image:hover img { transform: scale(1.04); }
    .img-fallback {
      width: 100%; height: 100%; display: flex; align-items: center; justify-content: center;
      color: #6b7280; font-weight: 700;
    }
    .foil-badge {
      position: absolute; bottom: 8px; left: 8px;
      background: linear-gradient(135deg, #4fc3f7, #e94560);
      color: #fff; padding: .2rem .5rem; border-radius: 4px;
      font-size: .7rem; font-weight: 700;
    }
    .card-body { padding: .55rem .65rem .7rem; }
    .card-body h4 {
      margin: 0 0 .25rem; font-size: .95rem; color: #fff;
      display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
      overflow: hidden; text-overflow: ellipsis;
    }
    .card-meta { color: #9ba3b4; font-size: .78rem; }
    .price-row { display: flex; justify-content: space-between; align-items: center; margin-top: .5rem; }
    .price { color: #e94560; font-weight: 800; font-size: 1.05rem; }
    .qty { color: #4fc3f7; font-size: .85rem; }

    .btn { padding: .4rem .8rem; border: 1px solid #2a3a4a; background: transparent; color: #c8c8da;
      border-radius: 6px; cursor: pointer; font-weight: 600; text-decoration: none; display: inline-block; }
    .btn:hover:not(:disabled) { background: #1e2d3d; }
    .btn:disabled { opacity: .5; cursor: not-allowed; }
    .btn-sm { padding: .35rem .65rem; font-size: .85rem; }
    .btn-primary { background: #e94560; border-color: #e94560; color: #fff; }
    .infinite-sentinel { width: 100%; height: 1px; margin-top: .5rem; }

    .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.85);
      display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 1rem; }
    .modal { background: #16213e; border: 1px solid #2a3a4a; border-radius: 14px;
      max-width: 720px; width: 100%; max-height: 90vh; overflow-y: auto;
      display: grid; grid-template-columns: 1fr 1.2fr; position: relative; }
    @media (max-width: 640px) { .modal { grid-template-columns: 1fr; } }
    .detail-image { width: 100%; height: auto; border-radius: 14px 0 0 14px; }
    .detail-info { padding: 1.4rem; color: #c8c8da; }
    .detail-info h2 { margin: 0 0 .5rem; color: #fff; }
    .close-btn { position: absolute; top: .5rem; right: .5rem;
      background: rgba(15,15,35,.85); border: 1px solid #2a3a4a; color: #fff;
      width: 32px; height: 32px; border-radius: 50%; cursor: pointer; z-index: 2; }
    .close-btn:hover { background: #e94560; border-color: #e94560; }

    .btn-tcg {
      display: inline-flex; align-items: center; gap: .4rem;
      margin-top: .8rem; padding: .55rem 1rem; border-radius: 8px;
      background: linear-gradient(135deg, #1a6bc4, #0d4a8e); border: 1px solid #2980d9;
      color: #fff; font-weight: 700; font-size: .9rem; text-decoration: none;
      transition: background .2s, transform .15s;
    }
    .btn-tcg:hover { background: linear-gradient(135deg, #2980d9, #1a6bc4); transform: translateY(-1px); }

    /* Cart */
    .add-fab {
      position: absolute; right: 8px; bottom: 8px; z-index: 2;
      width: 32px; height: 32px; border-radius: 50%;
      border: 1px solid rgba(255, 255, 255, .28);
      background: rgba(15, 15, 35, .72);
      color: #fff; font-size: 1.1rem; font-weight: 700; line-height: 1;
      display: flex; align-items: center; justify-content: center;
      cursor: pointer; transition: background .15s, border-color .15s, transform .15s;
    }
    .add-fab:hover:not(:disabled) { background: #e94560; border-color: #e94560; transform: scale(1.08); }
    .add-fab:disabled { opacity: .55; cursor: not-allowed; }

    /* Cápsula de cantidad [-] [qty] [+], reemplaza al add-fab cuando ya hay unidades en el carrito. */
    .qty-capsule {
      position: absolute; right: 8px; bottom: 8px; z-index: 2;
      display: flex; align-items: center; gap: .3rem;
      padding: .2rem .3rem;
      border-radius: 999px;
      background: rgba(20, 20, 25, 0.85);
      backdrop-filter: blur(6px);
      border: 1px solid rgba(255, 255, 255, .15);
      transition: all .2s ease;
    }
    .qty-btn {
      width: 22px; height: 22px; border-radius: 50%; flex-shrink: 0;
      border: none; background: rgba(255, 255, 255, .08);
      color: #fff; font-size: .95rem; font-weight: 700; line-height: 1;
      display: flex; align-items: center; justify-content: center;
      cursor: pointer; transition: background .15s, transform .15s;
    }
    .qty-btn:hover:not(:disabled) { background: #e94560; transform: scale(1.08); }
    .qty-btn:disabled { opacity: .4; cursor: not-allowed; transform: none; }
    .qty-value {
      min-width: 14px; text-align: center;
      color: #fff; font-size: .85rem; font-weight: 700;
    }
    .cart-fab {
      position: fixed; bottom: 1.25rem; right: 1.25rem; z-index: 999;
      padding: .85rem 1.3rem; border-radius: 999px; border: none;
      background: linear-gradient(135deg, #e94560, #c89b3c); color: #fff;
      font-weight: 700; cursor: pointer; box-shadow: 0 6px 18px rgba(0,0,0,.4);
      font-size: .95rem;
    }
    .cart-fab:hover { transform: translateY(-2px); }
    .cart-modal {
      background: #16213e; border: 1px solid #2a3a4a; border-radius: 14px;
      max-width: 640px; width: 100%; max-height: 90vh; overflow-y: auto;
      padding: 1.2rem; position: relative;
    }
    .cart-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: .8rem; }
    .cart-head h3 { margin: 0; color: #fff; }
    .empty-cart { color: #9ba3b4; text-align: center; padding: 1rem; }
    .cart-list { list-style: none; padding: 0; margin: 0 0 .8rem; display: flex; flex-direction: column; gap: .55rem; }
    .cart-item {
      display: grid;
      grid-template-columns: 52px 1fr auto;
      grid-template-areas: "thumb name controls" "thumb price controls";
      column-gap: .7rem; row-gap: .15rem;
      align-items: center; padding: .55rem .6rem; background: #0f0f23;
      border: 1px solid #2a3a4a; border-radius: 8px;
    }
    .cart-item-thumb { grid-area: thumb; width: 52px; height: 73px; object-fit: cover; border-radius: 5px; }
    .cart-item-name { grid-area: name; color: #fff; font-size: .9rem; }
    .cart-item-price { grid-area: price; display: flex; align-items: baseline; gap: .4rem; }
    .cart-item-price strong { color: #e94560; font-size: .92rem; }
    .cart-item-price small { color: #9ba3b4; font-size: .74rem; }
    .cart-item-controls {
      grid-area: controls; display: flex; flex-direction: column;
      align-items: flex-end; gap: .35rem;
    }
    .cart-qty { display: flex; align-items: center; gap: .3rem; }
    .cart-qty button {
      width: 26px; height: 26px; border-radius: 4px;
      background: #1e2d3d; color: #fff; border: 1px solid #2a3a4a; cursor: pointer;
    }
    .cart-qty button:disabled { opacity: .4; cursor: not-allowed; }
    .btn-icon { background: transparent; border: none; cursor: pointer; font-size: 1rem; }
    .cart-total {
      display: flex; align-items: center; justify-content: space-between;
      flex-wrap: wrap; gap: .4rem; padding: .65rem 0; border-top: 1px dashed #2a3a4a;
      color: #c8c8da;
    }
    .cart-total strong { color: #e94560; font-size: 1.1rem; }
    .cart-total .warn { width: 100%; color: #c89b3c; font-size: .8rem; }
    .buyer-form {
      margin-top: .75rem;
      padding: .7rem;
      border-radius: 8px;
      border: 1px solid #2a3a4a;
      background: #0f0f23;
    }
    .buyer-form h4 { margin: 0 0 .55rem; color: #fff; font-size: .92rem; }
    .buyer-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: .5rem;
    }
    .buyer-grid label {
      display: flex;
      flex-direction: column;
      gap: .25rem;
      color: #c8c8da;
      font-size: .82rem;
    }
    .buyer-grid label.full { grid-column: 1 / -1; }
    .buyer-grid input, .buyer-grid textarea {
      padding: .5rem .65rem;
      border-radius: 8px;
      border: 1px solid rgba(255, 255, 255, .1);
      background: rgba(255, 255, 255, .03);
      color: #e5ebf7;
      font-size: .9rem;
      font-family: inherit;
    }
    .buyer-grid input:focus, .buyer-grid textarea:focus {
      outline: none;
      border-color: #e94560;
    }
    .order-error {
      margin: .5rem 0 0;
      color: #ff9aa9;
      font-size: .83rem;
    }
    .order-success {
      margin: 0 0 1rem;
      padding: .65rem .85rem;
      border-radius: 8px;
      border: 1px solid rgba(79, 195, 247, 0.35);
      background: rgba(79, 195, 247, 0.12);
      color: #cbeeff;
      font-size: .9rem;
    }
    .cart-actions { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: .6rem; }
    .cart-actions .btn-primary { flex: 1 1 100%; }

    /* ── Mobile ── */
    @media (max-width: 768px) {
      .contact-row { gap: .5rem; }
      .contact-chip {
        width: 40px; height: 40px; padding: 0; border-radius: 50%;
        justify-content: center; background: rgba(255, 255, 255, .05);
        border-color: rgba(255, 255, 255, .12); color: #fff;
      }
      .contact-chip.wa, .contact-chip.ig, .contact-chip.em, .contact-chip.tr {
        color: #fff; border-color: rgba(255, 255, 255, .12);
      }
      .contact-chip .ci-icon { font-size: 1.05rem; }
      .contact-chip .ci-label {
        position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
        overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0;
      }

      .filters-toggle-btn .ft-text { display: none; }
      .filters-drawer {
        position: fixed; inset: 0; right: 0; margin-top: 0;
        width: 100%; max-height: 100%; border-radius: 0;
        animation: filters-drawer-mobile-in .22s ease-out;
      }
      .filters-drawer-actions {
        position: sticky; bottom: 0;
        background-color: rgba(18, 20, 28, 0.9);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
      }
      .cards-grid { grid-template-columns: repeat(auto-fit, minmax(96px, 1fr)); gap: .55rem; }
      .card-image img {
        object-fit: contain;
        background: #0b0b1a;
      }
      .detail-image {
        max-height: 58vh;
        width: auto;
        max-width: 100%;
        margin: 0 auto;
        display: block;
        border-radius: 14px;
      }
      .card-body { padding: .5rem .55rem .6rem; }
      .card-body h4 { font-size: .88rem; }
      .price { font-size: .95rem; }
      .add-fab { width: 30px; height: 30px; font-size: 1rem; right: 6px; bottom: 6px; }
      .qty-capsule { right: 6px; bottom: 6px; gap: .25rem; padding: .15rem .25rem; }
      .qty-btn { width: 20px; height: 20px; font-size: .85rem; }
      .qty-value { font-size: .78rem; }
      .cart-fab {
        bottom: calc(4.8rem + env(safe-area-inset-bottom, 0));
        right: .9rem; padding: .75rem 1.1rem; font-size: .9rem;
      }
      .cart-modal { padding: .9rem; max-height: 88vh; }
      .cart-item { padding: .45rem .5rem; }
      .cart-item-thumb { width: 44px; height: 62px; }
      .cart-item { grid-template-columns: 44px 1fr auto; }
    }
    @media (max-width: 480px) {
      .cards-grid { grid-template-columns: repeat(auto-fit, minmax(84px, 1fr)); gap: .45rem; }
      .card-body h4 { font-size: .76rem; }
      .card-meta { display: none; }
      .price { font-size: .82rem; }
      .qty { font-size: .74rem; }
      .add-fab { width: 26px; height: 26px; font-size: .9rem; }
      .qty-capsule { gap: .2rem; padding: .12rem .2rem; }
      .qty-btn { width: 18px; height: 18px; font-size: .78rem; }
      .qty-value { font-size: .7rem; min-width: 10px; }
    }
  `],
})
export class RiftboundTiendaComponent implements OnInit, AfterViewInit, OnDestroy {
  private readonly rb = inject(RiftboundService);
  readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);
  private readonly cdr = inject(ChangeDetectorRef);

  token = '';
  loading = signal(false);
  errorMsg = signal<string | null>(null);
  store = signal<RiftboundPublicBinderProfile | null>(null);
  entries = signal<RiftboundCollectionEntry[]>([]);
  count = signal(0);
  page = signal(1);
  hasMore = signal(false);
  preview = signal<RiftboundCardLite | null>(null);
  previewImageStep = signal(0);
  private storeSentinelRef?: ElementRef<HTMLElement>;
  private storeObserver?: IntersectionObserver;
  private contentScrollEl: HTMLElement | null = null;

  @ViewChild('storeSentinel')
  set storeSentinelSetter(el: ElementRef<HTMLElement> | undefined) {
    this.storeSentinelRef = el;
    this.setupStoreObserver();
  }

  // Cart
  cart = signal<RiftboundCartItem[]>([]);
  showCart = signal(false);
  buyerName = '';
  buyerWhatsapp = '';
  buyerNote = '';
  orderSubmitting = false;
  orderError = '';
  createdOrderId: number | null = null;

  // Tabs / wishlist
  activeTab = signal<'store' | 'wishlist'>('store');
  wishlist = signal<RiftboundWishlistEntry[]>([]);
  wishlistLoading = signal(false);
  wishlistLoaded = signal(false);
  wishlistSearch = '';

  search = '';
  ftype = '';
  fcondition = '';
  ffoil: '' | '0' | '1' = '';
  priceMin: number | null = null;
  priceMax: number | null = null;
  ordering = '-price';
  filtersOpen = signal(false);
  fcolors = signal(new Set<RiftboundColor>());
  fenergy: number | null = null;
  fpower: number | null = null;
  fmight: number | null = null;

  readonly riftboundColors = RIFTBOUND_COLORS;
  readonly cardTypes = RIFTBOUND_CARD_TYPES;

  toggleColor(code: RiftboundColor) {
    const next = new Set(this.fcolors());
    if (next.has(code)) next.delete(code); else next.add(code);
    this.fcolors.set(next);
  }

  clearColors() { this.fcolors.set(new Set()); }

  activeFilterCount(): number {
    let n = 0;
    if (this.ftype) n++;
    if (this.ffoil) n++;
    if (this.priceMin != null) n++;
    if (this.priceMax != null) n++;
    if (this.ordering !== '-price') n++;
    if (this.fcolors().size > 0) n++;
    if (this.fenergy != null) n++;
    if (this.fpower != null) n++;
    if (this.fmight != null) n++;
    return n;
  }

  cartCount() { return this.cart().reduce((s, c) => s + c.qty, 0); }
  cartTotal() { return this.cart().reduce((s, c) => s + (c.price || 0) * c.qty, 0); }
  cartHasUnpriced() { return this.cart().some(c => c.price == null); }
  canSubmitOrder(): boolean {
    return this.cart().length > 0
      && !this.orderSubmitting
      && !!this.buyerName.trim()
      && !!this.buyerWhatsapp.trim();
  }
  inCart(entryId: number): number { return this.cart().find(c => c.entryId === entryId)?.qty || 0; }

  ngOnInit() {
    this.token = this.route.snapshot.paramMap.get('token') || '';
    const dt = this.route.snapshot.data?.['defaultTab'];
    if (dt === 'wishlist') this.activeTab.set('wishlist');
    this.loadCart();
    this.buyerName = this.auth.user()?.username || '';
    this.reload();
    if (this.activeTab() === 'wishlist') this.reloadWishlist();
  }

  ngAfterViewInit() {
    this.setupStoreObserver();
    this.attachContentScrollListener();
    this.tryInfiniteScrollFallback();
  }

  ngOnDestroy() {
    this.storeObserver?.disconnect();
    this.detachContentScrollListener();
  }

  @HostListener('window:scroll')
  onWindowScroll() { this.tryInfiniteScrollFallback(); }

  @HostListener('window:resize')
  onWindowResize() { this.tryInfiniteScrollFallback(); }

  reload() {
    this.page.set(1);
    this.entries.set([]);
    this.hasMore.set(false);
    this.fetchStorePage();
  }

  applyFilters() {
    this.reload();
  }

  clearFilters() {
    this.search = '';
    this.ftype = '';
    this.ffoil = '';
    this.priceMin = null;
    this.priceMax = null;
    this.ordering = '-price';
    this.fcolors.set(new Set());
    this.fenergy = null;
    this.fpower = null;
    this.fmight = null;
    this.reload();
  }

  loadMoreStore() {
    if (this.activeTab() !== 'store' || this.loading() || !this.hasMore()) return;
    this.page.update(p => p + 1);
    this.fetchStorePage(true);
  }

  private fetchStorePage(append = false) {
    this.loading.set(true);
    this.errorMsg.set(null);
    this.rb.getPublicStore(this.token, {
      search: this.search || undefined,
      type: this.ftype || undefined,
      condition: this.fcondition || undefined,
      foil: this.ffoil || undefined,
      price_min: this.priceMin ?? undefined,
      price_max: this.priceMax ?? undefined,
      colors: this.fcolors().size ? Array.from(this.fcolors()) : undefined,
      energy: this.fenergy ?? undefined,
      power: this.fpower ?? undefined,
      might: this.fmight ?? undefined,
      ordering: this.ordering,
      page: this.page(),
    }).subscribe({
      next: res => {
        if (append) {
          this.entries.update(curr => [...curr, ...res.results]);
        } else {
          this.entries.set(res.results);
        }
        this.count.set(res.count);
        this.hasMore.set(!!res.next);
        this.store.set(res.store);
        this.loading.set(false);
        this.syncCartAvailability();
        this.cdr.markForCheck();
        setTimeout(() => {
          this.setupStoreObserver();
          this.tryInfiniteScrollFallback();
        });
      },
      error: err => {
        this.loading.set(false);
        this.errorMsg.set(err?.error?.detail || 'No se pudo cargar la tienda.');
        this.cdr.markForCheck();
      },
    });
  }

  private setupStoreObserver() {
    if (typeof IntersectionObserver === 'undefined') return;
    this.storeObserver?.disconnect();
    if (this.activeTab() !== 'store') return;
    const el = this.storeSentinelRef?.nativeElement;
    if (!el) return;
    this.storeObserver = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          this.loadMoreStore();
          break;
        }
      }
    }, { rootMargin: '320px 0px' });
    this.storeObserver.observe(el);
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

  private tryInfiniteScrollFallback() {
    if (!this.isNearPageBottom()) return;
    if (this.activeTab() === 'store') this.loadMoreStore();
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

  cleanWa(v: string): string { return v.replace(/[^0-9]/g, ''); }
  cleanHandle(v: string): string { return v.replace(/^@/, '').trim(); }

  entryCardImage(entry: RiftboundCollectionEntry): string {
    const card = entry?.card_data;
    if (!card) return '';

    // Foil shares the same card art; prefer canonical card URLs first.
    if (entry.is_foil) {
      return card.image_url || card.image || card.image_url_small || card.cdn_image_url || '';
    }
    return card.image || card.image_url || card.image_url_small || card.cdn_image_url || '';
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

  private cloudinaryFetchProxy(url: string | null | undefined): string {
    const raw = (url || '').trim();
    if (!raw) return '';
    return `https://res.cloudinary.com/daobfx9yb/image/fetch/f_auto,q_auto/${encodeURIComponent(raw)}`;
  }

  private cloudinaryFetchVariants(url: string | null | undefined): string[] {
    const raw = (url || '').trim();
    if (!raw) return [];
    const urls = this.imageUrlVariants(raw);
    const proxied = urls.map((candidate) => this.cloudinaryFetchProxy(candidate)).filter(Boolean);
    return Array.from(new Set(proxied));
  }

  cardImageFallbacks(card: RiftboundCardLite | null | undefined): string[] {
    if (!card) return [];
    const candidates = [
      ...this.imageUrlVariants(card.cdn_image_url),
      ...this.imageUrlVariants(card.image),
      ...this.imageUrlVariants(card.image_url),
      ...this.imageUrlVariants(card.image_url_small),
      ...this.cloudinaryFetchVariants(card.image),
      ...this.cloudinaryFetchVariants(card.image_url),
      ...this.cloudinaryFetchVariants(card.image_url_small),
    ].filter(Boolean);
    return Array.from(new Set(candidates));
  }

  openPreview(card: RiftboundCardLite) {
    this.preview.set(card);
    this.previewImageStep.set(0);
  }

  closePreview() {
    this.preview.set(null);
    this.previewImageStep.set(0);
  }

  previewImageUrl(card: RiftboundCardLite | null | undefined): string {
    if (!card) return '';
    const candidates = this.cardImageFallbacks(card);
    if (!candidates.length) return '';
    const step = Math.min(this.previewImageStep(), candidates.length - 1);
    return candidates[step] || '';
  }

  onPreviewImageError(card: RiftboundCardLite | null | undefined, event: Event) {
    if (!card) return;
    const candidates = this.cardImageFallbacks(card);
    if (!candidates.length) return;

    const nextStep = this.previewImageStep() + 1;
    if (nextStep >= candidates.length) return;

    this.previewImageStep.set(nextStep);
    const img = event.target as HTMLImageElement | null;
    if (img) img.src = candidates[nextStep];
  }

  // ── Compartir imagen estilo CardIndex ──
  sellerHandle(): string {
    const s = this.store();
    return s?.display_name || (s?.username ? '@' + s.username : 'Tu tienda');
  }
  shareContactLine(): string {
    return `¿Tienes alguna? Escríbeme · ${this.sellerHandle()}`;
  }
  shareSellingContactLine(): string {
    return `Escríbeme para comprar · ${this.sellerHandle()}`;
  }
  shareStoreItems(): ShareImageItem[] {
    return this.entries().slice(0, 20).map(e => {
      const imageCandidates = this.cardImageFallbacks(e.card_data);
      return {
        name: e.card_data.name || '',
        image: this.entryCardImage(e) || imageCandidates[0] || '',
        imageCandidates,
        quantity: e.selling_quantity || 1,
        foil: !!e.is_foil,
        price: e.price ?? null,
      };
    });
  }
  shareWishlistItems(): ShareImageItem[] {
    return this.wishlist().slice(0, 20).map(w => {
      const imageCandidates = this.cardImageFallbacks(w.card_data);
      return {
        name: w.card_data.name || '',
        image: imageCandidates[0] || '',
        imageCandidates,
        quantity: w.desired_quantity || 1,
        foil: false,
        price: null,
      };
    });
  }

  // ── Cart ──
  private cartKey(): string { return `riftbound-tienda-cart::${this.token}`; }

  loadCart() {
    try {
      const raw = localStorage.getItem(this.cartKey());
      this.cart.set(raw ? JSON.parse(raw) : []);
    } catch { this.cart.set([]); }
  }

  saveCart() {
    try { localStorage.setItem(this.cartKey(), JSON.stringify(this.cart())); } catch {}
  }

  syncCartAvailability() {
    const entries = this.entries();
    const updated = this.cart().map(ci => {
      const e = entries.find(x => x.id === ci.entryId);
      return e ? { ...ci, available: e.selling_quantity } : ci;
    });
    this.cart.set(updated);
    this.saveCart();
  }

  addToCart(entry: RiftboundCollectionEntry, ev: MouseEvent) {
    ev.stopPropagation();
    const list = [...this.cart()];
    const existing = list.find(c => c.entryId === entry.id);
    if (existing) {
      if (existing.qty < entry.selling_quantity) existing.qty++;
    } else {
      list.push({
        entryId: entry.id,
        cardId: entry.card_data.id,
        name: entry.card_data.name,
        price: entry.price ?? null,
        qty: 1,
        available: entry.selling_quantity,
        image: this.entryCardImage(entry),
      });
    }
    this.cart.set(list);
    this.saveCart();
    this.createdOrderId = null;
    this.orderError = '';
    this.cdr.markForCheck();
  }

  removeFromCart(item: RiftboundCartItem) {
    this.cart.set(this.cart().filter(c => c.entryId !== item.entryId));
    this.saveCart();
  }

  /** Resta una unidad directamente desde la tarjeta de la tienda (cápsula +/-). */
  decreaseFromCart(entry: RiftboundCollectionEntry, ev: MouseEvent) {
    ev.stopPropagation();
    const item = this.cart().find(c => c.entryId === entry.id);
    if (!item) return;
    this.changeCartQty(item, -1);
  }

  changeCartQty(item: RiftboundCartItem, delta: number) {
    const newQty = item.qty + delta;
    if (newQty <= 0) { this.removeFromCart(item); return; }
    if (newQty > item.available) return;
    this.cart.set(this.cart().map(c => c.entryId === item.entryId ? { ...c, qty: newQty } : c));
    this.saveCart();
  }

  clearCart() { this.cart.set([]); this.saveCart(); }

  private syncCartWithLatestStock(latestEntries: RiftboundCollectionEntry[]) {
    const latestByEntry = new Map<number, RiftboundCollectionEntry>();
    for (const entry of latestEntries) latestByEntry.set(entry.id, entry);

    const removed: string[] = [];
    const reduced: string[] = [];
    const nextCart: RiftboundCartItem[] = [];

    for (const item of this.cart()) {
      const latest = latestByEntry.get(item.entryId);
      const available = latest?.selling_quantity ?? 0;

      if (available <= 0) {
        removed.push(item.name);
        continue;
      }

      const nextQty = Math.min(item.qty, available);
      if (nextQty < item.qty) {
        reduced.push(`${item.name} (${item.qty}->${nextQty})`);
      }

      nextCart.push({
        ...item,
        name: latest?.card_data?.name || item.name,
        image: latest?.card_data?.image || item.image,
        price: latest?.price ?? item.price,
        available,
        qty: nextQty,
      });
    }

    return { nextCart, removed, reduced };
  }

  buildOrderText(): string {
    const s = this.store();
    const lines = [`Hola ${s?.display_name || s?.username}! Quiero comprar (Riftbound):`];
    for (const c of this.cart()) {
      const priceTxt = c.price != null ? `— $${c.price.toLocaleString('es-CL')} c/u` : '— precio?';
      lines.push(`• ${c.qty}x ${c.name} ${priceTxt}`);
    }
    if (!this.cartHasUnpriced()) {
      lines.push('');
      lines.push(`Total: $${this.cartTotal().toLocaleString('es-CL')}`);
    }
    lines.push('');
    lines.push(`(Pedido desde tienda Deckshado · Riftbound)`);
    return lines.join('\n');
  }

  sendWhatsApp() {
    const waUrl = this.buildWhatsAppOrderUrl();
    if (!waUrl) return;
    window.open(waUrl, '_blank');
  }

  private buildWhatsAppOrderUrl(orderId?: number): string | null {
    const wa = this.store()?.whatsapp;
    if (!wa) return null;
    const number = wa.replace(/[^0-9]/g, '');
    if (!number) return null;
    const orderSuffix = orderId ? `\n\nPedido #${orderId}` : '';
    const text = encodeURIComponent(`${this.buildOrderText()}${orderSuffix}`);
    return `https://wa.me/${number}?text=${text}`;
  }

  copyOrder() {
    navigator.clipboard.writeText(this.buildOrderText());
  }

  createOrder() {
    if (!this.canSubmitOrder()) return;
    this.orderSubmitting = true;
    this.orderError = '';
    const pendingWhatsApp = this.store()?.whatsapp ? window.open('about:blank', '_blank') : null;

    const entryIds = Array.from(new Set(this.cart().map(c => c.entryId)));
    this.rb.getPublicStore(this.token, {
      entry_ids: entryIds,
      page_size: Math.max(40, entryIds.length),
      ordering: 'id',
    }).subscribe({
      next: (res) => {
        const { nextCart, removed, reduced } = this.syncCartWithLatestStock(res.results);
        this.cart.set(nextCart);
        this.saveCart();

        if (removed.length > 0 || reduced.length > 0 || nextCart.length === 0) {
          const msg: string[] = ['Actualizamos el stock antes de enviar el pedido.'];
          if (removed.length > 0) {
            msg.push(`Sin stock: ${removed.slice(0, 3).join(', ')}${removed.length > 3 ? '...' : ''}.`);
          }
          if (reduced.length > 0) {
            msg.push(`Cantidades ajustadas: ${reduced.slice(0, 3).join(', ')}${reduced.length > 3 ? '...' : ''}.`);
          }
          if (nextCart.length === 0) {
            msg.push('El carrito quedó sin items disponibles.');
          } else {
            msg.push('Revisa el carrito y confirma nuevamente.');
          }

          this.orderSubmitting = false;
          this.orderError = msg.join(' ');
          if (pendingWhatsApp && !pendingWhatsApp.closed) pendingWhatsApp.close();
          this.reload();
          this.cdr.markForCheck();
          return;
        }

        const payload: RiftboundStoreOrderCreatePayload = {
          buyer_name: this.buyerName.trim(),
          buyer_whatsapp: this.buyerWhatsapp.trim(),
          buyer_note: (this.buyerNote || '').trim(),
          items: nextCart.map((item) => ({ entry_id: item.entryId, quantity: item.qty })),
        };

        this.rb.createPublicStoreOrder(this.token, payload).subscribe({
          next: (order) => {
            this.createdOrderId = order.id;
            const waUrl = this.buildWhatsAppOrderUrl(order.id);
            if (waUrl) {
              if (pendingWhatsApp && !pendingWhatsApp.closed) pendingWhatsApp.location.href = waUrl;
              else window.open(waUrl, '_blank');
            } else if (pendingWhatsApp && !pendingWhatsApp.closed) {
              pendingWhatsApp.close();
            }
            this.orderSubmitting = false;
            this.clearCart();
            this.showCart.set(false);
            this.reload();
            this.cdr.markForCheck();
          },
          error: (err) => {
            this.orderSubmitting = false;
            this.orderError = err?.error?.detail || 'No se pudo crear el pedido. Revisa stock y vuelve a intentar.';
            if (pendingWhatsApp && !pendingWhatsApp.closed) pendingWhatsApp.close();
            this.cdr.markForCheck();
          },
        });
      },
      error: (err) => {
        this.orderSubmitting = false;
        this.orderError = err?.error?.detail || 'No se pudo validar stock actualizado. Intenta nuevamente.';
        if (pendingWhatsApp && !pendingWhatsApp.closed) pendingWhatsApp.close();
        this.cdr.markForCheck();
      },
    });
  }

  // ── TCGPlayer ──
  private readonly tcgSetSlugs: Record<string, string> = {
    OGN: 'origins',
    UNL: 'unleashed',
    OGS: 'proving-grounds',
    SFD: 'spiritforged',
    ARC: 'product',
  };

  getTcgPlayerUrl(card: RiftboundCardLite): string {
    const setCode = card.card_number?.split('-')[0]?.toUpperCase() || '';
    const setSlug = this.tcgSetSlugs[setCode] || 'product';
    const q = encodeURIComponent(card.name);
    return `https://www.tcgplayer.com/search/riftbound-league-of-legends-trading-card-game/${setSlug}?q=${q}&Language=English`;
  }

  // ── Tabs / Wishlist ──
  switchTab(tab: 'store' | 'wishlist') {
    if (this.activeTab() === tab) return;
    this.activeTab.set(tab);
    if (tab === 'wishlist' && !this.wishlistLoaded()) this.reloadWishlist();
    if (tab === 'store') {
      setTimeout(() => {
        this.setupStoreObserver();
        this.tryInfiniteScrollFallback();
      });
    }
  }

  reloadWishlist() {
    this.wishlistLoading.set(true);
    this.rb.getPublicWishlist(this.token, {
      search: this.wishlistSearch || undefined,
    }).subscribe({
      next: res => {
        this.wishlist.set(res.results);
        if (res.store) {
          this.store.set({ ...(this.store() || {} as any), ...res.store });
        }
        this.wishlistLoading.set(false);
        this.wishlistLoaded.set(true);
        this.cdr.markForCheck();
      },
      error: () => {
        this.wishlistLoading.set(false);
        this.wishlistLoaded.set(true);
        this.cdr.markForCheck();
      },
    });
  }

  shareWishlistLink() {
    const url = `${window.location.origin}/riftbound/wishlist/${this.token}`;
    navigator.clipboard.writeText(url);
  }

  shareWishlistWhatsApp() {
    const url = `${window.location.origin}/riftbound/wishlist/${this.token}`;
    const txt = encodeURIComponent(`Mira mi wishlist Riftbound: ${url}`);
    window.open(`https://wa.me/?text=${txt}`, '_blank');
  }
}
