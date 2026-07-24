import { Component, signal, AfterViewInit, ViewChild, ElementRef, ChangeDetectorRef } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { GoogleAuthService } from '../../services/google-auth.service';

@Component({
  selector: 'app-profile-edit',
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: './profile-edit.component.html',
  styleUrl: './profile-edit.component.scss',
})
export class ProfileEditComponent implements AfterViewInit {
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

  // Cuentas vinculadas
  googleLinked = signal(false);
  googleEmail = signal('');
  hasUsablePassword = signal(true);
  socialMessage = signal('');

  @ViewChild('googleLinkBtn') googleLinkBtn?: ElementRef<HTMLDivElement>;

  constructor(
    public auth: AuthService,
    private router: Router,
    private googleAuth: GoogleAuthService,
    private cdr: ChangeDetectorRef,
  ) {
    const user = this.auth.user();
    if (user) {
      this.firstName = user.first_name || '';
      this.lastName = user.last_name || '';
      this.leagueCode = user.league_code || '';
    }
    this.loadSocialStatus();
  }

  ngAfterViewInit() {
    this.maybeRenderGoogleLinkButton();
  }

  private loadSocialStatus() {
    this.auth.getSocialStatus().subscribe({
      next: (s) => {
        const google = s.accounts.find(a => a.provider === 'google');
        this.googleLinked.set(!!google);
        this.googleEmail.set(google?.email || '');
        this.hasUsablePassword.set(s.has_usable_password);
        // Render boton si no está vinculado todavía
        setTimeout(() => this.maybeRenderGoogleLinkButton(), 0);
      },
    });
  }

  private maybeRenderGoogleLinkButton() {
    if (this.googleLinked()) return;
    const host = this.googleLinkBtn?.nativeElement;
    if (!host) return;
    if (host.hasChildNodes()) return;
    this.googleAuth.renderButton(host, (cred) => this.onGoogleLink(cred)).catch(() => {});
  }

  private onGoogleLink(credential: string) {
    this.socialMessage.set('');
    this.auth.linkGoogle(credential).subscribe({
      next: (res) => {
        this.googleLinked.set(true);
        this.googleEmail.set(res.email);
        this.socialMessage.set('Google vinculado correctamente.');
        this.cdr.detectChanges();
      },
      error: (err) => {
        this.socialMessage.set(err.error?.detail || 'No se pudo vincular Google.');
      },
    });
  }

  unlinkGoogle() {
    if (!confirm('¿Desvincular tu cuenta de Google? Después solo podrás entrar con usuario y contraseña.')) return;
    this.socialMessage.set('');
    this.auth.unlinkGoogle().subscribe({
      next: () => {
        this.googleLinked.set(false);
        this.googleEmail.set('');
        this.socialMessage.set('Google desvinculado.');
        setTimeout(() => this.maybeRenderGoogleLinkButton(), 0);
      },
      error: (err) => {
        this.socialMessage.set(err.error?.detail || 'No se pudo desvincular.');
      },
    });
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
    input.value = '';
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
        this.hasUsablePassword.set(true);
      },
      error: (err) => {
        this.savingPassword.set(false);
        const detail = err.error?.old_password?.[0] || err.error?.new_password?.[0] || err.error?.detail || 'Error al cambiar la contraseña.';
        this.passwordMessage.set(detail);
      },
    });
  }
}
