import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-riftbound-home',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    <section class="rb-hero">
      <h1>Riftbound</h1>
      <p>Constructor de mazos, explorador de cartas y carpeta para Riftbound (League of Legends TCG).</p>
      <div class="rb-actions">
        <a routerLink="/riftbound/cards" class="rb-btn rb-btn-primary">Explorar cartas</a>
        <a routerLink="/riftbound/builder" class="rb-btn">Constructor</a>
        <a routerLink="/riftbound/decks" class="rb-btn">Mazos públicos</a>
        <a routerLink="/riftbound/carpeta" class="rb-btn">Mi carpeta</a>
        <a routerLink="/riftbound/banlist" class="rb-btn">Banlist Standard</a>
      </div>
    </section>

    <section class="rb-rules">
      <h2>Reglas de construcción (Standard)</h2>
      <ul>
        <li><strong>Mazo principal:</strong> 40 cartas exactas.</li>
        <li><strong>Sideboard:</strong> 8 cartas exactas.</li>
        <li><strong>Mazo de runas:</strong> 12 runas exactas.</li>
        <li><strong>Campeón:</strong> 1 obligatorio (no cuenta en las 40).</li>
        <li><strong>Battlegrounds:</strong> 3 cartas en el mazo aparte.</li>
        <li><strong>Máximo 3 copias</strong> de la misma carta.</li>
      </ul>
    </section>
  `,
  styles: [`
    .rb-hero { padding: 3rem 1rem; text-align: center; }
    .rb-hero h1 { font-size: 3rem; margin: 0 0 1rem; background: linear-gradient(120deg, #c89b3c, #f0e6d2); -webkit-background-clip: text; background-clip: text; color: transparent; }
    .rb-actions { display: flex; gap: .75rem; flex-wrap: wrap; justify-content: center; margin-top: 1.5rem; }
    .rb-btn { padding: .75rem 1.25rem; border-radius: .5rem; border: 1px solid var(--border-color, #444); text-decoration: none; color: inherit; transition: background .15s; }
    .rb-btn:hover { background: var(--card-hover-bg, #2a2a2a); }
    .rb-btn-primary { background: #c89b3c; color: #1a1a1a; border-color: #c89b3c; font-weight: 600; }
    .rb-btn-primary:hover { background: #d4a84b; }
    .rb-rules { max-width: 720px; margin: 2rem auto; padding: 1.5rem; border: 1px solid var(--border-color, #333); border-radius: .75rem; }
    .rb-rules ul { padding-left: 1.5rem; line-height: 1.9; }
  `],
})
export class RiftboundHomeComponent {}
