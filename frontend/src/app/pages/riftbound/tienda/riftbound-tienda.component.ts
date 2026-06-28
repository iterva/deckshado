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
  RiftboundWishlistEntry,
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
            @if (s.whatsapp) { <a class="contact-chip wa" [href]="'https://wa.me/' + cleanWa(s.whatsapp)" target="_blank">📱 WhatsApp</a> }
            @if (s.instagram) { <a class="contact-chip ig" [href]="'https://instagram.com/' + cleanHandle(s.instagram)" target="_blank">📷 Instagram</a> }
            @if (s.discord) { <span class="contact-chip dc">💬 {{ s.discord }}</span> }
            @if (s.email_public) { <a class="contact-chip em" [href]="'mailto:' + s.email_public">✉️ Email</a> }
            @if (s.accepts_trades) { <span class="contact-chip tr">🔄 Acepta cambios</span> }
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
            } @else {
              <app-share-image
                mode="buying"
                gameLabel="Riftbound"
                [sellerName]="sellerHandle()"
                [contactLine]="shareContactLine()"
                [items]="shareWishlistItems()"
                ctaLabel="Imagen busco"
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

      @if (activeTab() === 'store') {
      <div class="filter-row">
        <input type="text" placeholder="Buscar..." [(ngModel)]="search" (keyup.enter)="reload()" />
        <select [(ngModel)]="ftype" (change)="reload()">
          <option value="">Todos los tipos</option>
          <option value="unit">Unit</option><option value="spell">Spell</option>
          <option value="champion">Champion</option><option value="legend">Legend</option>
          <option value="gear">Gear</option><option value="battlefield">Battlefield</option>
          <option value="rune">Rune</option>
        </select>
        <select [(ngModel)]="ffoil" (change)="reload()">
          <option value="">Foil/Normal</option>
          <option value="1">Solo foil</option>
          <option value="0">Solo normal</option>
        </select>
        <input type="number" placeholder="Precio mín." [(ngModel)]="priceMin" (change)="reload()" min="0" />
        <input type="number" placeholder="Precio máx." [(ngModel)]="priceMax" (change)="reload()" min="0" />
        <select [(ngModel)]="ordering" (change)="reload()">
          <option value="-id">Más recientes</option>
          <option value="price">Precio ↑</option>
          <option value="-price">Precio ↓</option>
          <option value="card__name">Nombre A-Z</option>
        </select>
      </div>

      <p class="results-count">{{ count() }} cartas</p>

      <div class="cards-grid">
        @for (e of entries(); track e.id) {
          <div class="store-card">
            <div class="card-image" (click)="preview.set(e.card_data)">
              @if (e.card_data?.image) {
                <app-card-photo-carousel
                  [cardImage]="e.card_data.image"
                  [photos]="[e.photo_url, e.photo_url_2]"
                  [alt]="e.card_data.name"
                  [thumbWidth]="350">
                </app-card-photo-carousel>
              } @else { <div class="img-fallback">{{ e.card_data?.card_number }}</div> }
              @if (e.is_foil) { <div class="foil-badge">✨ FOIL</div> }
            </div>
            <div class="card-body">
              <h4>{{ e.card_data?.name }}</h4>
              <span class="card-meta">{{ e.card_data?.card_number }} · {{ e.language }}</span>
              <div class="price-row">
                <span class="price">{{ e.price != null ? ('$' + (e.price | number)) : 'Consultar' }}</span>
                <span class="qty">x{{ e.selling_quantity }}</span>
              </div>
              <app-tcg-price [cardName]="e.card_data?.name || ''" [compact]="true" [showMarketPrice]="false"></app-tcg-price>
              <button class="btn btn-sm btn-primary btn-add-cart"
                      (click)="addToCart(e, $event)"
                      [disabled]="inCart(e.id) >= e.selling_quantity">
                @if (inCart(e.id)) {
                  🛒 En carrito ({{ inCart(e.id) }})
                } @else {
                  🛒 Añadir
                }
              </button>
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
              <div class="card-image" (click)="preview.set(w.card_data)">
                @if (w.card_data?.image) {
                  <img [src]="w.card_data.image" [alt]="w.card_data.name" loading="lazy" />
                } @else { <div class="img-fallback">{{ w.card_data?.card_number }}</div> }
              </div>
              <div class="card-body">
                <h4>{{ w.card_data?.name }}</h4>
                <span class="card-meta">{{ w.card_data?.card_number }}</span>
                <div class="price-row">
                  <span class="qty wishlist-qty">❤️ Quiere x{{ w.desired_quantity }}</span>
                </div>
                <app-tcg-price [cardName]="w.card_data?.name || ''" [compact]="true" [showMarketPrice]="false"></app-tcg-price>
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
                  @if (item.image) { <img [src]="item.image" [alt]="item.name" /> }
                  <div class="cart-item-info">
                    <strong>{{ item.name }}</strong>
                    <small>{{ item.price != null ? ('$' + (item.price | number)) : 'Sin precio' }}</small>
                  </div>
                  <div class="cart-qty">
                    <button (click)="changeCartQty(item, -1)">−</button>
                    <span>{{ item.qty }}</span>
                    <button (click)="changeCartQty(item, 1)" [disabled]="item.qty >= item.available">+</button>
                  </div>
                  <strong class="cart-line-total">\${{ ((item.price || 0) * item.qty) | number }}</strong>
                  <button class="btn-icon" (click)="removeFromCart(item)" title="Quitar">🗑️</button>
                </li>
              }
            </ul>
            <div class="cart-total">
              <span>Total estimado:</span>
              <strong>\${{ cartTotal() | number }}</strong>
              @if (cartHasUnpriced()) { <small class="warn">⚠ Hay cartas sin precio, consulta al vendedor.</small> }
            </div>
            <div class="cart-actions">
              @if (store()?.whatsapp) {
                <button class="btn btn-primary" (click)="sendWhatsApp()">📱 Enviar pedido por WhatsApp</button>
              }
              <button class="btn btn-sm" (click)="copyOrder()">📋 Copiar pedido</button>
              <button class="btn btn-sm" (click)="clearCart()">🗑️ Vaciar</button>
            </div>
          }
        </div>
      </div>
    }

    @if (preview(); as pc) {
      <div class="modal-overlay" (click)="preview.set(null)">
        <div class="modal" (click)="$event.stopPropagation()">
          <button class="close-btn" (click)="preview.set(null)">✕</button>
          @if (pc.image) { <img [src]="pc.image" [alt]="pc.name" class="detail-image" /> }
          <div class="detail-info">
            <h2>{{ pc.name }}</h2>
            <p class="card-meta">{{ pc.card_number }}</p>
            @if (pc.description) { <p>{{ pc.description }}</p> }
            <app-tcg-price [cardName]="pc.name" [compact]="false" [showLink]="true" [showMarketPrice]="false"></app-tcg-price>
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

    .filter-row { display: flex; gap: .5rem; flex-wrap: wrap; margin-bottom: 1rem; }
    .filter-row input, .filter-row select {
      padding: .5rem .7rem; background: #0f0f23; color: #c8c8da;
      border: 1px solid #2a3a4a; border-radius: 6px;
    }
    .filter-row input:focus, .filter-row select:focus { outline: none; border-color: #e94560; }

    .results-count { color: #9ba3b4; font-size: .9rem; margin-bottom: 1rem; }

    .cards-grid {
      display: grid; gap: 1rem;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    }
    .store-card { background: #16213e; border: 1px solid #2a3a4a; border-radius: 10px; overflow: hidden; }
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
    .card-body { padding: .65rem .75rem .8rem; }
    .card-body h4 {
      margin: 0 0 .25rem; font-size: .95rem; color: #fff;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
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
    .btn-add-cart { width: 100%; margin-top: .55rem; font-size: .82rem; }
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
      display: grid; grid-template-columns: 48px 1fr auto auto auto; gap: .6rem;
      align-items: center; padding: .5rem; background: #0f0f23;
      border: 1px solid #2a3a4a; border-radius: 8px;
    }
    .cart-item img { width: 48px; height: 67px; object-fit: cover; border-radius: 4px; }
    .cart-item-info strong { display: block; color: #fff; font-size: .9rem; }
    .cart-item-info small { color: #9ba3b4; font-size: .78rem; }
    .cart-qty { display: flex; align-items: center; gap: .3rem; }
    .cart-qty button {
      width: 26px; height: 26px; border-radius: 4px;
      background: #1e2d3d; color: #fff; border: 1px solid #2a3a4a; cursor: pointer;
    }
    .cart-qty button:disabled { opacity: .4; cursor: not-allowed; }
    .cart-line-total { color: #e94560; font-size: .9rem; }
    .btn-icon { background: transparent; border: none; cursor: pointer; font-size: 1rem; }
    .cart-total {
      display: flex; align-items: center; justify-content: space-between;
      flex-wrap: wrap; gap: .4rem; padding: .65rem 0; border-top: 1px dashed #2a3a4a;
      color: #c8c8da;
    }
    .cart-total strong { color: #e94560; font-size: 1.1rem; }
    .cart-total .warn { width: 100%; color: #c89b3c; font-size: .8rem; }
    .cart-actions { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: .6rem; }
    .cart-actions .btn-primary { flex: 1 1 100%; }

    /* ── Mobile ── */
    @media (max-width: 768px) {
      .cards-grid { grid-template-columns: repeat(auto-fit, minmax(96px, 1fr)); gap: .55rem; }
      .card-body { padding: .55rem .6rem .65rem; }
      .card-body h4 { font-size: .88rem; }
      .price { font-size: .95rem; }
      .btn-add-cart {
        margin-top: .5rem; padding: .55rem .6rem; font-size: .85rem;
        background: #e94560; color: #fff; border-color: #e94560; font-weight: 700;
      }
      .cart-fab {
        bottom: calc(4.8rem + env(safe-area-inset-bottom, 0));
        right: .9rem; padding: .75rem 1.1rem; font-size: .9rem;
      }
      .cart-modal { padding: .9rem; max-height: 88vh; }
      .cart-item { grid-template-columns: 40px 1fr auto; row-gap: .35rem; }
      .cart-item img { width: 40px; height: 56px; }
      .cart-item .cart-qty, .cart-item .cart-line-total, .cart-item .btn-icon {
        grid-column: span 1;
      }
    }
    @media (max-width: 480px) {
      .cards-grid { grid-template-columns: repeat(auto-fit, minmax(84px, 1fr)); gap: .45rem; }
      .card-body h4 { font-size: .76rem; }
      .card-meta { display: none; }
      .price { font-size: .82rem; }
      .qty { font-size: .74rem; }
      .btn-add-cart { font-size: .74rem; padding: .4rem .45rem; }
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
  ordering = '-id';

  cartCount() { return this.cart().reduce((s, c) => s + c.qty, 0); }
  cartTotal() { return this.cart().reduce((s, c) => s + (c.price || 0) * c.qty, 0); }
  cartHasUnpriced() { return this.cart().some(c => c.price == null); }
  inCart(entryId: number): number { return this.cart().find(c => c.entryId === entryId)?.qty || 0; }

  ngOnInit() {
    this.token = this.route.snapshot.paramMap.get('token') || '';
    const dt = this.route.snapshot.data?.['defaultTab'];
    if (dt === 'wishlist') this.activeTab.set('wishlist');
    this.loadCart();
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
    return this.entries().slice(0, 20).map(e => ({
      name: e.card_data?.name || '',
      image: e.card_data?.image || '',
      quantity: e.selling_quantity || 1,
      foil: !!e.is_foil,
      price: e.price ?? null,
    }));
  }
  shareWishlistItems(): ShareImageItem[] {
    return this.wishlist().slice(0, 20).map(w => ({
      name: w.card_data?.name || '',
      image: w.card_data?.image || '',
      quantity: w.desired_quantity || 1,
      foil: false,
      price: null,
    }));
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
        image: entry.card_data.image || '',
      });
    }
    this.cart.set(list);
    this.saveCart();
    this.cdr.markForCheck();
  }

  removeFromCart(item: RiftboundCartItem) {
    this.cart.set(this.cart().filter(c => c.entryId !== item.entryId));
    this.saveCart();
  }

  changeCartQty(item: RiftboundCartItem, delta: number) {
    const newQty = item.qty + delta;
    if (newQty <= 0) { this.removeFromCart(item); return; }
    if (newQty > item.available) return;
    this.cart.set(this.cart().map(c => c.entryId === item.entryId ? { ...c, qty: newQty } : c));
    this.saveCart();
  }

  clearCart() { this.cart.set([]); this.saveCart(); }

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
    const wa = this.store()?.whatsapp;
    if (!wa) return;
    const number = wa.replace(/[^0-9]/g, '');
    const text = encodeURIComponent(this.buildOrderText());
    window.open(`https://wa.me/${number}?text=${text}`, '_blank');
  }

  copyOrder() {
    navigator.clipboard.writeText(this.buildOrderText());
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
