import { Routes } from '@angular/router';
import { unsavedChangesGuard } from './guards/unsaved-changes.guard';

export const routes: Routes = [
  {
    path: '',
    title: 'ShadowForge — Constructor de mazos Mitos y Leyendas (MYL)',
    data: { description: 'Arma, comparte y descubre mazos de Mitos y Leyendas. Banlist oficial, formatos VCR, Primer Era y Racial, validador de decks y colección personal.' },
    loadComponent: () => import('./pages/home/home.component').then(m => m.HomeComponent)
  },
  {
    path: 'login',
    title: 'Iniciar sesión | ShadowForge',
    data: { description: 'Inicia sesión en ShadowForge para guardar tus mazos de Mitos y Leyendas y gestionar tu colección.' },
    loadComponent: () => import('./pages/login/login.component').then(m => m.LoginComponent)
  },
  {
    path: 'register',
    title: 'Crear cuenta | ShadowForge',
    data: { description: 'Regístrate gratis en ShadowForge y empieza a armar mazos de Mitos y Leyendas (MYL).' },
    loadComponent: () => import('./pages/register/register.component').then(m => m.RegisterComponent)
  },
  {
    path: 'cards',
    title: 'Cartas de Mitos y Leyendas — Buscador completo | ShadowForge',
    data: { description: 'Explora todas las cartas de Mitos y Leyendas: aliados, armas, talismanes, tótems y oros. Filtra por raza, edición, costo, daño y banlist VCR.' },
    loadComponent: () => import('./pages/card-list/card-list.component').then(m => m.CardListComponent)
  },
  {
    path: 'carpeta',
    title: 'Mi colección de cartas MYL | ShadowForge',
    data: { description: 'Gestiona tu colección de cartas de Mitos y Leyendas: marca las que tienes, arma una wishlist y compártela.' },
    loadComponent: () => import('./pages/carpeta/carpeta.component').then(m => m.CarpetaComponent)
  },
  {
    path: 'decks',
    title: 'Mazos de Mitos y Leyendas — Comunidad ShadowForge',
    data: { description: 'Descubre mazos de Mitos y Leyendas creados por la comunidad. Primer Era, Racial, VCR y más. Filtra por formato, raza y popularidad.' },
    loadComponent: () => import('./pages/deck-list/deck-list.component').then(m => m.DeckListComponent)
  },
  {
    path: 'decks/compare',
    title: 'Comparar mazos MYL | ShadowForge',
    data: { description: 'Compara dos mazos de Mitos y Leyendas lado a lado: cartas comunes, diferencias y estadísticas.' },
    loadComponent: () => import('./pages/compare-decks/compare-decks.component').then(m => m.CompareDecksComponent)
  },
  {
    path: 'decks/:id',
    loadComponent: () => import('./pages/deck-view/deck-view.component').then(m => m.DeckViewComponent)
  },
  {
    path: 'builder',
    title: 'Elegir formato — Constructor de mazos MYL | ShadowForge',
    data: { description: 'Elige formato (Primer Era, Racial, VCR) y empieza a armar tu mazo de Mitos y Leyendas con validación de banlist en tiempo real.' },
    loadComponent: () => import('./pages/format-select/format-select.component').then(m => m.FormatSelectComponent)
  },
  {
    path: 'builder/new/:format',
    title: 'Nuevo mazo — Constructor MYL | ShadowForge',
    data: { description: 'Constructor de mazos de Mitos y Leyendas con validación automática de banlist, estadísticas y exportación.' },
    loadComponent: () => import('./pages/deck-builder/deck-builder.component').then(m => m.DeckBuilderComponent),
    canDeactivate: [unsavedChangesGuard]
  },
  {
    path: 'builder/:id',
    title: 'Editar mazo — Constructor MYL | ShadowForge',
    data: { description: 'Edita tu mazo de Mitos y Leyendas: cambia cartas, valida banlist y guarda cambios.' },
    loadComponent: () => import('./pages/deck-builder/deck-builder.component').then(m => m.DeckBuilderComponent),
    canDeactivate: [unsavedChangesGuard]
  },
  {
    path: 'team',
    title: 'Equipo ShadowForge',
    data: { description: 'Conoce al equipo detrás de ShadowForge, la herramienta para jugadores de Mitos y Leyendas.' },
    loadComponent: () => import('./pages/team/team.component').then(m => m.TeamComponent)
  },
  {
    path: 'profile',
    title: 'Mi perfil | ShadowForge',
    data: { description: 'Tu perfil de jugador en ShadowForge: mazos, colección y estadísticas.' },
    loadComponent: () => import('./pages/profile/profile.component').then(m => m.ProfileComponent)
  },
  {
    path: 'profile/edit',
    title: 'Editar perfil | ShadowForge',
    data: { description: 'Edita tu perfil de ShadowForge.' },
    loadComponent: () => import('./pages/profile-edit/profile-edit.component').then(m => m.ProfileEditComponent)
  },
  {
    path: 'tienda/:token',
    loadComponent: () => import('./pages/tienda/tienda.component').then(m => m.TiendaComponent)
  },
  {
    path: 't/:slug',
    loadComponent: () => import('./pages/tienda/tienda.component').then(m => m.TiendaComponent)
  },
  {
    path: 'tiendas',
    title: 'Tiendas de Mitos y Leyendas en Chile | ShadowForge',
    data: { description: 'Directorio de tiendas físicas y online donde comprar cartas y sobres de Mitos y Leyendas en Chile.' },
    loadComponent: () => import('./pages/stores-index/stores-index.component').then(m => m.StoresIndexComponent)
  },
  {
    path: 'admin',
    title: 'Admin | ShadowForge',
    data: { description: 'Panel de administración.' },
    loadComponent: () => import('./pages/admin/admin.component').then(m => m.AdminComponent)
  },
  { path: '**', redirectTo: '' },
];
