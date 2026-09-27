import { ChangeDetectionStrategy, Component, OnInit, inject, input } from '@angular/core';
import { Title } from '@angular/platform-browser';
import { RouterLink } from '@angular/router';
import { IconComponent } from '../../components/icon/icon.component';

/** Estado "no encontrado": se usa como ruta `**` y dentro de vistas de mazo/carta. */
@Component({
  selector: 'app-not-found',
  imports: [RouterLink, IconComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="not-found" role="status">
      <app-icon name="search" [size]="36" class="nf-icon"></app-icon>
      <h1>{{ heading() }}</h1>
      <p>{{ message() }}</p>
      <a class="btn btn-primary" [routerLink]="link()">{{ linkText() }}</a>
    </section>
  `,
  styles: [`
    .not-found {
      max-width: 420px;
      margin: 3rem auto;
      padding: 2rem 1.5rem;
      text-align: center;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.75rem;
      border: 1px solid var(--ui-border);
      border-radius: var(--ui-radius-lg, 16px);
      background: var(--ui-surface);
    }
    .nf-icon { color: var(--ui-text-muted); }
    h1 { margin: 0; font-size: 1.4rem; color: var(--ui-text); }
    p { margin: 0; color: var(--ui-text-secondary); }
    .btn { margin-top: 0.5rem; padding: 0.55rem 1.2rem; text-decoration: none; }
  `],
})
export class NotFoundComponent implements OnInit {
  readonly heading = input('Página no encontrada');
  readonly message = input('El enlace que seguiste no existe o fue movido.');
  readonly link = input<string>('/');
  readonly linkText = input('Volver al inicio');

  private readonly title = inject(Title);

  ngOnInit() {
    this.title.setTitle('No encontrado | ShadowForge');
  }
}
