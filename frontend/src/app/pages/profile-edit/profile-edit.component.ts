import { Component, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-profile-edit',
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: './profile-edit.component.html',
  styleUrl: './profile-edit.component.scss',
})
export class ProfileEditComponent {
  firstName = '';
  lastName = '';
  leagueCode = '';
  oldPassword = '';
  newPassword = '';
  confirmPassword = '';

  saving = signal(false);
  savingPassword = signal(false);
  message = signal('');
  passwordMessage = signal('');
  avatarPreview = signal<string | null>(null);
  private avatarFile: File | null = null;

  constructor(public auth: AuthService, private router: Router) {
    const user = this.auth.user();
    if (user) {
      this.firstName = user.first_name || '';
      this.lastName = user.last_name || '';
      this.leagueCode = user.league_code || '';
    }
  }

  onAvatarSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    if (file.size > 2 * 1024 * 1024) {
      this.message.set('La imagen no puede superar 2 MB.');
      return;
    }
    this.avatarFile = file;
    const reader = new FileReader();
    reader.onload = () => this.avatarPreview.set(reader.result as string);
    reader.readAsDataURL(file);
  }

  saveProfile() {
    this.saving.set(true);
    this.message.set('');

    const uploadAvatar = () => {
      if (this.avatarFile) {
        this.auth.uploadAvatar(this.avatarFile).subscribe({
          next: () => {
            this.saving.set(false);
            this.message.set('Perfil actualizado correctamente.');
          },
          error: () => {
            this.saving.set(false);
            this.message.set('Error al subir la imagen.');
          },
        });
      } else {
        this.saving.set(false);
        this.message.set('Perfil actualizado correctamente.');
      }
    };

    this.auth.updateProfile({
      first_name: this.firstName,
      last_name: this.lastName,
      league_code: this.leagueCode,
    }).subscribe({
      next: () => uploadAvatar(),
      error: () => {
        this.saving.set(false);
        this.message.set('Error al guardar los cambios.');
      },
    });
  }

  changePassword() {
    this.passwordMessage.set('');
    if (this.newPassword !== this.confirmPassword) {
      this.passwordMessage.set('Las contraseñas no coinciden.');
      return;
    }
    this.savingPassword.set(true);
    this.auth.changePassword(this.oldPassword, this.newPassword).subscribe({
      next: (res) => {
        this.savingPassword.set(false);
        this.passwordMessage.set(res.detail);
        this.oldPassword = '';
        this.newPassword = '';
        this.confirmPassword = '';
      },
      error: (err) => {
        this.savingPassword.set(false);
        const detail = err.error?.old_password?.[0] || err.error?.new_password?.[0] || err.error?.detail || 'Error al cambiar la contraseña.';
        this.passwordMessage.set(detail);
      },
    });
  }
}
