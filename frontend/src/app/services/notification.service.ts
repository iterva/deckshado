import { Injectable, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { environment } from '../../environments/environment';

export interface AppNotification {
  id: number;
  type: string;
  message: string;
  link: string;
  is_read: boolean;
  created_at: string;
}

@Injectable({ providedIn: 'root' })
export class NotificationService {
  private readonly api = `${environment.apiUrl}/auth/notifications`;
  readonly notifications = signal<AppNotification[]>([]);
  readonly unreadCount = signal(0);

  constructor(private http: HttpClient) {}

  load() {
    this.http.get<{ notifications: AppNotification[]; unread_count: number }>(`${this.api}/`).subscribe({
      next: (res) => {
        this.notifications.set(res.notifications);
        this.unreadCount.set(res.unread_count);
      },
    });
  }

  markRead(id: number) {
    this.http.post(`${this.api}/${id}/read/`, {}).subscribe(() => {
      this.notifications.update(list =>
        list.map(n => n.id === id ? { ...n, is_read: true } : n)
      );
      this.unreadCount.update(c => Math.max(0, c - 1));
    });
  }

  markAllRead() {
    this.http.post(`${this.api}/read-all/`, {}).subscribe(() => {
      this.notifications.update(list => list.map(n => ({ ...n, is_read: true })));
      this.unreadCount.set(0);
    });
  }
}
