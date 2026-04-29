import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { switchMap } from 'rxjs/operators';
import { environment } from '../../environments/environment';
import {
  BinderProfile,
  PublicBinderProfile,
  CollectionEntry,
  WishlistEntry,
  CarpetaIds,
  PaginatedResponse,
} from '../models';

export interface PublicStoreResponse extends PaginatedResponse<CollectionEntry> {
  store: PublicBinderProfile;
  // legacy
  store_owner: string;
  store_avatar: string | null;
  store_binder_avatar: string | null;
}

export interface StoreFilters {
  page?: number;
  search?: string;
  edition?: string;
  race?: string;
  rarity?: string;
  type?: string;
  condition?: string;
  foil?: '0' | '1';
  price_min?: number;
  price_max?: number;
  only_priced?: '1';
  ordering?: string;
}

@Injectable({ providedIn: 'root' })
export class CarpetaService {
  private readonly apiUrl = `${environment.apiUrl}/carpeta`;

  constructor(private http: HttpClient) {}

  // ── Binder Profile ──
  getBinderProfile(): Observable<BinderProfile> {
    return this.http.get<BinderProfile>(`${this.apiUrl}/profile/`);
  }

  updateBinderProfile(data: Partial<BinderProfile>): Observable<BinderProfile> {
    return this.http.patch<BinderProfile>(`${this.apiUrl}/profile/`, data);
  }

  uploadBinderAvatar(file: File): Observable<BinderProfile> {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('upload_preset', environment.cloudinaryUploadPreset);
    fd.append('folder', 'deckshado/binder_avatars');
    return this.http.post<any>(
      `https://api.cloudinary.com/v1_1/${environment.cloudinaryCloudName}/image/upload`, fd
    ).pipe(
      switchMap(res => this.http.post<BinderProfile>(`${this.apiUrl}/profile/avatar/`, { avatar_url: res.secure_url }))
    );
  }

  regenerateShareToken(): Observable<{ share_token: string }> {
    return this.http.post<{ share_token: string }>(`${this.apiUrl}/share-token/regenerate/`, {});
  }

  // ── Collection ──
  getCollection(page?: number, search?: string, selling?: boolean): Observable<PaginatedResponse<CollectionEntry>> {
    let params = new HttpParams();
    if (page) params = params.set('page', page.toString());
    if (search) params = params.set('search', search);
    if (selling) params = params.set('selling', '1');
    return this.http.get<PaginatedResponse<CollectionEntry>>(`${this.apiUrl}/collection/`, { params });
  }

  upsertCollection(data: Partial<CollectionEntry> & { card: number }): Observable<CollectionEntry> {
    return this.http.post<CollectionEntry>(`${this.apiUrl}/collection/upsert/`, data);
  }

  removeFromCollection(cardId: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/collection/${cardId}/`);
  }

  bulkImport(text: string, mode: 'add' | 'set' = 'add'): Observable<{
    added: number; updated: number; not_found: number; ambiguous: number;
    not_found_lines: string[]; ambiguous_lines: { line: string; matches: string[] }[];
  }> {
    return this.http.post<any>(`${this.apiUrl}/collection/bulk-import/`, { text, mode });
  }

  // ── Wishlist ──
  getWishlist(page?: number, search?: string): Observable<PaginatedResponse<WishlistEntry>> {
    let params = new HttpParams();
    if (page) params = params.set('page', page.toString());
    if (search) params = params.set('search', search);
    return this.http.get<PaginatedResponse<WishlistEntry>>(`${this.apiUrl}/wishlist/`, { params });
  }

  toggleWishlist(cardId: number, desiredQuantity?: number): Observable<{ wishlisted: boolean; entry?: WishlistEntry }> {
    const body: any = { card: cardId };
    if (desiredQuantity) body.desired_quantity = desiredQuantity;
    return this.http.post<{ wishlisted: boolean; entry?: WishlistEntry }>(`${this.apiUrl}/wishlist/toggle/`, body);
  }

  updateWishlist(cardId: number, desiredQuantity: number): Observable<WishlistEntry> {
    return this.http.patch<WishlistEntry>(`${this.apiUrl}/wishlist/${cardId}/`, { desired_quantity: desiredQuantity });
  }

  // ── IDs ──
  getMyIds(): Observable<CarpetaIds> {
    return this.http.get<CarpetaIds>(`${this.apiUrl}/ids/`);
  }

  // ── Batch upsert ──
  batchUpsertCollection(items: Array<Partial<CollectionEntry> & { card: number }>): Observable<{ updated: number }> {
    return this.http.post<{ updated: number }>(`${this.apiUrl}/collection/batch-upsert/`, items);
  }

  // ── Share token ──
  getShareToken(): Observable<{ share_token: string; store_slug: string; is_store_public: boolean }> {
    return this.http.get<any>(`${this.apiUrl}/share-token/`);
  }

  // ── Public Store ──
  getPublicStore(tokenOrSlug: string, filters: StoreFilters = {}): Observable<PublicStoreResponse> {
    let params = new HttpParams();
    Object.entries(filters).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') params = params.set(k, String(v));
    });
    return this.http.get<PublicStoreResponse>(`${this.apiUrl}/store/${tokenOrSlug}/`, { params });
  }

  getPublicStores(filters: { page?: number; search?: string; country?: string; ordering?: string } = {})
    : Observable<PaginatedResponse<PublicBinderProfile>> {
    let params = new HttpParams();
    Object.entries(filters).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') params = params.set(k, String(v));
    });
    return this.http.get<PaginatedResponse<PublicBinderProfile>>(`${this.apiUrl}/stores/`, { params });
  }

  // ── Stats ──
  getCollectionStats(): Observable<any> {
    return this.http.get(`${this.apiUrl}/stats/`);
  }
}
