import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient } from '@angular/common/http';
import { Router, RouterLink } from '@angular/router';
import { environment } from '../../../environments/environment';
import { AuthService } from '../../services/auth.service';
import { AdminUser } from '../../models';

@Component({
  selector: 'app-admin',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, DatePipe],
  templateUrl: './admin.component.html',
  styleUrl: './admin.component.scss',
})
export class AdminComponent implements OnInit {
  private readonly apiUrl = `${environment.apiUrl}/auth/admin`;

  users = signal<AdminUser[]>([]);
  loading = signal(false);
  searchQuery = '';
  message = signal('');
  error = signal('');

  // Edit modal state
  editing = signal<AdminUser | null>(null);
  editForm = {
    username: '',
    email: '',
    first_name: '',
    last_name: '',
    league_code: '',
    is_active: true,
    is_staff: false,
  };
  saving = signal(false);

  // Password reset modal state
  resettingFor = signal<AdminUser | null>(null);
  newPassword = '';
  resetSaving = signal(false);

  filtered = computed(() => {
    const q = this.searchQuery.trim().toLowerCase();
    if (!q) return this.users();
    return this.users().filter(u =>
      u.username.toLowerCase().includes(q) ||
      (u.email || '').toLowerCase().includes(q)
    );
  });

  constructor(
    private http: HttpClient,
    public auth: AuthService,
    private router: Router,
  ) {}

  ngOnInit() {
    const me = this.auth.user();
    if (!me?.is_admin) {
      this.router.navigate(['/']);
      return;
    }
    this.loadUsers();
  }

  loadUsers() {
    this.loading.set(true);
    this.error.set('');
    this.http.get<AdminUser[]>(`${this.apiUrl}/users/`).subscribe({
      next: (data) => {
        this.users.set(data);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(err?.error?.detail || 'No se pudieron cargar los usuarios.');
        this.loading.set(false);
      },
    });
  }

  toggleActive(u: AdminUser) {
    const action = u.is_active ? 'banear' : 'reactivar';
    if (!confirm(`¿Seguro que deseas ${action} a "${u.username}"?`)) return;
    this.http.patch<AdminUser>(`${this.apiUrl}/users/${u.id}/`, {
      is_active: !u.is_active,
    }).subscribe({
      next: (updated) => {
        this.users.update(list => list.map(x => x.id === updated.id ? updated : x));
        this.message.set(`Usuario "${updated.username}" ${updated.is_active ? 'reactivado' : 'baneado'}.`);
        setTimeout(() => this.message.set(''), 3000);
      },
      error: (err) => {
        this.error.set(err?.error?.detail || 'Error al actualizar el usuario.');
        setTimeout(() => this.error.set(''), 4000);
      },
    });
  }

  toggleStaff(u: AdminUser) {
    if (!confirm(`¿Cambiar permisos de staff para "${u.username}"?`)) return;
    this.http.patch<AdminUser>(`${this.apiUrl}/users/${u.id}/`, {
      is_staff: !u.is_staff,
    }).subscribe({
      next: (updated) => {
        this.users.update(list => list.map(x => x.id === updated.id ? updated : x));
      },
      error: (err) => {
        this.error.set(err?.error?.detail || 'Error al actualizar permisos.');
        setTimeout(() => this.error.set(''), 4000);
      },
    });
  }

  openEdit(u: AdminUser) {
    this.editing.set(u);
    this.editForm = {
      username: u.username,
      email: u.email || '',
      first_name: u.first_name || '',
      last_name: u.last_name || '',
      league_code: u.league_code || '',
      is_active: u.is_active,
      is_staff: u.is_staff,
    };
  }

  closeEdit() {
    this.editing.set(null);
  }

  saveEdit() {
    const target = this.editing();
    if (!target) return;
    this.saving.set(true);
    this.http.patch<AdminUser>(`${this.apiUrl}/users/${target.id}/`, this.editForm).subscribe({
      next: (updated) => {
        this.users.update(list => list.map(x => x.id === updated.id ? updated : x));
        this.saving.set(false);
        this.editing.set(null);
        this.message.set('Usuario actualizado correctamente.');
        setTimeout(() => this.message.set(''), 3000);
      },
      error: (err) => {
        this.saving.set(false);
        this.error.set(err?.error?.detail || JSON.stringify(err?.error) || 'Error al guardar.');
        setTimeout(() => this.error.set(''), 5000);
      },
    });
  }

  openReset(u: AdminUser) {
    this.resettingFor.set(u);
    this.newPassword = '';
  }

  closeReset() {
    this.resettingFor.set(null);
    this.newPassword = '';
  }

  saveReset() {
    const target = this.resettingFor();
    if (!target) return;
    if (this.newPassword.length < 8) {
      this.error.set('La contraseña debe tener al menos 8 caracteres.');
      return;
    }
    this.resetSaving.set(true);
    this.http.post<{ detail: string }>(
      `${this.apiUrl}/users/${target.id}/reset-password/`,
      { new_password: this.newPassword },
    ).subscribe({
      next: () => {
        this.resetSaving.set(false);
        this.resettingFor.set(null);
        this.newPassword = '';
        this.message.set(`Contraseña de "${target.username}" actualizada.`);
        setTimeout(() => this.message.set(''), 3000);
      },
      error: (err) => {
        this.resetSaving.set(false);
        this.error.set(err?.error?.detail || 'Error al cambiar contraseña.');
        setTimeout(() => this.error.set(''), 4000);
      },
    });
  }
}
