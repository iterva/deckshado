import { Injectable, inject } from '@angular/core';
import { Title, Meta } from '@angular/platform-browser';
import { DOCUMENT } from '@angular/common';
import { RouterStateSnapshot, TitleStrategy } from '@angular/router';

const SITE_URL = 'https://shadow-forge-deck.vercel.app';
const DEFAULT_TITLE = 'ShadowForge — Constructor de mazos Mitos y Leyendas (MYL)';
const DEFAULT_DESC = 'ShadowForge: constructor y editor de mazos de Mitos y Leyendas (MYL). Banlist oficial, formatos Imperio, Escuelas Elementales y VCR, colección y comparador de decks.';

/**
 * TitleStrategy custom que sincroniza <title>, meta description, OG y <link rel=canonical>
 * a partir de los datos de cada ruta (data.description, data.path, route.title).
 */
@Injectable({ providedIn: 'root' })
export class SeoTitleStrategy extends TitleStrategy {
  private title = inject(Title);
  private meta = inject(Meta);
  private doc = inject(DOCUMENT);

  override updateTitle(routerState: RouterStateSnapshot): void {
    const title = this.buildTitle(routerState) ?? DEFAULT_TITLE;
    this.title.setTitle(title);

    // Buscar la ruta hoja para leer data.description
    const desc = this.findRouteData(routerState)?.['description'] || DEFAULT_DESC;
    this.meta.updateTag({ name: 'description', content: desc });
    this.meta.updateTag({ property: 'og:title', content: title });
    this.meta.updateTag({ property: 'og:description', content: desc });
    this.meta.updateTag({ name: 'twitter:title', content: title });
    this.meta.updateTag({ name: 'twitter:description', content: desc });

    // Canonical dinámico (sin query string para evitar duplicados)
    const url = SITE_URL + routerState.url.split('?')[0];
    this.meta.updateTag({ property: 'og:url', content: url });
    let link = this.doc.querySelector<HTMLLinkElement>('link[rel="canonical"]');
    if (!link) {
      link = this.doc.createElement('link');
      link.setAttribute('rel', 'canonical');
      this.doc.head.appendChild(link);
    }
    link.setAttribute('href', url);
  }

  private findRouteData(state: RouterStateSnapshot): Record<string, any> | null {
    let r: any = state.root;
    while (r?.firstChild) r = r.firstChild;
    return r?.data || null;
  }
}
