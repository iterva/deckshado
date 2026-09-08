import {
  Component, OnInit, OnDestroy, AfterViewInit, ChangeDetectionStrategy, ChangeDetectorRef,
  ElementRef, ViewChild, HostListener, inject, signal, computed,
} from '@angular/core';
import { CommonModule, DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import QRCode from 'qrcode';

import { RiftboundService } from '../../../services/riftbound.service';
import { AuthService } from '../../../services/auth.service';
import { ShareImageComponent, ShareImageItem } from '../../../components/share-image/share-image.component';
import { TcgPriceComponent } from '../../../components/tcg-price/tcg-price.component';
import { IconComponent } from '../../../components/icon/icon.component';
import {
  RiftboundCard, RiftboundCardLite, RiftboundCollectionEntry, RiftboundWishlistEntry,
  RiftboundSet, RiftboundCollectionStats, RiftboundBinderProfile, RiftboundBulkImportResult,
  RiftboundCondition, RiftboundLanguage, RiftboundStoreOrder, RiftboundStoreOrderStatus,
  RiftboundWorkspace, RiftboundStorePermissionFlags, RiftboundStoreCollaboratorPermission,
} from '../../../models/riftbound';

type Tab = 'carpeta' | 'codex' | 'wishlist' | 'mercado' | 'pedidos' | 'historial' | 'stats' | 'permisos';

interface DirtyPatch {
  quantity?: number;
  price?: number | null;
  selling_quantity?: number;
  condition?: RiftboundCondition;
  language?: RiftboundLanguage;
  is_foil?: boolean;
  notes?: string;
}

const FULL_STORE_PERMISSIONS: RiftboundStorePermissionFlags = {
  view_collection: true,
  edit_collection: true,
  delete_collection: true,
  edit_market: true,
  remove_from_market: true,
  view_orders: true,
  view_history: true,
  accept_orders: true,
  reject_orders: true,
  manage_permissions: true,
};

@Component({
  selector: 'app-riftbound-carpeta',
  standalone: true,
  imports: [CommonModule, FormsModule, DecimalPipe, ShareImageComponent, TcgPriceComponent, IconComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
  <div class="carpeta-container">
    <!-- Header + Stats Banner -->
    <div class="carpeta-header-layout">
      <div class="carpeta-profile-card">
        <div class="binder-avatar-wrap">
          @if (binderProfile()?.binder_avatar_url || binderProfile()?.user_avatar_url) {
            <img class="binder-avatar" [src]="binderProfile()!.binder_avatar_url || binderProfile()!.user_avatar_url" alt="avatar" />
          } @else {
            <div class="binder-avatar-placeholder">
              <app-icon name="folder" [size]="22"></app-icon>
            </div>
          }
          <button class="avatar-edit-btn" (click)="avatarInput.click()" [disabled]="avatarUploading()"
                  [title]="avatarUploading() ? 'Subiendo...' : 'Cambiar avatar'">
            <app-icon [name]="avatarUploading() ? 'refresh-cw' : 'upload'" [size]="12"></app-icon>
          </button>
          <input #avatarInput type="file" accept="image/*" hidden (change)="onAvatarFileChange($event)" />
        </div>
        <div class="binder-info">
          <h1>{{ workspaceMode() ? 'Carpetas · Riftbound' : 'Mi Carpeta · Riftbound' }}</h1>
          <p class="binder-user">
            @if (workspaceMode()) {
              @if (selectedWorkspace(); as ws) {
                Tienda de <strong>{{ ws.owner_username }}</strong>
              } @else {
                Selecciona una tienda
              }
            } @else {
              {{ auth.user()?.username || 'Invitado' }}
            }
          </p>
        </div>
      </div>

      <!-- Collection Stats Banner -->
      @if (!workspaceMode()) {
        <div class="collection-stats-banner">
          <div class="stat-item owned">
            <span class="stat-num">{{ collectionTotal() }}</span>
            <span class="stat-title"><app-icon name="check-circle" [size]="12"></app-icon> Poseídas</span>
          </div>
          <div class="stat-item wishlist">
            <span class="stat-num">{{ wishlistTotal() }}</span>
            <span class="stat-title"><app-icon name="heart" [size]="12"></app-icon> Wishlist</span>
          </div>
          <div class="stat-item selling">
            <span class="stat-num">{{ collectionSellingCount() }}</span>
            <span class="stat-title"><app-icon name="store" [size]="12"></app-icon> En Venta</span>
          </div>
        </div>
      }
    </div>

    @if (workspaceMode()) {
      <div class="workspace-panel">
        <div class="workspace-field">
          <label>Tienda con acceso</label>
          <select [value]="selectedWorkspaceId() ?? ''" (change)="onWorkspaceChange($any($event.target).value)">
            <option value="" disabled>Seleccionar tienda...</option>
            @for (ws of workspaces(); track ws.store_profile_id) {
              <option [value]="ws.store_profile_id">
                {{ workspaceLabel(ws) }}
              </option>
            }
          </select>
        </div>
        <div class="workspace-perms">
          @if (selectedWorkspacePermissions(); as perms) {
            @if (perms.edit_collection) { <span class="perm-chip">Editar carpeta</span> }
            @if (perms.delete_collection) { <span class="perm-chip">Eliminar de carpeta</span> }
            @if (perms.edit_market) { <span class="perm-chip">Editar mercado</span> }
            @if (perms.remove_from_market) { <span class="perm-chip">Quitar de venta</span> }
            @if (perms.view_orders) { <span class="perm-chip">Ver pedidos</span> }
            @if (perms.view_history) { <span class="perm-chip">Ver historial</span> }
            @if (perms.accept_orders) { <span class="perm-chip">Aceptar pedidos</span> }
            @if (perms.reject_orders) { <span class="perm-chip">Rechazar pedidos</span> }
            @if (perms.manage_permissions) { <span class="perm-chip">Gestionar permisos</span> }
          }
        </div>
      </div>
    }

    <!-- Tabs -->
    <div class="tabs">
      @if (!workspaceMode() || hasPermission('view_collection')) {
        <button class="tab" [class.active]="activeTab() === 'carpeta'" (click)="switchTab('carpeta')">
          <app-icon name="folder" [size]="15"></app-icon> <span>CARPETA</span>
        </button>
        <button class="tab" [class.active]="activeTab() === 'codex'" (click)="switchTab('codex')">
          <app-icon name="library" [size]="15"></app-icon> <span>COLECCIÓN</span>
        </button>
      }
      @if (!workspaceMode()) {
        <button class="tab" [class.active]="activeTab() === 'wishlist'" (click)="switchTab('wishlist')">
          <app-icon name="heart" [size]="15"></app-icon> <span>WISHLIST</span>
        </button>
      }
      @if (!workspaceMode() || hasPermission('view_collection')) {
        <button class="tab" [class.active]="activeTab() === 'mercado'" (click)="switchTab('mercado')">
          <app-icon name="store" [size]="15"></app-icon> <span>MERCADO</span>
        </button>
      }
      @if (!workspaceMode() || hasPermission('view_orders')) {
        <button class="tab" [class.active]="activeTab() === 'pedidos'" (click)="switchTab('pedidos')">
          <app-icon name="file-text" [size]="15"></app-icon> <span>PEDIDOS</span>
        </button>
      }
      @if (!workspaceMode() || hasPermission('view_history')) {
        <button class="tab" [class.active]="activeTab() === 'historial'" (click)="switchTab('historial')">
          <app-icon name="clock" [size]="15"></app-icon> <span>HISTORIAL</span>
        </button>
      }
      @if (!workspaceMode()) {
        <button class="tab" [class.active]="activeTab() === 'stats'" (click)="switchTab('stats')">
          <app-icon name="bar-chart-3" [size]="15"></app-icon> <span>STATS</span>
        </button>
      }
      @if (canManagePermissions()) {
        <button class="tab" [class.active]="activeTab() === 'permisos'" (click)="switchTab('permisos')">
          <app-icon name="shield" [size]="15"></app-icon> <span>PERMISOS</span>
        </button>
      }
    </div>

    @if (workspaceMode() && !selectedWorkspaceId()) {
      <div class="empty-state" style="margin-top: 1rem;">
        <p>Selecciona una tienda de la lista para trabajar sobre su carpeta compartida.</p>
      </div>
    }

    <!-- ═══ TAB: CARPETA ═══ -->
    @if (activeTab() === 'carpeta' && canUseWorkspaceContent()) {
      <div class="tab-content">
        <div class="tab-toolbar">
          <div class="search-bar">
            <input type="text" placeholder="Buscar en tu colección..."
                   [(ngModel)]="collectionSearch" (keyup.enter)="onCollectionSearch()" />
            <button class="btn btn-primary btn-sm" (click)="onCollectionSearch()">
              <app-icon name="search" [size]="14"></app-icon> <span>Buscar</span>
            </button>
          </div>
          <button class="btn btn-sm" [class.btn-primary]="onlySelling()" (click)="toggleOnlySelling()">
            <app-icon name="tag" [size]="14"></app-icon> Solo en venta
          </button>
          <button class="btn btn-sm" (click)="showBulkImport.update(v => !v)" [disabled]="!hasPermission('edit_collection')">
            <app-icon name="upload" [size]="14"></app-icon> Importar masivo
          </button>
          @if (dirtyEntries.size > 0 && (hasPermission('edit_collection') || hasPermission('edit_market') || hasPermission('remove_from_market'))) {
            <button class="btn btn-sm btn-primary" (click)="saveAllChanges()" [disabled]="batchSaving()">
              <app-icon name="save" [size]="14"></app-icon>
              {{ batchSaving() ? 'Guardando...' : 'Guardar Cambios (' + dirtyEntries.size + ')' }}
            </button>
          }
        </div>

        @if (showBulkImport()) {
          <div class="bulk-import-panel">
            <h4>Importación masiva</h4>
            <p class="hint">Formato por línea: <code>2 Nombre carta</code> ó <code>OGN-001</code> ó <code>3x Nombre</code></p>
            <textarea rows="8" [(ngModel)]="bulkText" placeholder="2 Volibear&#10;1x OGN-001&#10;Yasuo"></textarea>
            <div class="bulk-mode">
              <label><input type="radio" name="bulkmode" [(ngModel)]="bulkMode" value="add" /> Sumar a lo existente</label>
              <label><input type="radio" name="bulkmode" [(ngModel)]="bulkMode" value="set" /> Sobrescribir cantidad</label>
            </div>
            <div class="bulk-actions">
              <button class="btn btn-primary btn-sm" (click)="runBulkImport()" [disabled]="bulkImporting()">
                {{ bulkImporting() ? '⏳ Importando...' : '📥 Importar' }}
              </button>
              <button class="btn btn-sm" (click)="showBulkImport.set(false)">Cerrar</button>
            </div>
            @if (bulkResult(); as r) {
              <div class="bulk-result">
                <p>✅ Añadidas: <strong>{{ r.added }}</strong> · 🔄 Actualizadas: <strong>{{ r.updated }}</strong>
                   · ❓ No encontradas: <strong>{{ r.not_found }}</strong> · ⚠️ Ambiguas: <strong>{{ r.ambiguous }}</strong></p>
                @if (r.not_found_lines.length) {
                  <details><summary>No encontradas ({{ r.not_found_lines.length }})</summary>
                    <pre>{{ r.not_found_lines.join('\n') }}</pre>
                  </details>
                }
                @if (r.ambiguous_lines.length) {
                  <details><summary>Ambiguas ({{ r.ambiguous_lines.length }})</summary>
                    <pre>{{ r.ambiguous_lines.join('\n') }}</pre>
                  </details>
                }
              </div>
            }
          </div>
        }

        <p class="results-count">{{ collectionTotal() }} cartas únicas · {{ collectionCopies() }} copias totales</p>

        @if (collectionLoading()) { <div class="loading">Cargando...</div> }

        @if (!collectionLoading() && collectionEntries().length === 0) {
          <div class="empty-state">
            <p>Tu carpeta está vacía. Ve a <strong>Colección</strong> para añadir cartas.</p>
          </div>
        }

        <div class="collection-grid">
          @for (entry of collectionEntries(); track entry.id) {
            <div class="collection-card">
              <div class="card-image" (click)="previewCard.set(entry.card_data)">
                @if (cardImageUrl(entry.card_data) && !isCardImageBroken(entry.card_data)) {
                  <img [src]="cardImageUrl(entry.card_data)" [alt]="entry.card_data.name" loading="lazy"
                       (error)="onCardImageError(entry.card_data, $event)" />
                } @else {
                  <div class="img-fallback">{{ entry.card_data.card_number }}</div>
                }
                <div class="eye-overlay"><app-icon name="eye" [size]="18"></app-icon></div>
                @if (entry.is_foil) { <div class="foil-badge">✨ FOIL</div> }
              </div>
              <div class="card-body">
                <h4>{{ entry.card_data.name }}</h4>
                <span class="card-meta">{{ typeLabel(entry.card_data.card_type) }} · {{ entry.card_data.card_number }}</span>
                <div class="inline-fields">
                  <div class="field">
                    <label>Tengo</label>
                    <input type="number" [value]="entry.quantity" min="0"
                      [disabled]="!hasPermission('edit_collection')"
                      (input)="onFieldChange(entry, 'quantity', $any($event.target).valueAsNumber)" />
                  </div>
                  <div class="field">
                    <label>Precio</label>
                    <input type="number" [value]="entry.price ?? ''" min="0" placeholder="—"
                      [disabled]="!hasPermission('edit_market')"
                      (input)="onFieldChange(entry, 'price', priceFromInput($any($event.target).value))" />
                  </div>
                  <div class="field">
                    <label>En venta</label>
                    <input type="number" [value]="entry.selling_quantity" min="0" [max]="entry.quantity"
                      [disabled]="!hasPermission('edit_market') && !hasPermission('remove_from_market')"
                      (input)="onFieldChange(entry, 'selling_quantity', $any($event.target).valueAsNumber)" />
                  </div>
                </div>
                <div class="tcg-ref-row">
                  <app-tcg-price [cardName]="entry.card_data.name || ''" [compact]="true"></app-tcg-price>
                </div>
                <div class="inline-fields">
                  <div class="field">
                    <label>Idioma</label>
                    <select [value]="entry.language" [disabled]="!hasPermission('edit_collection')"
                      (change)="onFieldChange(entry, 'language', $any($event.target).value)">
                      <option value="EN">EN</option>
                      <option value="ZH">中文</option>
                    </select>
                  </div>
                  <label class="foil-toggle">
                    <input type="checkbox" [checked]="entry.is_foil"
                      [disabled]="!hasPermission('edit_collection')"
                      (change)="onFieldChange(entry, 'is_foil', $any($event.target).checked)" />
                    ✨ Foil
                  </label>
                </div>
                <div class="field full">
                  <label>Notas</label>
                  <input type="text" [value]="entry.notes" maxlength="200" placeholder="—"
                    [disabled]="!hasPermission('edit_collection')"
                    (input)="onFieldChange(entry, 'notes', $any($event.target).value)" />
                </div>
                <div class="card-action-row">
                  @if (dirtyEntries.has(entry.id) && (hasPermission('edit_collection') || hasPermission('edit_market') || hasPermission('remove_from_market'))) {
                    <button class="btn btn-xs btn-primary" (click)="saveEntry(entry)">💾 Guardar</button>
                  }
                  <button class="btn btn-xs btn-danger" (click)="removeFromCollection(entry)" [disabled]="!hasPermission('delete_collection')">
                    <app-icon name="trash-2" [size]="14"></app-icon>
                  </button>
                </div>
              </div>
            </div>
          }
        </div>

        @if (collectionTotalPages() > 1) {
          <div #collectionSentinel class="infinite-sentinel" aria-hidden="true"></div>
          @if (collectionLoading() && collectionEntries().length > 0) {
            <div class="loading">Cargando más...</div>
          }
          @if (!collectionHasMore() && collectionEntries().length > 0) {
            <p class="results-count" style="margin-top: 1rem;">— Fin de la carpeta —</p>
          }
        }
      </div>
    }

    <!-- ═══ TAB: CODEX ═══ -->
    @if (activeTab() === 'codex' && canUseWorkspaceContent()) {
      <div class="tab-content">
        <div class="tab-toolbar">
          <div class="search-bar">
            <input type="text" placeholder="Buscar cartas..."
                   [(ngModel)]="codexSearch" (keyup.enter)="onCodexSearch()" />
            <button class="btn btn-primary btn-sm" (click)="onCodexSearch()">Buscar</button>
          </div>
        </div>
        <div class="filter-row">
          <select [(ngModel)]="selectedSet" (change)="onCodexFilter()">
            <option value="">Todos los sets</option>
            @for (s of sets(); track s.id) { <option [value]="s.code">{{ s.name }} ({{ s.code }})</option> }
          </select>
          <select [(ngModel)]="selectedType" (change)="onCodexFilter()">
            <option value="">Todos los tipos</option>
            <option value="unit">Unit</option>
            <option value="spell">Spell</option>
            <option value="champion">Champion</option>
            <option value="legend">Legend</option>
            <option value="gear">Gear</option>
            <option value="battlefield">Battlefield</option>
            <option value="rune">Rune</option>
          </select>
          <select [(ngModel)]="selectedRarity" (change)="onCodexFilter()">
            <option value="">Todas las rarezas</option>
            <option value="common">Common</option>
            <option value="uncommon">Uncommon</option>
            <option value="rare">Rare</option>
            <option value="epic">Epic</option>
            <option value="legendary">Legendary</option>
            <option value="champion">Champion</option>
            <option value="promo">Promo</option>
          </select>
          <div class="color-chips">
            @for (c of COLORS; track c.code) {
              <button class="chip" [class.active]="selectedColors.has(c.code)"
                      [style.--c]="c.hex" (click)="toggleColor(c.code)">
                {{ c.label }}
              </button>
            }
          </div>
        </div>

        <p class="results-count">{{ codexCards().length }} de {{ codexTotal() }} cartas</p>

        @if (codexLoading()) { <div class="loading">Cargando...</div> }

        <div class="card-grid">
          @for (card of codexCards(); track card.id) {
            <div class="card-item" (click)="selectCodexCard(card)">
              <div class="card-image">
                @if (cardImageUrl(card) && !isCardImageBroken(card)) {
                  <img [src]="cardImageUrl(card)" [alt]="card.name" loading="lazy"
                       (error)="onCardImageError(card, $event)" />
                } @else {
                  <div class="img-fallback">{{ card.card_number }}</div>
                }
                @if (isInCollection(card.id)) {
                  <div class="owned-badge">✓ x{{ collectionQty(card.id) }}</div>
                }
              </div>
              <div class="card-info">
                <h4>{{ card.name }}</h4>
                <span class="card-type">{{ typeLabel(card.card_type) }}</span>
                <app-tcg-price [cardName]="card.name" [compact]="true"></app-tcg-price>
              </div>
              <div class="card-overlay-actions">
                <button class="btn-icon btn-add" (click)="quickAddToCollection(card, $event)" title="Añadir a colección"
                        [disabled]="!hasPermission('edit_collection')">
                  <app-icon name="plus" [size]="14"></app-icon>
                </button>
                <button class="btn-icon btn-heart" [class.active]="isInWishlist(card.id)"
                  [disabled]="workspaceMode()"
                        (click)="toggleWishlist(card.id, $event)" title="Wishlist">
                  <i class="bi" [class.bi-heart-fill]="isInWishlist(card.id)" [class.bi-heart]="!isInWishlist(card.id)"></i>
                </button>
              </div>
            </div>
          }
        </div>

        @if (codexHasMore()) {
          <div #codexSentinel class="infinite-sentinel" aria-hidden="true"></div>
        }
        @if (codexLoading() && codexCards().length > 0) {
          <div class="loading">Cargando más...</div>
        }
        @if (!codexHasMore() && !codexLoading() && codexCards().length > 0) {
          <p class="results-count" style="margin-top: 1rem;">— Fin de la colección —</p>
        }
      </div>
    }

    <!-- ═══ TAB: WISHLIST ═══ -->
    @if (activeTab() === 'wishlist' && canUseWorkspaceContent()) {
      <div class="tab-content">
        <div class="tab-toolbar">
          <div class="search-bar">
            <input type="text" placeholder="Buscar en wishlist..."
                   [(ngModel)]="wishlistSearch" (keyup.enter)="onWishlistSearch()" />
            <button class="btn btn-primary btn-sm" (click)="onWishlistSearch()">Buscar</button>
          </div>
          @if (wishlistEntries().length > 0) {
            <div class="share-row">
              <input type="text"
                     class="share-message-input"
                     placeholder="Mensaje en la imagen (opcional)"
                     [(ngModel)]="wishlistShareMessage"
                     maxlength="120" />
              <app-share-image
                mode="buying"
                gameLabel="Riftbound"
                [sellerName]="wishlistSellerHandle()"
                [customHeadline]="wishlistContactLine()"
                contactLine=""
                [items]="wishlistShareItems()"
                ctaLabel="Imagen busco"
                filenamePrefix="shadowforge-wishlist"
                footerTagline="ShadowForge · Marketplace TCG">
              </app-share-image>
              @if (binderProfile()?.is_store_public && binderProfile()?.share_token) {
                <button class="btn btn-sm" (click)="copyWishlistLink()">
                  <app-icon name="external-link" [size]="14"></app-icon> Copiar link wishlist
                </button>
                <button class="btn btn-sm" (click)="shareWishlistWhatsApp()">
                  <app-icon name="message-circle" [size]="14"></app-icon> Compartir
                </button>
              }
            </div>
          }
        </div>

        <p class="results-count">{{ wishlistTotal() }} cartas en tu wishlist</p>

        @if (wishlistLoading()) { <div class="loading">Cargando...</div> }

        @if (!wishlistLoading() && wishlistEntries().length === 0) {
          <div class="empty-state">
            <p>Tu wishlist está vacía. Usa el <app-icon name="heart" [size]="13"></app-icon> en la <strong>Colección</strong> para añadir cartas.</p>
          </div>
        }

        <div class="wishlist-grid">
          @for (entry of wishlistEntries(); track entry.id) {
            <div class="wishlist-card" [class.is-share-selected]="isWishlistShareSelected(entry.id)">
              <label class="share-check" title="Incluir en la imagen para compartir" (click)="$event.stopPropagation()">
                <input type="checkbox"
                       [checked]="isWishlistShareSelected(entry.id)"
                       (change)="toggleWishlistShare(entry.id, $any($event.target).checked)" />
                <app-icon name="image" [size]="14"></app-icon>
              </label>
              <div class="card-image" (click)="previewCard.set(entry.card_data)">
                @if (cardImageUrl(entry.card_data) && !isCardImageBroken(entry.card_data)) {
                  <img [src]="cardImageUrl(entry.card_data)" [alt]="entry.card_data.name" loading="lazy"
                       (error)="onCardImageError(entry.card_data, $event)" />
                } @else {
                  <div class="img-fallback">{{ entry.card_data.card_number }}</div>
                }
                <div class="eye-overlay"><app-icon name="eye" [size]="18"></app-icon></div>
              </div>
              <div class="card-info">
                <h4>{{ entry.card_data.name }}</h4>
                <span class="card-meta">{{ typeLabel(entry.card_data.card_type) }} · {{ entry.card_data.card_number }}</span>
                <div class="wishlist-qty">
                  <label>Quiero:</label>
                  <input type="number" [value]="entry.desired_quantity" min="1"
                    (change)="updateWishlistQty(entry, $any($event.target).valueAsNumber)" />
                </div>
                <app-tcg-price [cardName]="entry.card_data.name || ''" [compact]="true"></app-tcg-price>
              </div>
              <div class="card-actions">
                <button class="btn btn-xs btn-danger" (click)="removeFromWishlist(entry)" title="Quitar de wishlist">
                  <app-icon name="x" [size]="14"></app-icon>
                </button>
              </div>
            </div>
          }
        </div>

        @if (wishlistHasMore()) {
          <div #wishlistSentinel class="infinite-sentinel" aria-hidden="true"></div>
        }
        @if (wishlistLoading() && wishlistEntries().length > 0) {
          <div class="loading">Cargando más...</div>
        }
        @if (!wishlistHasMore() && !wishlistLoading() && wishlistEntries().length > 0) {
          <p class="results-count" style="margin-top: 1rem;">— Fin de la wishlist —</p>
        }
      </div>
    }

    <!-- ═══ TAB: MERCADO ═══ -->
    @if (activeTab() === 'mercado' && canUseWorkspaceContent()) {
      <div class="tab-content">
        <div class="mercado-toolbar">
          @if (!workspaceMode()) {
            <button class="btn btn-sm" (click)="showStoreConfig.update(v => !v)">
              <app-icon name="settings" [size]="14"></app-icon> {{ showStoreConfig() ? 'Cerrar' : 'Configurar' }} tienda
            </button>
            @if (binderProfile()?.is_store_public && binderProfile()?.share_token) {
              <button class="btn btn-sm" (click)="copyShareLink()">
                <app-icon name="external-link" [size]="14"></app-icon> Copiar enlace público
              </button>
              <button class="btn btn-sm" (click)="downloadStoreQr()" [disabled]="qrDownloading()">
                <app-icon name="grid" [size]="14"></app-icon> {{ qrDownloading() ? 'Generando QR...' : 'Generar QR' }}
              </button>
            }
          }
          <button class="btn btn-sm" (click)="exportMercadoPdf()" [disabled]="exportingPdf()">
            {{ exportingPdf() ? '⏳' : '📄' }} Exportar PDF
          </button>
          @if (mercadoDirty.size > 0 && (hasPermission('edit_market') || hasPermission('remove_from_market'))) {
            <button class="btn btn-sm btn-primary" (click)="saveMercadoChanges()" [disabled]="batchSaving()">
              💾 Guardar ({{ mercadoDirty.size }})
            </button>
          }
        </div>

        @if (!workspaceMode() && showStoreConfig()) {
          <div class="store-config-panel">
            <h4>Configuración de tienda</h4>
            <div class="form-grid">
              <label class="full check-row">
                <input type="checkbox" [checked]="binderProfile()?.is_store_public ?? false"
                  (change)="patchProfile({ is_store_public: $any($event.target).checked })" />
                <span>Tienda pública (visible en /riftbound/tiendas)</span>
              </label>
              <label>
                <span>Nombre público</span>
                <input type="text" [value]="binderProfile()?.display_name || ''" maxlength="80"
                  (change)="patchProfile({ display_name: $any($event.target).value })" />
              </label>
              <label>
                <span>Ciudad</span>
                <input type="text" [value]="binderProfile()?.city || ''" maxlength="80"
                  (change)="patchProfile({ city: $any($event.target).value })" />
              </label>
              <label>
                <span>País</span>
                <select [value]="binderProfile()?.country || 'CL'"
                  (change)="patchProfile({ country: $any($event.target).value })">
                  <option value="CL">Chile</option><option value="AR">Argentina</option>
                  <option value="PE">Perú</option><option value="MX">México</option>
                  <option value="CO">Colombia</option><option value="UY">Uruguay</option>
                  <option value="EC">Ecuador</option><option value="BO">Bolivia</option>
                  <option value="VE">Venezuela</option><option value="PY">Paraguay</option>
                  <option value="ES">España</option><option value="US">USA</option>
                  <option value="OT">Otro</option>
                </select>
              </label>
              <label>
                <span>WhatsApp</span>
                <input type="text" [value]="binderProfile()?.whatsapp || ''" maxlength="40"
                  (change)="patchProfile({ whatsapp: $any($event.target).value })" />
              </label>
              <label>
                <span>Instagram</span>
                <input type="text" [value]="binderProfile()?.instagram || ''" maxlength="80"
                  (change)="patchProfile({ instagram: $any($event.target).value })" />
              </label>
              <label>
                <span>Discord</span>
                <input type="text" [value]="binderProfile()?.discord || ''" maxlength="80"
                  (change)="patchProfile({ discord: $any($event.target).value })" />
              </label>
              <label>
                <span>Email público</span>
                <input type="email" [value]="binderProfile()?.email_public || ''" maxlength="120"
                  (change)="patchProfile({ email_public: $any($event.target).value })" />
              </label>
              <label class="full">
                <span>Bio</span>
                <textarea rows="2" maxlength="500" [value]="binderProfile()?.bio || ''"
                  (change)="patchProfile({ bio: $any($event.target).value })"></textarea>
              </label>
              <label class="full">
                <span>Métodos de pago</span>
                <input type="text" [value]="binderProfile()?.payment_methods || ''" maxlength="200"
                  (change)="patchProfile({ payment_methods: $any($event.target).value })" />
              </label>
              <label class="full">
                <span>Información de envío</span>
                <input type="text" [value]="binderProfile()?.shipping_info || ''" maxlength="200"
                  (change)="patchProfile({ shipping_info: $any($event.target).value })" />
              </label>
              <label class="full check-row">
                <input type="checkbox" [checked]="binderProfile()?.accepts_trades ?? false"
                  (change)="patchProfile({ accepts_trades: $any($event.target).checked })" />
                <span>Acepto cambios / trades</span>
              </label>
              <div class="full token-row">
                <span>Token público:</span>
                <code>{{ binderProfile()?.share_token }}</code>
                <button class="btn btn-xs btn-danger" (click)="regenerateToken()">Regenerar</button>
              </div>
            </div>
          </div>
        }

        <p class="results-count">{{ mercadoEntries().length }} cartas en venta</p>
        @if (mercadoLoading()) { <div class="loading">Cargando...</div> }
        @if (!mercadoLoading() && mercadoEntries().length === 0) {
          <div class="empty-state">
            <p>No tienes cartas marcadas como en venta. En la pestaña <strong>Carpeta</strong> indica "En venta" y precio.</p>
          </div>
        }

        <div #mercadoExport class="collection-grid">
          @for (entry of mercadoEntries(); track entry.id) {
            <div class="collection-card">
              <div class="card-image" (click)="previewCard.set(entry.card_data)">
                @if (cardImageUrl(entry.card_data) && !isCardImageBroken(entry.card_data)) {
                  <img [src]="cardImageUrl(entry.card_data)" [alt]="entry.card_data.name" loading="lazy"
                       (error)="onCardImageError(entry.card_data, $event)" />
                } @else {
                  <div class="img-fallback">{{ entry.card_data.card_number }}</div>
                }
                @if (entry.is_foil) { <div class="foil-badge">✨ FOIL</div> }
              </div>
              <div class="card-body">
                <h4>{{ entry.card_data.name }}</h4>
                <span class="card-meta">{{ entry.card_data.card_number }} · {{ entry.language }}</span>
                <div class="inline-fields">
                  <div class="field">
                    <label>Precio</label>
                    <input type="number" [value]="entry.price ?? ''" min="0" placeholder="—"
                      [disabled]="!hasPermission('edit_market')"
                      (input)="onMercadoFieldChange(entry, 'price', priceFromInput($any($event.target).value))" />
                  </div>
                  <div class="field">
                    <label>En venta</label>
                    <input type="number" [value]="entry.selling_quantity" min="0" [max]="entry.quantity"
                      [disabled]="!hasPermission('edit_market') && !hasPermission('remove_from_market')"
                      (input)="onMercadoFieldChange(entry, 'selling_quantity', $any($event.target).valueAsNumber)" />
                  </div>
                </div>
                <div class="tcg-ref-row">
                  <span class="tcg-ref-label">Ref. TCG:</span>
                  <app-tcg-price [cardName]="entry.card_data.name || ''" [compact]="true"></app-tcg-price>
                </div>
                <div class="card-photo-row">
                  <!-- Slot 1 -->
                  <input type="file" accept="image/*" capture="environment"
                         [id]="'rb-photo-input-' + entry.id + '-1'"
                        [disabled]="!hasPermission('edit_market')"
                         (change)="onPhotoSelected(entry, $event, 1)" hidden />
                  @if (entry.photo_url) {
                    <button class="btn btn-xs btn-photo" (click)="openPhotoModal(entry.photo_url, $event)" title="Ver foto 1">
                      <img class="photo-thumb" [src]="entry.photo_url" alt="Foto 1" /> 📸 1
                    </button>
                    <button class="btn btn-xs btn-photo-action" (click)="triggerPhotoUpload(entry, $event, 1)"
                          [disabled]="uploadingPhotoFor() === entry.id || !hasPermission('edit_market')" title="Reemplazar foto 1">
                      {{ uploadingPhotoFor() === entry.id && uploadingPhotoSlot() === 1 ? '⏳' : '🔄' }}
                    </button>
                    <button class="btn btn-xs btn-danger" (click)="removePhoto(entry, $event, 1)" title="Quitar"
                      [disabled]="!hasPermission('edit_market')">✕</button>
                  } @else {
                    <button class="btn btn-xs btn-photo btn-photo-empty" (click)="triggerPhotoUpload(entry, $event, 1)"
                            [disabled]="uploadingPhotoFor() === entry.id || !hasPermission('edit_market')" title="Subir foto real">
                      {{ uploadingPhotoFor() === entry.id && uploadingPhotoSlot() === 1 ? '⏳ Subiendo...' : '📷 Foto 1' }}
                    </button>
                  }
                  <!-- Slot 2 -->
                  <input type="file" accept="image/*" capture="environment"
                         [id]="'rb-photo-input-' + entry.id + '-2'"
                        [disabled]="!hasPermission('edit_market')"
                         (change)="onPhotoSelected(entry, $event, 2)" hidden />
                  @if (entry.photo_url_2) {
                    <button class="btn btn-xs btn-photo" (click)="openPhotoModal(entry.photo_url_2, $event)" title="Ver foto 2">
                      <img class="photo-thumb" [src]="entry.photo_url_2" alt="Foto 2" /> 📸 2
                    </button>
                    <button class="btn btn-xs btn-photo-action" (click)="triggerPhotoUpload(entry, $event, 2)"
                          [disabled]="uploadingPhotoFor() === entry.id || !hasPermission('edit_market')" title="Reemplazar foto 2">
                      {{ uploadingPhotoFor() === entry.id && uploadingPhotoSlot() === 2 ? '⏳' : '🔄' }}
                    </button>
                    <button class="btn btn-xs btn-danger" (click)="removePhoto(entry, $event, 2)" title="Quitar"
                      [disabled]="!hasPermission('edit_market')">✕</button>
                  } @else if (entry.photo_url) {
                    <button class="btn btn-xs btn-photo btn-photo-empty" (click)="triggerPhotoUpload(entry, $event, 2)"
                            [disabled]="uploadingPhotoFor() === entry.id || !hasPermission('edit_market')" title="Subir 2ª foto">
                      {{ uploadingPhotoFor() === entry.id && uploadingPhotoSlot() === 2 ? '⏳ Subiendo...' : '➕ Foto 2' }}
                    </button>
                  }
                </div>
              </div>
            </div>
          }
        </div>

        @if (mercadoHasMore()) {
          <div #mercadoSentinel class="infinite-sentinel" aria-hidden="true"></div>
        }
        @if (mercadoLoading() && mercadoEntries().length > 0) {
          <div class="loading">Cargando más...</div>
        }
        @if (!mercadoHasMore() && !mercadoLoading() && mercadoEntries().length > 0) {
          <p class="results-count" style="margin-top: 1rem;">— Fin del mercado —</p>
        }
      </div>
    }

    <!-- ═══ TAB: PEDIDOS (Pendientes) ═══ -->
    @if (activeTab() === 'pedidos' && canUseWorkspaceContent()) {
      <div class="tab-content">
        <div class="orders-toolbar">
          <button class="btn btn-sm" (click)="loadPendingOrders()">🔄 Recargar</button>
        </div>

        @if (ordersLoading()) {
          <div class="loading">Cargando pedidos...</div>
        }

        @if (!ordersLoading() && pendingOrders().length === 0) {
          <div class="empty-state">
            <p>No tienes pedidos pendientes.</p>
          </div>
        }

        <div class="orders-grid">
          @for (o of pendingOrders(); track o.id) {
            <div class="order-card">
              <div class="order-head">
                <h4>Pedido #{{ o.id }}</h4>
                <span class="order-status pending">{{ orderStatusLabel(o.status) }}</span>
              </div>
              <p class="order-meta">Comprador: <strong>{{ o.buyer_name || o.buyer_username || 'Anónimo' }}</strong></p>
              <p class="order-meta">WhatsApp: <strong>{{ o.buyer_whatsapp || '—' }}</strong></p>
              <p class="order-meta">Creado: {{ o.created_at | date:'short' }}</p>
              @if (o.total_estimated != null) {
                <p class="order-meta">Total estimado: <strong>\${{ o.total_estimated | number:'1.0-0':'es-CL' }}</strong></p>
              }
              @if (o.buyer_note) {
                <p class="order-note">📝 {{ o.buyer_note }}</p>
              }
              <div class="order-items">
                @for (it of o.items; track it.id) {
                  <div class="order-item-row">
                    <span>{{ it.quantity }}x {{ it.card_name || it.card_data?.name || ('Carta #' + it.card) }}</span>
                    <span>
                      @if (it.line_total != null) {
                        \${{ it.line_total | number:'1.0-0':'es-CL' }}
                      } @else {
                        —
                      }
                    </span>
                  </div>
                }
              </div>
              <div class="order-actions">
                <button class="btn btn-sm btn-primary" (click)="acceptOrder(o)" [disabled]="!hasPermission('accept_orders')">✅ Aceptar</button>
                <button class="btn btn-sm btn-danger" (click)="cancelOrder(o)" [disabled]="!hasPermission('reject_orders')">❌ Cancelar</button>
              </div>
            </div>
          }
        </div>
      </div>
    }

    <!-- ═══ TAB: HISTORIAL (Aceptados/Cancelados) ═══ -->
    @if (activeTab() === 'historial' && canUseWorkspaceContent()) {
      <div class="tab-content">
        <div class="orders-toolbar">
          <select [value]="historyStatusFilter()" (change)="onHistoryFilterChange($any($event.target).value)">
            <option value="">Todos</option>
            <option value="accepted">Aceptados</option>
            <option value="cancelled">Cancelados</option>
          </select>
          <button class="btn btn-sm" (click)="loadHistoryOrders()">🔄 Recargar</button>
        </div>

        @if (historyLoading()) {
          <div class="loading">Cargando historial...</div>
        }

        @if (!historyLoading() && historyOrders().length === 0) {
          <div class="empty-state">
            <p>No hay pedidos en historial para este filtro.</p>
          </div>
        }

        <div class="orders-grid history-grid">
          @for (o of historyOrders(); track o.id) {
            <div class="order-card">
              <div class="order-head">
                <h4>Pedido #{{ o.id }}</h4>
                <span class="order-status" [class.accepted]="o.status === 'accepted'" [class.cancelled]="o.status === 'cancelled'">
                  {{ orderStatusLabel(o.status) }}
                </span>
              </div>
              <p class="order-meta">Comprador: <strong>{{ o.buyer_name || o.buyer_username || 'Anónimo' }}</strong></p>
              <p class="order-meta">Creado: {{ o.created_at | date:'short' }}</p>
              <p class="order-meta">Cierre: {{ o.responded_at ? (o.responded_at | date:'short') : '—' }}</p>
              @if (o.responded_by_username) {
                <p class="order-meta">Gestionado por: <strong>{{ o.responded_by_username }}</strong></p>
              }
              @if (o.total_estimated != null) {
                <p class="order-meta">Total estimado: <strong>\${{ o.total_estimated | number:'1.0-0':'es-CL' }}</strong></p>
              }
              @if (o.buyer_note) {
                <p class="order-note">📝 {{ o.buyer_note }}</p>
              }
              @if (o.seller_note) {
                <p class="order-note">Nota vendedor: {{ o.seller_note }}</p>
              }
              <div class="order-items">
                @for (it of o.items; track it.id) {
                  <div class="order-item-row">
                    <span>{{ it.quantity }}x {{ it.card_name || it.card_data?.name || ('Carta #' + it.card) }}</span>
                    <span>
                      @if (it.line_total != null) {
                        \${{ it.line_total | number:'1.0-0':'es-CL' }}
                      } @else {
                        —
                      }
                    </span>
                  </div>
                }
              </div>
            </div>
          }
        </div>
      </div>
    }

    @if (activeTab() === 'stats' && canUseWorkspaceContent()) {
      <div class="tab-content">
        @if (statsLoading()) {
          <p class="loading">Calculando estadísticas...</p>
        } @else if (stats()) {
          <div class="stats-overview">
            <div class="stat-card-s">
              <div class="stat-big">{{ stats()!.total_cards | number }}</div>
              <div class="stat-desc">Cartas totales</div>
            </div>
            <div class="stat-card-s">
              <div class="stat-big">{{ stats()!.unique_cards | number }}</div>
              <div class="stat-desc">Cartas únicas</div>
            </div>
            <div class="stat-card-s">
              <div class="stat-big">{{ stats()!.set_completeness.length }}</div>
              <div class="stat-desc">Sets tocados</div>
            </div>
          </div>

          @if (stats()!.set_completeness.length) {
            <h3 class="stats-heading">Completitud por Set</h3>
            <div class="completeness-grid">
              @for (ed of stats()!.set_completeness; track ed.set) {
                <div class="completeness-item">
                  <div class="completeness-label">{{ ed.name }} <small>({{ ed.set }})</small></div>
                  <div class="completeness-bar-wrap">
                    <div class="completeness-bar" [style.width.%]="ed.pct"></div>
                  </div>
                  <span class="completeness-pct">{{ ed.owned }}/{{ ed.total }} ({{ ed.pct }}%)</span>
                </div>
              }
            </div>
          }

          @if (stats()!.by_type.length) {
            <h3 class="stats-heading">Por Tipo</h3>
            <div class="stats-dist">
              @for (r of stats()!.by_type; track r.key) {
                <div class="dist-row">
                  <span class="dist-label">{{ typeLabel(r.key) }}</span>
                  <span class="dist-count">{{ r.count }}</span>
                </div>
              }
            </div>
          }

          @if (stats()!.by_rarity.length) {
            <h3 class="stats-heading">Por Rareza</h3>
            <div class="stats-dist">
              @for (r of stats()!.by_rarity; track r.key) {
                <div class="dist-row">
                  <span class="dist-label">{{ rarityLabel(r.key) }}</span>
                  <span class="dist-count">{{ r.count }}</span>
                </div>
              }
            </div>
          }

          @if (stats()!.by_color.length) {
            <h3 class="stats-heading">Por Color</h3>
            <div class="stats-dist">
              @for (r of stats()!.by_color; track r.key) {
                <div class="dist-row">
                  <span class="dist-label" [style.color]="colorHex(r.key)">● {{ colorLabel(r.key) }}</span>
                  <span class="dist-count">{{ r.count }}</span>
                </div>
              }
            </div>
          }
        } @else if (statsError()) {
          <p class="error">{{ statsError() }}</p>
        }
      </div>
    }

    @if (activeTab() === 'permisos' && canUseWorkspaceContent() && canManagePermissions()) {
      <div class="tab-content">
        <div class="permissions-panel">
          <h3>Gestionar colaboradores</h3>
          <p class="hint">Asigna permisos por acción. No se usan roles fijos.</p>

          <div class="permissions-create-row">
            <input
              type="text"
              placeholder="Usuario o email"
              [(ngModel)]="newCollaboratorUser"
              maxlength="120" />
            <button class="btn btn-primary btn-sm" (click)="grantCollaboratorAccess()" [disabled]="permissionsSaving()">
              {{ permissionsSaving() ? '⏳ Guardando...' : '➕ Dar acceso' }}
            </button>
          </div>

          <div class="permissions-grid">
            @for (key of permissionKeys; track key) {
              <label class="perm-check">
                <input type="checkbox" [checked]="newCollaboratorPerms()[key]" (change)="toggleNewCollaboratorPerm(key, $any($event.target).checked)" />
                <span>{{ permissionLabel(key) }}</span>
              </label>
            }
          </div>
        </div>

        <div class="permissions-list">
          @if (workspacePermissionsLoading()) {
            <div class="loading">Cargando permisos...</div>
          }
          @if (!workspacePermissionsLoading() && collaboratorPermissions().length === 0) {
            <div class="empty-state"><p>No hay colaboradores con permisos en esta tienda.</p></div>
          }
          @for (row of collaboratorPermissions(); track row.id) {
            <div class="permission-row-card">
              <div class="permission-row-head">
                <strong>{{ row.username }}</strong>
                <div class="permission-row-actions">
                  <button class="btn btn-xs btn-primary" (click)="saveCollaboratorPermissions(row)" [disabled]="permissionsSaving()">Guardar</button>
                  <button class="btn btn-xs btn-danger" (click)="removeCollaboratorPermissions(row)" [disabled]="permissionsSaving()">Quitar acceso</button>
                </div>
              </div>
              <div class="permissions-grid">
                @for (key of permissionKeys; track key) {
                  <label class="perm-check">
                    <input type="checkbox" [checked]="collaboratorPermValue(row, key)"
                           (change)="toggleCollaboratorPerm(row.id, key, $any($event.target).checked)" />
                    <span>{{ permissionLabel(key) }}</span>
                  </label>
                }
              </div>
            </div>
          }
        </div>
      </div>
    }

    @if (showFloatingSaveButton()) {
      <button class="floating-save-btn" (click)="onFloatingSaveClick()" [disabled]="batchSaving()">
        {{ floatingSaveLabel() }}
      </button>
    }

    <!-- ═══ MODAL: Preview ═══ -->
    @if (previewCard(); as pc) {
      <div class="modal-overlay" (click)="previewCard.set(null)">
        <div class="modal modal-detail" (click)="$event.stopPropagation()">
          <button class="close-btn" (click)="previewCard.set(null)">✕</button>
          @if (cardImageUrl(pc) && !isCardImageBroken(pc)) {
            <img [src]="cardImageUrl(pc)" [alt]="pc.name" class="detail-image"
                 (error)="onCardImageError(pc, $event)" />
          }
          <div class="detail-info">
            <h2>{{ pc.name }}</h2>
            <div class="detail-meta">
              <span class="badge">{{ typeLabel(pc.card_type) }}</span>
              <span class="badge rarity">{{ rarityLabel(pc.rarity) }}</span>
              @for (c of pc.colors; track c) {
                <span class="badge color" [style.--c]="colorHex(c)">{{ colorLabel(c) }}</span>
              }
            </div>
            <div class="detail-stats">
              @if (pc.energy !== null && pc.energy !== undefined) { <span>⚡ Energía: {{ pc.energy }}</span> }
              @if (pc.power !== null && pc.power !== undefined) { <span>🛡️ Power: {{ pc.power }}</span> }
              @if (pc.might !== null && pc.might !== undefined) { <span>⚔️ Might: {{ pc.might }}</span> }
            </div>
            @if (pc.description) {
              <div class="detail-ability">
                <h4>Texto</h4>
                <p>{{ pc.description }}</p>
              </div>
            }
            <p class="detail-edition">{{ pc.card_number }}</p>
            <app-tcg-price [cardName]="pc.name" [compact]="false" [showLink]="true"></app-tcg-price>
            <div class="detail-actions">
              <button class="btn btn-primary" (click)="quickAddToCollection(pc, $event); previewCard.set(null)"
                [disabled]="!hasPermission('edit_collection')">
                <app-icon name="plus" [size]="14"></app-icon> Añadir a Carpeta
              </button>
              <button class="btn btn-heart-lg" [class.active]="isInWishlist(pc.id)"
                      (click)="toggleWishlist(pc.id, $event)">
                <i class="bi" [class.bi-heart-fill]="isInWishlist(pc.id)" [class.bi-heart]="!isInWishlist(pc.id)"></i>
                {{ isInWishlist(pc.id) ? ' En Wishlist' : ' Wishlist' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    }

    <!-- ═══ MODAL: Foto real en grande ═══ -->
    @if (viewPhotoUrl(); as purl) {
      <div class="modal-overlay" (click)="closePhotoModal()">
        <div class="modal modal-photo" (click)="$event.stopPropagation()">
          <button class="close-btn" (click)="closePhotoModal()">✕</button>
          <img [src]="purl" alt="Foto real" class="full-photo" />
        </div>
      </div>
    }
  </div>
  `,
  styles: [`
    :host { display: block; min-height: 100vh; background: #0f0f23; color: #c8c8da; }
    .carpeta-container { max-width: 1400px; margin: 0 auto; padding: 1.5rem; }
    @media (max-width: 600px) { .carpeta-container { padding: 1rem 0.65rem 2rem; } }

    .carpeta-header {
      display: flex; align-items: center; gap: 1.2rem;
      padding: 1.2rem; margin-bottom: 1.5rem;
      background: linear-gradient(135deg, #16213e, #1a1a2e);
      border: 1px solid #2a3a4a; border-radius: 12px;
    }
    .binder-avatar-wrap {
      position: relative; width: 72px; height: 72px;
    }
    .binder-avatar {
      width: 72px; height: 72px; border-radius: 12px;
      border: 2px solid #e94560; object-fit: cover; display: block;
    }
    .binder-avatar-placeholder {
      width: 72px; height: 72px; border-radius: 12px;
      background: #0f0f23; border: 2px solid #e94560;
      display: flex; align-items: center; justify-content: center;
      font-size: 2rem;
    }
    .avatar-edit-btn {
      position: absolute; bottom: -6px; right: -6px;
      width: 26px; height: 26px; border-radius: 50%;
      border: 1px solid #e94560; background: #16213e; color: #e94560;
      cursor: pointer; font-size: .75rem;
      display: flex; align-items: center; justify-content: center;
    }
    .avatar-edit-btn:hover { background: #e94560; color: #fff; }
    .binder-info h1 { margin: 0; font-size: 1.6rem; color: #fff;
      background: linear-gradient(90deg, #e94560, #fff); -webkit-background-clip: text;
      -webkit-text-fill-color: transparent; background-clip: text; }
    .binder-user { margin: .25rem 0 0; color: #9ba3b4; font-size: .95rem; }

    .workspace-panel {
      display: grid;
      grid-template-columns: minmax(260px, 360px) 1fr;
      gap: .8rem;
      align-items: start;
      margin-bottom: 1rem;
      padding: .8rem;
      border: 1px solid #2a3a4a;
      border-radius: 10px;
      background: rgba(22, 33, 62, 0.45);
    }
    .workspace-field { display: flex; flex-direction: column; gap: .3rem; }
    .workspace-field label { color: #9ba3b4; font-size: .8rem; }
    .workspace-field select {
      padding: .45rem .6rem;
      border: 1px solid #2a3a4a;
      border-radius: 6px;
      background: #0f0f23;
      color: #fff;
    }
    .workspace-perms { display: flex; flex-wrap: wrap; gap: .35rem; }
    .perm-chip {
      display: inline-flex;
      align-items: center;
      border-radius: 999px;
      padding: .2rem .55rem;
      font-size: .76rem;
      border: 1px solid #2a3a4a;
      color: #dbe7ff;
      background: #1a2b48;
    }
    @media (max-width: 760px) {
      .workspace-panel { grid-template-columns: 1fr; }
    }

    .tabs {
      display: flex; gap: .5rem; flex-wrap: wrap;
      border-bottom: 2px solid #2a3a4a; margin-bottom: 1.5rem;
    }
    .tab {
      padding: .7rem 1.2rem; background: transparent; color: #9ba3b4;
      border: none; border-bottom: 3px solid transparent;
      font-weight: 600; cursor: pointer; transition: all .15s;
      display: inline-flex; align-items: center; gap: .4rem;
    }
    .tab:hover { color: #fff; }
    .tab.active { color: #e94560; border-bottom-color: #e94560; }

    .tab-toolbar { display: flex; gap: .8rem; align-items: center; flex-wrap: wrap; margin-bottom: 1rem; }
    .share-row { display: inline-flex; gap: .5rem; align-items: center; flex-wrap: wrap; }
    .share-message-input {
      padding: .35rem .6rem; border-radius: 6px;
      border: 1px solid #2a3a4a; background: #0f0f23; color: #fff;
      font-size: .85rem; min-width: 220px;
    }
    .share-message-input::placeholder { color: #6b7a8a; }
    @media (max-width: 600px) {
      .share-row {
        display: flex;
        width: 100%;
        flex-direction: column;
        align-items: stretch;
        gap: .5rem;
      }
      .share-row .share-message-input { min-width: 0; width: 100%; }
      .share-row .btn { width: 100%; justify-content: center; }
      .share-row app-share-image { display: block; width: 100%; }
    }
    .search-bar { display: flex; gap: .4rem; flex: 1; min-width: 240px; }
    .search-bar input {
      flex: 1; padding: .55rem .8rem; background: #0f0f23;
      border: 1px solid #2a3a4a; border-radius: 6px; color: #c8c8da;
    }
    .search-bar input:focus { outline: none; border-color: #e94560; }

    .filter-row { display: flex; gap: .6rem; flex-wrap: wrap; margin-bottom: 1rem; align-items: center; }
    .filter-row select {
      padding: .5rem .7rem; background: #0f0f23; color: #c8c8da;
      border: 1px solid #2a3a4a; border-radius: 6px; cursor: pointer;
    }
    .filter-row select:focus { outline: none; border-color: #e94560; }

    .color-chips { display: flex; gap: .35rem; flex-wrap: wrap; }
    .chip {
      padding: .35rem .7rem; border-radius: 999px; cursor: pointer;
      border: 1px solid var(--c, #2a3a4a); background: transparent; color: #c8c8da;
      font-size: .8rem; font-weight: 600; transition: all .15s;
    }
    .chip:hover, .chip.active { background: var(--c, #e94560); color: #fff; }

    .results-count { color: #9ba3b4; font-size: .9rem; margin: .5rem 0 1rem; }
    .loading { color: #9ba3b4; padding: 2rem; text-align: center; }
    .empty-state { padding: 3rem 1rem; text-align: center; color: #9ba3b4;
      background: #16213e; border: 1px dashed #2a3a4a; border-radius: 12px; }
    .error { color: #e94560; padding: 1rem; }

    /* Botones */
    .btn { padding: .5rem .9rem; border: 1px solid #2a3a4a; background: transparent;
      color: #c8c8da; border-radius: 6px; cursor: pointer; font-weight: 600; transition: all .15s; }
    .btn:hover:not(:disabled) { background: #1e2d3d; }
    .btn:disabled { opacity: .5; cursor: not-allowed; }
    .btn-sm { padding: .4rem .75rem; font-size: .85rem; }
    .btn-xs { padding: .25rem .55rem; font-size: .78rem; }
    .btn-primary { background: #e94560; border-color: #e94560; color: #fff; }
    .btn-primary:hover:not(:disabled) { background: #d63950; border-color: #d63950; }
    .btn-danger { background: transparent; border-color: #e94560; color: #e94560; }
    .btn-danger:hover:not(:disabled) { background: #e94560; color: #fff; }
    .btn-heart-lg.active { background: #e94560; color: #fff; border-color: #e94560; }

    .orders-toolbar {
      display: flex;
      align-items: center;
      justify-content: flex-end;
      gap: .55rem;
      margin-bottom: .8rem;
      flex-wrap: wrap;
    }
    .orders-toolbar select {
      background: #16213e;
      border: 1px solid #2a3a4a;
      color: #e7edf8;
      border-radius: 8px;
      padding: .45rem .6rem;
    }
    .orders-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: .9rem;
    }
    .order-card {
      background: rgba(22, 33, 62, 0.6);
      border: 1px solid #2a3a4a;
      border-radius: 12px;
      padding: .8rem;
      display: flex;
      flex-direction: column;
      gap: .35rem;
    }
    .order-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: .5rem;
    }
    .order-head h4 {
      margin: 0;
      color: #fff;
      font-size: .98rem;
    }
    .order-status {
      font-size: .75rem;
      border-radius: 999px;
      padding: .18rem .55rem;
      border: 1px solid #2a3a4a;
      color: #c8d4ea;
    }
    .order-status.pending {
      border-color: #f6c85f;
      color: #ffe6a6;
      background: rgba(246, 200, 95, 0.15);
    }
    .order-status.accepted {
      border-color: #5abf90;
      color: #b9f5d8;
      background: rgba(90, 191, 144, 0.15);
    }
    .order-status.cancelled {
      border-color: #d95f5f;
      color: #ffd0d0;
      background: rgba(217, 95, 95, 0.15);
    }
    .order-meta {
      margin: 0;
      color: #c7cfdd;
      font-size: .84rem;
    }
    .order-note {
      margin: .1rem 0 0;
      color: #b5c0d8;
      font-size: .82rem;
      background: rgba(15, 23, 42, 0.45);
      border: 1px solid rgba(42, 58, 74, 0.6);
      border-radius: 8px;
      padding: .4rem .55rem;
      white-space: pre-wrap;
    }
    .order-items {
      margin-top: .25rem;
      border-top: 1px dashed #2a3a4a;
      padding-top: .35rem;
      display: flex;
      flex-direction: column;
      gap: .25rem;
    }
    .order-item-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: .7rem;
      font-size: .82rem;
      color: #d7e0ef;
    }
    .order-actions {
      margin-top: .45rem;
      display: flex;
      gap: .45rem;
      flex-wrap: wrap;
    }
    .order-actions .btn { flex: 1 1 0; min-width: 120px; }
    .history-grid .order-actions { display: none; }

    /* Grids */
    .collection-grid, .wishlist-grid {
      display: grid; gap: 1rem;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
    }
    .card-grid {
      display: grid; gap: .9rem;
      grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
    }
    @media (max-width: 600px) {
      .collection-grid, .wishlist-grid {
        grid-template-columns: 1fr;
        gap: .6rem;
      }
      .card-grid {
        grid-template-columns: repeat(auto-fit, minmax(78px, 1fr));
        gap: .5rem;
      }
      .card-item .card-info { padding: .4rem; }
      .card-item .card-info h4 { font-size: .68rem; }
      .card-item .card-info .card-type { display: none; }
      .wishlist-card .share-check {
        width: 22px; height: 22px; top: 4px; left: 4px; font-size: .7rem;
      }
    }

    @media (max-width: 360px) {
      .card-grid {
        grid-template-columns: repeat(auto-fit, minmax(70px, 1fr));
      }
    }

    .collection-card, .wishlist-card {
      background: #16213e; border: 1px solid #2a3a4a; border-radius: 10px;
      overflow: hidden; display: flex; flex-direction: column;
      position: relative;
    }
    .wishlist-card.is-share-selected {
      border-color: #e94560;
      box-shadow: 0 0 0 2px rgba(233,69,96,.35);
    }
    .wishlist-card .share-check {
      position: absolute; top: 8px; left: 8px; z-index: 5;
      width: 28px; height: 28px; display: flex; align-items: center; justify-content: center;
      background: rgba(0,0,0,.65); color: #fff; border-radius: 6px;
      cursor: pointer; font-size: .85rem;
      border: 1px solid rgba(255,255,255,.18);
    }
    .wishlist-card .share-check input { position: absolute; opacity: 0; inset: 0; cursor: pointer; }
    .wishlist-card .share-check i { pointer-events: none; opacity: .75; }
    .wishlist-card.is-share-selected .share-check {
      background: #e94560; border-color: #e94560;
    }
    .wishlist-card.is-share-selected .share-check i { opacity: 1; }
    .collection-card .card-image, .wishlist-card .card-image, .card-item .card-image {
      position: relative; aspect-ratio: 5/7; background: #0f0f23; overflow: hidden; cursor: pointer;
    }
    .card-image img { width: 100%; height: 100%; object-fit: cover; display: block; transition: transform .2s; }
    .card-image:hover img { transform: scale(1.04); }
    @media (max-width: 600px) {
      .card-image img {
        object-fit: contain;
        background: #0b0b1a;
      }
    }
    .img-fallback {
      width: 100%; height: 100%; display: flex; align-items: center; justify-content: center;
      color: #6b7280; font-weight: 700;
    }
    .eye-overlay {
      position: absolute; top: 8px; right: 8px;
      background: rgba(0,0,0,.65); color: #fff; padding: .3rem .5rem;
      border-radius: 6px; font-size: .85rem; opacity: 0; transition: opacity .15s;
    }
    .card-image:hover .eye-overlay { opacity: 1; }
    .foil-badge {
      position: absolute; bottom: 8px; left: 8px;
      background: linear-gradient(135deg, #4fc3f7, #e94560);
      color: #fff; padding: .2rem .5rem; border-radius: 4px;
      font-size: .7rem; font-weight: 700;
    }
    .owned-badge {
      position: absolute; top: 8px; left: 8px;
      background: #2a8a8a; color: #fff; padding: .25rem .5rem;
      border-radius: 6px; font-size: .8rem; font-weight: 700;
    }

    .card-body, .card-info { padding: .65rem .75rem .8rem; }
    .card-body h4, .card-info h4 {
      margin: 0 0 .25rem; font-size: .95rem; color: #fff;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .card-meta, .card-type { color: #9ba3b4; font-size: .78rem; }

    .inline-fields { display: flex; gap: .5rem; align-items: flex-end; margin-top: .6rem; flex-wrap: wrap; }

    .card-photo-row { display: flex; flex-wrap: wrap; gap: .35rem; margin-top: .55rem; }
    .btn-photo { display: inline-flex; align-items: center; gap: .35rem; padding: .25rem .5rem;
      background: #1e2235; color: #e5e7eb; border: 1px solid #374151; border-radius: 6px;
      font-size: .72rem; cursor: pointer; }
    .btn-photo:hover:not(:disabled) { background: #2a3553; }
    .btn-photo-empty { border-style: dashed; color: #9ba3b4; }
    .photo-thumb { width: 22px; height: 22px; object-fit: cover; border-radius: 3px; }
    .btn-photo-action { padding: .25rem .45rem; background: #1e2235; color: #e5e7eb;
      border: 1px solid #374151; border-radius: 6px; font-size: .72rem; cursor: pointer; }
    .btn-danger { background: #4a1d27 !important; border-color: #7f1d1d !important; color: #fecaca !important; }
    .modal-photo { background: #0f0f23; padding: .6rem; border-radius: 10px; max-width: 92vw; max-height: 92vh; }
    .full-photo { display: block; max-width: 88vw; max-height: 80vh; object-fit: contain; border-radius: 6px; }
    .field { display: flex; flex-direction: column; gap: .15rem; min-width: 60px; flex: 1; }
    .field.full { flex-basis: 100%; margin-top: .4rem; }
    .field label { color: #9ba3b4; font-size: .72rem; text-transform: uppercase; }
    .field input, .field select {
      padding: .35rem .5rem; background: #0f0f23; color: #c8c8da;
      border: 1px solid #2a3a4a; border-radius: 5px; font-size: .85rem; width: 100%;
    }
    .field input:focus, .field select:focus { outline: none; border-color: #e94560; }
    .foil-toggle {
      display: inline-flex; align-items: center; gap: .35rem;
      font-size: .8rem; color: #c8c8da; cursor: pointer; padding-bottom: .35rem;
    }
    .card-action-row { display: flex; gap: .35rem; margin-top: .6rem; justify-content: flex-end; align-items: center; }

    .tcg-ref-row {
      display: flex; align-items: center; gap: .4rem; margin-top: .5rem; flex-wrap: wrap;
    }
    .tcg-ref-label { font-size: .72rem; color: #9ba3b4; text-transform: uppercase; }

    /* Codex card */
    .card-item {
      background: #16213e; border: 1px solid #2a3a4a; border-radius: 10px;
      overflow: hidden; cursor: pointer; position: relative; transition: all .15s;
    }
    .card-item:hover { border-color: #e94560; transform: translateY(-2px); }
    .card-overlay-actions {
      position: absolute; bottom: 78px; right: 8px;
      display: flex; flex-direction: column; gap: .3rem; opacity: 0; transition: opacity .15s;
    }
    .card-item:hover .card-overlay-actions { opacity: 1; }
    .btn-icon {
      width: 32px; height: 32px; border-radius: 50%;
      border: 1px solid #2a3a4a; background: rgba(15,15,35,.9); color: #fff;
      display: flex; align-items: center; justify-content: center; cursor: pointer;
    }
    .btn-icon.btn-add:hover { background: #2a8a8a; border-color: #2a8a8a; }
    .btn-icon.btn-heart { color: #9ba3b4; }
    .btn-icon.btn-heart.active, .btn-icon.btn-heart:hover { color: #e94560; border-color: #e94560; }

    /* Wishlist qty */
    .wishlist-qty { display: flex; align-items: center; gap: .4rem; margin-top: .5rem; }
    .wishlist-qty label { font-size: .8rem; color: #9ba3b4; }
    .wishlist-qty input {
      width: 60px; padding: .3rem .4rem; background: #0f0f23; color: #c8c8da;
      border: 1px solid #2a3a4a; border-radius: 5px;
    }
    .card-actions { padding: .4rem .75rem .75rem; display: flex; justify-content: flex-end; }

    .infinite-sentinel {
      width: 100%;
      height: 1px;
      margin-top: .5rem;
    }

    /* Stats */
    .stats-overview {
      display: grid; gap: 1rem;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      margin-bottom: 1.5rem;
    }
    .stat-card-s {
      background: linear-gradient(135deg, #16213e, #1a1a2e);
      border: 1px solid #2a3a4a; border-radius: 12px;
      padding: 1.5rem; text-align: center;
    }
    .stat-big { font-size: 2.4rem; font-weight: 800; color: #e94560; }
    .stat-desc { color: #9ba3b4; font-size: .9rem; margin-top: .3rem; }
    .stats-heading { color: #fff; margin: 1.5rem 0 .8rem; font-size: 1.1rem; border-left: 3px solid #e94560; padding-left: .6rem; }
    .completeness-grid { display: grid; gap: .7rem; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }
    .completeness-item {
      background: #16213e; border: 1px solid #2a3a4a; border-radius: 8px; padding: .7rem .9rem;
      display: flex; flex-direction: column; gap: .35rem;
    }
    .completeness-label { color: #fff; font-weight: 600; }
    .completeness-label small { color: #9ba3b4; font-weight: 400; }
    .completeness-bar-wrap {
      width: 100%; height: 8px; background: #0f0f23; border-radius: 4px; overflow: hidden;
    }
    .completeness-bar {
      height: 100%; background: linear-gradient(90deg, #2a8a8a, #4fc3f7);
      border-radius: 4px; transition: width .3s;
    }
    .completeness-pct { color: #9ba3b4; font-size: .82rem; }
    .stats-dist {
      display: grid; gap: .35rem; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    }
    .dist-row {
      display: flex; justify-content: space-between; align-items: center;
      background: #16213e; border: 1px solid #2a3a4a; border-radius: 6px;
      padding: .5rem .8rem;
    }
    .dist-label { color: #c8c8da; }
    .dist-count { color: #e94560; font-weight: 700; }

    /* Modal */
    .modal-overlay {
      position: fixed; inset: 0; background: rgba(0,0,0,.85);
      display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 1rem;
    }
    .modal-detail {
      background: #16213e; border: 1px solid #2a3a4a; border-radius: 14px;
      max-width: 760px; width: 100%; max-height: 90vh; overflow-y: auto;
      display: grid; grid-template-columns: 1fr 1.2fr; gap: 0; position: relative;
    }
    @media (max-width: 640px) {
      .modal-detail { grid-template-columns: 1fr; }
      .modal-detail .detail-image {
        max-height: 58vh;
        width: auto;
        max-width: 100%;
        margin: 0 auto;
        border-radius: 14px;
      }
    }
    .modal-detail .detail-image { width: 100%; height: auto; border-radius: 14px 0 0 14px; display: block; }
    .modal-detail .detail-info { padding: 1.4rem; display: flex; flex-direction: column; gap: .8rem; }
    .modal-detail h2 { margin: 0; color: #fff; }
    .detail-meta { display: flex; gap: .4rem; flex-wrap: wrap; }
    .badge {
      padding: .25rem .55rem; border-radius: 6px; font-size: .8rem;
      border: 1px solid #2a3a4a; background: #0f0f23;
    }
    .badge.rarity { background: #c89b3c30; border-color: #c89b3c; color: #c89b3c; }
    .badge.color { background: color-mix(in srgb, var(--c) 15%, transparent); border-color: var(--c); color: var(--c); }
    .detail-stats { display: flex; gap: 1rem; flex-wrap: wrap; color: #c8c8da; font-size: .9rem; }
    .detail-ability { background: #0f0f23; border-radius: 8px; padding: .75rem 1rem; border-left: 3px solid #e94560; }
    .detail-ability h4 { margin: 0 0 .35rem; color: #4fc3f7; font-size: .85rem; }
    .detail-ability p { margin: 0; color: #c8c8da; font-size: .9rem; white-space: pre-wrap; }
    .detail-edition { color: #9ba3b4; font-size: .85rem; margin: 0; }
    .btn-tcg {
      display: inline-flex; align-items: center; gap: .4rem;
      margin-top: .8rem; padding: .55rem 1rem; border-radius: 8px;
      background: linear-gradient(135deg, #1a6bc4, #0d4a8e); border: 1px solid #2980d9;
      color: #fff; font-weight: 700; font-size: .9rem; text-decoration: none;
      transition: background .2s, transform .15s;
    }
    .btn-tcg:hover { background: linear-gradient(135deg, #2980d9, #1a6bc4); transform: translateY(-1px); }
    .detail-actions { display: flex; gap: .6rem; flex-wrap: wrap; margin-top: auto; }
    .close-btn {
      position: absolute; top: .5rem; right: .5rem;
      background: rgba(15,15,35,.85); border: 1px solid #2a3a4a; color: #fff;
      width: 32px; height: 32px; border-radius: 50%; cursor: pointer; z-index: 2;
    }
    .close-btn:hover { background: #e94560; border-color: #e94560; }

    /* Bulk import */
    .bulk-import-panel {
      background: #16213e; border: 1px solid #2a3a4a; border-radius: 10px;
      padding: 1rem; margin-bottom: 1rem;
    }
    .bulk-import-panel h4 { margin: 0 0 .4rem; color: #fff; }
    .bulk-import-panel .hint { color: #9ba3b4; font-size: .82rem; margin: 0 0 .6rem; }
    .bulk-import-panel .hint code { background: #0f0f23; padding: .1rem .35rem; border-radius: 3px; }
    .bulk-import-panel textarea {
      width: 100%; background: #0f0f23; color: #c8c8da;
      border: 1px solid #2a3a4a; border-radius: 6px; padding: .6rem;
      font-family: monospace; font-size: .85rem;
    }
    .bulk-mode { display: flex; gap: 1rem; margin: .6rem 0; }
    .bulk-mode label { color: #c8c8da; font-size: .9rem; display: inline-flex; gap: .35rem; align-items: center; }
    .bulk-actions { display: flex; gap: .5rem; }
    .bulk-result { margin-top: .8rem; padding: .6rem .8rem; background: #0f0f23;
      border-left: 3px solid #2a8a8a; border-radius: 6px; }
    .bulk-result p { margin: 0 0 .5rem; color: #c8c8da; font-size: .9rem; }
    .bulk-result details { margin-top: .35rem; }
    .bulk-result summary { cursor: pointer; color: #4fc3f7; font-size: .85rem; }
    .bulk-result pre {
      background: #16213e; color: #9ba3b4; padding: .5rem;
      border-radius: 5px; font-size: .8rem; max-height: 200px; overflow: auto;
    }

    /* Mercado */
    .mercado-toolbar { display: flex; gap: .6rem; flex-wrap: wrap; margin-bottom: 1rem; }
    .store-config-panel {
      background: #16213e; border: 1px solid #2a3a4a; border-radius: 10px;
      padding: 1rem; margin-bottom: 1rem;
    }
    .store-config-panel h4 { margin: 0 0 .8rem; color: #fff; }
    .form-grid {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: .7rem;
    }
    .form-grid label {
      display: flex; flex-direction: column; gap: .25rem; color: #9ba3b4; font-size: .82rem;
    }
    .form-grid label.full { grid-column: 1 / -1; }
    .form-grid label.check-row {
      flex-direction: row; align-items: center; gap: .55rem;
      color: #c8c8da; font-size: .9rem; cursor: pointer;
    }
    .form-grid label.check-row input[type="checkbox"] {
      width: 18px; height: 18px; accent-color: #e94560; flex-shrink: 0; margin: 0;
    }
    .form-grid input[type="text"],
    .form-grid input[type="email"],
    .form-grid input[type="number"],
    .form-grid textarea,
    .form-grid select {
      padding: .45rem .6rem; background: #0f0f23; color: #c8c8da;
      border: 1px solid #2a3a4a; border-radius: 5px; font-size: .9rem;
    }
    .form-grid input:focus, .form-grid select:focus, .form-grid textarea:focus {
      outline: none; border-color: #e94560;
    }
    .token-row { display: flex; gap: .6rem; align-items: center; color: #9ba3b4; font-size: .85rem; flex-wrap: wrap; }
    .token-row code { background: #0f0f23; padding: .25rem .5rem; border-radius: 4px; color: #4fc3f7; }

    .permissions-panel {
      background: #16213e;
      border: 1px solid #2a3a4a;
      border-radius: 10px;
      padding: .9rem;
      margin-bottom: 1rem;
    }
    .permissions-panel h3 { margin: 0 0 .35rem; color: #fff; }
    .permissions-panel .hint { margin: 0 0 .7rem; color: #9ba3b4; font-size: .84rem; }
    .permissions-create-row {
      display: flex;
      gap: .5rem;
      align-items: center;
      margin-bottom: .7rem;
      flex-wrap: wrap;
    }
    .permissions-create-row input {
      flex: 1;
      min-width: 240px;
      padding: .45rem .6rem;
      border-radius: 6px;
      border: 1px solid #2a3a4a;
      background: #0f0f23;
      color: #fff;
    }
    .permissions-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
      gap: .4rem .7rem;
    }
    .perm-check {
      display: inline-flex;
      align-items: center;
      gap: .45rem;
      color: #d1d8e6;
      font-size: .84rem;
    }
    .permissions-list {
      display: grid;
      gap: .8rem;
    }
    .permission-row-card {
      border: 1px solid #2a3a4a;
      border-radius: 10px;
      padding: .75rem;
      background: rgba(22, 33, 62, 0.45);
    }
    .permission-row-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: .65rem;
      margin-bottom: .65rem;
    }
    .permission-row-actions {
      display: inline-flex;
      gap: .35rem;
      flex-wrap: wrap;
    }

    .floating-save-btn {
      position: fixed;
      right: 1rem;
      bottom: calc(1rem + env(safe-area-inset-bottom, 0px));
      z-index: 220;
      min-height: 44px;
      padding: .65rem .95rem;
      border-radius: 999px;
      border: 1px solid #e94560;
      background: linear-gradient(135deg, #e94560, #c89b3c);
      color: #fff;
      font-weight: 800;
      font-size: .86rem;
      box-shadow: 0 10px 24px rgba(0,0,0,.35);
      cursor: pointer;
      transition: transform .15s ease, filter .15s ease;
    }
    .floating-save-btn:hover:not(:disabled) { transform: translateY(-1px); filter: brightness(1.05); }
    .floating-save-btn:disabled { opacity: .7; cursor: not-allowed; }
  `],
})
export class RiftboundCarpetaComponent implements OnInit, AfterViewInit, OnDestroy {
  readonly rb = inject(RiftboundService);
  readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly cdr = inject(ChangeDetectorRef);

  readonly COLORS = [
    { code: 'fury',    label: 'Fury',    hex: '#e94560' },
    { code: 'calm',    label: 'Calm',    hex: '#4fc3f7' },
    { code: 'mind',    label: 'Mind',    hex: '#9b6ad8' },
    { code: 'body',    label: 'Body',    hex: '#7cb342' },
    { code: 'chaos',   label: 'Chaos',   hex: '#c89b3c' },
    { code: 'order',   label: 'Order',   hex: '#e0e0e0' },
    { code: 'neutral', label: 'Neutral', hex: '#8896a8' },
  ] as const;

  // State
  activeTab = signal<Tab>('carpeta');
  workspaceMode = signal(false);
  workspacesLoading = signal(false);
  workspaces = signal<RiftboundWorkspace[]>([]);
  selectedWorkspaceId = signal<number | null>(null);
  selectedWorkspace = computed(() => this.workspaces().find(w => w.store_profile_id === this.selectedWorkspaceId()) || null);

  // Collection
  collectionEntries = signal<RiftboundCollectionEntry[]>([]);
  collectionTotal = signal(0);
  collectionPage = signal(1);
  collectionSearch = '';
  collectionLoading = signal(false);
  collectionHasMore = signal(false);
  private readonly COLLECTION_PAGE_SIZE = 50;
  @ViewChild('collectionSentinel') collectionSentinelRef?: ElementRef<HTMLElement>;
  private collectionObserver?: IntersectionObserver;
  dirtyEntries = new Map<number, DirtyPatch>();
  batchSaving = signal(false);
  collectionTotalPages = computed(() => Math.max(1, Math.ceil(this.collectionTotal() / this.COLLECTION_PAGE_SIZE)));
  collectionCopies = computed(() => this.collectionEntries().reduce((s, e) => s + (e.quantity || 0), 0));
  collectionSellingCount = computed(() => this.collectionEntries().filter(e => (e.selling_quantity || 0) > 0).length);

  // Codex
  codexCards = signal<RiftboundCardLite[]>([]);
  codexTotal = signal(0);
  codexPage = signal(1);
  codexSearch = '';
  codexLoading = signal(false);
  codexHasMore = signal(false);
  private readonly CODEX_PAGE_SIZE = 40;
  @ViewChild('codexSentinel') codexSentinelRef?: ElementRef<HTMLElement>;
  private codexObserver?: IntersectionObserver;
  sets = signal<RiftboundSet[]>([]);
  selectedSet = '';
  selectedType = '';
  selectedRarity = '';
  selectedColors = new Set<string>();

  // Wishlist
  wishlistEntries = signal<RiftboundWishlistEntry[]>([]);
  wishlistTotal = signal(0);
  wishlistPage = signal(1);
  wishlistSearch = '';
  wishlistLoading = signal(false);
  wishlistHasMore = signal(false);
  @ViewChild('wishlistSentinel') wishlistSentinelRef?: ElementRef<HTMLElement>;
  private wishlistObserver?: IntersectionObserver;

  // Stats
  stats = signal<RiftboundCollectionStats | null>(null);
  statsLoading = signal(false);
  statsError = signal<string | null>(null);

  // Binder profile / Mercado
  binderProfile = signal<RiftboundBinderProfile | null>(null);
  /** IDs (no persistidos) de entradas de wishlist marcadas para incluir en la imagen. */
  wishlistShareSelection = signal<Set<number>>(new Set<number>());
  /** Mensaje personalizable que aparece bajo el titulo en la imagen compartida. */
  wishlistShareMessage = '';
  avatarUploading = signal(false);
  showStoreConfig = signal(false);
  mercadoEntries = signal<RiftboundCollectionEntry[]>([]);
  mercadoLoading = signal(false);
  mercadoPage = signal(1);
  mercadoHasMore = signal(false);
  @ViewChild('mercadoSentinel') mercadoSentinelRef?: ElementRef<HTMLElement>;
  private mercadoObserver?: IntersectionObserver;
  private contentScrollEl: HTMLElement | null = null;
  mercadoDirty = new Map<number, DirtyPatch>();
  exportingPdf = signal(false);
  qrDownloading = signal(false);
  onlySelling = signal(false);

  // Pedidos (vendedor)
  pendingOrders = signal<RiftboundStoreOrder[]>([]);
  historyOrders = signal<RiftboundStoreOrder[]>([]);
  ordersLoading = signal(false);
  historyLoading = signal(false);
  historyStatusFilter = signal<'' | RiftboundStoreOrderStatus>('');

  // Permisos colaboradores
  workspacePermissionsLoading = signal(false);
  permissionsSaving = signal(false);
  collaboratorPermissions = signal<RiftboundStoreCollaboratorPermission[]>([]);
  collaboratorDirty = new Map<number, Partial<RiftboundStorePermissionFlags>>();
  newCollaboratorUser = '';
  newCollaboratorPerms = signal<RiftboundStorePermissionFlags>({
    view_collection: true,
    edit_collection: true,
    delete_collection: false,
    edit_market: true,
    remove_from_market: false,
    view_orders: true,
    view_history: true,
    accept_orders: false,
    reject_orders: false,
    manage_permissions: false,
  });
  readonly permissionKeys: Array<keyof RiftboundStorePermissionFlags> = [
    'view_collection',
    'edit_collection',
    'delete_collection',
    'edit_market',
    'remove_from_market',
    'view_orders',
    'view_history',
    'accept_orders',
    'reject_orders',
    'manage_permissions',
  ];

  // Bulk import
  showBulkImport = signal(false);
  bulkText = '';
  bulkMode: 'add' | 'set' = 'add';
  bulkImporting = signal(false);
  bulkResult = signal<RiftboundBulkImportResult | null>(null);

  // IDs cache
  private collectionIds: { [cardId: number]: number } = {};
  private wishlistIds = new Set<number>();
  private wishlistHydratingCardIds = new Set<number>();
  private wishlistHydratedCards = signal<Map<number, RiftboundCard>>(new Map<number, RiftboundCard>());

  // Preview
  previewCard = signal<RiftboundCardLite | null>(null);
  private imageFallbackStepByCard = new Map<number, number>();
  cardImageBroken = signal<Set<number>>(new Set<number>());

  // Foto real (por entry.id + slot)
  uploadingPhotoFor = signal<number | null>(null);
  uploadingPhotoSlot = signal<1 | 2 | null>(null);
  viewPhotoUrl = signal<string | null>(null);

  triggerPhotoUpload(entry: RiftboundCollectionEntry, ev: Event, slot: 1 | 2 = 1) {
    ev.stopPropagation();
    const input = document.getElementById(`rb-photo-input-${entry.id}-${slot}`) as HTMLInputElement | null;
    input?.click();
  }

  onPhotoSelected(entry: RiftboundCollectionEntry, ev: Event, slot: 1 | 2 = 1) {
    if (!this.hasPermission('edit_market')) {
      alert('No tienes permiso para editar fotos de mercado en esta tienda.');
      return;
    }
    const input = ev.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      alert('Solo se permiten imágenes.');
      input.value = '';
      return;
    }
    if (file.size > 8 * 1024 * 1024) {
      alert('La imagen es muy grande (máx 8 MB).');
      input.value = '';
      return;
    }
    this.uploadingPhotoFor.set(entry.id);
    this.uploadingPhotoSlot.set(slot);
    this.rb.uploadCollectionPhoto(entry.card, file, slot, !!entry.is_foil, this.currentStoreProfileId()).subscribe({
      next: (updated) => {
        entry.photo_url = updated.photo_url;
        entry.photo_url_2 = updated.photo_url_2;
        this.uploadingPhotoFor.set(null);
        this.uploadingPhotoSlot.set(null);
        input.value = '';
        this.cdr.markForCheck();
      },
      error: (err) => {
        console.error('Error subiendo foto:', err);
        alert('No se pudo subir la foto. Intenta de nuevo.');
        this.uploadingPhotoFor.set(null);
        this.uploadingPhotoSlot.set(null);
        input.value = '';
        this.cdr.markForCheck();
      },
    });
  }

  removePhoto(entry: RiftboundCollectionEntry, ev: Event, slot: 1 | 2 = 1) {
    ev.stopPropagation();
    if (!this.hasPermission('edit_market')) {
      alert('No tienes permiso para editar fotos de mercado en esta tienda.');
      return;
    }
    const currentUrl = slot === 2 ? entry.photo_url_2 : entry.photo_url;
    if (!currentUrl) return;
    if (!confirm('¿Quitar esta foto?')) return;
    const patch: any = { card: entry.card, is_foil: !!entry.is_foil };
    patch[slot === 2 ? 'photo_url_2' : 'photo_url'] = '';
    this.rb.upsertCollection(patch, { store_profile_id: this.currentStoreProfileId() }).subscribe(() => {
      if (slot === 2) entry.photo_url_2 = ''; else entry.photo_url = '';
      this.cdr.markForCheck();
    });
  }

  openPhotoModal(url: string | null | undefined, ev?: Event) {
    if (ev) ev.stopPropagation();
    if (!url) return;
    this.viewPhotoUrl.set(url);
  }

  closePhotoModal() { this.viewPhotoUrl.set(null); }

  @HostListener('window:scroll')
  onWindowScroll() { this.tryInfiniteScrollFallback(); }

  @HostListener('window:resize')
  onWindowResize() { this.tryInfiniteScrollFallback(); }

  ngOnInit() {
    if (!this.auth.isAuthenticated()) {
      this.router.navigate(['/login'], { queryParams: { returnUrl: '/riftbound/carpeta' } });
      return;
    }

    this.workspaceMode.set(!!this.route.snapshot.data?.['workspaceMode']);

    if (this.workspaceMode()) {
      this.loadWorkspaces();
    } else {
      this.loadIds();
      this.loadCollection();
      this.loadBinderProfile();
    }

    this.rb.listSets().subscribe(s => {
      // listSets returns paginated or array depending on backend
      const arr = Array.isArray(s) ? s : (s as any).results || [];
      this.sets.set(arr);
      this.cdr.markForCheck();
    });
  }

  ngAfterViewInit() {
    this.setupCollectionObserver();
    this.setupCodexObserver();
    this.setupWishlistObserver();
    this.setupMercadoObserver();
    this.attachContentScrollListener();
    this.tryInfiniteScrollFallback();
  }

  ngOnDestroy() {
    this.collectionObserver?.disconnect();
    this.codexObserver?.disconnect();
    this.wishlistObserver?.disconnect();
    this.mercadoObserver?.disconnect();
    this.detachContentScrollListener();
  }

  canUseWorkspaceContent(): boolean {
    return !this.workspaceMode() || !!this.selectedWorkspaceId();
  }

  private currentStoreProfileId(): number | undefined {
    return this.workspaceMode() ? (this.selectedWorkspaceId() || undefined) : undefined;
  }

  private permissionsStoreProfileId(): number | undefined {
    if (this.workspaceMode()) return this.currentStoreProfileId();
    return this.binderProfile()?.id;
  }

  selectedWorkspacePermissions(): RiftboundStorePermissionFlags {
    if (!this.workspaceMode()) return FULL_STORE_PERMISSIONS;
    return this.selectedWorkspace()?.permissions || {
      view_collection: false,
      edit_collection: false,
      delete_collection: false,
      edit_market: false,
      remove_from_market: false,
      view_orders: false,
      view_history: false,
      accept_orders: false,
      reject_orders: false,
      manage_permissions: false,
    };
  }

  hasPermission(key: keyof RiftboundStorePermissionFlags): boolean {
    return !!this.selectedWorkspacePermissions()[key];
  }

  canManagePermissions(): boolean {
    return this.hasPermission('manage_permissions');
  }

  workspaceLabel(ws: RiftboundWorkspace): string {
    const display = (ws.profile?.display_name || '').trim();
    if (display) return `${display} (@${ws.owner_username})`;
    return `@${ws.owner_username}`;
  }

  onWorkspaceChange(rawValue: string) {
    const id = Number(rawValue);
    if (!Number.isFinite(id) || id <= 0) return;
    this.selectedWorkspaceId.set(id);
    this.applyWorkspaceSelection();
  }

  private loadWorkspaces() {
    this.workspacesLoading.set(true);
    this.rb.listWorkspaces().subscribe({
      next: (res) => {
        const rows = res?.results || [];
        this.workspaces.set(rows);
        this.workspacesLoading.set(false);
        const first = rows[0]?.store_profile_id || null;
        this.selectedWorkspaceId.set(first);
        this.applyWorkspaceSelection();
      },
      error: (err) => {
        this.workspacesLoading.set(false);
        this.workspaces.set([]);
        this.selectedWorkspaceId.set(null);
        alert(err?.error?.detail || 'No se pudieron cargar tus tiendas compartidas.');
        this.cdr.markForCheck();
      },
    });
  }

  private applyWorkspaceSelection() {
    const ws = this.selectedWorkspace();
    if (!ws) {
      this.collectionEntries.set([]);
      this.mercadoEntries.set([]);
      this.pendingOrders.set([]);
      this.historyOrders.set([]);
      this.collaboratorPermissions.set([]);
      this.cdr.markForCheck();
      return;
    }

    this.binderProfile.set(ws.profile);

    if (this.hasPermission('view_collection')) {
      this.loadIds();
      this.loadCollection();
      this.loadMercado();
    } else {
      this.collectionEntries.set([]);
      this.mercadoEntries.set([]);
    }

    if (this.hasPermission('view_orders')) {
      this.loadPendingOrders();
    } else {
      this.pendingOrders.set([]);
    }

    if (this.hasPermission('view_history')) {
      this.loadHistoryOrders();
    } else {
      this.historyOrders.set([]);
    }

    if (this.canManagePermissions()) {
      this.loadWorkspacePermissions();
    } else {
      this.collaboratorPermissions.set([]);
    }

    this.cdr.markForCheck();
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

  private setupCollectionObserver() {
    if (typeof IntersectionObserver === 'undefined') return;
    this.collectionObserver?.disconnect();
    this.collectionObserver = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.isIntersecting
            && this.activeTab() === 'carpeta'
            && this.collectionHasMore()
            && !this.collectionLoading()) {
          this.loadMoreCollection();
        }
      }
    }, { rootMargin: '300px' });
    const el = this.collectionSentinelRef?.nativeElement;
    if (el) this.collectionObserver.observe(el);
  }

  private setupCodexObserver() {
    if (typeof IntersectionObserver === 'undefined') return;
    this.codexObserver?.disconnect();
    this.codexObserver = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.isIntersecting
            && this.activeTab() === 'codex'
            && this.codexHasMore()
            && !this.codexLoading()) {
          this.loadMoreCodex();
        }
      }
    }, { rootMargin: '300px' });
    const el = this.codexSentinelRef?.nativeElement;
    if (el) this.codexObserver.observe(el);
  }

  private setupWishlistObserver() {
    if (typeof IntersectionObserver === 'undefined') return;
    this.wishlistObserver?.disconnect();
    this.wishlistObserver = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.isIntersecting
            && this.activeTab() === 'wishlist'
            && this.wishlistHasMore()
            && !this.wishlistLoading()) {
          this.loadMoreWishlist();
        }
      }
    }, { rootMargin: '300px' });
    const el = this.wishlistSentinelRef?.nativeElement;
    if (el) this.wishlistObserver.observe(el);
  }

  private setupMercadoObserver() {
    if (typeof IntersectionObserver === 'undefined') return;
    this.mercadoObserver?.disconnect();
    this.mercadoObserver = new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (entry.isIntersecting
            && this.activeTab() === 'mercado'
            && this.mercadoHasMore()
            && !this.mercadoLoading()) {
          this.loadMoreMercado();
        }
      }
    }, { rootMargin: '300px' });
    const el = this.mercadoSentinelRef?.nativeElement;
    if (el) this.mercadoObserver.observe(el);
  }

  private tryInfiniteScrollFallback() {
    if (!this.isNearPageBottom()) return;
    if (this.activeTab() === 'carpeta') this.loadMoreCollection();
    if (this.activeTab() === 'codex') this.loadMoreCodex();
    if (this.activeTab() === 'wishlist') this.loadMoreWishlist();
    if (this.activeTab() === 'mercado') this.loadMoreMercado();
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

  // ── Tabs ──
  switchTab(t: Tab) {
    if (this.workspaceMode() && !this.selectedWorkspaceId()) return;

    if (t === 'carpeta' || t === 'codex' || t === 'mercado') {
      if (!this.hasPermission('view_collection')) {
        alert('No tienes permiso para ver la carpeta de esta tienda.');
        return;
      }
    }
    if (t === 'pedidos' && !this.hasPermission('view_orders')) {
      alert('No tienes permiso para ver pedidos pendientes.');
      return;
    }
    if (t === 'historial' && !this.hasPermission('view_history')) {
      alert('No tienes permiso para ver historial de pedidos.');
      return;
    }
    if (t === 'permisos' && !this.canManagePermissions()) {
      alert('No tienes permiso para gestionar accesos.');
      return;
    }
    if ((t === 'wishlist' || t === 'stats') && this.workspaceMode()) {
      return;
    }

    this.activeTab.set(t);
    if (t === 'carpeta') this.loadCollection();
    if (t === 'codex' && this.codexCards().length === 0) this.loadCodex();
    if (t === 'wishlist') this.loadWishlist();
    if (t === 'mercado') { this.loadMercado(); }
    if (t === 'pedidos') this.loadPendingOrders();
    if (t === 'historial') this.loadHistoryOrders();
    if (t === 'stats') this.loadStats();
    if (t === 'permisos') this.loadWorkspacePermissions();
    queueMicrotask(() => {
      this.setupCollectionObserver();
      this.setupCodexObserver();
      this.setupWishlistObserver();
      this.setupMercadoObserver();
      this.tryInfiniteScrollFallback();
    });
  }

  // ── IDs ──
  loadIds() {
    this.rb.carpetaIds({ store_profile_id: this.currentStoreProfileId() }).subscribe(ids => {
      this.collectionIds = ids.collection || {};
      this.wishlistIds = new Set(ids.wishlist || []);
      this.cdr.markForCheck();
    });
  }
  isInCollection(id: number) { return id in this.collectionIds; }
  collectionQty(id: number) { return this.collectionIds[id] || 0; }
  isInWishlist(id: number) { return this.wishlistIds.has(id); }

  // ── Collection ──
  loadCollection() {
    if (!this.hasPermission('view_collection')) {
      this.collectionEntries.set([]);
      this.collectionTotal.set(0);
      this.collectionHasMore.set(false);
      return;
    }
    this.collectionPage.set(1);
    this.collectionEntries.set([]);
    this.collectionHasMore.set(false);
    this.fetchCollectionPage();
  }

  loadMoreCollection() {
    if (this.collectionLoading() || !this.collectionHasMore()) return;
    this.collectionPage.update(p => p + 1);
    this.fetchCollectionPage(true);
  }

  private fetchCollectionPage(append = false) {
    this.collectionLoading.set(true);
    this.rb.listCollection({
      search: this.collectionSearch || undefined,
      page: this.collectionPage(),
      page_size: this.COLLECTION_PAGE_SIZE,
      selling: this.onlySelling() || undefined,
      store_profile_id: this.currentStoreProfileId(),
    }).subscribe({
      next: res => {
        if (append) {
          this.collectionEntries.update(curr => [...curr, ...res.results]);
        } else {
          this.collectionEntries.set(res.results);
        }
        this.collectionTotal.set(res.count);
        this.collectionHasMore.set(!!res.next);
        this.collectionLoading.set(false);
        this.cdr.markForCheck();
        // Re-observe sentinel in case DOM cleared it
        queueMicrotask(() => {
          this.setupCollectionObserver();
          this.tryInfiniteScrollFallback();
        });
      },
      error: () => { this.collectionLoading.set(false); this.cdr.markForCheck(); },
    });
  }
  onCollectionSearch() { this.loadCollection(); }
  toggleOnlySelling() { this.onlySelling.update(v => !v); this.loadCollection(); }

  onFieldChange(entry: RiftboundCollectionEntry, field: keyof DirtyPatch, value: any) {
    if (field === 'quantity' || field === 'condition' || field === 'language' || field === 'is_foil' || field === 'notes') {
      if (!this.hasPermission('edit_collection')) return;
    }
    if (field === 'price') {
      if (!this.hasPermission('edit_market')) return;
    }
    if (field === 'selling_quantity') {
      const nextVal = Number(value || 0);
      const isRemoval = (entry.selling_quantity || 0) > 0 && nextVal === 0;
      if (isRemoval) {
        if (!this.hasPermission('remove_from_market') && !this.hasPermission('edit_market')) return;
      } else if (!this.hasPermission('edit_market')) {
        return;
      }
    }
    const pending = this.dirtyEntries.get(entry.id) || {};
    (pending as any)[field] = value;
    this.dirtyEntries.set(entry.id, pending);
    this.cdr.markForCheck();
  }

  saveEntry(entry: RiftboundCollectionEntry) {
    const pending = this.dirtyEntries.get(entry.id);
    if (!pending) return;
    this.rb.upsertCollection(this.buildUpsertPayload(entry, pending), { store_profile_id: this.currentStoreProfileId() }).subscribe(res => {
      this.dirtyEntries.delete(entry.id);
      if ((res as any).deleted) {
        this.collectionEntries.update(arr => arr.filter(e => e.id !== entry.id));
        this.collectionTotal.update(n => Math.max(0, n - 1));
        delete this.collectionIds[entry.card];
      } else {
        const updated = res as RiftboundCollectionEntry;
        this.collectionEntries.update(arr => arr.map(e => e.id === entry.id ? updated : e));
        this.loadIds();
      }
      this.cdr.markForCheck();
    });
  }

  saveAllChanges() {
    if (!this.hasPermission('edit_collection') && !this.hasPermission('edit_market') && !this.hasPermission('remove_from_market')) {
      alert('No tienes permisos para guardar cambios en esta tienda.');
      return;
    }
    if (this.dirtyEntries.size === 0) return;
    this.batchSaving.set(true);
    const items = Array.from(this.dirtyEntries.entries()).map(([id, pending]) => {
      const entry = this.collectionEntries().find(e => e.id === id);
      return entry ? this.buildUpsertPayload(entry, pending) : null;
    }).filter(Boolean) as Partial<RiftboundCollectionEntry>[];
    if (!items.length) { this.batchSaving.set(false); return; }
    this.rb.batchUpsertCollection(items, { store_profile_id: this.currentStoreProfileId() }).subscribe({
      next: () => {
        this.dirtyEntries.clear();
        this.batchSaving.set(false);
        this.loadIds();
        this.loadCollection();
      },
      error: () => { this.batchSaving.set(false); this.cdr.markForCheck(); },
    });
  }

  private buildUpsertPayload(entry: RiftboundCollectionEntry, p: DirtyPatch): Partial<RiftboundCollectionEntry> {
    return {
      id: entry.id,
      card: entry.card,
      quantity: p.quantity ?? entry.quantity,
      is_foil: p.is_foil ?? entry.is_foil,
      notes: p.notes ?? entry.notes,
      price: p.price !== undefined ? p.price : entry.price,
      selling_quantity: p.selling_quantity ?? entry.selling_quantity,
      condition: p.condition ?? entry.condition,
      language: p.language ?? entry.language,
    };
  }

  priceFromInput(v: string): number | null {
    if (v === '' || v === null || v === undefined) return null;
    const n = Number(v);
    return Number.isFinite(n) && n >= 0 ? n : null;
  }

  removeFromCollection(entry: RiftboundCollectionEntry) {
    if (!this.hasPermission('delete_collection')) {
      alert('No tienes permiso para eliminar cartas de esta carpeta.');
      return;
    }
    if (!confirm(`¿Quitar "${entry.card_data.name}" de tu carpeta?`)) return;
    this.rb.deleteCollection(entry.id, { store_profile_id: this.currentStoreProfileId() }).subscribe(() => {
      this.collectionEntries.update(arr => arr.filter(e => e.id !== entry.id));
      this.collectionTotal.update(n => Math.max(0, n - 1));
      delete this.collectionIds[entry.card];
      this.dirtyEntries.delete(entry.id);
      this.cdr.markForCheck();
    });
  }

  // ── Codex ──
  loadCodex(append = false) {
    if (!this.hasPermission('view_collection')) {
      this.codexCards.set([]);
      this.codexTotal.set(0);
      this.codexHasMore.set(false);
      return;
    }
    this.codexLoading.set(true);
    this.rb.listCards({
      search: this.codexSearch || undefined,
      type: this.selectedType || undefined,
      rarity: this.selectedRarity || undefined,
      set: this.selectedSet || undefined,
      colors: this.selectedColors.size ? Array.from(this.selectedColors) : undefined,
      page: this.codexPage(),
      pageSize: this.CODEX_PAGE_SIZE,
      lite: true,
    }).subscribe({
      next: res => {
        const nextCards = res.results as RiftboundCardLite[];
        if (append) {
          this.codexCards.update(curr => [...curr, ...nextCards]);
        } else {
          this.codexCards.set(nextCards);
        }
        this.codexTotal.set(res.count);
        this.codexHasMore.set(!!res.next);
        this.codexLoading.set(false);
        this.cdr.markForCheck();
        queueMicrotask(() => {
          this.setupCodexObserver();
          this.tryInfiniteScrollFallback();
        });
      },
      error: () => { this.codexLoading.set(false); this.cdr.markForCheck(); },
    });
  }
  onCodexSearch() {
    this.codexPage.set(1);
    this.codexCards.set([]);
    this.codexHasMore.set(false);
    this.loadCodex();
  }
  onCodexFilter() {
    this.codexPage.set(1);
    this.codexCards.set([]);
    this.codexHasMore.set(false);
    this.loadCodex();
  }
  loadMoreCodex() {
    if (this.codexLoading() || !this.codexHasMore()) return;
    this.codexPage.update(p => p + 1);
    this.loadCodex(true);
  }

  toggleColor(c: string) {
    if (this.selectedColors.has(c)) this.selectedColors.delete(c);
    else this.selectedColors.add(c);
    this.onCodexFilter();
  }

  selectCodexCard(card: RiftboundCardLite) { this.previewCard.set(card); }

  // ── TCGPlayer ──
  private readonly tcgSetSlugs: Record<string, string> = {
    OGN: 'origins', UNL: 'unleashed', OGS: 'proving-grounds', SFD: 'spiritforged', ARC: 'product',
  };
  getTcgPlayerUrl(card: RiftboundCardLite | RiftboundCard): string {
    const setCode = card.card_number?.split('-')[0]?.toUpperCase() || '';
    const setSlug = this.tcgSetSlugs[setCode] || 'product';
    const q = encodeURIComponent(card.name);
    return `https://www.tcgplayer.com/search/riftbound-league-of-legends-trading-card-game/${setSlug}?q=${q}&Language=English`;
  }

  quickAddToCollection(card: RiftboundCardLite | RiftboundCard, ev?: MouseEvent) {
    ev?.stopPropagation();
    if (!this.hasPermission('edit_collection')) {
      alert('No tienes permiso para agregar cartas a esta carpeta.');
      return;
    }
    const newQty = (this.collectionIds[card.id] || 0) + 1;
    this.rb.upsertCollection({ card: card.id, quantity: newQty }, { store_profile_id: this.currentStoreProfileId() }).subscribe(res => {
      if (!(res as any).deleted) {
        const updated = res as RiftboundCollectionEntry;
        this.collectionIds[updated.card] = updated.quantity;
      }
      this.cdr.markForCheck();
    });
  }

  toggleWishlist(cardId: number, ev?: MouseEvent) {
    ev?.stopPropagation();
    if (this.workspaceMode()) return;
    this.rb.toggleWishlist(cardId).subscribe(res => {
      if (res.wishlisted) this.wishlistIds.add(cardId);
      else this.wishlistIds.delete(cardId);
      this.cdr.markForCheck();
    });
  }

  // ── Wishlist ──
  loadWishlist() {
    this.wishlistPage.set(1);
    this.wishlistEntries.set([]);
    this.wishlistHasMore.set(false);
    this.fetchWishlistPage();
  }

  loadMoreWishlist() {
    if (this.wishlistLoading() || !this.wishlistHasMore()) return;
    this.wishlistPage.update(p => p + 1);
    this.fetchWishlistPage(true);
  }

  private fetchWishlistPage(append = false) {
    this.wishlistLoading.set(true);
    this.rb.listWishlist({ search: this.wishlistSearch || undefined, page: this.wishlistPage() }).subscribe({
      next: res => {
        this.hydrateWishlistCardDetails(res.results);
        if (append) {
          this.wishlistEntries.update(arr => [...arr, ...res.results]);
        } else {
          this.wishlistEntries.set(res.results);
        }
        this.wishlistTotal.set(res.count);
        this.wishlistHasMore.set(!!res.next);
        this.wishlistLoading.set(false);
        this.cdr.markForCheck();
        queueMicrotask(() => {
          this.setupWishlistObserver();
          this.tryInfiniteScrollFallback();
        });
      },
      error: () => { this.wishlistLoading.set(false); this.cdr.markForCheck(); },
    });
  }

  private hydrateWishlistCardDetails(entries: RiftboundWishlistEntry[]) {
    for (const entry of entries) {
      const lite = entry.card_data;
      if (!lite?.id) continue;

      if (this.wishlistHydratedCards().has(lite.id)) continue;
      if (this.wishlistHydratingCardIds.has(lite.id)) continue;

      const hasCardNumber = !!(lite.card_number || '').trim();
      const hasCdn = !!(lite.cdn_image_url || '').trim();
      const imageHost = (lite.image || lite.image_url || '').trim();
      const isCmsOnly = /cmsassets\.rgpub\.io/i.test(imageHost) && !hasCdn;

      // Solo hidrata cuando el payload lite no trae suficientes datos para fallback robusto.
      if (hasCardNumber && !isCmsOnly) continue;

      this.wishlistHydratingCardIds.add(lite.id);
      this.rb.getCard(lite.id).subscribe({
        next: (full) => {
          this.wishlistHydratedCards.update(prev => {
            const next = new Map(prev);
            next.set(full.id, full);
            return next;
          });
          this.cdr.markForCheck();
        },
        error: () => {
          // No bloquear UI si una carta no se puede hidratar.
        },
        complete: () => {
          this.wishlistHydratingCardIds.delete(lite.id);
        },
      });
    }
  }
  onWishlistSearch() {
    this.wishlistPage.set(1);
    this.wishlistEntries.set([]);
    this.wishlistHasMore.set(false);
    this.loadWishlist();
  }

  updateWishlistQty(entry: RiftboundWishlistEntry, qty: number) {
    if (!qty || qty < 1) return;
    this.rb.updateWishlistQty(entry.card, qty).subscribe(updated => {
      this.wishlistEntries.update(arr => arr.map(e => e.id === entry.id ? updated : e));
      this.cdr.markForCheck();
    });
  }

  removeFromWishlist(entry: RiftboundWishlistEntry) {
    this.rb.toggleWishlist(entry.card).subscribe(() => {
      this.wishlistEntries.update(arr => arr.filter(e => e.id !== entry.id));
      this.wishlistTotal.update(n => Math.max(0, n - 1));
      this.wishlistIds.delete(entry.card);
      this.cdr.markForCheck();
    });
  }

  // ── Pedidos / Historial ──
  loadPendingOrders() {
    if (!this.hasPermission('view_orders')) {
      this.pendingOrders.set([]);
      return;
    }
    this.ordersLoading.set(true);
    this.rb.listMyStoreOrders({ status: 'pending', page: 1, store_profile_id: this.currentStoreProfileId() }).subscribe({
      next: (res) => {
        this.pendingOrders.set(res.results || []);
        this.ordersLoading.set(false);
        this.cdr.markForCheck();
      },
      error: () => {
        this.ordersLoading.set(false);
        this.pendingOrders.set([]);
        this.cdr.markForCheck();
      },
    });
  }

  loadHistoryOrders() {
    if (!this.hasPermission('view_history')) {
      this.historyOrders.set([]);
      return;
    }
    this.historyLoading.set(true);
    const status = this.historyStatusFilter() || undefined;
    this.rb.listMyStoreOrders({ status, page: 1, store_profile_id: this.currentStoreProfileId() }).subscribe({
      next: (res) => {
        this.historyOrders.set(res.results || []);
        this.historyLoading.set(false);
        this.cdr.markForCheck();
      },
      error: () => {
        this.historyLoading.set(false);
        this.historyOrders.set([]);
        this.cdr.markForCheck();
      },
    });
  }

  onHistoryFilterChange(v: '' | RiftboundStoreOrderStatus) {
    this.historyStatusFilter.set(v);
    this.loadHistoryOrders();
  }

  orderStatusLabel(status: RiftboundStoreOrderStatus): string {
    if (status === 'pending') return 'Pendiente';
    if (status === 'accepted') return 'Aceptado';
    if (status === 'cancelled') return 'Cancelado';
    return status;
  }

  acceptOrder(order: RiftboundStoreOrder) {
    if (!this.hasPermission('accept_orders')) {
      alert('No tienes permiso para aceptar pedidos en esta tienda.');
      return;
    }
    if (!confirm(`¿Aceptar pedido #${order.id}?`)) return;
    this.rb.acceptStoreOrder(order.id).subscribe({
      next: () => {
        this.pendingOrders.update(arr => arr.filter(o => o.id !== order.id));
        if (this.activeTab() === 'historial') this.loadHistoryOrders();
        this.cdr.markForCheck();
      },
      error: (err) => {
        alert(err?.error?.detail || 'No se pudo aceptar el pedido.');
      },
    });
  }

  cancelOrder(order: RiftboundStoreOrder) {
    if (!this.hasPermission('reject_orders')) {
      alert('No tienes permiso para rechazar pedidos en esta tienda.');
      return;
    }
    const reason = prompt(`Motivo de cancelación para pedido #${order.id}:`, '')?.trim() || '';
    if (!reason) {
      alert('Debes indicar un motivo para cancelar el pedido.');
      return;
    }
    this.rb.cancelStoreOrder(order.id, reason).subscribe({
      next: () => {
        this.pendingOrders.update(arr => arr.filter(o => o.id !== order.id));
        if (this.activeTab() === 'historial') this.loadHistoryOrders();
        this.cdr.markForCheck();
      },
      error: (err) => {
        alert(err?.error?.detail || 'No se pudo cancelar el pedido.');
      },
    });
  }

  // ── Stats ──
  loadStats() {
    this.statsLoading.set(true);
    this.statsError.set(null);
    this.rb.collectionStats({ store_profile_id: this.currentStoreProfileId() }).subscribe({
      next: s => { this.stats.set(s); this.statsLoading.set(false); this.cdr.markForCheck(); },
      error: err => {
        this.statsLoading.set(false);
        this.statsError.set(`Error ${err?.status ?? '?'}: ${err?.error?.detail || err?.message || 'sin detalle'}`);
        this.cdr.markForCheck();
      },
    });
  }

  // ── Helpers ──
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

  private cardImageCandidates(card: RiftboundCardLite | RiftboundCard | null | undefined): string[] {
    if (!card) return [];
    const candidates = [
      ...this.imageUrlVariants(card.cdn_image_url),
      ...this.imageUrlVariants(card.image),
      ...this.imageUrlVariants(card.image_url),
      ...this.imageUrlVariants(card.image_url_small),
    ].filter(Boolean);
    return Array.from(new Set(candidates));
  }

  private shareCardImageCandidates(card: RiftboundCardLite | RiftboundCard | null | undefined): string[] {
    if (!card) return [];
    const candidates = [
      ...this.imageUrlVariants(card.cdn_image_url),
      ...this.cloudinaryFetchVariants(card.image),
      ...this.cloudinaryFetchVariants(card.image_url),
      ...this.cloudinaryFetchVariants(card.image_url_small),
      ...this.imageUrlVariants(card.image),
      ...this.imageUrlVariants(card.image_url),
      ...this.imageUrlVariants(card.image_url_small),
    ].filter(Boolean);
    return Array.from(new Set(candidates));
  }

  cardImageUrl(card: RiftboundCardLite | RiftboundCard | null | undefined): string {
    const candidates = this.cardImageCandidates(card);
    if (!candidates.length) return '';
    const step = card?.id ? (this.imageFallbackStepByCard.get(card.id) || 0) : 0;
    return candidates[Math.min(step, candidates.length - 1)] || '';
  }

  isCardImageBroken(card: RiftboundCardLite | RiftboundCard | null | undefined): boolean {
    if (!card?.id) return false;
    return this.cardImageBroken().has(card.id);
  }

  onCardImageError(card: RiftboundCardLite | RiftboundCard | null | undefined, event: Event) {
    if (!card?.id) return;
    const candidates = this.cardImageCandidates(card);
    const currentStep = this.imageFallbackStepByCard.get(card.id) || 0;

    if (currentStep < candidates.length - 1) {
      const nextStep = currentStep + 1;
      this.imageFallbackStepByCard.set(card.id, nextStep);
      const img = event.target as HTMLImageElement | null;
      if (img) img.src = candidates[nextStep];
      this.cdr.markForCheck();
      return;
    }

    this.cardImageBroken.update(prev => {
      const next = new Set(prev);
      next.add(card.id);
      return next;
    });
    this.cdr.markForCheck();
  }

  typeLabel(t: string | undefined | null): string {
    return ({
      unit: 'Unit', spell: 'Spell', champion: 'Champion', legend: 'Legend',
      gear: 'Gear', battlefield: 'Battlefield', rune: 'Rune', other: 'Otro',
    } as Record<string, string>)[t || ''] || (t || '');
  }
  rarityLabel(r: string | undefined | null): string {
    return ({
      common: 'Common', uncommon: 'Uncommon', rare: 'Rare',
      epic: 'Epic', legendary: 'Legendary', champion: 'Champion', promo: 'Promo',
    } as Record<string, string>)[r || ''] || (r || '');
  }
  colorLabel(c: string): string {
    return this.COLORS.find(x => x.code === c)?.label || c;
  }
  colorHex(c: string): string {
    return this.COLORS.find(x => x.code === c)?.hex || '#8896a8';
  }

  // ── Binder profile ──
  loadBinderProfile() {
    this.rb.getBinderProfile().subscribe(p => {
      this.binderProfile.set(p);
      this.cdr.markForCheck();
    });
  }

  patchProfile(patch: Partial<RiftboundBinderProfile>) {
    this.rb.updateBinderProfile(patch).subscribe(p => {
      this.binderProfile.set(p);
      this.cdr.markForCheck();
    });
  }

  onAvatarFileChange(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
      alert('La imagen es muy grande (máx. 5 MB).');
      input.value = '';
      return;
    }
    this.avatarUploading.set(true);
    this.rb.uploadBinderAvatar(file).subscribe({
      next: p => {
        this.binderProfile.set(p);
        this.avatarUploading.set(false);
        this.cdr.markForCheck();
      },
      error: err => {
        this.avatarUploading.set(false);
        const detail = err?.error?.detail || 'No se pudo subir la imagen. Intentalo de nuevo.';
        alert(detail);
        this.cdr.markForCheck();
      },
    });
    input.value = '';
  }

  regenerateToken() {
    if (!confirm('¿Regenerar token? El enlace anterior dejará de funcionar.')) return;
    this.rb.regenerateShareToken().subscribe(res => {
      const cur = this.binderProfile();
      if (cur) {
        this.binderProfile.set({ ...cur, share_token: res.share_token });
        this.cdr.markForCheck();
      }
    });
  }

  copyShareLink() {
    const token = this.binderProfile()?.share_token;
    if (!token) return;
    const url = `${window.location.origin}/riftbound/tienda/${token}`;
    navigator.clipboard?.writeText(url).then(() => {
      alert('Enlace copiado:\n' + url);
    }).catch(() => prompt('Copia el enlace:', url));
  }

  async downloadStoreQr() {
    const token = this.binderProfile()?.share_token;
    if (!token || this.qrDownloading()) return;
    const url = `${window.location.origin}/riftbound/tienda/${token}`;

    this.qrDownloading.set(true);
    this.cdr.markForCheck();
    try {
      const qrDataUrl = await QRCode.toDataURL(url, {
        width: 1024,
        margin: 2,
        errorCorrectionLevel: 'H',
        color: { dark: '#0f172a', light: '#ffffff' },
      });
      const dataUrl = await this.composeQrWithCenteredLogo(qrDataUrl, this.getStoreQrLogoUrl());

      const a = document.createElement('a');
      a.href = dataUrl;
      a.download = `riftbound-tienda-qr-${this.auth.user()?.username || 'shadowforge'}.png`;
      document.body.appendChild(a);
      a.click();
      a.remove();
    } catch {
      alert('No se pudo generar el QR. Intenta de nuevo.');
    } finally {
      this.qrDownloading.set(false);
      this.cdr.markForCheck();
    }
  }

  private getStoreQrLogoUrl(): string | null {
    const profile = this.binderProfile();
    const binderAvatar = (profile?.binder_avatar_url || '').trim();
    if (binderAvatar) return binderAvatar;
    const userAvatar = (profile?.user_avatar_url || this.auth.user()?.avatar_url || '').trim();
    return userAvatar || null;
  }

  private async composeQrWithCenteredLogo(qrDataUrl: string, logoUrl: string | null): Promise<string> {
    if (!logoUrl) return qrDataUrl;
    try {
      const [qrImg, logoImg] = await Promise.all([
        this.loadImageForQr(qrDataUrl),
        this.loadImageForQr(logoUrl),
      ]);

      const size = qrImg.naturalWidth || qrImg.width || 1024;
      const canvas = document.createElement('canvas');
      canvas.width = size;
      canvas.height = size;
      const ctx = canvas.getContext('2d');
      if (!ctx) return qrDataUrl;

      ctx.drawImage(qrImg, 0, 0, size, size);

      const badgeSize = Math.round(size * 0.24);
      const badgeRadius = Math.round(badgeSize / 2);
      const centerX = Math.round(size / 2);
      const centerY = Math.round(size / 2);
      const imagePadding = Math.max(6, Math.round(badgeSize * 0.08));

      ctx.save();
      ctx.fillStyle = '#ffffff';
      ctx.beginPath();
      ctx.arc(centerX, centerY, badgeRadius, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();

      ctx.save();
      ctx.beginPath();
      ctx.arc(centerX, centerY, badgeRadius - imagePadding, 0, Math.PI * 2);
      ctx.clip();
      ctx.drawImage(
        logoImg,
        centerX - badgeRadius + imagePadding,
        centerY - badgeRadius + imagePadding,
        badgeSize - imagePadding * 2,
        badgeSize - imagePadding * 2,
      );
      ctx.restore();

      return canvas.toDataURL('image/png');
    } catch {
      return qrDataUrl;
    }
  }

  private loadImageForQr(src: string): Promise<HTMLImageElement> {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.crossOrigin = 'anonymous';
      img.referrerPolicy = 'no-referrer';
      img.onload = () => resolve(img);
      img.onerror = () => reject(new Error('No se pudo cargar imagen para QR'));
      img.src = src;
    });
  }

  // ── Compartir wishlist ──
  wishlistSellerHandle(): string {
    const p = this.binderProfile();
    if (p?.display_name) return p.display_name;
    const u = this.auth.user();
    return u?.username ? '@' + u.username : 'Mi wishlist';
  }
  wishlistContactLine(): string {
    const msg = (this.wishlistShareMessage || '').trim();
    return msg || 'Busco cartas';
  }
  wishlistShareItems(): ShareImageItem[] {
    const sel = this.wishlistShareSelection();
    const source = this.wishlistEntries();
    const hydrated = this.wishlistHydratedCards();
    const filtered = sel.size > 0 ? source.filter(w => sel.has(w.id)) : source;
    return filtered.map(w => {
      const card = hydrated.get(w.card_data.id) || w.card_data;
      const imageCandidates = this.shareCardImageCandidates(card);
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
  isWishlistShareSelected(id: number): boolean {
    return this.wishlistShareSelection().has(id);
  }
  toggleWishlistShare(id: number, checked: boolean) {
    const next = new Set(this.wishlistShareSelection());
    if (checked) next.add(id); else next.delete(id);
    this.wishlistShareSelection.set(next);
  }
  copyWishlistLink() {
    const token = this.binderProfile()?.share_token;
    if (!token) return;
    const url = `${window.location.origin}/riftbound/wishlist/${token}`;
    navigator.clipboard?.writeText(url).then(() => {
      alert('Enlace copiado:\n' + url);
    }).catch(() => prompt('Copia el enlace:', url));
  }
  shareWishlistWhatsApp() {
    const token = this.binderProfile()?.share_token;
    if (!token) return;
    const url = `${window.location.origin}/riftbound/wishlist/${token}`;
    const txt = encodeURIComponent(`Mira mi wishlist Riftbound: ${url}`);
    window.open(`https://wa.me/?text=${txt}`, '_blank');
  }

  // ── Mercado ──
  loadMercado() {
    if (!this.hasPermission('view_collection')) {
      this.mercadoEntries.set([]);
      this.mercadoHasMore.set(false);
      return;
    }
    this.mercadoPage.set(1);
    this.mercadoEntries.set([]);
    this.mercadoHasMore.set(false);
    this.fetchMercadoPage();
  }

  loadMoreMercado() {
    if (this.mercadoLoading() || !this.mercadoHasMore()) return;
    this.mercadoPage.update(p => p + 1);
    this.fetchMercadoPage(true);
  }

  private fetchMercadoPage(append = false) {
    this.mercadoLoading.set(true);
    this.rb.listCollection({ selling: true, page: this.mercadoPage(), store_profile_id: this.currentStoreProfileId() }).subscribe({
      next: res => {
        if (append) {
          this.mercadoEntries.update(arr => [...arr, ...res.results]);
        } else {
          this.mercadoEntries.set(res.results);
        }
        this.mercadoHasMore.set(!!res.next);
        this.mercadoLoading.set(false);
        this.cdr.markForCheck();
        queueMicrotask(() => {
          this.setupMercadoObserver();
          this.tryInfiniteScrollFallback();
        });
      },
      error: () => { this.mercadoLoading.set(false); this.cdr.markForCheck(); },
    });
  }

  onMercadoFieldChange(entry: RiftboundCollectionEntry, field: keyof DirtyPatch, value: any) {
    if (field === 'price' && !this.hasPermission('edit_market')) return;
    if (field === 'selling_quantity') {
      const nextVal = Number(value || 0);
      const isRemoval = (entry.selling_quantity || 0) > 0 && nextVal === 0;
      if (isRemoval) {
        if (!this.hasPermission('remove_from_market') && !this.hasPermission('edit_market')) return;
      } else if (!this.hasPermission('edit_market')) {
        return;
      }
    }
    const pending = this.mercadoDirty.get(entry.id) || {};
    (pending as any)[field] = value;
    this.mercadoDirty.set(entry.id, pending);
    this.cdr.markForCheck();
  }

  saveMercadoChanges() {
    if (!this.hasPermission('edit_market') && !this.hasPermission('remove_from_market')) {
      alert('No tienes permisos para guardar cambios de mercado en esta tienda.');
      return;
    }
    if (this.mercadoDirty.size === 0) return;
    this.batchSaving.set(true);
    const items = Array.from(this.mercadoDirty.entries()).map(([id, pending]) => {
      const entry = this.mercadoEntries().find(e => e.id === id);
      return entry ? this.buildUpsertPayload(entry, pending) : null;
    }).filter(Boolean) as Partial<RiftboundCollectionEntry>[];
    if (!items.length) { this.batchSaving.set(false); return; }
    this.rb.batchUpsertCollection(items, { store_profile_id: this.currentStoreProfileId() }).subscribe({
      next: () => {
        this.mercadoDirty.clear();
        this.batchSaving.set(false);
        this.loadMercado();
      },
      error: () => { this.batchSaving.set(false); this.cdr.markForCheck(); },
    });
  }

  async exportMercadoPdf() {
    this.exportingPdf.set(true);
    try {
      const [{ default: html2canvas }, jspdfMod] = await Promise.all([
        import('html2canvas') as any,
        import('jspdf') as any,
      ]);
      const jsPDF = jspdfMod.jsPDF || jspdfMod.default;
      const node = document.querySelector('.collection-grid') as HTMLElement | null;
      if (!node) return;
      const canvas = await html2canvas(node, { backgroundColor: '#0f0f23', scale: 2 });
      const pdf = new jsPDF({ orientation: 'portrait', unit: 'pt', format: 'a4' });
      const pageW = pdf.internal.pageSize.getWidth();
      const pageH = pdf.internal.pageSize.getHeight();
      const imgData = canvas.toDataURL('image/png');
      const ratio = canvas.width / canvas.height;
      let imgW = pageW - 40;
      let imgH = imgW / ratio;
      if (imgH > pageH - 40) { imgH = pageH - 40; imgW = imgH * ratio; }
      pdf.addImage(imgData, 'PNG', 20, 20, imgW, imgH);
      pdf.save(`mercado-riftbound-${Date.now()}.pdf`);
    } catch (e) {
      console.error('Export PDF error:', e);
      alert('Error al exportar PDF');
    } finally {
      this.exportingPdf.set(false);
      this.cdr.markForCheck();
    }
  }

  // ── Permisos de colaboradores ──
  permissionLabel(key: keyof RiftboundStorePermissionFlags): string {
    const labels: Record<keyof RiftboundStorePermissionFlags, string> = {
      view_collection: 'Ver carpeta',
      edit_collection: 'Editar carpeta',
      delete_collection: 'Eliminar de carpeta',
      edit_market: 'Editar venta/precio',
      remove_from_market: 'Quitar de venta',
      view_orders: 'Ver pedidos',
      view_history: 'Ver historial',
      accept_orders: 'Aceptar pedidos',
      reject_orders: 'Rechazar pedidos',
      manage_permissions: 'Gestionar permisos',
    };
    return labels[key];
  }

  collaboratorPermValue(row: RiftboundStoreCollaboratorPermission, key: keyof RiftboundStorePermissionFlags): boolean {
    const pending = this.collaboratorDirty.get(row.id);
    if (pending && key in pending) return !!pending[key];
    return !!row.permissions?.[key];
  }

  toggleNewCollaboratorPerm(key: keyof RiftboundStorePermissionFlags, checked: boolean) {
    this.newCollaboratorPerms.update(curr => ({ ...curr, [key]: checked }));
  }

  toggleCollaboratorPerm(id: number, key: keyof RiftboundStorePermissionFlags, checked: boolean) {
    const patch = this.collaboratorDirty.get(id) || {};
    (patch as any)[key] = checked;
    this.collaboratorDirty.set(id, patch);
    this.cdr.markForCheck();
  }

  loadWorkspacePermissions() {
    if (!this.canManagePermissions()) return;
    const profileId = this.permissionsStoreProfileId();
    if (!profileId) return;

    this.workspacePermissionsLoading.set(true);
    this.rb.listWorkspacePermissions(profileId).subscribe({
      next: (res) => {
        this.collaboratorPermissions.set(res.results || []);
        this.workspacePermissionsLoading.set(false);
        this.collaboratorDirty.clear();
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.workspacePermissionsLoading.set(false);
        alert(err?.error?.detail || 'No se pudieron cargar los permisos de colaboradores.');
        this.cdr.markForCheck();
      },
    });
  }

  grantCollaboratorAccess() {
    if (!this.canManagePermissions()) return;
    const profileId = this.permissionsStoreProfileId();
    if (!profileId) {
      alert('Aun no se pudo resolver tu tienda. Recarga la pagina e intenta de nuevo.');
      return;
    }
    const user = this.newCollaboratorUser.trim();
    if (!user) {
      alert('Ingresa un usuario o email.');
      return;
    }

    this.permissionsSaving.set(true);
    this.rb.upsertWorkspacePermission(profileId, user, this.newCollaboratorPerms()).subscribe({
      next: () => {
        this.newCollaboratorUser = '';
        this.permissionsSaving.set(false);
        this.loadWorkspacePermissions();
      },
      error: (err) => {
        this.permissionsSaving.set(false);
        alert(err?.error?.detail || 'No se pudo guardar el acceso del colaborador.');
        this.cdr.markForCheck();
      },
    });
  }

  saveCollaboratorPermissions(row: RiftboundStoreCollaboratorPermission) {
    if (!this.canManagePermissions()) return;
    const profileId = this.permissionsStoreProfileId();
    if (!profileId) {
      alert('Aun no se pudo resolver tu tienda. Recarga la pagina e intenta de nuevo.');
      return;
    }

    const patch = this.collaboratorDirty.get(row.id);
    if (!patch || Object.keys(patch).length === 0) return;

    this.permissionsSaving.set(true);
    this.rb.updateWorkspacePermission(profileId, row.id, patch).subscribe({
      next: () => {
        this.permissionsSaving.set(false);
        this.collaboratorDirty.delete(row.id);
        this.loadWorkspacePermissions();
      },
      error: (err) => {
        this.permissionsSaving.set(false);
        alert(err?.error?.detail || 'No se pudieron actualizar los permisos.');
        this.cdr.markForCheck();
      },
    });
  }

  removeCollaboratorPermissions(row: RiftboundStoreCollaboratorPermission) {
    if (!this.canManagePermissions()) return;
    const profileId = this.permissionsStoreProfileId();
    if (!profileId) {
      alert('Aun no se pudo resolver tu tienda. Recarga la pagina e intenta de nuevo.');
      return;
    }
    if (!confirm(`¿Quitar todos los accesos de ${row.username}?`)) return;

    this.permissionsSaving.set(true);
    this.rb.deleteWorkspacePermission(profileId, row.id).subscribe({
      next: () => {
        this.permissionsSaving.set(false);
        this.collaboratorDirty.delete(row.id);
        this.loadWorkspacePermissions();
      },
      error: (err) => {
        this.permissionsSaving.set(false);
        alert(err?.error?.detail || 'No se pudo quitar el acceso.');
        this.cdr.markForCheck();
      },
    });
  }

  // ── Bulk import ──
  runBulkImport() {
    const text = (this.bulkText || '').trim();
    if (!text) return;
    if (!this.hasPermission('edit_collection')) {
      alert('No tienes permiso para importar cartas en esta tienda.');
      return;
    }
    this.bulkImporting.set(true);
    this.bulkResult.set(null);
    this.rb.bulkImport(text, this.bulkMode, { store_profile_id: this.currentStoreProfileId() }).subscribe({
      next: res => {
        this.bulkResult.set(res);
        this.bulkImporting.set(false);
        this.loadIds();
        this.loadCollection();
        this.cdr.markForCheck();
      },
      error: () => {
        this.bulkImporting.set(false);
        this.cdr.markForCheck();
      },
    });
  }

  showFloatingSaveButton(): boolean {
    const canSaveCollection = this.hasPermission('edit_collection') || this.hasPermission('edit_market') || this.hasPermission('remove_from_market');
    const canSaveMercado = this.hasPermission('edit_market') || this.hasPermission('remove_from_market');
    return (this.activeTab() === 'carpeta' && this.dirtyEntries.size > 0 && canSaveCollection)
      || (this.activeTab() === 'mercado' && this.mercadoDirty.size > 0 && canSaveMercado);
  }

  floatingSaveLabel(): string {
    if (this.batchSaving()) return '⏳ Guardando...';
    if (this.activeTab() === 'carpeta') return `💾 Guardar carpeta (${this.dirtyEntries.size})`;
    if (this.activeTab() === 'mercado') return `💾 Guardar tienda (${this.mercadoDirty.size})`;
    return '💾 Guardar cambios';
  }

  onFloatingSaveClick() {
    if (this.batchSaving()) return;
    if (this.activeTab() === 'carpeta') { this.saveAllChanges(); return; }
    if (this.activeTab() === 'mercado') { this.saveMercadoChanges(); }
  }
}
