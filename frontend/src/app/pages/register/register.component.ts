import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: './register.component.html',
  styleUrl: './register.component.scss',
})
export class RegisterComponent {
  username = '';
  email = '';
  password = '';
  confirmPassword = '';
  error = '';
  loading = false;

  constructor(private auth: AuthService, private router: Router) {}

  onSubmit() {
    this.error = '';
    if (this.password !== this.confirmPassword) {
      this.error = 'Las contraseñas no coinciden';
      return;
    }
    this.loading = true;
    this.auth.register(this.username, this.email, this.password).subscribe({
      next: () => {
        this.auth.login(this.username, this.password).subscribe({
          next: (tokens) => {
            this.auth.handleLoginSuccess(tokens);
            this.router.navigate(['/builder']);
          },
          error: () => this.router.navigate(['/login']),
        });
      },
      error: (err) => {
        const detail = err.error;
        if (detail?.username) this.error = detail.username[0];
        else if (detail?.email) this.error = detail.email[0];
        else if (detail?.password) this.error = detail.password[0];
        else this.error = 'Error al registrar. Intenta de nuevo.';
        this.loading = false;
      },
    });
  }
}
