import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { Title } from '@angular/platform-browser';
import { RiftboundService } from '../../../services/riftbound.service';

@Component({
  selector: 'app-riftbound-home',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <div class="hero">
      <div class="hero-content">
        <h1 class="hero-title">
          <span class="icon">✨</span> ShadowForge <span class="sep">—</span> <span class="rb">Riftbound</span>
        </h1>
        <p class="hero-subtitle">Construye, comparte y descubre mazos del TCG de League of Legends</p>
        <div class="hero-stats">
          <div class="stat">
            <span class="stat-number">{{ totalCards() !== null ? totalCards() : '...' }}</span>
            <span class="stat-label">Cartas</span>
          </div>
          <div class="stat">
            <span class="stat-number">{{ totalDecks() !== null ? totalDecks() : '...' }}</span>
            <span class="stat-label">Mazos públicos</span>
          </div>
        </div>
      </div>
    </div>

    <div class="features container">
      <div class="feature-card" routerLink="/riftbound/cards">
        <div class="feature-icon">🃏</div>
        <h3>Explorador de cartas</h3>
        <p>Busca entre cientos de cartas por tipo, energía, color, set y más.</p>
      </div>

      <div class="feature-card" routerLink="/riftbound/builder">
        <div class="feature-icon">🔨</div>
        <h3>Constructor de mazos</h3>
        <p>Arma tus mazos con validación de zonas: principal, runas, sideboard, campeón y battlegrounds.</p>
      </div>

      <div class="feature-card" routerLink="/riftbound/decks">
        <div class="feature-icon">📚</div>
        <h3>Mazos de la comunidad</h3>
        <p>Inspírate con mazos compartidos por otros jugadores de Riftbound.</p>
      </div>

      <div class="feature-card" routerLink="/riftbound/carpeta">
        <div class="feature-icon">📁</div>
        <h3>Mi carpeta</h3>
        <p>Lleva el control de las cartas que tienes y de tu wishlist.</p>
      </div>

      <div class="feature-card highlight" routerLink="/riftbound/banlist">
        <div class="feature-icon">⚖️</div>
        <h3>Banlist Standard</h3>
        <p>Cartas baneadas y restringidas del formato oficial.</p>
      </div>
    </div>

    <section class="seo-content container">
      <div class="seo-block">
        <h2>Reglas de construcción (Standard)</h2>
        <ul class="seo-list">
          <li><strong>Mazo principal:</strong> 40 cartas exactas.</li>
          <li><strong>Sideboard:</strong> 8 cartas exactas.</li>
          <li><strong>Mazo de runas:</strong> 12 runas exactas.</li>
          <li><strong>Campeón:</strong> 1 carta obligatoria (no cuenta en las 40).</li>
          <li><strong>Battlegrounds:</strong> 3 cartas en mazo aparte.</li>
          <li><strong>Máximo 3 copias</strong> de la misma carta.</li>
        </ul>
      </div>

      <div class="seo-block">
        <h2>Empieza ahora</h2>
        <ul class="seo-links">
          <li><a routerLink="/riftbound/cards">Explorar todas las cartas de Riftbound</a></li>
          <li><a routerLink="/riftbound/builder">Construir un mazo nuevo</a></li>
          <li><a routerLink="/riftbound/decks">Ver mazos de la comunidad</a></li>
          <li><a routerLink="/riftbound/carpeta">Gestionar mi carpeta y wishlist</a></li>
          <li><a routerLink="/riftbound/banlist">Banlist Standard actualizada</a></li>
        </ul>
      </div>

      <div class="seo-block">
        <h2>Preguntas frecuentes</h2>
        <details>
          <summary>¿Qué es Riftbound?</summary>
          <p>Riftbound es el trading card game oficial del universo de League of Legends, desarrollado por Riot Games.</p>
        </details>
        <details>
          <summary>¿Es gratis usar ShadowForge para Riftbound?</summary>
          <p>Sí, completamente gratis. Puedes armar mazos, explorar cartas y guardar tu colección sin pagar nada.</p>
        </details>
        <details>
          <summary>¿Puedo cambiar entre Mitos y Leyendas y Riftbound?</summary>
          <p>Sí. Usa el botón ✨/⚔️ del navbar para alternar entre los dos juegos. Tu preferencia se recuerda automáticamente.</p>
        </details>
        <details>
          <summary>¿Cuántas cartas se permiten por mazo?</summary>
          <p>El formato Standard exige exactamente 40 cartas en el mazo principal, 8 en el sideboard, 12 runas, 1 campeón y 3 battlegrounds.</p>
        </details>
      </div>
    </section>
  `,
  styles: [`
    .hero {
      background: linear-gradient(135deg, #0a1428 0%, #091428 50%, #0a323c 100%);
      padding: 4rem 2rem;
      text-align: center;
      border-bottom: 2px solid #c89b3c;
    }
    .hero-title {
      font-size: 3rem;
      font-weight: 700;
      margin-bottom: 0.5rem;
      background: linear-gradient(90deg, #c89b3c, #f0e6d2);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      color: transparent;
    }
    .hero-title .icon { font-size: 2.5rem; -webkit-text-fill-color: initial; }
    .hero-title .sep { opacity: .6; }
    .hero-subtitle { color: #aaa; font-size: 1.2rem; margin-bottom: 2rem; }
    .hero-stats { display: flex; justify-content: center; gap: 3rem; flex-wrap: wrap; }
    .hero-stats .stat { display: flex; flex-direction: column; }
    .hero-stats .stat-number { font-size: 2rem; font-weight: 700; color: #f0e6d2; }
    .hero-stats .stat-label { color: #888; font-size: 0.9rem; }

    .features {
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 1.25rem;
      padding-top: 3rem;
      padding-bottom: 3rem;
    }
    @media (max-width: 1200px) { .features { grid-template-columns: repeat(3, 1fr); } }
    @media (max-width: 800px)  { .features { grid-template-columns: repeat(2, 1fr); } }
    @media (max-width: 520px)  { .features { grid-template-columns: 1fr; } }

    .feature-card {
      background: #0a1428;
      border: 1px solid #1e3a4a;
      border-radius: 12px;
      padding: 2rem 1.25rem;
      text-align: center;
      cursor: pointer;
      transition: all 0.3s;
    }
    .feature-card:hover {
      border-color: #c89b3c;
      transform: translateY(-4px);
      box-shadow: 0 8px 25px rgba(200, 155, 60, 0.25);
    }
    .feature-card.highlight {
      border-color: rgba(200, 155, 60, 0.5);
      background: linear-gradient(135deg, #0a1428 0%, #2a1f10 100%);
    }
    .feature-card.highlight:hover {
      border-color: #c89b3c;
      box-shadow: 0 8px 25px rgba(200, 155, 60, 0.35);
    }
    .feature-icon { font-size: 2.5rem; margin-bottom: 1rem; }
    .feature-card h3 { font-size: 1.15rem; margin-bottom: 0.5rem; color: #f0e6d2; }
    .feature-card p  { color: #98a2a8; font-size: 0.9rem; line-height: 1.5; margin: 0; }

    .seo-content { padding: 1rem 1rem 4rem; max-width: 900px; }
    .seo-content .seo-block { margin-bottom: 2.5rem; }
    .seo-content h2 {
      color: #f0e6d2;
      font-size: 1.5rem;
      margin-bottom: 0.75rem;
      border-left: 3px solid #c89b3c;
      padding-left: 0.75rem;
    }
    .seo-content p, .seo-content li { color: #c8c8d0; line-height: 1.7; font-size: 1rem; }
    .seo-content strong { color: #c89b3c; font-weight: 600; }
    .seo-list, .seo-links { margin: 0; padding-left: 1.25rem; }
    .seo-list li, .seo-links li { margin-bottom: 0.4rem; }
    .seo-links a { color: #c89b3c; text-decoration: none; font-weight: 600; }
    .seo-links a:hover { text-decoration: underline; }

    .seo-content details {
      background: #0a1428;
      border: 1px solid #1e3a4a;
      border-radius: 8px;
      padding: 0.75rem 1rem;
      margin-bottom: 0.6rem;
    }
    .seo-content summary {
      cursor: pointer;
      color: #f0e6d2;
      font-weight: 600;
      list-style: none;
      padding: 0.25rem 0;
    }
    .seo-content summary::before { content: "+ "; color: #c89b3c; }
    .seo-content details[open] summary::before { content: "− "; }
    .seo-content details p { margin-top: 0.6rem; margin-bottom: 0; color: #98a2a8; }

    /* Light theme overrides */
    :host-context(body.light-theme) .hero {
      background: linear-gradient(135deg, #f0e6d2 0%, #e8d8a8 50%, #d4c489 100%);
      border-bottom-color: #785a28;
    }
    :host-context(body.light-theme) .hero-title {
      background: linear-gradient(90deg, #785a28, #463714);
      -webkit-background-clip: text;
      background-clip: text;
    }
    :host-context(body.light-theme) .hero-subtitle { color: #5a4a2a; }
    :host-context(body.light-theme) .hero-stats .stat-number { color: #785a28; }
    :host-context(body.light-theme) .hero-stats .stat-label { color: #6a5a3a; }
    :host-context(body.light-theme) .feature-card {
      background: #fbf6e9;
      border-color: #d4c489;
    }
    :host-context(body.light-theme) .feature-card h3 { color: #463714; }
    :host-context(body.light-theme) .feature-card p { color: #5a4a2a; }
    :host-context(body.light-theme) .seo-content h2 { color: #463714; }
    :host-context(body.light-theme) .seo-content p,
    :host-context(body.light-theme) .seo-content li { color: #4a3c1e; }
    :host-context(body.light-theme) .seo-content details {
      background: #fbf6e9;
      border-color: #d4c489;
    }
    :host-context(body.light-theme) .seo-content summary { color: #463714; }
  `],
})
export class RiftboundHomeComponent implements OnInit {
  private rb = inject(RiftboundService);
  private titleSvc = inject(Title);

  totalCards = signal<number | null>(null);
  totalDecks = signal<number | null>(null);

  ngOnInit() {
    this.titleSvc.setTitle('ShadowForge — Riftbound | Constructor de mazos LoL TCG');
    this.rb.listCards({ page: 1, lite: true }).subscribe({
      next: (r) => this.totalCards.set(r.count),
      error: () => this.totalCards.set(0),
    });
    this.rb.listDecks({ page: 1 }).subscribe({
      next: (r: any) => this.totalDecks.set(r.count ?? (Array.isArray(r) ? r.length : 0)),
      error: () => this.totalDecks.set(0),
    });
  }
}
