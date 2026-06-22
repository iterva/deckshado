import { Component, OnInit, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { DOCUMENT } from '@angular/common';
import { Title, Meta } from '@angular/platform-browser';
import { CardService } from '../../services/card.service';
import { BanlistEntry } from '../../models';
import { forkJoin } from 'rxjs';
import { BANLIST_EDITIONS, BanlistEdition, getCurrentBanlistEdition, getBanlistEditionBySlug } from './banlist-editions';

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
  imports: [RouterLink],
  templateUrl: './banlist-article.component.html',
  styleUrl: './banlist-article.component.scss',
})
export class BanlistArticleComponent implements OnInit {
  private cards = inject(CardService);
  private doc = inject(DOCUMENT);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private titleSvc = inject(Title);
  private metaSvc = inject(Meta);

  edition = signal<BanlistEdition>(getCurrentBanlistEdition());
  allEditions = BANLIST_EDITIONS;

  formats = signal<FormatBanlist[]>([
    { code: 'imp', sub: 'racial', label: 'Imperio', description: 'Banlist clásica del formato Imperio.', banned: [], limited1: [], limited2: [], loading: true },
    { code: 'imp', sub: 'vcr', label: 'VCR Imperio', description: 'Vasallo, Cortesano y Real — formato competitivo de Imperio.', banned: [], limited1: [], limited2: [], loading: true },
    { code: 'esc', sub: 'racial', label: 'Escuelas Elementales', description: 'Banlist del bloque Escuelas Elementales.', banned: [], limited1: [], limited2: [], loading: true },
  ]);

  totalBanned = signal(0);
  totalLimited = signal(0);

  ngOnInit(): void {
    this.route.paramMap.subscribe(params => {
      const slug = params.get('slug');
      const found = slug ? getBanlistEditionBySlug(slug) : null;
      if (slug && !found) {
        this.router.navigate(['/banlist', getCurrentBanlistEdition().slug], { replaceUrl: true });
        return;
      }
      this.edition.set(found || getCurrentBanlistEdition());
      this.applySeo();
      this.injectStructuredData();
    });

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
      },
      error: () => {
        this.formats.update(arr => arr.map(f => ({ ...f, loading: false })));
      }
    });
  }

  /** Title + meta description + canonical en runtime para esta edición. */
  private applySeo() {
    const e = this.edition();
    const title = `Banlist Mitos y Leyendas ${e.month} ${e.year} — cartas baneadas y restringidas | ShadowForge`;
    const desc = `Banlist oficial de Mitos y Leyendas (MYL) ${e.month} ${e.year}. Lista de cartas baneadas y restringidas en Escuelas Elementales, Imperio y VCR Imperio.`;
    const url = `https://shadow-forge-deck.vercel.app/banlist/${e.slug}`;
    this.titleSvc.setTitle(title);
    this.metaSvc.updateTag({ name: 'description', content: desc });
    this.metaSvc.updateTag({ property: 'og:title', content: title });
    this.metaSvc.updateTag({ property: 'og:description', content: desc });
    this.metaSvc.updateTag({ property: 'og:url', content: url });
    const link = this.doc.querySelector<HTMLLinkElement>('link[rel="canonical"]');
    if (link) link.setAttribute('href', url);
  }

  /** Inyecta JSON-LD Article para que Google muestre rich snippet del artículo. */
  private injectStructuredData() {
    const e = this.edition();
    const existing = this.doc.getElementById('banlist-article-jsonld');
    if (existing) existing.remove();
    const json = {
      '@context': 'https://schema.org',
      '@type': 'Article',
      headline: `Banlist Mitos y Leyendas ${e.month} ${e.year}: cartas baneadas y restringidas`,
      datePublished: e.publishedDate,
      dateModified: e.modifiedDate,
      author: { '@type': 'Organization', name: 'ShadowForge' },
      publisher: {
        '@type': 'Organization',
        name: 'ShadowForge',
        logo: { '@type': 'ImageObject', url: 'https://shadow-forge-deck.vercel.app/icon-512.png' },
      },
      mainEntityOfPage: {
        '@type': 'WebPage',
        '@id': `https://shadow-forge-deck.vercel.app/banlist/${e.slug}`,
      },
      image: 'https://shadow-forge-deck.vercel.app/og-image.png',
      description: `Banlist oficial de Mitos y Leyendas para ${e.month} ${e.year}. Lista de cartas baneadas y restringidas en Escuelas Elementales, Imperio y VCR Imperio.`,
      inLanguage: 'es-CL',
      keywords: 'banlist mitos y leyendas, MYL banlist, cartas baneadas mitos y leyendas, cartas restringidas MYL, imperio banlist, escuelas elementales banlist, VCR Imperio banlist',
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
