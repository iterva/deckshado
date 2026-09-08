import { Component, ViewChild, ElementRef, AfterViewInit } from '@angular/core';
import { Router, RouterLink, ActivatedRoute } from '@angular/router';
import { AuthService } from '../../services/auth.service';
import { GoogleAuthService } from '../../services/google-auth.service';
import { IconComponent } from '../../components/icon/icon.component';

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [RouterLink, IconComponent],
  templateUrl: './register.component.html',
  styleUrl: './register.component.scss',
})
export class RegisterComponent implements AfterViewInit {
  error = '';
  loading = false;

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
          this.error = 'No se pudo cargar Google Sign-In. Refresca la página.';
        });
    }
  }

  private onGoogleCredential(credential: string) {
    this.error = '';
    this.loading = true;
    this.auth.loginWithGoogle(credential).subscribe({
      next: (tokens) => {
        this.auth.handleLoginSuccess(tokens);
        const returnUrl = this.route.snapshot.queryParamMap.get('returnUrl');
        if (returnUrl && returnUrl.startsWith('/')) {
          this.router.navigateByUrl(returnUrl);
        } else {
          this.router.navigate(['/']);
        }
      },
      error: (err) => {
        this.error = err.error?.detail || 'No se pudo registrar con Google.';
        this.loading = false;
      },
    });
  }
}
