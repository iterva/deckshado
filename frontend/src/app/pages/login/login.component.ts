import { Component, ViewChild, ElementRef, AfterViewInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { GoogleAuthService } from '../../services/google-auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [FormsModule, RouterLink],
  templateUrl: './login.component.html',
  styleUrl: './login.component.scss',
})
export class LoginComponent implements AfterViewInit {
  username = '';
  password = '';
  error = '';
  loading = false;
  googleError = '';
  showClassic = false;

  @ViewChild('googleBtn') googleBtn?: ElementRef<HTMLDivElement>;

  constructor(
    private auth: AuthService,
    private router: Router,
    private route: ActivatedRoute,
    private googleAuth: GoogleAuthService,
  ) {}

  ngAfterViewInit() {
    if (this.googleBtn?.nativeElement) {
      this.googleAuth
        .renderButton(this.googleBtn.nativeElement, (cred) => this.onGoogleCredential(cred))
        .catch((e) => {
          console.error(e);
          this.googleError = 'No se pudo cargar el botón de Google. Refresca la página.';
        });
    }
  }

  private onGoogleCredential(credential: string) {
    this.googleError = '';
    this.loading = true;
    this.auth.loginWithGoogle(credential).subscribe({
      next: (tokens) => {
        this.auth.handleLoginSuccess(tokens);
        this.redirectAfterLogin();
      },
      error: (err) => {
        this.googleError = err.error?.detail || 'No se pudo iniciar sesión con Google.';
        this.loading = false;
      },
    });
  }

  private redirectAfterLogin() {
    const returnUrl = this.route.snapshot.queryParamMap.get('returnUrl');
    if (returnUrl && returnUrl.startsWith('/')) {
      this.router.navigateByUrl(returnUrl);
    } else {
      this.router.navigate(['/']);
    }
  }

  onSubmit() {
    this.error = '';
    this.loading = true;
    this.auth.login(this.username, this.password).subscribe({
      next: (tokens) => {
        this.auth.handleLoginSuccess(tokens);
        this.redirectAfterLogin();
      },
      error: () => {
        this.error = 'Usuario o contraseña incorrectos';
        this.loading = false;
      },
    });
  }
}
