import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DOCUMENT, NgClass } from '@angular/common';
import { CardService } from '../../services/card.service';
import { BanlistEntry } from '../../models';
import { forkJoin } from 'rxjs';

interface FormatBanlist {
  code: string;
  sub: string;
  label: string;
  description: string;
  banned: BanlistEntry[];
  limited1: BanlistEntry[];
  limited2: BanlistEntry[];
  loading: boolean;
}

@Component({
  selector: 'app-banlist-article',
  standalone: true,
  imports: [RouterLink, NgClass],
  templateUrl: './banlist-article.component.html',
  styleUrl: './banlist-article.component.scss',
})
export class BanlistArticleComponent implements OnInit {
  private cards = inject(CardService);
  private doc = inject(DOCUMENT);

  /** Mes y año del artículo (queda fijo en la URL para SEO) */
  readonly month = 'mayo';
  readonly year = 2026;
  readonly publishedDate = '2026-05-03';
  readonly modifiedDate = '2026-05-03';

  formats = signal<FormatBanlist[]>([
    { code: 'imp', sub: 'racial', label: 'Imperio', description: 'Banlist clásica del formato Imperio.', banned: [], limited1: [], limited2: [], loading: true },
    { code: 'imp', sub: 'vcr', label: 'VCR Imperio', description: 'Vasallo, Cortesano y Real — formato competitivo de Imperio.', banned: [], limited1: [], limited2: [], loading: true },
    { code: 'esc', sub: 'racial', label: 'Escuelas Elementales', description: 'Banlist del bloque Escuelas Elementales.', banned: [], limited1: [], limited2: [], loading: true },
  ]);

  totalBanned = signal(0);
  totalLimited = signal(0);

  ngOnInit(): void {
    forkJoin(
      this.formats().map(f => this.cards.getBanlist(f.code, f.sub))
    ).subscribe({
      next: (results) => {
        const updated = this.formats().map((f, i) => {
          const entries = results[i] || [];
          return {
            ...f,
            banned: entries.filter(e => e.status === 'banned').sort((a, b) => a.card_name.localeCompare(b.card_name)),
            limited1: entries.filter(e => e.status === 'limited_1').sort((a, b) => a.card_name.localeCompare(b.card_name)),
            limited2: entries.filter(e => e.status === 'limited_2').sort((a, b) => a.card_name.localeCompare(b.card_name)),
            loading: false,
          };
        });
        this.formats.set(updated);
        this.totalBanned.set(updated.reduce((s, f) => s + f.banned.length, 0));
        this.totalLimited.set(updated.reduce((s, f) => s + f.limited1.length + f.limited2.length, 0));
        this.injectStructuredData();
      },
      error: () => {
        this.formats.update(arr => arr.map(f => ({ ...f, loading: false })));
      }
    });
  }

  /** Inyecta JSON-LD Article para que Google muestre rich snippet del artículo. */
  private injectStructuredData() {
    const existing = this.doc.getElementById('banlist-article-jsonld');
    if (existing) existing.remove();
    const json = {
      '@context': 'https://schema.org',
      '@type': 'Article',
      headline: `Banlist Mitos y Leyendas ${this.month} ${this.year}: cartas baneadas y restringidas`,
      datePublished: this.publishedDate,
      dateModified: this.modifiedDate,
      author: { '@type': 'Organization', name: 'ShadowForge' },
      publisher: {
        '@type': 'Organization',
        name: 'ShadowForge',
        logo: { '@type': 'ImageObject', url: 'https://shadow-forge-deck.vercel.app/icon-512.png' },
      },
      mainEntityOfPage: {
        '@type': 'WebPage',
        '@id': `https://shadow-forge-deck.vercel.app/banlist-${this.month}-${this.year}`,
      },
      image: 'https://shadow-forge-deck.vercel.app/og-image.png',
      description: `Banlist oficial de Mitos y Leyendas para ${this.month} ${this.year}. Lista de cartas baneadas y restringidas en los formatos Escuelas Elementales, Imperio y VCR Imperio.`,
      inLanguage: 'es-CL',
      keywords: 'banlist mitos y leyendas, MYL banlist, cartas baneadas mitos y leyendas, cartas restringidas MYL, imperio banlist, escuelas elementales banlist, VCR banlist',
    };
    const s = this.doc.createElement('script');
    s.type = 'application/ld+json';
    s.id = 'banlist-article-jsonld';
    s.textContent = JSON.stringify(json);
    this.doc.head.appendChild(s);
  }

  statusLabel(status: string): string {
    if (status === 'banned') return 'Baneada';
    if (status === 'limited_1') return 'Restringida (1 copia)';
    if (status === 'limited_2') return 'Restringida (2 copias)';
    return status;
  }
}
