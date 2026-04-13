import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  BinderProfile,
  CollectionEntry,
  WishlistEntry,
  CarpetaIds,
  PaginatedResponse,
} from '../models';

@Injectable({ providedIn: 'root' })
export class CarpetaService {
  private readonly apiUrl = `${environment.apiUrl}/carpeta`;

  constructor(private http: HttpClient) {}

  // ── Binder Profile ──
  getBinderProfile(): Observable<BinderProfile> {
    return this.http.get<BinderProfile>(`${this.apiUrl}/profile/`);
  }

  uploadBinderAvatar(file: File): Observable<BinderProfile> {
    const fd = new FormData();
    fd.append('binder_avatar', file);
    return this.http.post<BinderProfile>(`${this.apiUrl}/profile/avatar/`, fd);
  }

  // ── Collection ──
  getCollection(page?: number, search?: string, selling?: boolean): Observable<PaginatedResponse<CollectionEntry>> {
    let params = new HttpParams();
    if (page) params = params.set('page', page.toString());
    if (search) params = params.set('search', search);
    if (selling) params = params.set('selling', '1');
    return this.http.get<PaginatedResponse<CollectionEntry>>(`${this.apiUrl}/collection/`, { params });
  }

  upsertCollection(data: { card: number; quantity?: number; price?: number | null; selling_quantity?: number }): Observable<CollectionEntry> {
    return this.http.post<CollectionEntry>(`${this.apiUrl}/collection/upsert/`, data);
  }

  removeFromCollection(cardId: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/collection/${cardId}/`);
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

  // ── Bulk IDs ──
  getMyIds(): Observable<CarpetaIds> {
    return this.http.get<CarpetaIds>(`${this.apiUrl}/ids/`);
  }
}
